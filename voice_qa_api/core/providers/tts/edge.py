import os
import uuid
import edge_tts
from datetime import datetime
from .base import TTSProviderBase
from typing import Optional


class TTSProvider(TTSProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__(config, delete_audio_file)
        if config.get("private_voice"):
            self.voice = config.get("private_voice")
        else:
            self.voice = config.get("voice", "zh-CN-XiaoxiaoNeural")
        self.audio_file_type = config.get("format", "mp3")

    def generate_filename(self, extension: str = ".mp3") -> str:
        return os.path.join(
            self.output_file,
            f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}",
        )

    async def text_to_speak(self, text: str, output_file: Optional[str]) -> Optional[bytes]:
        try:
            communicate = edge_tts.Communicate(text, voice=self.voice)
            if output_file:
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                with open(output_file, "wb") as f:
                    pass

                with open(output_file, "ab") as f:
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            f.write(chunk["data"])
            else:
                audio_bytes = b""
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_bytes += chunk["data"]
                return audio_bytes
        except Exception as e:
            error_msg = f"Edge TTS请求失败: {e}"
            raise Exception(error_msg)