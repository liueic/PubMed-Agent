"""
LangChain tools for PubMed Agent.
Phase 1: Basic infrastructure - Tool system.
"""

from typing import List, Optional
from langchain.tools import BaseTool
from langchain_core.tools import tool
from .config import AgentConfig


class PubMedSearchTool(BaseTool):
    """Tool for searching PubMed articles."""
    
    name: str = "pubmed_search"
    description: str = (
        "Search PubMed for scientific articles. "
        "Input should be a search query string. "
        "Returns a list of articles with PMIDs."
    )
    
    def _run(self, query: str) -> str:
        """Execute PubMed search."""
        # Placeholder implementation
        # TODO: Implement actual PubMed search
        return f"Search results for '{query}': [PMID:12345678] Example article title"
    
    async def _arun(self, query: str) -> str:
        """Async version of PubMed search."""
        return self._run(query)


class VectorDBStoreTool(BaseTool):
    """Tool for storing articles in vector database."""
    
    name: str = "vector_store"
    description: str = (
        "Store an article in the vector database for semantic search. "
        "Input should be a PMID (PubMed ID). "
        "Returns confirmation message."
    )
    
    def _run(self, pmid: str) -> str:
        """Execute vector storage."""
        # Placeholder implementation
        # TODO: Implement actual vector storage
        return f"Successfully stored article with PMID: {pmid}"
    
    async def _arun(self, pmid: str) -> str:
        """Async version of vector storage."""
        return self._run(pmid)


class VectorSearchTool(BaseTool):
    """Tool for semantic search in vector database."""
    
    name: str = "vector_search"
    description: str = (
        "Search the vector database for semantically similar articles. "
        "Input should be a search query string. "
        "Returns relevant articles from stored database."
    )
    
    def _run(self, query: str) -> str:
        """Execute vector search."""
        # Placeholder implementation
        # TODO: Implement actual vector search
        return f"Vector search results for '{query}': Found relevant articles"
    
    async def _arun(self, query: str) -> str:
        """Async version of vector search."""
        return self._run(query)


def create_tools(config: AgentConfig) -> List[BaseTool]:
    """
    Create all tools for the agent.
    
    Args:
        config: Agent configuration
        
    Returns:
        List of tools
    """
    return [
        PubMedSearchTool(),
        VectorDBStoreTool(),
        VectorSearchTool()
    ]

