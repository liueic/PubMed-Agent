#!/usr/bin/env python3
"""
Command-line interface for ReAct PubMed Agent.
支持命令行使用方式的接口
"""

import argparse
import sys
import os
from typing import Optional

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from .agent import PubMedAgent
from .config import AgentConfig


def print_response(response: dict, verbose: bool = False):
    """格式化打印响应"""
    if not response.get('success', False):
        print(f"❌ 错误 / Error: {response.get('error', 'Unknown error')}")
        return
    
    print("\n" + "=" * 80)
    print("📋 回答 / Answer:")
    print("=" * 80)
    print(response.get('answer', ''))
    print("=" * 80)
    
    if verbose:
        print(f"\n语言 / Language: {response.get('language', 'unknown')}")
        print(f"提示词类型 / Prompt Type: {response.get('prompt_type', 'unknown')}")
        print(f"推理步骤数 / Reasoning Steps: {len(response.get('intermediate_steps', []))}")


def query_command(args):
    """处理查询命令"""
    try:
        # 创建配置
        config = None
        if args.api_base:
            config = AgentConfig(
                openai_api_key=os.getenv("OPENAI_API_KEY", args.api_key or ""),
                openai_api_base=args.api_base,
                openai_model=args.model or os.getenv("OPENAI_MODEL", "gpt-4o")
            )
        elif args.api_key:
            config = AgentConfig(
                openai_api_key=args.api_key,
                openai_model=args.model or os.getenv("OPENAI_MODEL", "gpt-4o")
            )
        
        # 创建agent
        agent = PubMedAgent(config=config, language=args.language)
        
        # 执行查询
        print(f"🔍 正在处理查询 / Processing query...")
        print(f"问题 / Question: {args.query}\n")
        
        response = agent.query(args.query, prompt_type=args.prompt_type)
        print_response(response, verbose=args.verbose)
        
    except Exception as e:
        print(f"❌ 错误 / Error: {str(e)}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def search_command(args):
    """处理搜索命令"""
    try:
        # 创建配置
        config = None
        if args.api_base:
            config = AgentConfig(
                openai_api_key=os.getenv("OPENAI_API_KEY", args.api_key or ""),
                openai_api_base=args.api_base,
                openai_model=args.model or os.getenv("OPENAI_MODEL", "gpt-4o")
            )
        elif args.api_key:
            config = AgentConfig(
                openai_api_key=args.api_key,
                openai_model=args.model or os.getenv("OPENAI_MODEL", "gpt-4o")
            )
        
        # 创建agent
        agent = PubMedAgent(config=config, language=args.language)
        
        # 执行搜索
        print(f"🔍 正在搜索PubMed...")
        print(f"查询 / Query: {args.query}\n")
        
        result = agent.search_and_store(args.query, max_results=args.max_results)
        
        if result.get('success'):
            print("✅ 搜索完成 / Search completed!")
            print(f"找到PMID数量 / PMIDs found: {result.get('pmids_found', 0)}")
            print(f"存储文章数量 / Articles stored: {result.get('articles_stored', 0)}")
            if args.verbose:
                print(f"\n搜索结果 / Search result:")
                print(result.get('search_result', '')[:500] + "...")
        else:
            print(f"❌ 搜索失败 / Search failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
        
    except Exception as e:
        print(f"❌ 错误 / Error: {str(e)}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def interactive_command(args):
    """交互式模式"""
    try:
        # 创建配置
        config = None
        if args.api_base:
            config = AgentConfig(
                openai_api_key=os.getenv("OPENAI_API_KEY", args.api_key or ""),
                openai_api_base=args.api_base,
                openai_model=args.model or os.getenv("OPENAI_MODEL", "gpt-4o")
            )
        elif args.api_key:
            config = AgentConfig(
                openai_api_key=args.api_key,
                openai_model=args.model or os.getenv("OPENAI_MODEL", "gpt-4o")
            )
        
        # 创建agent
        agent = PubMedAgent(config=config, language=args.language)
        
        print("🧬 ReAct PubMed Agent - 交互式模式 / Interactive Mode")
        print("=" * 80)
        print("输入您的问题，输入 'quit' 或 'exit' 退出")
        print("Enter your question, type 'quit' or 'exit' to exit")
        print("=" * 80)
        print()
        
        while True:
            try:
                # 读取用户输入
                query = input("❓ 问题 / Question: ").strip()
                
                if not query:
                    continue
                
                if query.lower() in ['quit', 'exit', 'q', '退出']:
                    print("\n👋 再见 / Goodbye!")
                    break
                
                # 执行查询
                print("\n🔍 正在处理 / Processing...")
                response = agent.query(query)
                print_response(response, verbose=args.verbose)
                print()
                
            except KeyboardInterrupt:
                print("\n\n👋 再见 / Goodbye!")
                break
            except EOFError:
                print("\n\n👋 再见 / Goodbye!")
                break
        
    except Exception as e:
        print(f"❌ 错误 / Error: {str(e)}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def stats_command(args):
    """显示统计信息"""
    try:
        # 创建配置
        config = None
        if args.api_base:
            config = AgentConfig(
                openai_api_key=os.getenv("OPENAI_API_KEY", args.api_key or ""),
                openai_api_base=args.api_base,
                openai_model=args.model or os.getenv("OPENAI_MODEL", "gpt-4o")
            )
        elif args.api_key:
            config = AgentConfig(
                openai_api_key=args.api_key,
                openai_model=args.model or os.getenv("OPENAI_MODEL", "gpt-4o")
            )
        
        # 创建agent
        agent = PubMedAgent(config=config, language=args.language)
        
        # 获取统计信息
        stats = agent.get_agent_stats()
        
        print("📊 Agent 统计信息 / Agent Statistics:")
        print("=" * 80)
        for key, value in stats.items():
            print(f"  {key}: {value}")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ 错误 / Error: {str(e)}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def create_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="ReAct PubMed Agent - 科学文献智能助手 / Scientific Literature Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例 / Examples:
  # 基本查询 / Basic query
  pubmed-agent query "mRNA疫苗的作用机制是什么？"
  
  # 使用指定语言 / With specific language
  pubmed-agent query "What are the mechanisms of mRNA vaccines?" --language en
  
  # 交互式模式 / Interactive mode
  pubmed-agent interactive
  
  # 搜索并存储文献 / Search and store articles
  pubmed-agent search "COVID-19 vaccine" --max-results 5
  
  # 使用自定义API endpoint / With custom API endpoint
  pubmed-agent query "Hello" --api-base http://localhost:8000/v1
        """
    )
    
    # 全局参数
    parser.add_argument(
        '--language', '-l',
        choices=['en', 'zh', 'auto'],
        default='auto',
        help='语言设置 / Language setting (default: auto)'
    )
    parser.add_argument(
        '--api-key', '-k',
        help='API密钥 / API key (覆盖环境变量 / overrides environment variable)'
    )
    parser.add_argument(
        '--api-base', '-b',
        help='自定义API端点 / Custom API endpoint (例如 / e.g. http://localhost:8000/v1)'
    )
    parser.add_argument(
        '--model', '-m',
        help='模型名称 / Model name (覆盖环境变量 / overrides environment variable)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='显示详细信息 / Show verbose information'
    )
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='可用命令 / Available commands')
    
    # query 命令
    query_parser = subparsers.add_parser('query', help='查询科学问题 / Query scientific question')
    query_parser.add_argument('query', help='查询问题 / Query question')
    query_parser.add_argument(
        '--prompt-type',
        choices=['scientific', 'mechanism', 'therapeutic', 'complex'],
        help='提示词类型 / Prompt type'
    )
    query_parser.set_defaults(func=query_command)
    
    # search 命令
    search_parser = subparsers.add_parser('search', help='搜索并存储PubMed文献 / Search and store PubMed articles')
    search_parser.add_argument('query', help='搜索查询 / Search query')
    search_parser.add_argument(
        '--max-results', '-n',
        type=int,
        default=10,
        help='最大结果数 / Maximum results (default: 10)'
    )
    search_parser.set_defaults(func=search_command)
    
    # interactive 命令
    interactive_parser = subparsers.add_parser('interactive', aliases=['i'], 
                                               help='交互式模式 / Interactive mode')
    interactive_parser.set_defaults(func=interactive_command)
    
    # stats 命令
    stats_parser = subparsers.add_parser('stats', help='显示统计信息 / Show statistics')
    stats_parser.set_defaults(func=stats_command)
    
    return parser


def main():
    """主入口函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 检查API密钥
    if not args.api_key and not os.getenv("OPENAI_API_KEY"):
        print("❌ 错误 / Error: 未找到API密钥 / API key not found")
        print("请设置环境变量 OPENAI_API_KEY 或使用 --api-key 参数")
        print("Please set OPENAI_API_KEY environment variable or use --api-key argument")
        sys.exit(1)
    
    # 执行对应命令
    args.func(args)


if __name__ == "__main__":
    main()

