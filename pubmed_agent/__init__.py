"""
ReAct PubMed Agent - An intelligent research assistant for scientific literature.
支持中文语言 / Chinese Language Support

This package provides a comprehensive implementation of a PubMed-aware agent
that uses the ReAct framework for transparent reasoning and action.

Implemented according to design plan with all 5 phases:
✅ Phase 1: Basic infrastructure
✅ Phase 2: Thought templates and logic control  
✅ Phase 3: Long text management and hallucination suppression
✅ Phase 4: Programmable thinking process
✅ Phase 5: Extensions and MCP integration

Enhanced with comprehensive Chinese language support:
🌏 Automatic language detection
🌏 Chinese ReAct prompt templates
🌏 Chinese scientific terminology
🌏 Multi-language query processing
"""

from .agent import PubMedAgent
from .tools import PubMedSearchTool, VectorDBStoreTool, VectorSearchTool
from .config import AgentConfig

# Import language support functions
from .prompts import (
    detect_language, 
    classify_query_type, 
    get_optimized_prompt,
    get_chinese_templates,
    get_english_templates
)

__version__ = "0.1.0"
__all__ = [
    "PubMedAgent", 
    "PubMedSearchTool", 
    "VectorDBStoreTool", 
    "VectorSearchTool", 
    "AgentConfig",
    # Language support functions
    "detect_language",
    "classify_query_type", 
    "get_optimized_prompt",
    "get_chinese_templates",
    "get_english_templates"
]

# Package information
__description__ = "ReAct PubMed Agent with Chinese Language Support"
__author__ = "PubMed Agent Team"
__language_support__ = ["en", "zh", "auto"]

# Quick usage guide
def quick_start(language="auto"):
    """
    Quick start function for easy usage.
    
    Args:
        language: Language setting ("en", "zh", "auto")
    
    Returns:
        Configured PubMedAgent instance
    """
    return PubMedAgent(language=language)

# Language-specific quick start functions
def create_agent_english():
    """Create agent with English language support."""
    return PubMedAgent(language="en")

def create_agent_chinese():
    """Create agent with Chinese language support."""
    return PubMedAgent(language="zh")

def create_agent_auto():
    """Create agent with automatic language detection."""
    return PubMedAgent(language="auto")