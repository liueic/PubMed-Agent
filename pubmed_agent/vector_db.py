"""
Vector database system for PubMed Agent.
支持ChromaDB和FAISS后端，使用DashScope或OpenAI嵌入模型。
"""

import logging
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

import chromadb
from chromadb.config import Settings
import numpy as np

from .embeddings import EmbeddingClient
from .config import AgentConfig

logger = logging.getLogger(__name__)


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
        
        # 初始化ChromaDB
        self.client = chromadb.PersistentClient(
            path=config.chroma_persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
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
            # 生成嵌入向量
            embeddings = self.embedding_client.embed_texts(texts)
            
            # 存储到ChromaDB
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Stored {len(texts)} documents to vector database")
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
            # 生成查询向量
            query_embedding = self.embedding_client.embed_text(query)
            
            # 执行搜索
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter_dict if filter_dict else None
            )
            
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
            
            logger.info(f"Found {len(formatted_results)} results for query: {query[:50]}...")
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

