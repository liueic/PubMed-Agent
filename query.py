#!/usr/bin/env python3
"""
PubMed Agent 命令行查询工具
Command-line query tool for PubMed Agent

支持单次查询和多轮对话
Supports single query and multi-turn conversation

使用方法 (Usage):
    python query.py -question:"你的问题"
    python query.py -question:"What are the mechanisms of mRNA vaccines?"
    python query.py -question:"mRNA疫苗的作用机制是什么？"
    
多轮对话模式 (Multi-turn conversation mode):
    python query.py -question:"第一个问题" -conversation
    python query.py -conversation  # 进入交互式对话模式
"""

import os
import sys
import argparse
from typing import Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def print_banner():
    """打印欢迎横幅"""
    print("=" * 70)
    print("🧬 ReAct PubMed Agent - 命令行查询工具")
    print("   Command-line Query Tool for Scientific Literature")
    print("=" * 70)
    print()

def check_environment():
    """检查环境配置"""
    # 检查 LLM API Key（支持多种供应商）
    llm_api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not llm_api_key:
        print("❌ 错误: LLM_API_KEY 或 OPENAI_API_KEY 环境变量未设置")
        print("   Error: LLM_API_KEY or OPENAI_API_KEY environment variable not set")
        print()
        print("请执行以下步骤:")
        print("Please follow these steps:")
        print("1. 复制 .env.example 为 .env: copy .env.example .env (Windows) 或 cp .env.example .env (Linux/macOS)")
        print("   Copy .env.example to .env: copy .env.example .env (Windows) or cp .env.example .env (Linux/macOS)")
        print("2. 编辑 .env 文件，填入您的 LLM_API_KEY 或 OPENAI_API_KEY")
        print("   Edit .env file and fill in your LLM_API_KEY or OPENAI_API_KEY")
        print("3. 支持多种大模型供应商：OpenAI、Azure OpenAI、本地模型等")
        print("   Supports multiple providers: OpenAI, Azure OpenAI, local models, etc.")
        print("4. 重新运行此脚本")
        print("   Run this script again")
        return False
    return True

def format_response(response: dict, verbose: bool = False):
    """格式化并打印响应"""
    print("\n" + "=" * 70)
    print("📋 查询结果 / Query Results")
    print("=" * 70)
    
    if response.get('success'):
        print(f"\n✅ 状态: 成功 / Status: Success")
        print(f"🌐 语言: {response.get('language', 'unknown')} / Language: {response.get('language', 'unknown')}")
        print(f"📝 提示词类型: {response.get('prompt_type', 'unknown')} / Prompt Type: {response.get('prompt_type', 'unknown')}")
        
        if verbose:
            print(f"\n📊 推理步骤数: {len(response.get('intermediate_steps', []))} / Reasoning Steps: {len(response.get('intermediate_steps', []))}")
        
        print("\n" + "-" * 70)
        print("💬 回答 / Answer:")
        print("-" * 70)
        print(response.get('answer', 'No answer provided'))
        print()
        
        if verbose and response.get('intermediate_steps'):
            print("-" * 70)
            print("🔍 推理过程 / Reasoning Process (详细)")
            print("-" * 70)
            for i, step in enumerate(response.get('intermediate_steps', []), 1):
                print(f"\n步骤 {i} / Step {i}:")
                if isinstance(step, tuple) and len(step) >= 2:
                    action, observation = step[0], step[1]
                    if hasattr(action, 'tool'):
                        print(f"  工具 / Tool: {action.tool}")
                    if hasattr(action, 'tool_input'):
                        print(f"  输入 / Input: {action.tool_input}")
                    print(f"  观察 / Observation: {str(observation)[:200]}...")
    else:
        print(f"\n❌ 状态: 失败 / Status: Failed")
        print(f"错误信息 / Error: {response.get('error', 'Unknown error')}")
        print()
    
    print("=" * 70)
    print()

def single_query(question: str, language: str = "auto", verbose: bool = False):
    """执行单次查询"""
    try:
        from pubmed_agent import PubMedAgent
        
        print(f"🔍 正在处理查询... / Processing query...")
        print(f"问题 / Question: {question}")
        print()
        
        agent = PubMedAgent(language=language)
        response = agent.query(question)
        
        format_response(response, verbose)
        
        return response
        
    except ImportError as e:
        print(f"❌ 导入错误 / Import Error: {e}")
        print("请确保已安装依赖: pip install -r requirements.txt")
        print("Please make sure dependencies are installed: pip install -r requirements.txt")
        return None
    except Exception as e:
        print(f"❌ 错误 / Error: {e}")
        return None

def conversation_mode(language: str = "auto", verbose: bool = False):
    """多轮对话模式"""
    try:
        from pubmed_agent import PubMedAgent
        
        print("💬 进入多轮对话模式 / Entering multi-turn conversation mode")
        print("输入 'exit' 或 'quit' 退出 / Type 'exit' or 'quit' to exit")
        print("输入 'clear' 清除对话历史 / Type 'clear' to clear conversation history")
        print("输入 'stats' 查看代理统计 / Type 'stats' to view agent statistics")
        print("-" * 70)
        print()
        
        agent = PubMedAgent(language=language)
        conversation_count = 0
        
        while True:
            try:
                # 获取用户输入
                question = input(f"[{conversation_count + 1}] 您的问题 / Your question: ").strip()
                
                if not question:
                    continue
                
                # 处理特殊命令
                if question.lower() in ['exit', 'quit', '退出']:
                    print("\n👋 再见！/ Goodbye!")
                    break
                
                if question.lower() in ['clear', '清除']:
                    agent.clear_memory()
                    conversation_count = 0
                    print("✅ 对话历史已清除 / Conversation history cleared")
                    print()
                    continue
                
                if question.lower() in ['stats', '统计']:
                    stats = agent.get_agent_stats()
                    print("\n📊 代理统计信息 / Agent Statistics:")
                    print("-" * 70)
                    for key, value in stats.items():
                        print(f"  {key}: {value}")
                    print()
                    continue
                
                # 执行查询
                print(f"\n🔍 正在处理... / Processing...")
                response = agent.query(question)
                
                format_response(response, verbose)
                
                conversation_count += 1
                
            except KeyboardInterrupt:
                print("\n\n👋 再见！/ Goodbye!")
                break
            except EOFError:
                print("\n\n👋 再见！/ Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ 错误 / Error: {e}")
                print()
        
    except ImportError as e:
        print(f"❌ 导入错误 / Import Error: {e}")
        print("请确保已安装依赖: pip install -r requirements.txt")
        print("Please make sure dependencies are installed: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ 错误 / Error: {e}")

def parse_colon_args():
    """解析 -key:value 格式的参数"""
    # 预处理 sys.argv，将 -key:value 格式转换为 -key value 格式
    processed_args = []
    i = 0
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg.startswith('-') and ':' in arg and not arg.startswith('--'):
            # 处理 -key:value 格式
            key, value = arg.split(':', 1)
            processed_args.append(key)
            processed_args.append(value)
        else:
            processed_args.append(arg)
        i += 1
    return processed_args

def main():
    """主函数"""
    # 预处理参数，支持 -key:value 格式
    original_argv = sys.argv[:]
    try:
        sys.argv = parse_colon_args()
        
        parser = argparse.ArgumentParser(
            description='PubMed Agent 命令行查询工具 / Command-line Query Tool',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
使用示例 / Usage Examples:
  python query.py -question:"What are the mechanisms of mRNA vaccines?"
  python query.py -question:"mRNA疫苗的作用机制是什么？"
  python query.py -question:"疫苗机制" -language:zh
  python query.py -conversation
  python query.py -conversation -language:auto -verbose

参数说明 / Parameter Description:
  -question: 要查询的问题 / Question to query
  -language: 语言设置 (en/zh/auto) / Language setting (en/zh/auto)
  -conversation: 进入多轮对话模式 / Enter multi-turn conversation mode
  -verbose: 显示详细推理过程 / Show detailed reasoning process
            """
        )
        
        parser.add_argument(
            '-question',
            '--question',
            type=str,
            help='要查询的问题 / Question to query'
        )
        
        parser.add_argument(
            '-language',
            '--language',
            type=str,
            default='auto',
            choices=['en', 'zh', 'auto'],
            help='语言设置: en(英文), zh(中文), auto(自动检测) / Language: en(English), zh(Chinese), auto(Auto-detect)'
        )
        
        parser.add_argument(
            '-conversation',
            '--conversation',
            action='store_true',
            help='进入多轮对话模式 / Enter multi-turn conversation mode'
        )
        
        parser.add_argument(
            '-verbose',
            '--verbose',
            action='store_true',
            help='显示详细推理过程 / Show detailed reasoning process'
        )
        
        args = parser.parse_args()
    finally:
        # 恢复原始 sys.argv（虽然这里不需要，但保持代码整洁）
        pass
    
    # 打印横幅
    print_banner()
    
    # 检查环境
    if not check_environment():
        sys.exit(1)
    
    # 处理参数
    if args.conversation:
        # 多轮对话模式
        conversation_mode(language=args.language, verbose=args.verbose)
    elif args.question:
        # 单次查询模式
        single_query(args.question, language=args.language, verbose=args.verbose)
    else:
        # 没有提供问题，进入对话模式
        print("ℹ️  未提供问题参数，进入多轮对话模式")
        print("   No question provided, entering conversation mode")
        print("   提示: 使用 -question:\"你的问题\" 进行单次查询")
        print("   Tip: Use -question:\"your question\" for single query")
        print()
        conversation_mode(language=args.language, verbose=args.verbose)

if __name__ == "__main__":
    main()

