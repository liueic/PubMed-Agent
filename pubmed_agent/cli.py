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
from .utils import setup_logging
import logging

logger = logging.getLogger(__name__)


def print_response(response: dict, verbose: bool = False):
    """格式化打印响应，并自动保存为Markdown文档"""
    if not response.get('success', False):
        error_msg = response.get('error', 'Unknown error')
        error_details = response.get('error_details', {})
        
        print("\n" + "=" * 80)
        print("❌ 错误 / Error")
        print("=" * 80)
        
        # 显示错误消息（可能包含详细建议）
        answer = response.get('answer', error_msg)
        print(answer)
        
        # 在verbose模式下显示详细错误信息
        if verbose:
            print("\n" + "-" * 80)
            print("🔍 详细错误信息 / Detailed Error Information:")
            print("-" * 80)
            print(f"错误类型 / Error Type: {error_details.get('type', 'Unknown')}")
            print(f"错误消息 / Error Message: {error_msg}")
            
            if error_details.get('status_code'):
                print(f"HTTP状态码 / HTTP Status Code: {error_details['status_code']}")
            
            if error_details.get('request_url'):
                print(f"请求URL / Request URL: {error_details['request_url']}")
            
            if error_details.get('response_body'):
                print(f"响应内容 / Response Body: {error_details['response_body'][:500]}")
            
            if error_details.get('details'):
                print(f"\n详细建议 / Detailed Suggestions:")
                print(error_details['details'])
        
        print("=" * 80)
        
        # 保存错误响应为Markdown
        try:
            from .output_utils import save_response_to_markdown
            saved_path = save_response_to_markdown(response)
            print(f"💾 结果已保存到 / Result saved to: {saved_path}")
            print()
        except Exception as e:
            logger.warning(f"保存Markdown文档时出错 / Error saving Markdown: {e}")
        
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
    
    # 自动保存为Markdown文档
    try:
        from .output_utils import save_response_to_markdown
        saved_path = save_response_to_markdown(response)
        print(f"\n💾 结果已保存到 / Result saved to: {saved_path}")
        print()
    except Exception as e:
        logger.warning(f"保存Markdown文档时出错 / Error saving Markdown: {e}")


def query_command(args):
    """处理查询命令"""
    try:
        # 创建配置（优先使用环境变量，命令行参数会覆盖）
        config = None
        if args.api_base or args.api_key or args.model:
            # 如果提供了命令行参数，手动创建配置
            llm_api_key = args.api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
            config_kwargs = {}
            if llm_api_key:
                config_kwargs["llm_api_key"] = llm_api_key
            if args.api_base:
                config_kwargs["llm_base_url"] = args.api_base
            if args.model:
                config_kwargs["llm_model"] = args.model
            if config_kwargs:
                config = AgentConfig(**config_kwargs)
        
        # 创建agent（如果 config 为 None，AgentConfig 会自动从环境变量读取）
        agent = PubMedAgent(config=config, language=args.language)
        
        # 执行查询
        logger.info(f"正在处理查询 / Processing query: {args.query}")
        print(f"🔍 正在处理查询 / Processing query...")
        print(f"问题 / Question: {args.query}\n")
        
        response = agent.query(args.query, prompt_type=args.prompt_type)
        print_response(response, verbose=args.verbose)
        
    except Exception as e:
        logger.error(f"查询处理失败 / Query processing failed: {str(e)}", exc_info=True)
        print(f"❌ 错误 / Error: {str(e)}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def search_command(args):
    """处理搜索命令"""
    try:
        # 创建配置（优先使用环境变量，命令行参数会覆盖）
        config = None
        if args.api_base or args.api_key or args.model:
            # 如果提供了命令行参数，手动创建配置
            llm_api_key = args.api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
            config_kwargs = {}
            if llm_api_key:
                config_kwargs["llm_api_key"] = llm_api_key
            if args.api_base:
                config_kwargs["llm_base_url"] = args.api_base
            if args.model:
                config_kwargs["llm_model"] = args.model
            if config_kwargs:
                config = AgentConfig(**config_kwargs)
        
        # 创建agent（如果 config 为 None，AgentConfig 会自动从环境变量读取）
        agent = PubMedAgent(config=config, language=args.language)
        
        # 执行搜索
        logger.info(f"正在搜索PubMed / Searching PubMed: {args.query}")
        print(f"🔍 正在搜索PubMed...")
        print(f"查询 / Query: {args.query}\n")
        
        result = agent.search_and_store(args.query, max_results=args.max_results)
        
        if result.get('success'):
            logger.info(f"搜索完成 / Search completed: 找到 {result.get('pmids_found', 0)} 个PMID，存储 {result.get('articles_stored', 0)} 篇文章")
            print("✅ 搜索完成 / Search completed!")
            print(f"找到PMID数量 / PMIDs found: {result.get('pmids_found', 0)}")
            print(f"存储文章数量 / Articles stored: {result.get('articles_stored', 0)}")
            if args.verbose:
                logger.debug(f"搜索结果详情 / Search result details: {result.get('search_result', '')[:500]}")
                print(f"\n搜索结果 / Search result:")
                print(result.get('search_result', '')[:500] + "...")
        else:
            logger.error(f"搜索失败 / Search failed: {result.get('error', 'Unknown error')}")
            print(f"❌ 搜索失败 / Search failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"搜索命令执行失败 / Search command failed: {str(e)}", exc_info=True)
        print(f"❌ 错误 / Error: {str(e)}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def _change_log_level(new_level: str) -> bool:
    """
    动态更改日志级别
    
    Args:
        new_level: 新的日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        是否成功更改
    """
    try:
        numeric_level = getattr(logging, new_level.upper(), None)
        if numeric_level is None:
            return False
        
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        
        # 更新所有处理器的级别
        for handler in root_logger.handlers:
            handler.setLevel(numeric_level)
        
        return True
    except Exception:
        return False


def _get_current_log_level() -> str:
    """获取当前日志级别"""
    root_logger = logging.getLogger()
    level = root_logger.level
    level_name = logging.getLevelName(level)
    return level_name


def interactive_command(args):
    """交互式模式"""
    try:
        # 创建配置（优先使用环境变量，命令行参数会覆盖）
        config = None
        if args.api_base or args.api_key or args.model:
            # 如果提供了命令行参数，手动创建配置
            llm_api_key = args.api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
            config_kwargs = {}
            if llm_api_key:
                config_kwargs["llm_api_key"] = llm_api_key
            if args.api_base:
                config_kwargs["llm_base_url"] = args.api_base
            if args.model:
                config_kwargs["llm_model"] = args.model
            if config_kwargs:
                config = AgentConfig(**config_kwargs)
        
        # 创建agent（如果 config 为 None，AgentConfig 会自动从环境变量读取）
        agent = PubMedAgent(config=config, language=args.language)
        
        # 开始新的对话会话，保持多轮对话上下文
        session_id = agent.start_new_session()
        logger.info(f"交互式模式启动 / Interactive mode started, session ID: {session_id}")
        
        # 获取当前日志配置
        current_log_level = _get_current_log_level()
        log_file = getattr(args, 'log_file', None)
        
        print("🧬 ReAct PubMed Agent - 交互式模式 / Interactive Mode")
        print("=" * 80)
        print("输入您的问题，输入 'quit' 或 'exit' 退出")
        print("输入 'new' 或 '/new' 开始新会话")
        print("输入 '/log-level <级别>' 更改日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)")
        print("输入 '/log-status' 查看当前日志配置")
        print("输入 '/help' 查看帮助信息")
        print("Enter your question, type 'quit' or 'exit' to exit")
        print("Type 'new' or '/new' to start a new session")
        print("Type '/log-level <level>' to change log level (DEBUG/INFO/WARNING/ERROR/CRITICAL)")
        print("Type '/log-status' to view current log configuration")
        print("Type '/help' to view help")
        print("=" * 80)
        
        # 显示当前日志配置
        log_info = f"📋 当前日志配置 / Current Log Config: 级别={current_log_level}"
        if log_file:
            log_info += f", 文件={log_file}"
        else:
            log_info += ", 文件=控制台输出"
        print(log_info)
        
        if args.verbose:
            logger.debug(f"会话ID / Session ID: {session_id}")
            print(f"会话ID / Session ID: {session_id}")
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
                
                # 处理帮助命令
                if query.lower() in ['/help', 'help', '/h']:
                    print("\n📖 可用命令 / Available Commands:")
                    print("  /new 或 new          - 开始新会话 / Start new session")
                    print("  /log-level <级别>    - 更改日志级别 / Change log level")
                    print("                       (DEBUG/INFO/WARNING/ERROR/CRITICAL)")
                    print("  /log-status          - 查看日志配置 / View log configuration")
                    print("  /help 或 help        - 显示此帮助 / Show this help")
                    print("  quit 或 exit         - 退出程序 / Exit program")
                    print()
                    continue
                
                # 处理日志级别更改命令
                if query.lower().startswith('/log-level ') or query.lower().startswith('log-level '):
                    parts = query.split()
                    if len(parts) >= 2:
                        new_level = parts[1].upper()
                        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
                        if new_level in valid_levels:
                            if _change_log_level(new_level):
                                logger.info(f"日志级别已更改 / Log level changed to: {new_level}")
                                print(f"\n✅ 日志级别已更改为 / Log level changed to: {new_level}")
                            else:
                                print(f"\n❌ 更改日志级别失败 / Failed to change log level")
                        else:
                            print(f"\n❌ 无效的日志级别 / Invalid log level: {new_level}")
                            print(f"   有效级别 / Valid levels: {', '.join(valid_levels)}")
                    else:
                        print("\n❌ 用法 / Usage: /log-level <级别>")
                        print("   例如 / Example: /log-level DEBUG")
                    print()
                    continue
                
                # 处理日志状态查看命令
                if query.lower() in ['/log-status', 'log-status', '/log']:
                    current_level = _get_current_log_level()
                    log_file = getattr(args, 'log_file', None)
                    print("\n📋 当前日志配置 / Current Log Configuration:")
                    print(f"  级别 / Level: {current_level}")
                    if log_file:
                        print(f"  文件 / File: {log_file}")
                    else:
                        print(f"  文件 / File: 控制台输出 / Console output")
                    print(f"  详细模式 / Verbose: {'是 / Yes' if args.verbose else '否 / No'}")
                    print()
                    continue
                
                # 处理新会话命令
                if query.lower() in ['new', '/new']:
                    session_id = agent.start_new_session()
                    logger.info(f"新会话已创建 / New session created: {session_id}")
                    print(f"\n✅ 已开始新会话 / New session started")
                    if args.verbose:
                        logger.debug(f"会话ID / Session ID: {session_id}")
                        print(f"会话ID / Session ID: {session_id}")
                    print()
                    continue
                
                # 执行查询
                logger.info(f"处理用户查询 / Processing user query: {query[:100]}")
                print("\n🔍 正在处理 / Processing...")
                try:
                    response = agent.query(query)
                    if response.get('success'):
                        logger.info("查询处理成功 / Query processed successfully")
                    else:
                        logger.warning(f"查询处理失败 / Query processing failed: {response.get('error', 'Unknown error')}")
                    print_response(response, verbose=args.verbose)
                except Exception as e:
                    # 如果query方法本身抛出异常（而不是返回错误响应）
                    logger.error(f"查询执行异常 / Query execution exception: {str(e)}", exc_info=True)
                    print(f"❌ 错误 / Error: {str(e)}")
                    if args.verbose:
                        import traceback
                        print("\n详细堆栈信息 / Detailed Traceback:")
                        traceback.print_exc()
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
        # 创建配置（优先使用环境变量，命令行参数会覆盖）
        config = None
        if args.api_base or args.api_key or args.model:
            # 如果提供了命令行参数，手动创建配置
            llm_api_key = args.api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
            config_kwargs = {}
            if llm_api_key:
                config_kwargs["llm_api_key"] = llm_api_key
            if args.api_base:
                config_kwargs["llm_base_url"] = args.api_base
            if args.model:
                config_kwargs["llm_model"] = args.model
            if config_kwargs:
                config = AgentConfig(**config_kwargs)
        
        # 创建agent（如果 config 为 None，AgentConfig 会自动从环境变量读取）
        agent = PubMedAgent(config=config, language=args.language)
        
        # 获取统计信息
        logger.info("获取Agent统计信息 / Getting agent statistics")
        stats = agent.get_agent_stats()
        
        print("📊 Agent 统计信息 / Agent Statistics:")
        print("=" * 80)
        for key, value in stats.items():
            print(f"  {key}: {value}")
        print("=" * 80)
        logger.debug(f"统计信息详情 / Statistics details: {stats}")
        
    except Exception as e:
        logger.error(f"获取统计信息失败 / Failed to get statistics: {str(e)}", exc_info=True)
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
  
  # 交互式模式（带日志控制）/ Interactive mode with log control
  pubmed-agent i --log-level DEBUG --log-file ./logs/agent.log
  
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
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='日志级别 / Log level (default: INFO)'
    )
    parser.add_argument(
        '--log-file',
        help='日志文件路径 / Log file path (可选 / optional)'
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
    
    # 初始化日志系统（在检查API密钥之前，以便记录错误）
    log_level = getattr(args, 'log_level', 'INFO')
    log_file = getattr(args, 'log_file', None)
    detailed = getattr(args, 'verbose', False)
    setup_logging(log_level=log_level, log_file=log_file, detailed=detailed)
    
    # 检查API密钥（支持 LLM_API_KEY 和 OPENAI_API_KEY）
    llm_api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not args.api_key and not llm_api_key:
        print("❌ 错误 / Error: 未找到API密钥 / API key not found")
        print("请设置环境变量 LLM_API_KEY 或 OPENAI_API_KEY，或使用 --api-key 参数")
        print("Please set LLM_API_KEY or OPENAI_API_KEY environment variable, or use --api-key argument")
        sys.exit(1)
    
    # 执行对应命令
    args.func(args)


if __name__ == "__main__":
    main()

