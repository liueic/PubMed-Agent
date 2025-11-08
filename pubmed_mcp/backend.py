"""Core backend that mirrors the Node MCP server features."""

from __future__ import annotations

import json
import os
import platform
import random
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .cache import MemoryCache, read_json, write_json
from .config import PubMedMCPConfig, ensure_directories
from .http import ProxyConfig, PubMedHTTPClient


PUBMED_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
PMC_BASE_URL = "https://www.ncbi.nlm.nih.gov/pmc"
UNPAYWALL_API_URL = "https://api.unpaywall.org/v2"


def _now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class OpenAccessInfo:
    is_open_access: bool
    sources: List[str]
    download_url: Optional[str]
    pmcid: Optional[str]


class PubMedMCPBackend:
    """Python port of the Node pubmed-data-server logic."""

    def __init__(self, config: PubMedMCPConfig) -> None:
        self.config = config
        ensure_directories(config)

        self.http = PubMedHTTPClient(
            proxy_config=ProxyConfig(
                enabled=config.proxy_enabled,
                http_proxy=config.http_proxy,
                https_proxy=config.https_proxy,
                username=config.proxy_username,
                password=config.proxy_password,
            ),
            request_timeout_ms=config.request_timeout_ms,
            rate_limit_delay_ms=config.rate_limit_delay_ms,
            proxy_timeout=config.proxy_timeout,
            proxy_retry_count=config.proxy_retry_count,
        )

        self.memory_cache = MemoryCache(
            timeout_ms=config.cache_timeout_ms,
            max_size=config.cache_max_size,
        )

        self._ensure_indexes()

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------
    def _ensure_indexes(self) -> None:
        if not (self.config.cache_dir / "index.json").exists():
            self._update_cache_index("", add=False)
        if not self._fulltext_index_path().exists():
            write_json(self._fulltext_index_path(), self._fulltext_index())
        endnote_index = self.config.endnote_cache_dir / "index.json"
        if not endnote_index.exists():
            write_json(
                endnote_index,
                {
                    "version": self.config.cache_version,
                    "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "exported_papers": {},
                    "stats": {"totalExports": 0, "risFiles": 0, "bibtexFiles": 0, "lastExport": None},
                },
            )

    # ------------------------------------------------------------------
    # PubMed requests
    # ------------------------------------------------------------------
    def _base_params(self) -> Dict[str, str]:
        params: Dict[str, str] = {
            "tool": self.config.pubmed_tool_name,
            "email": self.config.pubmed_email or "user@example.com",
        }
        if self.config.pubmed_api_key:
            params["api_key"] = self.config.pubmed_api_key
        return params

    def search_pubmed(self, query: str, max_results: int, days_back: int, sort_by: str) -> Dict[str, Any]:
        cache_key = f"{query}|{max_results}|{days_back}|{sort_by}"
        now = _now_ms()
        cached = self.memory_cache.get(cache_key, now)
        if cached is not None:
            return cached

        params = self._base_params()
        params.update(
            {
                "db": "pubmed",
                "term": self._build_query(query, days_back),
                "retmode": "json",
                "retmax": str(max_results),
                "sort": self._map_sort(sort_by),
            }
        )

        response = self.http.get(f"{PUBMED_BASE_URL}/esearch.fcgi", params=params)
        payload = response.json()
        id_list: List[str] = payload.get("esearchresult", {}).get("idlist", [])
        total = int(payload.get("esearchresult", {}).get("count", 0))

        if not id_list:
            result = {"articles": [], "total": total, "query": params["term"]}
            self.memory_cache.set(cache_key, result, now)
            return result

        articles = self.fetch_article_details(id_list)
        result = {"articles": articles, "total": total, "query": params["term"]}
        self.memory_cache.set(cache_key, result, now)
        return result

    def _build_query(self, query: str, days_back: int) -> str:
        if days_back <= 0:
            return query
        date = time.strftime("%Y/%m/%d", time.gmtime(time.time() - days_back * 24 * 60 * 60))
        return f'{query} AND ("{date}"[Date - Publication] : "3000"[Date - Publication])'

    def _map_sort(self, sort_by: str) -> str:
        mapping = {
            "relevance": "relevance",
            "date": "pub+date",
            "pubdate": "pub+date",
        }
        return mapping.get(sort_by.lower(), "relevance")

    # ------------------------------------------------------------------
    # Article details & caching
    # ------------------------------------------------------------------
    def fetch_article_details(self, ids: Sequence[str]) -> List[Dict[str, Any]]:
        articles: List[Dict[str, Any]] = []
        uncached: List[str] = []

        for pmid in ids:
            cached = self._read_article_cache(pmid)
            if cached:
                articles.append(cached)
            else:
                uncached.append(pmid)

        if uncached:
            fetched = self._fetch_from_pubmed(uncached)
            for article in fetched:
                self._write_article_cache(article["pmid"], article)
            articles.extend(fetched)

        # preserve input order
        index = {article["pmid"]: article for article in articles}
        ordered = [index[pmid] for pmid in ids if pmid in index]
        return ordered

    def _fetch_from_pubmed(self, ids: Sequence[str]) -> List[Dict[str, Any]]:
        params = self._base_params()
        params.update(
            {
                "db": "pubmed",
                "id": ",".join(ids),
                "retmode": "json",
            }
        )
        response = self.http.get(f"{PUBMED_BASE_URL}/esummary.fcgi", params=params)
        data = response.json()
        result = data.get("result", {})

        articles: List[Dict[str, Any]] = []
        for pmid in ids:
            raw = result.get(pmid)
            if not raw:
                continue
            article = {
                "pmid": pmid,
                "title": raw.get("title", "No title"),
                "authors": [author.get("name") for author in raw.get("authors", []) if author.get("name")],
                "journal": raw.get("source", "No journal"),
                "publicationDate": raw.get("pubdate", "No date"),
                "volume": raw.get("volume", ""),
                "issue": raw.get("issue", ""),
                "pages": raw.get("pages", ""),
                "abstract": raw.get("abstract"),
                "doi": raw.get("elocationid", ""),
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "publicationTypes": raw.get("pubtype", []),
                "meshTerms": raw.get("meshterms", []),
                "keywords": raw.get("keywords", []),
            }

            if self.config.abstract_mode == "deep":
                if not article["abstract"] or len(article["abstract"]) < 1000:
                    try:
                        article["abstract"] = self.fetch_full_abstract(pmid)
                    except Exception:
                        pass

            articles.append(article)
        return articles

    def fetch_full_abstract(self, pmid: str) -> str:
        params = self._base_params()
        params.update(
            {
                "db": "pubmed",
                "id": pmid,
                "rettype": "abstract",
                "retmode": "text",
            }
        )
        response = self.http.get(f"{PUBMED_BASE_URL}/efetch.fcgi", params=params)
        return response.text

    def _article_cache_path(self, pmid: str) -> Path:
        return self.config.paper_cache_dir / f"{pmid}.json"

    def _read_article_cache(self, pmid: str) -> Optional[Dict[str, Any]]:
        path = self._article_cache_path(pmid)
        entry = read_json(path)
        if not entry:
            return None
        if _now_ms() - entry.get("timestamp", 0) > self.config.paper_cache_expiry_ms:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
            return None
        return entry.get("data")

    def _write_article_cache(self, pmid: str, data: Dict[str, Any]) -> None:
        entry = {
            "version": self.config.cache_version,
            "pmid": pmid,
            "timestamp": _now_ms(),
            "data": data,
        }
        write_json(self._article_cache_path(pmid), entry)
        self._update_cache_index(pmid, add=True)

    def _update_cache_index(self, pmid: str, add: bool) -> None:
        index_path = self.config.cache_dir / "index.json"
        index = read_json(index_path) or {
            "version": self.config.cache_version,
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "papers": {},
            "stats": {"totalPapers": 0, "lastCleanup": None},
        }
        if add and pmid:
            index["papers"][pmid] = {
                "cached": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "file": f"{pmid}.json",
            }
        elif pmid:
            index["papers"].pop(pmid, None)
        index["stats"]["totalPapers"] = len(index["papers"])
        index["stats"]["lastCleanup"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        write_json(index_path, index)

    # ------------------------------------------------------------------
    # Cache maintenance
    # ------------------------------------------------------------------
    def cache_stats(self) -> Dict[str, Any]:
        file_index = read_json(self.config.cache_dir / "index.json") or {}
        return {
            "memory": {
                "hits": self.memory_cache.stats.hits,
                "misses": self.memory_cache.stats.misses,
                "sets": self.memory_cache.stats.sets,
                "evictions": self.memory_cache.stats.evictions,
                "currentSize": len(self.memory_cache.data),
                "maxSize": self.memory_cache.max_size,
                "timeoutMinutes": self.memory_cache.timeout_ms / (60 * 1000),
            },
            "file": {
                "totalPapers": len(file_index.get("papers", {})),
                "cacheDir": str(self.config.paper_cache_dir),
                "lastCleanup": file_index.get("stats", {}).get("lastCleanup"),
                "version": file_index.get("version", self.config.cache_version),
                "expiryDays": self.config.paper_cache_expiry_ms / (24 * 60 * 60 * 1000),
            },
        }

    def clear_memory_cache(self) -> None:
        self.memory_cache.clear()

    def clean_memory_cache(self) -> int:
        return self.memory_cache.clean_expired(_now_ms())

    def clean_file_cache(self) -> int:
        cleaned = 0
        index = read_json(self.config.cache_dir / "index.json") or {}
        papers = dict(index.get("papers", {}))
        for pmid in list(papers.keys()):
            path = self._article_cache_path(pmid)
            entry = read_json(path)
            if not entry or _now_ms() - entry.get("timestamp", 0) > self.config.paper_cache_expiry_ms:
                try:
                    path.unlink(missing_ok=True)
                except Exception:
                    pass
                cleaned += 1
                self._update_cache_index(pmid, add=False)
        return cleaned

    def clear_file_cache(self) -> int:
        count = 0
        if self.config.paper_cache_dir.exists():
            for entry in self.config.paper_cache_dir.glob("*.json"):
                try:
                    entry.unlink()
                    count += 1
                except Exception:
                    pass
        self._update_cache_index("", add=False)
        return count

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------
    def format_for_llm(self, articles: Sequence[Dict[str, Any]], response_format: str) -> List[Dict[str, Any]]:
        if response_format == "compact":
            return [
                {
                    "pmid": a["pmid"],
                    "title": a["title"],
                    "authors": self._format_authors(a["authors"], 2),
                    "journal": a["journal"],
                    "date": a["publicationDate"],
                    "url": a["url"],
                    "abstract": self._truncate(a.get("abstract"), 500),
                }
                for a in articles
            ]

        if response_format == "detailed":
            formatted: List[Dict[str, Any]] = []
            for article in articles:
                record = {
                    "identifier": f"PMID: {article['pmid']}",
                    "title": article["title"],
                    "citation": f"{self._format_authors(article['authors'], 3)} {article['journal']}, {article['publicationDate']}",
                    "url": article["url"],
                    "volume": article["volume"],
                    "issue": article["issue"],
                    "pages": article["pages"],
                    "doi": article["doi"],
                }
                if article.get("abstract"):
                    abstract = self._truncate(article["abstract"], self.config.abstract_max_chars)
                    record["abstract"] = abstract
                    record["key_points"] = self._extract_key_points(abstract)
                    record["structured_sections"] = self._extract_structured_sections(abstract)
                if article.get("meshTerms"):
                    record["keywords"] = article["meshTerms"][:15]
                formatted.append(record)
            return formatted

        # default standard (llm_optimized)
        formatted = []
        for article in articles:
            entry = {
                "pmid": article["pmid"],
                "title": article["title"],
                "citation": f"{self._format_authors(article['authors'], 3)} {article['journal']}, {article['publicationDate']}",
                "url": article["url"],
            }
            if article.get("abstract"):
                abstract = self._truncate(article["abstract"], self.config.abstract_max_chars)
                entry["abstract"] = abstract
                entry["key_points"] = self._extract_key_points(abstract)
            if article.get("meshTerms"):
                entry["keywords"] = article["meshTerms"][:8]
            formatted.append(entry)
        return formatted

    def _truncate(self, text: Optional[str], max_len: int) -> Optional[str]:
        if text is None:
            return None
        if len(text) <= max_len:
            return text
        return text[: max_len - 3] + "..."

    def _format_authors(self, authors: Sequence[str], limit: int) -> str:
        short = list(authors[:limit])
        if len(authors) > limit:
            short.append("et al.")
        return ", ".join(short) if short else "Unknown"

    def _extract_key_points(self, abstract: str) -> List[str]:
        sentences = [s.strip() for s in abstract.replace("\n", " ").split('.') if len(s.strip()) > 20]
        return sentences[:5]

    def _extract_structured_sections(self, abstract: str) -> Dict[str, str]:
        sections = {
            "background": ["background", "introduction"],
            "methods": ["methods", "method"],
            "results": ["results", "findings"],
            "conclusions": ["conclusions", "conclusion"],
        }
        lowered = abstract.lower()
        structured: Dict[str, str] = {}
        for name, keywords in sections.items():
            for keyword in keywords:
                token = f"{keyword}:"
                if token in lowered:
                    start = lowered.index(token) + len(token)
                    snippet = abstract[start:]
                    structured[name] = snippet.strip()
                    break
        return structured or {"full": abstract}

    # ------------------------------------------------------------------
    # Open access detection and downloads
    # ------------------------------------------------------------------
    def detect_open_access(self, article: Dict[str, Any]) -> OpenAccessInfo:
        sources: List[str] = []
        download_url: Optional[str] = None
        pmcid: Optional[str] = None

        pmcid_info = self._check_pmc(article["pmid"])
        if pmcid_info:
            sources.append("PMC")
            download_url = pmcid_info["download_url"]
            pmcid = pmcid_info["pmcid"]

        if not download_url and article.get("doi"):
            unpaywall = self._check_unpaywall(article["doi"])
            if unpaywall:
                sources.append("Unpaywall")
                download_url = unpaywall

        if not download_url and article.get("doi"):
            publisher = self._check_publisher(article["doi"])
            if publisher:
                sources.append("Publisher")
                download_url = publisher

        return OpenAccessInfo(
            is_open_access=bool(download_url),
            sources=sources,
            download_url=download_url,
            pmcid=pmcid,
        )

    def _check_pmc(self, pmid: str) -> Optional[Dict[str, str]]:
        url = f"{PMC_BASE_URL}/?term={pmid}"
        try:
            response = self.http.get(url)
            html = response.text
        except Exception:
            return None
        if "PMC" not in html:
            return None
        # simplistic extraction
        marker = "PMC"
        idx = html.find(marker)
        if idx == -1:
            return None
        digits = []
        for ch in html[idx + len(marker) : idx + len(marker) + 10]:
            if ch.isdigit():
                digits.append(ch)
            else:
                break
        if not digits:
            return None
        pmcid = marker + "".join(digits)
        return {
            "pmcid": pmcid,
            "download_url": f"{PMC_BASE_URL}/articles/{pmcid}/pdf/",
        }

    def _check_unpaywall(self, doi: str) -> Optional[str]:
        params = {
            "email": self.config.pubmed_email or "user@example.com",
        }
        try:
            response = self.http.get(f"{UNPAYWALL_API_URL}/{doi}", params=params)
        except Exception:
            return None
        data = response.json()
        best = data.get("best_oa_location") or {}
        if data.get("is_oa") and best.get("url"):
            return best["url"]
        return None

    def _check_publisher(self, doi: str) -> Optional[str]:
        url = f"https://doi.org/{doi}"
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; PubMedAgent/1.0)",
        }
        try:
            response = self.http.get(url, headers=headers)
            html = response.text
        except Exception:
            return None
        idx = html.lower().find(".pdf")
        if idx == -1:
            return None
        start = html.rfind("href=\"", 0, idx)
        if start == -1:
            return None
        start += len("href=\"")
        end = html.find("\"", start)
        if end == -1:
            return None
        return html[start:end]

    def download_pdf(self, pmid: str, url: str) -> Dict[str, Any]:
        if not url:
            return {"success": False, "error": "No download URL"}
        headers = {"User-Agent": "Mozilla/5.0 (compatible; PubMedAgent/1.0)"}
        try:
            response = self.http.get(url, headers=headers)
            content = response.content
        except Exception as exc:
            return {"success": False, "error": str(exc)}

        if len(content) > self.config.max_pdf_size_bytes:
            return {"success": False, "error": "PDF too large"}

        pdf_path = self.config.fulltext_cache_dir / f"{pmid}.pdf"
        pdf_path.write_bytes(content)

        self._update_fulltext_index(
            pmid,
            {
                "pmid": pmid,
                "downloadUrl": url,
                "filePath": pdf_path.name,
                "fileSize": len(content),
                "downloaded": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        )

        return {"success": True, "filePath": str(pdf_path), "fileSize": len(content)}

    def _fulltext_index_path(self) -> Path:
        return self.config.fulltext_cache_dir / "index.json"

    def _fulltext_index(self) -> Dict[str, Any]:
        return read_json(self._fulltext_index_path()) or {
            "version": self.config.cache_version,
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "fulltext_papers": {},
            "stats": {"totalPDFs": 0, "totalSize": 0, "lastCleanup": None},
        }

    def _update_fulltext_index(self, pmid: str, info: Dict[str, Any]) -> None:
        index = self._fulltext_index()
        info.setdefault("timestamp", _now_ms())
        index["fulltext_papers"][pmid] = info
        index["stats"]["totalPDFs"] = len(index["fulltext_papers"])
        index["stats"]["totalSize"] = sum(v.get("fileSize", 0) for v in index["fulltext_papers"].values())
        index["stats"]["lastCleanup"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        write_json(self._fulltext_index_path(), index)

    def fulltext_status(self) -> Dict[str, Any]:
        index = self._fulltext_index()
        return {
            "fulltext_mode": self.config.fulltext_mode,
            "enabled": self.config.fulltext_enabled,
            "auto_download": self.config.fulltext_auto_download,
            "cache_directory": str(self.config.fulltext_cache_dir),
            "stats": index.get("stats", {}),
        }

    def list_fulltext(self, pmid: Optional[str] = None) -> List[Dict[str, Any]]:
        index = self._fulltext_index()
        papers = index.get("fulltext_papers", {})
        if pmid:
            return [papers[pmid]] if pmid in papers else []
        return list(papers.values())

    def clean_fulltext(self) -> int:
        index = self._fulltext_index()
        papers = index.get("fulltext_papers", {})
        cleaned = 0
        for pmid, info in list(papers.items()):
            pdf_path = self.config.fulltext_cache_dir / info.get("filePath", "")
            if not pdf_path.exists():
                papers.pop(pmid, None)
                cleaned += 1
                continue
            age = _now_ms() - int(info.get("timestamp", _now_ms()))
            if age > self.config.fulltext_cache_expiry_ms:
                try:
                    pdf_path.unlink()
                except Exception:
                    pass
                papers.pop(pmid, None)
                cleaned += 1
        index["fulltext_papers"] = papers
        index["stats"]["totalPDFs"] = len(papers)
        index["stats"]["totalSize"] = sum(item.get("fileSize", 0) for item in papers.values())
        index["stats"]["lastCleanup"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        write_json(self._fulltext_index_path(), index)
        return cleaned

    def clear_fulltext(self) -> int:
        removed = 0
        if self.config.fulltext_cache_dir.exists():
            for pdf in self.config.fulltext_cache_dir.glob("*.pdf"):
                try:
                    pdf.unlink()
                    removed += 1
                except Exception:
                    pass
        index = self._fulltext_index()
        index["fulltext_papers"] = {}
        index["stats"]["totalPDFs"] = 0
        index["stats"]["totalSize"] = 0
        index["stats"]["lastCleanup"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        write_json(self._fulltext_index_path(), index)
        return removed

    # ------------------------------------------------------------------
    # EndNote export
    # ------------------------------------------------------------------
    def export_endnote(self, article: Dict[str, Any]) -> Dict[str, Any]:
        if not self.config.endnote_export_enabled:
            return {"success": False, "error": "EndNote export disabled"}

        ris_path = self.config.endnote_cache_dir / f"{article['pmid']}.ris"
        bib_path = self.config.endnote_cache_dir / f"{article['pmid']}.bib"

        ris_path.write_text(self._generate_ris(article), encoding="utf-8")
        bib_path.write_text(self._generate_bibtex(article), encoding="utf-8")

        index_path = self.config.endnote_cache_dir / "index.json"
        index = read_json(index_path) or {
            "version": self.config.cache_version,
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "exported_papers": {},
            "stats": {"totalExports": 0, "risFiles": 0, "bibtexFiles": 0, "lastExport": None},
        }
        index["exported_papers"][article["pmid"]] = {
            "pmid": article["pmid"],
            "title": article["title"],
            "formats": {"ris": str(ris_path), "bibtex": str(bib_path)},
            "exported": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        index["stats"]["totalExports"] = len(index["exported_papers"])
        index["stats"]["risFiles"] = len(index["exported_papers"])
        index["stats"]["bibtexFiles"] = len(index["exported_papers"])
        index["stats"]["lastExport"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        write_json(index_path, index)

        return {
            "success": True,
            "formats": {"ris": str(ris_path), "bibtex": str(bib_path)},
        }

    def _generate_ris(self, article: Dict[str, Any]) -> str:
        lines = ["TY  - JOUR"]
        if article.get("title"):
            lines.append(f"TI  - {article['title']}")
        for author in article.get("authors", []):
            lines.append(f"AU  - {author}")
        if article.get("journal"):
            lines.append(f"T2  - {article['journal']}")
        if article.get("publicationDate"):
            lines.append(f"PY  - {article['publicationDate']}")
        if article.get("volume"):
            lines.append(f"VL  - {article['volume']}")
        if article.get("issue"):
            lines.append(f"IS  - {article['issue']}")
        if article.get("pages"):
            lines.append(f"SP  - {article['pages']}")
        if article.get("doi"):
            lines.append(f"DO  - {article['doi']}")
        lines.append(f"PMID - {article['pmid']}")
        if article.get("abstract"):
            lines.append(f"AB  - {article['abstract']}")
        for keyword in (article.get("meshTerms") or []):
            lines.append(f"KW  - {keyword}")
        lines.append(f"UR  - {article['url']}")
        lines.append("LA  - eng")
        lines.append("DB  - PubMed")
        lines.append("ER  - ")
        return "\n".join(lines) + "\n"

    def _generate_bibtex(self, article: Dict[str, Any]) -> str:
        first_author = article.get("authors", ["unknown"])[0].replace(" ", "").lower()
        year = article.get("publicationDate", "unknown").split("-")[0]
        cite_key = f"{first_author}{year}{article['pmid']}"
        lines = [f"@article{{{cite_key},"]
        lines.append(f"  title = {{{article.get('title', 'Unknown Title')}}},")
        if article.get("authors"):
            lines.append(f"  author = {{{' and '.join(article['authors'])}}},")
        if article.get("journal"):
            lines.append(f"  journal = {{{article['journal']}}},")
        if article.get("publicationDate"):
            lines.append(f"  year = {{{article['publicationDate']}}},")
        if article.get("volume"):
            lines.append(f"  volume = {{{article['volume']}}},")
        if article.get("issue"):
            lines.append(f"  number = {{{article['issue']}}},")
        if article.get("pages"):
            lines.append(f"  pages = {{{article['pages']}}},")
        if article.get("doi"):
            lines.append(f"  doi = {{{article['doi']}}},")
        lines.append(f"  pmid = {{{article['pmid']}}},")
        lines.append(f"  url = {{https://pubmed.ncbi.nlm.nih.gov/{article['pmid']}/}},")
        if article.get("abstract"):
            lines.append(f"  abstract = {{{article['abstract']}}},")
        lines.append("}")
        return "\n".join(lines) + "\n"

    def endnote_status(self) -> Dict[str, Any]:
        index = read_json(self.config.endnote_cache_dir / "index.json") or {}
        return {
            "enabled": self.config.endnote_export_enabled,
            "directory": str(self.config.endnote_cache_dir),
            "stats": index.get("stats", {}),
            "total": len(index.get("exported_papers", {})),
        }

    def batch_download(self, items: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for item in items:
            result = self.download_pdf(item["pmid"], item.get("download_url", ""))
            results.append({"pmid": item["pmid"], "result": result})
            time.sleep(random.uniform(1.0, 2.5))
        return results

    def system_check(self) -> Dict[str, Any]:
        system_info = {
            "platform": platform.system().lower(),
            "arch": platform.machine(),
            "isWindows": os.name == "nt",
            "isMacOS": platform.system() == "Darwin",
            "isLinux": platform.system() == "Linux",
        }

        tools = []
        if system_info["isWindows"]:
            tools.append({"name": "PowerShell", "available": shutil.which("powershell") is not None})
        else:
            for tool_name in ("wget", "curl"):
                tools.append({"name": tool_name, "available": shutil.which(tool_name) is not None})

        return {
            "system": system_info,
            "tools": tools,
            "recommended": "powershell" if system_info["isWindows"] else ("wget" if shutil.which("wget") else "curl"),
        }

