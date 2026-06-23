"""
测试流式输出功能（无emoji版本）
"""
import sys
import os

# 修复Windows控制台UTF-8编码问题
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目路径
sys.path.insert(0, "C:/Users/yj/Desktop/Multimodal-Assistant")

print("=" * 60)
print("测试流式输出功能")
print("=" * 60)

# 测试1：ChatClient流式输出
print("\n测试1：ChatClient流式输出")
try:
    from core import ChatClient
    
    chat_client = ChatClient()
    print("ChatClient初始化成功")
    
    messages = [{"role": "user", "content": "你好，请简短回复"}]
    
    print("开始流式输出...")
    full_response = ""
    chunk_count = 0
    
    for chunk in chat_client.stream_chat(messages):
        full_response += chunk
        chunk_count += 1
        if chunk_count <= 5:  # 只显示前5个chunk
            print(f"接收chunk {chunk_count}: {chunk}")
    
    print(f"\n流式输出完成，总长度: {len(full_response)}字符")
    print(f"总共接收 {chunk_count} 个chunks")
    
except Exception as e:
    print(f"测试失败: {e}")

# 测试2：RAGPipeline流式输出
print("\n测试2：RAGPipeline流式输出")
try:
    from core import RAGPipeline
    
    rag = RAGPipeline()
    print("RAGPipeline初始化成功")
    print(f"当前文档片段数: {rag.collection.count()}")
    
    if rag.collection.count() > 0:
        print("开始RAG流式输出...")
        
        full_response = ""
        chunk_count = 0
        
        for chunk in rag.stream_chat_with_context("文档的主要内容是什么？", top_k=3):
            full_response += chunk
            chunk_count += 1
            if chunk_count <= 5:  # 只显示前5个chunk
                print(f"接收chunk {chunk_count}: {chunk}")
        
        print(f"\nRAG流式输出完成，总长度: {len(full_response)}字符")
        print(f"总共接收 {chunk_count} 个chunks")
    else:
        print("没有文档，跳过RAG流式测试")
    
except Exception as e:
    print(f"测试失败: {e}")

print("\n" + "=" * 60)
print("测试完成！")
print("如果看到'流式输出完成'，说明功能正常")
print("=" * 60)
