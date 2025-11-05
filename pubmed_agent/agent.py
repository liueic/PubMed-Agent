"""
Main ReAct PubMed Agent implementation.
Phase 1: Basic infrastructure - Core agent system.
Phase 2: Thought templates and logic control - Enhanced reasoning.
Phase 4: Programmable thinking process - Query-aware prompt selection.
Phase 5: Extensions and MCP integration - Extensible architecture.
Enhanced with comprehensive Chinese language support.
"""

import logging
from typing import List, Dict, Any, Optional

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
        
        self.llm = ChatOpenAI(**llm_kwargs)
        
        # Initialize tools
        self.tools = create_tools(self.config)
        
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
            
            return agent_executor
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
                    config = {"configurable": {"thread_id": "default"}}
                
                # Invoke with messages format
                result = self.agent_executor.invoke(
                    {"messages": [HumanMessage(content=question)]},
                    config=config if config else None
                )
                
                # Extract output from LangChain 1.0+ response format
                # Result is a dict with "messages" key containing message objects
                if isinstance(result, dict) and "messages" in result:
                    messages = result["messages"]
                    # Get the last assistant message
                    assistant_messages = [msg for msg in messages if hasattr(msg, 'content') and msg.type == "ai"]
                    if assistant_messages:
                        output = assistant_messages[-1].content
                    else:
                        output = str(result)
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
                "success": True
            }
            
            logger.info(f"Query completed successfully for: {question}")
            return response
            
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            logger.error(error_msg)
            
            return {
                "question": question,
                "answer": f"I apologize, but I encountered an error while processing your question: {error_msg}",
                "intermediate_steps": [],
                "prompt_type": prompt_type or "scientific",
                "language": language or self.language,
                "success": False,
                "error": str(e)
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
            
            return agent_executor
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
                "success": False,
                "error": error_msg
            }
    
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