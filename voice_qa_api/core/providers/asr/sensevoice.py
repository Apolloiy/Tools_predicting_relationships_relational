"""
SenseVoice 本地语音识别实现
使用 models/SenseVoiceSmall/model.pt 模型
"""
import os
import wave
import uuid
import logging
import tempfile
import io
import re
import numpy as np
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)

# 导入音频预处理模块
try:
    from .audio_preprocessor import (
        ensure_mono_16khz,
        process_audio,
        normalize_audio,
        detect_silence,
        spectral_subtraction,
        resample_audio
    )
    HAS_PREPROCESSOR = True
except ImportError as e:
    logger.warning(f"音频预处理模块导入失败: {e}")
    HAS_PREPROCESSOR = False


def clean_asr_output(text):
    """
    清洗 ASR 输出中的特殊标签，如 <|en|>, <|EMO_UNKNOWN|> 等
    """
    if not text:
        return ""

    # 正则表达式：匹配 <| ... |> 格式的内容并替换为空
    # \s* 用于同时去除标签周围可能存在的多余空格
    cleaned_text = re.sub(r'<\|.*?\|>\s*', '', text)

    return cleaned_text.strip()


class ASRProvider:
    """基于 SenseVoice 模型的本 ASR 服务"""

    def __init__(self, config: dict, delete_audio_file: bool = True):
        self.model_dir = config.get("model_dir", "models/SenseVoiceSmall")
        self.output_dir = config.get("output_dir", "tmp")
        self.delete_audio_file = delete_audio_file
        self.model = None
        self._initialize()

    def _initialize(self):
        """初始化 SenseVoice 模型"""
        try:
            # 尝试使用 funasr
            from funasr import AutoModel

            logger.info(f"正在加载 SenseVoice 模型: {self.model_dir}")

            self.model = AutoModel(
                model=self.model_dir,
                vad_model="fsmn-vad",
                vad_kwargs={"max_single_segment_time": 30000},
                hub="hf",
                disable_update=True,  # 禁用自动更新，避免耗时
            )

            logger.info("SenseVoice 模型加载成功")

        except ImportError as e:
            logger.warning(f"funasr 未安装，将使用 modelscope pipeline: {e}")
            try:
                from modelscope.pipelines import pipeline
                from modelscope.utils.constant import Tasks

                self.model = pipeline(
                    Tasks.auto_speech_recognition,
                    model=self.model_dir,
                    disable_update=True,
                )
                self._use_pipeline = True
                logger.info("使用 modelscope pipeline 加载 SenseVoice 模型成功")
            except Exception as e2:
                logger.error(f"modelscope pipeline 也加载失败: {e2}")
                raise

    def _save_audio(self, audio_data: bytes, audio_format: str) -> Tuple[str, dict]:
        """保存音频数据到临时文件，返回文件路径和元数据"""
        os.makedirs(self.output_dir, exist_ok=True)
        file_name = f"asr_{uuid.uuid4().hex[:8]}.wav"
        file_path = os.path.join(self.output_dir, file_name)

        metadata = {"channels": 1, "sample_rate": 16000, "sample_width": 2}

        # 检查文件头，尝试识别格式
        file_header = audio_data[:32]
        logger.debug(f"音频文件头: {file_header.hex()}")

        # 检查是否是 WAV 格式
        is_wav = (
            audio_format.lower() in ("wav", "audio/wav") or
            (len(audio_data) > 12 and file_header[:4] == b"RIFF" and file_header[8:12] == b"WAVE")
        )

        # 检查是否是 MP3 格式
        is_mp3 = (
            audio_format.lower() in ("mp3", "audio/mp3") or
            (len(audio_data) > 3 and file_header[:3] == b"ID3") or
            (len(audio_data) > 4 and file_header[:4] == b"\xff\xfb") or
            (len(audio_data) > 4 and file_header[:4] == b"\xff\xf3") or
            (len(audio_data) > 4 and file_header[:4] == b"\xff\xf2")
        )

        # 检查是否是 M4A/MP4 格式
        is_m4a = (
            audio_format.lower() in ("m4a", "mp4", "audio/m4a", "audio/mp4") or
            (len(audio_data) > 8 and file_header[:8] == b"\x00\x00\x00\x18ftyp") or
            (len(audio_data) > 4 and file_header[:4] == b"ftyp") or
            (len(audio_data) > 4 and file_header[:4] == b"moov")
        )

        # 检查是否是 OGG 格式
        is_ogg = (
            audio_format.lower() in ("ogg", "audio/ogg") or
            (len(audio_data) > 4 and file_header[:4] == b"OggS")
        )

        processed_audio = None

        # 优先使用 pydub + ffmpeg 解码（支持 M4A、MP3、OGG 等）
        if is_m4a or is_mp3 or is_ogg or not is_wav:
            try:
                from pydub import AudioSegment

                # 使用 pydub 读取音频
                audio_segment = AudioSegment.from_file(io.BytesIO(audio_data))
                
                # 转换为单声道 16kHz
                audio_segment = audio_segment.set_channels(1).set_frame_rate(16000).set_sample_width(2)
                
                # 导出为 WAV
                audio_segment.export(file_path, format="wav")
                
                metadata["channels"] = 1
                metadata["sample_rate"] = 16000
                metadata["sample_width"] = 2
                logger.info(f"使用 pydub 解码成功，格式: {audio_format}")
                
                # 读取处理后的音频进行增强
                with wave.open(file_path, "rb") as wf:
                    processed_frames = wf.readframes(wf.getnframes())
                
                processed_audio, _ = process_audio(processed_frames, 16000)
                
                with wave.open(file_path, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(processed_audio)
                
                logger.info("音频预处理完成（pydub路径）")
                return file_path, metadata
                
            except Exception as e:
                logger.warning(f"pydub 解码失败: {e}")
                # 继续尝试其他方法

        if is_wav:
            try:
                # 尝试解析 WAV 文件
                with wave.open(io.BytesIO(audio_data)) as wav_file:
                    original_channels = wav_file.getnchannels()
                    original_rate = wav_file.getframerate()
                    original_width = wav_file.getsampwidth()
                    frames = wav_file.readframes(wav_file.getnframes())

                metadata["channels"] = original_channels
                metadata["sample_rate"] = original_rate
                metadata["sample_width"] = original_width

                # 确保单声道 16kHz
                if original_channels != 1 or original_rate != 16000 or original_width != 2:
                    import numpy as np

                    if original_width == 2:
                        int_data = np.frombuffer(frames, dtype=np.int16)
                    elif original_width == 4:
                        int_data = np.frombuffer(frames, dtype=np.int32).astype(np.int16)
                    else:
                        int_data = np.frombuffer(frames, dtype=np.int16)

                    if original_channels == 2:
                        int_data = int_data.reshape(-1, 2).mean(axis=1).astype(np.int16)

                    # 重采样
                    if original_rate != 16000:
                        float_data = int_data.astype(np.float32) / 32767.0
                        float_data = resample_audio(float_data, original_rate, 16000)
                        int_data = (float_data * 32767.0).astype(np.int16)

                    # 音频增强处理
                    float_data = int_data.astype(np.float32) / 32767.0
                    float_data = normalize_audio(float_data)
                    start_idx, end_idx = detect_silence(float_data, 16000)
                    float_data = float_data[start_idx:end_idx]
                    
                    try:
                        float_data = spectral_subtraction(float_data, 16000)
                    except Exception as e:
                        logger.debug(f"降噪跳过: {e}")
                    
                    int_data = (float_data * 32767.0).astype(np.int16)

                    with wave.open(file_path, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(16000)
                        wf.writeframes(int_data.tobytes())
                else:
                    # 直接写入并进行增强处理
                    int_data = np.frombuffer(frames, dtype=np.int16)
                    float_data = int_data.astype(np.float32) / 32767.0
                    
                    float_data = normalize_audio(float_data)
                    start_idx, end_idx = detect_silence(float_data, 16000)
                    float_data = float_data[start_idx:end_idx]
                    
                    try:
                        float_data = spectral_subtraction(float_data, 16000)
                    except Exception as e:
                        logger.debug(f"降噪跳过: {e}")
                    
                    int_data = (float_data * 32767.0).astype(np.int16)

                    with wave.open(file_path, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(16000)
                        wf.writeframes(int_data.tobytes())
                
                logger.info("WAV 解析和增强完成")
                return file_path, metadata
                
            except Exception as e:
                logger.warning(f"WAV 解析失败，尝试其他格式: {e}")

        # 尝试使用 soundfile 解析其他音频格式
        try:
            import soundfile as sf

            data, samplerate = sf.read(io.BytesIO(audio_data))

            if data.dtype != np.float32:
                data = data.astype(np.float32)

            if len(data.shape) > 1 and data.shape[1] > 1:
                data = data.mean(axis=1)

            # 重采样
            if samplerate != 16000:
                data = resample_audio(data, samplerate, 16000)
                samplerate = 16000

            # 音频增强
            data = normalize_audio(data)
            start_idx, end_idx = detect_silence(data, samplerate)
            data = data[start_idx:end_idx]
            
            try:
                data = spectral_subtraction(data, samplerate)
            except Exception as e:
                logger.debug(f"降噪跳过: {e}")

            int_data = (data * 32767).astype(np.int16)

            with wave.open(file_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(int_data.tobytes())

            metadata["channels"] = 1
            metadata["sample_rate"] = 16000
            metadata["sample_width"] = 2
            logger.info(f"使用 soundfile 解析成功，采样率: {samplerate}")
            return file_path, metadata

        except Exception as e:
            logger.warning(f"soundfile 解析失败: {e}")

        # 最后尝试：假设是原始 PCM 数据
        try:
            # 尝试作为 PCM 数据处理
            try:
                # 尝试解析为 16 位 PCM
                int_data = np.frombuffer(audio_data, dtype=np.int16)
                float_data = int_data.astype(np.float32) / 32767.0
                
                float_data = normalize_audio(float_data)
                start_idx, end_idx = detect_silence(float_data, 16000)
                float_data = float_data[start_idx:end_idx]
                
                try:
                    float_data = spectral_subtraction(float_data, 16000)
                except Exception as e:
                    logger.debug(f"降噪跳过: {e}")
                
                int_data = (float_data * 32767.0).astype(np.int16)
                processed_audio = int_data.tobytes()
            except Exception as e:
                processed_audio = audio_data
            
            with wave.open(file_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(processed_audio)
            logger.info("使用原始 PCM 格式保存并增强")
            return file_path, metadata
            
        except Exception as e2:
            logger.error(f"PCM 保存也失败: {e2}")
            # 创建空文件
            with wave.open(file_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(b"")
            return file_path, metadata

    async def speech_to_text(
        self, audio_data: bytes, session_id: str, audio_format: str = "wav"
    ) -> Tuple[Optional[str], Optional[str]]:
        """将语音数据转换为文本

        Args:
            audio_data: 音频数据字节
            session_id: 会话 ID
            audio_format: 音频格式提示 (wav, mp3, ogg 等)
        """
        file_path = None

        try:
            if len(audio_data) == 0:
                logger.warning("音频数据为空")
                return "", None

            # 保存音频文件（自动检测格式）
            file_path, metadata = self._save_audio(audio_data, audio_format)
            logger.info(
                f"音频文件已保存: {file_path}, 格式: channels={metadata['channels']}, "
                f"rate={metadata['sample_rate']}, width={metadata['sample_width']}"
            )

            # 使用模型进行识别
            if hasattr(self, "_use_pipeline") and self._use_pipeline:
                # 使用 modelscope pipeline
                result = self.model(file_path)
                text = result.get("text", "") if isinstance(result, dict) else str(result)
            else:
                # 使用 funasr AutoModel
                result = self.model.generate(
                    input=file_path,
                    cache={},
                    language="zh",  # 强制使用中文，解决中英文识别混淆问题
                    use_itn=True,
                    batch_size_s=60,
                    merge_vad=True,
                    merge_length_s=15,
                )
                text = result[0]["text"] if result else ""

            logger.info(f"识别结果: {text}")

            # 清洗识别结果，移除特殊标签
            cleaned_text = clean_asr_output(text)
            if cleaned_text != text:
                logger.info(f"清洗后结果: {cleaned_text}")

            return cleaned_text, file_path

        except Exception as e:
            logger.error(f"语音识别失败: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return "", file_path

        finally:
            # 清理临时文件
            if self.delete_audio_file and file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.debug(f"已删除临时文件: {file_path}")
                except Exception as e:
                    logger.warning(f"删除临时文件失败: {e}")
