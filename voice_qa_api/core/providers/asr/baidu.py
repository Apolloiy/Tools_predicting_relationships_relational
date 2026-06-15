import time
import os
import logging
from typing import Optional, Tuple, List
from aip import AipSpeech
from .base import ASRProviderBase
from .dto.dto import InterfaceType

TAG = __name__
logger = logging.getLogger(__name__)


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool = True):
        super().__init__(config, delete_audio_file)
        self.interface_type = InterfaceType.NON_STREAM
        self.app_id = config.get("app_id")
        self.api_key = config.get("api_key")
        self.secret_key = config.get("secret_key")

        dev_pid = config.get("dev_pid", "1537")
        self.dev_pid = int(dev_pid) if dev_pid else 1537

        self.client = AipSpeech(str(self.app_id), self.api_key, self.secret_key)

    async def speech_to_text(
        self, audio_data: bytes, session_id: str, audio_format: str = "wav"
    ) -> Tuple[Optional[str], Optional[str]]:
        if not audio_data:
            logger.warning("音频数据为空！")
            return None, None

        file_path = None
        try:
            if not self.app_id or not self.api_key or not self.secret_key:
                logger.error("百度语音识别配置未设置，无法进行识别")
                return None, file_path

            combined_pcm_data = audio_data

            if not self.delete_audio_file:
                self.save_audio_to_file([combined_pcm_data], session_id)

            start_time = time.time()
            result = self.client.asr(
                combined_pcm_data,
                "pcm",
                16000,
                {
                    "dev_pid": str(self.dev_pid),
                },
            )

            if result and result["err_no"] == 0:
                logger.debug(f"百度语音识别耗时: {time.time() - start_time:.3f}s | 结果: {result}")
                result = result["result"][0]
                return result, file_path
            else:
                raise Exception(f"百度语音识别失败，错误码: {result['err_no']}，错误信息: {result['err_msg']}")

        except Exception as e:
            logger.error(f"处理音频时发生错误！{e}")
            return None, file_path