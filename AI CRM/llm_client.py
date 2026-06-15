# core/llm_client.py
import os
import sys
import re
import logging
from openai import OpenAI
from dotenv import load_dotenv

# 从主目录加载 .env 配置
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
main_dir = os.path.dirname(parent_dir)  # chatbot-1 目录

env_file = os.path.join(main_dir, ".env")
yaml_file = os.path.join(main_dir, "config.yaml")

# 先加载 .env
if os.path.exists(env_file):
    load_dotenv(env_file, override=True)
    logging.info(f"[llm_client] 从 .env 加载配置: {env_file}")
else:
    load_dotenv()

# 再加载 config.yaml 并覆盖环境变量
import yaml
if os.path.exists(yaml_file):
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            yaml_config = yaml.safe_load(f)
        # 覆盖环境变量
        if 'llm' in yaml_config:
            llm_config = yaml_config['llm']
            if 'model' in llm_config:
                os.environ['model'] = llm_config['model']
                logging.info(f"[llm_client] 从 config.yaml 覆盖 model: {llm_config['model']}")
            if 'base_url' in llm_config:
                os.environ['aliyun_url'] = llm_config['base_url']
            if 'api_key' in llm_config:
                os.environ['aliyun_key'] = llm_config['api_key']
    except Exception as e:
        logging.error(f"[llm_client] 加载 config.yaml 失败: {e}")

logger = logging.getLogger(__name__)


class AI_CRM_LLM:
    """统一使用阿里云 LLM（与主配置一致）"""

    def __init__(self, api_key=None, model=None):
        # 使用统一的阿里云配置
        self.api_key = api_key or os.getenv("aliyun_key")
        self.url = os.getenv("aliyun_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        # 优先使用传入的 model 参数，然后是环境变量，最后是默认值
        self.model = model or os.getenv("model", "qwen3-max")

        # 验证 API Key
        if not self.api_key or self.api_key == "your_api_key_here":
            logger.warning("API Key 未配置或使用默认值，将进入模拟模式")
            self.use_mock = True
        else:
            self.use_mock = False
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.url
            )

        logger.info(f"LLM 初始化成功: model={self.model}, mock_mode={self.use_mock}")

    def _validate_messages(self, messages):
        """验证并清理 messages 格式"""
        validated = []
        for msg in messages:
            if isinstance(msg, dict):
                if 'role' not in msg or 'content' not in msg:
                    continue
                # 确保 content 是字符串
                if not isinstance(msg['content'], str):
                    msg['content'] = str(msg['content'])
                validated.append(msg)
        return validated

    def chat(self, messages, temperature=0.7, model=None):
        """通用的聊天接口调用"""
        model_name = model or self.model

        # 如果是模拟模式，返回模拟响应
        if self.use_mock:
            return self._get_mock_response(messages)

        try:
            # 验证消息格式
            messages = self._validate_messages(messages)

            if not messages:
                return "消息格式错误，无法处理"

            logger.info(f"正在调用 LLM API... model: {model_name}, url: {self.url}")

            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature
            )

            content = response.choices[0].message.content
            content = self._clean_think_tags(content)
            logger.info("LLM API 调用成功")
            return content

        except Exception as e:
            logger.error(f"LLM API 请求异常: {e}")
            logger.error(f"API Key 前10位: {self.api_key[:10]}...")
            logger.error(f"模型: {model_name}, URL: {self.url}")
            # 返回模拟响应作为降级方案
            return self._get_mock_response(messages)

    def _get_mock_response(self, messages):
        """获取模拟响应（当 API 不可用时使用）"""
        try:
            # 获取最后一条用户消息
            user_message = ""
            for msg in reversed(messages):
                if isinstance(msg, dict) and msg.get('role') == 'user':
                    user_message = msg.get('content', '')
                    break

            # 基于用户消息类型返回不同的模拟响应
            if '查询' in user_message or '客户' in user_message or 'CRM' in user_message:
                return "抱歉，数据库查询功能需要真实的 LLM API 支持。您可以查询以下示例客户：\n\n• 张三 (VIP客户, 余额: 10000)\n• 李四 (普通客户, 余额: 5000)\n• 王五 (VIP客户, 余额: 20000)"
            elif '天气' in user_message:
                return "抱歉，天气查询功能需要真实的 LLM API 支持。"
            elif '修改' in user_message or '更新' in user_message:
                return "抱歉，修改数据库功能需要真实的 LLM API 支持。"
            else:
                return f"这是模拟响应。您的消息：{user_message[:50]}...\n\n提示：请配置有效的阿里云 API Key 以使用完整功能。"
        except Exception as e:
            logger.error(f"模拟响应生成失败: {e}")
            return "抱歉，AI 服务暂时不可用，请稍后再试。"

    def _clean_think_tags(self, text):
        """清理模型输出中的思考标签"""
        if not text:
            return text
        # 移除 <think>...</think> 标签和内容
        text = re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.IGNORECASE)
        # 清理多余的空白
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()
        return text