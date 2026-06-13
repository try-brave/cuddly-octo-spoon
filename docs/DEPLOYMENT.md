# Streamlit Cloud 部署指南

## 前置条件

1. GitHub 账号
2. Moonshot API Key（从 [Moonshot AI](https://platform.moonshot.cn/) 获取）
3. 项目代码已推送到 GitHub 仓库

## 部署步骤

### 1. 准备 GitHub 仓库

确保你的仓库包含以下文件：

```
Multimodal-Assistant/
├── app.py                 # 主应用
├── requirements.txt       # Python 依赖
├── packages.txt           # 系统依赖（可选）
├── .streamlit/
│   └── config.toml        # Streamlit 配置
├── core/                  # 核心模块
│   ├── __init__.py
│   ├── config.py
│   ├── chat.py
│   ├── multimodal.py
│   ├── rag.py
│   ├── intent.py
│   ├── history.py
│   └── utils.py
└── .env.example           # 环境变量示例
```

**重要：** 确保 `.env` 文件没有被提交到仓库（已在 `.gitignore` 中排除）。

### 2. 登录 Streamlit Cloud

1. 访问 [share.streamlit.io](https://share.streamlit.io/)
2. 使用 GitHub 账号登录

### 3. 创建新应用

1. 点击 **"New app"** 按钮
2. 填写以下信息：
   - **Repository**: 选择你的 GitHub 仓库
   - **Branch**: `main` 或 `master`
   - **Main file path**: `app.py`
3. 点击 **"Deploy!"**

### 4. 配置 Secrets

部署后，需要配置 API Key：

1. 在应用页面点击 **"Settings"**（右上角）
2. 选择 **"Secrets"** 标签
3. 添加以下内容：

```toml
MOONSHOT_API_KEY = "your-api-key-here"
MOONSHOT_BASE_URL = "https://api.moonshot.cn/v1"
DEFAULT_MODEL = "kimi-k2.5"
```

4. 点击 **"Save"**
5. 应用会自动重新部署

### 5. 验证部署

访问应用 URL，确认：
- 应用正常加载
- 聊天功能正常
- 没有错误提示

## 配置说明

### Secrets 配置项

| 配置项 | 必填 | 说明 | 默认值 |
|--------|------|------|--------|
| MOONSHOT_API_KEY | 是 | Moonshot API 密钥 | 无 |
| MOONSHOT_BASE_URL | 否 | API 基础 URL | https://api.moonshot.cn/v1 |
| DEFAULT_MODEL | 否 | 默认模型 | moonshot-v1-8k |
| DEFAULT_TEMPERATURE | 否 | 温度参数 | 1.0 |
| MAX_HISTORY_TOKENS | 否 | 历史记录最大 Token | 1000 |
| RAG_CHUNK_SIZE | 否 | RAG 文本块大小 | 500 |
| RAG_CHUNK_OVERLAP | 否 | RAG 文本块重叠 | 50 |

### 完整 Secrets 示例

```toml
# API 配置
MOONSHOT_API_KEY = "sk-xxxxxxxxxxxxxxxx"
MOONSHOT_BASE_URL = "https://api.moonshot.cn/v1"
DEFAULT_MODEL = "kimi-k2.5"

# 超时配置
API_TIMEOUT = "60"
MAX_RETRY_ATTEMPTS = "2"

# 上下文配置
MAX_HISTORY_TOKENS = "1000"
MAX_HISTORY_MESSAGES = "20"

# RAG 配置
RAG_CHUNK_SIZE = "500"
RAG_CHUNK_OVERLAP = "50"
RAG_TOP_K = "3"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
```

## 常见问题

### 1. 部署失败：ModuleNotFoundError

**原因：** 缺少依赖

**解决：** 检查 `requirements.txt` 是否包含所有需要的包

### 2. API Key 错误

**原因：** Secrets 未正确配置

**解决：**
1. 确认 Secrets 中 `MOONSHOT_API_KEY` 已设置
2. 确认 API Key 格式正确（以 `sk-` 开头）
3. 重新保存 Secrets 触发重新部署

### 3. 应用启动慢

**原因：** 首次部署需要下载模型文件

**解决：** 等待几分钟，后续访问会更快

### 4. RAG 功能不可用

**原因：** ChromaDB 需要持久化存储

**解决：** Streamlit Cloud 不支持持久化存储，RAG 功能在云端可能受限。建议：
- 使用外部向量数据库（如 Pinecone、Weaviate）
- 或在本地运行 RAG 功能

### 5. 历史记录丢失

**原因：** Streamlit Cloud 不支持持久化文件存储

**解决：**
- 使用外部数据库（如 MongoDB、PostgreSQL）
- 或接受历史记录在应用重启后丢失

## 本地开发

### 1. 克隆仓库

```bash
git clone https://github.com/your-username/Multimodal-Assistant.git
cd Multimodal-Assistant
```

### 2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key
```

### 5. 运行应用

```bash
streamlit run app.py
```

## 更新部署

当你推送新的代码到 GitHub 后：

1. Streamlit Cloud 会自动检测更新
2. 自动重新部署应用
3. Secrets 配置会保留

如果需要手动触发重新部署：
1. 访问应用设置页面
2. 点击 **"Reboot app"**

## 资源限制

Streamlit Cloud 免费版限制：

| 资源 | 限制 |
|------|------|
| 内存 | 1 GB |
| CPU | 1 核 |
| 存储 | 不持久化 |
| 带宽 | 有限制 |

如果需要更多资源，考虑升级到 Streamlit Cloud 付费版或使用其他云平台。
