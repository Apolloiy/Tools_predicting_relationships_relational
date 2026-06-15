import os
import json
import time
import logging
from typing import Optional, Tuple, List
from .base import ASRProviderBase
from .dto.dto import InterfaceType
import vosk

TAG = __name__
logger = logging.getLogger(__name__)


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool = True):
        super().__init__(config, delete_audio_file)
        self.interface_type = InterfaceType.LOCAL
        self.model_path = config.get("model_path")

        self.model = None
        self.recognizer = None
        self._load_model()

    def _load_model(self):
        try:
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"VOSK模型路径不存在: {self.model_path}")

            logger.info(f"正在加载VOSK模型: {self.model_path}")
            self.model = vosk.Model(self.model_path)
            self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
            logger.info("VOSK模型加载成功")
        except Exception as e:
            logger.error(f"加载VOSK模型失败: {e}")
            raise

    async def speech_to_text(
        self, audio_data: bytes, session_id: str, audio_format: str = "wav"
    ) -> Tuple[Optional[str], Optional[str]]:
        file_path = None
        try:
            if not self.model:
                logger.error("VOSK模型未加载，无法进行识别")
                return "", None

            combined_pcm_data = audio_data
            if len(combined_pcm_data) == 0:
                logger.warning("PCM数据为空")
                return "", None

            if not self.delete_audio_file:
                file_path = self.save_audio_to_file([combined_pcm_data], session_id)

            start_time = time.time()

            chunk_size = 2000
            text_result = ""

            for i in range(0, len(combined_pcm_data), chunk_size):
                chunk = combined_pcm_data[i:i+chunk_size]
                if self.recognizer.AcceptWaveform(chunk):
                    result = json.loads(self.recognizer.Result())
                    text = result.get('text', '')
                    if text:
                        text_result += text + " "

            final_result = json.loads(self.recognizer.FinalResult())
            final_text = final_result.get('text', '')
            if final_text:
                text_result += final_text

            logger.debug(f"VOSK语音识别耗时: {time.time() - start_time:.3f}s | 结果: {text_result.strip()}")

            return text_result.strip(), file_path

        except Exception as e:
            logger.error(f"VOSK语音识别失败: {e}")
            return "", None
        finally:
            if self.delete_audio_file and file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.debug(f"已删除临时音频文件: {file_path}")
                except Exception as e:
                    logger.error(f"文件删除失败: {file_path} | 错误: {e}")