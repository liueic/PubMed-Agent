"""
Vector database system for PubMed Agent.
支持ChromaDB和FAISS后端，使用DashScope或OpenAI嵌入模型。
"""

import logging
import threading
import time
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

import chromadb
from chromadb.config import Settings
import numpy as np

from .embeddings import EmbeddingClient
from .config import AgentConfig

logger = logging.getLogger(__name__)

# 模块级别的ChromaDB客户端缓存，按persist_directory路径缓存PersistentClient实例
# 使用线程锁保证线程安全
_chromadb_client_cache: Dict[str, chromadb.PersistentClient] = {}
_chromadb_client_cache_lock = threading.Lock()
# ChromaDB客户端缓存大小限制（通常只需要1个，但允许少量缓存以支持多路径）
_chromadb_client_cache_max_size = 10


def clear_chromadb_client_cache() -> int:
    """
    清空ChromaDB客户端缓存。
    
    Returns:
        清空的缓存项数量
    """
    with _chromadb_client_cache_lock:
        count = len(_chromadb_client_cache)
        _chromadb_client_cache.clear()
        logger.info(f"Cleared ChromaDB client cache: {count} entries removed")
        return count


def get_chromadb_client_cache_stats() -> Dict[str, int]:
    """
    获取ChromaDB客户端缓存的统计信息。
    
    Returns:
        包含缓存大小等统计信息的字典
    """
    with _chromadb_client_cache_lock:
        return {
            "cache_size": len(_chromadb_client_cache),
            "max_size": _chromadb_client_cache_max_size
        }


def _get_chromadb_client(persist_directory: str) -> chromadb.PersistentClient:
    """
    获取或创建ChromaDB PersistentClient实例，使用缓存避免重复创建。
    
    Args:
        persist_directory: ChromaDB持久化目录路径
        
    Returns:
        PersistentClient实例
    """
    with _chromadb_client_cache_lock:
        if persist_directory not in _chromadb_client_cache:
            # 如果缓存已满，删除最旧的项（简单策略：删除第一个）
            if len(_chromadb_client_cache) >= _chromadb_client_cache_max_size:
                oldest_key = next(iter(_chromadb_client_cache))
                _chromadb_client_cache.pop(oldest_key)
                logger.debug(f"ChromaDB client cache full, removed entry: {oldest_key}")
            
            logger.debug(f"Creating new ChromaDB PersistentClient for path: {persist_directory}")
            _chromadb_client_cache[persist_directory] = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )
        else:
            logger.debug(f"Reusing cached ChromaDB PersistentClient for path: {persist_directory}")
        
        return _chromadb_client_cache[persist_directory]


def normalize_collection_name(thread_id: str) -> str:
    """
    规范化collection名称，确保符合ChromaDB命名规范。
    
    Args:
        thread_id: 线程ID或对话ID
        
    Returns:
        规范化后的collection名称
    """
    import re
    # 移除或替换特殊字符，只保留字母、数字、下划线和连字符
    # ChromaDB collection名称应该只包含字母、数字、下划线和连字符
    normalized = re.sub(r'[^a-zA-Z0-9_-]', '_', str(thread_id))
    # 确保不以数字开头（避免某些数据库限制）
    if normalized and normalized[0].isdigit():
        normalized = f"thread_{normalized}"
    # 确保长度合理
    if len(normalized) > 100:
        normalized = normalized[:100]
    return normalized


def get_collection_name(thread_id: Optional[str] = None) -> str:
    """
    获取collection名称。
    
    Args:
        thread_id: 线程ID，如果为None则返回默认名称
        
    Returns:
        Collection名称
    """
    if thread_id is None:
        return "pubmed_articles"
    normalized_thread_id = normalize_collection_name(thread_id)
    return f"pubmed_articles_{normalized_thread_id}"


class VectorDB(ABC):
    """向量数据库抽象接口"""
    
    @abstractmethod
    def store(self, texts: List[str], metadatas: List[Dict[str, Any]], ids: List[str]) -> bool:
        """存储文本和元数据"""
        pass
    
    @abstractmethod
    def search(self, query: str, n_results: int = 10, filter_dict: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """语义搜索"""
        pass
    
    @abstractmethod
    def delete(self, ids: List[str]) -> bool:
        """删除文档"""
        pass


class ChromaVectorDB(VectorDB):
    """ChromaDB向量数据库实现"""
    
    def __init__(self, config: AgentConfig, collection_name: Optional[str] = None):
        """
        初始化ChromaDB向量数据库。
        
        Args:
            config: Agent配置对象
            collection_name: Collection名称，如果为None则使用默认名称"pubmed_articles"
        """
        self.config = config
        
        # 初始化嵌入客户端
        embedding_api_base = config.embedding_api_base
        embedding_api_key = None
        
        if embedding_api_base is None:
            # 如果未指定，根据模型名称或配置自动选择
            if config.dashscope_api_key:
                # 优先使用DashScope API（如果提供了DashScope API Key）
                embedding_api_base = "https://dashscope.aliyuncs.com/compatible-mode/v1"
                embedding_api_key = config.dashscope_api_key
            elif "dashscope" in config.embedding_model.lower() or "text-embedding-v4" in config.embedding_model.lower():
                # 如果模型名称包含dashscope或v4，使用DashScope API
                embedding_api_base = "https://dashscope.aliyuncs.com/compatible-mode/v1"
                embedding_api_key = config.dashscope_api_key or config.openai_api_key
            else:
                # 使用OpenAI API
                embedding_api_base = None  # 使用默认OpenAI endpoint
                embedding_api_key = config.openai_api_key
        else:
            # 如果指定了embedding_api_base，根据base_url判断使用哪个API key
            if "dashscope" in embedding_api_base.lower():
                embedding_api_key = config.dashscope_api_key or config.openai_api_key
            else:
                embedding_api_key = config.openai_api_key
        
        self.embedding_client = EmbeddingClient(
            model=config.embedding_model,
            api_key=embedding_api_key,
            base_url=embedding_api_base,
            dimension=config.embedding_dimension
        )
        
        # 使用缓存的ChromaDB客户端，避免重复创建
        self.client = _get_chromadb_client(config.chroma_persist_directory)
        
        # 确定collection名称，默认使用"pubmed_articles"（向后兼容）
        if collection_name is None:
            collection_name = "pubmed_articles"
        
        # 创建或获取集合
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
        )
        
        logger.info(f"Initialized ChromaDB vector database at {config.chroma_persist_directory} with collection: {collection_name}")
    
    def store(self, texts: List[str], metadatas: List[Dict[str, Any]], ids: List[str]) -> bool:
        """
        存储文本和元数据到向量数据库。
        
        Args:
            texts: 文本列表
            metadatas: 元数据列表
            ids: 文档ID列表
            
        Returns:
            是否成功
        """
        try:
            start_time = time.time()
            
            # 生成嵌入向量（批量处理，已优化）
            embedding_start = time.time()
            embeddings = self.embedding_client.embed_texts(texts)
            embedding_time = time.time() - embedding_start
            
            # 存储到ChromaDB
            storage_start = time.time()
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            storage_time = time.time() - storage_start
            total_time = time.time() - start_time
            
            logger.info(f"Stored {len(texts)} documents to vector database "
                      f"(embedding: {embedding_time:.2f}s, storage: {storage_time:.2f}s, total: {total_time:.2f}s)")
            return True
            
        except Exception as e:
            logger.error(f"Error storing documents: {e}")
            return False
    
    def search(self, query: str, n_results: int = 10, filter_dict: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        语义搜索。
        
        Args:
            query: 查询文本
            n_results: 返回结果数量
            filter_dict: 过滤条件
            
        Returns:
            搜索结果列表，每个结果包含文档、元数据和相似度分数
        """
        try:
            start_time = time.time()
            
            # 生成查询向量
            embedding_start = time.time()
            query_embedding = self.embedding_client.embed_text(query)
            embedding_time = time.time() - embedding_start
            
            # 执行搜索
            search_start = time.time()
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter_dict if filter_dict else None
            )
            search_time = time.time() - search_start
            
            # 格式化结果
            formatted_results = []
            if results['documents'] and len(results['documents']) > 0:
                documents = results['documents'][0]
                metadatas = results['metadatas'][0] if results['metadatas'] else [{}] * len(documents)
                distances = results['distances'][0] if results['distances'] else [0.0] * len(documents)
                ids = results['ids'][0] if results['ids'] else [None] * len(documents)
                
                for doc, metadata, distance, doc_id in zip(documents, metadatas, distances, ids):
                    formatted_results.append({
                        'document': doc,
                        'metadata': metadata,
                        'distance': distance,
                        'id': doc_id,
                        'score': 1 - distance  # 将距离转换为相似度分数（余弦距离）
                    })
            
            total_time = time.time() - start_time
            logger.info(f"Found {len(formatted_results)} results for query: {query[:50]}... "
                      f"(embedding: {embedding_time:.2f}s, search: {search_time:.2f}s, total: {total_time:.2f}s)")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching vector database: {e}")
            return []
    
    def delete(self, ids: List[str]) -> bool:
        """
        删除文档。
        
        Args:
            ids: 要删除的文档ID列表
            
        Returns:
            是否成功
        """
        try:
            self.collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} documents from vector database")
            return True
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            return False


def create_vector_db(config: AgentConfig, collection_name: Optional[str] = None) -> VectorDB:
    """
    创建向量数据库实例。
    
    Args:
        config: Agent配置对象
        collection_name: Collection名称，如果为None则使用默认名称"pubmed_articles"
        
    Returns:
        向量数据库实例
    """
    if config.vector_db_type == "chroma":
        return ChromaVectorDB(config, collection_name=collection_name)
    else:
        raise ValueError(f"Unsupported vector database type: {config.vector_db_type}")

