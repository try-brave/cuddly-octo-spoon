"""
对话历史持久化模块

提供对话历史的保存、加载、管理功能，支持 JSON 格式存储
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional

from core.config import Config


def save_history(history: List[Dict[str, str]], filename: str = None) -> None:
    """
    保存对话历史到 JSON 文件
    
    Args:
        history: 对话历史列表
        filename: 保存的文件名，默认为配置中的文件名
    """
    if filename is None:
        filename = Config.get_history_file_path()
    
    data = {
        "save_time": datetime.now().isoformat(),
        "history": history,
        "title": _generate_title(history)
    }
    
    dir_path = os.path.dirname(filename)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_history(filename: str = None) -> List[Dict[str, str]]:
    """
    从 JSON 文件加载对话历史
    
    Args:
        filename: 加载的文件名，默认为配置中的文件名
    
    Returns:
        对话历史列表，如果文件不存在则返回空列表
    """
    if filename is None:
        filename = Config.get_history_file_path()
    
    if not os.path.exists(filename):
        return []
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("history", [])
    except (json.JSONDecodeError, IOError):
        return []


def list_history_files() -> List[str]:
    """
    列出所有历史记录文件
    
    Returns:
        历史记录文件路径列表
    """
    history_dir = Config.get_history_dir()
    if not os.path.exists(history_dir):
        return []
    
    files = []
    for f in os.listdir(history_dir):
        if f.endswith('.json'):
            files.append(os.path.join(history_dir, f))
    return sorted(files)


def delete_history_file(filename: str) -> bool:
    """
    删除指定的历史记录文件
    
    Args:
        filename: 要删除的文件名
    
    Returns:
        是否删除成功
    """
    try:
        os.remove(filename)
        return True
    except (OSError, FileNotFoundError):
        return False


def save_history_with_timestamp(history: List[Dict[str, str]]) -> str:
    """
    使用时间戳保存对话历史为新文件
    
    Args:
        history: 对话历史列表
    
    Returns:
        保存的文件路径
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"history_{timestamp}.json"
    filepath = os.path.join(Config.get_history_dir(), filename)
    save_history(history, filepath)
    return filepath


def get_history_info(filename: str) -> Optional[dict]:
    """
    获取历史记录文件的信息
    
    Args:
        filename: 历史记录文件名
    
    Returns:
        包含文件信息的字典
    """
    if not os.path.exists(filename):
        return None
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            history = data.get("history", [])
            return {
                "filename": os.path.basename(filename),
                "filepath": filename,
                "save_time": data.get("save_time"),
                "message_count": len(history),
                "title": data.get("title", _generate_title(history)),
                "preview": _get_preview(history)
            }
    except (json.JSONDecodeError, IOError):
        return None


def create_new_session() -> str:
    """
    创建一个新的会话文件
    
    Returns:
        新会话的文件路径
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"history_{timestamp}.json"
    filepath = os.path.join(Config.get_history_dir(), filename)
    
    data = {
        "save_time": datetime.now().isoformat(),
        "history": [],
        "title": "新对话"
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return filepath


def get_all_sessions() -> List[dict]:
    """
    获取所有会话列表
    
    Returns:
        会话信息列表
    """
    files = list_history_files()
    sessions = []
    for filepath in files:
        info = get_history_info(filepath)
        if info:
            sessions.append(info)
    return sorted(sessions, key=lambda x: x.get("save_time", ""), reverse=True)


def _generate_title(history: List[Dict[str, str]]) -> str:
    """
    根据对话历史生成标题
    
    Args:
        history: 对话历史列表
    
    Returns:
        生成的标题
    """
    for msg in history:
        if msg.get("role") == "user":
            content = msg.get("content", "")
            return content[:30] + "..." if len(content) > 30 else content
    return "新对话"


def _get_preview(history: List[Dict[str, str]]) -> str:
    """
    获取对话预览
    
    Args:
        history: 对话历史列表
    
    Returns:
        预览文本
    """
    content = ""
    for msg in history[-3:]:  # 取最后3条消息
        role = "你" if msg.get("role") == "user" else "AI"
        content += f"{role}: {msg.get('content', '')[:20]}..." if len(msg.get('content', '')) > 20 else f"{role}: {msg.get('content', '')}"
        content += "\n"
    return content.strip()


# ==================== 导出功能 ====================

def export_history(
    history: List[Dict[str, str]],
    filename: str = None,
    format: str = "md"
) -> str:
    """
    导出对话历史到文件
    
    Args:
        history: 对话历史列表
        filename: 导出文件名（不含扩展名），默认为时间戳
        format: 导出格式，支持 'md'（Markdown）、'txt'（纯文本）、'json'
    
    Returns:
        导出的文件路径
    """
    if filename is None:
        filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # 确定导出目录
    export_dir = os.path.join(Config.get_history_dir(), "exports")
    os.makedirs(export_dir, exist_ok=True)
    
    # 根据格式生成内容和扩展名
    if format == "md":
        content = _format_markdown(history)
        ext = ".md"
    elif format == "txt":
        content = _format_text(history)
        ext = ".txt"
    elif format == "json":
        content = _format_json(history)
        ext = ".json"
    else:
        raise ValueError(f"不支持的格式: {format}")
    
    # 写入文件
    filepath = os.path.join(export_dir, filename + ext)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return filepath


def _format_markdown(history: List[Dict[str, str]]) -> str:
    """
    格式化为 Markdown 格式
    
    Args:
        history: 对话历史列表
    
    Returns:
        Markdown 格式的文本
    """
    lines = []
    lines.append(f"# 对话记录")
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"消息数量: {len([m for m in history if m.get('role') in ['user', 'assistant']])}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    for msg in history:
        role = msg.get("role")
        content = msg.get("content", "")
        
        if role == "user":
            lines.append("**你:**")
            lines.append(content)
            lines.append("")
        elif role == "assistant":
            lines.append("**AI:**")
            lines.append(content)
            lines.append("")
        elif role == "system":
            lines.append(f"*系统提示: {content}*")
            lines.append("")
    
    return "\n".join(lines)


def _format_text(history: List[Dict[str, str]]) -> str:
    """
    格式化为纯文本格式
    
    Args:
        history: 对话历史列表
    
    Returns:
        纯文本格式的文本
    """
    lines = []
    lines.append("=" * 60)
    lines.append(f"对话记录")
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"消息数量: {len([m for m in history if m.get('role') in ['user', 'assistant']])}")
    lines.append("=" * 60)
    lines.append("")
    
    for msg in history:
        role = msg.get("role")
        content = msg.get("content", "")
        
        if role == "user":
            lines.append("你:")
            lines.append(content)
            lines.append("-" * 60)
        elif role == "assistant":
            lines.append("AI:")
            lines.append(content)
            lines.append("-" * 60)
        elif role == "system":
            lines.append(f"【系统】{content}")
            lines.append("-" * 60)
    
    return "\n".join(lines)


def _format_json(history: List[Dict[str, str]]) -> str:
    """
    格式化为 JSON 格式
    
    Args:
        history: 对话历史列表
    
    Returns:
        JSON 格式的文本
    """
    data = {
        "export_time": datetime.now().isoformat(),
        "message_count": len([m for m in history if m.get('role') in ['user', 'assistant']]),
        "history": history
    }
    return json.dumps(data, ensure_ascii=False, indent=2)
