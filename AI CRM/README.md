# SeaChat AI CRM 接口文档

## 📋 概述

SeaChat AI CRM 是一款基于人工智能的客户关系管理系统，集成智能对话、天气查询、知识库问答和CRM数据管理功能。

### 系统架构

| 组件 | 描述 |
|-----|------|
| **核心引擎** | `agent.py` - AI智能体大脑 |
| **记忆管理** | `memory.py` - 对话历史与CRM数据管理 |
| **数据库** | `database.py` - MySQL数据库操作 |
| **LLM客户端** | `llm_client.py` - 百度千帆API集成 |
| **知识库** | `rag_engine.py` - FAISS向量数据库 |
| **Flask服务** | `flask_app.py` - REST API服务 |

### 服务地址

```flask
http://127.0.0.1:5000/
```

---

## 🚀 快速开始

### 启动服务

```bash
# Flask Web服务模式
python agent.py flask

# 命令行交互模式
python agent.py
```

---

## 📡 API 接口列表

### 1. 首页 - 聊天界面

**接口地址**：`GET /`

**接口说明**：返回Web聊天界面，用户可直接在浏览器中进行对话。

**请求示例**：

```bash
curl http://127.0.0.1:5000/
```

**响应说明**：返回HTML页面，包含完整的聊天界面。

---

### 2. 聊天接口

**接口地址**：`POST /api/chat`

**接口说明**：与AI助手进行对话，支持闲聊、天气查询、CRM数据操作、知识库问答。

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 | 示例值 |
|-------|------|------|------|--------|
| query | string | ✅ 是 | 用户问题 | "你好" |
| phone_number | string | ❌ 否 | 用户标识（默认为web_user） | "user001" |

#### 请求示例

**cURL**：

```bash
curl -X POST http://127.0.0.1:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "你好", "phone_number": "user001"}'
```

**Python**：

```python
import requests

response = requests.post(
    'http://127.0.0.1:5000/api/chat',
    json={
        'query': '你好',
        'phone_number': 'user001'
    }
)
print(response.json())
```

**JavaScript**：

```javascript
fetch('http://127.0.0.1:5000/api/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        query: '你好',
        phone_number: 'user001'
    })
})
.then(response => response.json())
.then(data => console.log(data));
```

#### 响应结构

```json
{
    "status": "success",
    "data": {
        "response": "您好！我是您的 CRM 智能助手，有什么可以帮助您的？"
    }
}
```

**响应字段说明**：

| 字段 | 类型 | 说明 |
|-----|------|------|
| status | string | 请求状态："success" 或 "error" |
| data.response | string | AI助手的回复内容 |
| message | string | 错误信息（仅在status为error时返回） |

#### 错误响应

```json
{
    "status": "error",
    "message": "Invalid request"
}
```

---

### 3. 健康检查

**接口地址**：`GET /health`

**接口说明**：检查服务是否正常运行，用于监控和负载均衡器健康检查。

#### 请求示例

```bash
curl http://127.0.0.1:5000/health
```

#### 响应结构

```json
{
    "status": "success",
    "data": {
        "status": "healthy"
    }
}
```

---

## 💬 支持的功能类型

### 1. 闲聊对话

**触发关键词**：你好、嗨、在吗、天气、怎么样等

**示例输入**：
- "你好"
- "今天天气怎么样"
- "讲个笑话"

**示例输出**：
```
您好！我是您的 CRM 智能助手，有什么可以帮助您的？
```

### 2. 天气查询

**触发关键词**：天气、温度、下雨、晴、温度等

**示例输入**：
- "北京今天天气怎么样"
- "上海明天的温度"
- "深圳会下雨吗"

**示例输出**：
```
北京今天天气晴，温度15-25℃，适合出行。
```

### 3. CRM数据查询

**触发关键词**：查询、列出、显示、看看等

**示例输入**：
- "查询所有客户"
- "列出所有客户"
- "查询张三的信息"
- "看看李四的数据"

**示例输出**：
```
当前 CRM 系统中共有 3 位客户：

1. 张三 (ID: 1001)
   电话: 13800138001
   邮箱: zhangsan@example.com
   状态: active | 等级: VIP
   余额: 5000.00
```

### 4. CRM数据更新

**触发关键词**：修改、更新、改成、设置、新增、增加等

**示例输入**：
- "把张三的余额改成5000"
- "将李四的等级升级为VIP"
- "新增一个客户叫王五，电话13900000000"
- "将赵六的状态设为inactive"

**示例输出**：
```
CRM 客户数据已成功更新！
```

**支持的更新字段**：

| 字段名 | 类型 | 说明 | 示例 |
|-------|------|------|------|
| name | string | 客户姓名 | "张三" |
| phone_number | string | 电话号码 | "13800138001" |
| email | string | 邮箱地址 | "zhangsan@example.com" |
| status | string | 客户状态 | "active" / "inactive" |
| level | string | 客户等级 | "普通" / "VIP" / "钻石VIP" |
| balance | number | 账户余额 | 5000.00 |

### 5. 知识库问答

**触发关键词**：知识库、公司、产品、服务、政策等

**示例输入**：
- "公司有哪些产品"
- "服务政策是什么"
- "如何使用XX功能"

**说明**：需要先运行 `python init_knowledge_base.py` 初始化知识库。

---

## 🔐 认证方式

### 当前版本

**认证要求**：❌ 不需要

当前版本为开发/演示版本，API无需认证即可访问。

### 生产环境建议

在正式生产环境中，建议添加以下安全措施：

1. **API Key认证**

```python
@app.before_request
def check_api_key():
    api_key = request.headers.get('X-API-Key')
    if api_key != Config.API_KEY:
        return jsonify({'error': 'Unauthorized'}), 401
```

2. **Token认证**

```python
@app.before_request
def check_token():
    token = request.headers.get('Authorization')
    if not token or not verify_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
```

3. **IP白名单**

```python
ALLOWED_IPS = ['127.0.0.1', '192.168.1.0/24']

@app.before_request
def check_ip():
    if request.remote_addr not in ALLOWED_IPS:
        return jsonify({'error': 'Forbidden'}), 403
```

---

## ⚠️ 错误码说明

| HTTP状态码 | 错误类型 | 说明 | 解决方案 |
|-----------|---------|------|---------|
| 200 | - | 请求成功 | - |
| 400 | Bad Request | 请求参数错误 | 检查请求参数是否正确 |
| 401 | Unauthorized | 未授权 | 添加有效的认证信息 |
| 403 | Forbidden | 禁止访问 | 检查IP白名单或权限设置 |
| 404 | Not Found | 接口不存在 | 检查接口地址是否正确 |
| 500 | Internal Server Error | 服务器内部错误 | 检查服务器日志 |
| 503 | Service Unavailable | 服务不可用 | 检查后端服务是否启动 |

---

## 📊 性能指标

| 指标 | 预期值 | 说明 |
|-----|-------|------|
| 响应时间 | < 3秒 | 单次API调用响应时间 |
| 并发能力 | 10-50 | 建议并发连接数 |
| 可用性 | 99.9% | 服务可用时间占比 |

---

## 🛠️ 故障排查

### 常见问题

#### 1. 连接超时

**症状**：`requests.exceptions.ReadTimeout`

**解决方案**：
- 检查网络连接
- 增加超时时间：

```python
response = requests.post(url, json=data, timeout=30)
```

#### 2. CORS跨域错误

**症状**：`Access-Control-Allow-Origin` 错误

**解决方案**：已在 `flask_app.py` 中启用CORS支持，如仍有问题检查前端请求头。

#### 3. 数据库连接失败

**症状**：`OperationalError: (1045, "Access denied")`

**解决方案**：
- 检查 `config.py` 中的数据库配置
- 确认MySQL服务已启动
- 验证用户名和密码

#### 4. LLM API调用失败

**症状**：`API调用失败` 或 `认证失败`

**解决方案**：
- 检查 `config.py` 中的API Key配置
- 确认API Key有效且未过期
- 检查网络连接到百度千帆服务

---

## 🔄 版本历史

### v1.0.0 (2026-05-29)

**新增功能**：
- ✅ 智能对话功能
- ✅ 天气查询
- ✅ CRM数据管理（查询、新增、更新）
- ✅ 知识库问答
- ✅ Web聊天界面
- ✅ REST API接口

**接口列表**：

| 接口 | 方法 | 说明 |
|-----|------|------|
| `/` | GET | 聊天界面 |
| `/api/chat` | POST | 聊天接口 |
| `/health` | GET | 健康检查 |

---

## 📞 技术支持

### 配置文件

| 文件 | 说明 |
|-----|------|
| `config.py` | 全局配置（API Key、数据库、路径等） |
| `flask_config.py` | Flask服务配置 |

### 核心模块

| 文件 | 说明 |
|-----|------|
| `agent.py` | AI智能体核心逻辑 |
| `llm_client.py` | LLM API客户端 |
| `memory.py` | 记忆与CRM数据管理 |
| `database.py` | MySQL数据库操作 |
| `rag_engine.py` | 知识库引擎 |
| `tools.py` | 工具函数（天气搜索等） |
| `prompts.py` | 提示词模板 |

### 初始化脚本

| 脚本 | 说明 |
|-----|------|
| `init_database.py` | 初始化MySQL数据库 |
| `init_knowledge_base.py` | 初始化向量知识库 |

---

## 📋 快速测试清单

- [ ] 服务启动成功
- [ ] 首页可访问 (`GET /`)
- [ ] 聊天接口可用 (`POST /api/chat`)
- [ ] 健康检查通过 (`GET /health`)
- [ ] 闲聊功能正常
- [ ] 天气查询正常
- [ ] CRM数据查询正常
- [ ] CRM数据更新正常
- [ ] 错误处理正常

---

**文档版本**：v1.0.0  
**最后更新**：2026-05-29  
**维护团队**：SeaChat Development Team
