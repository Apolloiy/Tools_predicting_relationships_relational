import os
import io
import wave
import uuid
import json
import time
import queue
import asyncio
import traceback
import threading
from abc import ABC, abstractmethod
import logging
from typing import Optional, Tuple, List

TAG = __name__
logger = logging.getLogger(__name__)


class ASRProviderBase(ABC):
    def __init__(self, config: dict = None, delete_audio_file: bool = True):
        self.output_dir = config.get("output_dir", "./audio_output") if config else "./audio_output"
        self.delete_audio_file = delete_audio_file
        os.makedirs(self.output_dir, exist_ok=True)

    def _pcm_to_wav(self, pcm_data: bytes) -> bytes:
        if len(pcm_data) == 0:
            logger.warning("PCM数据为空，无法转换WAV")
            return b""
        
        if len(pcm_data) % 2 != 0:
            pcm_data = pcm_data[:-1]
        
        wav_buffer = io.BytesIO()
        try:
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(pcm_data)
            
            wav_buffer.seek(0)
            wav_data = wav_buffer.read()
            
            return wav_data
        except Exception as e:
            logger.error(f"WAV转换失败: {e}")
            return b""

    def save_audio_to_file(self, pcm_data: List[bytes], session_id: str) -> str:
        module_name = __name__.split(".")[-1]
        file_name = f"asr_{module_name}_{session_id}_{uuid.uuid4()}.wav"
        file_path = os.path.join(self.output_dir, file_name)

        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"".join(pcm_data))

        return file_path

    @abstractmethod
    async def speech_to_text(
        self, audio_data: bytes, session_id: str, audio_format: str = "wav"
    ) -> Tuple[Optional[str], Optional[str]]:
        pass