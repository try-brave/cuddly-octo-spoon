# 架构设计文档

## 整体架构

```mermaid
graph TB
    subgraph UI["用户界面层 (Streamlit)"]
        A[聊天标签页]
        B[图片标签页]
        C[RAG标签页]
        D[侧边栏]
    end
    
    subgraph Core["核心业务层"]
        E[ChatClient<br/>聊天客户端]
        F[MultimodalClient<br/>多模态客户端]
        G[RAGPipeline<br/>RAG管线]
        H[IntentRouter<br/>意图路由]
        I[HistoryManager<br/>历史管理]
        J[Config<br/>配置管理]
        K[Utils<br/>工具函数]
    end
    
    subgraph External["外部服务层"]
        L[Moonshot API]
        M[ChromaDB]
        N[FileSystem]
    end
    
    A --> E
    B --> F
    C --> G
    D --> I
    
    E --> K
    F --> K
    G --> K
    
    K --> J
    
    E --> L
    F --> L
    G --> L
    G --> M
    
    I --> N
```

## 数据流架构

```mermaid
sequenceDiagram
    participant U as 用户
    participant S as Streamlit UI
    participant R as IntentRouter
    participant C as ChatClient
    participant G as RAGPipeline
    participant A as Moonshot API
    
    U->>S: 输入问题
    S->>R: 路由意图
    
    alt RAG模式启用
        R->>G: 检索文档
        G->>G: 向量相似度搜索
        G-->>S: 返回相关文档
        S->>C: 构建增强Prompt
    else 普通模式
        R-->>S: 返回意图结果
    end
    
    S->>C: 发送请求
    C->>A: API调用
    A-->>C: 流式响应
    C-->>S: 逐Token返回
    S-->>U: 实时显示
```

## 模块依赖关系

```mermaid
graph LR
    subgraph 核心模块
        config[config.py]
        utils[utils.py]
        chat[chat.py]
        multimodal[multimodal.py]
        rag[rag.py]
        intent[intent.py]
        history[history.py]
    end
    
    chat --> config
    chat --> utils
    multimodal --> config
    multimodal --> utils
    rag --> config
    rag --> utils
    intent --> config
    history --> config
```

## RAG 管线架构

```mermaid
graph LR
    subgraph 文档处理
        A[上传文档] --> B[文档加载器]
        B --> C[文本分割器]
        C --> D[文本块]
    end
    
    subgraph 向量化
        D --> E[Embedding模型]
        E --> F[向量]
    end
    
    subgraph 存储
        F --> G[ChromaDB]
    end
    
    subgraph 检索
        H[用户问题] --> I[问题向量化]
        I --> J[相似度搜索]
        J --> K[Top-K文档块]
    end
    
    subgraph 生成
        K --> L[构建Prompt]
        L --> M[LLM生成]
        M --> N[回答]
    end
    
    G --> J
```

## 会话状态管理

```mermaid
stateDiagram-v2
    [*] --> 初始化
    初始化 --> 加载历史
    加载历史 --> 等待输入
    
    等待输入 --> 处理消息: 用户输入
    处理消息 --> 意图识别
    意图识别 --> RAG检索: RAG模式
    意图识别 --> 直接响应: 普通模式
    
    RAG检索 --> 流式生成
    直接响应 --> 流式生成
    流式生成 --> 保存历史
    保存历史 --> 等待输入
    
    等待输入 --> 新建会话: 点击新建
    新建会话 --> 保存历史
    等待输入 --> 切换会话: 选择其他会话
    切换会话 --> 加载历史
```

## 错误处理流程

```mermaid
graph TD
    A[API调用] --> B{成功?}
    B -->|是| C[返回结果]
    B -->|否| D{错误类型}
    
    D -->|温度错误| E[使用默认温度重试]
    D -->|网络错误| F[等待后重试]
    D -->|认证错误| G[抛出APIKeyError]
    D -->|其他错误| H[抛出ServiceError]
    
    E --> I{重试成功?}
    F --> I
    I -->|是| C
    I -->|否| J[达到最大重试次数]
    J --> H
    
    G --> K[UI显示错误提示]
    H --> K
```

## 文件结构说明

```
Multimodal-Assistant/
├── app.py                    # 主入口，UI渲染
├── core/
│   ├── __init__.py          # 模块导出，统一接口
│   ├── config.py            # 配置管理，环境变量读取
│   ├── chat.py              # 聊天客户端，API调用封装
│   ├── multimodal.py        # 多模态客户端，图片处理
│   ├── rag.py               # RAG管线，文档问答
│   ├── intent.py            # 意图路由，关键词匹配
│   ├── history.py           # 历史管理，JSON持久化
│   └── utils.py             # 工具函数，重试逻辑
├── .streamlit/
│   └── config.toml          # Streamlit配置
├── history/                  # 对话历史存储
├── chromadb/                 # 向量数据库
└── docs/                     # 文档目录
```

## 关键设计决策

### 1. API 调用重试机制

采用带温度错误特殊处理的重试策略：
- 网络错误：指数退避重试
- 温度错误：自动使用默认温度 1.0 重试
- 认证错误：直接抛出，不重试

### 2. 配置集中管理

所有配置通过 `Config` 类统一管理：
- 支持环境变量覆盖
- 提供默认值
- 类型安全的访问方法

### 3. 模块化设计

每个功能独立成模块：
- 低耦合：模块间通过接口交互
- 高内聚：相关功能集中在同一模块
- 易测试：可独立测试每个模块

### 4. 流式输出

使用生成器实现流式输出：
- 实时显示 AI 回复
- 提升用户体验
- 减少等待感知时间
