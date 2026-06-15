import os
import tempfile
from typing import Optional, Tuple, List
import dashscope
import logging
from .base import ASRProviderBase
from .dto.dto import InterfaceType

tag = __name__
logger = logging.getLogger(__name__)


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__(config, delete_audio_file)
        self.interface_type = InterfaceType.NON_STREAM
        
        self.api_key = config.get("api_key")
        if not self.api_key:
            raise ValueError("Qwen3-ASR-Flash 需要配置 api_key")
            
        self.model_name = config.get("model_name", "qwen3-asr-flash")
        
        self.enable_lid = config.get("enable_lid", True)
        self.enable_itn = config.get("enable_itn", True)
        self.language = config.get("language", None)
        self.context = config.get("context", "")

    def _prepare_audio_file(self, pcm_data: bytes) -> str:
        try:
            import wave
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
                
            with wave.open(temp_path, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(pcm_data)
                
            return temp_path
            
        except Exception as e:
            logger.error(f"音频文件准备失败: {e}")
            return None

    async def speech_to_text(
        self, audio_data: bytes, session_id: str, audio_format: str = "wav"
    ) -> Tuple[Optional[str], Optional[str]]:
        temp_file_path = None
        file_path = None
        
        try:
            combined_pcm_data = audio_data
            if len(combined_pcm_data) == 0:
                logger.warning("音频数据为空")
                return "", None
            
            if audio_format != "pcm":
                try:
                    import wave
                    import io
                    with wave.open(io.BytesIO(audio_data), 'rb') as wav_file:
                        combined_pcm_data = wav_file.readframes(wav_file.getnframes())
                except Exception as e:
                    logger.warning(f"无法解析音频格式，尝试作为PCM处理: {e}")
            
            temp_file_path = self._prepare_audio_file(combined_pcm_data)
            if not temp_file_path:
                return "", None
            
            if not self.delete_audio_file:
                file_path = self.save_audio_to_file([combined_pcm_data], session_id)
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"audio": temp_file_path}
                    ]
                }
            ]
            
            if self.context:
                messages.insert(0, {
                    "role": "system", 
                    "content": [
                        {"text": self.context}
                    ]
                })
            
            asr_options = {
                "enable_lid": self.enable_lid,
                "enable_itn": self.enable_itn
            }
            
            if self.language:
                asr_options["language"] = self.language
            
            dashscope.api_key = self.api_key
            
            response = dashscope.MultiModalConversation.call(
                model=self.model_name,
                messages=messages,
                result_format="message",
                asr_options=asr_options,
                stream=True
            )
            
            full_text = ""
            for chunk in response:
                try:
                    text = chunk["output"]["choices"][0]["message"].content[0]["text"]
                    full_text = text.strip()
                except:
                    pass
            
            return full_text, file_path
                
        except Exception as e:
            logger.error(f"语音识别失败: {e}")
            return "", file_path
            
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    logger.warning(f"清理临时文件失败: {e}")