# Flask 应用核心代码

import json
from flask import Flask, request, Response
from flask_cors import CORS

def create_app():
    """创建 Flask 应用实例"""
    app = Flask(__name__)
    
    from flask_config import get_config
    app.config.from_object(get_config('development'))
    
    CORS(app, origins=app.config['CORS_ORIGINS'])
    
    global agent
    agent = None
    
    return app


def parse_request():
    """解析传入的 JSON 请求"""
    try:
        data = request.get_json()
        return data
    except Exception as e:
        return None


def valid_request(data):
    """验证请求内容是否有效"""
    if not data:
        return False
    if 'query' not in data or not isinstance(data['query'], str) or not data['query'].strip():
        return False
    return True


def success_response(data):
    """返回成功响应"""
    response = {
        'status': 'success',
        'data': data
    }
    return Response(
        json.dumps(response, ensure_ascii=False),
        status=200,
        content_type='application/json; charset=utf-8'
    )


def error_response(message="Invalid request", status_code=400):
    """返回错误响应"""
    response = {
        'status': 'error',
        'message': message
    }
    return Response(
        json.dumps(response, ensure_ascii=False),
        status=status_code,
        content_type='application/json; charset=utf-8'
    )


def chat_response(data):
    """处理聊天请求"""
    global agent
    
    try:
        if agent is None:
            from agent import SeaChatAgent, try_load_rag_engine
            rag_engine = try_load_rag_engine()
            agent = SeaChatAgent(rag_engine=rag_engine)
        
        query = data.get('query', '')
        phone_number = data.get('phone_number', 'web_user')
        
        response_text = agent.run(phone_number, query)
        
        return success_response({'response': response_text})
        
    except Exception as e:
        return error_response(f"处理请求时发生错误: {str(e)}")


def get_chat_ui():
    """生成简洁的聊天界面"""
    ui = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SeaChat AI CRM</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .chat-container { max-width: 900px; margin: 0 auto; padding: 20px; display: flex; flex-direction: column; height: calc(100vh - 40px); }
        .chat-header { background: rgba(255,255,255,0.95); padding: 20px; border-radius: 16px 16px 0 0; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .chat-header h1 { color: #2c3e50; font-size: 24px; text-align: center; }
        .chat-header p { color: #7f8c8d; text-align: center; margin-top: 5px; font-size: 14px; }
        .chat-messages { flex: 1; background: rgba(255,255,255,0.95); overflow-y: auto; padding: 20px; }
        .message { display: flex; margin-bottom: 15px; }
        .message.user { justify-content: flex-end; }
        .message.bot { justify-content: flex-start; }
        .message-content { max-width: 70%; padding: 12px 16px; border-radius: 20px; }
        .user .message-content { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 20px 20px 5px 20px; }
        .bot .message-content { background: #f1f3f4; color: #2c3e50; border-radius: 20px 20px 20px 5px; }
        .chat-input { background: rgba(255,255,255,0.95); padding: 15px; border-radius: 0 0 16px 16px; box-shadow: 0 -2px 10px rgba(0,0,0,0.1); display: flex; gap: 10px; }
        .chat-input input { flex: 1; padding: 12px 18px; border: 2px solid #e0e0e0; border-radius: 30px; font-size: 16px; outline: none; transition: border-color 0.3s; }
        .chat-input input:focus { border-color: #667eea; }
        .chat-input button { padding: 12px 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 30px; font-size: 16px; cursor: pointer; transition: transform 0.2s; }
        .chat-input button:hover { transform: scale(1.05); }
        .chat-input button:active { transform: scale(0.98); }
        .typing-indicator { display: flex; align-items: center; color: #95a5a6; }
        .typing-indicator span { width: 6px; height: 6px; background: #95a5a6; border-radius: 50%; margin: 0 2px; animation: typing 1.4s infinite ease-in-out; }
        .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
        .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes typing { 0%, 100% { opacity: 0.3; } 50% { opacity: 1; } }
        .welcome-message { text-align: center; padding: 20px; color: #7f8c8d; font-size: 14px; }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <h1>SeaChat AI CRM</h1>
            <p>智能助手 - 支持聊天、查询天气、操作 CRM 数据</p>
        </div>
        <div class="chat-messages" id="chatMessages">
            <div class="welcome-message">您好！我是您的 CRM 智能助手，有什么可以帮助您的？</div>
        </div>
        <div class="chat-input">
            <input type="text" id="userInput" placeholder="输入您的问题..." onkeydown="if(event.keyCode==13) sendMessage()">
            <button onclick="sendMessage()">发送</button>
        </div>
    </div>
    
    <script>
        const chatMessages = document.getElementById('chatMessages');
        const userInput = document.getElementById('userInput');
        
        function sendMessage() {
            const query = userInput.value.trim();
            if (!query) return;
            
            addMessage(query, 'user');
            userInput.value = '';
            
            addTypingIndicator();
            
            fetch('/api/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query: query})
            })
            .then(response => response.json())
            .then(data => {
                removeTypingIndicator();
                if (data.status === 'success') {
                    addMessage(data.data.response, 'bot');
                } else {
                    addMessage('抱歉，处理请求时发生错误。', 'bot');
                }
            })
            .catch(error => {
                removeTypingIndicator();
                addMessage('网络错误，请重试。', 'bot');
            });
        }
        
        function addMessage(text, sender) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;
            messageDiv.innerHTML = `<div class="message-content">${escapeHtml(text)}</div>`;
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        function addTypingIndicator() {
            const typingDiv = document.createElement('div');
            typingDiv.className = 'message bot typing';
            typingDiv.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
            chatMessages.appendChild(typingDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        function removeTypingIndicator() {
            const typingElement = document.querySelector('.typing');
            if (typingElement) {
                typingElement.remove();
            }
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        userInput.focus();
    </script>
</body>
</html>"""
    return ui


def start_flask_app():
    """运行 Flask 应用"""
    app = create_app()
    
    @app.route('/')
    def index():
        """首页 - 聊天界面"""
        return Response(get_chat_ui(), content_type='text/html; charset=utf-8')
    
    @app.route('/favicon.ico')
    def favicon():
        return "", 204
    
    @app.route('/api/chat', methods=['POST'])
    def api_chat():
        """聊天 API 端点"""
        data = parse_request()
        if not valid_request(data):
            return error_response("Invalid request")
        return chat_response(data)
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """健康检查端点"""
        return success_response({'status': 'healthy'})
    
    host = app.config['HOST']
    port = app.config['PORT']
    
    print("=" * 60)
    print("SeaChat AI CRM - Flask 服务")
    print("=" * 60)
    print(f"\n服务地址: http://127.0.0.1:{port}/")
    print("\n可用接口:")
    print(f"  - http://127.0.0.1:{port}/         (聊天界面)")
    print(f"  - http://127.0.0.1:{port}/api/chat (聊天API)")
    print("\n按 Ctrl+C 停止服务")
    print("=" * 60)
    
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == '__main__':
    start_flask_app()
