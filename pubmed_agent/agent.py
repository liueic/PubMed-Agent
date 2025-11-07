"""
Main ReAct PubMed Agent implementation.
Phase 1: Basic infrastructure - Core agent system.
Phase 2: Thought templates and logic control - Enhanced reasoning.
Phase 4: Programmable thinking process - Query-aware prompt selection.
Phase 5: Extensions and MCP integration - Extensible architecture.
Enhanced with comprehensive Chinese language support.
"""

import logging
import json
import uuid
from typing import List, Dict, Any, Optional, Callable

# LangChain imports with version compatibility
# LangChain 1.0+ uses a different API, so we need to handle both old and new versions
try:
    # Try LangChain 1.0+ API first
    from langchain.agents import create_agent
    from langchain_core.runnables import RunnableConfig
    LANGCHAIN_VERSION = "1.0+"
    HAS_AGENT_EXECUTOR = False
except ImportError:
    LANGCHAIN_VERSION = "0.x"
    HAS_AGENT_EXECUTOR = True
    try:
        # LangChain 0.2.x
        from langchain.agents import AgentExecutor, create_react_agent
    except ImportError:
        try:
            # LangChain 0.1.x - try alternative import paths
            from langchain_core.agents import AgentExecutor
            from langchain.agents import create_react_agent
        except ImportError:
            # Fallback for older versions
            from langchain.agents.agent import AgentExecutor
            from langchain.agents import create_react_agent

from langchain_openai import ChatOpenAI

# Memory handling - LangChain 1.0+ uses different memory API
try:
    from langchain.memory import ConversationBufferMemory
    HAS_OLD_MEMORY = True
except ImportError:
    HAS_OLD_MEMORY = False
    # LangChain 1.0+ uses checkpointer-based memory
    MemorySaver = None
    try:
        from langchain_core.checkpoints import MemorySaver
    except ImportError:
        try:
            from langgraph.checkpoint.memory import MemorySaver
        except ImportError:
            MemorySaver = None

try:
    from langchain.schema import BaseMessage
except ImportError:
    from langchain_core.messages import BaseMessage

from .config import AgentConfig
from .tools import create_tools
from .prompts import get_optimized_prompt, get_chinese_templates, get_english_templates
from .utils import setup_logging

logger = logging.getLogger(__name__)

# 临时标记常量
TEMP_QUOTE_MARKER = "___TEMP_QUOTE___"


def _clean_temp_markers(obj):
    """
    递归清理对象中的所有临时标记。
    
    Args:
        obj: 需要清理的对象（可以是字典、列表、字符串或其他类型）
        
    Returns:
        清理后的对象
    """
    if isinstance(obj, dict):
        cleaned = {}
        for k, v in obj.items():
            # 清理键
            clean_key = k.replace(TEMP_QUOTE_MARKER, '') if isinstance(k, str) else k
            # 清理值
            clean_value = _clean_temp_markers(v)
            cleaned[clean_key] = clean_value
        return cleaned
    elif isinstance(obj, list):
        return [_clean_temp_markers(item) for item in obj]
    elif isinstance(obj, str):
        return obj.replace(TEMP_QUOTE_MARKER, '')
    else:
        return obj


def _recursive_parse_json(value, max_depth=5):
    """
    递归解析JSON字符串，处理双重或多重编码的情况。
    增强版本：尝试修复不完整的JSON字符串。
    
    Args:
        value: 需要解析的值（可能是字符串、字典或其他类型）
        max_depth: 最大递归深度，防止无限循环
        
    Returns:
        解析后的字典对象，如果无法解析则返回原值
    """
    if max_depth <= 0:
        logger.warning("Reached maximum recursion depth in JSON parsing")
        return value
    
    # 如果不是字符串，直接返回
    if not isinstance(value, str):
        return value
    
    # 尝试解析JSON
    try:
        parsed = json.loads(value)
        # 如果解析后仍然是字符串，继续递归解析（处理双重编码）
        if isinstance(parsed, str):
            return _recursive_parse_json(parsed, max_depth - 1)
        # 如果是字典，确保其中的字符串值也被正确处理，并清理临时标记
        elif isinstance(parsed, dict):
            result = {k: _recursive_parse_json(v, max_depth - 1) if isinstance(v, str) else v 
                   for k, v in parsed.items()}
            return _clean_temp_markers(result)
        return parsed
    except json.JSONDecodeError as e:
        # 如果第一次解析失败，尝试修复不完整的JSON字符串
        fixed_value = value.strip()
        
        # 处理不完整的JSON字符串：可能缺少闭合引号或括号
        # 例如：'"{\\"query\\": \\"value\\"' 或 '"{\\"query\\": \\"value'
        
        # 步骤1: 去除外层引号（如果存在）
        if fixed_value.startswith('"'):
            # 检查是否有配对的结束引号
            if fixed_value.endswith('"'):
                # 有配对的引号，去除它们
                unquoted = fixed_value[1:-1]
            else:
                # 没有结束引号，只去除开始的引号
                unquoted = fixed_value[1:]
                # 如果去掉引号后仍然以转义引号开头，尝试修复
                if unquoted.startswith('\\"'):
                    unquoted = unquoted[2:]  # 去除 \\"
        else:
            unquoted = fixed_value
        
        # 步骤2: 处理转义的引号
        # 将 \\" 替换为临时标记，以便后续处理
        temp_marker = TEMP_QUOTE_MARKER
        unescaped = unquoted.replace('\\"', temp_marker)
        
        # 步骤3: 尝试补全不完整的JSON
        # 检查是否以 { 开头但没有 } 结尾
        if unescaped.startswith('{') and not unescaped.rstrip().endswith('}'):
            # 尝试补全JSON结构
            # 查找最后一个可能的值
            if ':' in unescaped:
                # 确保值部分有闭合引号（如果使用temp_marker）
                if temp_marker in unescaped:
                    # 检查是否有未配对的temp_marker
                    parts = unescaped.split(temp_marker)
                    if len(parts) % 2 == 0:
                        # 有偶数个部分，说明有未配对的引号，补全
                        unescaped = unescaped + temp_marker
                # 补全闭合括号
                unescaped = unescaped.rstrip() + '}'
                logger.debug(f"Attempting to fix incomplete JSON by adding closing brace")
        
        # 步骤4: 将临时标记替换回引号
        fixed_json = unescaped.replace(temp_marker, '"')
        
        # 步骤5: 尝试解析修复后的JSON
        try:
            parsed = json.loads(fixed_json)
            if isinstance(parsed, dict):
                cleaned = _clean_temp_markers(parsed)
                logger.info(f"Successfully parsed fixed incomplete JSON with keys: {list(cleaned.keys())}")
                return cleaned
            elif isinstance(parsed, str):
                return _recursive_parse_json(parsed, max_depth - 1)
        except json.JSONDecodeError:
            # 如果仍然失败，尝试去除外层引号（如果存在）
            if fixed_value.startswith('"') and fixed_value.endswith('"'):
                try:
                    unquoted = fixed_value[1:-1]
                    # 尝试解析去除引号后的内容
                    parsed = json.loads(unquoted)
                    if isinstance(parsed, dict):
                        return parsed
                    elif isinstance(parsed, str):
                        # 如果去除引号后仍然是字符串，继续递归解析
                        return _recursive_parse_json(parsed, max_depth - 1)
                except (json.JSONDecodeError, ValueError):
                    # 如果去除引号后仍然无法解析，尝试处理转义的JSON
                    try:
                        # 例如：'"{\\"query\\": \\"value\\"}"' -> 先去除外层引号，再解析内部
                        # 处理转义的引号：将 \\" 替换为 "
                        unescaped = unquoted.replace('\\"', '"')
                        parsed = json.loads(unescaped)
                        if isinstance(parsed, dict):
                            return parsed
                        elif isinstance(parsed, str):
                            return _recursive_parse_json(parsed, max_depth - 1)
                    except (json.JSONDecodeError, ValueError):
                        # 继续尝试其他修复方法
                        pass
        
        # 如果之前的修复都失败，尝试使用正则表达式提取键值对（即使JSON不完整）
        # 例如：从 '"{\\"query\\": \\"insect P450 gene family evolution\\"' 
        # 提取 query: "insect P450 gene family evolution"
        import re
        
        # 使用之前准备好的unquoted和temp_marker（如果它们已经定义）
        # 如果没有，重新处理
        try:
            # unquoted和temp_marker应该已经在前面定义了
            # 如果没有，重新处理
            _ = unquoted
            _ = temp_marker
        except NameError:
            # 变量未定义，重新处理
            unquoted = fixed_value
            if fixed_value.startswith('"') and fixed_value.endswith('"'):
                unquoted = fixed_value[1:-1]
            elif fixed_value.startswith('"'):
                # 只有开头引号，去除它
                unquoted = fixed_value[1:]
            temp_marker = TEMP_QUOTE_MARKER
        
        # 重新处理转义的引号（以防之前的修复改变了unescaped）
        unescaped = unquoted.replace('\\"', temp_marker)
        
        # 尝试直接匹配 JSON 键值对模式
        # 模式1: 匹配 {key": temp_marker value temp_marker 或 "key": temp_marker value temp_marker
        # 处理开头可能的 { 或 "
        pattern1 = r'\{?\s*"?([a-zA-Z_][a-zA-Z0-9_]*)"?\s*:\s*' + temp_marker + r'([^' + temp_marker + r']*)' + temp_marker
        matches1 = re.findall(pattern1, unescaped)
        
        if matches1:
            result = {}
            for key, val in matches1:
                result[key] = val
            if result:
                cleaned = _clean_temp_markers(result)
                logger.info(f"Extracted partial JSON from incomplete string using pattern1: {list(cleaned.keys())}")
                return cleaned
        
        # 模式2: 更宽松的匹配，处理可能不完整的值
        # 匹配 key": temp_marker value（可能没有结束标记）
        pattern2 = r'\{?\s*"?([a-zA-Z_][a-zA-Z0-9_]*)"?\s*:\s*' + temp_marker + r'([^' + temp_marker + r'}]*?)' + r'(?:' + temp_marker + r'|}|$)'
        matches2 = re.findall(pattern2, unescaped)
        
        if matches2:
            result = {}
            for key, val in matches2:
                result[key] = val
            if result:
                cleaned = _clean_temp_markers(result)
                logger.info(f"Extracted partial JSON using pattern2: {list(cleaned.keys())}")
                return cleaned
        
        # 模式3: 如果上面的模式都失败，尝试直接匹配转义引号格式
        # 匹配 \\"key\\": \\"value\\"
        pattern3 = r'\\"([a-zA-Z_][a-zA-Z0-9_]*)\\"\s*:\s*\\"([^\\"]*?)\\"'
        matches3 = re.findall(pattern3, unquoted)
        
        if matches3:
            result = {}
            for key, val in matches3:
                result[key] = val
            if result:
                cleaned = _clean_temp_markers(result)
                logger.info(f"Extracted partial JSON using pattern3 (escaped quotes): {list(cleaned.keys())}")
                return cleaned
        
        # 模式4: 最宽松的模式，匹配 key: value（即使值不完整）
        # 在去除转义后，尝试匹配任何 key: value 模式
        pattern4 = r'\{?\s*"?([a-zA-Z_][a-zA-Z0-9_]*)"?\s*:\s*"([^"]*)"?'
        matches4 = re.findall(pattern4, unescaped.replace(temp_marker, '"'))
        
        if matches4:
            result = {}
            for key, val in matches4:
                if val:  # 只添加非空值
                    result[key] = val
            if result:
                cleaned = _clean_temp_markers(result)
                logger.info(f"Extracted partial JSON using pattern4 (relaxed): {list(cleaned.keys())}")
                return cleaned
        
        # 如果所有修复尝试都失败，返回原值
        logger.warning(f"Failed to parse JSON string: {value[:100]}... Error: {e}")
        return value


def _extract_and_fix_tool_calls_from_error(error_str, messages):
    """
    从 Pydantic 验证错误信息中提取 tool_calls 数据并修复消息历史。
    
    当 LangChain 在创建 AIMessage 时遇到验证错误（tool_calls.0.args 是字符串而不是字典），
    此函数会从错误信息中提取所有 args 字符串，解析为字典，并修复消息历史中最后一条 AIMessage。
    支持处理多个 tool_calls 的情况。
    
    Args:
        error_str: 错误信息字符串
        messages: 当前的消息历史列表
        
    Returns:
        修复后的消息列表，如果无法修复则返回 None
    """
    import re
    from langchain_core.messages import AIMessage
    
    try:
        # 从错误信息中提取所有 tool_calls 的错误信息
        # 错误格式可能包含多个: tool_calls.0.args, tool_calls.1.args 等
        # 每个错误都有: Input should be a valid dictionary [type=dict_type, input_value='{"pmid": "..."}', input_type=str]
        
        # 提取所有 tool_calls 索引和对应的 args 字符串
        tool_call_fixes = {}  # {index: parsed_args_dict}
        
        # 匹配所有 tool_calls.X.args 错误
        # 错误格式: tool_calls.0.args\n  Input should be a valid dictionary [type=dict_type, input_value='{"pmid": "..."}', input_type=str]
        # 或者: tool_calls[0].args\n  Input should be a valid dictionary [type=dict_type, input_value='{"pmid": "..."}', input_type=str]
        pattern = r"tool_calls[\[\.](\d+)[\]\.]args[\s\S]*?input_value='([^']+)'"
        matches = re.findall(pattern, error_str, re.MULTILINE | re.DOTALL)
        
        if matches:
            for index_str, args_str in matches:
                index = int(index_str)
                logger.info(f"Found tool_call[{index}] error, args: {args_str[:100]}...")
                
                # 解析 args 字符串为字典
                parsed_args = _recursive_parse_json(args_str)
                if isinstance(parsed_args, dict):
                    tool_call_fixes[index] = parsed_args
                    logger.info(f"Successfully parsed tool_call[{index}] args: {list(parsed_args.keys())}")
                else:
                    logger.warning(f"Failed to parse tool_call[{index}] args as dict, got {type(parsed_args).__name__}")
        
        # 如果没有找到匹配的模式，尝试提取单个 args（向后兼容）
        if not tool_call_fixes:
            match = re.search(r"input_value='([^']+)'", error_str)
            if match:
                args_str = match.group(1)
                logger.info(f"Extracted single args string from error: {args_str[:100]}...")
                
                parsed_args = _recursive_parse_json(args_str)
                if isinstance(parsed_args, dict):
                    # 尝试从错误信息中提取索引
                    index_match = re.search(r"tool_calls[\[\.](\d+)", error_str)
                    index = int(index_match.group(1)) if index_match else 0
                    tool_call_fixes[index] = parsed_args
                    logger.info(f"Successfully parsed args for tool_call[{index}]: {list(parsed_args.keys())}")
        
        # 即使从错误信息中提取失败，也尝试从消息历史中直接修复 tool_calls
        # 因为错误信息中的 JSON 字符串可能被截断，但消息历史中可能包含完整的原始数据
        if not tool_call_fixes:
            logger.warning("Could not extract any tool_call args from error message, will try to fix from message history directly")
        
        # 查找所有包含 tool_calls 的消息并尝试修复（从后往前查找，优先修复最新的消息）
        fixed_messages = list(messages)  # 创建副本
        found_any_fix = False
        
        for i in range(len(fixed_messages) - 1, -1, -1):
            msg = fixed_messages[i]
            # 检查是否是 AIMessage 或包含 tool_calls
            is_ai_message = isinstance(msg, AIMessage) or (
                hasattr(msg, 'tool_calls') and msg.tool_calls
            )
            
            if is_ai_message and hasattr(msg, 'tool_calls') and msg.tool_calls:
                # 尝试修复这条消息的 tool_calls
                fixed_tool_calls = []
                found_problematic = False
                
                for idx, tc in enumerate(msg.tool_calls):
                    # 如果这个索引在修复列表中，使用修复后的 args
                    if idx in tool_call_fixes:
                        parsed_args = tool_call_fixes[idx]
                        if isinstance(tc, dict):
                            tc_dict = tc.copy()
                            # 如果 args 是字符串，使用解析后的字典
                            if isinstance(tc_dict.get('args'), str):
                                tc_dict['args'] = parsed_args
                                fixed_tool_calls.append(tc_dict)
                                found_problematic = True
                                logger.info(f"Fixed tool_call[{idx}] args from string to dict (using error extraction)")
                            else:
                                fixed_tool_calls.append(tc_dict)
                        elif hasattr(tc, 'args'):
                            # 对象格式的 tool_call
                            if isinstance(tc.args, str):
                                tc_dict = {
                                    'name': getattr(tc, 'name', ''),
                                    'args': parsed_args,
                                    'id': getattr(tc, 'id', ''),
                                    'type': getattr(tc, 'type', 'tool_call')
                                }
                                fixed_tool_calls.append(tc_dict)
                                found_problematic = True
                                logger.info(f"Fixed tool_call[{idx}] args from string to dict (using error extraction)")
                            else:
                                # 保持原样，但转换为字典格式
                                tc_dict = {
                                    'name': getattr(tc, 'name', ''),
                                    'args': getattr(tc, 'args', {}),
                                    'id': getattr(tc, 'id', ''),
                                    'type': getattr(tc, 'type', 'tool_call')
                                }
                                fixed_tool_calls.append(tc_dict)
                        else:
                            fixed_tool_calls.append(tc)
                    else:
                        # 其他 tool_call 保持不变，但确保是字典格式
                        if isinstance(tc, dict):
                            # 检查是否也需要修复（可能是字符串格式）
                            tc_dict = tc.copy()
                            if isinstance(tc_dict.get('args'), str):
                                # 尝试解析并修复
                                parsed = _recursive_parse_json(tc_dict['args'])
                                if isinstance(parsed, dict):
                                    tc_dict['args'] = parsed
                                    found_problematic = True
                                    logger.info(f"Fixed tool_call[{idx}] args from string to dict (not in error list)")
                                else:
                                    # 如果解析失败，但错误信息中提到了这个索引，尝试使用部分信息
                                    # 或者保持原样，让后续的修复逻辑处理
                                    logger.debug(f"Could not parse tool_call[{idx}] args, keeping original")
                            fixed_tool_calls.append(tc_dict)
                        else:
                            # 对象格式的 tool_call，不在 tool_call_fixes 中
                            # 检查 args 是否是字符串，如果是则尝试解析
                            args = getattr(tc, 'args', {})
                            if isinstance(args, str):
                                parsed = _recursive_parse_json(args)
                                if isinstance(parsed, dict):
                                    args = parsed
                                    found_problematic = True
                                    logger.info(f"Fixed tool_call[{idx}] args from string to dict (object format, not in error list)")
                                else:
                                    logger.debug(f"Could not parse tool_call[{idx}] args (object format), keeping original")
                            
                            tc_dict = {
                                'name': getattr(tc, 'name', ''),
                                'args': args,
                                'id': getattr(tc, 'id', ''),
                                'type': getattr(tc, 'type', 'tool_call')
                            }
                            fixed_tool_calls.append(tc_dict)
                
                if found_problematic and fixed_tool_calls:
                    # 创建新的 AIMessage 对象，使用修复后的 tool_calls
                    try:
                        # 获取消息的其他属性
                        content = getattr(msg, 'content', '') or ''
                        msg_id = getattr(msg, 'id', None)
                        
                        new_msg = AIMessage(
                            content=content,
                            tool_calls=fixed_tool_calls,
                            id=msg_id
                        )
                        fixed_messages[i] = new_msg
                        fixed_count = sum(1 for tc in fixed_tool_calls if isinstance(tc.get('args') if isinstance(tc, dict) else getattr(tc, 'args', None), dict))
                        logger.info(f"Successfully fixed {fixed_count} tool_calls in message at index {i}")
                        found_any_fix = True
                        # 继续检查其他消息，不立即返回
                    except Exception as e:
                        logger.warning(f"Failed to create new AIMessage at index {i}: {e}")
                        # 尝试直接修复原消息（如果可能）
                        try:
                            if hasattr(msg, 'tool_calls'):
                                object.__setattr__(msg, 'tool_calls', fixed_tool_calls)
                                logger.info(f"Fixed tool_calls in existing message at index {i}")
                                found_any_fix = True
                        except Exception as e2:
                            logger.error(f"Failed to fix message directly at index {i}: {e2}")
        
        if found_any_fix:
            logger.info("Successfully fixed tool_calls in at least one message")
            return fixed_messages
        
        logger.warning("Could not find AIMessage with problematic tool_calls in message history")
        return None
    except Exception as e:
        logger.error(f"Error extracting tool_calls from error: {e}", exc_info=True)
        return None


def _fix_tool_calls_args(message):
    """
    修复消息中 tool_calls 的 args 字段，将字符串格式的 args 转换为字典。
    
    某些自定义 API 端点（如 deepseek）可能返回字符串格式的 args，
    而 LangChain 期望字典格式，这会导致验证错误。
    支持处理双重或多重JSON编码的情况。
    
    Args:
        message: LangChain 消息对象
        
    Returns:
        修复后的消息对象（如果修复了任何内容）或原消息对象
    """
    if not hasattr(message, 'tool_calls') or not message.tool_calls:
        return message
    
    fixed = False
    fixed_tool_calls = []
    
    for tool_call in message.tool_calls:
        if isinstance(tool_call, dict):
            # 处理字典格式的 tool_call
            tool_call_dict = tool_call.copy()
            if 'args' in tool_call_dict:
                args = tool_call_dict['args']
                # 检查args是否为字符串类型
                if isinstance(args, str):
                    # 使用递归解析处理双重编码
                    parsed_args = _recursive_parse_json(args)
                    if isinstance(parsed_args, dict):
                        tool_call_dict['args'] = parsed_args
                        fixed = True
                        logger.debug(f"Fixed tool_call args from string to dict: {args[:50]}...")
                    else:
                        # 如果解析后仍不是字典，记录警告但继续处理
                        logger.warning(f"Failed to parse tool_call args as dict, got {type(parsed_args).__name__}: {args[:100]}...")
                        # 尝试将解析结果包装为字典（如果解析失败，使用空字典）
                        tool_call_dict['args'] = parsed_args if isinstance(parsed_args, dict) else {}
                elif not isinstance(args, dict):
                    # 如果args既不是字符串也不是字典，记录警告并尝试转换
                    logger.warning(f"Tool call args is neither string nor dict (type: {type(args).__name__}), attempting conversion")
                    try:
                        # 尝试转换为字符串再解析
                        args_str = str(args)
                        parsed_args = _recursive_parse_json(args_str)
                        if isinstance(parsed_args, dict):
                            tool_call_dict['args'] = parsed_args
                            fixed = True
                        else:
                            tool_call_dict['args'] = {}
                    except Exception as e:
                        logger.error(f"Failed to convert args to dict: {e}")
                        tool_call_dict['args'] = {}
            fixed_tool_calls.append(tool_call_dict)
        elif hasattr(tool_call, 'args'):
            # 处理对象格式的 tool_call
            if isinstance(tool_call.args, str):
                # 使用递归解析处理双重编码
                parsed_args = _recursive_parse_json(tool_call.args)
                if isinstance(parsed_args, dict):
                    tool_call.args = parsed_args
                    fixed = True
                    logger.debug(f"Fixed tool_call args from string to dict")
                else:
                    logger.warning(f"Failed to parse tool_call args as dict, got {type(parsed_args).__name__}")
                    # 尝试将解析结果赋值为空字典
                    try:
                        tool_call.args = parsed_args if isinstance(parsed_args, dict) else {}
                    except:
                        logger.warning("Failed to update tool_call.args")
            elif not isinstance(tool_call.args, dict):
                # 如果args既不是字符串也不是字典，尝试转换
                logger.warning(f"Tool call args is neither string nor dict (type: {type(tool_call.args).__name__}), attempting conversion")
                try:
                    args_str = str(tool_call.args)
                    parsed_args = _recursive_parse_json(args_str)
                    if isinstance(parsed_args, dict):
                        tool_call.args = parsed_args
                        fixed = True
                    else:
                        tool_call.args = {}
                except Exception as e:
                    logger.error(f"Failed to convert args to dict: {e}")
                    try:
                        tool_call.args = {}
                    except:
                        pass
            fixed_tool_calls.append(tool_call)
        else:
            fixed_tool_calls.append(tool_call)
    
    if fixed:
        # 如果修复了任何内容，更新消息的 tool_calls
        # 将所有 tool_call 转换为字典格式，确保 Pydantic 验证通过
        dict_tool_calls = []
        for tool_call in fixed_tool_calls:
            if isinstance(tool_call, dict):
                dict_tool_calls.append(tool_call)
            elif hasattr(tool_call, '__dict__'):
                # 将对象转换为字典
                tool_call_dict = {
                    'name': getattr(tool_call, 'name', ''),
                    'args': getattr(tool_call, 'args', {}),
                    'id': getattr(tool_call, 'id', ''),
                    'type': getattr(tool_call, 'type', 'tool_call')
                }
                dict_tool_calls.append(tool_call_dict)
            else:
                dict_tool_calls.append(tool_call)
        
        # 使用 object.__setattr__ 来绕过 Pydantic 的只读限制（如果存在）
        try:
            message.tool_calls = dict_tool_calls
        except (AttributeError, ValueError):
            # 如果直接赋值失败，尝试使用 object.__setattr__
            try:
                object.__setattr__(message, 'tool_calls', dict_tool_calls)
            except Exception as e:
                logger.warning(f"Failed to update tool_calls: {e}")
        
        logger.info("Fixed tool_calls args in message")
    
    # 最终清理：确保所有临时标记都被移除
    if hasattr(message, 'tool_calls') and message.tool_calls:
        try:
            cleaned_tool_calls = []
            for tool_call in message.tool_calls:
                if isinstance(tool_call, dict):
                    cleaned_tool_call = _clean_temp_markers(tool_call.copy())
                    cleaned_tool_calls.append(cleaned_tool_call)
                else:
                    cleaned_tool_calls.append(tool_call)
            
            # 更新tool_calls
            try:
                message.tool_calls = cleaned_tool_calls
            except (AttributeError, ValueError):
                try:
                    object.__setattr__(message, 'tool_calls', cleaned_tool_calls)
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Error cleaning temp markers from tool_calls: {e}")
    
    return message


def _fix_invalid_tool_calls(message):
    """
    修复消息中的 invalid_tool_calls，尝试将它们转换为有效的 tool_calls。
    
    Args:
        message: LangChain 消息对象
        
    Returns:
        修复后的消息对象，如果修复了invalid_tool_calls，返回修复后的消息
    """
    if not hasattr(message, 'invalid_tool_calls') or not message.invalid_tool_calls:
        return message
    
    fixed_invalid_calls = []
    valid_tool_calls = []
    
    for invalid_call in message.invalid_tool_calls:
        if isinstance(invalid_call, dict):
            # 尝试修复这个invalid_tool_call
            if 'args' in invalid_call:
                args = invalid_call['args']
                if isinstance(args, str):
                    # 规范化args字符串：去除首尾空白，处理常见的不完整格式
                    normalized_args = args.strip()
                    
                    # 记录原始args用于调试
                    logger.debug(f"Attempting to fix invalid tool_call args: {normalized_args[:100]}...")
                    
                    # 使用增强的递归解析修复双重编码和不完整的JSON
                    parsed_args = _recursive_parse_json(normalized_args)
                    if isinstance(parsed_args, dict) and len(parsed_args) > 0:
                        # 清理临时标记
                        cleaned_args = _clean_temp_markers(parsed_args)
                        # 创建一个有效的tool_call
                        fixed_call = {
                            'name': invalid_call.get('name', ''),
                            'args': cleaned_args,
                            'id': invalid_call.get('id', '')
                        }
                        valid_tool_calls.append(fixed_call)
                        logger.info(f"Fixed invalid tool_call: {invalid_call.get('name', 'unknown')} with args keys: {list(cleaned_args.keys())}")
                        continue
                    else:
                        # 解析失败，记录详细信息
                        logger.warning(f"Failed to parse invalid tool_call args for {invalid_call.get('name', 'unknown')}: {normalized_args[:100]}...")
        
        # 如果无法修复，保留为invalid
        fixed_invalid_calls.append(invalid_call)
    
    # 如果有修复成功的tool_calls，将它们添加到message的tool_calls中
    if valid_tool_calls:
        # 清理所有临时标记
        cleaned_valid_tool_calls = [_clean_temp_markers(tc) for tc in valid_tool_calls]
        
        if hasattr(message, 'tool_calls'):
            # 合并现有的tool_calls和修复后的tool_calls
            if message.tool_calls:
                message.tool_calls.extend(cleaned_valid_tool_calls)
            else:
                message.tool_calls = cleaned_valid_tool_calls
        else:
            message.tool_calls = cleaned_valid_tool_calls
        
        # 更新invalid_tool_calls列表（只保留无法修复的）
        if fixed_invalid_calls:
            message.invalid_tool_calls = fixed_invalid_calls
        else:
            # 如果没有剩余的invalid_tool_calls，清空它
            message.invalid_tool_calls = []
            # 在某些LangChain版本中，可能需要删除这个属性
            if hasattr(message, '__dict__'):
                # 如果所有invalid都被修复了，尝试删除invalid_tool_calls属性
                pass
    
    # 最终清理：确保所有临时标记都被移除
    if hasattr(message, 'tool_calls') and message.tool_calls:
        try:
            cleaned_tool_calls = [_clean_temp_markers(tc) for tc in message.tool_calls]
            try:
                message.tool_calls = cleaned_tool_calls
            except (AttributeError, ValueError):
                try:
                    object.__setattr__(message, 'tool_calls', cleaned_tool_calls)
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Error cleaning temp markers from fixed tool_calls: {e}")
    
    return message


def _fix_messages_tool_calls(messages):
    """
    修复消息列表中的所有消息的 tool_calls。
    包括修复invalid_tool_calls。
    
    Args:
        messages: 消息列表
        
    Returns:
        修复后的消息列表
    """
    if not messages:
        return messages
    
    fixed_messages = []
    for msg in messages:
        # 先修复invalid_tool_calls
        fixed_msg = _fix_invalid_tool_calls(msg)
        # 再修复tool_calls的args
        fixed_msg = _fix_tool_calls_args(fixed_msg)
        fixed_messages.append(fixed_msg)
    
    return fixed_messages


def _create_fix_tool_calls_wrapper(agent_executor, tools):
    """
    创建一个包装器函数，用于修复工具调用并处理invalid_tool_calls。
    
    Args:
        agent_executor: 原始的agent executor
        tools: 工具列表
        
    Returns:
        包装后的invoke函数
    """
    from langchain_core.messages import ToolMessage
    
    def fix_tool_calls_wrapper(input_dict, config=None):
        """包装器函数，修复消息中的 tool_calls并处理invalid_tool_calls"""
        if isinstance(input_dict, dict) and "messages" in input_dict:
            # 修复输入消息
            input_dict["messages"] = _fix_messages_tool_calls(input_dict["messages"])
        
        # 调用原始的 agent_executor，捕获验证错误
        try:
            result = agent_executor.invoke(input_dict, config=config if config is not None else {})
        except Exception as e:
            # 如果遇到tool_calls验证错误，尝试从错误信息中修复
            error_str = str(e)
            if "tool_calls" in error_str and ("dict_type" in error_str or "Input should be a valid dictionary" in error_str):
                logger.warning(f"Caught tool_calls validation error in agent_executor: {e}")
                
                # 尝试从错误信息中提取并修复 tool_calls
                if isinstance(input_dict, dict) and "messages" in input_dict:
                    # 首先尝试从消息历史中修复
                    fixed_messages = _extract_and_fix_tool_calls_from_error(error_str, input_dict["messages"])
                    
                    # 如果无法从消息历史中修复，尝试从错误信息中手动构造修复后的消息
                    if not fixed_messages:
                        try:
                            # 从错误信息中提取所有 tool_calls 的信息
                            import re
                            import uuid
                            from langchain_core.messages import AIMessage
                            
                            tool_call_fixes = {}
                            pattern = r"tool_calls[\[\.](\d+)[\]\.]args[\s\S]*?input_value='([^']+)'"
                            matches = re.findall(pattern, error_str, re.MULTILINE | re.DOTALL)
                            
                            if matches:
                                for index_str, args_str in matches:
                                    index = int(index_str)
                                    parsed_args = _recursive_parse_json(args_str)
                                    if isinstance(parsed_args, dict):
                                        tool_call_fixes[index] = parsed_args
                                        logger.info(f"Extracted tool_call[{index}] args from error: {list(parsed_args.keys())}")
                                
                                # 尝试从错误信息或消息历史中获取 tool_call 的其他信息（name, id）
                                # 首先尝试从消息历史中查找最后一条消息
                                fixed_tool_calls = []
                                if input_dict.get("messages"):
                                    # 从后往前查找，找到最后一条包含 tool_calls 的消息
                                    last_msg_with_tool_calls = None
                                    for msg in reversed(input_dict["messages"]):
                                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                            last_msg_with_tool_calls = msg
                                            break
                                    
                                    if last_msg_with_tool_calls and last_msg_with_tool_calls.tool_calls:
                                        # 使用最后一条消息的 tool_calls 结构，但修复 args
                                        for idx, tc in enumerate(last_msg_with_tool_calls.tool_calls):
                                            if idx in tool_call_fixes:
                                                if isinstance(tc, dict):
                                                    tc_dict = tc.copy()
                                                    tc_dict['args'] = tool_call_fixes[idx]
                                                    fixed_tool_calls.append(tc_dict)
                                                else:
                                                    fixed_tool_calls.append({
                                                        'name': getattr(tc, 'name', ''),
                                                        'args': tool_call_fixes[idx],
                                                        'id': getattr(tc, 'id', '') or f"call_{uuid.uuid4().hex[:8]}",
                                                        'type': getattr(tc, 'type', 'tool_call')
                                                    })
                                            else:
                                                # 保持原样，但确保是字典格式
                                                if isinstance(tc, dict):
                                                    fixed_tool_calls.append(tc)
                                                else:
                                                    fixed_tool_calls.append({
                                                        'name': getattr(tc, 'name', ''),
                                                        'args': getattr(tc, 'args', {}),
                                                        'id': getattr(tc, 'id', ''),
                                                        'type': getattr(tc, 'type', 'tool_call')
                                                    })
                                    
                                    # 如果没有找到包含 tool_calls 的消息，尝试从工具列表中推断
                                    if not fixed_tool_calls and tool_call_fixes:
                                        logger.warning("Could not find message with tool_calls, attempting to infer from tools")
                                        # 尝试从 args 中推断工具名称
                                        for idx, parsed_args in tool_call_fixes.items():
                                            # 尝试从工具列表中匹配（根据参数结构）
                                            tool_name = None
                                            
                                            # 首先尝试从常见的参数名推断
                                            if 'pmid' in parsed_args:
                                                tool_name = 'pubmed_fetch'
                                            elif 'query' in parsed_args:
                                                tool_name = 'vector_store'
                                            elif 'input_data' in parsed_args:
                                                tool_name = 'vector_store'
                                            else:
                                                # 尝试从工具列表中匹配
                                                for tool in tools:
                                                    if hasattr(tool, 'args_schema'):
                                                        try:
                                                            # 检查工具的参数键是否与解析后的参数匹配
                                                            schema = tool.args_schema
                                                            if hasattr(schema, 'schema') and isinstance(schema.schema, dict):
                                                                schema_props = schema.schema.get('properties', {})
                                                                if set(parsed_args.keys()).issubset(set(schema_props.keys())):
                                                                    tool_name = tool.name
                                                                    break
                                                        except:
                                                            pass
                                            
                                            # 如果仍然无法推断，使用第一个工具或默认名称
                                            if not tool_name:
                                                tool_name = tools[0].name if tools else 'unknown_tool'
                                            
                                            fixed_tool_calls.append({
                                                'name': tool_name,
                                                'args': parsed_args,
                                                'id': f"call_{uuid.uuid4().hex[:8]}",
                                                'type': 'tool_call'
                                            })
                                            logger.info(f"Inferred tool name '{tool_name}' for tool_call[{idx}] with args keys: {list(parsed_args.keys())}")
                                    
                                    # 如果成功构造了 tool_calls，创建修复后的消息
                                    if fixed_tool_calls:
                                        # 尝试从最后一条消息获取 content
                                        last_msg = input_dict["messages"][-1] if input_dict["messages"] else None
                                        content = getattr(last_msg, 'content', '') or '' if last_msg else ''
                                        
                                        # 检查最后一条消息是否是 AIMessage（可能是部分创建的失败消息）
                                        is_last_ai = isinstance(last_msg, AIMessage) if last_msg else False
                                        
                                        # 创建修复后的消息
                                        fixed_msg = AIMessage(
                                            content=content,
                                            tool_calls=fixed_tool_calls,
                                            id=getattr(last_msg, 'id', None) if last_msg else None
                                        )
                                        
                                        # 根据最后一条消息的类型决定是替换还是添加
                                        fixed_messages = list(input_dict["messages"])
                                        if is_last_ai:
                                            # 如果最后一条是 AIMessage（可能是失败的），替换它
                                            fixed_messages[-1] = fixed_msg
                                            logger.info(f"Replaced failed AIMessage with fixed message containing {len(fixed_tool_calls)} tool_calls")
                                        else:
                                            # 如果最后一条不是 AIMessage，添加新的消息
                                            fixed_messages.append(fixed_msg)
                                            logger.info(f"Added fixed AIMessage with {len(fixed_tool_calls)} tool_calls")
                        except Exception as manual_fix_e:
                            logger.warning(f"Could not manually fix from error: {manual_fix_e}", exc_info=True)
                    
                    # 如果仍然无法修复，尝试从 checkpointer 中获取最后的消息
                    if not fixed_messages and config and isinstance(config, dict):
                        try:
                            # 尝试从 checkpointer 获取最后的消息
                            checkpointer = config.get("configurable", {}).get("checkpoint_id")
                            if not checkpointer and hasattr(agent_executor, 'checkpointer'):
                                # 尝试从 agent_executor 获取 checkpointer
                                checkpointer = agent_executor.checkpointer
                            
                            if checkpointer:
                                # 尝试从 checkpointer 获取最后的消息
                                # 注意：这可能需要根据实际的 checkpointer 实现来调整
                                logger.info("Attempting to retrieve last message from checkpointer...")
                        except Exception as checkpoint_e:
                            logger.debug(f"Could not retrieve from checkpointer: {checkpoint_e}")
                    
                    if fixed_messages:
                        logger.info("Successfully extracted and fixed tool_calls from error, retrying...")
                        # 使用修复后的消息重试
                        input_dict["messages"] = fixed_messages
                        try:
                            result = agent_executor.invoke(input_dict, config=config if config is not None else {})
                        except Exception as retry_e:
                            logger.error(f"Retry after fix still failed: {retry_e}")
                            # 如果重试仍然失败，尝试最后一次修复
                            error_str_retry = str(retry_e)
                            if "tool_calls" in error_str_retry and ("dict_type" in error_str_retry or "Input should be a valid dictionary" in error_str_retry):
                                fixed_messages_retry = _extract_and_fix_tool_calls_from_error(error_str_retry, input_dict["messages"])
                                if fixed_messages_retry:
                                    input_dict["messages"] = fixed_messages_retry
                                    result = agent_executor.invoke(input_dict, config=config if config is not None else {})
                                else:
                                    raise e  # 抛出原始错误
                            else:
                                raise e  # 抛出原始错误
                    else:
                        logger.warning("Failed to extract tool_calls from error, re-raising original error")
                        raise
                else:
                    logger.warning("Cannot fix error: input_dict does not contain messages")
                    raise
            else:
                # 其他类型的错误，直接抛出
                raise
        
        # 修复返回消息并处理invalid_tool_calls
        if isinstance(result, dict) and "messages" in result:
            result["messages"] = _fix_messages_tool_calls(result["messages"])
            
            # 检查是否有修复后的tool_calls需要执行
            # 查找最后一条包含invalid_tool_calls但已被修复的消息
            last_message = None
            for msg in reversed(result["messages"]):
                if hasattr(msg, 'invalid_tool_calls') and msg.invalid_tool_calls:
                    # 尝试修复invalid_tool_calls
                    fixed_msg = _fix_invalid_tool_calls(msg)
                    
                    # 如果修复成功（有新的tool_calls），记录这条消息
                    if hasattr(fixed_msg, 'tool_calls') and fixed_msg.tool_calls:
                        # 检查这些tool_calls是否是新修复的（通过比较tool_calls和invalid_tool_calls的数量）
                        original_valid_count = len(msg.tool_calls) if hasattr(msg, 'tool_calls') and msg.tool_calls else 0
                        fixed_valid_count = len(fixed_msg.tool_calls) if fixed_msg.tool_calls else 0
                        
                        if fixed_valid_count > original_valid_count:
                            last_message = fixed_msg
                            # 更新消息列表中的消息
                            msg_idx = result["messages"].index(msg)
                            result["messages"][msg_idx] = fixed_msg
                            break
            
            # 如果有修复后的tool_calls，执行它们
            # 使用循环处理连续的工具调用，直到没有更多的工具调用需要执行
            max_iterations = 10  # 防止无限循环
            iteration = 0
            while iteration < max_iterations:
                iteration += 1
                has_tool_calls_to_execute = False
                
                # 查找最后一条包含tool_calls但还没有执行结果的消息
                last_message = None
                for msg in reversed(result["messages"]):
                    # 检查是否有tool_calls
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        # 检查是否已经有对应的ToolMessage
                        tool_call_ids = [tc.get('id') if isinstance(tc, dict) else getattr(tc, 'id', '') 
                                        for tc in msg.tool_calls]
                        has_results = any(
                            hasattr(m, 'tool_call_id') and m.tool_call_id in tool_call_ids
                            for m in result["messages"]
                            if hasattr(m, 'tool_call_id')
                        )
                        
                        if not has_results:
                            last_message = msg
                            has_tool_calls_to_execute = True
                            break
                    
                    # 也检查是否有invalid_tool_calls但已被修复
                    if hasattr(msg, 'invalid_tool_calls') and msg.invalid_tool_calls:
                        fixed_msg = _fix_invalid_tool_calls(msg)
                        if hasattr(fixed_msg, 'tool_calls') and fixed_msg.tool_calls:
                            # 检查这些tool_calls是否已经执行
                            tool_call_ids = [tc.get('id') if isinstance(tc, dict) else getattr(tc, 'id', '') 
                                            for tc in fixed_msg.tool_calls]
                            has_results = any(
                                hasattr(m, 'tool_call_id') and m.tool_call_id in tool_call_ids
                                for m in result["messages"]
                                if hasattr(m, 'tool_call_id')
                            )
                            
                            if not has_results:
                                last_message = fixed_msg
                                # 更新消息列表中的消息
                                msg_idx = result["messages"].index(msg)
                                result["messages"][msg_idx] = fixed_msg
                                has_tool_calls_to_execute = True
                                break
                
                if not has_tool_calls_to_execute or not last_message:
                    break
                
                # 执行工具调用
                tool_calls_to_execute = last_message.tool_calls if hasattr(last_message, 'tool_calls') and last_message.tool_calls else []
                tool_results = []
                
                for tool_call in tool_calls_to_execute:
                    # 清理工具调用中的临时标记
                    cleaned_tool_call = _clean_temp_markers(tool_call) if isinstance(tool_call, dict) else tool_call
                    
                    tool_name = cleaned_tool_call.get('name') if isinstance(cleaned_tool_call, dict) else getattr(cleaned_tool_call, 'name', None)
                    tool_args = cleaned_tool_call.get('args') if isinstance(cleaned_tool_call, dict) else getattr(cleaned_tool_call, 'args', {})
                    tool_id = cleaned_tool_call.get('id') if isinstance(cleaned_tool_call, dict) else getattr(cleaned_tool_call, 'id', '')
                    
                    # 确保tool_args是字典类型（如果不是，尝试修复）
                    if not isinstance(tool_args, dict):
                        logger.warning(f"Tool args for {tool_name} is not a dict (type: {type(tool_args).__name__}), attempting to fix")
                        if isinstance(tool_args, str):
                            # 尝试解析JSON字符串
                            parsed_args = _recursive_parse_json(tool_args)
                            if isinstance(parsed_args, dict):
                                tool_args = parsed_args
                            else:
                                # 如果解析失败，根据工具名称决定如何处理
                                if tool_name == "vector_store":
                                    # vector_store工具接受字符串参数（JSON字符串或PMID）
                                    # 如果解析失败，保持原字符串（可能是被截断的JSON，工具内部会尝试修复）
                                    logger.debug(f"Keeping string args for vector_store (may be truncated JSON): {tool_args[:100]}...")
                                    # tool_args保持为字符串，不需要修改
                                else:
                                    # 其他工具，尝试转换为字符串
                                    tool_args = str(tool_args)
                        else:
                            # 非字符串非字典类型，尝试转换为字符串
                            tool_args = str(tool_args)
                    
                    # 最终清理工具参数
                    if isinstance(tool_args, dict):
                        tool_args = _clean_temp_markers(tool_args)
                    elif isinstance(tool_args, str):
                        tool_args = tool_args.replace(TEMP_QUOTE_MARKER, '')
                    
                    if tool_name:
                        # 查找对应的工具
                        tool = next((t for t in tools if t.name == tool_name), None)
                        if tool:
                            try:
                                # 执行工具
                                if isinstance(tool_args, dict):
                                    # 对于vector_store工具，它期望接收一个字符串参数（JSON字符串或PMID）
                                    if tool_name == "vector_store":
                                        # 如果字典有input_data键，使用该值
                                        if "input_data" in tool_args:
                                            input_data_value = tool_args["input_data"]
                                            # 检查 input_data 值是否是不完整的 JSON 字符串
                                            if isinstance(input_data_value, str):
                                                # 如果字符串看起来像是不完整的 JSON（例如只有 '{' 或 '{\\\\'），尝试从消息历史中获取完整数据
                                                stripped = input_data_value.strip()
                                                if stripped.startswith('{') and (len(stripped) < 10 or not stripped.rstrip().endswith('}')):
                                                    logger.warning(f"Detected potentially incomplete JSON in input_data: {stripped[:100]}...")
                                                    # 尝试从消息历史中查找最近的 pubmed_fetch 工具结果
                                                    # 查找最近的 ToolMessage，其内容可能是完整的 JSON
                                                    if isinstance(input_dict, dict) and "messages" in input_dict:
                                                        found_complete_data = False
                                                        # 从后往前查找最近的 ToolMessage
                                                        for msg in reversed(input_dict["messages"]):
                                                            if hasattr(msg, 'content') and isinstance(msg.content, str):
                                                                # 检查是否是 pubmed_fetch 的结果（通常包含 "pmid" 和 "title" 字段）
                                                                if '"pmid"' in msg.content and '"title"' in msg.content:
                                                                    # 尝试提取 JSON 数据
                                                                    try:
                                                                        import json
                                                                        import re
                                                                        # 尝试从内容中提取 JSON 对象
                                                                        # 使用更可靠的方法：查找完整的 JSON 对象（处理嵌套）
                                                                        # 首先尝试直接解析整个内容
                                                                        try:
                                                                            parsed = json.loads(msg.content)
                                                                            if isinstance(parsed, dict) and "pmid" in parsed:
                                                                                input_data_value = json.dumps(parsed, ensure_ascii=False)
                                                                                logger.info(f"Found complete JSON data from previous message content, using it")
                                                                                found_complete_data = True
                                                                                break
                                                                        except json.JSONDecodeError:
                                                                            # 如果整个内容不是 JSON，尝试提取 JSON 对象
                                                                            # 查找第一个 { 和匹配的 }
                                                                            start_idx = msg.content.find('{')
                                                                            if start_idx != -1:
                                                                                brace_count = 0
                                                                                end_idx = start_idx
                                                                                for i in range(start_idx, len(msg.content)):
                                                                                    if msg.content[i] == '{':
                                                                                        brace_count += 1
                                                                                    elif msg.content[i] == '}':
                                                                                        brace_count -= 1
                                                                                        if brace_count == 0:
                                                                                            end_idx = i + 1
                                                                                            break
                                                                                if end_idx > start_idx:
                                                                                    potential_json = msg.content[start_idx:end_idx]
                                                                                    try:
                                                                                        parsed = json.loads(potential_json)
                                                                                        if isinstance(parsed, dict) and "pmid" in parsed:
                                                                                            input_data_value = json.dumps(parsed, ensure_ascii=False)
                                                                                            logger.info(f"Found complete JSON data from previous message, using it instead of incomplete input_data")
                                                                                            found_complete_data = True
                                                                                            break
                                                                                    except json.JSONDecodeError:
                                                                                        pass
                                                                    except Exception as e:
                                                                        logger.debug(f"Failed to extract JSON from previous message: {e}")
                                                    if not found_complete_data:
                                                        logger.debug(f"Could not find complete JSON data, passing incomplete input_data to tool for internal repair: {stripped[:200]}")
                                            tool_result = tool.run(input_data_value)
                                        else:
                                            # 否则，将整个字典序列化为JSON字符串
                                            import json
                                            tool_result = tool.run(json.dumps(tool_args, ensure_ascii=False))
                                    else:
                                        # 其他工具：如果只有一个键值对，提取值；否则用**展开
                                        if len(tool_args) == 1:
                                            tool_result = tool.run(list(tool_args.values())[0])
                                        else:
                                            tool_result = tool.run(**tool_args)
                                else:
                                    # 非字典参数，直接传递给工具（例如vector_store工具可能接受字符串PMID）
                                    tool_result = tool.run(tool_args)
                                
                                # 创建ToolMessage
                                tool_message = ToolMessage(
                                    content=str(tool_result),
                                    tool_call_id=tool_id
                                )
                                tool_results.append(tool_message)
                                logger.info(f"Executed tool_call: {tool_name} (iteration {iteration})")
                            except Exception as e:
                                logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
                                tool_message = ToolMessage(
                                    content=f"Error: {str(e)}",
                                    tool_call_id=tool_id
                                )
                                tool_results.append(tool_message)
                
                # 如果有工具执行结果，将它们添加到消息列表并继续执行
                if tool_results:
                    result["messages"].extend(tool_results)
                    logger.debug(f"Added {len(tool_results)} tool results, continuing agent execution...")
                    
                    # 在调用前修复消息，确保tool_calls格式正确
                    messages_to_send = _fix_messages_tool_calls(result["messages"])
                    
                    # 继续执行agent，传入工具执行结果
                    try:
                        continue_result = agent_executor.invoke(
                            {"messages": messages_to_send},
                            config=config if config is not None else {}
                        )
                    except Exception as e:
                        # 如果遇到tool_calls验证错误，尝试从错误信息中修复
                        error_str = str(e)
                        if "tool_calls" in error_str and ("dict_type" in error_str or "Input should be a valid dictionary" in error_str):
                            logger.warning(f"Caught tool_calls validation error in continue_result invoke: {e}")
                            # 尝试从错误信息中提取并修复tool_calls
                            fixed_messages = _extract_and_fix_tool_calls_from_error(error_str, messages_to_send)
                            if fixed_messages:
                                logger.info("Successfully extracted and fixed tool_calls from error, retrying...")
                                messages_to_send = fixed_messages
                                # 再次尝试调用
                                try:
                                    continue_result = agent_executor.invoke(
                                        {"messages": messages_to_send},
                                        config=config if config is not None else {}
                                    )
                                except Exception as e2:
                                    # 如果重试仍然失败，尝试更激进的修复策略
                                    logger.warning(f"Retry after fix still failed: {e2}")
                                    # 尝试修复所有消息中的 tool_calls（包括字符串格式的）
                                    messages_to_send = _fix_messages_tool_calls(messages_to_send)
                                    # 再次尝试调用
                                    continue_result = agent_executor.invoke(
                                        {"messages": messages_to_send},
                                        config=config if config is not None else {}
                                    )
                            else:
                                # 如果无法从错误信息中修复，尝试更激进的修复策略
                                logger.warning("Could not extract tool_calls from error, trying aggressive fix on all messages")
                                # 尝试修复所有消息中的 tool_calls（包括字符串格式的）
                                messages_to_send = _fix_messages_tool_calls(messages_to_send)
                                # 再次尝试调用
                                try:
                                    continue_result = agent_executor.invoke(
                                        {"messages": messages_to_send},
                                        config=config if config is not None else {}
                                    )
                                except Exception as e2:
                                    # 如果仍然失败，重新抛出原始错误
                                    logger.error(f"All fix attempts failed, raising original error: {e}")
                                    raise e
                        else:
                            # 其他类型的错误，直接抛出
                            raise
                    
                    # 更新结果并修复消息
                    if isinstance(continue_result, dict) and "messages" in continue_result:
                        # 修复返回的消息中的 tool_calls
                        result["messages"] = _fix_messages_tool_calls(continue_result["messages"])
                        
                        # 检查最后一条消息是否有新的tool_calls
                        # 如果没有tool_calls，说明agent已经返回了最终答案，应该退出循环
                        last_msg = None
                        for msg in reversed(result["messages"]):
                            if hasattr(msg, 'type') and msg.type == "ai":
                                last_msg = msg
                                break
                        
                        # 如果最后一条消息没有tool_calls或tool_calls已经全部执行完成，说明是最终答案
                        if last_msg:
                            has_new_tool_calls = False
                            if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                                # 检查这些tool_calls是否已经执行
                                tool_call_ids = [tc.get('id') if isinstance(tc, dict) else getattr(tc, 'id', '') 
                                                for tc in last_msg.tool_calls]
                                has_results = any(
                                    hasattr(m, 'tool_call_id') and m.tool_call_id in tool_call_ids
                                    for m in result["messages"]
                                    if hasattr(m, 'tool_call_id')
                                )
                                # 如果有tool_calls但没有执行结果，说明需要继续执行
                                if not has_results:
                                    has_new_tool_calls = True
                            
                            # 如果没有新的tool_calls，说明agent已经返回了最终答案，退出循环
                            if not has_new_tool_calls:
                                logger.debug("Agent returned final answer (no more tool calls), exiting loop")
                                break
                else:
                    # 没有工具结果，退出循环
                    break
            
            if iteration >= max_iterations:
                logger.warning(f"Reached maximum iterations ({max_iterations}) in tool call execution loop")
            
            # 检查是否还有无法修复的invalid_tool_calls
            # 如果有，创建错误消息并让agent重新尝试（限制重试次数）
            max_retries = 3
            retry_count = 0
            
            # 计算消息中invalid_tool_calls的数量
            total_invalid_calls = sum(
                len(msg.invalid_tool_calls) if hasattr(msg, 'invalid_tool_calls') and msg.invalid_tool_calls else 0
                for msg in result["messages"]
            )
            
            # 只有当invalid_tool_calls数量不超过限制时才尝试重试
            if total_invalid_calls > 0 and total_invalid_calls <= max_retries:
                for msg in result["messages"]:
                    if hasattr(msg, 'invalid_tool_calls') and msg.invalid_tool_calls:
                        # 再次尝试修复（可能之前的修复已经部分成功）
                        fixed_msg = _fix_invalid_tool_calls(msg)
                        if hasattr(fixed_msg, 'invalid_tool_calls') and fixed_msg.invalid_tool_calls:
                            # 创建错误消息，通知agent工具调用失败，需要重新尝试
                            invalid_call = fixed_msg.invalid_tool_calls[0]
                            tool_name = invalid_call.get('name', 'unknown') if isinstance(invalid_call, dict) else getattr(invalid_call, 'name', 'unknown')
                            error_msg = invalid_call.get('error', 'Invalid tool call arguments') if isinstance(invalid_call, dict) else getattr(invalid_call, 'error', 'Invalid tool call arguments')
                            tool_id = invalid_call.get('id', '') if isinstance(invalid_call, dict) else getattr(invalid_call, 'id', '')
                            
                            # 提取args字符串中的信息用于提示
                            args_str = invalid_call.get('args', '') if isinstance(invalid_call, dict) else getattr(invalid_call, 'args', '')
                            parsed_args = _recursive_parse_json(args_str) if isinstance(args_str, str) else {}
                            
                            # 如果成功提取了部分参数，在错误消息中提示
                            if isinstance(parsed_args, dict) and len(parsed_args) > 0:
                                error_message_content = (
                                    f"工具调用参数格式错误 (Tool call argument format error): {tool_name}\n"
                                    f"已提取的参数 (Extracted parameters): {parsed_args}\n"
                                    f"请使用正确的JSON格式重新调用，例如: {{\"query\": \"your search term\"}}"
                                    f"Please use correct JSON format, e.g.: {{\"query\": \"your search term\"}}"
                                )
                            else:
                                error_message_content = (
                                    f"工具调用失败 (Tool call failed): {tool_name}\n"
                                    f"错误信息 (Error): JSON格式不正确。请使用正确的JSON格式调用工具，例如: {{\"query\": \"your search term\"}}\n"
                                    f"JSON format is incorrect. Please use correct JSON format, e.g.: {{\"query\": \"your search term\"}}"
                                )
                            
                            tool_error_message = ToolMessage(
                                content=error_message_content,
                                tool_call_id=tool_id if tool_id else f"error_{tool_name}"
                            )
                            result["messages"].append(tool_error_message)
                            logger.warning(f"Created error message for unfixable invalid tool_call: {tool_name}")
                            
                            # 让agent继续执行，传入错误消息（只重试一次）
                            continue_result = agent_executor.invoke(
                                {"messages": result["messages"]},
                                config=config if config is not None else {}
                            )
                            # 更新结果并修复消息
                            if isinstance(continue_result, dict) and "messages" in continue_result:
                                # 修复返回的消息中的 tool_calls
                                result["messages"] = _fix_messages_tool_calls(continue_result["messages"])
                            break
            
            # 最终修复所有消息
            result["messages"] = _fix_messages_tool_calls(result["messages"])
        
        return result
    
    return fix_tool_calls_wrapper


class PubMedAgent:
    """
    ReAct PubMed Agent for intelligent scientific literature search and analysis.
    
    This agent uses the ReAct (Reasoning and Acting) framework to:
    1. Search PubMed for relevant articles
    2. Store articles in a vector database for semantic search
    3. Retrieve and synthesize information based on user queries
    4. Provide evidence-based answers with proper citations
    
    Phase 1: Basic infrastructure - Core agent functionality
    Phase 2: Thought templates - Enhanced reasoning capabilities
    Phase 4: Programmable thinking process - Query-aware behavior
    Phase 5: Extensions and MCP integration - Extensible design
    Enhanced with Chinese language support for broader accessibility.
    """
    
    def __init__(self, config: Optional[AgentConfig] = None, language: str = "auto"):
        """
        Initialize the PubMed Agent.
        
        Args:
            config: Agent configuration. If None, loads from environment variables.
            language: Language setting ("en", "zh", "auto" for auto-detection)
        """
        self.config = config or AgentConfig()
        self.language = language
        
        # Initialize LLM - 支持多种大模型供应商
        # 构建 LLM 初始化参数
        llm_kwargs = {
            "model": self.config.llm_model,
            "temperature": self.config.temperature,
            "openai_api_key": self.config.llm_api_key,
        }
        
        # 添加 top_p 参数（默认 0.95，适合大多数模型）
        model_kwargs = {}
        if hasattr(self.config, 'top_p') and self.config.top_p is not None:
            model_kwargs["top_p"] = self.config.top_p
        if model_kwargs:
            llm_kwargs["model_kwargs"] = model_kwargs
        
        # 如果设置了自定义 base_url，则使用它（支持 Azure、本地模型等）
        if self.config.llm_base_url:
            llm_kwargs["base_url"] = self.config.llm_base_url
        
        self.llm = ChatOpenAI(**llm_kwargs)
        
        # Initialize tools
        self.tools = create_tools(self.config, thread_id_getter=self._thread_id_getter)
        
        # Initialize memory for conversation context
        if HAS_OLD_MEMORY:
            self.memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
        else:
            # LangChain 1.0+ uses checkpointer
            self.memory = MemorySaver() if MemorySaver else None
        
        # Create agent
        self.agent_executor = self._create_agent()
        
        logger.info(f"PubMedAgent initialized successfully (language: {self.language}, LangChain: {LANGCHAIN_VERSION})")
    
    def _create_agent(self):
        """
        Create the ReAct agent executor.
        
        Phase 1: Basic infrastructure - Agent creation
        Phase 2: Thought templates - Enhanced prompt integration
        Enhanced with Chinese language support and structured workflow.
        Supports both LangChain 0.x and 1.0+ APIs.
        """
        if LANGCHAIN_VERSION == "1.0+":
            # LangChain 1.0+ API - use create_agent which returns a graph
            from .prompts import get_chinese_templates, get_english_templates
            
            # Get appropriate system prompt based on language - default to structured workflow
            if self.language == "zh":
                templates = get_chinese_templates()
                # Prefer structured template, fallback to scientific
                system_prompt = templates.get("structured", templates.get("chinese_scientific", templates["chinese"]))
            else:
                templates = get_english_templates()
                # Prefer structured template, fallback to scientific
                system_prompt = templates.get("structured", templates.get("scientific", templates["basic"]))
            
            # Extract system prompt text from template
            if hasattr(system_prompt, 'template'):
                # It's a PromptTemplate, extract the template string
                system_prompt_text = system_prompt.template.split("Question:")[0].strip()
            else:
                system_prompt_text = str(system_prompt)
            
            # Create agent graph (already compiled in LangChain 1.0+)
            agent_executor = create_agent(
                model=self.llm,
                tools=self.tools,
                system_prompt=system_prompt_text,
                checkpointer=self.memory,
                debug=True
            )
            
            # 包装 agent_executor 以修复 tool_calls 中的 args 字段
            # 某些自定义 API 端点可能返回字符串格式的 args，需要转换为字典
            from langchain_core.runnables import RunnableLambda
            
            fix_tool_calls_wrapper = _create_fix_tool_calls_wrapper(agent_executor, self.tools)
            
            # 创建包装的 Runnable
            wrapped_agent = RunnableLambda(fix_tool_calls_wrapper)
            # 复制 invoke 方法，使其行为与原始 agent_executor 一致
            wrapped_agent.invoke = fix_tool_calls_wrapper
            
            return wrapped_agent
        else:
            # LangChain 0.x API - use traditional AgentExecutor
            # Get tool names for the prompt
            tool_names = [tool.name for tool in self.tools]
            
            # Create the prompt template with structured workflow (default: structured=True)
            from .prompts import get_react_prompt_template
            prompt = get_react_prompt_template(
                prompt_type="scientific",
                language=self.language,
                structured=True  # Default to structured workflow
            )
            
            # Create ReAct agent
            agent = create_react_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=prompt
            )
            
            # Create agent executor with enhanced configuration
            agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=True,
                memory=self.memory,
                max_iterations=10,
                early_stopping_method="generate",
                handle_parsing_errors=True,
                return_intermediate_steps=True
            )
            
            return agent_executor
    
    def start_new_session(self) -> str:
        """
        Start a new conversation session.
        
        Generates a new thread_id for the session, which will be used for all subsequent
        queries until a new session is started. This allows maintaining conversation context
        across multiple queries in the same session.
        
        Returns:
            The new session thread_id
        """
        self._session_thread_id = str(uuid.uuid4())
        logger.info(f"Started new session with thread_id: {self._session_thread_id}")
        return self._session_thread_id
    
    def get_current_session_id(self) -> Optional[str]:
        """
        Get the current session thread_id.
        
        Returns:
            The current session thread_id, or None if no session has been started
        """
        return self._session_thread_id
    
    def query(self, question: str, prompt_type: Optional[str] = None, language: Optional[str] = None, thread_id: Optional[str] = None, new_session: bool = False) -> Dict[str, Any]:
        """
        Query the agent with a scientific question.
        
        Phase 4: Programmable thinking process - Query-aware prompt selection.
        Enhanced with Chinese language support and multi-turn conversation support.
        
        Args:
            question: The scientific question to answer
            prompt_type: Optional prompt type override. If None, auto-classifies.
            language: Language override ("en", "zh"). If None, uses instance default.
            thread_id: Optional explicit thread_id to use. If provided, this thread_id will be used
                       and the session will be updated to use this thread_id.
            new_session: If True, start a new conversation session. Defaults to False.
        
        Returns:
            Dictionary containing the answer and metadata, including the thread_id used
        """
        try:
            logger.info(f"Processing query: {question}")
            
            # Session management: determine thread_id for this query
            # Priority: 1. explicit thread_id parameter, 2. new_session flag, 3. existing session, 4. create new
            if thread_id is not None:
                # Use explicitly provided thread_id and update session
                self._session_thread_id = thread_id
                thread_id_to_use = thread_id
                logger.info(f"Using explicit thread_id: {thread_id_to_use}")
            elif new_session:
                # Start a new session
                thread_id_to_use = self.start_new_session()
                logger.info(f"Started new session with thread_id: {thread_id_to_use}")
            elif self._session_thread_id is not None:
                # Reuse existing session
                thread_id_to_use = self._session_thread_id
                logger.info(f"Reusing existing session with thread_id: {thread_id_to_use}")
            else:
                # No session exists, create one
                thread_id_to_use = self.start_new_session()
                logger.info(f"Created new session with thread_id: {thread_id_to_use}")
            
            # 设置当前thread_id，工具会通过thread_id_getter获取
            self._current_thread_id = thread_id_to_use
            logger.info(f"Using thread_id for vector database isolation: {thread_id_to_use}")
            
            # Determine language for this query
            query_language = language or self.language
            if query_language == "auto":
                from .prompts import detect_language
                query_language = detect_language(question)
            
            # Phase 4: Classify query type if not specified
            if prompt_type is None:
                from .prompts import classify_query_type
                prompt_type = classify_query_type(question)
            
            # Recreate agent with appropriate prompt type and language
            if query_language != self.language or prompt_type != "scientific":
                self.agent_executor = self._create_agent_with_prompt(prompt_type, query_language)
            
            # Execute the query - handle both LangChain 0.x and 1.0+ APIs
            if LANGCHAIN_VERSION == "1.0+":
                # LangChain 1.0+ uses different invoke signature
                from langchain_core.messages import HumanMessage
                config = {}
                if self.memory:
                    # 使用会话的thread_id，保持对话上下文
                    config = {"configurable": {"thread_id": thread_id_to_use}}
                
                # Invoke with messages format
                result = self.agent_executor.invoke(
                    {"messages": [HumanMessage(content=question)]},
                    config=config if config else None
                )
                
                # Extract output from LangChain 1.0+ response format
                # Result is a dict with "messages" key containing message objects
                if isinstance(result, dict) and "messages" in result:
                    messages = result["messages"]
                    # Get all assistant messages
                    assistant_messages = [msg for msg in messages if hasattr(msg, 'content') and msg.type == "ai"]
                    
                    if assistant_messages:
                        # 优先选择最后一条没有tool_call或tool_call全部有效的消息
                        # 如果最后一条消息包含invalid_tool_calls，向前查找包含完整content的消息
                        selected_message = None
                        
                        # 从后往前查找，优先选择没有tool_call或tool_call全部有效的消息
                        for msg in reversed(assistant_messages):
                            # 检查是否有invalid_tool_calls
                            has_invalid_calls = (hasattr(msg, 'invalid_tool_calls') and 
                                               msg.invalid_tool_calls and 
                                               len(msg.invalid_tool_calls) > 0)
                            
                            # 检查是否有有效的tool_calls
                            has_valid_calls = (hasattr(msg, 'tool_calls') and 
                                             msg.tool_calls and 
                                             len(msg.tool_calls) > 0)
                            
                            # 选择有content且没有invalid_tool_calls的消息
                            # 或者有content且tool_calls全部有效的消息
                            if msg.content and not has_invalid_calls:
                                selected_message = msg
                                logger.debug(f"Selected assistant message with content length: {len(msg.content)}")
                                break
                        
                        # 如果没有找到合适的消息，使用最后一条消息（即使有invalid_tool_calls）
                        if selected_message is None and assistant_messages:
                            selected_message = assistant_messages[-1]
                            logger.warning(f"Using last assistant message (may have invalid tool calls)")
                        
                        if selected_message and selected_message.content:
                            output = selected_message.content
                            # 如果content被截断（以不完整句子结尾），记录警告
                            if output and len(output) > 0 and not output.strip().endswith(('.', '!', '?', '。', '！', '？')):
                                # 检查是否是真正的截断（而不是自然结束）
                                if len(output) > 100 and not any(output.endswith(ending) for ending in ['.', '!', '?', '。', '！', '？', '...', '…']):
                                    logger.warning(f"Answer content may be truncated: {output[-50:]}")
                        else:
                            output = str(result)
                            logger.warning("No valid assistant message content found")
                    else:
                        output = str(result)
                        logger.warning("No assistant messages found in result")
                else:
                    output = str(result)
            else:
                # LangChain 0.x API
                result = self.agent_executor.invoke({"input": question})
                output = result.get("output", "")
            
            response = {
                "question": question,
                "answer": output,
                "intermediate_steps": result.get("intermediate_steps", []) if isinstance(result, dict) else [],
                "prompt_type": prompt_type,
                "language": query_language,
                "thread_id": thread_id_to_use,  # 使用会话的thread_id
                "success": True
            }
            
            logger.info(f"Query completed successfully for: {question}")
            return response
            
        except Exception as e:
            # 提取详细的错误信息
            error_details = self._extract_error_details(e)
            error_msg = error_details.get("message", f"Error processing query: {str(e)}")
            
            # 记录详细错误信息
            logger.error(f"{error_msg}")
            if error_details.get("details"):
                logger.error(f"错误详情: {error_details['details']}")
            
            # 构建用户友好的错误消息
            user_message = self._build_user_error_message(error_details)
            
            return {
                "question": question,
                "answer": user_message,
                "intermediate_steps": [],
                "prompt_type": prompt_type or "scientific",
                "language": language or self.language,
                "thread_id": self._current_thread_id,  # 即使出错也记录thread_id
                "success": False,
                "error": error_msg,
                "error_details": error_details
            }
    
    def _create_agent_with_prompt(self, prompt_type: str, language: str):
        """
        Create agent executor with specific prompt type and language.
        
        Phase 4: Programmable thinking process - Dynamic prompt selection.
        Enhanced with Chinese language support and structured workflow.
        Supports both LangChain 0.x and 1.0+ APIs.
        """
        if LANGCHAIN_VERSION == "1.0+":
            # LangChain 1.0+ API
            from .prompts import get_chinese_templates, get_english_templates
            
            # Get appropriate system prompt based on language
            # For "scientific" type, prefer structured workflow
            if language == "zh":
                templates = get_chinese_templates()
                if prompt_type == "scientific":
                    # Prefer structured template for scientific queries
                    system_prompt = templates.get("structured", templates.get("chinese_scientific", templates["chinese"]))
                else:
                    system_prompt = templates.get(f"chinese_{prompt_type}", templates.get("chinese_scientific", templates["chinese"]))
            else:
                templates = get_english_templates()
                if prompt_type == "scientific":
                    # Prefer structured template for scientific queries
                    system_prompt = templates.get("structured", templates.get("scientific", templates["basic"]))
                else:
                    system_prompt = templates.get(prompt_type, templates.get("scientific", templates["basic"]))
            
            # Extract system prompt text from template
            if hasattr(system_prompt, 'template'):
                system_prompt_text = system_prompt.template.split("Question:")[0].strip()
            else:
                system_prompt_text = str(system_prompt)
            
            # Create agent graph (already compiled)
            agent_executor = create_agent(
                model=self.llm,
                tools=self.tools,
                system_prompt=system_prompt_text,
                checkpointer=self.memory,
                debug=True
            )
            
            # 包装 agent_executor 以修复 tool_calls 中的 args 字段
            # 某些自定义 API 端点可能返回字符串格式的 args，需要转换为字典
            from langchain_core.runnables import RunnableLambda
            
            fix_tool_calls_wrapper = _create_fix_tool_calls_wrapper(agent_executor, self.tools)
            
            # 创建包装的 Runnable
            wrapped_agent = RunnableLambda(fix_tool_calls_wrapper)
            # 复制 invoke 方法，使其行为与原始 agent_executor 一致
            wrapped_agent.invoke = fix_tool_calls_wrapper
            
            return wrapped_agent
        else:
            # LangChain 0.x API
            # Get tool names for the prompt
            tool_names = [tool.name for tool in self.tools]
            
            # Create the specific prompt template with language support
            # Use structured workflow for scientific queries
            from .prompts import get_react_prompt_template
            use_structured = (prompt_type == "scientific")
            
            prompt = get_react_prompt_template(
                prompt_type=prompt_type,
                language=language,
                structured=use_structured
            )
            
            # Create ReAct agent
            agent = create_react_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=prompt
            )
            
            # Create agent executor
            agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=True,
                memory=self.memory,
                max_iterations=10,
                early_stopping_method="generate",
                handle_parsing_errors=True,
                return_intermediate_steps=True
            )
            
            return agent_executor
    
    def search_and_store(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """
        Convenience method to search PubMed and store results in vector database.
        
        Phase 1: Basic infrastructure - End-to-end workflow.
        Enhanced with Chinese language support.
        
        Args:
            query: Search query for PubMed
            max_results: Maximum number of articles to retrieve and store
        
        Returns:
            Dictionary with operation results
        """
        try:
            logger.info(f"Searching and storing articles for: {query}")
            
            # Generate thread_id for vector database isolation
            thread_id = str(uuid.uuid4())
            self._current_thread_id = thread_id
            logger.info(f"Using thread_id for vector database isolation: {thread_id}")
            
            # Use the PubMed search tool
            pubmed_tool = next(tool for tool in self.tools if tool.name == "pubmed_search")
            search_result = pubmed_tool.run(query)
            
            # Extract PMIDs from search results (simplified approach)
            # In a real implementation, you'd parse the search results more carefully
            import re
            pmid_pattern = r'\[PMID:(\d+)\]'
            pmids = re.findall(pmid_pattern, search_result)
            
            stored_count = 0
            if pmids:
                # Store each article
                store_tool = next(tool for tool in self.tools if tool.name == "vector_store")
                for pmid in pmids[:max_results]:
                    try:
                        store_result = store_tool.run(pmid)
                        if "Successfully stored" in store_result:
                            stored_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to store article {pmid}: {e}")
            
            return {
                "query": query,
                "search_result": search_result,
                "pmids_found": len(pmids),
                "articles_stored": stored_count,
                "thread_id": thread_id,  # 添加thread_id信息
                "success": True
            }
            
        except Exception as e:
            error_msg = f"Error in search_and_store: {str(e)}"
            logger.error(error_msg)
            
            return {
                "query": query,
                "search_result": "",
                "pmids_found": 0,
                "articles_stored": 0,
                "thread_id": self._current_thread_id,  # 即使出错也记录thread_id
                "success": False,
                "error": error_msg
            }
    
    def _extract_error_details(self, error: Exception) -> Dict[str, Any]:
        """
        提取详细的错误信息，包括HTTP状态码、响应体、请求URL等。
        
        Args:
            error: 捕获的异常对象
            
        Returns:
            包含详细错误信息的字典
        """
        error_details = {
            "type": type(error).__name__,
            "message": str(error),
            "status_code": None,
            "response_body": None,
            "request_url": None,
            "details": None
        }
        
        # 尝试提取HTTP错误信息
        error_str = str(error)
        
        # 检查是否是HTTP状态错误（如404, 401等）
        if "404" in error_str or "not found" in error_str.lower():
            error_details["status_code"] = 404
            error_details["details"] = "API端点未找到。请检查：\n1. API endpoint URL是否正确（需要包含/v1路径）\n2. 服务是否正在运行\n3. 网络连接是否正常"
        elif "401" in error_str or "unauthorized" in error_str.lower():
            error_details["status_code"] = 401
            error_details["details"] = "API密钥认证失败。请检查：\n1. OPENAI_API_KEY是否正确设置\n2. API密钥是否有效\n3. 是否具有访问该服务的权限"
        elif "403" in error_str or "forbidden" in error_str.lower():
            error_details["status_code"] = 403
            error_details["details"] = "访问被拒绝。请检查API密钥是否有足够的权限"
        elif "429" in error_str or "rate limit" in error_str.lower():
            error_details["status_code"] = 429
            error_details["details"] = "API请求频率超限。请稍后重试"
        elif "connection" in error_str.lower() or "connect" in error_str.lower():
            error_details["details"] = "无法连接到API服务。请检查：\n1. 网络连接是否正常\n2. API endpoint地址是否正确\n3. 服务是否正在运行\n4. 防火墙设置是否允许连接"
        elif "timeout" in error_str.lower():
            error_details["details"] = "请求超时。请检查：\n1. 网络连接是否稳定\n2. API服务是否响应正常\n3. 可以尝试增加超时时间"
        
        # 尝试从OpenAI API错误中提取信息
        try:
            if hasattr(error, "response"):
                response = error.response
                if hasattr(response, "status_code"):
                    error_details["status_code"] = response.status_code
                if hasattr(response, "text"):
                    error_details["response_body"] = response.text
                if hasattr(response, "request"):
                    if hasattr(response.request, "url"):
                        error_details["request_url"] = str(response.request.url)
        except:
            pass
        
        # 尝试从HTTPX错误中提取信息
        try:
            if hasattr(error, "request"):
                if hasattr(error.request, "url"):
                    error_details["request_url"] = str(error.request.url)
            if hasattr(error, "response"):
                if hasattr(error.response, "status_code"):
                    error_details["status_code"] = error.response.status_code
                if hasattr(error.response, "text"):
                    error_details["response_body"] = error.response.text
        except:
            pass
        
        return error_details
    
    def _build_user_error_message(self, error_details: Dict[str, Any]) -> str:
        """
        构建用户友好的错误消息，包含诊断建议。
        
        Args:
            error_details: 错误详情字典
            
        Returns:
            用户友好的错误消息
        """
        base_msg = "抱歉，处理您的问题时遇到了错误。"
        
        # 根据错误类型提供具体的建议
        if error_details.get("status_code") == 404:
            base_msg = f"{base_msg}\n\n❌ 错误代码: 404 (未找到)\n\n"
            base_msg += "可能的原因：\n"
            base_msg += "1. API endpoint配置不正确\n"
            base_msg += "   - 请检查 OPENAI_API_BASE 环境变量或 --api-base 参数\n"
            base_msg += "   - 确保endpoint包含 /v1 路径（例如: http://localhost:8000/v1）\n"
            base_msg += "2. API服务未运行或不可访问\n"
            base_msg += "3. 网络连接问题\n\n"
            if error_details.get("request_url"):
                base_msg += f"请求的URL: {error_details['request_url']}\n"
            if error_details.get("details"):
                base_msg += f"\n详细建议：\n{error_details['details']}"
        elif error_details.get("status_code") == 401:
            base_msg = f"{base_msg}\n\n❌ 错误代码: 401 (未授权)\n\n"
            base_msg += "请检查您的API密钥是否正确设置。\n"
            if error_details.get("details"):
                base_msg += f"\n详细建议：\n{error_details['details']}"
        elif error_details.get("status_code"):
            base_msg = f"{base_msg}\n\n❌ HTTP错误代码: {error_details['status_code']}\n"
            if error_details.get("details"):
                base_msg += f"\n{error_details['details']}"
        else:
            base_msg = f"{base_msg}\n\n错误信息: {error_details.get('message', '未知错误')}\n"
            if error_details.get("details"):
                base_msg += f"\n建议：\n{error_details['details']}"
        
        # 添加通用故障排除建议
        base_msg += "\n\n💡 故障排除提示：\n"
        base_msg += "- 使用 --verbose 参数查看详细错误信息\n"
        base_msg += "- 检查 .env 文件中的配置是否正确\n"
        base_msg += "- 验证API服务是否正常运行\n"
        
        return base_msg
    
    def clear_memory(self) -> None:
        """Clear the conversation memory."""
        if HAS_OLD_MEMORY:
            self.memory.clear()
        else:
            # LangChain 1.0+ uses checkpointer, clearing is handled differently
            # For now, create a new MemorySaver instance
            if MemorySaver:
                self.memory = MemorySaver()
        logger.info("Conversation memory cleared")
    
    def get_conversation_history(self) -> List[BaseMessage]:
        """Get the conversation history."""
        if HAS_OLD_MEMORY:
            return self.memory.chat_memory.messages
        else:
            # LangChain 1.0+ uses checkpointer, history is stored differently
            # Return empty list for now as LangChain 1.0+ doesn't have direct chat_memory
            return []
    
    def get_available_tools(self) -> List[str]:
        """
        Get list of available tools.
        
        Phase 5: Extensions and MCP integration - Tool discovery.
        """
        return [tool.name for tool in self.tools]
    
    def add_custom_tool(self, tool) -> None:
        """
        Add a custom tool to the agent.
        
        Phase 5: Extensions and MCP integration - Tool extensibility.
        """
        self.tools.append(tool)
        # Recreate agent with new tools
        self.agent_executor = self._create_agent()
        logger.info(f"Added custom tool: {tool.name}")
    
    def get_agent_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the agent.
        
        Phase 5: Extensions and MCP integration - Agent monitoring.
        Enhanced with language support information.
        """
        return {
            "total_tools": len(self.tools),
            "available_tools": self.get_available_tools(),
            "llm_model": self.config.llm_model,
            "llm_base_url": self.config.llm_base_url or "default",
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "vector_db_type": self.config.vector_db_type,
            "max_iterations": 10,
            "memory_messages": len(self.get_conversation_history()),
            "language": self.language,
            "supported_languages": ["en", "zh", "auto"]
        }
    
    def set_language(self, language: str) -> None:
        """
        Set the default language for the agent.
        
        Enhanced language support method.
        """
        if language in ["en", "zh", "auto"]:
            self.language = language
            # Recreate agent with new language setting
            self.agent_executor = self._create_agent()
            logger.info(f"Language set to: {language}")
        else:
            logger.warning(f"Unsupported language: {language}. Supported: en, zh, auto")
    
    def query_multi_language(self, question: str, languages: List[str]) -> List[Dict[str, Any]]:
        """
        Query the agent in multiple languages for comparison.
        
        Enhanced multi-language support method.
        """
        results = []
        for lang in languages:
            if lang in ["en", "zh"]:
                result = self.query(question, language=lang)
                results.append(result)
            else:
                logger.warning(f"Unsupported language: {lang}")
        
        return results