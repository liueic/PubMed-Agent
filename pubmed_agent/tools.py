"""
LangChain tools for PubMed Agent.
Phase 1: Basic infrastructure - Tool system.
"""

import logging
import json
import threading
import time
from typing import List, Optional, Dict, Any
from langchain.tools import BaseTool
from langchain_core.tools import tool
from .config import AgentConfig
from .vector_db import create_vector_db, get_collection_name
from .utils import chunk_text, PubMedRateLimiter, parse_pubmed_date

logger = logging.getLogger(__name__)

# 模块级别的向量数据库缓存，按collection_name缓存实例
# 使用线程锁保证线程安全
_vector_db_cache: Dict[str, Any] = {}
_vector_db_cache_lock = threading.Lock()
# 向量数据库缓存大小限制（最多缓存50个实例）
_vector_db_cache_max_size = 50


def clear_vector_db_cache() -> int:
    """
    清空向量数据库缓存。
    
    Returns:
        清空的缓存项数量
    """
    with _vector_db_cache_lock:
        count = len(_vector_db_cache)
        _vector_db_cache.clear()
        logger.info(f"Cleared vector database cache: {count} entries removed")
        return count


def get_vector_db_cache_stats() -> Dict[str, int]:
    """
    获取向量数据库缓存的统计信息。
    
    Returns:
        包含缓存大小等统计信息的字典
    """
    with _vector_db_cache_lock:
        return {
            "cache_size": len(_vector_db_cache),
            "max_size": _vector_db_cache_max_size
        }


def _parse_pubmed_article_xml(article_elem) -> Optional[Dict[str, Any]]:
    """
    从XML元素中解析PubMed文章信息。
    这是一个辅助函数，用于复用文章解析逻辑。
    
    Args:
        article_elem: XML元素，包含PubmedArticle数据
        
    Returns:
        包含文章信息的字典，如果解析失败则返回None
    """
    try:
        # 提取 PMID
        pmid_elem = article_elem.find(".//PMID")
        pmid = pmid_elem.text if pmid_elem is not None else "Unknown"
        
        # 提取标题
        title_elem = article_elem.find(".//ArticleTitle")
        title = title_elem.text if title_elem is not None else "No title"
        
        # 提取完整作者列表
        authors = []
        author_list = article_elem.find(".//AuthorList")
        if author_list is not None:
            for author in author_list:
                last_name = author.find("LastName")
                first_name = author.find("ForeName")
                initials = author.find("Initials")
                if last_name is not None and last_name.text:
                    author_name = last_name.text
                    if first_name is not None and first_name.text:
                        author_name += f" {first_name.text}"
                    elif initials is not None and initials.text:
                        author_name += f" {initials.text}"
                    authors.append(author_name)
        
        # 提取期刊信息
        journal_elem = article_elem.find(".//Journal/Title")
        journal = journal_elem.text if journal_elem is not None else "Unknown journal"
        
        # 提取期刊ISO缩写
        journal_iso = article_elem.find(".//Journal/ISOAbbreviation")
        journal_iso_text = journal_iso.text if journal_iso is not None else None
        
        # 提取更详细的出版日期
        pub_date_elem = article_elem.find(".//PubDate")
        pub_year = "Unknown"
        pub_month = ""
        pub_day = ""
        if pub_date_elem is not None:
            year_elem = pub_date_elem.find("Year")
            month_elem = pub_date_elem.find("Month")
            day_elem = pub_date_elem.find("Day")
            if year_elem is not None:
                pub_year = year_elem.text
            if month_elem is not None:
                pub_month = month_elem.text
            if day_elem is not None:
                pub_day = day_elem.text
        
        # 构建完整的出版日期字符串
        pub_date_parts = [pub_year]
        if pub_month:
            pub_date_parts.append(pub_month)
        if pub_day:
            pub_date_parts.append(pub_day)
        publication_date = "-".join(pub_date_parts) if pub_date_parts else "Unknown"
        
        # 提取卷号、期号、页码
        volume_elem = article_elem.find(".//JournalIssue/Volume")
        issue_elem = article_elem.find(".//JournalIssue/Issue")
        pagination_elem = article_elem.find(".//Pagination/MedlinePgn")
        volume = volume_elem.text if volume_elem is not None else None
        issue = issue_elem.text if issue_elem is not None else None
        pages = pagination_elem.text if pagination_elem is not None else None
        
        # 提取完整摘要（支持多个AbstractText部分）
        abstract_parts = []
        abstract_elem_list = article_elem.findall(".//Abstract/AbstractText")
        if abstract_elem_list:
            for abs_elem in abstract_elem_list:
                if abs_elem.text:
                    # 检查是否有Label属性（如Background, Methods, Results, Conclusion）
                    label = abs_elem.get("Label", "")
                    text = abs_elem.text.strip()
                    if label:
                        abstract_parts.append(f"{label}: {text}")
                    else:
                        abstract_parts.append(text)
        # 如果没有结构化摘要，尝试获取简单的AbstractText
        if not abstract_parts:
            simple_abstract = article_elem.find(".//AbstractText")
            if simple_abstract is not None and simple_abstract.text:
                abstract_parts.append(simple_abstract.text.strip())
        
        abstract = " ".join(abstract_parts) if abstract_parts else ""
        
        # 提取DOI
        doi = None
        article_id_list = article_elem.findall(".//ArticleIdList/ArticleId")
        for article_id in article_id_list:
            if article_id.get("IdType") == "doi":
                doi = article_id.text
                break
        
        # 提取PMC ID（如果可用）
        pmc_id = None
        for article_id in article_id_list:
            if article_id.get("IdType") == "pmc":
                pmc_id = article_id.text
                break
        
        # 提取MeSH术语
        mesh_terms = []
        mesh_list = article_elem.findall(".//MeshHeadingList/MeshHeading")
        for mesh_heading in mesh_list:
            descriptor = mesh_heading.find("DescriptorName")
            if descriptor is not None and descriptor.text:
                mesh_terms.append(descriptor.text)
        
        # 提取关键词（如果可用）
        keywords = []
        keyword_list = article_elem.findall(".//KeywordList/Keyword")
        for keyword in keyword_list:
            if keyword.text:
                keywords.append(keyword.text)
        
        # 提取文章类型
        publication_types = []
        pub_type_list = article_elem.findall(".//PublicationTypeList/PublicationType")
        for pub_type in pub_type_list:
            if pub_type.text:
                publication_types.append(pub_type.text)
        
        # 提取语言
        language_list = article_elem.findall(".//Language")
        languages = [lang.text for lang in language_list if lang.text]
        language = languages[0] if languages else "Unknown"
        
        # 构建文章信息字典
        article_info = {
            "pmid": pmid,
            "title": title,
            "authors": authors,
            "journal": journal,
            "journal_iso": journal_iso_text,
            "publication_date": publication_date,
            "year": pub_year,
            "volume": volume,
            "issue": issue,
            "pages": pages,
            "abstract": abstract,
            "doi": doi,
            "pmc_id": pmc_id,
            "mesh_terms": mesh_terms,
            "keywords": keywords,
            "publication_types": publication_types,
            "language": language
        }
        
        return article_info
        
    except Exception as e:
        logger.warning(f"Error parsing article XML: {e}", exc_info=True)
        return None


class PubMedSearchTool(BaseTool):
    """Tool for searching PubMed articles."""
    
    name: str = "pubmed_search"
    description: str = (
        "Search PubMed for scientific articles using keywords extracted from user intent. "
        "This is STEP 2 in the structured workflow: query PubMed with relevant keywords. "
        "Input should be a search query string with key terms. "
        "Returns a formatted list of articles with PMIDs, titles, authors, journals, abstracts, and MeSH terms. "
        "The output format is designed to facilitate article selection in the next step. "
        "Use this tool after parsing user intent to search for relevant literature."
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
            # NCBI要求提供真实的email地址，强烈建议配置
            if self.config.pubmed_email:
                email = self.config.pubmed_email.strip()
                # 检查是否是假邮箱
                if email == "pubmed_agent@example.com" or "@example.com" in email.lower():
                    logger.warning(
                        "⚠️  检测到使用了示例邮箱地址。NCBI要求提供真实的email地址。"
                        "请设置环境变量 PUBMED_EMAIL 或在配置中提供您的真实邮箱。"
                        "获取帮助：https://www.ncbi.nlm.nih.gov/account/register/"
                    )
                Entrez.email = email
            else:
                # 未配置email时给出严重警告
                default_email = "pubmed_agent@example.com"
                logger.warning(
                    "警告：未配置 PUBMED_EMAIL 环境变量。"
                    "NCBI要求提供真实的email地址以符合使用政策。"
                    "当前使用临时邮箱，可能导致API访问受限。"
                    "请设置环境变量 PUBMED_EMAIL=your_email@example.com"
                    "或在配置文件中提供您的真实邮箱。"
                )
                Entrez.email = default_email
            
            if self.config.pubmed_tool_name:
                Entrez.tool = self.config.pubmed_tool_name
            else:
                Entrez.tool = "pubmed_agent"
            
            # 设置API key（可选，但强烈推荐以提升速率限制）
            if self.config.pubmed_api_key:
                Entrez.api_key = self.config.pubmed_api_key.strip()
                logger.info("✅ 已配置PubMed API Key，速率限制已提升（10次/秒）")
            else:
                logger.warning(
                    "ℹ️  未配置 PUBMED_API_KEY。"
                    "当前速率限制为3次/秒。"
                    "配置API Key可将速率限制提升至10次/秒。"
                    "获取方式：登录NCBI账户 -> 我的NCBI -> API密钥"
                    "设置环境变量：PUBMED_API_KEY=your_api_key"
                )
            
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
            # 使用 medline 格式获取更全面的信息（包括DOI、MeSH、关键词等）
            pmid_string = ",".join(pmids)
            fetch_handle = Entrez.efetch(
                db="pubmed",
                id=pmid_string,
                rettype="medline",  # 使用medline格式获取更全面的元数据
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
            
            # 提取文章信息（增强版，提取更全面的字段）
            articles = []
            for article in root.findall(".//PubmedArticle"):
                article_info = _parse_pubmed_article_xml(article)
                if article_info:
                    # 添加额外的字段用于格式化输出
                    article_info["author_count"] = len(article_info.get("authors", []))
                    article_info["abstract_length"] = len(article_info.get("abstract", ""))
                    articles.append(article_info)
            
            # 格式化输出（增强版，展示更全面的信息）
            if not articles:
                return f"Found {len(pmids)} article(s) but failed to parse details for query: {query}"
            
            result_lines = [f"Found {len(articles)} article(s) for query: {query}\n"]
            
            for article in articles:
                # 标题和PMID
                result_lines.append(f"[PMID:{article['pmid']}] {article['title']}")
                
                # 作者信息
                if article['authors']:
                    # 显示前5个作者，如果超过5个则显示"et al."
                    if len(article['authors']) <= 5:
                        authors_str = ", ".join(article['authors'])
                    else:
                        authors_str = ", ".join(article['authors'][:5]) + f" et al. ({article['author_count']} authors)"
                    result_lines.append(f"Authors: {authors_str}")
                
                # 期刊和出版信息
                journal_info = f"Journal: {article['journal']}"
                if article.get('journal_iso'):
                    journal_info += f" ({article['journal_iso']})"
                
                # 添加卷、期、页信息
                pub_info_parts = [article.get('year', 'Unknown')]
                if article.get('volume'):
                    pub_info_parts.append(f"Vol.{article['volume']}")
                if article.get('issue'):
                    pub_info_parts.append(f"Issue {article['issue']}")
                if article.get('pages'):
                    pub_info_parts.append(f"pp.{article['pages']}")
                
                journal_info += f" ({', '.join(pub_info_parts)})"
                result_lines.append(journal_info)
                
                # DOI和PMC ID
                id_info = []
                if article.get('doi'):
                    id_info.append(f"DOI: {article['doi']}")
                if article.get('pmc_id'):
                    id_info.append(f"PMC: {article['pmc_id']}")
                if id_info:
                    result_lines.append(", ".join(id_info))
                
                # 文章类型和语言
                meta_info = []
                if article.get('publication_types'):
                    meta_info.append(f"Type: {', '.join(article['publication_types'])}")
                if article.get('language') and article['language'] != 'Unknown':
                    meta_info.append(f"Language: {article['language']}")
                if meta_info:
                    result_lines.append(" | ".join(meta_info))
                
                # MeSH术语（显示前5个）
                if article.get('mesh_terms'):
                    mesh_display = article['mesh_terms'][:5]
                    mesh_str = ", ".join(mesh_display)
                    if len(article['mesh_terms']) > 5:
                        mesh_str += f" (+{len(article['mesh_terms']) - 5} more)"
                    result_lines.append(f"MeSH Terms: {mesh_str}")
                
                # 关键词（如果可用）
                if article.get('keywords'):
                    keywords_display = article['keywords'][:5]
                    keywords_str = ", ".join(keywords_display)
                    if len(article['keywords']) > 5:
                        keywords_str += f" (+{len(article['keywords']) - 5} more)"
                    result_lines.append(f"Keywords: {keywords_str}")
                
                # 摘要（完整摘要，不截断）
                if article.get('abstract'):
                    abstract = article['abstract']
                    # 如果摘要太长，在显示时可以截断，但保留完整信息用于存储
                    display_abstract = abstract
                    if len(abstract) > 1000:  # 显示时如果超过1000字符则截断并提示
                        display_abstract = abstract[:1000] + f"... (完整摘要共{len(abstract)}字符)"
                    result_lines.append(f"Abstract: {display_abstract}")
                
                result_lines.append("")  # 空行分隔
            
            return "\n".join(result_lines)
            
        except Exception as e:
            error_msg = f"Error searching PubMed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg
    
    async def _arun(self, query: str) -> str:
        """Async version of PubMed search."""
        return self._run(query)


class PubMedFetchTool(BaseTool):
    """Tool for fetching a single article by PMID."""
    
    name: str = "pubmed_fetch"
    description: str = (
        "Fetch detailed information for a single article from PubMed by its PMID (PubMed ID). "
        "This is STEP 4 in the structured workflow: get complete article details for selected articles. "
        "Input should be a PMID string (e.g., '12345678') from articles selected in STEP 3. "
        "Returns JSON-formatted article data including title, abstract, authors, journal, MeSH terms, keywords, and metadata. "
        "The output is in the correct format to be directly stored using vector_store tool. "
        "Use this tool after selecting interesting articles from search results to get their complete information."
    )
    
    # 使用类级别的变量存储配置和速率限制器
    _config: Optional[AgentConfig] = None
    _rate_limiter = None
    
    def __init__(self, config: Optional[AgentConfig] = None, **kwargs):
        """Initialize the PubMed fetch tool."""
        super().__init__(**kwargs)
        # 使用私有属性存储，避免Pydantic验证错误
        object.__setattr__(self, '_config', config or AgentConfig())
        object.__setattr__(self, '_rate_limiter', PubMedRateLimiter(requests_per_second=3.0))
    
    @property
    def config(self) -> AgentConfig:
        """Get the configuration."""
        return self._config
    
    def _run(self, pmid: str) -> str:
        """
        Execute PubMed fetch by PMID.
        
        Args:
            pmid: PubMed ID (PMID) as a string
            
        Returns:
            JSON-formatted string containing article data, or error message
        """
        try:
            # 导入 Bio.Entrez（延迟导入，避免在模块级别导入）
            try:
                from Bio import Entrez
                from xml.etree import ElementTree as ET
            except ImportError:
                logger.error("Bio.Entrez is not available. Please install biopython: pip install biopython")
                return json.dumps({
                    "error": "biopython is required for PubMed fetch. Please install it: pip install biopython"
                })
            
            # 清理PMID输入（移除可能的空格和非数字字符）
            pmid = str(pmid).strip()
            # 移除常见的PMID前缀（如"PMID:"）
            if pmid.upper().startswith("PMID:"):
                pmid = pmid[5:].strip()
            
            # 验证PMID格式（应该是1-8位数字）
            if not pmid.isdigit() or len(pmid) > 8:
                error_msg = f"Invalid PMID format: {pmid}. PMID should be 1-8 digits."
                logger.warning(error_msg)
                return json.dumps({"error": error_msg, "pmid": pmid})
            
            # 设置 NCBI Entrez 参数
            if self.config.pubmed_email:
                email = self.config.pubmed_email.strip()
                if email == "pubmed_agent@example.com" or "@example.com" in email.lower():
                    logger.warning(
                        "⚠️  检测到使用了示例邮箱地址。NCBI要求提供真实的email地址。"
                        "请设置环境变量 PUBMED_EMAIL 或在配置中提供您的真实邮箱。"
                    )
                Entrez.email = email
            else:
                default_email = "pubmed_agent@example.com"
                logger.warning(
                    "警告：未配置 PUBMED_EMAIL 环境变量。"
                    "NCBI要求提供真实的email地址以符合使用政策。"
                )
                Entrez.email = default_email
            
            if self.config.pubmed_tool_name:
                Entrez.tool = self.config.pubmed_tool_name
            else:
                Entrez.tool = "pubmed_agent"
            
            # 设置API key（可选，但强烈推荐以提升速率限制）
            if self.config.pubmed_api_key:
                Entrez.api_key = self.config.pubmed_api_key.strip()
                logger.info("✅ 已配置PubMed API Key，速率限制已提升（10次/秒）")
            else:
                logger.debug("未配置 PUBMED_API_KEY，当前速率限制为3次/秒")
            
            # 使用速率限制器
            self._rate_limiter.wait_if_needed()
            
            # 使用 efetch 获取文章详情
            logger.info(f"Fetching article with PMID: {pmid}")
            fetch_handle = Entrez.efetch(
                db="pubmed",
                id=pmid,
                rettype="medline",  # 使用medline格式获取更全面的元数据
                retmode="xml"
            )
            
            # 解析 XML
            try:
                xml_data = fetch_handle.read()
                fetch_handle.close()
                
                root = ET.fromstring(xml_data)
            except ET.ParseError as e:
                error_msg = f"Error parsing XML response for PMID {pmid}: {e}"
                logger.error(error_msg)
                return json.dumps({"error": error_msg, "pmid": pmid})
            
            # 查找文章元素
            articles = root.findall(".//PubmedArticle")
            
            if not articles:
                # 检查是否有错误信息
                error_elements = root.findall(".//ERROR")
                if error_elements:
                    error_text = error_elements[0].text if error_elements[0].text else "Unknown error"
                    error_msg = f"PubMed API error for PMID {pmid}: {error_text}"
                    logger.error(error_msg)
                    return json.dumps({"error": error_msg, "pmid": pmid})
                
                # 没有找到文章
                error_msg = f"Article with PMID {pmid} not found in PubMed database."
                logger.warning(error_msg)
                return json.dumps({"error": error_msg, "pmid": pmid})
            
            # 解析第一篇文章（应该只有一篇）
            article_elem = articles[0]
            article_info = _parse_pubmed_article_xml(article_elem)
            
            if not article_info:
                error_msg = f"Failed to parse article data for PMID {pmid}"
                logger.error(error_msg)
                return json.dumps({"error": error_msg, "pmid": pmid})
            
            # 返回JSON格式的文章数据
            logger.info(f"Successfully fetched article: {article_info.get('title', 'Unknown')[:50]}...")
            return json.dumps(article_info, ensure_ascii=False, indent=2)
            
        except Exception as e:
            error_msg = f"Error fetching article from PubMed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return json.dumps({"error": error_msg, "pmid": pmid if 'pmid' in locals() else "unknown"})
    
    async def _arun(self, pmid: str) -> str:
        """Async version of PubMed fetch."""
        return self._run(pmid)


class VectorDBStoreTool(BaseTool):
    """Tool for storing articles in vector database."""
    
    name: str = "vector_store"
    description: str = (
        "Store an article in the vector database for semantic search. "
        "This is STEP 6 in the structured workflow: store high-quality, relevant articles that passed evaluation in STEP 5. "
        "Input should be JSON-formatted article data from pubmed_fetch tool (already in correct format). "
        "Only store articles that are highly relevant, have complete information, and provide unique contributions. "
        "The tool will chunk the article text and create embeddings for semantic retrieval. "
        "Returns confirmation message with number of chunks stored. "
        "Use this tool after evaluating fetched articles to store only the most valuable ones."
    )
    
    # 使用类级别的变量存储配置和向量数据库
    _config: Optional[AgentConfig] = None
    _vector_db = None
    _thread_id_getter = None
    
    def __init__(self, config: Optional[AgentConfig] = None, thread_id_getter=None, **kwargs):
        """
        Initialize the vector storage tool.
        
        Args:
            config: Agent配置对象
            thread_id_getter: 用于获取当前thread_id的函数，如果为None则使用默认collection
        """
        super().__init__(**kwargs)
        # 使用私有属性存储，避免Pydantic验证错误
        object.__setattr__(self, '_config', config or AgentConfig())
        object.__setattr__(self, '_thread_id_getter', thread_id_getter)
        # 不在这里创建vector_db，而是在运行时根据thread_id动态创建
    
    @property
    def config(self) -> AgentConfig:
        """Get the configuration."""
        return self._config
    
    def _get_vector_db(self):
        """动态获取向量数据库实例，根据当前thread_id创建对应的collection，使用缓存避免重复创建"""
        thread_id = None
        if self._thread_id_getter:
            try:
                thread_id = self._thread_id_getter()
            except Exception as e:
                logger.warning(f"Failed to get thread_id: {e}, using default collection")
        
        collection_name = get_collection_name(thread_id)
        
        # 使用缓存机制，避免重复创建向量数据库实例
        with _vector_db_cache_lock:
            if collection_name not in _vector_db_cache:
                # 如果缓存已满，删除最旧的项（简单策略：删除第一个）
                if len(_vector_db_cache) >= _vector_db_cache_max_size:
                    oldest_key = next(iter(_vector_db_cache))
                    _vector_db_cache.pop(oldest_key)
                    logger.debug(f"Vector DB cache full, removed entry: {oldest_key}")
                
                logger.debug(f"Creating new vector database instance for collection: {collection_name}")
                _vector_db_cache[collection_name] = create_vector_db(self._config, collection_name=collection_name)
            else:
                logger.debug(f"Reusing cached vector database instance for collection: {collection_name}")
            
            return _vector_db_cache[collection_name]
    
    def _run(self, input_data: str) -> str:
        """
        Execute vector storage.
        
        Args:
            input_data: Can be a PMID string or JSON string with PMID and content.
                       Format: '{"pmid": "12345678", "title": "...", "abstract": "...", ...}'
        """
        try:
            import json
            
            # 尝试解析JSON格式（支持增强的字段）
            try:
                # 首先检查input_data是否为字符串
                if not isinstance(input_data, str):
                    # 如果不是字符串，尝试转换为字符串
                    input_data = str(input_data)
                
                # 尝试修复可能被截断的JSON字符串
                fixed_input = input_data.strip()
                
                # 处理可能的双重编码（外层有引号）
                if fixed_input.startswith('"') and fixed_input.endswith('"'):
                    # 去除外层引号
                    fixed_input = fixed_input[1:-1]
                    # 处理转义的引号
                    fixed_input = fixed_input.replace('\\"', '"')
                
                # 如果字符串看起来像JSON但可能被截断（以不完整的引号或括号结尾）
                if fixed_input.startswith('{') and not fixed_input.rstrip().endswith('}'):
                    # 尝试补全JSON结构
                    # 检查是否有未闭合的字符串值（考虑转义引号）
                    # 简单方法：统计未转义的引号
                    unescaped_quotes = 0
                    i = 0
                    while i < len(fixed_input):
                        if fixed_input[i] == '"' and (i == 0 or fixed_input[i-1] != '\\'):
                            unescaped_quotes += 1
                        i += 1
                    
                    # 如果有奇数个未转义的引号，说明有未闭合的字符串
                    if unescaped_quotes % 2 != 0:
                        # 有未闭合的引号，尝试补全
                        if not fixed_input.rstrip().endswith('"'):
                            fixed_input = fixed_input.rstrip() + '"'
                    
                    # 补全闭合括号
                    if not fixed_input.rstrip().endswith('}'):
                        fixed_input = fixed_input.rstrip() + '}'
                    logger.debug(f"Attempting to fix truncated JSON: {fixed_input[:100]}...")
                
                data = json.loads(fixed_input)
                
                # 检查解析结果是否为字典类型
                if not isinstance(data, dict):
                    # 如果解析结果是整数或其他非字典类型（例如JSON数字），按PMID字符串处理
                    pmid = str(data).strip()
                    logger.warning(f"JSON解析结果为非字典类型，按PMID处理: {pmid}")
                    return f"Note: Storage for PMID {pmid} requires article content. Please provide article data in JSON format."
                
                # 确保data是字典后才调用.get()方法
                pmid = data.get("pmid") or data.get("PMID")
                title = data.get("title", "")
                abstract = data.get("abstract", "") or data.get("Abstract", "")
                authors = data.get("authors", []) or data.get("Authors", [])
                journal = data.get("journal", "") or data.get("Journal", "")
                publication_date = data.get("publication_date", "") or data.get("PublicationDate", "")
                # 提取新增字段
                doi = data.get("doi", "")
                pmc_id = data.get("pmc_id", "")
                mesh_terms = data.get("mesh_terms", []) or data.get("MeSH", [])
                keywords = data.get("keywords", []) or data.get("Keywords", [])
                publication_types = data.get("publication_types", []) or data.get("PublicationTypes", [])
                language = data.get("language", "")
                volume = data.get("volume", "")
                issue = data.get("issue", "")
                pages = data.get("pages", "")
                journal_iso = data.get("journal_iso", "")
            except json.JSONDecodeError as e:
                # JSON解析失败，尝试使用原始输入
                logger.warning(f"JSON解析失败，尝试使用原始输入: {e}")
                # 如果原始输入看起来像JSON（以{开头），记录详细信息
                if isinstance(input_data, str) and input_data.strip().startswith('{'):
                    logger.warning(f"输入看起来像JSON但解析失败，可能是格式错误或被截断: {input_data[:200]}...")
                    return f"Error: Invalid JSON format for article data. Please provide valid JSON-formatted article data from pubmed_fetch tool."
                # 如果不是JSON，假设是PMID字符串，需要从其他地方获取文章内容
                pmid = input_data.strip() if isinstance(input_data, str) else str(input_data).strip()
                logger.warning(f"PMID only provided, but article content fetching not implemented yet: {pmid}")
                return f"Note: Storage for PMID {pmid} requires article content. Please provide article data in JSON format."
            
            if not pmid:
                return "Error: PMID is required"
            
            if not abstract and not title:
                return f"Error: Article content (title or abstract) is required for PMID {pmid}"
            
            # 准备文本内容（包含标题、摘要、MeSH术语和关键词以增强语义搜索）
            text_parts = [title]
            if abstract:
                text_parts.append(abstract)
            # 添加MeSH术语和关键词以增强检索能力
            if mesh_terms:
                text_parts.append(f"MeSH Terms: {', '.join(mesh_terms[:10])}")  # 限制数量
            if keywords:
                text_parts.append(f"Keywords: {', '.join(keywords[:10])}")  # 限制数量
            
            full_text = "\n\n".join(text_parts).strip()
            
            # 分块处理长文本
            chunks = chunk_text(full_text, chunk_size=self.config.chunk_size, overlap=self.config.chunk_overlap)
            
            if not chunks:
                return f"Error: No valid text content to store for PMID {pmid}"
            
            # 准备元数据（包含所有可用字段）
            texts = []
            metadatas = []
            ids = []
            
            for i, chunk in enumerate(chunks):
                texts.append(chunk)
                # 构建完整的元数据字典
                metadata = {
                    "pmid": pmid,
                    "title": title,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "authors": ", ".join(authors) if authors else "",
                    "journal": journal,
                    "publication_date": publication_date
                }
                # 添加可选字段（如果存在）
                if doi:
                    metadata["doi"] = doi
                if pmc_id:
                    metadata["pmc_id"] = pmc_id
                if journal_iso:
                    metadata["journal_iso"] = journal_iso
                if volume:
                    metadata["volume"] = volume
                if issue:
                    metadata["issue"] = issue
                if pages:
                    metadata["pages"] = pages
                if language:
                    metadata["language"] = language
                if mesh_terms:
                    metadata["mesh_terms"] = ", ".join(mesh_terms[:20])  # 存储前20个MeSH术语
                if keywords:
                    metadata["keywords"] = ", ".join(keywords[:20])  # 存储前20个关键词
                if publication_types:
                    metadata["publication_types"] = ", ".join(publication_types)
                
                metadatas.append(metadata)
                ids.append(f"{pmid}_chunk_{i}")
            
            # 存储到向量数据库（动态获取对应的collection）
            start_time = time.time()
            vector_db = self._get_vector_db()
            success = vector_db.store(texts=texts, metadatas=metadatas, ids=ids)
            elapsed_time = time.time() - start_time
            
            if success:
                logger.info(f"Performance: Stored {len(chunks)} chunks for PMID {pmid} in {elapsed_time:.2f}s "
                          f"({len(chunks)/elapsed_time:.1f} chunks/s)")
                return f"Successfully stored article with PMID {pmid} ({len(chunks)} chunks)"
            else:
                logger.warning(f"Performance: Failed to store {len(chunks)} chunks for PMID {pmid} after {elapsed_time:.2f}s")
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
        "Search the vector database for semantically similar article chunks. "
        "This is STEP 7 in the structured workflow: retrieve the best matching papers from stored articles. "
        "Input should be the original user question or refined query based on user intent. "
        "Uses semantic similarity to find the most relevant content from articles stored in STEP 6. "
        "Returns relevant article chunks with PMIDs, titles, similarity scores, and content previews. "
        "The results are ranked by relevance and can be used to synthesize the final answer. "
        "Use this tool after storing articles to find the best information for answering the user's question."
    )
    
    # 使用类级别的变量存储配置和向量数据库
    _config: Optional[AgentConfig] = None
    _vector_db = None
    _thread_id_getter = None
    
    def __init__(self, config: Optional[AgentConfig] = None, thread_id_getter=None, **kwargs):
        """
        Initialize the vector search tool.
        
        Args:
            config: Agent配置对象
            thread_id_getter: 用于获取当前thread_id的函数，如果为None则使用默认collection
        """
        super().__init__(**kwargs)
        # 使用私有属性存储，避免Pydantic验证错误
        object.__setattr__(self, '_config', config or AgentConfig())
        object.__setattr__(self, '_thread_id_getter', thread_id_getter)
        # 不在这里创建vector_db，而是在运行时根据thread_id动态创建
    
    @property
    def config(self) -> AgentConfig:
        """Get the configuration."""
        return self._config
    
    def _get_vector_db(self):
        """动态获取向量数据库实例，根据当前thread_id创建对应的collection，使用缓存避免重复创建"""
        thread_id = None
        if self._thread_id_getter:
            try:
                thread_id = self._thread_id_getter()
            except Exception as e:
                logger.warning(f"Failed to get thread_id: {e}, using default collection")
        
        collection_name = get_collection_name(thread_id)
        
        # 使用缓存机制，避免重复创建向量数据库实例
        with _vector_db_cache_lock:
            if collection_name not in _vector_db_cache:
                # 如果缓存已满，删除最旧的项（简单策略：删除第一个）
                if len(_vector_db_cache) >= _vector_db_cache_max_size:
                    oldest_key = next(iter(_vector_db_cache))
                    _vector_db_cache.pop(oldest_key)
                    logger.debug(f"Vector DB cache full, removed entry: {oldest_key}")
                
                logger.debug(f"Creating new vector database instance for collection: {collection_name}")
                _vector_db_cache[collection_name] = create_vector_db(self._config, collection_name=collection_name)
            else:
                logger.debug(f"Reusing cached vector database instance for collection: {collection_name}")
            
            return _vector_db_cache[collection_name]
    
    def _run(self, query: str) -> str:
        """Execute vector search."""
        try:
            if not query or not query.strip():
                return "Error: Search query is required"
            
            # 执行搜索（动态获取对应的collection）
            start_time = time.time()
            vector_db = self._get_vector_db()
            results = vector_db.search(
                query=query,
                n_results=self.config.max_retrieve_results
            )
            elapsed_time = time.time() - start_time
            
            if not results:
                logger.info(f"Performance: Vector search for '{query[:50]}...' completed in {elapsed_time:.2f}s, no results")
                return f"No relevant articles found for query: {query}"
            
            logger.info(f"Performance: Vector search for '{query[:50]}...' found {len(results)} results in {elapsed_time:.2f}s")
            
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


def create_tools(config: AgentConfig, thread_id_getter=None) -> List[BaseTool]:
    """
    Create all tools for the agent.
    
    Args:
        config: Agent configuration
        thread_id_getter: 用于获取当前thread_id的函数，如果为None则使用默认collection
        
    Returns:
        List of tools
    """
    return [
        PubMedSearchTool(config=config),
        PubMedFetchTool(config=config),
        VectorDBStoreTool(config=config, thread_id_getter=thread_id_getter),
        VectorSearchTool(config=config, thread_id_getter=thread_id_getter)
    ]

