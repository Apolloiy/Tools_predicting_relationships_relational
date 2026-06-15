import logging
import sys
import io

# 解决 Windows 控制台编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 配置日志：显示在控制台，级别设为 DEBUG（显示所有信息）
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from logger import configure_logging
from agent import SeaChatAgent

def main():
    # 1. 最先初始化全局日志系统
    configure_logging()
    
    # 2. 初始化 Agent 大脑
    agent = SeaChatAgent()
    
    # 3. 这里可以接入你的 Web 框架（如 Flask / FastAPI）
    # from flask import Flask, request, jsonify
    # app = Flask(__name__)
    # 
    # @app.route("/chat", methods=["POST"])
    # def chat():
    #     data = request.json
    #     response = agent.run(data["phone_number"], data["query"])
    #     return jsonify({"response": response})
    # 
    # app.run(host="0.0.0.0", port=5000)

    # 4. 或者，如果只是本地测试，提供一个简单的命令行交互界面
    print("SeaChat CRM 智能助手已启动！(输入 'exit' 退出)")
    phone_number = input("请输入您的手机号: ")
    
    while True:
        query = input("\n您: ")
        if query.lower() in ["exit", "quit"]:
            print("再见！")
            break
            
        response = agent.run(phone_number, query)
        print(f"\nAI助手: {response}")

if __name__ == "__main__":
    main()
