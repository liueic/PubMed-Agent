"""
ReAct PubMed Agent - An intelligent research assistant for scientific literature.

This package provides a comprehensive implementation of a PubMed-aware agent
that uses the ReAct framework for transparent reasoning and action.

Implemented according to design plan with all 5 phases:
✅ Phase 1: Basic infrastructure
✅ Phase 2: Thought templates and logic control  
✅ Phase 3: Long text management and hallucination suppression
✅ Phase 4: Programmable thinking process
✅ Phase 5: Extensions and MCP integration
"""

from .agent import PubMedAgent
from .tools import PubMedSearchTool, VectorDBStoreTool, VectorSearchTool
from .config import AgentConfig

__version__ = "0.1.0"
__all__ = ["PubMedAgent", "PubMedSearchTool", "VectorDBStoreTool", "VectorSearchTool", "AgentConfig"]