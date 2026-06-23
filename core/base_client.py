"""
基础客户端模块

提供所有 AI 客户端的通用功能，包括：
- OpenAI 客户端初始化
- API 调用和异常处理
- 重试机制
- Token 使用统计
"""

import httpx
from typing import List, Dict, Optional, Callable, Any, Generator

from core.config import Config
from core.utils import (
    execute_with_retry,
    execute_stream_with_retry,
    execute_with_retry_temp_fallback,
    execute_stream_with_retry_temp_fallback
)

# 延迟导入 openai（避免在模块导入时就加载）
OpenAI = None
AuthenticationError = None
APIConnectionError = None
APIError = None


def _ensure_openai_imported():
    """确保 openai 模块已导入（延迟导入）"""
    global OpenAI, AuthenticationError, APIConnectionError, APIError
    if OpenAI is None:
        from openai import OpenAI, AuthenticationError, APIConnectionError, APIError


# ==================== 自定义异常基类 ====================

class BaseClientError(Exception):
    """客户端错误基类"""
    def __init__(self, message: str, error_type: str = "unknown"):
        super().__init__(message)
        self.error_type = error_type
        self.message = message


class APIKeyError(BaseClientError):
    """API Key 错误"""
    def __init__(self, message: str):
        super().__init__(message, "api_key_error")


class NetworkError(BaseClientError):
    """网络错误"""
    def __init__(self, message: str):
        super().__init__(message, "network_error")


class ClientTimeoutError(BaseClientError):
    """客户端超时错误"""
    def __init__(self, message: str):
        super().__init__(message, "timeout_error")


class ServiceError(BaseClientError):
    """服务端错误"""
    def __init__(self, message: str):
        super().__init__(message, "service_error")


# ==================== 异常处理工具函数 ====================

def _handle_api_error(error: Exception) -> BaseClientError:
    """
    统一处理 API 错误，返回对应的自定义异常
    
    Args:
        error: 原始异常
    
    Returns:
        对应的自定义异常
    """
    if isinstance(error, AuthenticationError):
        return APIKeyError(f"API Key 无效或未配置: {str(error)}")
    elif isinstance(error, APIConnectionError):
        return NetworkError(f"网络连接失败，请检查网络连接: {str(error)}")
    elif isinstance(error, httpx.ConnectTimeout):
        return ClientTimeoutError(f"连接超时，请稍后重试: {str(error)}")
    elif isinstance(error, httpx.ReadTimeout):
        return ClientTimeoutError(f"读取超时，服务器响应时间过长: {str(error)}")
    elif isinstance(error, APIError):
        return ServiceError(f"服务错误: {str(error)}")
    else:
        return BaseClientError(f"未知错误: {str(error)}")


def _wrap_api_call(api_call: Callable[[], Any]) -> Callable[[], Any]:
    """
    包装 API 调用，添加异常处理
    
    Args:
        api_call: 原始 API 调用函数
    
    Returns:
        包装后的函数，会将异常转换为自定义异常
    """
    def wrapper():
        try:
            return api_call()
        except AuthenticationError as e:
            raise _handle_api_error(e)
        except Exception as e:
            raise _handle_api_error(e)
    return wrapper


# ==================== 基础客户端类 ====================

class BaseClient:
    """
    基础客户端类
    
    提供所有 AI 客户端的通用功能，包括：
    - OpenAI 客户端初始化
    - API 调用和异常处理
    - 重试机制
    - Token 使用统计
    """
    
    def __init__(self, provider: str = "moonshot"):
        """
        初始化基础客户端
        
        Args:
            provider: 模型提供商名称
        """
        # 确保 openai 模块已导入（延迟导入）
        _ensure_openai_imported()
        
        self.provider = provider
        self.api_key = Config.get_api_key()
        self.base_url = Config.get_base_url()
        self.default_model = Config.get_default_model()
        self.last_usage = None
        
        # 创建 OpenAI 客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            http_client=httpx.Client(
                timeout=httpx.Timeout(Config.get_timeout()),
                follow_redirects=True,
            )
        )
    
    def _create_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        stream: bool = False,
        **kwargs
    ):
        """
        创建 API 完成请求（带重试和异常处理）
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            stream: 是否使用流式响应
            **kwargs: 其他参数传递给 API
        
        Returns:
            API 完成对象
        """
        if temperature is None:
            temperature = Config.get_default_temperature()
        
        def api_call():
            return self.client.chat.completions.create(
                model=self.default_model,
                messages=messages,
                temperature=temperature,
                stream=stream,
                **kwargs
            )
        
        def on_temperature_retry(new_temp):
            return self.client.chat.completions.create(
                model=self.default_model,
                messages=messages,
                temperature=new_temp,
                stream=stream,
                **kwargs
            )
        
        if stream:
            return execute_stream_with_retry_temp_fallback(
                api_call,
                temperature,
                max_retries=Config.get_max_retries(),
                on_temperature_retry=on_temperature_retry
            )
        else:
            completion = execute_with_retry_temp_fallback(
                _wrap_api_call(api_call),
                temperature,
                max_retries=Config.get_max_retries(),
                on_temperature_retry=_wrap_api_call(on_temperature_retry)
            )
            
            # 记录 Token 使用情况
            if hasattr(completion, 'usage'):
                self.last_usage = {
                    'total_tokens': completion.usage.total_tokens,
                    'prompt_tokens': completion.usage.prompt_tokens,
                    'completion_tokens': completion.usage.completion_tokens
                }
            
            return completion
    
    def _create_completion_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        创建流式 API 完成请求
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            **kwargs: 其他参数传递给 API
        
        Yields:
            流式响应内容
        """
        for chunk in self._create_completion(
            messages=messages,
            temperature=temperature,
            stream=True,
            **kwargs
        ):
            yield chunk
    
    def get_last_usage(self) -> Optional[dict]:
        """
        获取最后一次 API 调用的 Token 使用情况
        
        Returns:
            Token 使用情况字典，如果没有则返回 None
        """
        return self.last_usage
