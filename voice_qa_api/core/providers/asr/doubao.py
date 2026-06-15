import time
import os
import uuid
import json
import gzip
import websockets
import logging
from typing import Optional, Tuple, List
from .base import ASRProviderBase
from .dto.dto import InterfaceType

TAG = __name__
logger = logging.getLogger(__name__)

CLIENT_FULL_REQUEST = 0b0001
CLIENT_AUDIO_ONLY_REQUEST = 0b0010

NO_SEQUENCE = 0b0000
NEG_SEQUENCE = 0b0010

SERVER_FULL_RESPONSE = 0b1001
SERVER_ACK = 0b1011
SERVER_ERROR_RESPONSE = 0b1111

NO_SERIALIZATION = 0b0000
JSON = 0b0001
THRIFT = 0b0011
CUSTOM_TYPE = 0b1111
NO_COMPRESSION = 0b0000
GZIP = 0b0001
CUSTOM_COMPRESSION = 0b1111


def parse_response(res):
    protocol_version = res[0] >> 4
    header_size = res[0] & 0x0F
    message_type = res[1] >> 4
    message_type_specific_flags = res[1] & 0x0F
    serialization_method = res[2] >> 4
    message_compression = res[2] & 0x0F
    reserved = res[3]
    header_extensions = res[4 : header_size * 4]
    payload = res[header_size * 4 :]
    result = {}
    payload_msg = None
    payload_size = 0
    if message_type == SERVER_FULL_RESPONSE:
        payload_size = int.from_bytes(payload[:4], "big", signed=True)
        payload_msg = payload[4:]
    elif message_type == SERVER_ACK:
        seq = int.from_bytes(payload[:4], "big", signed=True)
        result["seq"] = seq
        if len(payload) >= 8:
            payload_size = int.from_bytes(payload[4:8], "big", signed=False)
            payload_msg = payload[8:]
    elif message_type == SERVER_ERROR_RESPONSE:
        code = int.from_bytes(payload[:4], "big", signed=False)
        result["code"] = code
        payload_size = int.from_bytes(payload[4:8], "big", signed=False)
        payload_msg = payload[8:]
    if payload_msg is None:
        return result
    if message_compression == GZIP:
        payload_msg = gzip.decompress(payload_msg)
    if serialization_method == JSON:
        payload_msg = json.loads(str(payload_msg, "utf-8"))
    elif serialization_method != NO_SERIALIZATION:
        payload_msg = str(payload_msg, "utf-8")
    result["payload_msg"] = payload_msg
    result["payload_size"] = payload_size
    return result


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__(config, delete_audio_file)
        self.interface_type = InterfaceType.NON_STREAM
        self.appid = config.get("appid")
        self.cluster = config.get("cluster")
        self.access_token = config.get("access_token")
        self.boosting_table_name = config.get("boosting_table_name", "")
        self.correct_table_name = config.get("correct_table_name", "")

        self.host = "openspeech.bytedance.com"
        self.ws_url = f"wss://{self.host}/api/v2/asr"
        self.success_code = 1000
        self.seg_duration = 15000

    @staticmethod
    def _generate_header(
        message_type=CLIENT_FULL_REQUEST, message_type_specific_flags=NO_SEQUENCE
    ) -> bytearray:
        header = bytearray()
        header_size = 1
        header.append((0b0001 << 4) | header_size)
        header.append((message_type << 4) | message_type_specific_flags)
        header.append((0b0001 << 4) | 0b0001)
        header.append(0x00)
        return header

    def _construct_request(self, reqid) -> dict:
        return {
            "app": {
                "appid": f"{self.appid}",
                "cluster": self.cluster,
                "token": self.access_token,
            },
            "user": {
                "uid": str(uuid.uuid4()),
            },
            "request": {
                "reqid": reqid,
                "show_utterances": False,
                "sequence": 1,
                "boosting_table_name": self.boosting_table_name,
                "correct_table_name": self.correct_table_name,
            },
            "audio": {
                "format": "raw",
                "rate": 16000,
                "language": "zh-CN",
                "bits": 16,
                "channel": 1,
                "codec": "raw",
            },
        }

    async def _send_request(
        self, audio_data: bytes, segment_size: int
    ) -> Optional[str]:
        try:
            auth_header = {"Authorization": "Bearer; {}".format(self.access_token)}
            async with websockets.connect(
                self.ws_url, additional_headers=auth_header
            ) as websocket:
                request_params = self._construct_request(str(uuid.uuid4()))
                payload_bytes = str.encode(json.dumps(request_params))
                payload_bytes = gzip.compress(payload_bytes)
                full_client_request = self._generate_header()
                full_client_request.extend((len(payload_bytes)).to_bytes(4, "big"))
                full_client_request.extend(payload_bytes)

                await websocket.send(full_client_request)
                res = await websocket.recv()
                result = parse_response(res)
                if (
                    "payload_msg" in result
                    and result["payload_msg"]["code"] != self.success_code
                    and result["payload_msg"]["code"] != 1013
                ):
                    logger.error(f"ASR error: {result}")
                    return None

                for seq, (chunk, last) in enumerate(
                    self.slice_data(audio_data, segment_size), 1
                ):
                    if last:
                        audio_only_request = self._generate_header(
                            message_type=CLIENT_AUDIO_ONLY_REQUEST,
                            message_type_specific_flags=NEG_SEQUENCE,
                        )
                    else:
                        audio_only_request = self._generate_header(
                            message_type=CLIENT_AUDIO_ONLY_REQUEST
                        )
                    payload_bytes = gzip.compress(chunk)
                    audio_only_request.extend((len(payload_bytes)).to_bytes(4, "big"))
                    audio_only_request.extend(payload_bytes)
                    await websocket.send(audio_only_request)

                response = await websocket.recv()
                result = parse_response(response)

                if (
                    "payload_msg" in result
                    and result["payload_msg"]["code"] == self.success_code
                ):
                    if len(result["payload_msg"]["result"]) > 0:
                        return result["payload_msg"]["result"][0]["text"]
                    return None
                elif "payload_msg" in result and result["payload_msg"]["code"] == 1013:
                    return ""
                else:
                    logger.error(f"ASR error: {result}")
                    return None

        except Exception as e:
            logger.error(f"ASR request failed: {e}")
            return None

    @staticmethod
    def slice_data(data: bytes, chunk_size: int) -> (list, bool):
        data_len = len(data)
        offset = 0
        while offset + chunk_size < data_len:
            yield data[offset : offset + chunk_size], False
            offset += chunk_size
        else:
            yield data[offset:data_len], True

    async def speech_to_text(
        self, audio_data: bytes, session_id: str, audio_format: str = "wav"
    ) -> Tuple[Optional[str], Optional[str]]:
        file_path = None
        try:
            combined_pcm_data = audio_data

            if not self.delete_audio_file:
                file_path = self.save_audio_to_file([combined_pcm_data], session_id)

            size_per_sec = 1 * 2 * 16000
            segment_size = int(size_per_sec * self.seg_duration / 1000)

            start_time = time.time()
            text = await self._send_request(combined_pcm_data, segment_size)
            if text:
                logger.debug(f"语音识别耗时: {time.time() - start_time:.3f}s | 结果: {text}")
                return text, file_path
            return "", file_path

        except Exception as e:
            logger.error(f"语音识别失败: {e}")
            return "", file_path