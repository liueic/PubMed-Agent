"""Public interface for the internal PubMed MCP backend."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from .backend import PubMedMCPBackend
from .config import PubMedMCPConfig
from .cache import read_json, write_json


class PubMedMCPClient:
    """High-level wrapper that mirrors the MCP tool contract."""

    def __init__(self, config: Optional[PubMedMCPConfig] = None, base_path: Optional[Path] = None) -> None:
        self.config = config or PubMedMCPConfig.from_env(base_path)
        self.backend = PubMedMCPBackend(self.config)

    # ------------------------------------------------------------------
    # Search entrypoints
    # ------------------------------------------------------------------
    def search(
        self,
        query: str,
        *,
        max_results: int = 20,
        page_size: int = 20,
        days_back: int = 0,
        include_abstract: bool = True,
        sort_by: str = "relevance",
        response_format: str = "standard",
    ) -> Dict[str, Any]:
        effective_max = min(max_results, page_size)
        result = self.backend.search_pubmed(query, effective_max, days_back, sort_by)

        formatted = self.backend.format_for_llm(result["articles"], response_format)

        if include_abstract is False:
            for item in formatted:
                item.pop("abstract", None)
                item.pop("key_points", None)

        endnote_export = None
        if self.config.endnote_export_enabled and result["articles"]:
            endnote_export = []
            for article in result["articles"]:
                export_result = self.backend.export_endnote(article)
                if export_result.get("success"):
                    endnote_export.append({"pmid": article["pmid"], **export_result})

        return {
            "success": True,
            "total": result["total"],
            "query": result["query"],
            "found": len(result["articles"]),
            "articles": formatted,
            "search_metadata": {
                "max_results": max_results,
                "page_size": page_size,
                "effective_results": effective_max,
                "days_back": days_back,
                "sort_by": sort_by,
                "include_abstract": include_abstract,
                "response_format": response_format,
                "is_large_query": max_results > 50,
            },
            "endnote_export": endnote_export,
        }

    def quick_search(self, query: str, *, max_results: int = 10) -> Dict[str, Any]:
        payload = self.search(
            query,
            max_results=max_results,
            page_size=max_results,
            response_format="compact",
        )
        payload["search_metadata"].update({"search_type": "quick"})
        return payload

    # ------------------------------------------------------------------
    # Cache operations
    # ------------------------------------------------------------------
    def cache_info(self, action: str = "stats") -> Dict[str, Any]:
        action = action.lower()
        if action == "stats":
            return {"success": True, "cache_stats": self.backend.cache_stats()}
        if action == "clear":
            before = len(self.backend.memory_cache.data)
            self.backend.clear_memory_cache()
            return {"success": True, "message": f"Cleared {before} memory entries", "cache_stats": self.backend.cache_stats()}
        if action == "clean":
            cleaned = self.backend.clean_memory_cache()
            return {"success": True, "message": f"Removed {cleaned} expired memory entries", "cache_stats": self.backend.cache_stats()}
        if action == "clean_files":
            cleaned = self.backend.clean_file_cache()
            return {"success": True, "message": f"Removed {cleaned} expired file entries", "cache_stats": self.backend.cache_stats()}
        if action == "clear_files":
            cleared = self.backend.clear_file_cache()
            return {"success": True, "message": f"Cleared {cleared} file cache entries", "cache_stats": self.backend.cache_stats()}
        raise ValueError(f"Unknown cache action: {action}")

    # ------------------------------------------------------------------
    # Article retrieval helpers
    # ------------------------------------------------------------------
    def get_details(self, pmids: Union[str, Sequence[str]], *, include_full_text: bool = False) -> Dict[str, Any]:
        pmid_list = [pmids] if isinstance(pmids, str) else list(pmids)
        if len(pmid_list) > 20:
            raise ValueError("A maximum of 20 PMIDs can be requested")
        articles = self.backend.fetch_article_details(pmid_list)
        if include_full_text:
            for article in articles:
                try:
                    article["fullAbstract"] = self.backend.fetch_full_abstract(article["pmid"])
                except Exception:
                    article["fullAbstract"] = None
        return {
            "success": True,
            "articles": articles,
            "metadata": {"count": len(articles), "include_full_text": include_full_text},
        }

    def extract_key_info(
        self,
        pmid: str,
        *,
        extract_sections: Optional[Sequence[str]] = None,
        max_abstract_length: Optional[int] = None,
    ) -> Dict[str, Any]:
        extract_sections = list(extract_sections or ["basic_info", "abstract_summary", "authors"])
        article_result = self.get_details([pmid])
        articles = article_result["articles"]
        if not articles:
            raise ValueError(f"PMID {pmid} not found")
        article = articles[0]

        info: Dict[str, Any] = {}
        if "basic_info" in extract_sections:
            info["basic_info"] = {
                "pmid": article["pmid"],
                "title": article["title"],
                "journal": article["journal"],
                "publicationDate": article["publicationDate"],
                "volume": article["volume"],
                "issue": article["issue"],
                "pages": article["pages"],
                "doi": article["doi"],
                "url": article["url"],
                "publicationTypes": article.get("publicationTypes", []),
            }
        if "authors" in extract_sections:
            info["authors"] = {
                "full_list": article.get("authors", []),
                "first_author": article.get("authors", [None])[0],
                "last_author": article.get("authors", [None])[-1],
                "author_count": len(article.get("authors", [])),
            }
        if "abstract_summary" in extract_sections and article.get("abstract"):
            truncated = self.backend._truncate(article["abstract"], max_abstract_length or self.config.abstract_max_chars)
            info["abstract_summary"] = {
                "full": truncated,
                "structured": self.backend._extract_structured_sections(truncated),
                "key_points": self.backend._extract_key_points(truncated),
                "word_count": len(truncated.split()),
            }
        if "keywords" in extract_sections:
            info["keywords"] = {
                "mesh_terms": article.get("meshTerms", []),
                "keywords": article.get("keywords", []),
            }
        if "doi_link" in extract_sections and article.get("doi"):
            info["doi_link"] = {
                "doi": article["doi"],
                "url": f"https://doi.org/{article['doi']}" if article["doi"].startswith("10.") else article["url"],
            }

        return {
            "success": True,
            "pmid": pmid,
            "extracted_info": info,
            "extraction_metadata": {
                "sections": extract_sections,
                "max_abstract_length": max_abstract_length or self.config.abstract_max_chars,
                "actual_mode": self.config.abstract_mode,
                "actual_max_chars": self.config.abstract_max_chars,
            },
        }

    def cross_reference(self, pmid: str, *, reference_type: str = "similar", max_results: int = 10) -> Dict[str, Any]:
        reference_type = reference_type.lower()
        if reference_type == "reviews":
            query = f"{pmid}[uid] AND review[publication type]"
        else:
            query = f"{pmid}[uid]"
        result = self.search(query, max_results=max_results)
        return {
            "success": True,
            "base_pmid": pmid,
            "reference_type": reference_type,
            "related_articles": result["articles"],
            "metadata": {"found": len(result["articles"]), "max_results": max_results},
        }

    def batch_query(
        self,
        pmids: Sequence[str],
        *,
        query_format: str = "llm_optimized",
    ) -> Dict[str, Any]:
        if len(pmids) > 20:
            raise ValueError("Batch query supports up to 20 PMIDs")
        articles = self.backend.fetch_article_details(pmids)
        formatted = self.backend.format_for_llm(articles, query_format)
        return {
            "success": True,
            "query_format": query_format,
            "articles": formatted,
            "metadata": {"total_queried": len(pmids), "found": len(articles)},
        }

    # ------------------------------------------------------------------
    # Full-text handling
    # ------------------------------------------------------------------
    def detect_fulltext(self, pmid: str, *, auto_download: bool = False) -> Dict[str, Any]:
        article = self.get_details([pmid])["articles"][0]
        oa_info = self.backend.detect_open_access(article)
        download_result = None
        if oa_info.is_open_access and (auto_download or self.config.fulltext_auto_download):
            cached = self._is_pdf_cached(pmid)
            if not cached:
                download_result = self.backend.download_pdf(pmid, oa_info.download_url)
            else:
                download_result = {"success": True, "cached": True, **cached}
        return {
            "success": True,
            "pmid": pmid,
            "article_info": {
                "title": article["title"],
                "authors": article.get("authors", [])[:3],
                "journal": article["journal"],
                "doi": article["doi"],
            },
            "open_access": oa_info.__dict__,
            "download_result": download_result,
            "fulltext_mode": {
                "enabled": self.config.fulltext_enabled,
                "auto_download": self.config.fulltext_auto_download,
                "requested_auto_download": auto_download,
            },
        }

    def download_fulltext(self, pmid: str, *, force_download: bool = False) -> Dict[str, Any]:
        if not self.config.fulltext_enabled:
            return {"success": False, "error": "Full-text mode disabled"}
        cached = None if force_download else self._is_pdf_cached(pmid)
        if cached:
            return {"success": True, "status": "already_cached", **cached}
        article = self.get_details([pmid])["articles"][0]
        oa_info = self.backend.detect_open_access(article)
        if not oa_info.is_open_access:
            return {"success": False, "error": "No open access full-text available", "open_access_sources": oa_info.sources}
        download_result = self.backend.download_pdf(pmid, oa_info.download_url)
        return {
            "success": download_result.get("success", False),
            "pmid": pmid,
            "download_result": download_result,
            "open_access_info": oa_info.__dict__,
        }

    def fulltext_status(self, *, action: str = "stats", pmid: Optional[str] = None) -> Dict[str, Any]:
        action = action.lower()
        if action == "stats":
            return {"success": True, "action": action, "stats": self.backend.fulltext_status()}
        if action == "list":
            return {"success": True, "action": action, "papers": self.backend.list_fulltext(pmid)}
        if action == "clean":
            cleaned = self.backend.clean_fulltext()
            return {"success": True, "action": action, "cleaned": cleaned}
        if action == "clear":
            cleared = self.backend.clear_fulltext()
            return {"success": True, "action": action, "cleared": cleared}
        raise ValueError(f"Unknown fulltext action: {action}")

    def batch_download(self, pmids: Sequence[str]) -> Dict[str, Any]:
        if not self.config.fulltext_enabled:
            return {"success": False, "error": "Full-text mode disabled"}
        download_list = []
        for pmid in pmids:
            article = self.get_details([pmid])["articles"][0]
            oa_info = self.backend.detect_open_access(article)
            if oa_info.is_open_access:
                download_list.append({"pmid": pmid, "download_url": oa_info.download_url})
        results = self.backend.batch_download(download_list)
        return {
            "success": True,
            "requested": len(pmids),
            "available_for_download": len(download_list),
            "results": results,
        }

    # ------------------------------------------------------------------
    # System / EndNote helpers
    # ------------------------------------------------------------------
    def system_check(self) -> Dict[str, Any]:
        info = self.backend.system_check()
        recommendations = []
        if info["system"]["isWindows"]:
            match = next((tool for tool in info["tools"] if tool["name"].lower() == "powershell" and tool["available"]), None)
            if match:
                recommendations.append("PowerShell available for downloads")
            else:
                recommendations.append("Install PowerShell to enable downloads")
        else:
            wget_available = any(tool["name"] == "wget" and tool["available"] for tool in info["tools"])
            curl_available = any(tool["name"] == "curl" and tool["available"] for tool in info["tools"])
            if wget_available:
                recommendations.append("wget available - preferred downloader")
            elif curl_available:
                recommendations.append("curl available - falling back to curl")
            else:
                recommendations.append("Install wget or curl for full-text downloads")
        return {"success": True, "system_environment": info, "recommendations": recommendations}

    def endnote_status(self, action: str = "stats") -> Dict[str, Any]:
        action = action.lower()
        if action == "stats":
            return {"success": True, "action": action, "status": self.backend.endnote_status()}
        if action == "list":
            index = read_json(self.backend.config.endnote_cache_dir / "index.json") or {}
            return {
                "success": True,
                "action": action,
                "exported_papers": list(index.get("exported_papers", {}).values()),
                "total": len(index.get("exported_papers", {})),
            }
        if action in {"clean", "clear"}:
            return {
                "success": False,
                "action": action,
                "message": "EndNote clean/clear operations are not yet implemented in the Python MCP backend.",
            }
        raise ValueError(f"Unknown EndNote action: {action}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _is_pdf_cached(self, pmid: str) -> Optional[Dict[str, Any]]:
        pdf_path = self.backend.config.fulltext_cache_dir / f"{pmid}.pdf"
        if not pdf_path.exists():
            return None
        stats = pdf_path.stat()
        age_hours = (time.time() - stats.st_mtime) / 3600
        if age_hours * 3600 * 1000 > self.config.fulltext_cache_expiry_ms:
            return None
        return {"file_path": str(pdf_path), "file_size": stats.st_size, "age_hours": round(age_hours, 2)}

    def _is_file_older_than(self, path: Path, *, days: int) -> bool:
        age_days = (time.time() - path.stat().st_mtime) / (24 * 3600)
        return age_days > days



