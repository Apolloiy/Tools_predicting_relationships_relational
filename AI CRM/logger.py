# utils/logger.py
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from config import Config

# 引入 colorlog 库实现控制台彩色日志（需在 requirements.txt 中已包含 colorlog）
try:
    import colorlog
    HAS_COLORLOG = True
except ImportError:
    HAS_COLORLOG = False


def configure_logging():
    """
    全局日志配置函数
    功能：同时输出到控制台和文件，支持按文件大小自动轮转，防止单文件过大。
    建议在 main.py 启动时最先调用此方法。
    """
    
    # 1. 确保 logs 目录存在
    log_dir = os.path.join(Config.BASE_DIR, "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 2. 定义统一的日志格式 (时间 | 级别 | 模块名 | 具体信息)
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # 3. 创建根 Logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # 根级别设为最低，由各 Handler 自行过滤
    
    # 避免重复添加 Handler（例如在测试或多次导入时）
    if root_logger.handlers:
        return 

    # ================= 控制台 Handler =================
    if HAS_COLORLOG:
        # 使用 colorlog 让控制台日志带颜色，方便快速识别错误
        console_formatter = colorlog.ColoredFormatter(
            fmt="%(log_color)s%(asctime)s | %(levelname)-8s%(reset)s | %(name)s | %(message)s",
            datefmt=date_format,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
            }
        )
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
    else:
        # 如果没有安装 colorlog，回退到普通文本格式
        console_formatter = logging.Formatter(log_format, datefmt=date_format)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        
    console_handler.setLevel(logging.INFO)  # 控制台只展示 INFO 及以上级别，保持界面整洁
    root_logger.addHandler(console_handler)

    # ================= 文件 Handler (支持轮转) =================
    log_file_path = os.path.join(log_dir, "sea_chat.log")
    # maxBytes=10MB, backupCount=5 表示最多保留 5 个历史备份文件
    file_handler = RotatingFileHandler(
        log_file_path, 
        maxBytes=10 * 1024 * 1024, 
        backupCount=5, 
        encoding='utf-8'
    )
    file_formatter = logging.Formatter(log_format, datefmt=date_format)
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)  # 文件中记录所有 DEBUG 及以上级别，便于深度排查
    root_logger.addHandler(file_handler)

    logging.info("Global logging system initialized successfully!")


# 测试入口
if __name__ == "__main__":
    configure_logging()
    
    # 模拟不同级别的日志输出
    logger = logging.getLogger(__name__)
    logger.debug("这是一条调试信息（仅写入文件）")
    logger.info("RAG 引擎初始化成功")
    logger.warning("Tavily API 响应较慢，耗时 3s")
    logger.error("MySQL 连接池耗尽，请稍后重试")
