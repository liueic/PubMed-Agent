"""
Configuration management for the PubMed Agent.
Phase 1: Basic infrastructure - Configuration system with environment variable support.
"""

import os
from typing import Optional
from pydantic import BaseModel

# Auto-load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    # Load .env file from project root
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        # Also try loading from current directory
        load_dotenv()
except ImportError:
    # python-dotenv not installed, skip auto-loading
    pass


class AgentConfig(BaseModel):
    """
    Configuration settings for PubMed Agent.
    
    This configuration system supports:
    - Environment variable loading
    - Default values for all settings
    - Runtime configuration override
    - Automatic directory creation
    """
    
    def __init__(self, **kwargs):
        # Load from environment variables first
        env_values = {}
        env_values["openai_api_key"] = os.getenv("OPENAI_API_KEY")
        env_values["openai_api_base"] = os.getenv("OPENAI_API_BASE")  # 支持自定义endpoint
        env_values["openai_model"] = os.getenv("OPENAI_MODEL", "gpt-4o")
        env_values["vector_db_type"] = os.getenv("VECTOR_DB_TYPE", "chroma")
        env_values["chroma_persist_directory"] = os.getenv("CHROMA_PERSIST_DIRECTORY", "./data/chroma")
        env_values["faiss_index_path"] = os.getenv("FAISS_INDEX_PATH", "./data/faiss.index")
        env_values["pubmed_email"] = os.getenv("PUBMED_EMAIL")
        env_values["pubmed_tool_name"] = os.getenv("PUBMED_TOOL_NAME", "pubmed_agent")
        env_values["pubmed_api_key"] = os.getenv("PUBMED_API_KEY")
        env_values["embedding_model"] = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        env_values["embedding_dimension"] = int(os.getenv("EMBEDDING_DIMENSION", "1536"))
        env_values["max_retrieve_results"] = int(os.getenv("MAX_RETRIEVE_RESULTS", "10"))
        env_values["chunk_size"] = int(os.getenv("CHUNK_SIZE", "1000"))
        env_values["chunk_overlap"] = int(os.getenv("CHUNK_OVERLAP", "200"))
        env_values["temperature"] = float(os.getenv("TEMPERATURE", "0.0"))
        env_values["log_level"] = os.getenv("LOG_LEVEL", "INFO")
        
        # Override with explicit kwargs
        env_values.update(kwargs)
        
        super().__init__(**env_values)
        
        # Create data directories if they don't exist
        os.makedirs(self.chroma_persist_directory, exist_ok=True)
        os.makedirs(os.path.dirname(self.faiss_index_path), exist_ok=True)
    
    # Runtime attributes (declared for Pydantic)
    openai_api_key: str = ""
    openai_api_base: Optional[str] = None  # 自定义API endpoint，None表示使用默认OpenAI API
    openai_model: str = "gpt-4o"
    vector_db_type: str = "chroma"
    chroma_persist_directory: str = "./data/chroma"
    faiss_index_path: str = "./data/faiss.index"
    pubmed_email: Optional[str] = None
    pubmed_tool_name: str = "pubmed_agent"
    pubmed_api_key: Optional[str] = None
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    max_retrieve_results: int = 10
    chunk_size: int = 1000
    chunk_overlap: int = 200
    temperature: float = 0.0
    log_level: str = "INFO"