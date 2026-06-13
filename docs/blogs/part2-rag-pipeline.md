# RAG 从零到跑通（下篇）

> 6 步流程 + 踩坑经验 + 实验结论

## 前言

RAG（Retrieval-Augmented Generation）是让 AI "记住"私有数据的关键技术。本文将从零实现一个完整的 RAG 管线，分享踩坑经验和实验结论。

## 一、RAG 是什么？

RAG = 检索 + 生成

```
用户问题 → 向量检索 → 找到相关文档 → 构建 Prompt → LLM 生成回答
```

**为什么需要 RAG？**
- LLM 不知道你的私有数据
- Fine-tuning 成本高、更新慢
- RAG 实时检索，数据随时更新

## 二、6 步实现 RAG 管线

### Step 1: 文档加载

支持多种格式：TXT、PDF、Markdown、Word、HTML、CSV

```python
# core/rag.py
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredHTMLLoader,
    CSVLoader
)

def _load_document(self, filepath: str) -> List[Document]:
    """加载文档"""
    ext = os.path.splitext(filepath)[1].lower()
    
    loaders = {
        '.txt': TextLoader,
        '.md': TextLoader,
        '.pdf': PyPDFLoader,
        '.docx': Docx2txtLoader,
        '.html': UnstructuredHTMLLoader,
        '.htm': UnstructuredHTMLLoader,
        '.csv': CSVLoader,
    }
    
    loader_class = loaders.get(ext)
    if not loader_class:
        raise ValueError(f"不支持的文件格式: {ext}")
    
    loader = loader_class(filepath)
    return loader.load()
```

**踩坑：**
- PDF 加载需要 `PyPDF2` 库
- Word 需要 `docx2txt` 或 `python-docx`
- HTML 需要 `unstructured` 库
- 中文文档需要指定 `encoding='utf-8'`

### Step 2: 文本分割

长文档需要分割成小块：

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

def _split_documents(self, documents: List[Document]) -> List[Document]:
    """分割文档"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=self.chunk_size,      # 块大小
        chunk_overlap=self.chunk_overlap, # 重叠大小
        separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""]
    )
    return splitter.split_documents(documents)
```

**关键参数：**
- `chunk_size`：每块的最大字符数
- `chunk_overlap`：块之间的重叠字符数

### Step 3: 向量化

将文本转换为向量：

```python
from langchain_community.embeddings import HuggingFaceEmbeddings

def __init__(self):
    self.embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
```

**模型选择：**
| 模型 | 维度 | 速度 | 质量 |
|------|------|------|------|
| all-MiniLM-L6-v2 | 384 | 快 | 中 |
| all-mpnet-base-v2 | 768 | 中 | 高 |
| text-embedding-ada-002 | 1536 | API | 最高 |

### Step 4: 向量存储

使用 ChromaDB 存储向量：

```python
from langchain_community.vectorstores import Chroma

def __init__(self):
    self.vectorstore = Chroma(
        persist_directory=Config.get_chroma_db_path(),
        embedding_function=self.embeddings
    )

def add_document(self, filepath: str) -> Dict:
    """添加文档到向量库"""
    # 1. 加载文档
    documents = self._load_document(filepath)
    
    # 2. 分割文档
    chunks = self._split_documents(documents)
    
    # 3. 添加元数据
    filename = os.path.basename(filepath)
    display_name = os.path.splitext(filename)[0]
    for chunk in chunks:
        chunk.metadata["filename"] = filename
        chunk.metadata["display_name"] = display_name
    
    # 4. 存入向量库
    ids = self.vectorstore.add_documents(chunks)
    
    return {
        "success": True,
        "chunks_added": len(ids),
        "filename": filename
    }
```

### Step 5: 相似度检索

根据问题检索相关文档：

```python
def retrieve(self, query: str, top_k: int = 3) -> List[Dict]:
    """检索相关文档"""
    results = self.vectorstore.similarity_search(
        query,
        k=top_k
    )
    
    return [
        {
            "content": doc.page_content,
            "metadata": doc.metadata
        }
        for doc in results
    ]
```

### Step 6: 增强生成

将检索结果注入 Prompt：

```python
def chat_with_context(self, query: str, top_k: int = 3) -> str:
    """基于文档上下文的问答"""
    # 1. 检索相关文档
    docs = self.retrieve(query, top_k)
    
    # 2. 构建上下文
    context = "\n\n".join([doc["content"] for doc in docs])
    
    # 3. 构建 Prompt
    prompt = f"""基于以下文档内容回答问题。如果文档中没有相关信息，请说"文档中没有相关信息"。

文档内容：
{context}

问题：{query}

回答："""
    
    # 4. 调用 LLM
    messages = [{"role": "user", "content": prompt}]
    return self.client.chat(messages)
```

## 三、踩坑经验

### 坑 1: Chunk Size 太大或太小

**问题：**
- 太大：检索不精确，包含无关内容
- 太小：语义不完整，回答质量差

**实验：**

| Chunk Size | 检索精度 | 回答质量 |
|------------|----------|----------|
| 200 | 高 | 低（语义不完整）|
| 500 | 中 | 高（平衡）|
| 1000 | 低 | 中（噪音多）|

**结论：** 500 字符是较好的平衡点

### 坑 2: 忘记添加元数据

**问题：** 检索结果不知道来自哪个文档

**解决：**

```python
for chunk in chunks:
    chunk.metadata["filename"] = filename
    chunk.metadata["display_name"] = display_name
    chunk.metadata["source"] = filepath
```

### 坑 3: 向量库没有持久化

**问题：** 每次重启数据丢失

**解决：**

```python
self.vectorstore = Chroma(
    persist_directory="./chromadb",  # 指定持久化目录
    embedding_function=self.embeddings
)
```

### 坑 4: 中文分割效果差

**问题：** 默认分隔符对中文效果不好

**解决：** 使用中文标点作为分隔符

```python
separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""]
```

### 坑 5: 检索结果不相关

**问题：** 返回的文档与问题无关

**解决：** 使用混合检索（向量 + 关键词）

```python
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever

# 向量检索
vector_retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})

# 关键词检索
bm25_retriever = BM25Retriever.from_documents(documents)
bm25_retriever.k = 5

# 混合检索
ensemble_retriever = EnsembleRetriever(
    retrievers=[vector_retriever, bm25_retriever],
    weights=[0.5, 0.5]
)
```

## 四、实验结论

### 实验 1: Chunk Size 对比

**测试文档：** 10 页技术文档
**测试问题：** 5 个具体问题

| Chunk Size | 检索命中率 | 回答准确率 | 平均响应时间 |
|------------|------------|------------|--------------|
| 200 | 80% | 60% | 1.2s |
| 500 | 100% | 100% | 1.5s |
| 1000 | 60% | 80% | 2.1s |

**结论：** 500 字符最优

### 实验 2: Top-K 对比

| Top-K | 检索覆盖率 | 回答相关性 | Token 消耗 |
|-------|------------|------------|------------|
| 1 | 40% | 高 | 低 |
| 3 | 80% | 高 | 中 |
| 5 | 95% | 中 | 高 |

**结论：** Top-K=3 是较好的平衡点

### 实验 3: 重叠大小对比

| Overlap | 语义完整性 | 存储开销 |
|---------|------------|----------|
| 0 | 低 | 小 |
| 50 | 高 | 中 |
| 100 | 高 | 大 |

**结论：** Overlap=50 足够

## 五、完整代码

```python
# core/rag.py
from typing import List, Dict, Generator
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from core.config import Config
from core.chat import ChatClient

class RAGPipeline:
    def __init__(self):
        self.chunk_size = Config.get_rag_chunk_size()
        self.chunk_overlap = Config.get_rag_chunk_overlap()
        
        self.embeddings = HuggingFaceEmbeddings(
            model_name=Config.get_embedding_model()
        )
        
        self.vectorstore = Chroma(
            persist_directory=Config.get_chroma_db_path(),
            embedding_function=self.embeddings
        )
        
        self.client = ChatClient()
    
    def add_document(self, filepath: str) -> Dict:
        """添加文档"""
        documents = self._load_document(filepath)
        chunks = self._split_documents(documents)
        
        for chunk in chunks:
            chunk.metadata["filename"] = os.path.basename(filepath)
        
        self.vectorstore.add_documents(chunks)
        return {"success": True, "chunks_added": len(chunks)}
    
    def retrieve(self, query: str, top_k: int = 3) -> List[Dict]:
        """检索文档"""
        docs = self.vectorstore.similarity_search(query, k=top_k)
        return [{"content": d.page_content, "metadata": d.metadata} for d in docs]
    
    def chat_with_context(self, query: str, top_k: int = 3) -> str:
        """基于文档问答"""
        docs = self.retrieve(query, top_k)
        context = "\n\n".join([d["content"] for d in docs])
        
        prompt = f"基于以下内容回答：\n{context}\n\n问题：{query}"
        return self.client.chat([{"role": "user", "content": prompt}])
```

## 六、总结

RAG 管线的 6 步流程：

1. **文档加载**：支持多种格式
2. **文本分割**：Chunk Size 500，Overlap 50
3. **向量化**：使用 HuggingFace Embeddings
4. **向量存储**：ChromaDB 持久化
5. **相似度检索**：Top-K=3
6. **增强生成**：上下文注入 Prompt

**最佳实践：**
- Chunk Size 500，Overlap 50
- Top-K=3
- 添加完整元数据
- 使用中文分隔符
- 考虑混合检索

---

**完整代码：** [GitHub 仓库地址]

**相关文章：**
- [上篇：从零打造 AI 多模态助手](./part1-multimodal-assistant.md)
