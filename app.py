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
from typing import Dict, List, Optional

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
    """初始化 Streamlit 会话状态（只操作 session_state，不调用任何 st.* 显示函数）"""
    # 意图路由器
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

    # 聊天客户端（失败时记录错误，不调用 st.error）
    if "client" not in st.session_state:
        try:
            st.session_state.client = ChatClient("moonshot")
            st.session_state._init_error_client = ""
        except Exception as e:
            st.session_state.client = None
            st.session_state._init_error_client = str(e)

    # 多模态客户端
    if "multimodal_client" not in st.session_state:
        try:
            st.session_state.multimodal_client = MultimodalClient("moonshot")
            st.session_state._init_error_multimodal = ""
        except Exception as e:
            st.session_state.multimodal_client = None
            st.session_state._init_error_multimodal = str(e)

    # RAG 管道
    if "rag_pipeline" not in st.session_state:
        try:
            st.session_state.rag_pipeline = RAGPipeline()
            st.session_state._init_error_rag = ""
        except Exception as e:
            st.session_state.rag_pipeline = None
            st.session_state._init_error_rag = str(e)

    # 当前会话
    if "current_session" not in st.session_state:
        try:
            sessions = get_all_sessions()
            st.session_state.current_session = sessions[0]["filepath"] if sessions else create_new_session()
        except Exception as e:
            st.session_state.current_session = None
            st.session_state._init_error_session = str(e)

    # 消息历史
    if "messages" not in st.session_state:
        try:
            loaded = load_history(st.session_state.current_session) if st.session_state.current_session else None
            st.session_state.messages = loaded if loaded else [{"role": "system", "content": "你是一个友好的中文助手"}]
        except Exception:
            st.session_state.messages = [{"role": "system", "content": "你是一个友好的中文助手"}]

    # 图片状态
    if "uploaded_image" not in st.session_state:
        st.session_state.uploaded_image = None
    if "image_tab_image" not in st.session_state:
        st.session_state.image_tab_image = None

    # 意图提醒
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

    # 当前页面（用 selectbox 替代 tabs）
    if "current_page" not in st.session_state:
        st.session_state.current_page = "聊天"


def render_sidebar() -> None:
    """渲染侧边栏（不含任何导致 DOM 冲突的组件）"""
    with st.sidebar:
        st.subheader("会话管理")

        try:
            if st.button("新建对话"):
                save_history(st.session_state.messages, st.session_state.current_session)
                st.session_state.current_session = create_new_session()
                st.session_state.messages = [{"role": "system", "content": "你是一个友好的中文助手"}]
                st.session_state.uploaded_image = None
                if st.session_state.multimodal_client:
                    st.session_state.multimodal_client.clear_image_context()

            st.divider()

            sessions = get_all_sessions()
            if sessions:
                selected = st.selectbox(
                    "选择对话",
                    sessions,
                    format_func=lambda x: x["title"],
                    index=0,
                    key="session_selector"
                )
                if selected and selected.get("filepath") != st.session_state.current_session:
                    save_history(st.session_state.messages, st.session_state.current_session)
                    st.session_state.current_session = selected["filepath"]
                    loaded = load_history(selected["filepath"])
                    st.session_state.messages = loaded if loaded else [{"role": "system", "content": "你是一个友好的中文助手"}]
                    st.session_state.uploaded_image = None
                    if st.session_state.multimodal_client:
                        st.session_state.multimodal_client.clear_image_context()

                delete_options = [s for s in sessions if s.get("filepath") != st.session_state.current_session]
                if delete_options:
                    to_delete = st.selectbox("删除对话", [""] + delete_options, format_func=lambda x: x["title"] if isinstance(x, dict) else "")
                    if isinstance(to_delete, dict) and st.button("确认删除"):
                        delete_history_file(to_delete["filepath"])
                        st.info(f"已删除: {to_delete['title']}")

        except Exception as e:
            st.error(f"会话管理错误: {str(e)}")

        st.divider()
        st.subheader("文档管理")

        st.session_state.rag_enabled = st.checkbox("启用文档检索", value=st.session_state.rag_enabled)

        if st.session_state.rag_pipeline:
            try:
                docs = st.session_state.rag_pipeline.get_document_list()
                if docs:
                    st.write(f"**已上传文档 ({len(docs)} 个):**")
                    for doc in docs:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            ext = doc.get('extension', '')
                            icons = {'txt': '[T]', 'md': '[M]', 'pdf': '[P]', 'doc': '[D]', 'docx': '[D]', 'html': '[H]', 'htm': '[H]', 'csv': '[C]'}
                            st.text(f"{icons.get(ext, '[_]')} {doc.get('display_name', '')} ({doc.get('chunks', 0)} 片段)")
                        with col2:
                            if st.button("X", key=f"del_{doc.get('filename', '')}"):
                                result = st.session_state.rag_pipeline.delete_document(doc.get('filename', ''))
                                if result.get("success"):
                                    st.info(f"已删除: {doc.get('display_name', '')}")
                                else:
                                    st.error(result.get("message", "删除失败"))
                else:
                    st.info("暂无上传的文档")
            except Exception as e:
                st.error(f"加载文档列表失败: {str(e)}")

        if st.session_state.rag_pipeline:
            if st.button("清空所有文档"):
                try:
                    if st.session_state.rag_pipeline.clear_database():
                        st.info("所有文档已清空")
                except Exception as e:
                    st.error(f"清空文档失败: {str(e)}")

        st.divider()
        st.subheader("使用统计")
        if st.session_state.client and hasattr(st.session_state.client, 'last_usage') and st.session_state.client.last_usage:
            usage = st.session_state.client.last_usage
            col1, col2 = st.columns(2)
            with col1:
                st.metric("总Token", usage.get('total_tokens', 0))
            with col2:
                st.metric("生成Token", usage.get('completion_tokens', 0))


def render_chat_page() -> None:
    """渲染聊天页面"""
    st.subheader("对话")

    # RAG 状态
    if st.session_state.rag_enabled and st.session_state.rag_pipeline:
        try:
            stats = st.session_state.rag_pipeline.get_stats()
            if stats.get("success") and stats.get("total_documents", 0) > 0:
                st.info(f"RAG 已启用，共 {stats['total_documents']} 个文档，{stats['total_chunks']} 个片段")
        except Exception:
            pass

    # 显示历史消息
    for i, msg in enumerate(st.session_state.messages):
        if msg["role"] in ["user", "assistant"]:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    # 意图提醒
    if st.session_state.show_ocr_reminder:
        st.info("检测到你需要 OCR 文字识别功能，请上传图片")
        st.session_state.show_ocr_reminder = False
    if st.session_state.show_image_reminder:
        st.info("检测到你需要图片分析功能，请上传图片")
        st.session_state.show_image_reminder = False


def render_image_page() -> None:
    """渲染图片页面"""
    st.subheader("图片问答")

    uploaded_file = st.file_uploader("上传图片", type=["png", "jpg", "jpeg", "webp", "gif"])
    if uploaded_file:
        try:
            file_bytes = uploaded_file.read()
            image_b64 = f"data:image/{uploaded_file.type.split('/')[1]};base64,{base64.b64encode(file_bytes).decode()}"
            st.session_state.image_tab_image = image_b64
            st.image(uploaded_file, width=300)
        except Exception as e:
            st.error(f"图片处理失败: {str(e)}")
            st.session_state.image_tab_image = None

    if st.session_state.get("image_tab_image"):
        if st.button("清除图片"):
            st.session_state.image_tab_image = None
            st.rerun()

    if st.session_state.get("image_tab_image"):
        if st.session_state.multimodal_client is None:
            st.error("多模态功能暂不可用，请检查配置")
        elif st.button("OCR 识别"):
            try:
                with st.spinner("正在识别..."):
                    ocr_result = st.session_state.multimodal_client.ocr_image(image_base64=st.session_state.image_tab_image)
                    st.text_area("OCR 结果", ocr_result, height=200)
            except Exception as e:
                st.error(f"OCR 识别失败: {str(e)}")

        image_prompt = st.text_input("输入关于图片的问题...")
        if image_prompt:
            if st.session_state.multimodal_client is None:
                st.error("多模态功能暂不可用，请检查配置")
            else:
                try:
                    with st.spinner("正在分析图片..."):
                        response = st.session_state.multimodal_client.chat_with_image(
                            messages=[{"role": "user", "content": image_prompt}],
                            image_base64=st.session_state.image_tab_image
                        )
                        st.write(response)
                except Exception as e:
                    st.error(f"图片问答失败: {str(e)}")


def render_rag_page() -> None:
    """渲染 RAG 页面"""
    st.subheader("文档问答")

    if not st.session_state.rag_pipeline:
        st.error("RAG 功能暂不可用，请检查配置")
        return

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
                os.remove(temp_path)
            except Exception as e:
                st.error(f"处理文档 {doc.name} 失败: {str(e)}")

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

    st.divider()
    st.subheader("基于文档问答")

    rag_query = st.text_input("输入问题:", placeholder="例如：文档中关于XX的说明是什么？")
    if rag_query:
        try:
            with st.spinner("正在检索..."):
                retrieved = st.session_state.rag_pipeline.retrieve(rag_query, top_k=5)
                if retrieved:
                    st.write("**参考文档:**")
                    for i, item in enumerate(retrieved):
                        metadata = item.get("metadata", {})
                        display_name = metadata.get("display_name", "未知文档")
                        with st.expander(f"文档 {i+1}: {display_name}"):
                            st.write(item["content"])
                response = st.session_state.rag_pipeline.chat_with_context(rag_query, top_k=5)
                st.write("**回答:**")
                st.write(response)
        except Exception as e:
            st.error(f"问答失败: {str(e)}")


def handle_user_input(prompt: str) -> None:
    """处理用户输入（在 main 中调用，确保 chat_input 在顶层）"""
    if st.session_state.client is None:
        st.error("聊天功能暂不可用，请检查配置")
        return

    with st.chat_message("user"):
        st.write(prompt)

    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        start_time = time.time()
        try:
            intent_result = st.session_state.intent_router.route(prompt)

            if intent_result["is_default"] == False and intent_result["score"] >= 0.7 and not st.session_state.uploaded_image:
                full_response = intent_result["result"]
                st.write(full_response)
            else:
                if st.session_state.rag_enabled and st.session_state.rag_pipeline:
                    try:
                        retrieved = st.session_state.rag_pipeline.retrieve(prompt, top_k=3)
                        if retrieved:
                            st.write("**参考文档:**")
                            for i, item in enumerate(retrieved):
                                metadata = item.get("metadata", {})
                                display_name = metadata.get("display_name", "未知文档")
                                with st.expander(f"文档 {i+1}: {display_name}"):
                                    st.write(item["content"])
                        response_stream = st.session_state.rag_pipeline.stream_chat_with_context(prompt, top_k=3)
                        full_response = st.write_stream(response_stream)
                    except Exception as e:
                        st.error(f"RAG 检索失败: {str(e)}，使用普通对话")
                        response_stream = st.session_state.client.stream_chat(st.session_state.messages)
                        full_response = st.write_stream(response_stream)
                else:
                    response_stream = st.session_state.client.stream_chat(st.session_state.messages)
                    full_response = st.write_stream(response_stream)
        except Exception as e:
            st.error(f"生成回复失败: {str(e)}")
            full_response = "抱歉，发生了错误，请稍后再试。"

        elapsed_time = time.time() - start_time
        st.caption(f"响应时间: {elapsed_time:.2f} 秒")

    st.session_state.messages.append({"role": "assistant", "content": full_response})
    save_history(st.session_state.messages, st.session_state.current_session)


def main() -> None:
    """主函数"""
    # 页面配置（必须是第一个 Streamlit 命令）
    st.set_page_config(
        page_title="AI 助手",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 初始化
    initialize_session_state()

    # 显示初始化错误（在页面配置之后，用 st.error 安全显示）
    if hasattr(st.session_state, '_init_error_client') and st.session_state._init_error_client:
        st.error(f"初始化聊天客户端失败: {st.session_state._init_error_client}")
    if hasattr(st.session_state, '_init_error_multimodal') and st.session_state._init_error_multimodal:
        st.error(f"初始化多模态客户端失败: {st.session_state._init_error_multimodal}")
    if hasattr(st.session_state, '_init_error_rag') and st.session_state._init_error_rag:
        st.error(f"RAG 初始化失败: {st.session_state._init_error_rag}")

    # 标题
    st.title("AI 助手")

    # 使用说明
    with st.expander("使用说明"):
        st.write("""
        **聊天功能:** 在底部输入框输入问题，按回车发送。
        **图片功能:** 切换到"图片"页面上传图片。
        **文档功能:** 切换到"文档"页面上传文档进行问答。
        """)

    # 侧边栏
    render_sidebar()

    # 页面导航（用 selectbox 替代 tabs，彻底避免 React DOM 冲突）
    page = st.selectbox(
        "选择功能页面",
        ["聊天", "图片", "RAG"],
        index=["聊天", "图片", "RAG"].index(st.session_state.current_page),
        key="main_nav"
    )
    st.session_state.current_page = page

    st.divider()

    # 根据选择渲染页面
    if page == "聊天":
        render_chat_page()
    elif page == "图片":
        render_image_page()
    elif page == "RAG":
        render_rag_page()

    # st.chat_input 必须在 main() 底部、所有 st.* 之后调用
    # 这样它始终在 DOM 的固定位置，不会随 tabs 切换而挂载/卸载
    prompt = st.chat_input("说点什么...")
    if prompt:
        handle_user_input(prompt)


if __name__ == "__main__":
    main()
