import sys
import os

# 设置环境变量
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HUGGINGFACE_HUB_DISABLE_PROGRESS_BARS'] = '1'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

import warnings
warnings.filterwarnings("ignore")

import json
import logging

from config import Config
from llm_client import AI_CRM_LLM
from memory import MemoryManager
from tools import SearchTools
from prompts import SYSTEM_PROMPT, INTENT_CLASSIFICATION_PROMPT, DATABASE_EXTRACT_PROMPT

logger = logging.getLogger(__name__)


def convert_gradio_to_openai_format(gradio_history):
    """将 Gradio 的 [[user, ai], ...] 格式转换为 OpenAI 的 [{role, content}, ...] 格式"""
    messages = []
    for turn in gradio_history:
        if isinstance(turn, list) and len(turn) == 2:
            user_msg, ai_msg = turn
            if user_msg:
                messages.append({"role": "user", "content": str(user_msg)})
            if ai_msg:
                messages.append({"role": "assistant", "content": str(ai_msg)})
        elif isinstance(turn, dict) and 'role' in turn and 'content' in turn:
            messages.append({"role": turn['role'], "content": str(turn['content'])})
    return messages


def try_load_rag_engine():
    try:
        vector_db_path = Config.VECTOR_DB_PATH
        index_path = vector_db_path + "/index.faiss"
        
        if os.path.exists(index_path):
            from rag_engine import RAGEngine
            return RAGEngine(enable_rag=True)
        else:
            return None
    except Exception as e:
        logger.warning(f"加载知识库失败: {e}")
        return None


class SeaChatAgent:
    def __init__(self, rag_engine=None):
        self.llm_client = AI_CRM_LLM(api_key=Config.api_key, model=Config.model)
        self.memory_manager = MemoryManager()
        self.search_tools = SearchTools()
        self.rag_engine = rag_engine

    def _get_intent(self, query: str) -> str:
        prompt = INTENT_CLASSIFICATION_PROMPT.format(query=query)
        messages = [{"role": "user", "content": prompt}]
        
        try:
            response = self.llm_client.chat(messages, temperature=0.1)
            intent = response.strip().upper()
            
            valid_intents = ["WEATHER", "DATABASE_UPDATE", "RAG_QUERY", "DATABASE_QUERY", "CHAT"]
            for valid in valid_intents:
                if valid in intent:
                    return valid
            return "CHAT"
        except Exception as e:
            return "CHAT"

    def _handle_weather(self, query: str) -> str:
        try:
            weather_info = self.search_tools.search_weather(query)
            if weather_info:
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"请根据以下天气信息回答用户问题。\n天气信息:\n{weather_info}\n\n用户问题: {query}"}
                ]
                return self.llm_client.chat(messages)
            else:
                return "抱歉，暂时无法获取天气信息。"
        except Exception as e:
            return "抱歉，天气查询功能暂时不可用。"

    def _handle_database_update(self, query: str, phone_number: str) -> str:
        try:
            extract_prompt = DATABASE_EXTRACT_PROMPT.format(query=query)
            json_str = self.llm_client.chat([{"role": "user", "content": extract_prompt}])
            
            logger.info(f"LLM原始输出: {json_str}")
            
            clean_json = json_str.replace("```json", "").replace("```", "").strip()
            
            logger.info(f"清理后的JSON: {clean_json}")
            
            extracted_data = json.loads(clean_json)
            
            logger.info(f"提取到的更新数据: {extracted_data}")
            
            # 检查是否有用于识别客户的字段
            has_identifier = any(key in extracted_data for key in ['name', 'phone_number', 'email', 'user_id'])
            
            if not has_identifier:
                return "抱歉，我没有找到客户的姓名、电话、邮箱或ID，请提供客户的识别信息，例如：'把张三的余额改成5000'。"
            
            if not extracted_data:
                return "抱歉，未提取到有效的更新数据，请提供更明确的信息。"
            
            success = self.memory_manager.update_long_term_memory(phone_number, extracted_data)
            
            if success:
                return "CRM 客户数据已成功更新！"
            else:
                return "数据更新失败，请检查参数是否正确。"
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}, 原始数据: {json_str}")
            return "抱歉，我无法准确理解您需要修改的数据内容，请尝试提供更明确的描述，例如：'把张三的余额改成5000'。"
        except Exception as e:
            logger.error(f"数据更新失败: {e}", exc_info=True)
            return "抱歉，数据操作功能暂时不可用。"

    def _handle_rag_query(self, query: str) -> str:
        if not self.rag_engine or not self.rag_engine.vector_store:
            return "知识库功能未启用，如需使用请先运行: python init_knowledge_base.py"
        
        try:
            context, sources = self.rag_engine.retrieve_context(query)
            
            if not context or "未找到相关内容" in context:
                return "知识库中未找到相关信息，请尝试其他问题，或先运行 init_knowledge_base.py 更新知识库。"
            
            messages = [
                {"role": "user", "content": f"请根据以下知识库内容回答用户问题，不要重复回答。\n知识库内容:\n{context}\n\n用户问题: {query}"}
            ]
            response = self.llm_client.chat(messages)
            
            if response:
                response = self._clean_duplicate_content(response)
            
            if sources:
                unique_sources = list(set(sources))
                source_str = "、".join(unique_sources)
                response = f"{response}\n\n信息来源：{source_str}"
            
            return response
        except Exception as e:
            logger.error(f"RAG查询失败: {e}")
            return "抱歉，知识库查询功能暂时不可用。"
    
    def _clean_duplicate_content(self, text):
        """清理重复内容"""
        if not text:
            return text
        
        import re
        
        text = text.strip()
        
        lines = text.split('\n')
        result = []
        seen = set()
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                result.append(line)
                continue
            
            if line_stripped in seen:
                continue
            
            has_duplicate = False
            for prev_line in seen:
                if len(line_stripped) > 30 and line_stripped in prev_line:
                    has_duplicate = True
                    break
                if len(prev_line) > 30 and prev_line in line_stripped:
                    has_duplicate = True
                    break
            
            if not has_duplicate:
                seen.add(line_stripped)
                result.append(line)
        
        cleaned = '\n'.join(result)
        
        if len(cleaned) > 50:
            pattern = re.compile(r'(.{30,}?)\1+')
            cleaned = pattern.sub(r'\1', cleaned)
        
        return cleaned

    def _handle_database_query(self, query: str, phone_number: str) -> str:
        try:
            if "所有" in query or "全部" in query or "列表" in query:
                all_customers = self.memory_manager.get_all_customers()
                if all_customers:
                    customer_info = []
                    for customer in all_customers:
                        info = f"- {customer.get('name', '未知')} (ID: {customer.get('user_id')})\n"
                        info += f"  电话: {customer.get('phone_number', '无')}\n"
                        info += f"  邮箱: {customer.get('email', '无')}\n"
                        info += f"  状态: {customer.get('status', '无')} | 等级: {customer.get('level', '无')}\n"
                        info += f"  余额: {customer.get('balance', 0.0)}\n"
                        customer_info.append(info)
                    
                    response_text = f"当前 CRM 系统中共有 {len(all_customers)} 位客户：\n\n" + "\n".join(customer_info)
                    
                    messages = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"请将以下 CRM 客户数据以友好易读的格式回答用户。\n数据:\n{response_text}\n\n用户问题: {query}"}
                    ]
                    return self.llm_client.chat(messages)
                else:
                    return "目前 CRM 系统中暂无客户数据。"
            
            extract_prompt = f"请从以下用户查询中提取用于查询 CRM 客户数据的关键词（例如客户姓名、ID、电话等），直接返回关键词即可，不要有其他内容：\n{query}"
            search_keyword = self.llm_client.chat([{"role": "user", "content": extract_prompt}]).strip()
            
            results = self.memory_manager.query_customer(search_keyword)
            
            if results:
                customer_info = []
                for customer in results:
                    info = f"- {customer.get('name', '未知')} (ID: {customer.get('user_id')})\n"
                    info += f"  电话: {customer.get('phone_number', '无')}\n"
                    info += f"  邮箱: {customer.get('email', '无')}\n"
                    info += f"  状态: {customer.get('status', '无')} | 等级: {customer.get('level', '无')}\n"
                    info += f"  余额: {customer.get('balance', 0.0)}\n"
                    customer_info.append(info)
                
                response_text = f"查询到 {len(results)} 位客户：\n\n" + "\n".join(customer_info)
                
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"请将以下 CRM 客户数据以友好易读的格式回答用户。\n数据:\n{response_text}\n\n用户问题: {query}"}
                ]
                return self.llm_client.chat(messages)
            else:
                return f"未找到与 '{search_keyword}' 相关的客户信息。您可以尝试使用姓名、ID 或电话进行查询。"
                
        except Exception as e:
            return "抱歉，数据库查询功能暂时不可用。"

    def _handle_chat(self, query: str, trimmed_history: list) -> str:
        try:
            # 将 Gradio 格式转换为 OpenAI 格式
            formatted_history = convert_gradio_to_openai_format(trimmed_history)

            # 构建消息列表
            messages = []

            # 添加系统提示
            if SYSTEM_PROMPT:
                messages.append({"role": "system", "content": str(SYSTEM_PROMPT)})

            # 添加转换后的历史对话
            messages.extend(formatted_history)

            # 添加当前用户输入
            messages.append({"role": "user", "content": str(query)})

            return self.llm_client.chat(messages)
        except Exception as e:
            logger.error(f"聊天处理失败: {e}")
            return "抱歉，我现在无法回复，请稍后再试。"

    def run(self, phone_number: str, query: str) -> str:
        chat_history = self.memory_manager.get_chat_history(phone_number)
        trimmed_history = self.memory_manager.trim_short_term_memory(chat_history, max_rounds=5)
        
        intent = self._get_intent(query)
        
        final_response = ""
        
        if intent == "WEATHER":
            final_response = self._handle_weather(query)
        elif intent == "DATABASE_UPDATE":
            final_response = self._handle_database_update(query, phone_number)
        elif intent == "DATABASE_QUERY":
            final_response = self._handle_database_query(query, phone_number)
        elif intent == "RAG_QUERY":
            final_response = self._handle_rag_query(query)
        else:
            final_response = self._handle_chat(query, trimmed_history)
        
        final_response = self._clean_duplicate_content(final_response)
        
        self.memory_manager.save_to_history(phone_number, query, final_response)
        
        return final_response


def cli_mode():
    """命令行交互模式"""
    print("你好！我是 CRM 小助手")
    print("您可以：")
    print("  - 与我聊天")
    print("  - 询问天气")
    print("  - 查询本地知识库")
    print("  - 操作 CRM 数据（可以查询/新增/修改，不允许删除）")
    print("输入 'exit' 或 'quit' 退出")
    print("=" * 60)
    print()
   
    rag_engine = try_load_rag_engine()
    
    try:
        agent = SeaChatAgent(rag_engine=rag_engine)
    except Exception as e:
        print(f"初始化失败: {e}")
        return
    
    phone_number = "default_user"
    
    while True:
        try:
            user_input = input("你: ").strip()
            
            if user_input.lower() in ["exit", "quit"]:
                print("再见！")
                break
                
            if not user_input:
                continue
                          
            response = agent.run(phone_number, user_input)
            
            print(f"AI助手: {response}")
            
        except KeyboardInterrupt:
            print("\n程序被中断，再见！")
            break
        except Exception as e:
            print(f"发生错误: {e}")


def flask_mode():
    """Flask 服务模式"""
    try:
        from flask_app import start_flask_app
        start_flask_app()
    except ImportError as e:
        print(f"启动 Flask 服务失败，缺少依赖: {e}")
        print("请安装 Flask 和 Flask-CORS: pip install flask flask-cors")
    except Exception as e:
        print(f"启动 Flask 服务失败: {e}")


def main():
    """主入口函数"""
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode == 'flask':
            flask_mode()
            return
        else:
            print(f"未知模式: {mode}")
            print("使用方式:")
            print("  python agent.py        - 交互式命令行模式")
            print("  python agent.py flask - Flask 服务模式")
            return
    
    # 默认启动命令行模式
    cli_mode()


if __name__ == "__main__":
    main()