import os
from typing import Optional
from dotenv import load_dotenv

# 加载 .env 文件（本地开发）
load_dotenv()

# 尝试导入 streamlit secrets（云端部署）
try:
    import streamlit as st
    _has_streamlit = True
except ImportError:
    _has_streamlit = False


def _get_secret(key: str, default: str = None) -> Optional[str]:
    """
    获取配置值，优先从 Streamlit Secrets 读取，其次从环境变量读取
    
    Args:
        key: 配置键名
        default: 默认值
    
    Returns:
        配置值
    """
    # 优先从 Streamlit Secrets 读取（云端部署）
    if _has_streamlit:
        try:
            if hasattr(st, 'secrets') and key in st.secrets:
                return st.secrets[key]
        except Exception:
            pass
    
    # 其次从环境变量读取（本地开发）
    return os.getenv(key, default)


class Config:
    """
    统一配置管理类
    
    支持从以下来源读取配置（按优先级）：
    1. Streamlit Secrets（云端部署）
    2. 环境变量 / .env 文件（本地开发）
    """
    
    # ==================== API 配置 ====================
    
    @staticmethod
    def get_api_key() -> str:
        """获取 API Key"""
        key = _get_secret("MOONSHOT_API_KEY")
        if not key:
            raise ValueError("MOONSHOT_API_KEY 未配置。本地开发请在 .env 文件中设置，云端部署请在 Streamlit Secrets 中设置。")
        return key
    
    @staticmethod
    def get_base_url() -> str:
        """获取 API 基础 URL"""
        return _get_secret("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1")
    
    @staticmethod
    def get_default_model() -> str:
        """获取默认模型名称"""
        return _get_secret("DEFAULT_MODEL", "kimi-k2.5")
    
    # ==================== 超时配置 ====================
    
    @staticmethod
    def get_timeout() -> int:
        """获取超时时间（秒）"""
        return int(_get_secret("API_TIMEOUT", "60"))
    
    @staticmethod
    def get_max_retries() -> int:
        """获取最大重试次数"""
        return int(_get_secret("MAX_RETRY_ATTEMPTS", "2"))
    
    # ==================== 上下文配置 ====================
    
    @staticmethod
    def get_max_history_tokens() -> int:
        """获取历史对话最大 token 数"""
        return int(_get_secret("MAX_HISTORY_TOKENS", "1000"))
    
    @staticmethod
    def get_max_history_messages() -> int:
        """获取历史对话最大消息数"""
        return int(_get_secret("MAX_HISTORY_MESSAGES", "20"))
    
    # ==================== 系统提示词 ====================
    
    @staticmethod
    def get_system_prompt() -> str:
        """获取系统提示词"""
        return _get_secret(
            "SYSTEM_PROMPT",
            "你是 Kimi，由 Moonshot AI 提供的中文人工智能助手。你会为用户提供安全、有帮助、准确的中文回答。"
        )
    
    # ==================== 温度配置 ====================
    
    @staticmethod
    def get_default_temperature() -> float:
        """获取默认温度参数"""
        return float(_get_secret("DEFAULT_TEMPERATURE", "1.0"))
    
    # ==================== 历史记录配置 ====================
    
    @staticmethod
    def get_history_dir() -> str:
        """获取历史记录保存目录"""
        return _get_secret("HISTORY_DIR", "history")
    
    @staticmethod
    def get_history_filename() -> str:
        """获取默认历史记录文件名"""
        return _get_secret("HISTORY_FILENAME", "chat_history.json")
    
    @staticmethod
    def get_export_dir() -> str:
        """获取导出文件保存目录"""
        return _get_secret("EXPORT_DIR", "history/exports")
    
    # ==================== RAG 配置 ====================
    
    @staticmethod
    def get_rag_chunk_size() -> int:
        """获取 RAG 文本分割块大小"""
        return int(_get_secret("RAG_CHUNK_SIZE", "500"))
    
    @staticmethod
    def get_rag_chunk_overlap() -> int:
        """获取 RAG 文本分割块重叠大小"""
        return int(_get_secret("RAG_CHUNK_OVERLAP", "50"))
    
    @staticmethod
    def get_rag_top_k() -> int:
        """获取 RAG 检索返回的最大片段数"""
        return int(_get_secret("RAG_TOP_K", "3"))
    
    @staticmethod
    def get_embedding_model() -> str:
        """获取嵌入模型名称"""
        return _get_secret("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    
    @staticmethod
    def get_chroma_db_path() -> str:
        """获取 ChromaDB 持久化路径"""
        return _get_secret("CHROMA_DB_PATH", "chromadb")
    
    # ==================== 便捷方法 ====================
    
    @staticmethod
    def validate_config() -> bool:
        """验证必要配置是否存在"""
        try:
            Config.get_api_key()
            return True
        except ValueError:
            return False
    
    @staticmethod
    def get_config_summary() -> dict:
        """获取配置摘要（不包含敏感信息）"""
        return {
            "base_url": Config.get_base_url(),
            "default_model": Config.get_default_model(),
            "timeout": Config.get_timeout(),
            "max_retries": Config.get_max_retries(),
            "max_history_tokens": Config.get_max_history_tokens(),
            "max_history_messages": Config.get_max_history_messages(),
            "default_temperature": Config.get_default_temperature(),
            "has_api_key": bool(os.getenv("MOONSHOT_API_KEY")),
            "history_dir": Config.get_history_dir(),
            "history_filename": Config.get_history_filename(),
            "export_dir": Config.get_export_dir(),
            "rag_chunk_size": Config.get_rag_chunk_size(),
            "rag_chunk_overlap": Config.get_rag_chunk_overlap(),
            "rag_top_k": Config.get_rag_top_k(),
            "embedding_model": Config.get_embedding_model(),
            "chroma_db_path": Config.get_chroma_db_path(),
        }


# 全局配置实例（方便导入使用）
config = Config
