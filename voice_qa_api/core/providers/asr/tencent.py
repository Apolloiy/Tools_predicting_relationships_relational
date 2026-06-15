import base64
import hashlib
import hmac
import json
import time
import os
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple, List
from .dto.dto import InterfaceType
import requests
from .base import ASRProviderBase

TAG = __name__
logger = logging.getLogger(__name__)


class ASRProvider(ASRProviderBase):
    API_URL = "https://asr.tencentcloudapi.com"
    API_VERSION = "2019-06-14"
    FORMAT = "pcm"

    def __init__(self, config: dict, delete_audio_file: bool = True):
        super().__init__(config, delete_audio_file)
        self.interface_type = InterfaceType.NON_STREAM
        self.secret_id = config.get("secret_id")
        self.secret_key = config.get("secret_key")

    async def speech_to_text(
        self, audio_data: bytes, session_id: str, audio_format: str = "wav"
    ) -> Tuple[Optional[str], Optional[str]]:
        if not audio_data:
            logger.warning("音频数据为空！")
            return None, None

        file_path = None
        try:
            if not self.secret_id or not self.secret_key:
                logger.error("腾讯云语音识别配置未设置，无法进行识别")
                return None, file_path

            combined_pcm_data = audio_data

            if not self.delete_audio_file:
                self.save_audio_to_file([combined_pcm_data], session_id)

            base64_audio = base64.b64encode(combined_pcm_data).decode("utf-8")

            request_body = self._build_request_body(base64_audio)

            timestamp, authorization = self._get_auth_headers(request_body)

            start_time = time.time()
            result = self._send_request(request_body, timestamp, authorization)

            if result:
                logger.debug(f"腾讯云语音识别耗时: {time.time() - start_time:.3f}s | 结果: {result}")

            return result, file_path

        except Exception as e:
            logger.error(f"处理音频时发生错误！{e}")
            return None, file_path

    def _build_request_body(self, base64_audio: str) -> str:
        request_map = {
            "ProjectId": 0,
            "SubServiceType": 2,
            "EngSerViceType": "16k_zh",
            "SourceType": 1,
            "VoiceFormat": self.FORMAT,
            "Data": base64_audio,
            "DataLen": len(base64_audio),
        }
        return json.dumps(request_map)

    def _get_auth_headers(self, request_body: str) -> Tuple[str, str]:
        try:
            now = datetime.now(timezone.utc)
            timestamp = str(int(now.timestamp()))
            date = now.strftime("%Y-%m-%d")

            service = "asr"

            credential_scope = f"{date}/{service}/tc3_request"
            algorithm = "TC3-HMAC-SHA256"

            http_request_method = "POST"
            canonical_uri = "/"
            canonical_query_string = ""

            content_type = "application/json; charset=utf-8"
            host = "asr.tencentcloudapi.com"
            action = "SentenceRecognition"

            canonical_headers = (
                f"content-type:{content_type.lower()}\n"
                + f"host:{host.lower()}\n"
                + f"x-tc-action:{action.lower()}\n"
            )

            signed_headers = "content-type;host;x-tc-action"

            payload_hash = self._sha256_hex(request_body)

            canonical_request = (
                f"{http_request_method}\n"
                + f"{canonical_uri}\n"
                + f"{canonical_query_string}\n"
                + f"{canonical_headers}\n"
                + f"{signed_headers}\n"
                + f"{payload_hash}"
            )

            hashed_canonical_request = self._sha256_hex(canonical_request)

            string_to_sign = (
                f"{algorithm}\n"
                + f"{timestamp}\n"
                + f"{credential_scope}\n"
                + f"{hashed_canonical_request}"
            )

            secret_date = self._hmac_sha256(f"TC3{self.secret_key}", date)
            secret_service = self._hmac_sha256(secret_date, service)
            secret_signing = self._hmac_sha256(secret_service, "tc3_request")

            signature = self._bytes_to_hex(self._hmac_sha256(secret_signing, string_to_sign))

            authorization = (
                f"{algorithm} "
                + f"Credential={self.secret_id}/{credential_scope}, "
                + f"SignedHeaders={signed_headers}, "
                + f"Signature={signature}"
            )

            return timestamp, authorization

        except Exception as e:
            logger.error(f"生成认证头失败: {e}")
            raise RuntimeError(f"生成认证头失败: {e}")

    def _send_request(
        self, request_body: str, timestamp: str, authorization: str
    ) -> Optional[str]:
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Host": "asr.tencentcloudapi.com",
            "Authorization": authorization,
            "X-TC-Action": "SentenceRecognition",
            "X-TC-Version": self.API_VERSION,
            "X-TC-Timestamp": timestamp,
            "X-TC-Region": "ap-shanghai",
        }

        try:
            response = requests.post(self.API_URL, headers=headers, data=request_body)

            if not response.ok:
                raise IOError(f"请求失败: {response.status_code} {response.reason}")

            response_json = response.json()

            if "Response" in response_json and "Error" in response_json["Response"]:
                error = response_json["Response"]["Error"]
                error_code = error["Code"]
                error_message = error["Message"]
                raise IOError(f"API返回错误: {error_code}: {error_message}")

            if "Response" in response_json and "Result" in response_json["Response"]:
                return response_json["Response"]["Result"]
            else:
                logger.warning(f"响应中没有识别结果: {response_json}")
                return ""

        except Exception as e:
            logger.error(f"发送请求失败: {e}")
            return None

    def _sha256_hex(self, data: str) -> str:
        digest = hashlib.sha256(data.encode("utf-8")).digest()
        return self._bytes_to_hex(digest)

    def _hmac_sha256(self, key, data: str) -> bytes:
        if isinstance(key, str):
            key = key.encode("utf-8")
        return hmac.new(key, data.encode("utf-8"), hashlib.sha256).digest()

    def _bytes_to_hex(self, bytes_data: bytes) -> str:
        return "".join(f"{b:02x}" for b in bytes_data)