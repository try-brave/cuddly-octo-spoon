# 🤖 AI 多模态智能助手

> 基于大语言模型的桌面端多模态 AI 助手，支持文本对话、图片识别、RAG 文档问答，面向 AI 应用开发学习与实践。

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-orange.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

---

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 💬 多轮对话 | 支持上下文记忆，连续对话不丢失历史 |
| 🖼️ 图片识别（OCR） | 上传图片自动提取文字内容 |
| 📚 RAG 文档问答 | 上传 TXT/PDF/DOCX 文档，基于向量检索精准问答 |
| ⏹️ 流式输出 + 停止生成 | AI 回复逐字显示，随时可中断生成 |
| 🎨 打字动画 | "AI 正在思考..." 动画提示，体验更流畅 |
| 💾 对话历史管理 | 多会话管理，历史记录持久化保存 |
| 🌙 主题切换 | 深色/浅色模式一键切换 |
| 📊 Token 统计 | 实时显示输入输出 Token 消耗量 |

---

## 🛠️ 技术栈

- **语言**: Python 3.10+
- **GUI**: [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
- **LLM 接口**: OpenAI API 兼容格式（支持 Moonshot、DeepSeek 等）
- **RAG 向量检索**: [ChromaDB](https://www.trychroma.com/) + [LangChain](https://www.langchain.com/)
- **文档处理**: PyPDF2、docx2txt
- **OCR**: 视觉模型（通过 MultimodalClient 调用）

---

## 📦 安装运行

### 1. 克隆仓库

```bash
git clone https://github.com/try-brave/cuddly-octo-spoon.git
cd cuddly-octo-spoon
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API Key

复制环境变量模板：

```bash
cp .env.example .env
```

编辑 `.env`，填入你的 API Key：

```env
# 必填：LLM API Key
MOONSHOT_API_KEY=your_api_key_here

# 可选：API Base URL（默认 Moonshot API）
OPENAI_BASE_URL=https://api.moonshot.cn/v1

# 可选：使用的模型名称
MODEL_NAME=moonshot-v1-8k
```

### 4. 运行应用

```bash
python desktop_app.py
```

或直接双击 `run.bat`（Windows）。

---

## 📂 项目结构

```
Multimodal-Assistant/
├── core/                   # 核心模块
│   ├── __init__.py
│   ├── base_client.py      # API 基础客户端
│   ├── chat.py            # 文本对话客户端
│   ├── config.py          # 配置管理（环境变量 + 默认值）
│   ├── history.py         # 对话历史持久化
│   ├── intent.py          # 用户意图识别
│   ├── multimodal.py      # 多模态（图片/OCR）客户端
│   ├── rag.py             # RAG 向量检索管线
│   └── utils.py           # 工具函数
├── data/                   # 数据目录（主题配置等）
├── history/                # 对话历史记录（gitignore）
├── desktop_app.py          # 桌面应用主入口
├── requirements.txt        # Python 依赖清单
├── .env.example           # 环境变量模板
└── README.md
```

---

## 🚀 使用指南

### 文本对话
1. 启动应用，在底部输入框输入消息
2. 按回车或点击「发送」
3. AI 逐字流式回复，可随时点击「停止」中断

### 图片识别（OCR）
1. 点击输入框左侧的 📎 图标
2. 选择图片文件（支持 PNG/JPG/BMP）
3. AI 自动识别并提取图片中的文字

### RAG 文档问答
1. 勾选底部「启用 RAG 文档问答」
2. 点击「上传文档」，选择 TXT/PDF/DOCX 文件
3. 文档自动向量化并存入 ChromaDB
4. 直接提问，AI 基于文档内容作答

---

## 📊 性能参考

> 以下数据基于本地测试环境（Moonshot API，网络良好）

| 指标 | 数值 |
|------|------|
| 短问题响应延迟 | < 3 秒 |
| RAG 向量检索速度 | < 0.1 秒 |
| 长回复生成（流式） | 逐字实时显示 |
| 支持最大上下文长度 | 32K Tokens |

---

## 🔮 开发计划

- [ ] 支持更多文档格式（Markdown、Excel）
- [ ] 对话导出（Markdown / PDF）
- [ ] 插件系统（天气查询、计算器、联网搜索）
- [ ] 多语言界面（中/英）
- [ ] 打包为单文件 exe（PyInstaller）

---

## 📄 许可证

MIT License —— 自由使用、修改和分发。

---

## 👤 作者

**try-brave**

- GitHub: [@try-brave](https://github.com/try-brave)
- 广东工业大学 · 智能制造工程专业

---

> ⭐ 如果这个项目对你有帮助，欢迎 Star！
