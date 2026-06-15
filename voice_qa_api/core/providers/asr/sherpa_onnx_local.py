import time
import wave
import os
import sys
import io
import logging
from typing import Optional, Tuple, List
from .dto.dto import InterfaceType
from .base import ASRProviderBase

import numpy as np
import sherpa_onnx

from modelscope.hub.file_download import model_file_download

TAG = __name__
logger = logging.getLogger(__name__)


class CaptureOutput:
    def __enter__(self):
        self._output = io.StringIO()
        self._original_stdout = sys.stdout
        sys.stdout = self._output

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout = self._original_stdout
        self.output = self._output.getvalue()
        self._output.close()

        if self.output:
            logger.info(self.output.strip())


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__(config, delete_audio_file)
        self.interface_type = InterfaceType.LOCAL
        self.model_dir = config.get("model_dir")
        self.model_type = config.get("model_type", "sense_voice")

        model_files = {
            "model.int8.onnx": os.path.join(self.model_dir, "model.int8.onnx"),
            "tokens.txt": os.path.join(self.model_dir, "tokens.txt"),
        }

        try:
            for file_name, file_path in model_files.items():
                if not os.path.isfile(file_path):
                    logger.info(f"正在下载模型文件: {file_name}")
                    model_file_download(
                        model_id="pengzhendong/sherpa-onnx-sense-voice-zh-en-ja-ko-yue",
                        file_path=file_name,
                        local_dir=self.model_dir,
                    )

                    if not os.path.isfile(file_path):
                        raise FileNotFoundError(f"模型文件下载失败: {file_path}")

            self.model_path = model_files["model.int8.onnx"]
            self.tokens_path = model_files["tokens.txt"]

        except Exception as e:
            logger.error(f"模型文件处理失败: {str(e)}")
            raise

        with CaptureOutput():
            if self.model_type == "paraformer":
                self.model = sherpa_onnx.OfflineRecognizer.from_paraformer(
                    paraformer=self.model_path,
                    tokens=self.tokens_path,
                    num_threads=2,
                    sample_rate=16000,
                    feature_dim=80,
                    decoding_method="greedy_search",
                    debug=False,
                )
            else:
                self.model = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                    model=self.model_path,
                    tokens=self.tokens_path,
                    num_threads=2,
                    sample_rate=16000,
                    feature_dim=80,
                    decoding_method="greedy_search",
                    debug=False,
                    use_itn=True,
                )

    def read_wave(self, wave_filename: str) -> Tuple[np.ndarray, int]:
        with wave.open(wave_filename) as f:
            assert f.getnchannels() == 1, f.getnchannels()
            assert f.getsampwidth() == 2, f.getsampwidth()
            num_samples = f.getnframes()
            samples = f.readframes(num_samples)
            samples_int16 = np.frombuffer(samples, dtype=np.int16)
            samples_float32 = samples_int16.astype(np.float32)
            samples_float32 = samples_float32 / 32768
            return samples_float32, f.getframerate()

    async def speech_to_text(
        self, audio_data: bytes, session_id: str, audio_format: str = "wav"
    ) -> Tuple[Optional[str], Optional[str]]:
        file_path = None
        try:
            start_time = time.time()
            file_path = self.save_audio_to_file([audio_data], session_id)
            logger.debug(f"音频文件保存耗时: {time.time() - start_time:.3f}s | 路径: {file_path}")

            start_time = time.time()
            s = self.model.create_stream()
            samples, sample_rate = self.read_wave(file_path)
            s.accept_waveform(sample_rate, samples)
            self.model.decode_stream(s)
            text = s.result.text
            logger.debug(f"语音识别耗时: {time.time() - start_time:.3f}s | 结果: {text}")

            return text, file_path

        except Exception as e:
            logger.error(f"语音识别失败: {e}")
            return "", file_path
        finally:
            if self.delete_audio_file and file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.debug(f"已删除临时音频文件: {file_path}")
                except Exception as e:
                    logger.error(f"文件删除失败: {file_path} | 错误: {e}")