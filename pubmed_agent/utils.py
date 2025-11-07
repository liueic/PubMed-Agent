"""
Utility functions for the PubMed Agent.
Phase 1: Basic infrastructure - Core utilities for text processing and data handling.
Phase 3: Long text management - Enhanced text processing.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class PubMedArticle:
    """
    Data class representing a PubMed article.
    
    This structure supports:
    - Article metadata (PMID, title, authors, etc.)
    - Abstract text for processing
    - Keywords for categorization
    - Publication information
    """
    pmid: str
    title: str
    abstract: str
    authors: List[str]
    journal: str
    publication_date: str
    doi: Optional[str] = None
    keywords: List[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None, detailed: bool = False) -> None:
    """
    设置日志配置，使用统一的日志配置模块
    
    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径，如果为None则不写入文件
        detailed: 是否显示详细信息（时间戳、函数名等）
    """
    from .logging_config import setup_logging as setup_logging_impl
    setup_logging_impl(log_level=log_level, log_file=log_file, detailed=detailed, use_color=True)


def clean_text(text: str) -> str:
    """
    Clean and normalize text content.
    
    Phase 3: Long text management - Text preprocessing for better embedding.
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters that might cause issues
    text = re.sub(r'[^\w\s\-\.,;:!?()[\]{}"\'/]', '', text)
    
    return text.strip()


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks for better embedding and retrieval.
    
    Phase 3: Long text management - Intelligent text chunking.
    
    Args:
        text: The text to chunk
        chunk_size: Maximum size of each chunk
        overlap: Number of characters to overlap between chunks
    
    Returns:
        List of text chunks
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundaries (Phase 3 enhancement)
        if end < len(text):
            # Look for sentence endings near the chunk boundary
            sentence_end = max(
                text.rfind('.', start, end + 100),
                text.rfind('!', start, end + 100),
                text.rfind('?', start, end + 100)
            )
            
            if sentence_end > start:
                end = sentence_end + 1
        
        chunks.append(text[start:end].strip())
        
        if end >= len(text):
            break
            
        start = max(start + 1, end - overlap)
    
    return [chunk for chunk in chunks if chunk]


def format_reference(pmid: str, title: str, authors: List[str], journal: str) -> str:
    """
    Format a reference in a consistent format.
    
    Phase 2: Thought templates - Standardized citation format.
    """
    author_str = ", ".join(authors[:3])  # Limit to first 3 authors
    if len(authors) > 3:
        author_str += f" et al. ({len(authors)} authors)"
    
    return f"[PMID:{pmid}] {author_str}. {title}. {journal}"


def parse_pubmed_date(pub_date: Dict[str, Any]) -> str:
    """Parse PubMed publication date into a consistent format."""
    try:
        if 'Year' in pub_date:
            year = pub_date['Year']
            month = pub_date.get('Month', '')
            day = pub_date.get('Day', '')
            
            if month and day:
                return f"{year}-{month}-{day}"
            elif month:
                return f"{year}-{month}"
            else:
                return year
        
        return "Unknown"
    except Exception:
        return "Unknown"


def validate_pmids(pmids: List[str]) -> List[str]:
    """Validate and clean PMID list."""
    valid_pmids = []
    
    for pmid in pmids:
        # Remove any non-digit characters
        clean_pmid = re.sub(r'[^\d]', '', str(pmid))
        if clean_pmid and len(clean_pmid) <= 8:  # Valid PMIDs are 1-8 digits
            valid_pmids.append(clean_pmid)
    
    return valid_pmids


class PubMedRateLimiter:
    """
    Rate limiter for PubMed API calls.
    
    Phase 1: Basic infrastructure - API rate limiting.
    """
    
    def __init__(self, requests_per_second: float = 3.0):
        self.requests_per_second = requests_per_second
        self.last_request_time = 0
        import time
        self.time = time
    
    def wait_if_needed(self):
        """Wait if necessary to respect rate limits."""
        current_time = self.time.time()
        time_since_last_request = current_time - self.last_request_time
        
        min_interval = 1.0 / self.requests_per_second
        
        if time_since_last_request < min_interval:
            sleep_time = min_interval - time_since_last_request
            self.time.sleep(sleep_time)
        
        self.last_request_time = self.time.time()