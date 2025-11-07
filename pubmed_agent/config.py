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
        
        # LLM 配置 - 支持多种大模型供应商
        # 优先使用通用配置，如果没有则使用 OpenAI 特定配置（向后兼容）
        env_values["llm_api_key"] = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        env_values["llm_base_url"] = os.getenv("LLM_BASE_URL")  # 如果为空则使用默认 OpenAI URL
        env_values["llm_model"] = os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL", "gpt-4o")
        
        # 向后兼容：保留 openai_ 前缀的配置
        env_values["openai_api_key"] = env_values["llm_api_key"]
        env_values["openai_model"] = env_values["llm_model"]
        
        # LLM 推理参数
        env_values["temperature"] = float(os.getenv("TEMPERATURE", "0.7"))
        env_values["top_p"] = float(os.getenv("TOP_P", "0.95"))
        
        # 向量数据库配置
        env_values["vector_db_type"] = os.getenv("VECTOR_DB_TYPE", "chroma")
        env_values["chroma_persist_directory"] = os.getenv("CHROMA_PERSIST_DIRECTORY", "./data/chroma")
        env_values["faiss_index_path"] = os.getenv("FAISS_INDEX_PATH", "./data/faiss.index")
        
        # PubMed API 配置
        env_values["pubmed_email"] = os.getenv("PUBMED_EMAIL")
        env_values["pubmed_tool_name"] = os.getenv("PUBMED_TOOL_NAME", "pubmed_agent")
        env_values["pubmed_api_key"] = os.getenv("PUBMED_API_KEY")
        
        # 嵌入模型配置 - 支持独立供应商
        # 如果用户填写了独立的 embedding 配置，则使用用户的配置
        # 否则默认使用 LLM 的配置（与 LLM 供应商一致）
        embedding_api_key = os.getenv("EMBEDDING_API_KEY")
        embedding_base_url = os.getenv("EMBEDDING_BASE_URL")
        
        # 如果用户未填写独立的 embedding 配置，则使用 LLM 配置
        if not embedding_api_key:
            embedding_api_key = env_values.get("llm_api_key")
        if not embedding_base_url:
            embedding_base_url = env_values.get("llm_base_url")
        
        env_values["embedding_api_key"] = embedding_api_key
        env_values["embedding_base_url"] = embedding_base_url
        env_values["embedding_model"] = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        env_values["embedding_dimension"] = int(os.getenv("EMBEDDING_DIMENSION", "1536"))
        
        # 检索和分块配置
        env_values["max_retrieve_results"] = int(os.getenv("MAX_RETRIEVE_RESULTS", "10"))
        env_values["chunk_size"] = int(os.getenv("CHUNK_SIZE", "1000"))
        env_values["chunk_overlap"] = int(os.getenv("CHUNK_OVERLAP", "200"))
        
        # 日志配置
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
    # LLM 配置 - 支持多种大模型供应商
    llm_api_key: str = ""  # 通用 API Key，支持 OpenAI、Azure、Anthropic、本地模型等
    llm_base_url: Optional[str] = None  # 自定义 Base URL，为空时使用默认 OpenAI URL
    llm_model: str = "gpt-4o"  # 模型名称，用户可自由填写
    
    # 向后兼容：保留 openai_ 前缀
    openai_api_key: str = ""
    openai_api_base: Optional[str] = None  # 自定义API endpoint，None表示使用默认OpenAI API
    openai_model: str = "gpt-4o"
    
    # LLM 推理参数
    temperature: float = 0.7  # 默认 0.7，适合大多数模型
    top_p: float = 0.95  # 默认 0.95，适合大多数模型
    
    # 向量数据库配置
    vector_db_type: str = "chroma"
    chroma_persist_directory: str = "./data/chroma"
    faiss_index_path: str = "./data/faiss.index"
    
    # PubMed API 配置
    pubmed_email: Optional[str] = None
    pubmed_tool_name: str = "pubmed_agent"
    pubmed_api_key: Optional[str] = None
    
    # 嵌入模型配置 - 支持独立供应商
    embedding_api_key: Optional[str] = None  # 如果为空，则使用 LLM API Key
    embedding_base_url: Optional[str] = None  # 如果为空，则使用 LLM Base URL
    embedding_model: str = "text-embedding-3-small"  # 模型名称，用户可自由填写
    embedding_dimension: int = 1536  # 嵌入向量维度
    
    # 检索和分块配置
    max_retrieve_results: int = 10
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    # 日志配置
    log_level: str = "INFO"
