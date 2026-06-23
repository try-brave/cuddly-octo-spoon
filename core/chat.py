"""
聊天客户端模块

提供核心的聊天功能，包括：
- 普通聊天
- 流式聊天
- 多轮对话管理
- 异常处理
"""

from typing import List, Dict, Optional, Generator, Any

# 导入基础客户端
from core.base_client import BaseClient, APIKeyError, NetworkError, ClientTimeoutError, ServiceError

# 导入统一配置管理
from core.config import Config


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
    client = ChatClient()
    
    # 执行 API 调用
    response = client.chat(messages, temperature=temperature)
    
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
    client = ChatClient()
    
    # 收集完整响应
    full_response = ""
    for chunk in client.stream_chat(messages, temperature=temperature):
        full_response += chunk
        yield chunk
    
    # 添加助手回复到历史
    history.append({"role": "assistant", "content": full_response})


# ==================== 聊天客户端类 ====================

class ChatClient(BaseClient):
    """
    聊天客户端类
    
    提供完整的聊天功能，包括普通聊天和流式聊天，
    支持多轮对话和 Token 统计。
    """
    
    def __init__(self, provider: str = "moonshot"):
        """
        初始化聊天客户端
        
        Args:
            provider: 模型提供商名称（目前仅支持 moonshot）
        """
        super().__init__(provider=provider)
    
    def chat(self, messages: List[Dict[str, str]], temperature: Optional[float] = None) -> str:
        """
        发送消息并获取回复
        
        Args:
            messages: 消息列表，格式为 [{"role": "...", "content": "..."}]
            temperature: 温度参数，可选，默认使用配置值
        
        Returns:
            AI 的回复内容
        
        Raises:
            BaseClientError: 各种聊天错误
        """
        completion = self._create_completion(
            messages=messages,
            temperature=temperature,
            stream=False
        )
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
            BaseClientError: 各种聊天错误
        """
        for chunk in self._create_completion_stream(
            messages=messages,
            temperature=temperature,
            max_tokens=Config.get_max_tokens()  # 优化：添加max_tokens限制
        ):
            yield chunk


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
            print("[!] 请输入内容")
            continue
        
        print("思考中...")
        
        try:
            result = chat(user_input, history=history)
            response = result["response"]
            history = result["history"]
            
            print(f"\nKimi: {response}")
        except APIKeyError as e:
            print(f"\n[!] API Key 错误: {e.message}")
            print("   请检查 .env 文件中的 MOONSHOT_API_KEY 配置")
            break
        except NetworkError as e:
            print(f"\n[!] 网络错误: {e.message}")
            print("   请检查网络连接后重试")
        except ClientTimeoutError as e:
            print(f"\n[!] 超时错误: {e.message}")
            print("   服务器响应超时，请稍后重试")
        except ServiceError as e:
            print(f"\n[!] 服务错误: {e.message}")
        except Exception as e:
            print(f"\n[!] 未知错误: {str(e)}")


if __name__ == "__main__":
    cli_chat()
