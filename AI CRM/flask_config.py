# Flask 配置文件

class FlaskConfig:
    """Flask 应用配置"""
    
    # 基础配置
    DEBUG = False
    TESTING = False
    SECRET_KEY = 'your-secret-key-here-change-in-production'
    
    # 服务器配置
    HOST = '0.0.0.0'
    PORT = 5000
    
    # API 配置
    API_VERSION = 'v1'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # CORS 配置（允许跨域）
    CORS_ORIGINS = ['*']
    
    # 日志配置
    LOG_LEVEL = 'INFO'


class DevelopmentConfig(FlaskConfig):
    """开发环境配置"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(FlaskConfig):
    """生产环境配置"""
    DEBUG = False
    LOG_LEVEL = 'WARNING'


# 根据环境选择配置
def get_config(env='development'):
    """获取配置对象"""
    configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig
    }
    return configs.get(env, DevelopmentConfig)
