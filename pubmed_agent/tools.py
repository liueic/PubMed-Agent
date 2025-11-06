"""
LangChain tools for PubMed Agent.
Phase 1: Basic infrastructure - Tool system.
"""

import logging
from typing import List, Optional
from langchain.tools import BaseTool
from langchain_core.tools import tool
from .config import AgentConfig
from .vector_db import create_vector_db
from .utils import chunk_text, PubMedRateLimiter, parse_pubmed_date

logger = logging.getLogger(__name__)


class PubMedSearchTool(BaseTool):
    """Tool for searching PubMed articles."""
    
    name: str = "pubmed_search"
    description: str = (
        "Search PubMed for scientific articles. "
        "Input should be a search query string. "
        "Returns a list of articles with PMIDs."
    )
    
    # 使用类级别的变量存储配置和速率限制器
    _config: Optional[AgentConfig] = None
    _rate_limiter = None
    
    def __init__(self, config: Optional[AgentConfig] = None, **kwargs):
        """Initialize the PubMed search tool."""
        super().__init__(**kwargs)
        # 使用私有属性存储，避免Pydantic验证错误
        object.__setattr__(self, '_config', config or AgentConfig())
        object.__setattr__(self, '_rate_limiter', PubMedRateLimiter(requests_per_second=3.0))
    
    @property
    def config(self) -> AgentConfig:
        """Get the configuration."""
        return self._config
    
    def _run(self, query: str) -> str:
        """Execute PubMed search."""
        try:
            # 导入 Bio.Entrez（延迟导入，避免在模块级别导入）
            try:
                from Bio import Entrez
                from xml.etree import ElementTree as ET
            except ImportError:
                logger.error("Bio.Entrez is not available. Please install biopython: pip install biopython")
                return f"Error: biopython is required for PubMed search. Please install it: pip install biopython"
            
            # 设置 NCBI Entrez 参数
            if self.config.pubmed_email:
                Entrez.email = self.config.pubmed_email
            else:
                # NCBI 要求提供 email，如果未配置则使用默认值
                Entrez.email = "pubmed_agent@example.com"
            
            if self.config.pubmed_tool_name:
                Entrez.tool = self.config.pubmed_tool_name
            
            if self.config.pubmed_api_key:
                Entrez.api_key = self.config.pubmed_api_key
            
            # 使用速率限制器
            self._rate_limiter.wait_if_needed()
            
            # 搜索 PubMed
            logger.info(f"Searching PubMed for: {query}")
            search_handle = Entrez.esearch(
                db="pubmed",
                term=query,
                retmax=20  # 默认返回 20 篇文章
            )
            search_results = Entrez.read(search_handle)
            search_handle.close()
            
            # 获取 PMID 列表
            pmids = search_results.get("IdList", [])
            
            if not pmids:
                return f"No articles found for query: {query}"
            
            logger.info(f"Found {len(pmids)} articles, fetching details...")
            
            # 使用速率限制器
            self._rate_limiter.wait_if_needed()
            
            # 批量获取文章详情
            pmid_string = ",".join(pmids)
            fetch_handle = Entrez.efetch(
                db="pubmed",
                id=pmid_string,
                rettype="abstract",
                retmode="xml"
            )
            
            # 解析 XML（efetch 返回的是 XML 格式）
            try:
                # 读取 XML 内容
                xml_data = fetch_handle.read()
                fetch_handle.close()
                
                # 解析 XML
                root = ET.fromstring(xml_data)
            except ET.ParseError as e:
                logger.error(f"Error parsing XML: {e}")
                # 如果 XML 解析失败，尝试返回基本 PMID 信息
                return f"Found {len(pmids)} article(s) for query: {query}\n" + "\n".join([f"[PMID:{pmid}]" for pmid in pmids[:10]])
            
            # 提取文章信息
            articles = []
            for article in root.findall(".//PubmedArticle"):
                try:
                    # 提取 PMID
                    pmid_elem = article.find(".//PMID")
                    pmid = pmid_elem.text if pmid_elem is not None else "Unknown"
                    
                    # 提取标题
                    title_elem = article.find(".//ArticleTitle")
                    title = title_elem.text if title_elem is not None else "No title"
                    
                    # 提取作者（前 3 个）
                    authors = []
                    author_list = article.find(".//AuthorList")
                    if author_list is not None:
                        for author in list(author_list)[:3]:
                            last_name = author.find("LastName")
                            first_name = author.find("ForeName")
                            if last_name is not None and last_name.text:
                                author_name = last_name.text
                                if first_name is not None and first_name.text:
                                    author_name += f" {first_name.text}"
                                authors.append(author_name)
                    
                    # 提取期刊
                    journal_elem = article.find(".//Journal/Title")
                    journal = journal_elem.text if journal_elem is not None else "Unknown journal"
                    
                    # 提取发表年份
                    pub_date_elem = article.find(".//PubDate")
                    pub_year = "Unknown"
                    if pub_date_elem is not None:
                        year_elem = pub_date_elem.find("Year")
                        if year_elem is not None:
                            pub_year = year_elem.text
                    
                    # 提取摘要
                    abstract_elem = article.find(".//AbstractText")
                    abstract = ""
                    if abstract_elem is not None:
                        abstract = abstract_elem.text if abstract_elem.text else ""
                        # 限制摘要长度
                        if len(abstract) > 300:
                            abstract = abstract[:300] + "..."
                    
                    articles.append({
                        "pmid": pmid,
                        "title": title,
                        "authors": authors,
                        "journal": journal,
                        "year": pub_year,
                        "abstract": abstract
                    })
                except Exception as e:
                    logger.warning(f"Error parsing article: {e}")
                    continue
            
            # 格式化输出
            if not articles:
                return f"Found {len(pmids)} article(s) but failed to parse details for query: {query}"
            
            result_lines = [f"Found {len(articles)} article(s) for query: {query}\n"]
            
            for article in articles:
                result_lines.append(f"[PMID:{article['pmid']}] {article['title']}")
                if article['authors']:
                    authors_str = ", ".join(article['authors'])
                    if len(article['authors']) == 3:
                        authors_str += " et al."
                    result_lines.append(f"Authors: {authors_str}")
                result_lines.append(f"Journal: {article['journal']}, {article['year']}")
                if article['abstract']:
                    result_lines.append(f"Abstract: {article['abstract']}")
                result_lines.append("")  # 空行分隔
            
            return "\n".join(result_lines)
            
        except Exception as e:
            error_msg = f"Error searching PubMed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg
    
    async def _arun(self, query: str) -> str:
        """Async version of PubMed search."""
        return self._run(query)


class VectorDBStoreTool(BaseTool):
    """Tool for storing articles in vector database."""
    
    name: str = "vector_store"
    description: str = (
        "Store an article in the vector database for semantic search. "
        "Input should be a PMID (PubMed ID) or a JSON string with PMID and article content. "
        "Returns confirmation message."
    )
    
    # 使用类级别的变量存储配置和向量数据库
    _config: Optional[AgentConfig] = None
    _vector_db = None
    
    def __init__(self, config: Optional[AgentConfig] = None, **kwargs):
        """Initialize the vector storage tool."""
        super().__init__(**kwargs)
        # 使用私有属性存储，避免Pydantic验证错误
        object.__setattr__(self, '_config', config or AgentConfig())
        object.__setattr__(self, '_vector_db', create_vector_db(self._config))
    
    @property
    def config(self) -> AgentConfig:
        """Get the configuration."""
        return self._config
    
    @property
    def vector_db(self):
        """Get the vector database."""
        return self._vector_db
    
    def _run(self, input_data: str) -> str:
        """
        Execute vector storage.
        
        Args:
            input_data: Can be a PMID string or JSON string with PMID and content.
                       Format: '{"pmid": "12345678", "title": "...", "abstract": "...", ...}'
        """
        try:
            import json
            
            # 尝试解析JSON格式
            try:
                data = json.loads(input_data)
                pmid = data.get("pmid") or data.get("PMID")
                title = data.get("title", "")
                abstract = data.get("abstract", "") or data.get("Abstract", "")
                authors = data.get("authors", []) or data.get("Authors", [])
                journal = data.get("journal", "") or data.get("Journal", "")
                publication_date = data.get("publication_date", "") or data.get("PublicationDate", "")
            except json.JSONDecodeError:
                # 如果不是JSON，假设是PMID字符串，需要从其他地方获取文章内容
                # 这里暂时返回占位符，实际实现需要调用PubMed API
                pmid = input_data.strip()
                logger.warning(f"PMID only provided, but article content fetching not implemented yet: {pmid}")
                return f"Note: Storage for PMID {pmid} requires article content. Please provide article data in JSON format."
            
            if not pmid:
                return "Error: PMID is required"
            
            if not abstract and not title:
                return f"Error: Article content (title or abstract) is required for PMID {pmid}"
            
            # 准备文本内容
            full_text = f"{title}\n\n{abstract}".strip()
            
            # 分块处理长文本
            chunks = chunk_text(full_text, chunk_size=self.config.chunk_size, overlap=self.config.chunk_overlap)
            
            if not chunks:
                return f"Error: No valid text content to store for PMID {pmid}"
            
            # 准备元数据
            texts = []
            metadatas = []
            ids = []
            
            for i, chunk in enumerate(chunks):
                texts.append(chunk)
                metadatas.append({
                    "pmid": pmid,
                    "title": title,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "authors": ", ".join(authors) if authors else "",
                    "journal": journal,
                    "publication_date": publication_date
                })
                ids.append(f"{pmid}_chunk_{i}")
            
            # 存储到向量数据库
            success = self.vector_db.store(texts=texts, metadatas=metadatas, ids=ids)
            
            if success:
                return f"Successfully stored article with PMID {pmid} ({len(chunks)} chunks)"
            else:
                return f"Error storing article with PMID {pmid}"
                
        except Exception as e:
            logger.error(f"Error in vector storage: {e}")
            return f"Error storing article: {str(e)}"
    
    async def _arun(self, input_data: str) -> str:
        """Async version of vector storage."""
        return self._run(input_data)


class VectorSearchTool(BaseTool):
    """Tool for semantic search in vector database."""
    
    name: str = "vector_search"
    description: str = (
        "Search the vector database for semantically similar articles. "
        "Input should be a search query string. "
        "Returns relevant articles from stored database with PMIDs and similarity scores."
    )
    
    # 使用类级别的变量存储配置和向量数据库
    _config: Optional[AgentConfig] = None
    _vector_db = None
    
    def __init__(self, config: Optional[AgentConfig] = None, **kwargs):
        """Initialize the vector search tool."""
        super().__init__(**kwargs)
        # 使用私有属性存储，避免Pydantic验证错误
        object.__setattr__(self, '_config', config or AgentConfig())
        object.__setattr__(self, '_vector_db', create_vector_db(self._config))
    
    @property
    def config(self) -> AgentConfig:
        """Get the configuration."""
        return self._config
    
    @property
    def vector_db(self):
        """Get the vector database."""
        return self._vector_db
    
    def _run(self, query: str) -> str:
        """Execute vector search."""
        try:
            if not query or not query.strip():
                return "Error: Search query is required"
            
            # 执行搜索
            results = self.vector_db.search(
                query=query,
                n_results=self.config.max_retrieve_results
            )
            
            if not results:
                return f"No relevant articles found for query: {query}"
            
            # 格式化结果
            formatted_results = []
            for result in results:
                metadata = result.get('metadata', {})
                pmid = metadata.get('pmid', 'Unknown')
                title = metadata.get('title', '')
                score = result.get('score', 0.0)
                
                # 获取文档内容（前200字符）
                doc = result.get('document', '')
                preview = doc[:200] + "..." if len(doc) > 200 else doc
                
                formatted_results.append(
                    f"[PMID:{pmid}] {title}\n"
                    f"Similarity: {score:.3f}\n"
                    f"Content: {preview}\n"
                )
            
            # 汇总结果
            summary = f"Found {len(results)} relevant article(s) for query: {query}\n\n"
            summary += "\n---\n\n".join(formatted_results)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return f"Error searching vector database: {str(e)}"
    
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
        PubMedSearchTool(config=config),
        VectorDBStoreTool(config=config),
        VectorSearchTool(config=config)
    ]

