from typing import Callable, Dict, Any, List, Optional, Tuple
import re
from abc import ABC, abstractmethod


class Intent(ABC):
    """
    意图基类
    """
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
    
    @abstractmethod
    def match(self, text: str, context: Dict[str, Any] = None) -> float:
        """
        判断文本是否匹配此意图
        
        Args:
            text: 用户输入文本
            context: 上下文信息
        
        Returns:
            匹配分数 (0-1)
        """
        pass
    
    @abstractmethod
    def handle(self, text: str, context: Dict[str, Any] = None) -> Any:
        """
        处理此意图
        
        Args:
            text: 用户输入文本
            context: 上下文信息
        
        Returns:
            处理结果
        """
        pass


class PatternIntent(Intent):
    """
    基于正则表达式模式匹配的意图
    """
    
    def __init__(self, name: str, pattern: str, handler: Callable, description: str = "", priority: int = 0):
        super().__init__(name, description)
        self.pattern = re.compile(pattern, re.IGNORECASE)
        self.handler = handler
        self.priority = priority
    
    def match(self, text: str, context: Dict[str, Any] = None) -> float:
        if self.pattern.search(text):
            return 0.9 + self.priority * 0.01
        return 0.0
    
    def handle(self, text: str, context: Dict[str, Any] = None) -> Any:
        return self.handler(text, context)


class KeywordIntent(Intent):
    """
    基于关键词匹配的意图
    """
    
    def __init__(self, name: str, keywords: List[str], handler: Callable, description: str = "", priority: int = 0):
        super().__init__(name, description)
        self.keywords = keywords
        self.handler = handler
        self.priority = priority
    
    def match(self, text: str, context: Dict[str, Any] = None) -> float:
        text_lower = text.lower()
        matched_count = sum(1 for keyword in self.keywords if keyword.lower() in text_lower)
        if matched_count > 0:
            return min(0.9, matched_count / len(self.keywords)) + self.priority * 0.01
        return 0.0
    
    def handle(self, text: str, context: Dict[str, Any] = None) -> Any:
        return self.handler(text, context)


class MLIntent(Intent):
    """
    基于机器学习模型的意图（占位符）
    """
    
    def __init__(self, name: str, model, handler: Callable, description: str = ""):
        super().__init__(name, description)
        self.model = model
        self.handler = handler
    
    def match(self, text: str, context: Dict[str, Any] = None) -> float:
        # 实际实现中会调用 ML 模型进行意图分类
        # 这里返回一个默认值作为示例
        return 0.5
    
    def handle(self, text: str, context: Dict[str, Any] = None) -> Any:
        return self.handler(text, context)


class IntentRouter:
    """
    意图路由器
    
    负责识别用户意图并路由到相应的处理函数。
    
    工作流程：
    1. 接收用户输入
    2. 使用所有注册的意图匹配器进行匹配
    3. 选择匹配分数最高的意图
    4. 调用该意图的处理函数
    5. 返回处理结果
    
    示例用法：
    >>> router = IntentRouter()
    >>> router.register_intent(PatternIntent("greeting", r"^(你好|hello|hi)", greet_handler))
    >>> router.register_intent(KeywordIntent("goodbye", ["再见", "拜拜", "再见了"], goodbye_handler))
    >>> result = router.route("你好，我想咨询一下")
    """
    
    def __init__(self, default_handler: Optional[Callable] = None):
        """
        初始化意图路由器
        
        Args:
            default_handler: 当没有匹配到任何意图时调用的默认处理器
        """
        self.intents: List[Intent] = []
        self.default_handler = default_handler
    
    def register_intent(self, intent: Intent):
        """
        注册一个意图
        
        Args:
            intent: 意图对象
        """
        self.intents.append(intent)
        # 按优先级排序
        self.intents.sort(key=lambda x: getattr(x, 'priority', 0), reverse=True)
    
    def register_pattern_intent(self, name: str, pattern: str, handler: Callable, description: str = "", priority: int = 0):
        """
        便捷方法：注册一个基于正则表达式的意图
        
        Args:
            name: 意图名称
            pattern: 正则表达式模式
            handler: 处理函数
            description: 意图描述
            priority: 优先级（数字越大优先级越高）
        """
        intent = PatternIntent(name, pattern, handler, description, priority)
        self.register_intent(intent)
    
    def register_keyword_intent(self, name: str, keywords: List[str], handler: Callable, description: str = "", priority: int = 0):
        """
        便捷方法：注册一个基于关键词的意图
        
        Args:
            name: 意图名称
            keywords: 关键词列表
            handler: 处理函数
            description: 意图描述
            priority: 优先级
        """
        intent = KeywordIntent(name, keywords, handler, description, priority)
        self.register_intent(intent)
    
    def match(self, text: str, context: Dict[str, Any] = None) -> Tuple[Optional[Intent], float]:
        """
        匹配最佳意图
        
        Args:
            text: 用户输入文本
            context: 上下文信息
        
        Returns:
            匹配的意图和匹配分数
        """
        best_intent = None
        best_score = 0.0
        
        for intent in self.intents:
            score = intent.match(text, context)
            if score > best_score:
                best_score = score
                best_intent = intent
        
        return best_intent, best_score
    
    def route(self, text: str, context: Dict[str, Any] = None, threshold: float = 0.3) -> Dict[str, Any]:
        """
        路由到最佳匹配的意图处理器
        
        Args:
            text: 用户输入文本
            context: 上下文信息
            threshold: 匹配阈值，低于此阈值使用默认处理器
        
        Returns:
            处理结果，包含：
            - intent: 匹配的意图名称
            - score: 匹配分数
            - result: 处理结果
            - is_default: 是否使用了默认处理器
        """
        intent, score = self.match(text, context)
        
        if intent and score >= threshold:
            try:
                result = intent.handle(text, context)
                return {
                    "intent": intent.name,
                    "score": score,
                    "result": result,
                    "is_default": False
                }
            except Exception as e:
                return {
                    "intent": intent.name,
                    "score": score,
                    "result": f"处理失败: {str(e)}",
                    "is_default": False,
                    "error": str(e)
                }
        else:
            if self.default_handler:
                try:
                    result = self.default_handler(text, context)
                    return {
                        "intent": "default",
                        "score": score if intent else 0.0,
                        "result": result,
                        "is_default": True
                    }
                except Exception as e:
                    return {
                        "intent": "default",
                        "score": score if intent else 0.0,
                        "result": f"默认处理失败: {str(e)}",
                        "is_default": True,
                        "error": str(e)
                    }
            else:
                return {
                    "intent": None,
                    "score": score if intent else 0.0,
                    "result": None,
                    "is_default": True,
                    "error": "未找到匹配的意图且没有设置默认处理器"
                }
    
    def get_intents(self) -> List[Dict[str, Any]]:
        """
        获取所有已注册的意图信息
        
        Returns:
            意图列表，每个元素包含名称、描述和类型
        """
        return [
            {
                "name": intent.name,
                "description": intent.description,
                "type": type(intent).__name__
            }
            for intent in self.intents
        ]
    
    def remove_intent(self, name: str):
        """
        移除指定名称的意图
        
        Args:
            name: 意图名称
        """
        self.intents = [intent for intent in self.intents if intent.name != name]


# ==================== 预设意图示例 ====================

def create_default_intents(router: IntentRouter) -> IntentRouter:
    """
    创建预设的常见意图
    
    Args:
        router: 意图路由器实例
    
    Returns:
        注册了预设意图的路由器实例
    """
    
    # 问候意图
    def greet_handler(text: str, context: Dict[str, Any] = None) -> str:
        return "你好！我是你的 AI 助手，请问有什么可以帮助你的？"
    
    router.register_pattern_intent(
        name="greeting",
        pattern=r"^(你好|hello|hi|您好|嗨|早上好|下午好|晚上好)",
        handler=greet_handler,
        description="问候语",
        priority=1
    )
    
    # 感谢意图
    def thank_handler(text: str, context: Dict[str, Any] = None) -> str:
        return "不客气！能帮到你我很开心。"
    
    router.register_keyword_intent(
        name="thank",
        keywords=["谢谢", "感谢", "辛苦了", "谢谢啦"],
        handler=thank_handler,
        description="感谢语",
        priority=1
    )
    
    # 再见意图
    def goodbye_handler(text: str, context: Dict[str, Any] = None) -> str:
        return "再见！欢迎下次再来。"
    
    router.register_keyword_intent(
        name="goodbye",
        keywords=["再见", "拜拜", "再见了", "下次见"],
        handler=goodbye_handler,
        description="告别语",
        priority=1
    )
    
    # 帮助意图
    def help_handler(text: str, context: Dict[str, Any] = None) -> str:
        return """我可以帮你做这些事情：
- 回答各种问题
- 分析图片内容
- 识别图片中的文字（OCR）
- 基于文档进行问答（RAG）

请问你需要什么帮助？"""
    
    router.register_keyword_intent(
        name="help",
        keywords=["帮助", "help", "功能", "能做什么", "怎么用"],
        handler=help_handler,
        description="寻求帮助",
        priority=1
    )
    
    # OCR 意图
    def ocr_handler(text: str, context: Dict[str, Any] = None) -> str:
        return "请上传图片，我来帮你识别图片中的文字。"
    
    router.register_keyword_intent(
        name="ocr",
        keywords=["识别文字", "提取文字", "OCR", "文字识别", "图片文字"],
        handler=ocr_handler,
        description="OCR文字识别",
        priority=2
    )
    
    # 图片问答意图
    def image_qa_handler(text: str, context: Dict[str, Any] = None) -> str:
        return "请上传图片，然后描述你想了解的内容。"
    
    router.register_keyword_intent(
        name="image_qa",
        keywords=["图片", "照片", "图片分析", "分析图片", "看图", "这张图"],
        handler=image_qa_handler,
        description="图片问答",
        priority=2
    )


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 创建意图路由器
    router = IntentRouter()
    
    # 注册预设意图
    create_default_intents(router)
    
    # 添加自定义意图
    def echo_handler(text: str, context: Dict[str, Any] = None) -> str:
        return f"你说的是：{text}"
    
    router.register_pattern_intent(
        name="echo",
        pattern=r"^echo\s+(.+)",
        handler=echo_handler,
        description="重复用户输入",
        priority=3
    )
    
    # 测试路由
    test_cases = [
        "你好！",
        "谢谢帮助",
        "帮我识别图片中的文字",
        "echo hello world",
        "这张图片里有什么",
        "明天天气怎么样"
    ]
    
    print("意图路由测试：")
    print("-" * 50)
    
    for text in test_cases:
        result = router.route(text)
        print(f"输入: {text}")
        print(f"  意图: {result['intent']}, 分数: {result['score']:.2f}")
        print(f"  结果: {result['result']}")
        print()
