"""
工具函数模块

提供通用的工具函数，包括：
- API 调用重试逻辑
- 异常处理工具
- 剪贴板操作
- 文本处理工具
"""

import time
import httpx
from typing import Callable, Any, Generator, Optional

# ==================== 剪贴板操作 ====================

def copy_to_clipboard(text: str) -> bool:
    """
    复制文本到剪贴板
    
    Args:
        text: 要复制的文本
        
    Returns:
        成功返回 True，失败返回 False
    """
    try:
        # 优先使用 pyperclip
        import pyperclip
        pyperclip.copy(text)
        return True
    except ImportError:
        try:
            # Windows 平台
            import win32clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            return True
        except:
            # 作为后备，什么都不做
            return False


# ==================== 文本处理工具 ====================

def truncate_text(text: str, max_length: int = 50) -> str:
    """
    截断文本并添加省略号
    
    Args:
        text: 原始文本
        max_length: 最大长度
        
    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def count_tokens(text: str) -> int:
    """
    估算文本的 token 数量（简单估算：按字符数的 1/4 计算）
    
    Args:
        text: 要计算的文本
        
    Returns:
        估算的 token 数量
    """
    return len(text) // 4


# ==================== API 调用工具 ====================

def execute_with_retry(
    api_call: Callable[[], Any],
    max_retries: int = 2,
    on_retry: Optional[Callable[[int], None]] = None
) -> Any:
    """
    统一的 API 调用重试逻辑
    
    Args:
        api_call: API 调用函数
        max_retries: 最大重试次数
        on_retry: 重试前的回调函数，接收当前重试次数
        
    Returns:
        API 调用结果
        
    Raises:
        原始异常（所有重试都失败时）
    """
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            return api_call()
        except Exception as e:
            last_error = e
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries:
                if on_retry:
                    on_retry(attempt + 1)
                wait_time = 2 ** attempt
                time.sleep(wait_time)
    
    # 所有重试都失败，抛出最后一个错误
    if last_error is not None:
        raise last_error


def execute_stream_with_retry(
    api_call: Callable[[], Generator],
    max_retries: int = 2,
    on_retry: Optional[Callable[[int], None]] = None
) -> Generator:
    """
    统一的流式 API 调用重试逻辑
    
    Args:
        api_call: API 调用函数，返回生成器
        max_retries: 最大重试次数
        on_retry: 重试前的回调函数，接收当前重试次数
        
    Yields:
        流式响应内容
        
    Raises:
        原始异常（所有重试都失败时）
    """
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            stream = api_call()
            for chunk in stream:
                yield chunk
            return
        except Exception as e:
            last_error = e
            
            if attempt < max_retries:
                if on_retry:
                    on_retry(attempt + 1)
                wait_time = 2 ** attempt
                time.sleep(wait_time)
    
    if last_error is not None:
        raise last_error


# ==================== API 错误处理工具 ====================

def is_temperature_error(error: Exception) -> bool:
    """
    检查是否为温度参数错误
    
    Args:
        error: 异常对象
    
    Returns:
        如果是温度错误返回 True，否则返回 False
    """
    error_str = str(error)
    return "temperature" in error_str.lower() or "温度" in error_str


def execute_with_retry_temp_fallback(
    api_call: Callable[[], Any],
    temperature: float,
    max_retries: int = 2,
    on_temperature_retry: Optional[Callable[[float], Any]] = None
) -> Any:
    """
    统一的 API 调用重试逻辑，支持温度错误特殊处理
    
    当遇到温度参数错误时，会自动尝试使用温度 1.0 重试。
    
    Args:
        api_call: API 调用函数
        temperature: 温度参数
        max_retries: 最大重试次数
        on_temperature_retry: 温度错误时的重试回调函数，接收新的温度值
    
    Returns:
        API 调用结果
    
    Raises:
        原始异常（所有重试都失败时）
    """
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            return api_call()
        except Exception as e:
            last_error = e
            
            # 如果是温度错误且不是最后一次尝试，尝试用 1.0 重试
            if is_temperature_error(e) and attempt < max_retries:
                try:
                    if on_temperature_retry:
                        return on_temperature_retry(1.0)
                except Exception as retry_e:
                    last_error = retry_e
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries:
                wait_time = 2 ** attempt
                time.sleep(wait_time)

    if last_error is not None:
        raise last_error


def execute_stream_with_retry_temp_fallback(
    api_call: Callable[[], Generator],
    temperature: float,
    max_retries: int = 2,
    on_temperature_retry: Optional[Callable[[float], Generator]] = None
) -> Generator:
    """
    统一的流式 API 调用重试逻辑，支持温度错误特殊处理
    
    当遇到温度参数错误时，会自动尝试使用温度 1.0 重试。
    
    Args:
        api_call: API 调用函数，返回生成器
        temperature: 温度参数
        max_retries: 最大重试次数
        on_temperature_retry: 温度错误时的重试回调函数，接收新的温度值
    
    Yields:
        流式响应内容
    
    Raises:
        原始异常（所有重试都失败时）
    """
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            stream = api_call()
            for chunk in stream:
                if hasattr(chunk, 'choices') and chunk.choices:
                    content = chunk.choices[0].delta.content
                    if content is not None:
                        yield content
                else:
                    yield chunk
            return
            
        except Exception as e:
            last_error = e
            
            # 如果是温度错误且不是最后一次尝试，尝试用 1.0 重试
            if is_temperature_error(e) and attempt < max_retries:
                try:
                    if on_temperature_retry:
                        stream = on_temperature_retry(1.0)
                        for chunk in stream:
                            if hasattr(chunk, 'choices') and chunk.choices:
                                content = chunk.choices[0].delta.content
                                if content is not None:
                                    yield content
                            else:
                                yield chunk
                        return
                except Exception as retry_e:
                    last_error = retry_e
            
            if attempt < max_retries:
                wait_time = 2 ** attempt
                time.sleep(wait_time)

    if last_error is not None:
        raise last_error


# ==================== 时间工具 ====================

def format_elapsed_time(seconds: float) -> str:
    """
    格式化耗时为可读字符串
    
    Args:
        seconds: 耗时（秒）
        
    Returns:
        格式化的时间字符串
    """
    if seconds < 0.001:
        return f"{seconds * 1000000:.1f} μs"
    elif seconds < 1:
        return f"{seconds * 1000:.1f} ms"
    elif seconds < 60:
        return f"{seconds:.2f} 秒"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes} 分 {secs:.1f} 秒"


# ==================== 文件工具 ====================

def ensure_directory_exists(path: str) -> None:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        path: 目录路径
    """
    import os
    os.makedirs(path, exist_ok=True)


def get_file_extension(filename: str) -> str:
    """
    获取文件扩展名（不含点）
    
    Args:
        filename: 文件名
        
    Returns:
        扩展名（小写）
    """
    import os
    return os.path.splitext(filename)[1][1:].lower()


def generate_unique_filename(prefix: str = "file", extension: str = "txt") -> str:
    """
    生成唯一的文件名
    
    Args:
        prefix: 文件名前缀
        extension: 文件扩展名
        
    Returns:
        唯一的文件名
    """
    import uuid
    return f"{prefix}_{uuid.uuid4().hex[:8]}.{extension}"
