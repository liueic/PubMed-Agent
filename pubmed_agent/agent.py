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
                # 尝试从错误信息中提取tool_calls数据并修复
                import re
                # 查找所有tool_calls的args字符串
                matches = re.findall(r"input_value='([^']+)'", error_str)
                if matches:
                    logger.info(f"Found {len(matches)} tool_call args in error message, attempting to fix...")
                    # 尝试重新调用，但这次在LLM层面修复
                    # 由于我们无法直接修改已经验证失败的消息，我们需要在下一轮修复
                    # 但首先，让我们尝试修复输入，然后重试
                    result = agent_executor.invoke(input_dict, config=config if config is not None else {})
                else:
                    # 如果无法提取，重新抛出错误
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
                                    # vector_store工具接受字符串参数（PMID），保持原样
                                    pass
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
                                    # 如果工具期望单个参数，提取第一个值
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
                    
                    # 继续执行agent，传入工具执行结果
                    continue_result = agent_executor.invoke(
                        {"messages": result["messages"]},
                        config=config if config is not None else {}
                    )
                    # 更新结果并修复消息
                    if isinstance(continue_result, dict) and "messages" in continue_result:
                        # 修复返回的消息中的 tool_calls
                        result["messages"] = _fix_messages_tool_calls(continue_result["messages"])
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
        
        # Thread ID management for vector database isolation
        self._current_thread_id: Optional[str] = None
        self._thread_id_getter: Optional[Callable[[], Optional[str]]] = None
        
        # Initialize LLM with controlled temperature for factual responses
        # Support custom API endpoint for compatibility with OpenAI-compatible APIs
        llm_kwargs = {
            "model": self.config.openai_model,
            "temperature": self.config.temperature,  # Phase 2: Temperature control for reduced hallucinations
            "openai_api_key": self.config.openai_api_key
        }
        
        # Add custom base_url if provided (for custom endpoints like local models, Azure, etc.)
        if self.config.openai_api_base:
            llm_kwargs["base_url"] = self.config.openai_api_base
            logger.info(f"Using custom API endpoint: {self.config.openai_api_base}")
        else:
            logger.info("Using default OpenAI API endpoint")
        
        # 记录实际使用的完整API配置
        logger.info(f"API Configuration - Model: {self.config.openai_model}, Endpoint: {llm_kwargs.get('base_url', 'default OpenAI API')}")
        
        # 创建基础LLM
        base_llm = ChatOpenAI(**llm_kwargs)
        
        # 创建包装类以修复tool_calls（使用组合而不是继承）
        class FixedChatOpenAI:
            """包装ChatOpenAI以自动修复tool_calls中的args"""
            
            def __init__(self, base_llm_instance):
                self._base_llm = base_llm_instance
            
            def _fix_response_before_validation(self, response_data):
                """
                在Pydantic验证之前修复响应数据。
                尝试从原始响应数据中修复tool_calls的args字段。
                """
                try:
                    # 如果response_data是字典（可能是原始API响应），尝试修复
                    if isinstance(response_data, dict):
                        # 检查是否有tool_calls字段
                        if 'tool_calls' in response_data:
                            tool_calls = response_data['tool_calls']
                            if isinstance(tool_calls, list):
                                fixed_tool_calls = []
                                for tc in tool_calls:
                                    if isinstance(tc, dict) and 'args' in tc:
                                        if isinstance(tc['args'], str):
                                            parsed = _recursive_parse_json(tc['args'])
                                            if isinstance(parsed, dict):
                                                tc['args'] = parsed
                                                fixed_tool_calls.append(tc)
                                            else:
                                                fixed_tool_calls.append(tc)
                                        else:
                                            fixed_tool_calls.append(tc)
                                    else:
                                        fixed_tool_calls.append(tc)
                                response_data['tool_calls'] = fixed_tool_calls
                        # 检查choices字段（OpenAI格式）
                        if 'choices' in response_data:
                            for choice in response_data.get('choices', []):
                                if 'message' in choice:
                                    message = choice['message']
                                    if 'tool_calls' in message:
                                        tool_calls = message['tool_calls']
                                        if isinstance(tool_calls, list):
                                            fixed_tool_calls = []
                                            for tc in tool_calls:
                                                if isinstance(tc, dict) and 'function' in tc:
                                                    func = tc['function']
                                                    if isinstance(func, dict) and 'arguments' in func:
                                                        if isinstance(func['arguments'], str):
                                                            parsed = _recursive_parse_json(func['arguments'])
                                                            if isinstance(parsed, dict):
                                                                func['arguments'] = parsed
                                                            fixed_tool_calls.append(tc)
                                                        else:
                                                            fixed_tool_calls.append(tc)
                                                    else:
                                                        fixed_tool_calls.append(tc)
                                                else:
                                                    fixed_tool_calls.append(tc)
                                            message['tool_calls'] = fixed_tool_calls
                except Exception as e:
                    logger.warning(f"Error fixing response before validation: {e}")
                return response_data
            
            def invoke(self, input, config=None, **kwargs):
                """调用LLM并修复返回的消息"""
                try:
                    result = self._base_llm.invoke(input, config=config, **kwargs)
                    return _fix_tool_calls_args(result)
                except Exception as e:
                    # 如果验证失败，尝试从错误中提取信息并修复
                    error_str = str(e)
                    if "tool_calls" in error_str and ("dict_type" in error_str or "Input should be a valid dictionary" in error_str):
                        logger.warning(f"Caught validation error for tool_calls, attempting to fix: {e}")
                        # 尝试从原始响应中修复
                        try:
                            # 检查base_llm是否有_client属性，如果有，我们可以尝试直接调用API
                            if hasattr(self._base_llm, '_client'):
                                # 尝试使用原始客户端调用，然后在响应中修复
                                import inspect
                                # 获取调用的原始参数
                                # 这里我们需要手动构造消息并调用API
                                pass
                            
                            # 如果无法从底层修复，尝试使用LangChain的fallback机制
                            # 创建一个修复后的消息对象
                            from langchain_core.messages import AIMessage
                            from langchain_core.exceptions import OutputParserException
                            
                            # 尝试从错误信息中提取tool_calls数据
                            # 错误信息格式: Input should be a valid dictionary [type=dict_type, input_value='{"query": "..."}', input_type=str]
                            import re
                            match = re.search(r"input_value='([^']+)'", error_str)
                            if match:
                                args_str = match.group(1)
                                # 尝试解析args字符串
                                parsed_args = _recursive_parse_json(args_str)
                                if isinstance(parsed_args, dict):
                                    logger.info(f"Successfully parsed args from error message: {list(parsed_args.keys())}")
                                    # 这里我们需要重新构造消息，但我们需要完整的tool_call信息
                                    # 由于信息不完整，我们只能记录并重试
                                    pass
                            
                            # 如果所有修复尝试都失败，重新调用（可能会再次失败，但至少尝试了）
                            logger.warning("Retrying LLM call after validation error...")
                            result = self._base_llm.invoke(input, config=config, **kwargs)
                            return _fix_tool_calls_args(result)
                        except Exception as inner_e:
                            logger.error(f"Failed to fix validation error: {inner_e}")
                            # 如果修复失败，抛出原始错误
                            raise e
                    raise
            
            def batch(self, inputs, config=None, **kwargs):
                """批量调用LLM并修复返回的消息"""
                try:
                    results = self._base_llm.batch(inputs, config=config, **kwargs)
                    return [_fix_tool_calls_args(msg) for msg in results]
                except Exception as e:
                    logger.warning(f"Error in batch call: {e}")
                    # 尝试修复后重新调用
                    results = self._base_llm.batch(inputs, config=config, **kwargs)
                    return [_fix_tool_calls_args(msg) for msg in results]
            
            def stream(self, input, config=None, **kwargs):
                """流式调用LLM并修复返回的消息"""
                try:
                    for chunk in self._base_llm.stream(input, config=config, **kwargs):
                        yield _fix_tool_calls_args(chunk)
                except Exception as e:
                    logger.warning(f"Error in stream call: {e}")
                    for chunk in self._base_llm.stream(input, config=config, **kwargs):
                        yield _fix_tool_calls_args(chunk)
            
            # 代理所有其他方法和属性到base_llm
            def __getattr__(self, name):
                """代理未定义的属性和方法到base_llm"""
                attr = getattr(self._base_llm, name)
                if callable(attr):
                    # 如果是方法，包装它以确保返回的消息也被修复
                    def wrapper(*args, **kwargs):
                        try:
                            result = attr(*args, **kwargs)
                            # 如果结果是消息对象，修复它
                            if hasattr(result, 'tool_calls'):
                                return _fix_tool_calls_args(result)
                            return result
                        except Exception as e:
                            # 如果调用失败且是验证错误，尝试修复
                            error_str = str(e)
                            if "tool_calls" in error_str:
                                logger.warning(f"Error in {name}, attempting fix: {e}")
                                raise
                            raise
                    return wrapper
                return attr
        
        # 使用包装的LLM
        self.llm = FixedChatOpenAI(base_llm)
        
        # Initialize tools with thread_id_getter (will be set up in _create_agent)
        # 先创建thread_id_getter函数
        def get_thread_id():
            """获取当前thread_id"""
            return self._current_thread_id
        
        self._thread_id_getter = get_thread_id
        
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
        Enhanced with Chinese language support.
        Supports both LangChain 0.x and 1.0+ APIs.
        """
        if LANGCHAIN_VERSION == "1.0+":
            # LangChain 1.0+ API - use create_agent which returns a graph
            from .prompts import get_chinese_templates, get_english_templates
            
            # Get appropriate system prompt based on language
            if self.language == "zh":
                templates = get_chinese_templates()
                system_prompt = templates.get("chinese_scientific", templates["chinese"])
            else:
                templates = get_english_templates()
                system_prompt = templates.get("scientific", templates["basic"])
            
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
            
            # Create the base prompt template with language optimization
            prompt = get_optimized_prompt("", language=self.language)
            
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
    
    def query(self, question: str, prompt_type: Optional[str] = None, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Query the agent with a scientific question.
        
        Phase 4: Programmable thinking process - Query-aware prompt selection.
        Enhanced with Chinese language support.
        
        Args:
            question: The scientific question to answer
            prompt_type: Optional prompt type override. If None, auto-classifies.
            language: Language override ("en", "zh"). If None, uses instance default.
        
        Returns:
            Dictionary containing the answer and metadata
        """
        try:
            logger.info(f"Processing query: {question}")
            
            # Generate or get thread_id for vector database isolation
            # 对于LangChain 1.0+，可以从config中获取thread_id；否则生成新的UUID
            if LANGCHAIN_VERSION == "1.0+":
                # 在LangChain 1.0+中，每个query都会生成新的thread_id
                # 使用UUID生成唯一的thread_id
                thread_id = str(uuid.uuid4())
            else:
                # LangChain 0.x中，如果没有指定thread_id，生成新的UUID
                thread_id = str(uuid.uuid4())
            
            # 设置当前thread_id，工具会通过thread_id_getter获取
            self._current_thread_id = thread_id
            logger.info(f"Using thread_id for vector database isolation: {thread_id}")
            
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
                    # 使用生成的thread_id，而不是"default"
                    config = {"configurable": {"thread_id": thread_id}}
                
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
                "thread_id": thread_id,  # 添加thread_id信息
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
        Enhanced with Chinese language support.
        Supports both LangChain 0.x and 1.0+ APIs.
        """
        if LANGCHAIN_VERSION == "1.0+":
            # LangChain 1.0+ API
            from .prompts import get_chinese_templates, get_english_templates
            
            # Get appropriate system prompt based on language
            if language == "zh":
                templates = get_chinese_templates()
                system_prompt = templates.get(f"chinese_{prompt_type}", templates.get("chinese_scientific", templates["chinese"]))
            else:
                templates = get_english_templates()
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
            if language == "zh":
                from .prompts import get_chinese_templates
                templates = get_chinese_templates()
                template_key = f"chinese_{prompt_type}"
            else:
                from .prompts import get_english_templates
                templates = get_english_templates()
                template_key = prompt_type
            
            template = templates.get(template_key, templates["scientific"])
            
            # Create ReAct agent
            agent = create_react_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=template
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
            "llm_model": self.config.openai_model,
            "temperature": self.config.temperature,
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