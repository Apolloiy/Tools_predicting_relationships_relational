import requests
import logging
from .base import TTSProviderBase

TAG = __name__
logger = logging.getLogger(__name__)


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.api_key = config.get("api_key")
        self.api_url = config.get("api_url", "https://api.openai.com/v1/audio/speech")
        self.model = config.get("model", "tts-1")
        
        if config.get("private_voice"):
            self.voice = config.get("private_voice")
        else:
            self.voice = config.get("voice", "alloy")
        
        self.response_format = config.get("format", "wav")
        self.audio_file_type = config.get("format", "wav")

        speed = config.get("speed", "1.0")
        self.speed = float(speed) if speed else 1.0

    async def text_to_speak(self, text, output_file):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = {
            "model": self.model,
            "input": text,
            "voice": self.voice,
            "response_format": "wav",
            "speed": self.speed,
        }
        response = requests.post(self.api_url, json=data, headers=headers)
        if response.status_code == 200:
            if output_file:
                with open(output_file, "wb") as audio_file:
                    audio_file.write(response.content)
            else:
                return response.content
        else:
            raise Exception(
                f"OpenAI TTS请求失败: {response.status_code} - {response.text}"
            )