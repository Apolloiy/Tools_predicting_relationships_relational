#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM API 测试脚本 - 从配置文件读取模型配置
"""

import os
import sys
import yaml
from dotenv import load_dotenv
from openai import OpenAI

def load_config():
    """从 config.yaml 和 .env 加载配置"""
    main_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 先加载 .env
    env_file = os.path.join(main_dir, ".env")
    if os.path.exists(env_file):
        load_dotenv(env_file, override=True)
        print("[INFO] Loaded config from .env")
    
    # 再加载 config.yaml
    yaml_file = os.path.join(main_dir, "config.yaml")
    config = {}
    if os.path.exists(yaml_file):
        with open(yaml_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        print("[INFO] Loaded config from config.yaml")
    
    # 优先使用 config.yaml，其次是环境变量，最后是默认值
    llm_config = config.get('llm', {})
    api_key = llm_config.get('api_key') or os.getenv("aliyun_key")
    base_url = llm_config.get('base_url') or os.getenv("aliyun_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    model = llm_config.get('model') or os.getenv("model", "qwen-max")
    
    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model
    }

def test_llm_connection(config):
    """测试 LLM API 连接"""
    if not config['api_key'] or config['api_key'] == "your_api_key_here":
        print("\n[ERROR] API Key not configured!")
        return False
    
    try:
        print("\n[INFO] Connecting to {}".format(config['base_url']))
        client = OpenAI(
            api_key=config['api_key'],
            base_url=config['base_url']
        )
        
        print("[INFO] Calling model: {}".format(config['model']))
        response = client.chat.completions.create(
            model=config['model'],
            messages=[
                {"role": "user", "content": "Hello, please introduce yourself briefly"}
            ],
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        print("\n[SUCCESS] Model output:")
        print("-" * 50)
        print(content)
        print("-" * 50)
        return True
        
    except Exception as e:
        print("\n[ERROR] Connection failed:")
        print("   Error type: {}".format(type(e).__name__))
        print("   Error message: {}".format(str(e)))
        return False

def main():
    print("=" * 60)
    print("      LLM API Test Script")
    print("=" * 60)
    
    config = load_config()
    
    print("\n[CONFIG] Configuration:")
    print("   API Key: {}...".format(config['api_key'][:10]) if config['api_key'] else "   API Key: Not configured")
    print("   Base URL: {}".format(config['base_url']))
    print("   Model: {}".format(config['model']))
    
    success = test_llm_connection(config)
    
    print("\n" + "=" * 60)
    if success:
        print("[RESULT] Test passed!")
    else:
        print("[RESULT] Test failed")
    print("=" * 60)

if __name__ == "__main__":
    main()