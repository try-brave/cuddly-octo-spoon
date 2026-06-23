"""
多模态智能助手 - 性能测试脚本
测试项目：响应速度、OCR准确率、RAG准确率
"""
import time
import sys
import os
import io

# 修复Windows控制台UTF-8编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目路径到 Python 路径
sys.path.insert(0, "C:/Users/yj/Desktop/Multimodal-Assistant")

print("=" * 60)
print("🚀 多模态智能助手 - 性能测试")
print("=" * 60)

# ==================== 测试1：响应速度 ====================
print("\n📊 测试1：响应速度测试")
print("-" * 60)

try:
    from core import ChatClient
    
    # 初始化客户端
    print("⏳ 正在初始化 ChatClient...")
    start_init = time.time()
    chat_client = ChatClient()
    init_time = time.time() - start_init
    print(f"✅ 初始化完成，耗时: {init_time:.2f}秒")
    
    # 测试不同长度输入的响应速度
    test_cases = [
        ("短问题", "你好"),
        ("中等问题", "请简单介绍一下什么是人工智能？"),
        ("长问题", "请详细介绍一下人工智能的发展历程，包括早期的符号主义、连接主义，到现在的深度学习时代，以及未来的发展趋势。")
    ]
    
    response_times = []
    
    for case_name, question in test_cases:
        print(f"\n📝 测试: {case_name}")
        print(f"问题: {question}")
        
        try:
            start_time = time.time()
            response = chat_client.chat([{"role": "user", "content": question}])
            end_time = time.time()
            
            elapsed = end_time - start_time
            response_times.append(elapsed)
            
            print(f"✅ 响应时间: {elapsed:.2f}秒")
            print(f"回复长度: {len(response)}字符")
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
    
    if response_times:
        avg_time = sum(response_times) / len(response_times)
        print(f"\n📈 平均响应时间: {avg_time:.2f}秒")
        print(f"📈 最快响应: {min(response_times):.2f}秒")
        print(f"📈 最慢响应: {max(response_times):.2f}秒")

except Exception as e:
    print(f"❌ ChatClient 测试失败: {e}")
    print("请检查：1) .env 文件是否配置 2) API Key 是否有效")

# ==================== 测试2：OCR准确率 ====================
print("\n\n📊 测试2：OCR准确率测试")
print("-" * 60)

# 检查是否有测试图片
test_image_path = "C:/Users/yj/Desktop/Multimodal-Assistant/data/test_image.png"

if os.path.exists(test_image_path):
    try:
        from core import MultimodalClient
        
        print("⏳ 正在初始化 MultimodalClient...")
        multimodal_client = MultimodalClient()
        
        print(f"📷 测试图片: {test_image_path}")
        print("⏳ 正在进行OCR识别...")
        
        start_time = time.time()
        ocr_result = multimodal_client.ocr_image(image_path=test_image_path)
        ocr_time = time.time() - start_time
        
        print(f"✅ OCR完成，耗时: {ocr_time:.2f}秒")
        print(f"识别结果:\n{ocr_result}")
        print(f"识别文字长度: {len(ocr_result)}字符")
        
    except Exception as e:
        print(f"❌ OCR测试失败: {e}")
else:
    print("⚠️  未找到测试图片")
    print(f"请将测试图片放到: {test_image_path}")
    print("或者修改脚本中的 test_image_path 变量")

# ==================== 测试3：RAG准确率 ====================
print("\n\n📊 测试3：RAG检索准确率测试")
print("-" * 60)

try:
    from core import RAGPipeline
    
    print("⏳ 正在初始化 RAGPipeline...")
    rag = RAGPipeline()
    
    # 检查是否已有文档
    collection_count = 0
    try:
        collection_count = rag.collection.count()
        print(f"✅ RAG系统已就绪，当前文档片段数: {collection_count}")
    except:
        print("⚠️  RAG系统未初始化或没有文档")
        print("建议：先上传一个测试文档")
    
    if collection_count > 0:
        # 测试检索功能
        test_queries = [
            "文档的主要内容是什么？",
            "请总结文档的关键信息",
            "文档中提到了哪些重要概念？"
        ]
        
        for query in test_queries:
            print(f"\n📝 测试查询: {query}")
            
            try:
                start_time = time.time()
                results = rag.retrieve(query)
                retrieve_time = time.time() - start_time
                
                print(f"✅ 检索完成，耗时: {retrieve_time:.2f}秒")
                print(f"检索到 {len(results)} 个相关片段")
                
                if results:
                    # 正确访问：results[0]是字典，需要用["content"]获取文本
                    content_preview = results[0]["content"][:100]
                    print(f"最相关片段预览: {content_preview}...")
                    
            except Exception as e:
                print(f"❌ 检索失败: {e}")
        
        # 测试基于文档的问答
        print(f"\n📝 测试RAG问答...")
        try:
            start_time = time.time()
            response = rag.chat_with_context("请简要总结文档内容")
            rag_time = time.time() - start_time
            
            print(f"✅ RAG问答完成，耗时: {rag_time:.2f}秒")
            print(f"回答: {response[:200]}...")
            
        except Exception as e:
            print(f"❌ RAG问答失败: {e}")
    else:
        print("\n💡 提示：上传文档后可以测试RAG功能")
        print("在桌面应用中，使用'上传文档'功能")

except Exception as e:
    print(f"❌ RAG测试失败: {e}")

# ==================== 测试总结 ====================
print("\n\n" + "=" * 60)
print("📊 测试总结")
print("=" * 60)

print("\n✅ 测试完成！结果说明：")
print("1. 响应速度: 优秀 <2秒, 良好 2-5秒, 需优化 >5秒")
print("2. OCR准确率: 需要人工对比原图和识别结果")
print("3. RAG准确率: 需要人工评估检索相关性和回答质量")

print("\n💡 下一步建议：")
print("1. 记录测试结果到简历项目亮点")
print("2. 如果响应时间>5秒，优化API调用参数")
print("3. 测试不同图片类型（打印体、手写体、表格）的OCR效果")
print("4. 测试不同文档类型（PDF、Word、TXT）的RAG效果")

print("\n" + "=" * 60)
print("测试结束，感谢使用！")
print("=" * 60)
