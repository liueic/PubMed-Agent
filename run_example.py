#!/usr/bin/env python3
"""
简单运行示例 - Simple Run Example
演示如何快速运行 PubMed Agent
Demonstrates how to quickly run the PubMed Agent
"""

import os
from dotenv import load_dotenv

# 加载环境变量
# Load environment variables
load_dotenv()

def main():
    """主函数 - Main function"""
    print("🧬 ReAct PubMed Agent - 简单运行示例")
    print("=" * 60)
    
    # 检查环境变量
    # Check environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ 错误: 未找到 OPENAI_API_KEY 环境变量")
        print("请确保已创建 .env 文件并配置 OPENAI_API_KEY")
        print("\n📝 配置步骤:")
        print("1. 复制 .env.example 为 .env: cp .env.example .env")
        print("2. 编辑 .env 文件，填入你的 OPENAI_API_KEY")
        return
    
    print("✅ 环境变量配置正确")
    print("\n正在初始化 PubMed Agent...")
    
    try:
        from pubmed_agent import PubMedAgent
        
        # 创建代理（自动检测语言）
        # Create agent (auto-detect language)
        agent = PubMedAgent(language="auto")
        
        print("✅ Agent 初始化成功！")
        print("\n" + "=" * 60)
        print("📋 示例查询:")
        print("=" * 60)
        
        # 示例1: 中文查询
        print("\n🇨🇳 示例1: 中文查询")
        print("-" * 40)
        question_zh = "mRNA疫苗的作用机制是什么？"
        print(f"问题: {question_zh}")
        print("处理中...")
        
        try:
            response = agent.query(question_zh)
            if response['success']:
                print(f"\n✅ 回答: {response['answer'][:200]}...")
                print(f"语言: {response.get('language', 'unknown')}")
            else:
                print(f"\n❌ 错误: {response.get('error', '未知错误')}")
        except Exception as e:
            print(f"\n❌ 异常: {str(e)}")
        
        # 示例2: 英文查询
        print("\n🇺🇸 示例2: English Query")
        print("-" * 40)
        question_en = "What are the mechanisms of mRNA vaccines?"
        print(f"Question: {question_en}")
        print("Processing...")
        
        try:
            response = agent.query(question_en)
            if response['success']:
                print(f"\n✅ Answer: {response['answer'][:200]}...")
                print(f"Language: {response.get('language', 'unknown')}")
            else:
                print(f"\n❌ Error: {response.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"\n❌ Exception: {str(e)}")
        
        print("\n" + "=" * 60)
        print("🎉 示例运行完成！")
        print("\n💡 提示: 查看 examples/chinese_demo.py 了解更多示例")
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请确保已安装所有依赖:")
        print("  uv pip install -r requirements.txt")
        print("  或")
        print("  pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

