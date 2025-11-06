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
        env_values["embedding_model"] = os.getenv("EMBEDDING_MODEL", "text-embedding-v4")
        env_values["embedding_dimension"] = int(os.getenv("EMBEDDING_DIMENSION", "1536"))
        env_values["dashscope_api_key"] = os.getenv("DASHSCOPE_API_KEY")
        env_values["embedding_api_base"] = os.getenv("EMBEDDING_API_BASE")  # 支持自定义嵌入API endpoint
        env_values["max_retrieve_results"] = int(os.getenv("MAX_RETRIEVE_RESULTS", "10"))
        env_values["chunk_size"] = int(os.getenv("CHUNK_SIZE", "1000"))
        env_values["chunk_overlap"] = int(os.getenv("CHUNK_OVERLAP", "200"))
        env_values["temperature"] = float(os.getenv("TEMPERATURE", "0.0"))
        env_values["log_level"] = os.getenv("LOG_LEVEL", "INFO")
        env_values["log_file"] = os.getenv("LOG_FILE")  # 可选，如果未设置则为None
        
        # Override with explicit kwargs
        env_values.update(kwargs)
        
        # 验证和规范化API base URL
        # 注意：对于某些服务（如阿里云DashScope），URL已经包含完整路径，不应修改
        if env_values.get("openai_api_base"):
            api_base = env_values["openai_api_base"].rstrip("/")
            
            # 检查URL是否已经包含/v1路径（可能在末尾或中间）
            from urllib.parse import urlparse
            parsed = urlparse(api_base)
            path = parsed.path
            
            # 如果路径中已经包含/v1，保持原样（不修改）
            # 这样可以支持：
            # - http://localhost:8000/v1
            # - https://dashscope.aliyuncs.com/compatible-mode/v1
            # - https://api.example.com/v1/chat (即使路径更长也保持原样)
            if path and "/v1" in path:
                # URL已经包含/v1路径，保持原样
                pass
            else:
                # 如果路径中没有/v1，且不是以/v1结尾，才添加/v1
                # 这是为了支持简单的base URL（如 http://localhost:8000）
                if not api_base.endswith("/v1"):
                    api_base = f"{api_base}/v1"
            
            env_values["openai_api_base"] = api_base
        
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
    embedding_model: str = "text-embedding-v4"
    embedding_dimension: Optional[int] = 1536
    dashscope_api_key: Optional[str] = None
    embedding_api_base: Optional[str] = None  # 嵌入API base URL，如果为None则根据模型自动选择
    max_retrieve_results: int = 10
    chunk_size: int = 1000
    chunk_overlap: int = 200
    temperature: float = 0.0
    log_level: str = "INFO"
    log_file: Optional[str] = None  # 日志文件路径，如果为None则不写入文件