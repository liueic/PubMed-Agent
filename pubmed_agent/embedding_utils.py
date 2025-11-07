"""
Embedding model initialization utilities.
支持独立供应商配置的 embedding 模型初始化工具。
"""

from typing import Optional
from langchain_openai import OpenAIEmbeddings

from .config import AgentConfig


def create_embedding_model(config: AgentConfig) -> OpenAIEmbeddings:
    """
    创建 embedding 模型实例，支持独立供应商配置。
    
    Create embedding model instance with independent provider support.
    
    Args:
        config: Agent configuration containing embedding settings
        
    Returns:
        OpenAIEmbeddings instance configured with appropriate API key and base URL
        
    配置优先级 (Configuration Priority):
    1. 如果设置了 EMBEDDING_API_KEY 和 EMBEDDING_BASE_URL，使用独立配置
    2. 否则使用 LLM 的配置（与 LLM 供应商一致）
    
    Configuration Priority:
    1. If EMBEDDING_API_KEY and EMBEDDING_BASE_URL are set, use independent config
    2. Otherwise use LLM configuration (same as LLM provider)
    """
    # 构建 embedding 初始化参数
    embedding_kwargs = {
        "model": config.embedding_model,
        "openai_api_key": config.embedding_api_key or config.llm_api_key,
    }
    
    # 如果设置了独立的 embedding base_url，则使用它
    # 否则使用 LLM 的 base_url（如果设置了）
    embedding_base_url = config.embedding_base_url or config.llm_base_url
    if embedding_base_url:
        embedding_kwargs["base_url"] = embedding_base_url
    
    return OpenAIEmbeddings(**embedding_kwargs)

