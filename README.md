# Multimodal Assistant

基于 Moonshot AI 的多模态 AI 助手，支持聊天、图片问答、RAG 文档问答等功能。

**[在线演示](https://share.streamlit.io/)** | **[部署指南](docs/DEPLOYMENT.md)**

## 功能特性

- **多轮对话**：支持上下文保持的流畅对话体验
- **流式输出**：实时显示 AI 回复，提升用户体验
- **图片问答**：上传图片进行 OCR 识别或图片内容分析
- **RAG 文档问答**：上传文档后基于内容进行智能问答
- **会话管理**：支持新建、切换、删除对话历史
- **Token 统计**：实时显示 Token 消耗情况
- **意图识别**：自动识别用户意图，提供智能响应

## 项目结构

```
Multimodal-Assistant/
├── app.py                 # Streamlit 应用主入口
├── requirements.txt       # Python 依赖
├── .env.example          # 环境变量示例
├── .streamlit/
│   └── config.toml       # Streamlit 主题配置
├── core/
│   ├── __init__.py       # 模块导出
│   ├── config.py         # 配置管理
│   ├── chat.py           # 聊天客户端
│   ├── multimodal.py     # 多模态客户端
│   ├── rag.py            # RAG 管线
│   ├── intent.py         # 意图路由
│   ├── history.py        # 历史记录管理
│   └── utils.py          # 工具函数
├── history/              # 对话历史存储
├── chromadb/             # 向量数据库
└── docs/                 # 文档
    ├── ARCHITECTURE.md   # 架构设计
    └── blogs/            # 技术博客
        ├── part1-multimodal-assistant.md
        └── part2-rag-pipeline.md
```

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-username/Multimodal-Assistant.git
cd Multimodal-Assistant
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 Moonshot API Key
```

### 4. 运行应用

```bash
streamlit run app.py
```

## 配置说明

在 `.env` 文件中配置以下环境变量：

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| MOONSHOT_API_KEY | Moonshot API 密钥 | 必填 |
| MOONSHOT_BASE_URL | API 基础 URL | https://api.moonshot.cn/v1 |
| DEFAULT_MODEL | 默认模型 | moonshot-v1-8k |
| DEFAULT_TEMPERATURE | 默认温度参数 | 1.0 |
| MAX_HISTORY_TOKENS | 历史记录最大 Token 数 | 4000 |
| RAG_CHUNK_SIZE | RAG 文本分割块大小 | 500 |
| RAG_CHUNK_OVERLAP | RAG 文本分割块重叠 | 50 |

## 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit UI (app.py)                     │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────────┐ │
│  │  聊天   │  │  图片   │  │   RAG   │  │     会话管理        │ │
│  └────┬────┘  └────┬────┘  └────┬────┘  └─────────────────────┘ │
└───────┼────────────┼────────────┼───────────────────────────────┘
        │            │            │
┌───────┴────────────┴────────────┴───────────────────────────────┐
│                         Core Layer                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ ChatClient  │  │Multimodal   │  │ RAGPipeline │              │
│  │             │  │  Client     │  │             │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                      │
│  ┌──────┴────────────────┴────────────────┴──────┐              │
│  │              Utils (重试/剪贴板/工具)          │              │
│  └───────────────────────────────────────────────┘              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Config    │  │   Intent    │  │   History   │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
        │                │                │
┌───────┴────────────────┴────────────────┴───────────────────────┐
│                      External Services                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Moonshot API│  │  ChromaDB   │  │ FileSystem  │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

## 核心模块

### ChatClient - 聊天客户端

支持多轮对话和流式输出，自动处理 API 重试和温度参数错误。

```python
from core import ChatClient

client = ChatClient()
response = client.chat([{"role": "user", "content": "你好"}])
```

### MultimodalClient - 多模态客户端

支持图片问答和 OCR 功能。

```python
from core import MultimodalClient

client = MultimodalClient()
# OCR 识别
text = client.ocr_image(image_path="image.png")
# 图片问答
response = client.chat_with_image(
    messages=[{"role": "user", "content": "描述这张图片"}],
    image_path="image.png"
)
```

### RAGPipeline - RAG 管线

支持文档上传、向量检索和基于文档的问答。

```python
from core import RAGPipeline

rag = RAGPipeline()
# 添加文档
rag.add_document("document.pdf")
# 检索相关内容
results = rag.retrieve("什么是 RAG?")
# 基于文档问答
response = rag.chat_with_context("文档的主要内容是什么?")
```

## 技术栈

- **前端**：Streamlit
- **后端**：Python 3.9+
- **AI API**：Moonshot AI (OpenAI 兼容)
- **向量数据库**：ChromaDB
- **嵌入模型**：sentence-transformers (all-MiniLM-L6-v2)
- **文档处理**：LangChain

## 许可证

MIT License
