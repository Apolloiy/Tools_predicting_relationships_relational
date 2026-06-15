import os
import re
import time
import uuid
from datetime import datetime
from typing import Callable, Any, Optional
from abc import ABC, abstractmethod
import logging
from .dto.dto import (
    TTSMessageDTO,
    SentenceType,
    ContentType,
    InterfaceType,
)

TAG = __name__
logger = logging.getLogger(__name__)


class TTSProviderBase(ABC):
    def __init__(self, config: dict = None, delete_audio_file: bool = True):
        self.interface_type = InterfaceType.NON_STREAM
        self.delete_audio_file = delete_audio_file
        self.audio_file_type = "wav"
        self.output_file = config.get("output_dir", "tmp/") if config else "tmp/"
        os.makedirs(self.output_file, exist_ok=True)

    def generate_filename(self, extension: str = ".wav") -> str:
        return os.path.join(
            self.output_file,
            f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}",
        )

    @abstractmethod
    async def text_to_speak(self, text: str, output_file: Optional[str]) -> Optional[bytes]:
        pass

    async def to_tts(self, text: str) -> Optional[Any]:
        max_repeat_time = 5
        if self.delete_audio_file:
            while max_repeat_time > 0:
                try:
                    audio_bytes = await self.text_to_speak(text, None)
                    if audio_bytes:
                        return audio_bytes
                    else:
                        max_repeat_time -= 1
                except Exception as e:
                    logger.warning(f"语音生成失败{5 - max_repeat_time + 1}次: {text}，错误: {e}")
                    max_repeat_time -= 1
            if max_repeat_time > 0:
                logger.info(f"语音生成成功: {text}，重试{5 - max_repeat_time}次")
            else:
                logger.error(f"语音生成失败: {text}，请检查网络或服务是否正常")
            return None
        else:
            tmp_file = self.generate_filename()
            try:
                while not os.path.exists(tmp_file) and max_repeat_time > 0:
                    try:
                        await self.text_to_speak(text, tmp_file)
                    except Exception as e:
                        logger.warning(f"语音生成失败{5 - max_repeat_time + 1}次: {text}，错误: {e}")
                        if os.path.exists(tmp_file):
                            os.remove(tmp_file)
                        max_repeat_time -= 1

                if max_repeat_time > 0:
                    logger.info(f"语音生成成功: {text}:{tmp_file}，重试{5 - max_repeat_time}次")
                else:
                    logger.error(f"语音生成失败: {text}，请检查网络或服务是否正常")

                return tmp_file
            except Exception as e:
                logger.error(f"Failed to generate TTS file: {e}")
                return None