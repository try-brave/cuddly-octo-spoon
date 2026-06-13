# 从零打造 AI 多模态助手（上篇）

> 架构设计 + API 封装 + 多轮对话实现

## 前言

在 AI 应用开发中，如何设计一个可扩展、易维护的多模态助手？本文将从架构设计、API 封装、多轮对话三个维度，分享从零打造 AI 助手的实践经验。

## 一、架构设计

### 1.1 分层架构

我们采用经典的分层架构，将系统分为三层：

```
┌─────────────────────────────────────────┐
│           UI Layer (Streamlit)          │  用户界面层
├─────────────────────────────────────────┤
│           Core Layer (Python)           │  业务逻辑层
├─────────────────────────────────────────┤
│        External Services (API/DB)       │  外部服务层
└─────────────────────────────────────────┘
```

**设计原则：**
- UI 层只负责渲染，不包含业务逻辑
- Core 层封装所有业务逻辑，可独立测试
- External 层通过接口抽象，便于替换实现

### 1.2 模块划分

```
core/
├── config.py      # 配置管理
├── chat.py        # 聊天客户端
├── multimodal.py  # 多模态客户端
├── rag.py         # RAG 管线
├── intent.py      # 意图路由
├── history.py     # 历史管理
└── utils.py       # 工具函数
```

每个模块职责单一，通过 `__init__.py` 统一导出：

```python
# core/__init__.py
from core.config import Config
from core.chat import ChatClient
from core.multimodal import MultimodalClient
from core.rag import RAGPipeline
```

## 二、API 封装

### 2.1 配置管理

首先，将所有配置集中管理：

```python
# core/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    @staticmethod
    def get_api_key() -> str:
        key = os.getenv("MOONSHOT_API_KEY")
        if not key:
            raise ValueError("请设置 MOONSHOT_API_KEY 环境变量")
        return key
    
    @staticmethod
    def get_base_url() -> str:
        return os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1")
    
    @staticmethod
    def get_default_model() -> str:
        return os.getenv("DEFAULT_MODEL", "moonshot-v1-8k")
    
    @staticmethod
    def get_timeout() -> int:
        return int(os.getenv("TIMEOUT", "60"))
```

**优势：**
- 环境变量与代码解耦
- 提供默认值，降低配置复杂度
- 类型安全的访问方法

### 2.2 聊天客户端封装

封装 OpenAI 兼容的 API 调用：

```python
# core/chat.py
from openai import OpenAI
from core.config import Config

class ChatClient:
    def __init__(self, provider: str = "moonshot"):
        self.client = OpenAI(
            api_key=Config.get_api_key(),
            base_url=Config.get_base_url()
        )
        self.default_model = Config.get_default_model()
    
    def chat(self, messages: List[Dict], temperature: float = 1.0) -> str:
        """发送聊天请求"""
        completion = self.client.chat.completions.create(
            model=self.default_model,
            messages=messages,
            temperature=temperature
        )
        return completion.choices[0].message.content
    
    def stream_chat(self, messages: List[Dict], temperature: float = 1.0):
        """流式聊天"""
        stream = self.client.chat.completions.create(
            model=self.default_model,
            messages=messages,
            temperature=temperature,
            stream=True
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
```

### 2.3 重试机制

API 调用可能失败，需要实现重试机制：

```python
# core/utils.py
import time
from typing import Callable, Any

def execute_with_retry_temp_fallback(
    api_call: Callable[[], Any],
    temperature: float,
    max_retries: int = 2,
    on_temperature_retry: Callable = None
) -> Any:
    """
    带温度错误特殊处理的重试逻辑
    
    某些模型只支持特定温度值，遇到温度错误时自动使用 1.0 重试
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            return api_call()
        except Exception as e:
            last_error = e
            error_msg = str(e).lower()
            
            # 温度错误特殊处理
            if "temperature" in error_msg or "温度" in error_msg:
                if on_temperature_retry:
                    return on_temperature_retry(1.0)
            
            # 网络错误等待后重试
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
    
    raise last_error
```

**关键点：**
- 温度错误：某些模型只支持特定温度，自动降级到 1.0
- 网络错误：指数退避重试
- 认证错误：直接抛出，不重试

### 2.4 异常处理

定义自定义异常，提供清晰的错误信息：

```python
# core/chat.py
class ChatError(Exception):
    """聊天错误基类"""
    pass

class APIKeyError(ChatError):
    """API 密钥错误"""
    pass

class NetworkError(ChatError):
    """网络错误"""
    pass

class ServiceError(ChatError):
    """服务错误"""
    pass
```

使用时统一捕获：

```python
try:
    response = client.chat(messages)
except APIKeyError:
    st.error("API 密钥无效，请检查配置")
except NetworkError:
    st.error("网络连接失败，请稍后重试")
except ServiceError as e:
    st.error(f"服务错误: {str(e)}")
```

## 三、多轮对话实现

### 3.1 消息格式

OpenAI API 使用消息列表格式：

```python
messages = [
    {"role": "system", "content": "你是一个友好的助手"},
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "你好！有什么可以帮助你的？"},
    {"role": "user", "content": "今天天气怎么样？"}
]
```

### 3.2 上下文管理

多轮对话需要管理上下文，但上下文过长会消耗大量 Token：

```python
# core/chat.py
class ChatClient:
    def __init__(self):
        # ... 初始化代码
        self.max_history_tokens = Config.get_max_history_tokens()
    
    def _truncate_history(self, messages: List[Dict]) -> List[Dict]:
        """截断历史记录，保持在 Token 限制内"""
        # 保留系统消息
        system_msg = None
        if messages and messages[0]["role"] == "system":
            system_msg = messages[0]
            messages = messages[1:]
        
        # 从最新的消息开始保留
        total_tokens = 0
        truncated = []
        
        for msg in reversed(messages):
            msg_tokens = count_tokens(msg["content"])
            if total_tokens + msg_tokens > self.max_history_tokens:
                break
            truncated.insert(0, msg)
            total_tokens += msg_tokens
        
        if system_msg:
            truncated.insert(0, system_msg)
        
        return truncated
```

### 3.3 历史持久化

将对话历史保存到 JSON 文件：

```python
# core/history.py
import json
import os
from datetime import datetime

def save_history(messages: List[Dict], filepath: str) -> None:
    """保存对话历史"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

def load_history(filepath: str) -> List[Dict]:
    """加载对话历史"""
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def get_all_sessions() -> List[Dict]:
    """获取所有会话"""
    history_dir = Config.get_history_dir()
    sessions = []
    
    for filename in os.listdir(history_dir):
        if filename.endswith(".json"):
            filepath = os.path.join(history_dir, filename)
            messages = load_history(filepath)
            if messages:
                # 从第一条用户消息生成标题
                title = next(
                    (m["content"][:30] for m in messages if m["role"] == "user"),
                    "新对话"
                )
                sessions.append({
                    "title": title,
                    "filepath": filepath,
                    "mtime": os.path.getmtime(filepath)
                })
    
    return sorted(sessions, key=lambda x: x["mtime"], reverse=True)
```

### 3.4 流式输出

流式输出提升用户体验，实现"打字机"效果：

```python
# app.py
def render_chat_tab():
    # ... 显示历史消息
    
    prompt = st.chat_input("说点什么...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("assistant"):
            # 流式输出
            response_stream = st.session_state.client.stream_chat(
                st.session_state.messages
            )
            full_response = st.write_stream(response_stream)
        
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        save_history(st.session_state.messages, st.session_state.current_session)
```

**关键点：**
- `st.write_stream()` 自动处理流式输出
- 需要收集完整响应用于保存历史

## 四、总结

本文介绍了 AI 多模态助手的架构设计、API 封装和多轮对话实现：

1. **分层架构**：UI 层、Core 层、External 层分离
2. **配置管理**：集中管理，环境变量覆盖
3. **API 封装**：重试机制、异常处理、流式输出
4. **多轮对话**：上下文管理、历史持久化

下篇将深入讲解 RAG 管线的实现，包括文档处理、向量检索和增强生成。

---

**完整代码：** [GitHub 仓库地址]

**相关文章：**
- [下篇：RAG 从零到跑通](./part2-rag-pipeline.md)
