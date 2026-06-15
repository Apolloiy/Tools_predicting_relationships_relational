# AI CRM 语音助手

一个基于 Gradio 的智能语音交互系统，集成了语音识别（ASR）、语音合成（TTS）、大语言模型（LLM）和检索增强生成（RAG）功能，支持多种云服务商的语音服务。

## 📋 功能特性

### 核心功能
- **语音交互**: 支持语音输入输出，实现自然对话体验
- **文本交互**: 支持文本输入，灵活切换交互方式
- **CRM 客户管理**: 集成 MySQL 数据库，支持客户数据查询和管理
- **RAG 知识库**: 基于 FAISS 的向量数据库，支持文档检索和问答
- **多服务商支持**: 支持阿里云、百度、腾讯、字节等多家云服务商

### 语音识别（ASR）支持
| 服务商 | 类型 | 说明 |
|--------|------|------|
| SenseVoice | 本地模型 | 免费开源，离线运行 |
| FunASR | 本地模型 | 达摩院开源模型 |
| Qwen3-ASR-Flash | 云端 API | 阿里云多语言识别 |
| 阿里云 ASR | 云端 API | 企业级语音识别 |
| 百度 ASR | 云端 API | 高精度语音识别 |
| 腾讯 ASR | 云端 API | 腾讯云语音服务 |
| 字节豆包 ASR | 云端 API | 字节跳动语音服务 |
| OpenAI Whisper | 云端 API | 多语言识别 |
| Vosk | 本地模型 | 轻量级离线识别 |
| Sherpa ONNX | 本地模型 | 高性能离线识别 |

### 语音合成（TTS）支持
| 服务商 | 类型 | 说明 |
|--------|------|------|
| EdgeTTS | 免费 API | Microsoft Edge 语音服务 |
| 阿里云 TTS | 云端 API | 企业级语音合成 |
| 百度 TTS | 云端 API | 丰富音色选择 |
| 腾讯 TTS | 云端 API | 腾讯云语音服务 |
| 字节豆包 TTS | 云端 API | 字节跳动语音服务 |
| OpenAI TTS | 云端 API | OpenAI 语音合成 |

### 大语言模型（LLM）支持
| 服务商 | 模型 |
|--------|------|
| 阿里云 | Qwen-Max |
| 百度 | 文心一言 |
| 腾讯 | 混元 |
| 字节 | 豆包 |

## 🚀 快速开始

### 环境要求
- Python 3.8+
- 推荐使用 Conda 环境

### 安装依赖

```bash
# 创建并激活 Conda 环境
conda create -n trae-ai python=3.10
conda activate trae-ai

# 安装依赖
pip install -r requirements.txt
```

### 启动应用

#### 方式一：直接运行（推荐）

```bash
cd E:\AI practice\trae\chatbot-1
python Chatbot.py
```

#### 方式二：启动 API 服务

```bash
cd E:\AI practice\trae\chatbot-1\voice_qa_api
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 访问界面

启动后，打开浏览器访问：
- **Gradio 界面**: http://localhost:7860
- **API 文档**: http://localhost:8000/docs

## ⚙️ 配置说明

### 配置文件位置

主配置文件: `E:\AI practice\trae\chatbot-1\config.yaml`

### 配置项详解

#### LLM 配置

```yaml
llm:
  type: openai  # 可选: openai, baidu, tencent, doubao
  openai:
    api_key: your_api_key
    base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
    model: qwen-max
    temperature: 0.7
    max_tokens: 2000
```

#### TTS 配置

```yaml
tts:
  type: edge  # 可选: edge, aliyun, baidu, tencent, doubao, openai
  edge:
    voice: "zh-CN-XiaoxiaoNeural"
```

#### ASR 配置

```yaml
asr:
  type: sensevoice  # 可选: sensevoice, funasr, aliyun, baidu, tencent, doubao, openai, qwen3, vosk, sherpa
  sensevoice:
    model_dir: "voice_qa_api/models/SenseVoiceSmall"
```

#### 数据库配置

```yaml
database:
  host: "localhost"
  port: 3306
  user: "root"
  password: "your_password"
  db: "AI_CRM"
```

### 切换服务商示例

**切换到阿里云 ASR:**
```yaml
asr:
  type: aliyun
  aliyun:
    access_key_id: "your_access_key_id"
    access_key_secret: "your_access_key_secret"
    appkey: "your_appkey"
```

**切换到 Qwen3-ASR-Flash:**
```yaml
asr:
  type: qwen3
  qwen3:
    api_key: "your_dashscope_api_key"
    model_name: "qwen3-asr-flash"
```

**切换到阿里云 TTS:**
```yaml
tts:
  type: aliyun
  aliyun:
    access_key_id: "your_access_key_id"
    access_key_secret: "your_access_key_secret"
    appkey: "your_appkey"
    voice: "xiaoyun"
```

## 📁 项目结构

```
E:\AI practice\trae\chatbot-1/
├── AI CRM/                    # CRM 核心模块
│   ├── config.py              # CRM 配置
│   ├── llm_client.py          # LLM 客户端
│   ├── rag_engine.py          # RAG 引擎
│   ├── init_knowledge_base.py # 知识库初始化
│   ├── storage/               # 向量数据库存储
│   └── uploads/               # 上传文件目录
├── voice_qa_api/              # 语音问答 API
│   ├── main.py                # FastAPI 入口
│   ├── core/                  # 核心模块
│   │   ├── providers/         # 服务提供商
│   │   │   ├── asr/           # ASR 模块
│   │   │   │   ├── sensevoice.py
│   │   │   │   ├── fun_local.py
│   │   │   │   ├── qwen3_asr_flash.py
│   │   │   │   ├── aliyun.py
│   │   │   │   ├── baidu.py
│   │   │   │   ├── tencent.py
│   │   │   │   ├── doubao.py
│   │   │   │   ├── openai.py
│   │   │   │   ├── vosk.py
│   │   │   │   ├── sherpa_onnx_local.py
│   │   │   │   ├── audio_preprocessor.py
│   │   │   │   ├── base.py
│   │   │   │   ├── utils.py
│   │   │   │   └── dto/       # 数据传输对象
│   │   │   └── tts/           # TTS 模块
│   │   │       ├── edge.py
│   │   │       ├── aliyun.py
│   │   │       ├── baidu.py
│   │   │       ├── tencent.py
│   │   │       ├── doubao.py
│   │   │       ├── openai.py
│   │   │       ├── base.py
│   │   │       └── dto/       # 数据传输对象
│   │   └── config.py          # API 配置
│   └── models/                # 本地模型目录
│       └── SenseVoiceSmall/   # SenseVoice 模型
├── asr/                       # ASR 原始代码（参考）
├── tts/                       # TTS 原始代码（参考）
├── Chatbot.py                 # 主入口 - Gradio 界面
├── GradioUI.py                # Gradio UI 组件
├── config.yaml                # 统一配置文件
├── .env.example               # 环境变量示例
├── llmtest.py                 # LLM 测试脚本
└── requirements.txt           # 依赖列表
```

## 🎯 使用说明

### 1. 语音对话

1. 启动应用：`python Chatbot.py`
2. 打开 http://localhost:7860
3. 点击麦克风按钮开始录音
4. 说话后松开麦克风
5. 系统自动识别语音并回复

### 2. 文本对话

1. 在输入框中输入文字
2. 点击发送按钮或按 Enter
3. 查看 AI 回复

### 3. 客户数据查询

系统支持查询 MySQL 数据库中的客户信息，例如：
- "查询所有客户"
- "查询张三的联系方式"
- "添加新客户"

### 4. RAG 知识库

#### 初始化知识库

```bash
python "AI CRM/init_knowledge_base.py"
```

#### 添加文档

1. 在 Gradio 界面上传文档
2. 系统自动处理并加入知识库
3. 可以基于文档内容进行问答

### 5. 测试 LLM

```bash
python llmtest.py
```

## 🔧 技术栈

| 模块 | 技术 |
|------|------|
| 界面 | Gradio 4.x |
| API | FastAPI |
| 语音识别 | SenseVoice, FunASR, Qwen3-ASR |
| 语音合成 | EdgeTTS, 阿里云 TTS |
| 大语言模型 | Qwen-Max |
| 向量数据库 | FAISS |
| 数据库 | MySQL |
| 文档处理 | LangChain |

## 📝 API 接口

### 语音识别

```http
POST /api/asr
Content-Type: multipart/form-data

{
  "audio": <audio_file>,
  "format": "wav"
}
```

### 语音合成

```http
POST /api/tts
Content-Type: application/json

{
  "text": "你好，这是测试语音",
  "voice": "zh-CN-XiaoxiaoNeural"
}
```

### 问答接口

```http
POST /api/chat
Content-Type: application/json

{
  "message": "你好",
  "use_rag": true
}
```

## ⚠️ 注意事项

1. **API Key 安全**: 请勿将 API Key 提交到版本控制
2. **模型下载**: 首次使用本地模型需要下载，可能需要较长时间
3. **网络要求**: 使用云端服务需要稳定的网络连接
4. **内存要求**: 本地模型建议至少 8GB 内存

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**开发团队**: AI CRM Team  
**版本**: 1.0.0  
**最后更新**: 2026-06-15