"""
Embedding model client for PubMed Agent.
支持多种嵌入模型API，包括OpenAI和阿里云DashScope。
"""

import os
import logging
from typing import List, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class EmbeddingClient:
    """
    嵌入模型客户端，支持OpenAI和DashScope API。
    """
    
    def __init__(
        self,
        model: str = "text-embedding-v4",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        dimension: Optional[int] = None
    ):
        """
        初始化嵌入模型客户端。
        
        Args:
            model: 嵌入模型名称
            api_key: API密钥，如果为None则从环境变量读取
            base_url: API基础URL，如果为None则使用默认值
            dimension: 嵌入维度，如果为None则使用模型默认值
        """
        self.model = model
        self.dimension = dimension
        
        # 确定使用哪个API
        # 如果base_url包含dashscope，使用DashScope API
        if base_url and "dashscope" in base_url.lower():
            self.api_type = "dashscope"
            self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
            self.base_url = base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
            if not self.api_key:
                raise ValueError("DASHSCOPE_API_KEY环境变量未设置")
        else:
            # 默认使用OpenAI API
            self.api_type = "openai"
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            self.base_url = base_url or "https://api.openai.com/v1"
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY环境变量未设置")
        
        # 创建OpenAI客户端（兼容两种API）
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        logger.info(f"Initialized embedding client: model={model}, api_type={self.api_type}, base_url={self.base_url}")
    
    def embed_text(self, text: str) -> List[float]:
        """
        生成单个文本的嵌入向量。
        
        Args:
            text: 要嵌入的文本
            
        Returns:
            嵌入向量列表
        """
        try:
            # 准备参数
            params = {
                "model": self.model,
                "input": text
            }
            # 只有OpenAI API支持dimensions参数，DashScope不支持
            if self.api_type == "openai" and self.dimension:
                params["dimensions"] = self.dimension
            
            response = self.client.embeddings.create(**params)
            
            # 提取嵌入向量
            if hasattr(response, 'data') and len(response.data) > 0:
                embedding = response.data[0].embedding
                return embedding
            else:
                raise ValueError("API返回的嵌入向量为空")
                
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成文本的嵌入向量。
        
        Args:
            texts: 要嵌入的文本列表
            
        Returns:
            嵌入向量列表的列表
        """
        try:
            # 准备参数
            params = {
                "model": self.model,
                "input": texts
            }
            # 只有OpenAI API支持dimensions参数，DashScope不支持
            if self.api_type == "openai" and self.dimension:
                params["dimensions"] = self.dimension
            
            response = self.client.embeddings.create(**params)
            
            # 提取所有嵌入向量
            embeddings = []
            if hasattr(response, 'data'):
                for item in response.data:
                    if hasattr(item, 'embedding'):
                        embeddings.append(item.embedding)
                    else:
                        raise ValueError("API返回的嵌入向量格式不正确")
            
            if len(embeddings) != len(texts):
                raise ValueError(f"返回的嵌入向量数量({len(embeddings)})与输入文本数量({len(texts)})不匹配")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def get_dimension(self) -> int:
        """
        获取嵌入向量的维度。
        
        Returns:
            嵌入维度
        """
        if self.dimension:
            return self.dimension
        
        # 根据模型名称返回默认维度
        if "text-embedding-v4" in self.model.lower():
            return 1536  # DashScope text-embedding-v4的默认维度
        elif "text-embedding-3" in self.model.lower():
            return 1536  # OpenAI text-embedding-3的默认维度
        elif "text-embedding-ada" in self.model.lower():
            return 1536  # OpenAI ada模型的维度
        else:
            # 默认维度
            return 1536

