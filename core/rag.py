import os
import tempfile
import httpx
from typing import List, Dict, Optional, Any
from chromadb import PersistentClient, EphemeralClient
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, PyPDFLoader, UnstructuredMarkdownLoader, BSHTMLLoader, UnstructuredWordDocumentLoader, CSVLoader
from core.config import Config
from core.chat import ChatClient


class RAGPipeline:
    """
    RAG (Retrieval-Augmented Generation) 端到端管线
    
    流程：文档加载 → 文本分割 → 向量化 → 存储 → 检索 → 生成回复
    
    支持的文档格式：
    - txt: 纯文本
    - md: Markdown
    - pdf: PDF 文档
    - doc/docx: Word 文档
    - html/htm: 网页
    - csv: CSV 表格
    """
    
    def __init__(self):
        """初始化 RAG 管线"""
        # 从配置获取参数
        self.embedding_model = Config.get_embedding_model()
        self.chunk_size = Config.get_rag_chunk_size()
        self.chunk_overlap = Config.get_rag_chunk_overlap()
        
        # 支持的文件格式
        self.supported_formats = ['txt', 'md', 'pdf', 'doc', 'docx', 'html', 'htm', 'csv']
        
        # 初始化向量数据库
        self._init_chromadb()
        
        # 初始化文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?"]
        )
        
        # 初始化聊天客户端
        self.chat_client = ChatClient()
    
    def _init_chromadb(self):
        """初始化 ChromaDB 客户端（云端自动降级为内存模式）"""
        persist_dir = os.path.join(os.path.dirname(__file__), "..", "chromadb")
        
        try:
            os.makedirs(persist_dir, exist_ok=True)
            self.client = PersistentClient(path=persist_dir)
        except Exception:
            # 持久化失败（如 Streamlit Cloud 无文件写入权限），降级为内存模式
            self.client = EphemeralClient()
        
        self.collection = self.client.get_or_create_collection(name="documents")
    
    def _load_document(self, file_path: str) -> str:
        """
        加载文档内容
        
        Args:
            file_path: 文档文件路径
        
        Returns:
            文档内容字符串
        
        Raises:
            ValueError: 不支持的文件格式
        """
        ext = file_path.lower().split('.')[-1]
        
        try:
            if ext == 'txt':
                loader = TextLoader(file_path, encoding='utf-8')
            elif ext == 'pdf':
                loader = PyPDFLoader(file_path)
            elif ext == 'md':
                loader = UnstructuredMarkdownLoader(file_path)
            elif ext in ['html', 'htm']:
                loader = BSHTMLLoader(file_path)
            elif ext in ['doc', 'docx']:
                loader = UnstructuredWordDocumentLoader(file_path)
            elif ext == 'csv':
                loader = CSVLoader(file_path, encoding='utf-8')
            else:
                raise ValueError(f"不支持的文件格式: {ext}")
            
            docs = loader.load()
            return "\n\n".join([doc.page_content for doc in docs])
        except ImportError as e:
            raise ValueError(f"缺少依赖库，请安装: pip install {' '.join([p for p in ['langchain-community', 'pypdf', 'python-docx'] if p not in str(e)])}")
        except Exception as e:
            raise ValueError(f"文档加载失败: {str(e)}")
    
    def _split_text(self, text: str) -> List[str]:
        """
        分割文本为 chunks
        
        Args:
            text: 原始文本
        
        Returns:
            分割后的文本片段列表
        """
        if not text.strip():
            return []
        
        chunks = self.text_splitter.split_text(text)
        # 过滤空片段
        return [chunk.strip() for chunk in chunks if chunk.strip()]
    
    def _create_embedding(self, text: str) -> List[float]:
        """
        创建文本嵌入（使用本地计算的简单哈希作为占位符）
        
        Args:
            text: 文本内容
        
        Returns:
            嵌入向量
        """
        # 使用简单的哈希方法生成嵌入向量（实际应用中应使用真实的嵌入模型）
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        # 生成一个 384 维的简单向量
        vector = []
        for i in range(384):
            vector.append(((hash_val >> (i * 8)) & 0xFF) / 255.0)
        return vector
    
    def add_document(self, file_path: str) -> Dict[str, Any]:
        """
        添加文档到向量库
        
        Args:
            file_path: 文档文件路径
        
        Returns:
            添加结果信息
        """
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return {"success": False, "message": f"文件不存在: {file_path}", "chunks_added": 0}
        
        # 检查文件格式
        ext = file_path.lower().split('.')[-1]
        if ext not in self.supported_formats:
            return {
                "success": False,
                "message": f"不支持的文件格式: {ext}。支持的格式: {', '.join(self.supported_formats)}",
                "chunks_added": 0
            }
        
        try:
            # 加载文档
            text = self._load_document(file_path)
            
            # 检查文档内容是否为空
            if not text or not text.strip():
                return {"success": False, "message": "文档内容为空", "chunks_added": 0}
            
            # 分割文本
            chunks = self._split_text(text)
            
            if not chunks:
                return {"success": False, "message": "无法分割文档内容", "chunks_added": 0}
            
            # 生成嵌入并存储
            ids = []
            embeddings = []
            metadatas = []
            documents = []
            
            file_name = os.path.basename(file_path)
            # 移除文件扩展名
            display_name = os.path.splitext(file_name)[0]
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{file_name}_{i}"
                embedding = self._create_embedding(chunk)
                
                ids.append(chunk_id)
                embeddings.append(embedding)
                metadatas.append({
                    "source": file_name,
                    "display_name": display_name,
                    "extension": ext,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                })
                documents.append(chunk)
            
            # 批量添加到向量库
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents
            )
            
            return {
                "success": True,
                "message": f"文档 '{file_name}' 添加成功",
                "chunks_added": len(chunks),
                "total_chunks": len(chunks),
                "display_name": display_name
            }
        except ValueError as e:
            # 已知错误类型
            return {"success": False, "message": str(e), "chunks_added": 0}
        except Exception as e:
            # 未知错误
            return {"success": False, "message": f"添加文档时发生错误: {str(e)}", "chunks_added": 0}
    
    def add_documents(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        批量添加文档
        
        Args:
            file_paths: 文档文件路径列表
        
        Returns:
            每个文档的添加结果列表
        """
        results = []
        for file_path in file_paths:
            if os.path.exists(file_path):
                results.append(self.add_document(file_path))
            else:
                results.append({
                    "success": False,
                    "message": f"文件不存在: {file_path}",
                    "chunks_added": 0
                })
        return results
    
    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        检索相关文档片段
        
        Args:
            query: 查询文本
            top_k: 返回的最大片段数
        
        Returns:
            检索到的文档片段列表，按相关性排序
        """
        if not query.strip():
            return []
        
        # 生成查询嵌入
        query_embedding = self._create_embedding(query)
        
        # 查询向量库
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        
        # 格式化结果
        retrieved = []
        for i in range(len(results['ids'][0])):
            retrieved.append({
                "id": results['ids'][0][i],
                "content": results['documents'][0][i],
                "metadata": results['metadatas'][0][i],
                "distance": results['distances'][0][i] if results['distances'] else None
            })
        
        return retrieved
    
    def _build_prompt(self, query: str, contexts: List[str]) -> str:
        """
        构建包含上下文的提示词
        
        Args:
            query: 用户查询
            contexts: 检索到的上下文片段
        
        Returns:
            完整的提示词
        """
        if not contexts:
            return f"请回答以下问题：\n{query}"
        
        context_text = "\n\n".join([f"【参考文档{i+1}】\n{ctx}" for i, ctx in enumerate(contexts)])
        
        return f"""
基于以下参考文档回答问题。如果文档中有相关信息，请优先根据文档内容回答；如果文档中没有相关信息，请根据你的知识回答。

参考文档：
{context_text}

问题：
{query}

请给出详细的回答：
"""
    
    def chat_with_context(self, query: str, top_k: int = 3) -> str:
        """
        结合上下文生成回复
        
        Args:
            query: 用户查询
            top_k: 检索的最大片段数
        
        Returns:
            AI 生成的回复
        """
        # 检索相关文档
        retrieved = self.retrieve(query, top_k=top_k)
        
        # 提取上下文内容
        contexts = [item['content'] for item in retrieved]
        
        # 构建提示词
        prompt = self._build_prompt(query, contexts)
        
        # 构建消息列表
        messages = [
            {"role": "system", "content": "你是一个基于文档的问答助手，请根据提供的参考文档回答问题。"},
            {"role": "user", "content": prompt}
        ]
        
        # 调用聊天客户端
        return self.chat_client.chat(messages)
    
    def stream_chat_with_context(self, query: str, top_k: int = 3):
        """
        流式结合上下文生成回复
        
        Args:
            query: 用户查询
            top_k: 检索的最大片段数
        
        Yields:
            流式响应内容
        """
        # 检索相关文档
        retrieved = self.retrieve(query, top_k=top_k)
        
        # 提取上下文内容
        contexts = [item['content'] for item in retrieved]
        
        # 构建提示词
        prompt = self._build_prompt(query, contexts)
        
        # 构建消息列表
        messages = [
            {"role": "system", "content": "你是一个基于文档的问答助手，请根据提供的参考文档回答问题。"},
            {"role": "user", "content": prompt}
        ]
        
        # 调用流式聊天客户端
        yield from self.chat_client.stream_chat(messages)
    
    def clear_database(self) -> bool:
        """
        清空向量库
        
        Returns:
            是否成功清空
        """
        try:
            self.collection.delete(ids=self.collection.get()['ids'])
            return True
        except Exception:
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取向量库统计信息
        
        Returns:
            统计信息字典
        """
        try:
            info = self.collection.get()
            ids = info['ids']
            
            # 统计来源文档
            sources = {}
            for metadata in info['metadatas']:
                source = metadata.get('source', 'unknown')
                if source not in sources:
                    sources[source] = {
                        'count': 0,
                        'display_name': metadata.get('display_name', source),
                        'extension': metadata.get('extension', '')
                    }
                sources[source]['count'] += 1
            
            return {
                "success": True,
                "total_chunks": len(ids),
                "total_documents": len(sources),
                "sources": sources
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"获取统计信息失败: {str(e)}",
                "total_chunks": 0,
                "total_documents": 0,
                "sources": {}
            }
    
    def get_document_list(self) -> List[Dict[str, Any]]:
        """
        获取已上传文档列表
        
        Returns:
            文档列表，每个元素包含文档名、片段数、扩展名
        """
        try:
            stats = self.get_stats()
            if not stats.get("success"):
                return []
            
            docs = []
            for source, info in stats.get("sources", {}).items():
                docs.append({
                    "filename": source,
                    "display_name": info.get("display_name", source),
                    "extension": info.get("extension", ""),
                    "chunks": info.get("count", 0)
                })
            
            # 按文件名排序
            docs.sort(key=lambda x: x["display_name"])
            return docs
        except Exception as e:
            return []
    
    def delete_document(self, file_name: str) -> Dict[str, Any]:
        """
        删除指定文档的所有 chunks
        
        Args:
            file_name: 文件名
        
        Returns:
            删除结果
        """
        try:
            # 获取所有包含该文件名的 ids
            info = self.collection.get()
            ids_to_delete = []
            
            for i, metadata in enumerate(info['metadatas']):
                if metadata.get('source') == file_name:
                    ids_to_delete.append(info['ids'][i])
            
            if ids_to_delete:
                self.collection.delete(ids=ids_to_delete)
                return {
                    "success": True,
                    "message": f"文档 '{file_name}' 删除成功",
                    "chunks_deleted": len(ids_to_delete)
                }
            else:
                return {
                    "success": False,
                    "message": f"未找到文档 '{file_name}'",
                    "chunks_deleted": 0
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"删除失败: {str(e)}",
                "chunks_deleted": 0
            }
