"""
核心模块初始化

提供便捷的导入方式，从 core 包可以直接导入常用类和函数
"""

# 配置管理
from core.config import Config, config

# 聊天客户端
from core.chat import ChatClient

# 多模态客户端
from core.multimodal import MultimodalClient

# RAG 管线
from core.rag import RAGPipeline

# 意图路由器
from core.intent import IntentRouter, create_default_intents

# 历史记录管理
from core.history import (
    save_history,
    load_history,
    get_all_sessions,
    create_new_session,
    delete_history_file,
    export_history
)

# 工具函数
from core.utils import (
    copy_to_clipboard,
    truncate_text,
    count_tokens,
    execute_with_retry,
    execute_stream_with_retry,
    execute_with_retry_temp_fallback,
    execute_stream_with_retry_temp_fallback,
    is_temperature_error,
    format_elapsed_time,
    ensure_directory_exists,
    get_file_extension,
    generate_unique_filename
)

# 异常类
from core.base_client import BaseClientError, APIKeyError, NetworkError, ClientTimeoutError, ServiceError

__all__ = [
    # 配置
    'Config',
    'config',
    
    # 客户端
    'ChatClient',
    'MultimodalClient',
    'RAGPipeline',
    
    # 意图
    'IntentRouter',
    'create_default_intents',
    
    # 历史记录
    'save_history',
    'load_history',
    'get_all_sessions',
    'create_new_session',
    'delete_history_file',
    'export_history',
    
    # 工具函数
    'copy_to_clipboard',
    'truncate_text',
    'count_tokens',
    'execute_with_retry',
    'execute_stream_with_retry',
    'execute_with_retry_temp_fallback',
    'execute_stream_with_retry_temp_fallback',
    'is_temperature_error',
    'format_elapsed_time',
    'ensure_directory_exists',
    'get_file_extension',
    'generate_unique_filename',
    
    # 异常类
    'BaseClientError',
    'APIKeyError',
    'NetworkError',
    'ClientTimeoutError',
    'ServiceError'
]
