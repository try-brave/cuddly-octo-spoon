"""
Streamlit 应用主入口

提供 AI 助手的 Web 界面，包含：
- 聊天功能
- 图片问答
- RAG 文档问答
- 会话管理
- Token 统计
"""

import streamlit as st
import base64
import os
import tempfile
import time
from typing import Dict, List

# 从 core 包导入所有需要的功能
from core import (
    Config,
    ChatClient,
    MultimodalClient,
    RAGPipeline,
    IntentRouter,
    create_default_intents,
    save_history,
    load_history,
    get_all_sessions,
    create_new_session,
    delete_history_file,
    copy_to_clipboard
)


def initialize_session_state() -> None:
    """初始化 Streamlit 会话状态"""
    # 初始化意图路由器
    if "intent_router" not in st.session_state:
        router = IntentRouter()
        create_default_intents(router)
        
        def ocr_reminder_handler(text: str, context: Dict = None) -> str:
            st.session_state.show_ocr_reminder = True
            return "请上传图片，我来帮你识别图片中的文字。"
        
        def image_qa_reminder_handler(text: str, context: Dict = None) -> str:
            st.session_state.show_image_reminder = True
            return "请上传图片，然后描述你想了解的内容。"
        
        router.register_keyword_intent(
            name="ocr",
            keywords=["识别文字", "提取文字", "OCR", "文字识别", "图片文字"],
            handler=ocr_reminder_handler,
            description="OCR文字识别",
            priority=2
        )
        
        router.register_keyword_intent(
            name="image_qa",
            keywords=["图片", "照片", "图片分析", "分析图片", "看图", "这张图"],
            handler=image_qa_reminder_handler,
            description="图片问答",
            priority=2
        )
        
        st.session_state.intent_router = router

    # 初始化客户端
    if "client" not in st.session_state:
        try:
            st.session_state.client = ChatClient("moonshot")
        except Exception as e:
            st.error(f"初始化聊天客户端失败: {str(e)}")
            st.session_state.client = None

    if "multimodal_client" not in st.session_state:
        try:
            st.session_state.multimodal_client = MultimodalClient("moonshot")
        except Exception as e:
            st.error(f"初始化多模态客户端失败: {str(e)}")
            st.session_state.multimodal_client = None

    if "rag_pipeline" not in st.session_state:
        try:
            st.session_state.rag_pipeline = RAGPipeline()
        except Exception as e:
            st.error(f"RAG 初始化失败: {str(e)}")
            st.session_state.rag_pipeline = None

    # 初始化会话
    if "current_session" not in st.session_state:
        try:
            sessions = get_all_sessions()
            st.session_state.current_session = sessions[0]["filepath"] if sessions else create_new_session()
        except Exception as e:
            st.error(f"加载会话失败: {str(e)}")
            st.session_state.current_session = None

    # 初始化消息
    if "messages" not in st.session_state:
        try:
            loaded = load_history(st.session_state.current_session) if st.session_state.current_session else None
            st.session_state.messages = loaded if loaded else [{"role": "system", "content": "你是一个友好的中文助手"}]
        except Exception as e:
            st.error(f"加载历史记录失败: {str(e)}")
            st.session_state.messages = [{"role": "system", "content": "你是一个友好的中文助手"}]

    # 初始化图片
    if "uploaded_image" not in st.session_state:
        st.session_state.uploaded_image = None
    
    # 图片标签页的图片
    if "image_tab_image" not in st.session_state:
        st.session_state.image_tab_image = None

    # 意图提醒状态
    if "show_ocr_reminder" not in st.session_state:
        st.session_state.show_ocr_reminder = False

    if "show_image_reminder" not in st.session_state:
        st.session_state.show_image_reminder = False

    # RAG 开关
    if "rag_enabled" not in st.session_state:
        st.session_state.rag_enabled = True

    # 累计 Token
    if "total_tokens_used" not in st.session_state:
        st.session_state.total_tokens_used = 0


def render_sidebar() -> None:
    """渲染侧边栏"""
    with st.sidebar:
        # 会话管理
        st.subheader("会话管理")
        
        # 用于触发一次性刷新的标记
        if "needs_rerun" not in st.session_state:
            st.session_state.needs_rerun = False
        
        try:
            if st.button("新建对话"):
                save_history(st.session_state.messages, st.session_state.current_session)
                st.session_state.current_session = create_new_session()
                st.session_state.messages = [{"role": "system", "content": "你是一个友好的中文助手"}]
                st.session_state.uploaded_image = None
                if st.session_state.multimodal_client:
                    st.session_state.multimodal_client.clear_image_context()
                st.session_state.needs_rerun = True
            
            st.divider()
            
            sessions = get_all_sessions()
            if sessions:
                selected_session = st.selectbox(
                    "选择对话",
                    sessions,
                    format_func=lambda x: x["title"],
                    index=next((i for i, s in enumerate(sessions) if s.get("filepath") == st.session_state.current_session), 0)
                )
                
                if selected_session and selected_session.get("filepath") != st.session_state.current_session:
                    save_history(st.session_state.messages, st.session_state.current_session)
                    st.session_state.current_session = selected_session["filepath"]
                    loaded = load_history(selected_session["filepath"])
                    st.session_state.messages = loaded if loaded else [{"role": "system", "content": "你是一个友好的中文助手"}]
                    st.session_state.uploaded_image = None
                    if st.session_state.multimodal_client:
                        st.session_state.multimodal_client.clear_image_context()
                    st.session_state.needs_rerun = True
                
                delete_options = [s for s in sessions if s.get("filepath") != st.session_state.current_session]
                if delete_options:
                    to_delete = st.selectbox("删除对话", [""] + delete_options, format_func=lambda x: x["title"] if isinstance(x, dict) else "")
                    if isinstance(to_delete, dict) and st.button("删除"):
                        delete_history_file(to_delete["filepath"])
                        st.toast(f"已删除: {to_delete['title']}")
                        st.session_state.needs_rerun = True
        except Exception as e:
            st.error(f"会话管理错误: {str(e)}")
        
        st.divider()
        
        # RAG 文档管理
        st.subheader("文档管理")
        
        # RAG 开关
        st.session_state.rag_enabled = st.checkbox("启用文档检索", value=st.session_state.rag_enabled)
        
        # 显示已上传文档列表
        if st.session_state.rag_pipeline:
            try:
                docs = st.session_state.rag_pipeline.get_document_list()
                
                if docs:
                    st.write(f"**已上传文档 ({len(docs)} 个):**")
                    
                    for doc in docs:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            ext_icon = {
                                'txt': '[T]', 'md': '[M]', 'pdf': '[P]',
                                'doc': '[D]', 'docx': '[D]', 'html': '[H]',
                                'htm': '[H]', 'csv': '[C]'
                            }.get(doc['extension'], '[_]')
                            st.text(f"{ext_icon} {doc['display_name']} ({doc['chunks']} 片段)")
                        with col2:
                            if st.button("X", key=f"del_{doc['filename']}"):
                                result = st.session_state.rag_pipeline.delete_document(doc['filename'])
                                if result.get("success"):
                                    st.toast(f"已删除: {doc['display_name']}")
                                else:
                                    st.error(result.get("message", "删除失败"))
                                st.session_state.needs_rerun = True
                else:
                    st.info("暂无上传的文档")
            except Exception as e:
                st.error(f"加载文档列表失败: {str(e)}")
        
        # 清空所有文档
        if st.session_state.rag_pipeline:
            if st.button("清空所有文档"):
                try:
                    if st.session_state.rag_pipeline.clear_database():
                        st.toast("所有文档已清空")
                        st.session_state.needs_rerun = True
                    else:
                        st.error("清空失败")
                except Exception as e:
                    st.error(f"清空文档失败: {str(e)}")
        
        st.divider()
        
        # Token 统计
        st.subheader("使用统计")
        if st.session_state.client and hasattr(st.session_state.client, 'last_usage') and st.session_state.client.last_usage:
            usage = st.session_state.client.last_usage
            total_tokens = usage.get('total_tokens', 0)
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("总Token", total_tokens)
            with col2:
                st.metric("生成Token", completion_tokens)
            
            st.write(f"提示Token: {prompt_tokens}")
        
        # 更新累计统计
        if st.session_state.client and hasattr(st.session_state.client, 'last_usage') and st.session_state.client.last_usage:
            st.session_state.total_tokens_used += st.session_state.client.last_usage.get('total_tokens', 0)
        
        st.metric("累计Token", st.session_state.total_tokens_used)


def render_usage_expander() -> None:
    """渲染使用说明展开面板"""
    with st.expander("使用说明"):
        st.write("""
        **聊天功能:**
        - 在输入框中输入问题，按回车发送
        - 支持多轮对话，会自动保留上下文
        - 可以启用文档检索，让 AI 基于上传的文档回答
        
        **图片功能:**
        - 上传图片后可以进行 OCR 文字识别
        - 可以提问关于图片的问题
        
        **文档功能:**
        - 支持上传 TXT、PDF、Markdown、Word、HTML、CSV 格式
        - 上传后可以基于文档内容进行问答
        - 会显示参考文档来源
        
        **快捷操作:**
        - 复制回答：点击回答下方的复制按钮
        - 重新生成：点击重新生成按钮可以重新获取回答
        """)


def render_chat_tab() -> None:
    """渲染聊天标签页"""
    st.subheader("对话")
    
    # RAG 状态提示
    if st.session_state.rag_enabled and st.session_state.rag_pipeline:
        stats = st.session_state.rag_pipeline.get_stats()
        if stats.get("success") and stats.get("total_documents", 0) > 0:
            st.info(f"RAG 已启用，共 {stats['total_documents']} 个文档，{stats['total_chunks']} 个片段")
    
    # 显示消息
    for i, msg in enumerate(st.session_state.messages):
        if msg["role"] in ["user", "assistant"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
                # 快捷操作：复制和重新生成（仅对助手消息）
                if msg["role"] == "assistant":
                    col1, col2 = st.columns([1, 8])
                    with col1:
                        if st.button("复制", key=f"copy_{i}"):
                            copy_to_clipboard(msg["content"])
                            st.success("已复制")
                    with col2:
                        if st.button("重新生成", key=f"regen_{i}"):
                            # 删除当前助手消息和对应的用户消息
                            if len(st.session_state.messages) >= 2:
                                st.session_state.messages.pop()  # 删除助手消息
                                st.session_state.messages.pop()  # 删除用户消息
                            st.session_state.needs_rerun = True
    
    # 用户输入
    prompt = st.chat_input("说点什么...")
    if prompt:
        if st.session_state.client is None:
            st.error("聊天功能暂不可用，请检查配置")
        else:
            with st.chat_message("user"):
                st.markdown(prompt)
            
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("assistant"):
                start_time = time.time()
                try:
                    # 先进行意图识别
                    intent_result = st.session_state.intent_router.route(prompt)
                    
                    # 如果是高置信度的特定意图且没有图片，则直接响应
                    if intent_result["is_default"] == False and intent_result["score"] >= 0.7 and not st.session_state.uploaded_image:
                        full_response = intent_result["result"]
                        st.markdown(full_response)
                    else:
                        # 检查是否启用 RAG
                        if st.session_state.rag_enabled and st.session_state.rag_pipeline:
                            try:
                                # 先检索相关文档
                                retrieved = st.session_state.rag_pipeline.retrieve(prompt, top_k=3)
                                
                                if retrieved:
                                    st.write("**参考文档:**")
                                    for i, item in enumerate(retrieved):
                                        with st.expander(f"文档 {i+1} - {item['metadata'].get('display_name', '未知')}"):
                                            st.write(item["content"])
                                    
                                    # 使用 RAG 流式对话
                                    response_stream = st.session_state.rag_pipeline.stream_chat_with_context(prompt, top_k=3)
                                    full_response = st.write_stream(response_stream)
                                else:
                                    # 没有检索到文档，使用普通对话
                                    response_stream = st.session_state.client.stream_chat(st.session_state.messages)
                                    full_response = st.write_stream(response_stream)
                            except Exception as e:
                                st.error(f"RAG 检索失败: {str(e)}，使用普通对话")
                                response_stream = st.session_state.client.stream_chat(st.session_state.messages)
                                full_response = st.write_stream(response_stream)
                        else:
                            # 未启用 RAG，使用普通对话
                            response_stream = st.session_state.client.stream_chat(st.session_state.messages)
                            full_response = st.write_stream(response_stream)
                except Exception as e:
                    st.error(f"生成回复失败: {str(e)}")
                    full_response = "抱歉，发生了错误，请稍后再试。"
                    st.markdown(full_response)
                
                elapsed_time = time.time() - start_time
                st.caption(f"响应时间: {elapsed_time:.2f} 秒")
            
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            save_history(st.session_state.messages, st.session_state.current_session)


def render_image_tab() -> None:
    """渲染图片标签页"""
    st.subheader("图片问答")
    
    # 图片上传
    uploaded_file = st.file_uploader("上传图片", type=["png", "jpg", "jpeg", "webp", "gif"])
    if uploaded_file:
        try:
            file_bytes = uploaded_file.read()
            image_base64 = f"data:image/{uploaded_file.type.split('/')[1]};base64,{base64.b64encode(file_bytes).decode()}"
            st.session_state.image_tab_image = image_base64
            st.image(uploaded_file, width=300)
        except Exception as e:
            st.error(f"图片处理失败: {str(e)}")
            st.session_state.image_tab_image = None
    
    # 清除图片
    if "image_tab_image" in st.session_state and st.session_state.image_tab_image:
        if st.button("清除图片"):
            st.session_state.image_tab_image = None
            st.session_state.needs_rerun = True
    
    # OCR 识别
    if "image_tab_image" in st.session_state and st.session_state.image_tab_image:
        if st.session_state.multimodal_client is None:
            st.error("多模态功能暂不可用，请检查配置")
        elif st.button("OCR 识别"):
            try:
                with st.spinner("正在识别..."):
                    ocr_result = st.session_state.multimodal_client.ocr_image(image_base64=st.session_state.image_tab_image)
                    st.text_area("OCR 结果", ocr_result, height=200)
            except Exception as e:
                st.error(f"OCR 识别失败: {str(e)}")
    
    # 图片问答输入
    image_prompt = st.text_input("输入关于图片的问题...")
    if image_prompt and "image_tab_image" in st.session_state and st.session_state.image_tab_image:
        if st.session_state.multimodal_client is None:
            st.error("多模态功能暂不可用，请检查配置")
        else:
            try:
                with st.spinner("正在分析图片..."):
                    response = st.session_state.multimodal_client.chat_with_image(
                        messages=[{"role": "user", "content": image_prompt}],
                        image_base64=st.session_state.image_tab_image
                    )
                    st.markdown(response)
            except Exception as e:
                st.error(f"图片问答失败: {str(e)}")


def render_rag_tab() -> None:
    """渲染 RAG 标签页"""
    st.subheader("文档问答")
    
    if not st.session_state.rag_pipeline:
        st.error("RAG 功能暂不可用，请检查配置")
    else:
        # 文档上传
        uploaded_docs = st.file_uploader(
            "上传文档",
            type=["txt", "pdf", "md", "doc", "docx", "html", "csv"],
            accept_multiple_files=True,
            help="支持 TXT、PDF、Markdown、Word、HTML、CSV 格式"
        )
        
        if uploaded_docs:
            for doc in uploaded_docs:
                try:
                    temp_dir = tempfile.mkdtemp()
                    temp_path = os.path.join(temp_dir, doc.name)
                    
                    with open(temp_path, "wb") as f:
                        f.write(doc.read())
                    
                    with st.spinner(f"正在处理 {doc.name}..."):
                        result = st.session_state.rag_pipeline.add_document(temp_path)
                        
                        if result["success"]:
                            st.success(f"{doc.name} - 添加成功，生成 {result['chunks_added']} 个片段")
                        else:
                            st.error(f"{doc.name} - {result['message']}")
                    
                    # 清理临时文件
                    os.remove(temp_path)
                except Exception as e:
                    st.error(f"处理文档 {doc.name} 失败: {str(e)}")
        
        # 向量库统计
        try:
            stats = st.session_state.rag_pipeline.get_stats()
            if stats.get("success"):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("总片段数", stats["total_chunks"])
                with col2:
                    st.metric("文档数", stats["total_documents"])
        except Exception as e:
            st.error(f"获取统计信息失败: {str(e)}")
        
        # RAG 问答
        st.divider()
        st.subheader("基于文档问答")
        
        rag_query = st.text_input("输入问题:", placeholder="例如：文档中关于XX的说明是什么？")
        
        if rag_query:
            try:
                with st.spinner("正在检索..."):
                    # 先检索相关文档
                    retrieved = st.session_state.rag_pipeline.retrieve(rag_query, top_k=5)
                    
                    if retrieved:
                        st.write("**参考文档:**")
                        for i, item in enumerate(retrieved):
                            metadata = item.get("metadata", {})
                            display_name = metadata.get("display_name", "未知文档")
                            with st.expander(f"文档 {i+1}: {display_name}"):
                                st.write(item["content"])
                    
                    # 生成回答
                    response = st.session_state.rag_pipeline.chat_with_context(rag_query, top_k=5)
                    st.write("**回答:**")
                    st.markdown(response)
            except Exception as e:
                st.error(f"问答失败: {str(e)}")


def main() -> None:
    """主函数"""
    # 页面配置
    st.set_page_config(
        page_title="AI 助手",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 初始化会话状态
    initialize_session_state()
    
    # 标题
    st.title("AI 助手")
    
    # 使用说明
    render_usage_expander()
    
    # 侧边栏
    render_sidebar()
    
    # 意图识别提示
    if st.session_state.show_ocr_reminder:
        st.info("检测到你需要 OCR 文字识别功能，请上传图片")
        st.session_state.show_ocr_reminder = False
    
    if st.session_state.show_image_reminder:
        st.info("检测到你需要图片分析功能，请上传图片")
        st.session_state.show_image_reminder = False
    
    # 三个标签页
    tab1, tab2, tab3 = st.tabs(["聊天", "图片", "RAG"])
    
    with tab1:
        render_chat_tab()
    
    with tab2:
        render_image_tab()
    
    with tab3:
        render_rag_tab()
    
    # 延迟 rerun：在所有组件渲染完成后统一执行
    # 避免 React 虚拟 DOM 和 Streamlit 的 removeChild 冲突
    if st.session_state.get("needs_rerun", False):
        st.session_state.needs_rerun = False
        st.rerun()


if __name__ == "__main__":
    main()
