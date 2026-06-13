"""
聊天客户端模块

提供核心的聊天功能，包括：
- 普通聊天
- 流式聊天
- 多轮对话管理
- 异常处理
"""

import httpx
import time
from openai import OpenAI, AuthenticationError, APIConnectionError, APIError
from typing import List, Dict, Optional, Callable, Any, Generator

# 导入统一配置管理
from core.config import Config

# 导入工具函数
from core.utils import (
    execute_with_retry,
    execute_stream_with_retry,
    execute_with_retry_temp_fallback,
    execute_stream_with_retry_temp_fallback
)


# ==================== 自定义异常类 ====================

class ChatError(Exception):
    """聊天错误基类"""
    def __init__(self, message: str, error_type: str = "unknown"):
        """
        初始化聊天错误
        
        Args:
            message: 错误消息
            error_type: 错误类型
        """
        super().__init__(message)
        self.error_type = error_type
        self.message = message


class APIKeyError(ChatError):
    """API Key 错误"""
    def __init__(self, message: str):
        """
        初始化 API Key 错误
        
        Args:
            message: 错误消息
        """
        super().__init__(message, "api_key_error")


class NetworkError(ChatError):
    """网络错误"""
    def __init__(self, message: str):
        """
        初始化网络错误
        
        Args:
            message: 错误消息
        """
        super().__init__(message, "network_error")


class ChatTimeoutError(ChatError):
    """聊天超时错误"""
    def __init__(self, message: str):
        """
        初始化超时错误
        
        Args:
            message: 错误消息
        """
        super().__init__(message, "timeout_error")


class ServiceError(ChatError):
    """服务端错误"""
    def __init__(self, message: str):
        """
        初始化服务端错误
        
        Args:
            message: 错误消息
        """
        super().__init__(message, "service_error")


# ==================== 异常处理工具函数 ====================

def _handle_api_error(error: Exception) -> ChatError:
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
        return ChatTimeoutError(f"连接超时，请稍后重试: {str(error)}")
    elif isinstance(error, httpx.ReadTimeout):
        return ChatTimeoutError(f"读取超时，服务器响应时间过长: {str(error)}")
    elif isinstance(error, APIError):
        return ServiceError(f"服务错误: {str(error)}")
    else:
        return ChatError(f"未知错误: {str(error)}")


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


# ==================== 上下文截断工具 ====================

def truncate_messages(
    messages: List[Dict[str, str]],
    max_messages: Optional[int] = None,
    max_tokens: Optional[int] = None
) -> List[Dict[str, str]]:
    """
    截断消息列表，限制消息数量和 token 数
    
    Args:
        messages: 原始消息列表
        max_messages: 最大消息数
        max_tokens: 最大 token 数（估算）
    
    Returns:
        截断后的消息列表
    """
    if max_messages is None:
        max_messages = Config.get_max_history_messages()
    if max_tokens is None:
        max_tokens = Config.get_max_history_tokens()
    
    # 首先按消息数量截断
    if len(messages) > max_messages:
        messages = messages[-max_messages:]
    
    # 然后按 token 数截断（简单估算）
    total_tokens = 0
    result = []
    
    for msg in reversed(messages):
        msg_tokens = len(msg.get("content", "")) // 4
        if total_tokens + msg_tokens <= max_tokens:
            result.insert(0, msg)
            total_tokens += msg_tokens
        else:
            # 如果单条消息就超过限制，截断内容
            if not result:
                content = msg.get("content", "")
                max_chars = max_tokens * 4
                msg["content"] = content[-max_chars:]
                result.insert(0, msg)
            break
    
    return result


# ==================== 核心聊天函数 ====================

def chat(
    user_input: str,
    history: Optional[List[Dict[str, str]]] = None,
    temperature: Optional[float] = None
) -> Dict[str, Any]:
    """
    发送消息并获取回复（支持多轮对话）
    
    Args:
        user_input: 用户输入
        history: 历史对话记录
        temperature: 温度参数
    
    Returns:
        包含响应和更新后历史的字典
    """
    # 获取配置
    system_prompt = Config.get_system_prompt()
    
    # 初始化或更新历史
    if history is None:
        history = []
    
    # 添加用户消息到历史
    history.append({"role": "user", "content": user_input})
    
    # 构建完整消息列表
    messages = [{"role": "system", "content": system_prompt}] + truncate_messages(history)
    
    # 创建客户端
    client = OpenAI(
        api_key=Config.get_api_key(),
        base_url=Config.get_base_url(),
        http_client=httpx.Client(
            timeout=httpx.Timeout(Config.get_timeout()),
            follow_redirects=True,
        )
    )
    
    # 执行 API 调用
    def api_call():
        return client.chat.completions.create(
            model=Config.get_default_model(),
            messages=messages,
            temperature=temperature if temperature else Config.get_default_temperature()
        )
    
    def on_temperature_retry(new_temp):
        return client.chat.completions.create(
            model=Config.get_default_model(),
            messages=messages,
            temperature=new_temp
        )
    
    completion = execute_with_retry_temp_fallback(
        _wrap_api_call(api_call),
        temperature if temperature else Config.get_default_temperature(),
        max_retries=Config.get_max_retries(),
        on_temperature_retry=_wrap_api_call(on_temperature_retry)
    )
    response = completion.choices[0].message.content
    
    # 添加助手回复到历史
    history.append({"role": "assistant", "content": response})
    
    return {
        "response": response,
        "history": history,
        "messages": messages
    }


def stream_chat(
    user_input: str,
    history: Optional[List[Dict[str, str]]] = None,
    temperature: Optional[float] = None
) -> Generator[str, None, None]:
    """
    发送消息并获取流式回复（支持多轮对话）
    
    Args:
        user_input: 用户输入
        history: 历史对话记录
        temperature: 温度参数
    
    Yields:
        流式响应内容
    """
    # 获取配置
    system_prompt = Config.get_system_prompt()
    
    # 初始化或更新历史
    if history is None:
        history = []
    
    # 添加用户消息到历史
    history.append({"role": "user", "content": user_input})
    
    # 构建完整消息列表
    messages = [{"role": "system", "content": system_prompt}] + truncate_messages(history)
    
    # 创建客户端
    client = OpenAI(
        api_key=Config.get_api_key(),
        base_url=Config.get_base_url(),
        http_client=httpx.Client(
            timeout=httpx.Timeout(Config.get_timeout()),
            follow_redirects=True,
        )
    )
    
    # 执行流式 API 调用
    def api_call():
        return client.chat.completions.create(
            model=Config.get_default_model(),
            messages=messages,
            temperature=temperature if temperature else Config.get_default_temperature(),
            stream=True
        )
    
    def on_temperature_retry(new_temp):
        return client.chat.completions.create(
            model=Config.get_default_model(),
            messages=messages,
            temperature=new_temp,
            stream=True
        )
    
    yield from execute_stream_with_retry_temp_fallback(
        api_call,
        temperature if temperature else Config.get_default_temperature(),
        max_retries=Config.get_max_retries(),
        on_temperature_retry=on_temperature_retry
    )


# ==================== 聊天客户端类 ====================

class ChatClient:
    """
    聊天客户端类，兼容 Streamlit 应用
    
    提供完整的聊天功能，包括普通聊天和流式聊天，
    支持多轮对话和 Token 统计。
    """
    
    def __init__(self, provider: str = "moonshot"):
        """
        初始化聊天客户端
        
        Args:
            provider: 模型提供商名称（目前仅支持 moonshot）
        """
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
    
    def chat(self, messages: List[Dict[str, str]], temperature: Optional[float] = None) -> str:
        """
        发送消息并获取回复
        
        Args:
            messages: 消息列表，格式为 [{"role": "...", "content": "..."}]
            temperature: 温度参数，可选，默认使用配置值
        
        Returns:
            AI 的回复内容
        
        Raises:
            ChatError: 各种聊天错误
        """
        if temperature is None:
            temperature = Config.get_default_temperature()
        
        def api_call():
            return self.client.chat.completions.create(
                model=self.default_model,
                messages=messages,
                temperature=temperature
            )
        
        def on_temperature_retry(new_temp):
            return self.client.chat.completions.create(
                model=self.default_model,
                messages=messages,
                temperature=new_temp
            )
        
        completion = execute_with_retry_temp_fallback(
            _wrap_api_call(api_call),
            temperature,
            max_retries=Config.get_max_retries(),
            on_temperature_retry=_wrap_api_call(on_temperature_retry)
        )
        
        # 记录使用情况
        if hasattr(completion, 'usage'):
            self.last_usage = {
                'total_tokens': completion.usage.total_tokens,
                'prompt_tokens': completion.usage.prompt_tokens,
                'completion_tokens': completion.usage.completion_tokens
            }
        
        return completion.choices[0].message.content
    
    def stream_chat(self, messages: List[Dict[str, str]], temperature: Optional[float] = None) -> Generator[str, None, None]:
        """
        发送消息并获取流式回复
        
        Args:
            messages: 消息列表，格式为 [{"role": "...", "content": "..."}]
            temperature: 温度参数，可选，默认使用配置值
        
        Yields:
            流式响应内容
        
        Raises:
            ChatError: 各种聊天错误
        """
        if temperature is None:
            temperature = Config.get_default_temperature()
        
        def api_call():
            return self.client.chat.completions.create(
                model=self.default_model,
                messages=messages,
                temperature=temperature,
                stream=True
            )
        
        def on_temperature_retry(new_temp):
            return self.client.chat.completions.create(
                model=self.default_model,
                messages=messages,
                temperature=new_temp,
                stream=True
            )
        
        yield from execute_stream_with_retry_temp_fallback(
            api_call,
            temperature,
            max_retries=Config.get_max_retries(),
            on_temperature_retry=on_temperature_retry
        )


# ==================== 命令行交互 ====================

def cli_chat() -> None:
    """
    命令行交互式多轮对话
    
    提供简单的命令行界面，支持多轮对话和退出命令。
    """
    print("Kimi AI 多轮对话助手")
    print("---------------------")
    print("输入 'exit' 或 'quit' 退出对话")
    print("---------------------")
    
    history = None
    
    while True:
        try:
            user_input = input("\n你: ")
        except KeyboardInterrupt:
            print("\n[再见]")
            break
        
        if user_input.lower() in ["exit", "quit"]:
            print("再见！")
            break
        
        if not user_input.strip():
            print("[W] 请输入内容")
            continue
        
        print("思考中...")
        
        try:
            result = chat(user_input, history=history)
            response = result["response"]
            history = result["history"]
            
            print(f"\nKimi: {response}")
        except APIKeyError as e:
            print(f"\n[X] API Key 错误: {e.message}")
            print("   请检查 .env 文件中的 MOONSHOT_API_KEY 配置")
            break
        except NetworkError as e:
            print(f"\n[X] 网络错误: {e.message}")
            print("   请检查网络连接后重试")
        except ChatTimeoutError as e:
            print(f"\n[X] 超时错误: {e.message}")
            print("   服务器响应超时，请稍后重试")
        except ServiceError as e:
            print(f"\n[X] 服务错误: {e.message}")
        except Exception as e:
            print(f"\n[X] 未知错误: {str(e)}")


if __name__ == "__main__":
    cli_chat()
