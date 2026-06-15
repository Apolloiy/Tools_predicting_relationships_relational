# Chatbot.py - 整合语音功能 + AI CRM 系统
import os
import sys
import asyncio
import logging
import warnings

# 设置环境变量 - 使用 ModelScope 镜像加速下载
os.environ['HF_ENDPOINT'] = 'https://modelscope.cn'
os.environ['HUGGINGFACE_HUB_DISABLE_PROGRESS_BARS'] = '1'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

warnings.filterwarnings("ignore")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加 AI CRM 到路径
ai_crm_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AI CRM")
if ai_crm_path not in sys.path:
    sys.path.insert(0, ai_crm_path)

# 添加 voice_qa_api 到路径
voice_api_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice_qa_api")
if voice_api_path not in sys.path:
    sys.path.insert(0, voice_api_path)

# 从 config.yaml 加载配置
import yaml
from dotenv import load_dotenv

# 加载 .env
load_dotenv()

# 加载 config.yaml
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
app_config = {}
if os.path.exists(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        app_config = yaml.safe_load(f)
    print("[Chatbot] 从 config.yaml 加载配置")


class STTService:
    """语音转文字服务 - 使用 SenseVoice"""

    def __init__(self):
        self.provider = None
        self._initialize()

    def _initialize(self):
        """初始化 ASR 服务"""
        try:
            from core.providers.asr.sensevoice import ASRProvider

            # 从配置读取路径
            asr_config = app_config.get('asr', {})
            model_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                asr_config.get('model_dir', 'voice_qa_api/models/SenseVoiceSmall')
            )
            output_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                asr_config.get('output_dir', 'tmp/')
            )

            config = {
                "model_dir": model_dir,
                "output_dir": output_dir
            }
            self.provider = ASRProvider(config, delete_audio_file=True)
            logger.info("STT 服务初始化成功 (SenseVoice)")
        except Exception as e:
            logger.warning(f"STT 服务初始化失败: {e}，语音功能将不可用")

    def transcribe(self, audio_path: str) -> str:
        """将音频文件转换为文字"""
        if not self.provider:
            logger.warning("STT 服务未初始化")
            return ""

        if not audio_path or not os.path.exists(audio_path):
            logger.warning(f"音频文件不存在: {audio_path}")
            return ""

        try:
            with open(audio_path, "rb") as f:
                audio_data = f.read()

            # 异步调用
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            self.provider.speech_to_text(audio_data, "default_session", "wav")
                        )
                        result, _ = future.result(timeout=60)
                        return result or ""
                else:
                    result, _ = loop.run_until_complete(
                        self.provider.speech_to_text(audio_data, "default_session", "wav")
                    )
                    return result or ""
            except RuntimeError:
                result, _ = asyncio.run(
                    self.provider.speech_to_text(audio_data, "default_session", "wav")
                )
                return result or ""
        except Exception as e:
            logger.error(f"语音识别失败: {e}")
            return ""


class TTSService:
    """文字转语音服务 - 使用 EdgeTTS"""

    def __init__(self):
        self.provider = None
        self._initialize()

    def _initialize(self):
        """初始化 TTS 服务"""
        try:
            from core.providers.tts.edge import TTSProvider

            # 从配置读取
            tts_config = app_config.get('tts', {})
            voice = tts_config.get('voice', 'zh-CN-XiaoxiaoNeural')
            output_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                tts_config.get('output_dir', 'tmp/')
            )

            config = {
                "voice": voice,
                "output_dir": output_dir
            }
            self.provider = TTSProvider(config, delete_audio_file=False)
            logger.info("TTS 服务初始化成功 (EdgeTTS)")
        except Exception as e:
            logger.warning(f"TTS 服务初始化失败: {e}，语音输出将不可用")

    def synthesize(self, text: str) -> str:
        """将文字转换为语音文件，返回文件路径"""
        if not self.provider or not text:
            return None

        try:
            output_file = self.provider.generate_filename(".mp3")

            # 异步调用
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            self.provider.text_to_speak(text, output_file)
                        )
                        future.result(timeout=30)
                else:
                    loop.run_until_complete(
                        self.provider.text_to_speak(text, output_file)
                    )
            except RuntimeError:
                asyncio.run(self.provider.text_to_speak(text, output_file))

            return output_file if os.path.exists(output_file) else None
        except Exception as e:
            logger.error(f"语音合成失败: {e}")
            return None


class CRMVoiceAgent:
    """整合语音功能的 CRM 智能助手"""

    def __init__(self):
        self.stt = STTService()
        self.tts = TTSService()
        self.crm_agent = None
        self.phone_number = "default_user"
        self._initialize_crm()

    def _initialize_crm(self):
        """初始化 CRM Agent"""
        try:
            # 导入 AI CRM 模块
            from agent import SeaChatAgent, try_load_rag_engine

            # 尝试加载 RAG 知识库
            rag_engine = try_load_rag_engine()

            # 初始化 CRM Agent
            self.crm_agent = SeaChatAgent(rag_engine=rag_engine)
            logger.info("CRM Agent 初始化成功")
        except Exception as e:
            logger.error(f"CRM Agent 初始化失败: {e}")
            self.crm_agent = None

    def set_phone_number(self, phone_number: str):
        """设置用户手机号"""
        self.phone_number = phone_number

    def _process_query(self, query: str) -> tuple:
        """处理用户查询"""
        if not self.crm_agent:
            return "CRM 系统未初始化，请检查配置", "系统错误"

        try:
            response = self.crm_agent.run(self.phone_number, query)
            return response, "处理完成"
        except Exception as e:
            logger.error(f"处理查询失败: {e}")
            return f"处理请求时发生错误: {str(e)}", "处理失败"

    def get_all_customers(self):
        """获取所有客户数据"""
        if self.crm_agent and self.crm_agent.memory_manager:
            return self.crm_agent.memory_manager.get_all_customers()
        return []


class ChatController:
    """Gradio 控制器"""

    def __init__(self):
        self.agent = CRMVoiceAgent()
        self.phone_number = "default_user"

    def set_phone_number(self, phone_number: str):
        """设置用户手机号"""
        self.phone_number = phone_number
        self.agent.set_phone_number(phone_number)

    def handle_interaction(self, *args):
        """
        统一处理交互 - 支持两种调用方式：
        1. submit_btn: handle_interaction(audio_input, chat_history) -> [chatbot, status, audio_output]
        2. text_input: handle_interaction(audio_input, text_input, chat_history) -> [chatbot, status, text_input, audio_output]
        """
        # 区分调用方式
        if len(args) == 2:
            # submit_btn 调用: [audio_input, chat_history]
            audio_input, chat_history = args
            text_input = None
            has_text_output = False
        elif len(args) == 3:
            # text_input.submit 调用: [audio_input, text_input, chat_history]
            audio_input, text_input, chat_history = args
            has_text_output = True
        else:
            return [], "参数错误", "", None if has_text_output else None

        # 确保 chat_history 是正确的格式
        if chat_history is None:
            chat_history = []

        audio_output = None

        # 优先使用文本输入
        if text_input and text_input.strip():
            user_text = text_input.strip()
            response_text, status = self.agent._process_query(user_text)
            
            # 使用 Gradio messages 格式
            new_history = chat_history + [
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": response_text}
            ]

            # 生成语音回复
            audio_output = self.agent.tts.synthesize(response_text)
            
            if has_text_output:
                return new_history, status, "", audio_output
            else:
                return new_history, status, audio_output

        # 否则使用语音输入
        if audio_input is None:
            if has_text_output:
                return chat_history, "未检测到音频输入", "", None
            else:
                return chat_history, "未检测到音频输入", None

        # 语音转文字
        user_text = self.agent.stt.transcribe(audio_input)
        if not user_text:
            if has_text_output:
                return chat_history, "语音识别失败，请重试", "", None
            else:
                return chat_history, "语音识别失败，请重试", None

        # 处理请求
        response_text, status = self.agent._process_query(user_text)

        # 更新聊天历史 - 使用 Gradio messages 格式
        new_history = chat_history + [
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": response_text}
        ]

        # 生成语音回复
        audio_output = self.agent.tts.synthesize(response_text)

        if has_text_output:
            return new_history, status, "", audio_output
        else:
            return new_history, status, audio_output

    def get_customer_list(self):
        """获取客户列表"""
        customers = self.agent.get_all_customers()
        if not customers:
            return "暂无客户数据"

        result = "📋 CRM 客户列表:\n\n"
        for customer in customers:
            result += f"• {customer.get('name', '未知')} (ID: {customer.get('user_id')})\n"
            result += f"  电话: {customer.get('phone_number', '无')}\n"
            result += f"  状态: {customer.get('status', '无')} | 等级: {customer.get('level', '无')}\n"
            result += f"  余额: {customer.get('balance', 0.0)}\n\n"
        return result


def main():
    """主入口 - 启动 Gradio UI"""
    from GradioUI import create_ui

    print("=" * 60)
    print("AI CRM Voice Assistant Starting...")
    print("=" * 60)

    # 初始化控制器
    controller = ChatController()

    # 创建 UI 并启动（自动查找可用端口）
    ui = create_ui(controller)
    ui.launch(
        server_name="0.0.0.0",
        server_port=None,
        share=False,
        show_error=True
    )


if __name__ == "__main__":
    main()