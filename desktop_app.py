"""
AI 多模态助手 - 桌面应用版
使用 CustomTkinter 构建原生桌面 GUI
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import base64
import os
import tempfile
from typing import List, Dict, Optional
from datetime import datetime
import logging
import time  # 添加时间模块用于性能测试
import json  # 用于主题持久化

# 配置日志
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AIDesktopApp")

# 导入核心模块
from core.config import Config
from core.chat import ChatClient
from core.multimodal import MultimodalClient
from core.rag import RAGPipeline
from core.history import (
    save_history, load_history, get_all_sessions,
    create_new_session, delete_history_file
)
from core.utils import copy_to_clipboard


# ==================== 主题持久化 ====================

THEME_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "theme_config.json")

def load_saved_theme() -> str:
    """从配置文件加载保存的主题"""
    try:
        if os.path.exists(THEME_CONFIG_FILE):
            with open(THEME_CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                saved_theme = config.get("theme", "pure_white")
                if saved_theme in THEMES:
                    logger.info(f"已加载保存的主题: {THEMES[saved_theme]['name']}")
                    return saved_theme
    except Exception as e:
        logger.error(f"加载主题配置失败: {e}")
    return "pure_white"  # 默认主题

def save_theme(theme_key: str) -> bool:
    """保存主题到配置文件"""
    try:
        os.makedirs(os.path.dirname(THEME_CONFIG_FILE), exist_ok=True)
        with open(THEME_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"theme": theme_key}, f, ensure_ascii=False, indent=2)
        logger.info(f"已保存主题: {THEMES[theme_key]['name']}")
        return True
    except Exception as e:
        logger.error(f"保存主题配置失败: {e}")
        return False


# ==================== 全局样式配置 ====================

ctk.set_appearance_mode("light")  # 强制浅色模式，让自定义主题生效
ctk.set_default_color_theme("blue")

FONT_TITLE = ("Microsoft YaHei", 18, "bold")
FONT_HEADING = ("Microsoft YaHei", 14, "bold")
FONT_BODY = ("Microsoft YaHei", 12)
FONT_SMALL = ("Microsoft YaHei", 10)

# 颜色主题配置
THEMES = {
    "pure_white": {
        "name": "纯白色",
        "bg_color": "#ffffff",
        "scrollbar_button_color": "#cccccc",
        "user_bubble": "#2d6a9f",
        "ai_bubble": "#f5f5f5",
        "sidebar_color": "#f8f9fa",
        "accent_color": "#2d6a9f"
    },
    "warm_gray": {
        "name": "暖灰色",
        "bg_color": "#f5f5f5",
        "scrollbar_button_color": "#999999",
        "user_bubble": "#4a90e2",
        "ai_bubble": "#ffffff",
        "sidebar_color": "#e8e8e8",
        "accent_color": "#4a90e2"
    },
    "dark_mode": {
        "name": "深色模式",
        "bg_color": "#1a1a2e",
        "scrollbar_button_color": "#555555",
        "user_bubble": "#2d6a9f",
        "ai_bubble": "#16213e",
        "sidebar_color": "#0f3460",
        "accent_color": "#e94560"
    },
    "ocean_blue": {
        "name": "海洋蓝",
        "bg_color": "#e6f2ff",
        "scrollbar_button_color": "#999999",
        "user_bubble": "#0066cc",
        "ai_bubble": "#ffffff",
        "sidebar_color": "#cce6ff",
        "accent_color": "#0066cc"
    },
    "forest_green": {
        "name": "森林绿",
        "bg_color": "#e8f5e9",
        "scrollbar_button_color": "#999999",
        "user_bubble": "#2e7d32",
        "ai_bubble": "#ffffff",
        "sidebar_color": "#c8e6c9",
        "accent_color": "#2e7d32"
    }
}

# 当前主题（从配置文件加载）
CURRENT_THEME = load_saved_theme()
BG_COLOR = THEMES[CURRENT_THEME]["bg_color"]
USER_BUBBLE = THEMES[CURRENT_THEME]["user_bubble"]
AI_BUBBLE = THEMES[CURRENT_THEME]["ai_bubble"]


# ==================== 消息气泡组件 ====================

class ChatBubble(ctk.CTkFrame):
    """聊天气泡组件"""

    def __init__(self, master, role: str, content: str, **kwargs):
        super().__init__(master, **kwargs)
        self.role = role
        self.content = content

        # 气泡颜色（使用当前主题颜色）
        if role == "user":
            bg_color = USER_BUBBLE
            anchor = "e"  # 右对齐
        else:
            bg_color = AI_BUBBLE
            anchor = "w"  # 左对齐

        # 角色标签
        role_text = "你" if role == "user" else "AI"
        self.role_label = ctk.CTkLabel(
            self, text=role_text, font=FONT_SMALL,
            text_color="#888888", anchor=anchor
        )
        self.role_label.pack(anchor=anchor, padx=10, pady=(5, 0))

        # 消息内容
        self.text_box = ctk.CTkTextbox(
            self, font=FONT_BODY, wrap="word",
            fg_color=bg_color, border_width=0
        )
        self.text_box.insert("0.0", content)
        # 优化高度计算：根据字符数估算行数，限制最大高度
        lines = content.count('\n') + 1
        chars_per_line = 50  # 估算每行的字符数
        estimated_lines = max(lines, len(content) // chars_per_line + 1)
        height = min(max(60, estimated_lines * 22 + 20), 400)
        self.text_box.configure(state="disabled", height=height)
        self.text_box.pack(fill="x", padx=10, pady=(2, 5))

    def update_theme(self):
        """更新气泡颜色（主题切换时调用）"""
        if self.role == "user":
            new_color = USER_BUBBLE
        else:
            new_color = AI_BUBBLE
        
        self.text_box.configure(fg_color=new_color)


# ==================== 聊天页面 ====================

class ChatTab(ctk.CTkFrame):
    """聊天页面"""

    def __init__(self, master, main_app):
        super().__init__(master, fg_color="transparent")
        self.main_app = main_app
        self.bubbles = []  # 存储所有聊天气泡引用
        self._stop_generation = False  # 初始化停止标志
        self._build_ui()

    def _build_ui(self):
        # 标题
        title = ctk.CTkLabel(self, text="💬 智能对话", font=FONT_HEADING)
        title.pack(pady=(10, 5))

        # RAG 状态提示
        self.rag_status = ctk.CTkLabel(
            self, text="", font=FONT_SMALL,
            text_color="#4caf50"
        )
        self.rag_status.pack(pady=(0, 5))
        self._update_rag_status()

        # 消息显示区域（可滚动）
        self.chat_scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color="#555555"
        )
        self.chat_scroll.pack(fill="both", expand=True, padx=10, pady=5)

        # 输入区域
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", padx=10, pady=(5, 10))

        self.input_entry = ctk.CTkEntry(
            input_frame, placeholder_text="输入消息，按回车发送...",
            font=FONT_BODY, height=40
        )
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.input_entry.bind("<Return>", lambda e: self._send_message())

        self.send_btn = ctk.CTkButton(
            input_frame, text="发送", width=80, height=40,
            font=FONT_BODY, command=self._send_message
        )
        self.send_btn.pack(side="right")
        
        # 停止按钮（初始隐藏）
        self.stop_btn = ctk.CTkButton(
            input_frame, text="⏹ 停止", width=80, height=40,
            font=FONT_BODY, command=self._stop_generation_handler,
            fg_color="#f44336", hover_color="#d32f2f",
            text_color="white"
        )
        self.stop_btn.pack_forget()  # 初始隐藏

        # 加载历史消息
        self._load_history_messages()

    def _update_rag_status(self):
        """更新 RAG 状态显示"""
        if self.main_app.rag_enabled and self.main_app.rag_pipeline:
            try:
                stats = self.main_app.rag_pipeline.get_stats()
                if stats.get("success") and stats.get("total_documents", 0) > 0:
                    self.rag_status.configure(
                        text=f"📚 RAG 已启用 | {stats['total_documents']} 个文档，{stats['total_chunks']} 个片段"
                    )
                else:
                    self.rag_status.configure(text="📚 RAG 已启用（未上传文档）")
            except Exception:
                self.rag_status.configure(text="📚 RAG 状态获取失败")
        else:
            self.rag_status.configure(text="")

    def _load_history_messages(self):
        """加载历史消息到界面"""
        for widget in self.chat_scroll.winfo_children():
            widget.destroy()

        messages = self.main_app.messages
        for msg in messages:
            if msg["role"] in ["user", "assistant"]:
                bubble = ChatBubble(
                    self.chat_scroll,
                    role=msg["role"],
                    content=msg["content"]
                )
                bubble.pack(fill="x", pady=2)
                # 存储引用
                self.bubbles.append(bubble)

        # 滚动到底部
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        """滚动到消息底部"""
        self.chat_scroll.update_idletasks()
        self.chat_scroll._parent_canvas.yview_moveto(1.0)

    def _send_message(self):
        """发送消息"""
        prompt = self.input_entry.get().strip()
        if not prompt:
            return
        
        self.input_entry.delete(0, "end")
        self.send_btn.configure(state="disabled", text="思考中...")
        
        # 隐藏发送按钮，显示停止按钮
        self.send_btn.pack_forget()
        self.stop_btn.pack(side="right", padx=(5, 0))
        
        # 重置停止标志
        self._stop_generation = False

        # 显示用户消息
        self.main_app.messages.append({"role": "user", "content": prompt})
        user_bubble = ChatBubble(self.chat_scroll, role="user", content=prompt)
        user_bubble.pack(fill="x", pady=2)
        # 存储引用
        self.bubbles.append(user_bubble)
        self._scroll_to_bottom()

        # 在新线程中调用 API
        threading.Thread(
            target=self._call_api, args=(prompt,), daemon=True
        ).start()

    def _call_api(self, prompt: str):
        """调用 API（在后台线程中执行）"""
        try:
            # 使用延迟初始化获取聊天客户端
            chat_client = self.main_app._ensure_chat_client()
            
            if not chat_client:
                logger.error("聊天客户端未初始化")
                self.main_app.after(0, lambda: self._show_error("聊天客户端未初始化，请检查 API Key 配置"))
                return
            
            logger.info(f"开始调用 API，提示长度: {len(prompt)} 字符")
            
            # 检查是否启用 RAG
            if self.main_app.rag_enabled:
                rag_pipeline = self.main_app._ensure_rag_pipeline()
                if rag_pipeline:
                    try:
                        # 先检索相关文档（显示检索进度）
                        self.main_app.after(0, lambda: self._show_typing_animation("正在检索文档..."))
                        
                        retrieved = rag_pipeline.retrieve(
                            prompt, top_k=3
                        )
                        logger.info(f"RAG 检索到 {len(retrieved)} 条相关文档")
                        
                        # 使用 RAG 流式输出
                        self.main_app.after(0, lambda: self._start_streaming(rag_pipeline, prompt))
                        
                    except Exception as e:
                        # RAG 失败，降级为普通对话
                        logger.warning(f"RAG 失败: {e}，降级为普通对话")
                        self.main_app.after(0, lambda: self._start_streaming(chat_client, prompt, is_rag=False))
                else:
                    # RAG 未初始化，使用普通对话（流式）
                    logger.info("RAG 管线未初始化，使用流式对话")
                    self.main_app.after(0, lambda: self._start_streaming(chat_client, prompt, is_rag=False))
            else:
                # 普通对话（使用流式输出）
                logger.info("使用流式对话模式")
                self.main_app.after(0, lambda: self._start_streaming(chat_client, prompt, is_rag=False))
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"API 调用失败: {error_msg}")
            self.main_app.after(0, lambda: self._show_error(f"发送失败: {error_msg}"))
    
    def _start_streaming(self, client, prompt, is_rag=True):
        """开始流式输出"""
        try:
            # 显示打字动画
            self._show_typing_animation()
            
            # 创建流式输出气泡
            self._create_streaming_bubble()
            
            # 启动后台线程进行流式输出
            def stream_worker():
                try:
                    full_response = ""
                    
                    if is_rag:
                        # RAG 流式输出
                        for chunk in client.stream_chat_with_context(prompt, top_k=3):
                            if self._stop_generation:  # 检查停止标志
                                break
                            full_response += chunk
                            self.main_app.after(0, lambda c=chunk: self._update_streaming_bubble_optimized(c))
                    else:
                        # 普通对话流式输出
                        messages = self.main_app.messages + [{"role": "user", "content": prompt}]
                        for chunk in client.stream_chat(messages):
                            if self._stop_generation:  # 检查停止标志
                                break
                            full_response += chunk
                            self.main_app.after(0, lambda c=chunk: self._update_streaming_bubble_optimized(c))
                    
                    # 流式输出完成
                    logger.info(f"流式输出完成，响应长度: {len(full_response)} 字符")
                    
                    # 保存到消息历史
                    self.main_app.messages.append({"role": "assistant", "content": full_response})
                    
                    # 保存历史
                    save_history(self.main_app.messages, self.main_app.current_session)
                    
                    # 恢复UI状态
                    self.main_app.after(0, lambda: self._finish_streaming())
                    
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"流式输出失败: {error_msg}")
                    self.main_app.after(0, lambda: self._show_error(f"流式输出失败: {error_msg}"))
            
            # 启动后台线程
            self._stream_thread = threading.Thread(target=stream_worker, daemon=True)
            self._stream_thread.start()
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"启动流式输出失败: {error_msg}")
            self.main_app.after(0, lambda: self._show_error(f"启动失败: {error_msg}"))
    
    def _show_typing_animation(self, message="AI 正在思考"):
        """显示打字动画"""
        # 创建打字动画气泡
        if hasattr(self, 'typing_bubble') and self.typing_bubble:
            self.typing_bubble.destroy()
        
        self.typing_bubble = ChatBubble(
            self.chat_scroll,
            role="assistant",
            content=f"{message} ●●●"
        )
        self.typing_bubble.pack(fill="x", pady=2)
        self.bubbles.append(self.typing_bubble)
        self._scroll_to_bottom()
        
        # 启动动画
        self._typing_animation_running = True
        self._animate_typing()
    
    def _animate_typing(self):
        """动画打字指示器"""
        if not hasattr(self, '_typing_animation_running') or not self._typing_animation_running:
            return
        
        # 更新动画帧
        if hasattr(self, 'typing_bubble') and self.typing_bubble:
            current_text = self.typing_bubble.text_box.get("0.0", "end").strip()
            
            # 简单的点动画
            if "●" in current_text:
                if current_text.endswith("●●●"):
                    new_text = current_text.replace("●●●", "○●●")
                elif current_text.endswith("○●●"):
                    new_text = current_text.replace("○●●", "○○●")
                elif current_text.endswith("○○●"):
                    new_text = current_text.replace("○○●", "●●●")
                else:
                    new_text = current_text.replace("●●●", "○●●")
            else:
                new_text = current_text + " ●●●"
            
            self.typing_bubble.text_box.configure(state="normal")
            self.typing_bubble.text_box.delete("0.0", "end")
            self.typing_bubble.text_box.insert("0.0", new_text)
            self.typing_bubble.text_box.configure(state="disabled")
        
        # 500ms后继续动画
        self.main_app.after(500, self._animate_typing)
    
    def _create_streaming_bubble(self):
        """创建流式输出的气泡（初始为空）"""
        # 停止打字动画
        self._typing_animation_running = False
        
        # 移除打字动画气泡
        if hasattr(self, 'typing_bubble') and self.typing_bubble:
            self.typing_bubble.destroy()
            self.typing_bubble = None
        
        # 创建AI气泡
        self.streaming_bubble = ChatBubble(
            self.chat_scroll, 
            role="assistant", 
            content=""
        )
        self.streaming_bubble.pack(fill="x", pady=2);
        self.bubbles.append(self.streaming_bubble);
        self._scroll_to_bottom();
        
        # 完整的响应内容
        self.streaming_content = "";
        
        # UI更新优化：累计字符数
        self._pending_chars = "";
        self._last_ui_update = time.time()
    
    def _update_streaming_bubble_optimized(self, chunk: str):
        """优化版：更新流式输出的气泡内容（减少UI更新频率）"""
        # 累加内容
        self.streaming_content += chunk
        self._pending_chars += chunk
        
        # 优化策略：每100个字符或每200ms更新一次UI
        current_time = time.time()
        should_update = (
            len(self._pending_chars) >= 100 or  # 累计100字符
            current_time - self._last_ui_update >= 0.2  # 或200ms超时
        )
        
        if should_update:
            # 更新气泡显示
            self.streaming_bubble.text_box.configure(state="normal")
            self.streaming_bubble.text_box.delete("0.0", "end")
            self.streaming_bubble.text_box.insert("0.0", self.streaming_content)
            
            # 动态调整高度
            lines = self.streaming_content.count('\n') + 1
            chars_per_line = 50
            estimated_lines = max(lines, len(self.streaming_content) // chars_per_line + 1)
            height = min(max(60, estimated_lines * 22 + 20), 400)
            self.streaming_bubble.text_box.configure(height=height)
            
            self.streaming_bubble.text_box.configure(state="disabled")
            
            # 滚动到底部
            self._scroll_to_bottom()
            
            # 重置累计
            self._pending_chars = ""
            self._last_ui_update = current_time
    
    def _finish_streaming(self):
        """完成流式输出，恢复UI状态"""
        # 确保最后一次更新显示完整内容
        if hasattr(self, 'streaming_bubble') and self.streaming_bubble:
            self.streaming_bubble.text_box.configure(state="normal")
            self.streaming_bubble.text_box.delete("0.0", "end")
            self.streaming_bubble.text_box.insert("0.0", self.streaming_content)
            self.streaming_bubble.text_box.configure(state="disabled")
        
        # 恢复按钮状态
        self.send_btn.configure(state="normal", text="发送")
        
        # 隐藏停止按钮
        if hasattr(self, 'stop_btn'):
            self.stop_btn.pack_forget()
        
        # 更新 RAG 状态
        self._update_rag_status()
        
        # 重置停止标志
        self._stop_generation = False
    
    def _stop_generation_handler(self):
        """停止生成按钮的回调函数"""
        self._stop_generation = True
        logger.info("用户停止了生成")
        
        # 立即更新UI
        if hasattr(self, 'streaming_bubble') and self.streaming_bubble:
            current_content = self.streaming_content
            self.streaming_bubble.text_box.configure(state="normal")
            self.streaming_bubble.text_box.delete("0.0", "end")
            self.streaming_bubble.text_box.insert("0.0", current_content + "\n\n[生成已停止]")
            self.streaming_bubble.text_box.configure(state="disabled")
        
        # 恢复UI状态
        self._finish_streaming()
    
    def _show_error(self, error_msg: str):
        """显示错误信息"""
        # 停止打字动画
        self._typing_animation_running = False
        
        # 移除打字动画气泡
        if hasattr(self, 'typing_bubble') and self.typing_bubble:
            self.typing_bubble.destroy()
            self.typing_bubble = None
        
        # 显示错误气泡
        error_bubble = ChatBubble(
            self.chat_scroll,
            role="assistant",
            content=f"❌ 错误: {error_msg}"
        )
        error_bubble.pack(fill="x", pady=2)
        self.bubbles.append(error_bubble)
        self._scroll_to_bottom()
        
        # 恢复按钮状态
        self.send_btn.configure(state="normal", text="发送")
        
        # 隐藏停止按钮
        if hasattr(self, 'stop_btn'):
            self.stop_btn.pack_forget()

    def _display_response(self, response: str):
        """显示 AI 回复（在主线程中调用）"""
        self.main_app.messages.append({"role": "assistant", "content": response})

        # 显示气泡
        ai_bubble = ChatBubble(self.chat_scroll, role="assistant", content=response)
        ai_bubble.pack(fill="x", pady=2)
        # 存储引用
        self.bubbles.append(ai_bubble)
        self._scroll_to_bottom()

        # 保存历史
        save_history(self.main_app.messages, self.main_app.current_session)

        # 恢复按钮状态
        self.send_btn.configure(state="normal", text="发送")

        # 更新 RAG 状态
        self._update_rag_status()

    def _show_error(self, message: str):
        """显示错误"""
        messagebox.showerror("错误", message)
        self.send_btn.configure(state="normal", text="发送")


# ==================== 图片页面 ====================

class ImageTab(ctk.CTkFrame):
    """图片问答页面"""

    def __init__(self, master, main_app):
        super().__init__(master, fg_color="transparent")
        self.main_app = main_app
        self.image_base64 = None
        self._build_ui()

    def _build_ui(self):
        title = ctk.CTkLabel(self, text="🖼️ 图片问答", font=FONT_HEADING)
        title.pack(pady=(10, 10))

        # 图片预览区域
        self.image_frame = ctk.CTkFrame(self, height=250, fg_color=("#e0e0e0", "#2a2a2a"))
        self.image_frame.pack(fill="x", padx=10, pady=5)
        self.image_frame.pack_propagate(False)

        self.image_label = ctk.CTkLabel(
            self.image_frame,
            text="请上传图片\n支持 PNG、JPG、JPEG、WEBP、GIF",
            font=FONT_BODY, text_color="#888888"
        )
        self.image_label.pack(expand=True)

        # 按钮区域
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=5)

        self.upload_btn = ctk.CTkButton(
            btn_frame, text="上传图片", width=120,
            command=self._upload_image
        )
        self.upload_btn.pack(side="left", padx=(0, 10))

        self.clear_btn = ctk.CTkButton(
            btn_frame, text="清除图片", width=120,
            fg_color="#555555", hover_color="#666666",
            command=self._clear_image
        )
        self.clear_btn.pack(side="left")

        # OCR 按钮
        self.ocr_btn = ctk.CTkButton(
            self, text="🔍 OCR 文字识别", height=35,
            font=FONT_BODY, command=self._do_ocr
        )
        self.ocr_btn.pack(fill="x", padx=10, pady=5)

        # OCR 结果
        self.ocr_result = ctk.CTkTextbox(
            self, height=100, font=FONT_BODY, wrap="word"
        )
        self.ocr_result.pack(fill="x", padx=10, pady=(0, 5))
        self.ocr_result.insert("0.0", "OCR 结果将显示在这里...")
        self.ocr_result.configure(state="disabled")

        # 图片问答输入
        self.image_qa_label = ctk.CTkLabel(
            self, text="关于图片的问题：", font=FONT_BODY
        )
        self.image_qa_label.pack(anchor="w", padx=10)

        self.image_qa_entry = ctk.CTkEntry(
            self, placeholder_text="输入关于图片的问题...",
            font=FONT_BODY, height=35
        )
        self.image_qa_entry.pack(fill="x", padx=10, pady=(2, 5))
        self.image_qa_entry.bind("<Return>", lambda e: self._ask_image())

        self.image_qa_btn = ctk.CTkButton(
            self, text="提问", height=35,
            font=FONT_BODY, command=self._ask_image
        )
        self.image_qa_btn.pack(fill="x", padx=10, pady=(0, 5))

        # 回答显示
        self.image_answer = ctk.CTkTextbox(
            self, font=FONT_BODY, wrap="word"
        )
        self.image_answer.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.image_answer.insert("0.0", "回答将显示在这里...")
        self.image_answer.configure(state="disabled")

    def _upload_image(self):
        """上传图片"""
        logger.info("开始上传图片")
        file_path = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[
                ("图片文件", "*.png *.jpg *.jpeg *.webp *.gif"),
                ("所有文件", "*.*")
            ]
        )
        if not file_path:
            logger.info("用户取消图片上传")
            return

        try:
            logger.info(f"读取图片文件: {file_path}")
            # 读取并编码图片
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            ext = file_path.lower().split(".")[-1]
            mime_types = {
                "png": "image/png", "jpg": "image/jpeg",
                "jpeg": "image/jpeg", "webp": "image/webp",
                "gif": "image/gif"
            }
            mime = mime_types.get(ext, "image/jpeg")
            self.image_base64 = f"data:{mime};base64,{base64.b64encode(file_bytes).decode()}"
            logger.info(f"图片编码完成，大小: {len(self.image_base64)} 字符")

            # 显示图片预览
            from PIL import Image
            import io
            img_data = base64.b64decode(self.image_base64.split(",")[1])
            img = Image.open(io.BytesIO(img_data))
            img.thumbnail((300, 200))
            ctk_img = ctk.CTkImage(img, size=(300, 200))

            self.image_label.configure(image=ctk_img, text="")
            self.image_label.image = ctk_img  # 保持引用
            
            # 设置多模态客户端上下文（使用延迟初始化）
            multimodal_client = self.main_app._ensure_multimodal_client()
            if multimodal_client:
                multimodal_client.set_image_context(self.image_base64)
                logger.info("已设置图片上下文到多模态客户端")
            else:
                logger.warning("多模态客户端初始化失败，无法设置图片上下文")

        except Exception as e:
            logger.error(f"图片处理失败: {str(e)}")
            messagebox.showerror("错误", f"图片处理失败: {str(e)}")

    def _clear_image(self):
        """清除图片"""
        logger.info("清除图片")
        self.image_base64 = None
        self.image_label.configure(image=None, text="请上传图片\n支持 PNG、JPG、JPEG、WEBP、GIF")
        self.image_label.image = None
        
        # 清除多模态客户端的图片上下文（使用延迟初始化）
        multimodal_client = self.main_app._ensure_multimodal_client()
        if multimodal_client:
            multimodal_client.clear_image_context()
            logger.info("已清除多模态客户端的图片上下文")
        else:
            logger.warning("多模态客户端未初始化，无法清除图片上下文")

    def _do_ocr(self):
        """执行 OCR 文字识别"""
        logger.info("开始 OCR 文字识别")
        if not self.image_base64:
            logger.warning("未上传图片，无法执行 OCR")
            messagebox.showwarning("提示", "请先上传图片")
            return

        # 使用延迟初始化获取多模态客户端
        multimodal_client = self.main_app._ensure_multimodal_client()
        if not multimodal_client:
            logger.error("多模态客户端未初始化，无法执行 OCR")
            messagebox.showerror("错误", "多模态客户端未初始化")
            return

        self.ocr_btn.configure(state="disabled", text="识别中...")
        self.ocr_result.configure(state="normal")
        self.ocr_result.delete("0.0", "end")
        self.ocr_result.insert("0.0", "正在识别...")
        self.ocr_result.configure(state="disabled")
        logger.info("OCR 识别中...")

        threading.Thread(
            target=self._ocr_thread, daemon=True
        ).start()

    def _ocr_thread(self):
        """OCR 线程"""
        try:
            logger.info("OCR 线程开始执行")
            multimodal_client = self.main_app._ensure_multimodal_client()
            if not multimodal_client:
                raise Exception("多模态客户端未初始化")
            
            result = multimodal_client.ocr_image(
                image_base64=self.image_base64
            )
            logger.info(f"OCR 识别成功，结果长度: {len(result)} 字符")
            self.main_app.after(0, lambda: self._ocr_done(result))
        except Exception as e:
            logger.error(f"OCR 识别失败: {str(e)}")
            self.main_app.after(0, lambda: self._ocr_error(str(e)))

    def _ocr_done(self, result: str):
        self.ocr_result.configure(state="normal")
        self.ocr_result.delete("0.0", "end")
        self.ocr_result.insert("0.0", result)
        self.ocr_result.configure(state="disabled")
        self.ocr_btn.configure(state="normal", text="🔍 OCR 文字识别")

    def _ocr_error(self, error: str):
        self.ocr_result.configure(state="normal")
        self.ocr_result.delete("0.0", "end")
        self.ocr_result.insert("0.0", f"识别失败: {error}")
        self.ocr_result.configure(state="disabled")
        self.ocr_btn.configure(state="normal", text="🔍 OCR 文字识别")

    def _ask_image(self):
        """提问关于图片的问题"""
        question = self.image_qa_entry.get().strip()
        if not question:
            logger.warning("问题为空，不执行提问")
            return

        if not self.image_base64:
            logger.warning("未上传图片，无法提问")
            messagebox.showwarning("提示", "请先上传图片")
            return

        logger.info(f"开始图片问答，问题: {question[:50]}...")
        
        # 使用延迟初始化获取多模态客户端
        multimodal_client = self.main_app._ensure_multimodal_client()
        if not multimodal_client:
            logger.error("多模态客户端未初始化，无法提问")
            messagebox.showerror("错误", "多模态客户端未初始化")
            return

        self.image_qa_btn.configure(state="disabled", text="分析中...")
        self.image_answer.configure(state="normal")
        self.image_answer.delete("0.0", "end")
        self.image_answer.insert("0.0", "正在分析图片...")
        self.image_answer.configure(state="disabled")
        logger.info("图片问答进行中...")

        threading.Thread(
            target=self._ask_image_thread, args=(question,), daemon=True
        ).start()

    def _ask_image_thread(self, question: str):
        try:
            logger.info(f"图片问答线程开始执行，问题: {question[:50]}...")
            multimodal_client = self.main_app._ensure_multimodal_client()
            if not multimodal_client:
                raise Exception("多模态客户端未初始化")
            
            response = multimodal_client.chat_with_image(
                messages=[{"role": "user", "content": question}],
                image_base64=self.image_base64
            )
            logger.info(f"图片问答成功，响应长度: {len(response)} 字符")
            self.main_app.after(0, lambda: self._ask_image_done(response))
        except Exception as e:
            logger.error(f"图片问答失败: {str(e)}")
            self.main_app.after(0, lambda: self._ask_image_error(str(e)))

    def _ask_image_done(self, response: str):
        self.image_answer.configure(state="normal")
        self.image_answer.delete("0.0", "end")
        self.image_answer.insert("0.0", response)
        self.image_answer.configure(state="disabled")
        self.image_qa_btn.configure(state="normal", text="提问")

    def _ask_image_error(self, error: str):
        self.image_answer.configure(state="normal")
        self.image_answer.delete("0.0", "end")
        self.image_answer.insert("0.0", f"分析失败: {error}")
        self.image_answer.configure(state="disabled")
        self.image_qa_btn.configure(state="normal", text="提问")


# ==================== RAG 页面 ====================

    def update_theme(self):
        """更新主题（切换主题时调用）"""
        # 更新图片标签背景
        self.image_label.configure(fg_color=BG_COLOR)
        
        # 更新OCR结果和回答显示的背景
        try:
            self.ocr_result.configure(fg_color=AI_BUBBLE)
            self.image_answer.configure(fg_color=AI_BUBBLE)
        except:
            pass
        
        self.update_idletasks()

class RAGTab(ctk.CTkFrame):
    """RAG 文档问答页面"""

    def __init__(self, master, main_app):
        super().__init__(master, fg_color="transparent")
        self.main_app = main_app
        self._build_ui()

    def _build_ui(self):
        title = ctk.CTkLabel(self, text="📚 文档问答", font=FONT_HEADING)
        title.pack(pady=(10, 10))

        # 文档上传区域
        upload_frame = ctk.CTkFrame(self)
        upload_frame.pack(fill="x", padx=10, pady=5)

        upload_label = ctk.CTkLabel(
            upload_frame,
            text="上传文档（支持 TXT、PDF、MD、DOCX、HTML、CSV）",
            font=FONT_BODY
        )
        upload_label.pack(side="left", padx=10, pady=10)

        upload_btn = ctk.CTkButton(
            upload_frame, text="选择文件", width=120,
            command=self._upload_documents
        )
        upload_btn.pack(side="right", padx=10, pady=10)

        # 文档列表
        list_label = ctk.CTkLabel(
            self, text="已上传文档：", font=FONT_BODY
        )
        list_label.pack(anchor="w", padx=10, pady=(10, 2))

        self.doc_list_frame = ctk.CTkScrollableFrame(
            self, height=150, fg_color=("#e0e0e0", "#2a2a2a")
        )
        self.doc_list_frame.pack(fill="x", padx=10, pady=(0, 5))
        self._refresh_doc_list()

        # 清空按钮
        clear_btn = ctk.CTkButton(
            self, text="🗑️ 清空所有文档",
            fg_color="#d32f2f", hover_color="#b71c1c",
            height=30, command=self._clear_all_docs
        )
        clear_btn.pack(fill="x", padx=10, pady=5)

        # 统计信息
        self.stats_label = ctk.CTkLabel(self, text="", font=FONT_SMALL)
        self.stats_label.pack(pady=5)
        self._refresh_stats()

        # 问答区域
        qa_label = ctk.CTkLabel(
            self, text="基于文档提问：", font=FONT_BODY
        )
        qa_label.pack(anchor="w", padx=10, pady=(10, 2))

        self.rag_query = ctk.CTkEntry(
            self, placeholder_text="输入问题，例如：文档中关于XX的说明是什么？",
            font=FONT_BODY, height=35
        )
        self.rag_query.pack(fill="x", padx=10, pady=(0, 5))
        self.rag_query.bind("<Return>", lambda e: self._ask_rag())

        self.rag_ask_btn = ctk.CTkButton(
            self, text="提问", height=35,
            font=FONT_BODY, command=self._ask_rag
        )
        self.rag_ask_btn.pack(fill="x", padx=10, pady=(0, 5))

        # 回答显示
        self.rag_answer = ctk.CTkTextbox(
            self, font=FONT_BODY, wrap="word"
        )
        self.rag_answer.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.rag_answer.insert("0.0", "回答将显示在这里...\n\n参考文档片段也会显示在这里。")
        self.rag_answer.configure(state="disabled")

    def update_theme(self):
        """更新主题（切换主题时调用）"""
        # 更新文档列表背景
        try:
            self.doc_list_frame.configure(fg_color=BG_COLOR)
            self.rag_answer.configure(fg_color=AI_BUBBLE)
        except:
            pass
        
        self.update_idletasks()
        
        # 刷新文档列表以更新颜色
        self._refresh_doc_list()

    def _refresh_doc_list(self):
        """刷新文档列表"""
        logger.info("刷新文档列表")
        for widget in self.doc_list_frame.winfo_children():
            widget.destroy()

        # 使用延迟初始化获取 RAG 管线
        rag_pipeline = self.main_app._ensure_rag_pipeline()
        if not rag_pipeline:
            logger.warning("RAG 功能未初始化")
            label = ctk.CTkLabel(
                self.doc_list_frame, text="RAG 功能未初始化",
                text_color="#ff0000"
            )
            label.pack(pady=10)
            return

        try:
            docs = rag_pipeline.get_document_list()
            if not docs:
                logger.info("暂无上传文档")
                label = ctk.CTkLabel(
                    self.doc_list_frame, text="暂无上传文档",
                    text_color="#888888"
                )
                label.pack(pady=10)
            else:
                logger.info(f"已加载 {len(docs)} 个文档")
                for doc in docs:
                    doc_frame = ctk.CTkFrame(self.doc_list_frame)
                    doc_frame.pack(fill="x", pady=2)

                    icon_map = {"txt": "📝", "md": "📝", "pdf": "📕", "doc": "📄", "docx": "📄", "html": "🌐", "htm": "🌐", "csv": "📊"}
                    icon = icon_map.get(doc["extension"], "📎")

                    label = ctk.CTkLabel(
                        doc_frame,
                        text=f"{icon} {doc['display_name']} ({doc['chunks']} 片段)",
                        font=FONT_SMALL, anchor="w"
                    )
                    label.pack(side="left", fill="x", expand=True, padx=5, pady=2)

                    del_btn = ctk.CTkButton(
                        doc_frame, text="删除", width=60, height=25,
                        fg_color="#d32f2f", hover_color="#b71c1c",
                        font=FONT_SMALL,
                        command=lambda f=doc["filename"]: self._delete_doc(f)
                    )
                    del_btn.pack(side="right", padx=5, pady=2)
        except Exception as e:
            logger.error(f"加载文档列表失败: {str(e)}")
            label = ctk.CTkLabel(
                self.doc_list_frame, text=f"加载失败: {str(e)}",
                text_color="#ff0000"
            )
            label.pack(pady=10)

    def _refresh_stats(self):
        """刷新统计信息"""
        logger.info("刷新统计信息")
        # 使用延迟初始化获取 RAG 管线
        rag_pipeline = self.main_app._ensure_rag_pipeline()
        if not rag_pipeline:
            logger.warning("RAG 未初始化")
            self.stats_label.configure(text="RAG 未初始化")
            return
        try:
            stats = rag_pipeline.get_stats()
            if stats.get("success"):
                logger.info(f"统计信息：{stats['total_documents']} 个文档，{stats['total_chunks']} 个片段")
                self.stats_label.configure(
                    text=f"📊 总计：{stats['total_documents']} 个文档，{stats['total_chunks']} 个片段"
                )
            else:
                logger.info("暂无文档")
                self.stats_label.configure(text="📊 暂无文档")
        except Exception as e:
            logger.error(f"统计获取失败: {str(e)}")
            self.stats_label.configure(text="📊 统计获取失败")

    def _upload_documents(self):
        """上传文档"""
        logger.info("开始上传文档")
        # 使用延迟初始化获取 RAG 管线
        rag_pipeline = self.main_app._ensure_rag_pipeline()
        if not rag_pipeline:
            logger.error("RAG 功能未初始化，无法上传文档")
            messagebox.showerror("错误", "RAG 功能未初始化")
            return

        file_paths = filedialog.askopenfilenames(
            title="选择文档",
            filetypes=[
                ("所有支持的格式", "*.txt *.pdf *.md *.doc *.docx *.html *.htm *.csv"),
                ("文本文件", "*.txt *.md"),
                ("PDF 文件", "*.pdf"),
                ("Word 文件", "*.doc *.docx"),
                ("网页文件", "*.html *.htm"),
                ("CSV 文件", "*.csv"),
                ("所有文件", "*.*")
            ]
        )

        if not file_paths:
            logger.info("用户取消文档上传")
            return

        logger.info(f"选择了 {len(file_paths)} 个文档")
        for file_path in file_paths:
            logger.info(f"处理文档: {file_path}")
            threading.Thread(
                target=self._process_document, args=(file_path,), daemon=True
            ).start()

    def _process_document(self, file_path: str):
        """处理单个文档（后台线程）"""
        try:
            logger.info(f"开始处理文档: {file_path}")
            # 使用延迟初始化获取 RAG 管线
            rag_pipeline = self.main_app._ensure_rag_pipeline()
            if not rag_pipeline:
                raise Exception("RAG 管线未初始化")
            
            result = rag_pipeline.add_document(file_path)
            if result.get("success"):
                logger.info(f"文档处理成功: {file_path}，生成 {result.get('chunks_added', 0)} 个片段")
                self.main_app.after(0, lambda: messagebox.showinfo(
                    "成功", f"{result['message']}，生成 {result['chunks_added']} 个片段"
                ))
            else:
                logger.error(f"文档处理失败: {result.get('message', '未知错误')}")
                self.main_app.after(0, lambda: messagebox.showerror(
                    "失败", result.get("message", "未知错误")
                ))
        except Exception as e:
            logger.error(f"处理文档失败: {str(e)}")
            self.main_app.after(0, lambda: messagebox.showerror(
                "错误", f"处理文档失败: {str(e)}"
            ))
        finally:
            self.main_app.after(0, self._refresh_doc_list)
            self.main_app.after(0, self._refresh_stats)

    def _delete_doc(self, filename: str):
        """删除文档"""
        logger.info(f"开始删除文档: {filename}")
        if messagebox.askyesno("确认", f"确定要删除 {filename} 吗？"):
            try:
                # 使用延迟初始化获取 RAG 管线
                rag_pipeline = self.main_app._ensure_rag_pipeline()
                if not rag_pipeline:
                    raise Exception("RAG 管线未初始化")
                
                result = rag_pipeline.delete_document(filename)
                if result.get("success"):
                    logger.info(f"文档删除成功: {filename}")
                    messagebox.showinfo("成功", result.get("message"))
                else:
                    logger.error(f"文档删除失败: {result.get('message')}")
                    messagebox.showerror("失败", result.get("message"))
            except Exception as e:
                logger.error(f"删除文档失败: {str(e)}")
                messagebox.showerror("错误", f"删除失败: {str(e)}")
            finally:
                self._refresh_doc_list()
                self._refresh_stats()

    def _clear_all_docs(self):
        """清空所有文档"""
        logger.info("开始清空所有文档")
        if not messagebox.askyesno("确认", "确定要清空所有文档吗？此操作不可恢复！"):
            logger.info("用户取消清空文档")
            return

        try:
            # 使用延迟初始化获取 RAG 管线
            rag_pipeline = self.main_app._ensure_rag_pipeline()
            if not rag_pipeline:
                raise Exception("RAG 管线未初始化")
            
            if rag_pipeline.clear_database():
                logger.info("所有文档已清空")
                messagebox.showinfo("成功", "所有文档已清空")
            else:
                logger.error("清空文档失败")
                messagebox.showerror("失败", "清空失败")
        except Exception as e:
            logger.error(f"清空文档失败: {str(e)}")
            messagebox.showerror("错误", f"清空失败: {str(e)}")
        finally:
            self._refresh_doc_list()
            self._refresh_stats()

    def _ask_rag(self):
        """基于文档提问"""
        query = self.rag_query.get().strip()
        if not query:
            logger.warning("问题为空，不执行 RAG 提问")
            return

        logger.info(f"开始 RAG 提问，问题: {query[:50]}...")
        
        # 使用延迟初始化获取 RAG 管线
        rag_pipeline = self.main_app._ensure_rag_pipeline()
        if not rag_pipeline:
            logger.error("RAG 功能未初始化，无法提问")
            messagebox.showerror("错误", "RAG 功能未初始化")
            return

        self.rag_ask_btn.configure(state="disabled", text="检索中...")
        self.rag_answer.configure(state="normal")
        self.rag_answer.delete("0.0", "end")
        self.rag_answer.insert("0.0", "正在检索文档...")
        self.rag_answer.configure(state="disabled")
        logger.info("RAG 检索进行中...")

        threading.Thread(
            target=self._rag_thread, args=(query,), daemon=True
        ).start()

    def _rag_thread(self, query: str):
        """RAG 问答线程"""
        try:
            logger.info(f"RAG 问答线程开始执行，问题: {query[:50]}...")
            
            # 使用延迟初始化获取 RAG 管线
            rag_pipeline = self.main_app._ensure_rag_pipeline()
            if not rag_pipeline:
                raise Exception("RAG 管线未初始化")
            
            # 先检索
            logger.info("开始检索相关文档...")
            retrieved = rag_pipeline.retrieve(query, top_k=5)
            logger.info(f"检索完成，找到 {len(retrieved)} 条相关文档")

            # 生成回答
            logger.info("开始生成回答...")
            response = rag_pipeline.chat_with_context(query, top_k=5)
            logger.info(f"回答生成成功，响应长度: {len(response)} 字符")

            # 更新 UI
            self.main_app.after(0, lambda: self._rag_done(response, retrieved))
        except Exception as e:
            logger.error(f"RAG 问答失败: {str(e)}")
            self.main_app.after(0, lambda: self._rag_error(str(e)))

    def _rag_done(self, response: str, retrieved: list):
        self.rag_answer.configure(state="normal")
        self.rag_answer.delete("0.0", "end")

        if retrieved:
            self.rag_answer.insert("end", "【参考文档】\n")
            for i, item in enumerate(retrieved):
                metadata = item.get("metadata", {})
                display_name = metadata.get("display_name", "未知文档")
                self.rag_answer.insert("end", f"\n▶ 文档 {i+1}: {display_name}\n")
                content_preview = item["content"][:200] + "..." if len(item["content"]) > 200 else item["content"]
                self.rag_answer.insert("end", f"{content_preview}\n")
            self.rag_answer.insert("end", "\n" + "=" * 50 + "\n\n【回答】\n")

        self.rag_answer.insert("end", response)
        self.rag_answer.configure(state="disabled")
        self.rag_ask_btn.configure(state="normal", text="提问")

    def _rag_error(self, error: str):
        self.rag_answer.configure(state="normal")
        self.rag_answer.delete("0.0", "end")
        self.rag_answer.insert("0.0", f"问答失败: {error}")
        self.rag_answer.configure(state="disabled")
        self.rag_ask_btn.configure(state="normal", text="提问")


# ==================== 主应用窗口 ====================

class AIDesktopApp(ctk.CTk):
    """AI 多模态助手桌面应用主窗口"""

    def __init__(self):
        super().__init__()

        # 应用数据
        self.messages: List[Dict[str, str]] = []
        self.current_session: Optional[str] = None
        self.chat_client: Optional[ChatClient] = None
        self.multimodal_client: Optional[MultimodalClient] = None
        self.rag_pipeline: Optional[RAGPipeline] = None
        self.rag_enabled: bool = True

        # 初始化
        self._init_window()
        self._init_clients()
        self._init_ui()

    def _init_window(self):
        """初始化窗口"""
        self.title("AI 多模态助手")
        self.geometry("1000x700")
        self.minsize(800, 600)

        # 尝试设置图标（如果存在）
        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
        
        # 强制使用浅色模式，让自定义主题生效
        ctk.set_appearance_mode("light")
        
        # 设置窗口初始背景色（根据当前主题）
        theme = THEMES[CURRENT_THEME]
        self.configure(fg_color=theme["bg_color"])

    def _init_clients(self):
        """初始化 API 客户端（延迟加载模式）"""
        start_time = time.time()
        logger.info("开始初始化客户端（延迟加载模式）")
        
        # 设置为 None，延迟初始化
        self.chat_client = None
        self.multimodal_client = None
        self.rag_pipeline = None
        self.rag_enabled: bool = True
        
        # 标记是否需要初始化
        self._chat_client_initialized = False
        self._multimodal_client_initialized = False
        self._rag_pipeline_initialized = False
        
        # 加载会话（这个必须同步加载）
        try:
            sessions = get_all_sessions()
            if sessions:
                self.current_session = sessions[0]["filepath"]
                loaded = load_history(self.current_session)
                self.messages = loaded if loaded else [{"role": "system", "content": Config.get_system_prompt()}]
            else:
                self.current_session = create_new_session()
                self.messages = [{"role": "system", "content": Config.get_system_prompt()}]
        except Exception as e:
            logger.error(f"加载会话失败: {e}")
            self.current_session = None
            self.messages = [{"role": "system", "content": Config.get_system_prompt()}]
        
        elapsed = time.time() - start_time
        logger.info(f"客户端初始化完成（延迟模式），耗时 {elapsed:.2f} 秒")

    def _init_ui(self):
        """初始化界面"""
        # 左侧边栏（使用当前主题颜色）
        theme = THEMES[CURRENT_THEME]
        self.sidebar = ctk.CTkFrame(self, width=200, fg_color=theme["sidebar_color"])
        self.sidebar.pack(side="left", fill="y", padx=(0, 5))
        self.sidebar.pack_propagate(False)

        self._build_sidebar()

        # 右侧主区域（Tab 视图）- 使用当前主题颜色
        theme = THEMES[CURRENT_THEME]
        self.main_area = ctk.CTkFrame(self, fg_color=theme["bg_color"])
        self.main_area.pack(side="right", fill="both", expand=True)

        self.tab_view = ctk.CTkTabview(self.main_area, fg_color=theme["bg_color"])
        self.tab_view.pack(fill="both", expand=True, padx=5, pady=5)

        # 添加标签页
        self.tab_view.add("聊天")
        self.tab_view.add("图片")
        self.tab_view.add("文档")

        # 创建各页面
        self.chat_tab = ChatTab(self.tab_view.tab("聊天"), self)
        self.chat_tab.pack(fill="both", expand=True)

        self.image_tab = ImageTab(self.tab_view.tab("图片"), self)
        self.image_tab.pack(fill="both", expand=True)

        self.rag_tab = RAGTab(self.tab_view.tab("文档"), self)
        self.rag_tab.pack(fill="both", expand=True)

    def _ensure_chat_client(self):
        """确保聊天客户端已初始化（延迟初始化）"""
        if not self._chat_client_initialized:
            logger.info("开始初始化聊天客户端")
            start_time = time.time()
            try:
                from core.chat import ChatClient
                self.chat_client = ChatClient("moonshot")
                self._chat_client_initialized = True
                elapsed = time.time() - start_time
                logger.info(f"聊天客户端初始化成功，耗时 {elapsed:.2f} 秒")
            except Exception as e:
                logger.error(f"初始化聊天客户端失败: {e}")
                self.chat_client = None
                messagebox.showerror("错误", f"初始化聊天客户端失败: {str(e)}")
        
        return self.chat_client
    
    def _ensure_multimodal_client(self):
        """确保多模态客户端已初始化（延迟初始化）"""
        if not self._multimodal_client_initialized:
            logger.info("开始初始化多模态客户端")
            start_time = time.time()
            try:
                from core.multimodal import MultimodalClient
                self.multimodal_client = MultimodalClient("moonshot")
                self._multimodal_client_initialized = True
                elapsed = time.time() - start_time
                logger.info(f"多模态客户端初始化成功，耗时 {elapsed:.2f} 秒")
            except Exception as e:
                logger.error(f"初始化多模态客户端失败: {e}")
                self.multimodal_client = None
                messagebox.showerror("错误", f"初始化多模态客户端失败: {str(e)}")
        
        return self.multimodal_client
    
    def _ensure_rag_pipeline(self):
        """确保 RAG 管线已初始化（延迟初始化）"""
        if not self._rag_pipeline_initialized:
            logger.info("开始初始化 RAG 管线")
            start_time = time.time()
            try:
                from core.rag import RAGPipeline
                self.rag_pipeline = RAGPipeline()
                self._rag_pipeline_initialized = True
                elapsed = time.time() - start_time
                logger.info(f"RAG 管线初始化成功，耗时 {elapsed:.2f} 秒")
            except Exception as e:
                # 详细的错误日志
                import traceback
                error_details = traceback.format_exc()
                logger.error(f"初始化 RAG 管线失败: {e}")
                logger.error(f"详细错误: {error_details}")
                
                # 提示用户
                error_text = """RAG 文档检索功能初始化失败:

""" + str(e) + """

可能原因:
1. 磁盘空间不足
2. chromadb 目录权限问题
3. 缺少依赖库

其他功能（聊天、图片）仍然可以正常使用。"""
                messagebox.showwarning("RAG 初始化警告", error_text)
                self.rag_pipeline = None
        
        return self.rag_pipeline

    def _build_sidebar(self):
        """构建侧边栏"""
        # Logo / 标题
        logo = ctk.CTkLabel(
            self.sidebar, text="🤖 AI 助手", font=FONT_TITLE
        )
        logo.pack(pady=(20, 10))

        # 会话管理
        session_label = ctk.CTkLabel(
            self.sidebar, text="会话管理", font=FONT_HEADING
        )
        session_label.pack(pady=(20, 5))

        self.new_session_btn = ctk.CTkButton(
            self.sidebar, text="➕ 新建对话",
            command=self._new_session, height=35
        )
        self.new_session_btn.pack(fill="x", padx=10, pady=2)

        # 会话列表（简化版：只显示切换按钮）
        self.session_var = ctk.StringVar(value="")
        self.session_menu = ctk.CTkOptionMenu(
            self.sidebar, variable=self.session_var,
            values=self._get_session_names(),
            command=self._switch_session,
            font=FONT_SMALL
        )
        self.session_menu.pack(fill="x", padx=10, pady=2)

        # RAG 开关
        self.rag_switch = ctk.CTkSwitch(
            self.sidebar, text="启用文档检索",
            command=self._toggle_rag,
            font=FONT_SMALL
        )
        self.rag_switch.pack(pady=(15, 2), padx=10)
        if self.rag_enabled:
            self.rag_switch.select()

        # Token 统计
        stats_label = ctk.CTkLabel(
            self.sidebar, text="使用统计", font=FONT_HEADING
        )
        stats_label.pack(pady=(20, 5))

        self.token_label = ctk.CTkLabel(
            self.sidebar, text="累计 Token: 0", font=FONT_SMALL
        )
        self.token_label.pack(padx=10)

        # 主题设置按钮
        self.settings_btn = ctk.CTkButton(
            self.sidebar, text="🎨 主题设置",
            fg_color=THEMES[CURRENT_THEME]["accent_color"],
            hover_color=THEMES[CURRENT_THEME]["user_bubble"],
            text_color="white",
            font=FONT_BODY,
            height=40,
            command=self._show_settings
        )
        self.settings_btn.pack(side="bottom", fill="x", padx=10, pady=5)

        # 底部关于信息
        about_btn = ctk.CTkButton(
            self.sidebar, text="ℹ️ 关于",
            fg_color="transparent", hover_color=("#c0c0c0", "#333333"),
            font=FONT_SMALL, command=self._show_about
        )
        about_btn.pack(side="bottom", fill="x", padx=10, pady=10)

    def _get_session_names(self) -> list:
        """获取会话名称列表"""
        try:
            sessions = get_all_sessions()
            return [s["title"] for s in sessions] if sessions else [""]
        except Exception:
            return [""]

    def _new_session(self):
        """新建会话"""
        save_history(self.messages, self.current_session)
        self.current_session = create_new_session()
        self.messages = [{"role": "system", "content": Config.get_system_prompt()}]
        self.chat_tab._load_history_messages()
        self.session_var.set("")
        self.session_menu.configure(values=self._get_session_names())
        messagebox.showinfo("提示", "已创建新对话")

    def _switch_session(self, selected_title: str):
        """切换会话"""
        if not selected_title:
            return
        try:
            sessions = get_all_sessions()
            for s in sessions:
                if s["title"] == selected_title:
                    save_history(self.messages, self.current_session)
                    self.current_session = s["filepath"]
                    loaded = load_history(self.current_session)
                    self.messages = loaded if loaded else [{"role": "system", "content": Config.get_system_prompt()}]
                    self.chat_tab._load_history_messages()
                    break
        except Exception as e:
            messagebox.showerror("错误", f"切换会话失败: {str(e)}")

    def _toggle_rag(self):
        """切换 RAG 开关"""
        self.rag_enabled = self.rag_switch.get()
        self.chat_tab._update_rag_status()

    def _show_about(self):
        """显示关于对话框"""
        messagebox.showinfo(
            "关于 AI 多模态助手",
            "AI 多模态助手 v1.0\n\n"
            "功能：\n"
            "• 智能对话（支持多轮）\n"
            "• 图片问答 + OCR 文字识别\n"
            "• 文档上传与问答（RAG）\n\n"
            "技术栈：\n"
            "• Moonshot API (Kimi)\n"
            "• CustomTkinter GUI\n"
            "• ChromaDB + LangChain\n\n"
            "© 2026 jy"
        )

    def _show_settings(self):
        """显示设置对话框"""
        settings_window = ctk.CTkToplevel(self)
        settings_window.title("主题设置")
        settings_window.geometry("500x600")
        settings_window.transient(self)
        settings_window.grab_set()

        # 标题
        title_label = ctk.CTkLabel(
            settings_window, text="选择颜色主题",
            font=FONT_HEADING
        )
        title_label.pack(pady=20)

        # 主题选择
        self.theme_var = ctk.StringVar(value=CURRENT_THEME)

        for theme_key, theme_info in THEMES.items():
            theme_frame = ctk.CTkFrame(settings_window)
            theme_frame.pack(fill="x", padx=20, pady=10)

            # 单选按钮
            radio = ctk.CTkRadioButton(
                theme_frame, text=theme_info["name"],
                variable=self.theme_var, value=theme_key,
                font=FONT_BODY, command=lambda k=theme_key: self._preview_theme(k)
            )
            radio.pack(side="left", padx=10)

            # 预览色块
            preview_frame = ctk.CTkFrame(
                theme_frame, width=100, height=40,
                fg_color=theme_info["bg_color"]
            )
            preview_frame.pack(side="right", padx=10)
            preview_label = ctk.CTkLabel(
                preview_frame, text="预览",
                text_color="#333333" if theme_info["bg_color"] == "#ffffff" else "#ffffff"
            )
            preview_label.pack(expand=True)

        # 应用按钮
        button_frame = ctk.CTkFrame(settings_window, fg_color="transparent")
        button_frame.pack(side="bottom", fill="x", pady=20)

        apply_btn = ctk.CTkButton(
            button_frame, text="应用主题",
            command=lambda: self._apply_theme(settings_window),
            font=FONT_BODY, height=40
        )
        apply_btn.pack(side="left", expand=True, padx=10)

        cancel_btn = ctk.CTkButton(
            button_frame, text="取消",
            command=settings_window.destroy,
            font=FONT_BODY, height=40,
            fg_color="gray", hover_color="#666666"
        )
        cancel_btn.pack(side="right", expand=True, padx=10)

    def _preview_theme(self, theme_key: str):
        """预览主题（可以在这里添加实时预览）"""
        logger.info(f"预览主题: {THEMES[theme_key]['name']}")

    def _apply_theme(self, settings_window):
        """应用选中的主题"""
        global CURRENT_THEME, BG_COLOR, USER_BUBBLE, AI_BUBBLE

        selected_theme = self.theme_var.get()
        if selected_theme not in THEMES:
            messagebox.showerror("错误", "无效的主题选择")
            return

        CURRENT_THEME = selected_theme
        theme = THEMES[selected_theme]

        # 更新全局颜色
        BG_COLOR = theme["bg_color"]
        USER_BUBBLE = theme["user_bubble"]
        AI_BUBBLE = theme["ai_bubble"]

        # 保存主题到配置文件
        if save_theme(selected_theme):
            save_status = "已保存到本地"
        else:
            save_status = "保存失败（已应用但下次启动不会记住）"

        # 应用主题到当前窗口（带动画）
        self._apply_theme_with_animation()

        logger.info(f"已应用主题: {theme['name']} ({save_status})")
        messagebox.showinfo("成功", f"已应用主题: {theme['name']}\n{save_status}")
        settings_window.destroy()

    def _apply_theme_with_animation(self):
        """应用主题并添加平滑过渡动画"""
        # 阶段 1: 临时改变窗口背景色（快速闪烁效果）
        original_bg = self.cget("fg_color")
        transition_color = self._get_transition_color(original_bg)
        self.configure(fg_color=transition_color)
        self.update_idletasks()
        
        # 阶段 2: 50ms 后应用主题
        self.after(50, lambda: self._apply_theme_to_app())
        
        # 阶段 3: 200ms 后恢复（主题已应用）
        self.after(200, lambda: self.configure(fg_color=THEMES[CURRENT_THEME]["bg_color"]))

    def _get_transition_color(self, color):
        """获取过渡颜色（比原色稍暗）"""
        try:
            # 简单的颜色变化
            if color.startswith("#"):
                hex_color = color.lstrip("#")
                rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                # 临时使用稍暗的颜色
                dark_rgb = tuple(max(0, c - 30) for c in rgb)
                return "#{:02x}{:02x}{:02x}".format(*dark_rgb)
        except:
            pass
        return color

    def _apply_theme_to_app(self):
        """将主题应用到当前应用"""
        theme = THEMES[CURRENT_THEME]

        # 更新侧边栏颜色
        self.sidebar.configure(fg_color=theme["sidebar_color"])

        # 更新主区域背景
        self.main_area.configure(fg_color=theme["bg_color"])

        # 更新标签页颜色
        self.tab_view.configure(fg_color=theme["bg_color"])

        # 刷新所有标签页
        for tab_name in ["聊天", "图片", "文档"]:
            tab = self.tab_view.tab(tab_name)
            tab.configure(fg_color=theme["bg_color"])

        # 调用所有 Tab 的 update_theme 方法
        if hasattr(self.chat_tab, 'update_theme'):
            self.chat_tab.update_theme()
        
        if hasattr(self.image_tab, 'update_theme'):
            self.image_tab.update_theme()
        
        if hasattr(self.rag_tab, 'update_theme'):
            self.rag_tab.update_theme()

        self.update_idletasks()

    def run(self):
        """运行应用"""
        self.mainloop()


# ==================== 程序入口 ====================

if __name__ == "__main__":
    app = AIDesktopApp()
    app.run()
