"""
Embedding model client for PubMed Agent.
支持多种嵌入模型API，包括OpenAI和阿里云DashScope。
"""

import os
import logging
import hashlib
import threading
from typing import List, Optional, Dict, Tuple
from collections import OrderedDict
from openai import OpenAI

logger = logging.getLogger(__name__)

# 模块级别的嵌入向量缓存，使用LRU策略
# 缓存key格式: (model, text_hash) -> embedding
# 使用线程锁保证线程安全
_embedding_cache: OrderedDict[Tuple[str, str], List[float]] = OrderedDict()
_embedding_cache_lock = threading.Lock()
# 默认缓存大小限制（最多缓存1000个嵌入向量）
_embedding_cache_max_size = 1000


def _get_text_hash(text: str) -> str:
    """
    计算文本的hash值，用于缓存key。
    
    Args:
        text: 文本内容
        
    Returns:
        hash字符串
    """
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _get_cached_embedding(model: str, text: str) -> Optional[List[float]]:
    """
    从缓存中获取嵌入向量。
    
    Args:
        model: 模型名称
        text: 文本内容
        
    Returns:
        嵌入向量，如果缓存中不存在则返回None
    """
    text_hash = _get_text_hash(text)
    cache_key = (model, text_hash)
    
    with _embedding_cache_lock:
        if cache_key in _embedding_cache:
            # 移动到末尾（LRU策略）
            embedding = _embedding_cache.pop(cache_key)
            _embedding_cache[cache_key] = embedding
            logger.debug(f"Cache hit for embedding: model={model}, text_hash={text_hash[:8]}...")
            return embedding
        return None


def _cache_embedding(model: str, text: str, embedding: List[float]) -> None:
    """
    将嵌入向量存入缓存。
    
    Args:
        model: 模型名称
        text: 文本内容
        embedding: 嵌入向量
    """
    text_hash = _get_text_hash(text)
    cache_key = (model, text_hash)
    
    with _embedding_cache_lock:
        # 如果缓存已满，删除最旧的项（LRU策略）
        if len(_embedding_cache) >= _embedding_cache_max_size:
            oldest_key = next(iter(_embedding_cache))
            _embedding_cache.pop(oldest_key)
            logger.debug(f"Cache full, removed oldest entry: {oldest_key[0]}")
        
        _embedding_cache[cache_key] = embedding
        logger.debug(f"Cached embedding: model={model}, text_hash={text_hash[:8]}...")


def clear_embedding_cache() -> int:
    """
    清空嵌入向量缓存。
    
    Returns:
        清空的缓存项数量
    """
    with _embedding_cache_lock:
        count = len(_embedding_cache)
        _embedding_cache.clear()
        logger.info(f"Cleared embedding cache: {count} entries removed")
        return count


def get_embedding_cache_stats() -> Dict[str, int]:
    """
    获取嵌入向量缓存的统计信息。
    
    Returns:
        包含缓存大小等统计信息的字典
    """
    with _embedding_cache_lock:
        return {
            "cache_size": len(_embedding_cache),
            "max_size": _embedding_cache_max_size
        }


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
        生成单个文本的嵌入向量，使用缓存避免重复生成。
        
        Args:
            text: 要嵌入的文本
            
        Returns:
            嵌入向量列表
        """
        # 先检查缓存
        cached_embedding = _get_cached_embedding(self.model, text)
        if cached_embedding is not None:
            return cached_embedding
        
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
                # 存入缓存
                _cache_embedding(self.model, text, embedding)
                return embedding
            else:
                raise ValueError("API返回的嵌入向量为空")
                
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成文本的嵌入向量，使用缓存避免重复生成。
        
        Args:
            texts: 要嵌入的文本列表
            
        Returns:
            嵌入向量列表的列表
        """
        if not texts:
            return []
        
        # 分离需要从缓存获取和需要API调用的文本
        cached_embeddings: Dict[int, List[float]] = {}
        texts_to_fetch: List[Tuple[int, str]] = []
        
        for idx, text in enumerate(texts):
            cached_embedding = _get_cached_embedding(self.model, text)
            if cached_embedding is not None:
                cached_embeddings[idx] = cached_embedding
            else:
                texts_to_fetch.append((idx, text))
        
        # 如果有需要从API获取的文本，批量调用API
        if texts_to_fetch:
            try:
                # 准备参数（只包含需要API调用的文本）
                texts_for_api = [text for _, text in texts_to_fetch]
                params = {
                    "model": self.model,
                    "input": texts_for_api
                }
                # 只有OpenAI API支持dimensions参数，DashScope不支持
                if self.api_type == "openai" and self.dimension:
                    params["dimensions"] = self.dimension
                
                response = self.client.embeddings.create(**params)
                
                # 提取所有嵌入向量并缓存
                api_embeddings = []
                if hasattr(response, 'data'):
                    for item in response.data:
                        if hasattr(item, 'embedding'):
                            api_embeddings.append(item.embedding)
                        else:
                            raise ValueError("API返回的嵌入向量格式不正确")
                
                if len(api_embeddings) != len(texts_for_api):
                    raise ValueError(f"返回的嵌入向量数量({len(api_embeddings)})与输入文本数量({len(texts_for_api)})不匹配")
                
                # 将API返回的嵌入向量存入缓存
                for (idx, text), embedding in zip(texts_to_fetch, api_embeddings):
                    _cache_embedding(self.model, text, embedding)
                    cached_embeddings[idx] = embedding
                
                cache_hits = len(texts) - len(texts_to_fetch)
                if cache_hits > 0:
                    logger.debug(f"Embedding cache: {cache_hits} hits, {len(texts_to_fetch)} API calls "
                               f"(hit rate: {cache_hits/len(texts)*100:.1f}%)")
            except Exception as e:
                logger.error(f"Error generating embeddings: {e}")
                raise
        
        # 按照原始顺序组合结果
        result = [cached_embeddings[i] for i in range(len(texts))]
        return result
    
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

