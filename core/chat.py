import os
from openai import OpenAI
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()


def chat(message: str, model: str = None) -> str:
    """
    与 Kimi AI 进行对话
    
    Args:
        message: 用户输入的消息
        model: 使用的模型名称，默认为 .env 中配置的 DEFAULT_MODEL
    
    Returns:
        AI 的回复内容
    """
    # 从环境变量读取配置
    api_key = os.getenv("MOONSHOT_API_KEY")
    base_url = os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1")
    default_model = os.getenv("DEFAULT_MODEL", "kimi-k2.5")
    
    if model is None:
        model = default_model
    
    if not api_key:
        raise ValueError("MOONSHOT_API_KEY 未配置，请在 .env 文件中设置")
    
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一切涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。"},
            {"role": "user", "content": message}
        ]
    )

    return completion.choices[0].message.content


if __name__ == "__main__":
    # 测试示例
    response = chat("你好，我叫李雷，1+1 等于多少？")
    print(response)