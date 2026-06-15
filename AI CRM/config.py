import os
import sys
import yaml
from dotenv import load_dotenv

# 设置 Hugging Face 镜像 - 使用 ModelScope 加速下载
os.environ['HF_ENDPOINT'] = 'https://modelscope.cn'
os.environ['HUGGINGFACE_HUB_DISABLE_PROGRESS_BARS'] = '1'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

# 路径设置
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)  # chatbot-1 目录

# 优先加载 config.yaml（统一配置）
config_yaml_path = os.path.join(parent_dir, "config.yaml")
config = {}

if os.path.exists(config_yaml_path):
    try:
        with open(config_yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        print(f"[config] 从 config.yaml 加载配置: {config_yaml_path}")
    except Exception as e:
        print(f"[config] 加载 config.yaml 失败: {e}")
        config = {}

# 补充加载 .env（用于敏感信息）
env_file = os.path.join(parent_dir, ".env")
if os.path.exists(env_file):
    load_dotenv(env_file)
    print(f"[config] 从 .env 加载环境变量")


class Config:
    """全局配置类，统一管理所有配置"""

    # ==================== LLM 配置 ====================
    api_key = config.get('llm', {}).get('api_key') or os.getenv("aliyun_key") or os.getenv("api_key")
    aliyun_url = config.get('llm', {}).get('base_url') or os.getenv("aliyun_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    model = config.get('llm', {}).get('model') or os.getenv("model", "qwen3-max")

    # ==================== 搜索工具配置 ====================
    tavily_api_key = config.get('crm', {}).get('TavilySearchResults_API_KEY') or os.getenv("TavilySearchResults_API_KEY")

    # ==================== MySQL 数据库配置 ====================
    db_config = config.get('database', {})
    MYSQL_HOST = db_config.get('host') or os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(db_config.get('port') or os.getenv("MYSQL_PORT", 3306))
    MYSQL_USER = db_config.get('user') or os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = db_config.get('password') or os.getenv("MYSQL_PASSWORD", "123456")
    MYSQL_DB = db_config.get('db') or os.getenv("MYSQL_DB", "AI_CRM")
    DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"

    # ==================== 路径与存储配置 ====================
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # 优先使用 config.yaml 中的路径
    crm_config = config.get('crm', {})
    VECTOR_DB_PATH = os.path.join(parent_dir, crm_config.get('vector_db_path', os.path.join("AI CRM", "storage", "vector_db")))
    UPLOAD_FOLDER = os.path.join(parent_dir, crm_config.get('upload_folder', os.path.join("AI CRM", "uploads")))

    # ==================== TTS 配置 ====================
    tts_config = config.get('tts', {})
    TTS_VOICE = tts_config.get('voice', 'zh-CN-XiaoxiaoNeural')
    TTS_OUTPUT_DIR = os.path.join(parent_dir, tts_config.get('output_dir', 'tmp/'))

    # ==================== ASR 配置 ====================
    asr_config = config.get('asr', {})
    ASR_MODEL_DIR = os.path.join(parent_dir, asr_config.get('model_dir', 'voice_qa_api/models/SenseVoiceSmall'))
    ASR_OUTPUT_DIR = os.path.join(parent_dir, asr_config.get('output_dir', 'tmp/'))

    # ==================== 服务配置 ====================
    server_config = config.get('server', {})
    HTTP_PORT = server_config.get('http_port', 8000)
    GRADIO_PORT = server_config.get('gradio_port', 7860)

    # ==================== 系统提示词 ====================
    SYSTEM_PROMPT = config.get('prompts', {}).get('system', """你是一个专业的 AI CRM 智能助手。请用简洁、专业的方式回答用户问题。""")

    @classmethod
    def init_storage(cls):
        """初始化必要的本地存储文件夹"""
        # 确保 tmp 目录存在
        os.makedirs(cls.TTS_OUTPUT_DIR, exist_ok=True)
        os.makedirs(cls.ASR_OUTPUT_DIR, exist_ok=True)
        os.makedirs(cls.VECTOR_DB_PATH, exist_ok=True)
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
        print(f"[config] 存储目录初始化完成")

    @classmethod
    def check_keys(cls):
        """检查关键 API Key 是否已配置"""
        warnings = []
        if not cls.api_key or cls.api_key == "your_api_key_here":
            warnings.append("LLM API Key (aliyun_key)")
        if not cls.tavily_api_key or cls.tavily_api_key == "your_tavily_api_key_here":
            warnings.append("Tavily API Key")

        if warnings:
            print(f"[config] ⚠️ 以下配置未填写: {', '.join(warnings)}")
        else:
            print("[config] ✅ 所有 API Keys 配置完成")


if __name__ == "__main__":
    Config.init_storage()
    Config.check_keys()