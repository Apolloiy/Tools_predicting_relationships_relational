import time
import os
import logging
from typing import Optional, Tuple, List
from .dto.dto import InterfaceType
from .base import ASRProviderBase
import requests

TAG = __name__
logger = logging.getLogger(__name__)


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__(config, delete_audio_file)
        self.interface_type = InterfaceType.NON_STREAM
        self.api_key = config.get("api_key")
        self.api_url = config.get("base_url")
        self.model = config.get("model_name")

    async def speech_to_text(
        self, audio_data: bytes, session_id: str, audio_format: str = "wav"
    ) -> Tuple[Optional[str], Optional[str]]:
        file_path = None
        try:
            start_time = time.time()
            file_path = self.save_audio_to_file([audio_data], session_id)

            logger.debug(f"音频文件保存耗时: {time.time() - start_time:.3f}s | 路径: {file_path}")

            headers = {
                "Authorization": f"Bearer {self.api_key}",
            }

            data = {
                "model": self.model
            }

            with open(file_path, "rb") as audio_file:
                files = {
                    "file": audio_file
                }

                start_time = time.time()
                response = requests.post(
                    self.api_url,
                    files=files,
                    data=data,
                    headers=headers
                )
                logger.debug(f"语音识别耗时: {time.time() - start_time:.3f}s | 结果: {response.text}")

            if response.status_code == 200:
                text = response.json().get("text", "")
                return text, file_path
            else:
                raise Exception(f"API请求失败: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"语音识别失败: {e}")
            return "", None
        finally:
            if self.delete_audio_file and file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.debug(f"已删除临时音频文件: {file_path}")
                except Exception as e:
                    logger.error(f"文件删除失败: {file_path} | 错误: {e}")