import os
import time
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.rag import RAGPipeline


class ChunkSizeExperiment:
    """
    Chunk Size 对比实验
    
    测试不同 chunk_size 设置对 RAG 检索效果的影响：
    - 检索相关性
    - 响应质量
    - 推理时间
    """
    
    def __init__(self):
        self.test_document = os.path.join(os.path.dirname(__file__), "test_document.txt")
        self.queries = [
            "什么是 RAG 技术？",
            "RAG 的主要组成部分有哪些？",
            "如何评估 RAG 的效果？",
            "RAG 与传统问答系统有什么区别？",
            "文本分割在 RAG 中起到什么作用？"
        ]
    
    def create_test_document(self):
        """创建测试文档"""
        content = """
# 检索增强生成 (RAG) 技术介绍

## 一、什么是 RAG

检索增强生成（Retrieval-Augmented Generation，简称 RAG）是一种将信息检索与生成式 AI 相结合的技术。
它通过在生成回答之前，先从外部知识库中检索相关信息，然后将这些信息作为上下文提供给语言模型，
从而生成更加准确、可靠和最新的回答。

## 二、RAG 的主要组成部分

RAG 系统通常包含以下几个核心组件：

### 1. 文档加载器
负责从各种数据源加载文档，支持多种格式如 PDF、TXT、Markdown 等。

### 2. 文本分割器
将长文档分割成适合模型处理的小块（chunks）。常用的分割策略包括：
- 基于字符数的分割
- 基于段落的分割
- 基于语义的分割

chunk_size 参数决定了每个文本块的大小，通常设置在 200-1000 字符之间。

### 3. 嵌入模型
将文本转换为向量表示，便于进行相似度计算。常用的嵌入模型包括：
- Sentence-BERT
- OpenAI Embeddings
- Cohere Embeddings

### 4. 向量数据库
存储和检索文本向量。常用的向量数据库包括：
- Chroma
- Pinecone
- Milvus

### 5. 语言模型
基于检索到的上下文生成回答。可以是闭源模型如 GPT-4，也可以是开源模型如 Llama、Qwen。

## 三、文本分割的重要性

文本分割是 RAG 流程中的关键步骤，直接影响检索效果和回答质量：

### 分割过细（小 chunk_size）
- 优点：检索精度高，噪音少
- 缺点：可能丢失上下文信息，导致回答不完整

### 分割过粗（大 chunk_size）
- 优点：保留完整上下文
- 缺点：可能引入无关信息，降低检索精度

### 最佳实践
- 根据文档类型调整：技术文档可能需要较小的 chunk_size，叙述性文档可以使用较大的 chunk_size
- 保留重叠部分：通过 chunk_overlap 参数设置相邻块的重叠，避免信息丢失

## 四、评估 RAG 效果的指标

### 1. 检索指标
- 召回率（Recall）：检索到相关文档的比例
- 精确率（Precision）：检索结果中相关文档的比例
- MRR（Mean Reciprocal Rank）：平均倒数排名

### 2. 生成指标
- ROUGE 分数：评估生成文本与参考文本的相似度
- BLEU 分数：评估机器翻译质量
- 人类评估：最直接但成本最高的评估方式

## 五、RAG 与传统问答系统的区别

### 传统问答系统
- 依赖预训练知识
- 无法处理最新信息
- 容易产生幻觉

### RAG 系统
- 可以利用外部知识库
- 支持动态更新知识
- 回答可追溯到来源文档
- 减少幻觉风险

## 六、实际应用场景

RAG 技术已广泛应用于多个领域：
- 智能客服：基于产品文档提供准确的技术支持
- 知识管理：帮助企业内部知识的检索和利用
- 教育领域：提供个性化的学习辅导
- 医疗领域：辅助医生获取最新医学知识

## 七、总结

RAG 是连接大语言模型与外部知识的桥梁，通过合理的文本分割和检索策略，可以显著提升 AI 系统的回答质量和可靠性。
选择合适的 chunk_size 是优化 RAG 性能的关键步骤，需要根据具体应用场景进行调整。
"""
        os.makedirs(os.path.dirname(self.test_document), exist_ok=True)
        with open(self.test_document, 'w', encoding='utf-8') as f:
            f.write(content)
        return self.test_document
    
    def run_experiment(self, chunk_sizes=[200, 300, 500, 700, 1000]):
        """运行 chunk_size 对比实验"""
        print("=" * 80)
        print("Chunk Size 对比实验")
        print("=" * 80)
        print(f"测试文档: {self.test_document}")
        print(f"测试查询数: {len(self.queries)}")
        print(f"测试 chunk_size: {chunk_sizes}")
        print("-" * 80)
        
        # 创建测试文档
        self.create_test_document()
        
        results = []
        
        for chunk_size in chunk_sizes:
            print(f"\n🔬 测试 chunk_size = {chunk_size}")
            print("-" * 60)
            
            # 创建 RAG 实例
            rag = RAGPipeline()
            rag.chunk_size = chunk_size
            # 重新创建文本分割器
            rag.text_splitter = self._create_text_splitter(chunk_size)
            
            # 清空向量库
            rag.clear_database()
            
            # 添加文档
            start_time = time.time()
            add_result = rag.add_document(self.test_document)
            add_time = time.time() - start_time
            
            print(f"文档添加完成，生成 {add_result['chunks_added']} 个 chunks")
            print(f"添加耗时: {add_time:.2f} 秒")
            
            # 测试查询
            query_results = []
            total_time = 0
            
            for i, query in enumerate(self.queries):
                start_time = time.time()
                response = rag.chat_with_context(query, top_k=3)
                elapsed = time.time() - start_time
                total_time += elapsed
                
                # 简单评估相关性（基于响应长度和关键词匹配）
                relevance_score = self._calculate_relevance(query, response)
                
                query_results.append({
                    "query": query,
                    "response_length": len(response),
                    "relevance_score": relevance_score,
                    "time": elapsed
                })
                
                print(f"查询 {i+1}: {query[:30]}...")
                print(f"  响应长度: {len(response)} 字符")
                print(f"  相关性评分: {relevance_score:.2f}")
                print(f"  耗时: {elapsed:.2f} 秒")
            
            # 计算平均值
            avg_response_length = sum(r["response_length"] for r in query_results) / len(query_results)
            avg_relevance = sum(r["relevance_score"] for r in query_results) / len(query_results)
            avg_time = total_time / len(query_results)
            
            results.append({
                "chunk_size": chunk_size,
                "chunks_created": add_result["chunks_added"],
                "avg_response_length": avg_response_length,
                "avg_relevance": avg_relevance,
                "avg_time": avg_time,
                "add_time": add_time
            })
            
            print("-" * 60)
            print(f"chunk_size={chunk_size} 总结:")
            print(f"  生成 chunks: {add_result['chunks_added']}")
            print(f"  平均响应长度: {avg_response_length:.0f}")
            print(f"  平均相关性: {avg_relevance:.2f}")
            print(f"  平均查询时间: {avg_time:.2f} 秒")
        
        # 输出汇总表格
        self._print_summary(results)
    
    def _create_text_splitter(self, chunk_size):
        """创建指定 chunk_size 的文本分割器"""
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=int(chunk_size * 0.1),
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?"]
        )
    
    def _calculate_relevance(self, query, response):
        """简单计算相关性分数"""
        query_keywords = [k for k in query.split() if len(k) > 1]
        
        if not query_keywords:
            return 0.5
        
        # 检查关键词是否在响应中出现
        matches = sum(1 for keyword in query_keywords if keyword in response)
        keyword_match_ratio = matches / len(query_keywords)
        
        # 响应长度评分（太短可能不完整，太长可能冗余）
        ideal_length = 300
        length_score = max(0.3, 1 - abs(len(response) - ideal_length) / ideal_length)
        
        # 综合评分
        return (keyword_match_ratio * 0.6 + length_score * 0.4)
    
    def _print_summary(self, results):
        """打印实验汇总表格"""
        print("\n" + "=" * 80)
        print("实验结果汇总")
        print("=" * 80)
        print(f"{'chunk_size':<12} {'chunks':<8} {'响应长度':<10} {'相关性':<10} {'查询时间':<10} {'添加时间':<10}")
        print("-" * 80)
        
        for result in results:
            print(f"{result['chunk_size']:<12} {result['chunks_created']:<8} {result['avg_response_length']:<10.0f} {result['avg_relevance']:<10.2f} {result['avg_time']:<10.2f} {result['add_time']:<10.2f}")
        
        print("\n[分析结论]")
        print("-" * 60)
        
        # 找出最佳表现
        best_relevance = max(results, key=lambda x: x["avg_relevance"])
        fastest = min(results, key=lambda x: x["avg_time"])
        
        print(f"• 最佳相关性: chunk_size={best_relevance['chunk_size']} (评分: {best_relevance['avg_relevance']:.2f})")
        print(f"• 最快响应: chunk_size={fastest['chunk_size']} (时间: {fastest['avg_time']:.2f}秒)")
        
        print("\n💡 建议:")
        print("-" * 60)
        print("• 小 chunk_size (200-300): 适合需要高精度检索的场景")
        print("• 中等 chunk_size (500-700): 平衡检索精度和上下文完整性")
        print("• 大 chunk_size (1000+): 适合需要完整上下文的场景")


if __name__ == "__main__":
    experiment = ChunkSizeExperiment()
    experiment.run_experiment(chunk_sizes=[200, 300, 500, 700, 1000])
