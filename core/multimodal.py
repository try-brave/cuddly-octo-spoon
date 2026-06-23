import base64
from typing import List, Dict, Optional, Generator, Any
from PIL import Image
import io

from core.base_client import BaseClient, APIKeyError, NetworkError, ClientTimeoutError, ServiceError
from core.config import Config


# ==================== 图片处理工具函数 ====================

def image_to_base64(image_path: str) -> str:
    """
    将图片文件转换为 Base64 编码
    
    Args:
        image_path: 图片文件路径
    
    Returns:
        Base64 编码的图片数据（包含 MIME 类型）
    """
    try:
        # 确定图片格式
        ext = image_path.lower().split('.')[-1]
        mime_types = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'webp': 'image/webp',
            'gif': 'image/gif'
        }
        
        if ext not in mime_types:
            raise ImageError(f"不支持的图片格式: {ext}")
        
        # 读取并转换图片
        with open(image_path, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
        
        return f"data:{mime_types[ext]};base64,{encoded}"
    except Exception as e:
        raise ImageError(f"图片处理失败: {str(e)}")


def resize_image(image_data: bytes, max_size: int = 4 * 1024 * 1024) -> bytes:
    """
    调整图片大小，确保不超过指定大小
    
    Args:
        image_data: 原始图片数据
        max_size: 最大大小（字节），默认 4MB
    
    Returns:
        调整后的图片数据
    """
    if len(image_data) <= max_size:
        return image_data
    
    try:
        img = Image.open(io.BytesIO(image_data))
        
        # 计算缩放比例
        scale = (max_size / len(image_data)) ** 0.5
        
        # 调整尺寸
        new_width = int(img.width * scale)
        new_height = int(img.height * scale)
        
        # 确保至少有一个像素
        new_width = max(new_width, 1)
        new_height = max(new_height, 1)
        
        img = img.resize((new_width, new_height), Image.LANCZOS)
        
        # 保存到字节流
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=85)
        
        return buf.getvalue()
    except Exception as e:
        raise ImageError(f"图片调整失败: {str(e)}")


# ==================== 自定义异常类 ====================

class MultimodalError(Exception):
    """多模态错误基类"""
    def __init__(self, message: str, error_type: str = "unknown"):
        super().__init__(message)
        self.error_type = error_type
        self.message = message


class ImageError(MultimodalError):
    """图片处理错误"""
    def __init__(self, message: str):
        super().__init__(message, "image_error")


# ==================== 多模态客户端类 ====================

class MultimodalClient(BaseClient):
    """
    多模态客户端 - 支持文本和图片输入
    
    支持的图片格式：png, jpg, jpeg, webp, gif
    
    功能特性：
    - 图片问答
    - 图片追问（保留图片上下文）
    - OCR 文字识别
    """
    
    def __init__(self, provider: str = "moonshot"):
        """
        初始化多模态客户端
        
        Args:
            provider: 模型提供商名称
        """
        super().__init__(provider=provider)
        
        # 图片上下文缓存（用于追问机制）
        self.current_image_base64 = None
        self.image_context_history = []
    
    def _build_multimodal_message(self, text: str, image_base64: str = None) -> Dict[str, Any]:
        """
        构建多模态消息内容
        
        Args:
            text: 用户文本消息
            image_base64: Base64 编码的图片数据
        
        Returns:
            格式化的消息内容
        """
        if image_base64:
            return {
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                    {"type": "image_url", "image_url": {"url": image_base64}}
                ]
            }
        else:
            return {"role": "user", "content": text}
    
    def chat_with_image(
        self,
        messages: List[Dict[str, Any]],
        image_path: str = None,
        image_base64: str = None,
        temperature: float = None
    ) -> str:
        """
        发送包含图片的消息
        
        Args:
            messages: 消息列表
            image_path: 图片文件路径（与 image_base64 二选一）
            image_base64: Base64 编码的图片数据（与 image_path 二选一）
            temperature: 温度参数
        
        Returns:
            AI 的回复内容
        
        Raises:
            ImageError: 图片处理错误
        """
        # 处理图片输入
        processed_image_base64 = None
        if image_path:
            processed_image_base64 = image_to_base64(image_path)
        elif image_base64:
            processed_image_base64 = image_base64
        
        # 构建完整消息列表
        final_messages = messages.copy()
        
        # 如果有图片，创建多模态消息
        if processed_image_base64:
            # 检查最后一条消息是否是用户消息
            if final_messages and final_messages[-1].get("role") == "user":
                # 修改最后一条用户消息为多模态消息
                text = final_messages[-1].get("content", "")
                final_messages[-1] = self._build_multimodal_message(text, processed_image_base64)
            else:
                # 添加新的多模态消息
                final_messages.append(self._build_multimodal_message("", processed_image_base64))
        
        completion = self._create_completion(
            messages=final_messages,
            temperature=temperature,
            stream=False
        )
        return completion.choices[0].message.content
    
    def stream_chat_with_image(
        self,
        messages: List[Dict[str, Any]],
        image_path: str = None,
        image_base64: str = None,
        temperature: float = None
    ) -> Generator[str, None, None]:
        """
        流式发送包含图片的消息
        
        Args:
            messages: 消息列表
            image_path: 图片文件路径（与 image_base64 二选一）
            image_base64: Base64 编码的图片数据（与 image_path 二选一）
            temperature: 温度参数
        
        Yields:
            流式响应内容
        
        Raises:
            ImageError: 图片处理错误
        """
        # 处理图片输入
        processed_image_base64 = None
        if image_path:
            processed_image_base64 = image_to_base64(image_path)
        elif image_base64:
            processed_image_base64 = image_base64
        
        # 构建完整消息列表
        final_messages = messages.copy()
        
        # 如果有图片，创建多模态消息
        if processed_image_base64:
            if final_messages and final_messages[-1].get("role") == "user":
                text = final_messages[-1].get("content", "")
                final_messages[-1] = self._build_multimodal_message(text, processed_image_base64)
            else:
                final_messages.append(self._build_multimodal_message("", processed_image_base64))
        
        for chunk in self._create_completion_stream(
            messages=final_messages,
            temperature=temperature
        ):
            yield chunk
    
    def set_image_context(self, image_base64: str):
        """
        设置图片上下文（用于追问机制）
        
        Args:
            image_base64: Base64 编码的图片数据
        """
        self.current_image_base64 = image_base64
        # 重置图片上下文历史
        self.image_context_history = []
    
    def clear_image_context(self):
        """
        清除图片上下文
        
        调用此方法后，后续的追问将不再包含之前的图片
        """
        self.current_image_base64 = None
        self.image_context_history = []
    
    def has_image_context(self) -> bool:
        """
        检查是否有图片上下文
        
        Returns:
            是否存在图片上下文
        """
        return self.current_image_base64 is not None
    
    def follow_up_with_image(
        self,
        text: str,
        temperature: float = None,
        use_context: bool = True
    ) -> str:
        """
        图片追问 - 在已有图片上下文的基础上继续提问
        
        Args:
            text: 用户追问的文本
            temperature: 温度参数
            use_context: 是否使用之前的图片上下文
        
        Returns:
            AI 的回复内容
        
        Raises:
            ImageError: 如果没有图片上下文且 use_context=True
        """
        if temperature is None:
            temperature = Config.get_default_temperature()
        
        # 确定要使用的图片
        image_to_use = None
        if use_context and self.current_image_base64:
            image_to_use = self.current_image_base64
        elif not use_context:
            # 不使用上下文，直接发送文本
            final_messages = [{"role": "user", "content": text}]
            completion = self._create_completion(
                messages=final_messages,
                temperature=temperature,
                stream=False
            )
            return completion.choices[0].message.content
        else:
            raise ImageError("没有可用的图片上下文，请先上传图片或使用 chat_with_image 方法")
        
        # 构建包含图片上下文的消息
        final_messages = []
        
        # 添加之前的对话历史（作为上下文）
        for item in self.image_context_history:
            final_messages.append(item)
        
        # 添加当前追问（带图片）
        final_messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": image_to_use}}
            ]
        })
        
        completion = self._create_completion(
            messages=final_messages,
            temperature=temperature,
            stream=False
        )
        response = completion.choices[0].message.content
        
        # 更新图片上下文历史
        self.image_context_history.append({"role": "user", "content": text})
        self.image_context_history.append({"role": "assistant", "content": response})
        
        return response
    
    def stream_follow_up_with_image(
        self,
        text: str,
        temperature: float = None,
        use_context: bool = True
    ) -> Generator[str, None, None]:
        """
        流式图片追问 - 在已有图片上下文的基础上继续提问
        
        Args:
            text: 用户追问的文本
            temperature: 温度参数
            use_context: 是否使用之前的图片上下文
        
        Yields:
            流式响应内容
        
        Raises:
            ImageError: 如果没有图片上下文且 use_context=True
        """
        if temperature is None:
            temperature = Config.get_default_temperature()
        
        image_to_use = None
        if use_context and self.current_image_base64:
            image_to_use = self.current_image_base64
        elif not use_context:
            final_messages = [{"role": "user", "content": text}]
            for chunk in self._create_completion_stream(
                messages=final_messages,
                temperature=temperature
            ):
                yield chunk
            return
        else:
            raise ImageError("没有可用的图片上下文，请先上传图片")
        
        final_messages = []
        for item in self.image_context_history:
            final_messages.append(item)
        
        final_messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": image_to_use}}
            ]
        })
        
        full_response = ""
        for chunk in self._create_completion_stream(
            messages=final_messages,
            temperature=temperature
        ):
            full_response += chunk
            yield chunk
        
        # 更新图片上下文历史
        self.image_context_history.append({"role": "user", "content": text})
        self.image_context_history.append({"role": "assistant", "content": full_response})
    
    def ocr_image(
        self,
        image_path: str = None,
        image_base64: str = None,
        temperature: float = None
    ) -> str:
        """
        OCR 文字识别 - 提取图片中的文字内容
        
        Args:
            image_path: 图片文件路径
            image_base64: Base64 编码的图片数据
            temperature: 温度参数
        
        Returns:
            识别出的文字内容
        
        Raises:
            ImageError: 图片处理错误
        """
        if temperature is None:
            temperature = Config.get_default_temperature()
        
        # 处理图片输入
        processed_image_base64 = None
        if image_path:
            processed_image_base64 = image_to_base64(image_path)
        elif image_base64:
            processed_image_base64 = image_base64
        else:
            raise ImageError("请提供图片路径或 Base64 编码的图片数据")
        
        # 设置图片上下文（用于后续追问）
        self.set_image_context(processed_image_base64)
        
        # 构建 OCR 请求
        ocr_prompt = """请识别图片中的所有文字内容，并以清晰可读的格式输出。
        如果图片中有表格，请尽量保持表格结构。
        如果图片中有多行文字，请按顺序列出。
        只输出识别结果，不要添加额外说明。"""
        
        final_messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": ocr_prompt},
                {"type": "image_url", "image_url": {"url": processed_image_base64}}
            ]
        }]
        
        completion = self._create_completion(
            messages=final_messages,
            temperature=temperature,
            stream=False
        )
        response = completion.choices[0].message.content
        
        # 更新图片上下文历史
        self.image_context_history.append({"role": "user", "content": ocr_prompt})
        self.image_context_history.append({"role": "assistant", "content": response})
        
        return response
    
    def stream_ocr_image(
        self,
        image_path: str = None,
        image_base64: str = None,
        temperature: float = None
    ) -> Generator[str, None, None]:
        """
        流式 OCR 文字识别 - 提取图片中的文字内容
        
        Args:
            image_path: 图片文件路径
            image_base64: Base64 编码的图片数据
            temperature: 温度参数
        
        Yields:
            识别出的文字内容（流式输出）
        
        Raises:
            ImageError: 图片处理错误
        """
        if temperature is None:
            temperature = Config.get_default_temperature()
        
        processed_image_base64 = None
        if image_path:
            processed_image_base64 = image_to_base64(image_path)
        elif image_base64:
            processed_image_base64 = image_base64
        else:
            raise ImageError("请提供图片路径或 Base64 编码的图片数据")
        
        self.set_image_context(processed_image_base64)
        
        ocr_prompt = """请识别图片中的所有文字内容，并以清晰可读的格式输出。
        如果图片中有表格，请尽量保持表格结构。
        如果图片中有多行文字，请按顺序列出。
        只输出识别结果，不要添加额外说明。"""
        
        final_messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": ocr_prompt},
                {"type": "image_url", "image_url": {"url": processed_image_base64}}
            ]
        }]
        
        full_response = ""
        for chunk in self._create_completion_stream(
            messages=final_messages,
            temperature=temperature
        ):
            full_response += chunk
            yield chunk
        
        self.image_context_history.append({"role": "user", "content": ocr_prompt})
        self.image_context_history.append({"role": "assistant", "content": full_response})


# ==================== 便捷函数 ====================

def chat_with_image(
    message: str,
    image_path: str = None,
    image_base64: str = None,
    model: str = None,
    temperature: float = None,
    history: Optional[List[Dict[str, str]]] = None
) -> dict:
    """
    便捷函数：发送包含图片的消息
    
    Args:
        message: 用户消息文本
        image_path: 图片文件路径
        image_base64: Base64 编码的图片数据
        model: 模型名称
        temperature: 温度参数
        history: 对话历史
    
    Returns:
        包含回复内容和更新后对话历史的字典
    """
    client = MultimodalClient()
    
    # 构建消息列表
    messages = [{"role": "system", "content": Config.get_system_prompt()}]
    
    if history:
        messages.extend(history)
    
    messages.append({"role": "user", "content": message})
    
    response = client.chat_with_image(
        messages=messages,
        image_path=image_path,
        image_base64=image_base64,
        temperature=temperature
    )
    
    # 更新历史
    new_history = history.copy() if history else []
    new_history.append({"role": "user", "content": message})
    new_history.append({"role": "assistant", "content": response})
    
    return {
        "response": response,
        "history": new_history
    }
