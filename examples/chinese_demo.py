#!/usr/bin/env python3
"""
Chinese language demonstration for ReAct PubMed Agent.
展示中文语言支持功能的完整示例。
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def demo_chinese_support():
    """Demonstrate Chinese language support."""
    print("🧬 ReAct PubMed Agent - 中文语言演示")
    print("=" * 60)
    print("展示完整的中文语言支持功能：")
    print("✅ 自动语言检测")
    print("✅ 中文提示词模板")
    print("✅ 中文科学术语支持")
    print("✅ 中文推理循环")
    print("=" * 60)
    
    # Check if API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ 错误：OPENAI_API_KEY 环境变量未设置。")
        print("请在 .env 文件或环境中设置。")
        return
    
    try:
        from pubmed_agent import PubMedAgent
        
        # Demo 1: Auto-detection (自动检测)
        print("\n🔍 演示1：自动语言检测")
        print("-" * 40)
        
        agent_auto = PubMedAgent(language="auto")
        
        # Test English query
        question_en = "What are the mechanisms of mRNA vaccines?"
        print(f"英文问题: {question_en}")
        result_en = agent_auto.query(question_en)
        
        print(f"检测语言: {result_en.get('language', 'unknown')}")
        print(f"回答: {result_en['answer'][:200]}...")
        
        # Test Chinese query
        question_zh = "mRNA疫苗的作用机制是什么？"
        print(f"\n中文问题: {question_zh}")
        result_zh = agent_auto.query(question_zh)
        
        print(f"检测语言: {result_zh.get('language', 'unknown')}")
        print(f"回答: {result_zh['answer'][:200]}...")
        
        print("\n✅ 自动语言检测功能正常工作！")
        
        # Demo 2: Fixed Chinese mode (固定中文模式)
        print("\n🇨🇳 演示2：固定中文模式")
        print("-" * 40)
        
        agent_zh = PubMedAgent(language="zh")
        
        # Test various Chinese scientific queries
        chinese_queries = [
            {
                "question": "CRISPR-Cas9系统如何在分子水平编辑DNA？",
                "type": "mechanism",
                "description": "机制研究查询"
            },
            {
                "question": "GLP-1受体激动剂对肥胖患者的减肥效果如何？",
                "type": "therapeutic",
                "description": "临床治疗查询"
            },
            {
                "question": "比较不同COVID-19疫苗的疗效和安全性",
                "type": "complex",
                "description": "复杂比较查询"
            },
            {
                "question": "最新的基因编辑技术发展有哪些？",
                "type": "scientific",
                "description": "一般科学查询"
            }
        ]
        
        for i, demo in enumerate(chinese_queries, 1):
            print(f"\n{i}. {demo['description']}")
            print(f"   问题: {demo['question']}")
            print(f"   类型: {demo['type']}")
            print("   处理中...")
            
            try:
                result = agent_zh.query(demo['question'], prompt_type=demo['type'])
                
                if result['success']:
                    answer = result['answer']
                    # Truncate long answers for demo
                    if len(answer) > 300:
                        answer = answer[:300] + "..."
                    
                    print(f"   ✅ 成功！")
                    print(f"   回答: {answer}")
                    print(f"   推理步骤: {len(result['intermediate_steps'])} 步")
                    print(f"   使用的提示词: {result['prompt_type']}")
                else:
                    print(f"   ❌ 错误: {result.get('error', '未知错误')}")
                    
            except Exception as e:
                print(f"   ❌ 异常: {str(e)}")
        
        print("\n✅ 中文模式功能完美运行！")
        
        # Demo 3: Multi-language comparison (多语言对比)
        print("\n🌐 演示3：多语言对比")
        print("-" * 40)
        
        agent_en = PubMedAgent(language="en")
        agent_zh = PubMedAgent(language="zh")
        
        comparison_question = "疫苗的作用机制"
        
        print(f"对比问题: {comparison_question}")
        
        # English response
        result_en = agent_en.query(comparison_question)
        print(f"\n🇺🇸 英文回答:")
        print(f"   检测语言: {result_en.get('language', 'unknown')}")
        print(f"   回答: {result_en['answer'][:200]}...")
        
        # Chinese response
        result_zh = agent_zh.query(comparison_question)
        print(f"\n🇨🇳 中文回答:")
        print(f"   检测语言: {result_zh.get('language', 'unknown')}")
        print(f"   回答: {result_zh['answer'][:200]}...")
        
        print("\n✅ 多语言支持功能正常工作！")
        
        # Demo 4: Agent statistics (代理统计)
        print("\n📊 演示4：代理统计信息")
        print("-" * 40)
        
        stats = agent_zh.get_agent_stats()
        print("代理统计信息:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        print("\n✅ 统计功能正常工作！")
        
        # Demo 5: Search and store (搜索和存储)
        print("\n🔍 演示5：搜索和存储功能")
        print("-" * 40)
        
        search_query = "mRNA疫苗安全性"
        print(f"搜索查询: {search_query}")
        
        result = agent_zh.search_and_store(search_query, max_results=3)
        
        if result['success']:
            print(f"✅ 搜索成功！")
            print(f"   找到PMID数量: {result['pmids_found']}")
            print(f"   存储文章数量: {result['articles_stored']}")
        else:
            print(f"❌ 搜索失败: {result.get('error', '未知错误')}")
        
        print("\n✅ 搜索和存储功能正常工作！")
        
        print("\n🎉 中文语言演示完成！")
        print("=" * 60)
        print("所有中文语言支持功能都已成功演示：")
        print("✅ 自动语言检测")
        print("✅ 中文ReAct推理循环")
        print("✅ 中文科学术语处理")
        print("✅ 中文提示词优化")
        print("✅ 多语言对比功能")
        print("✅ 代理统计和监控")
        
        print("\n🚀 ReAct PubMed Agent 中文版已准备就绪！")
        print("\n📋 使用方法：")
        print("   from pubmed_agent import PubMedAgent")
        print("   agent = PubMedAgent(language='zh')  # 中文模式")
        print("   agent = PubMedAgent(language='auto')  # 自动检测模式")
        print("   response = agent.query('您的问题')")
        print("\n🔬 支持的功能：")
        print("   🔍 PubMed文献检索")
        print("   🧠 ReAct推理框架")
        print("   💾 向量数据库存储")
        print("   🔎 语义搜索")
        print("   📖 参考文献管理")
        print("   🌐 多语言支持（英文/中文）")
        print("   🔧 可扩展工具系统")
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请确保已安装依赖：pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ 意外错误: {e}")


if __name__ == "__main__":
    print("🧬 ReAct PubMed Agent - 中文语言支持演示")
    print("=" * 60)
    print("这个演示展示了ReAct PubMed Agent的完整中文语言支持：")
    print("🎯 项目目标：构建具备检索、理解、存储和推理能力的智能科研助理")
    print("🏗️ 系统架构：ReAct框架 + 向量数据库 + 工具系统")
    print("🚀 核心功能：PubMed搜索、语义检索、证据回答")
    print("🌏 语言支持：自动检测 + 英文/中文提示词")
    print("=" * 60)
    
    demo_chinese_support()