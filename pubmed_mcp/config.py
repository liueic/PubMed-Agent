"""Configuration helpers for the internal PubMed MCP backend."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class PubMedMCPConfig:
    """Runtime configuration values for the PubMed MCP backend."""

    # PubMed credentials
    pubmed_api_key: Optional[str]
    pubmed_email: Optional[str]
    pubmed_tool_name: str

    # Query behaviour
    abstract_mode: str
    abstract_max_chars: int
    fulltext_mode: str
    fulltext_enabled: bool
    fulltext_auto_download: bool
    endnote_export_enabled: bool

    # Rate limiting / timeout
    rate_limit_delay_ms: int
    request_timeout_ms: int

    # Cache paths
    cache_dir: Path
    paper_cache_dir: Path
    fulltext_cache_dir: Path
    endnote_cache_dir: Path
    cache_version: str
    paper_cache_expiry_ms: int
    fulltext_cache_expiry_ms: int
    max_pdf_size_bytes: int

    # Memory cache tuning
    cache_timeout_ms: int
    cache_max_size: int

    # Proxy configuration
    proxy_enabled: bool
    http_proxy: Optional[str]
    https_proxy: Optional[str]
    proxy_username: Optional[str]
    proxy_password: Optional[str]
    proxy_timeout: int
    proxy_retry_count: int

    @classmethod
    def from_env(cls, base_path: Optional[Path] = None) -> "PubMedMCPConfig":
        """Read configuration from environment variables."""

        def _bool_env(name: str, default: str = "false") -> bool:
            value = os.getenv(name, default)
            return value.lower() in {"1", "true", "yes", "enabled", "on"}

        base_dir = Path(base_path or os.getcwd())
        cache_dir = Path(os.getenv("PUBMED_MCP_CACHE_DIR", base_dir / "cache"))

        abstract_mode = os.getenv("ABSTRACT_MODE", "quick").lower()
        if abstract_mode not in {"quick", "deep"}:
            abstract_mode = "quick"

        fulltext_mode = os.getenv("FULLTEXT_MODE", "disabled").lower()
        fulltext_enabled = fulltext_mode in {"enabled", "auto"}
        fulltext_auto_download = fulltext_mode == "auto"

        endnote_export_enabled = _bool_env("ENDNOTE_EXPORT", "enabled")

        return cls(
            pubmed_api_key=os.getenv("PUBMED_API_KEY"),
            pubmed_email=os.getenv("PUBMED_EMAIL"),
            pubmed_tool_name=os.getenv("PUBMED_TOOL_NAME", "pubmed_agent"),
            abstract_mode=abstract_mode,
            abstract_max_chars=6000 if abstract_mode == "deep" else 1500,
            fulltext_mode=fulltext_mode,
            fulltext_enabled=fulltext_enabled,
            fulltext_auto_download=fulltext_auto_download,
            endnote_export_enabled=endnote_export_enabled,
            rate_limit_delay_ms=int(os.getenv("PUBMED_RATE_LIMIT_DELAY_MS", "334")),
            request_timeout_ms=int(os.getenv("PUBMED_REQUEST_TIMEOUT_MS", "30000")),
            cache_dir=cache_dir,
            paper_cache_dir=cache_dir / "papers",
            fulltext_cache_dir=cache_dir / "fulltext",
            endnote_cache_dir=cache_dir / "endnote",
            cache_version=os.getenv("PUBMED_CACHE_VERSION", "1.0"),
            paper_cache_expiry_ms=int(os.getenv("PUBMED_PAPER_CACHE_EXPIRY_MS", str(30 * 24 * 60 * 60 * 1000))),
            fulltext_cache_expiry_ms=int(os.getenv("PUBMED_FULLTEXT_CACHE_EXPIRY_MS", str(90 * 24 * 60 * 60 * 1000))),
            max_pdf_size_bytes=int(os.getenv("PUBMED_MAX_PDF_SIZE_BYTES", str(50 * 1024 * 1024))),
            cache_timeout_ms=int(os.getenv("PUBMED_MEMORY_CACHE_TIMEOUT_MS", str(5 * 60 * 1000))),
            cache_max_size=int(os.getenv("PUBMED_MEMORY_CACHE_MAX_SIZE", "100")),
            proxy_enabled=_bool_env("PROXY_ENABLED", "disabled"),
            http_proxy=os.getenv("HTTP_PROXY") or os.getenv("http_proxy"),
            https_proxy=os.getenv("HTTPS_PROXY") or os.getenv("https_proxy"),
            proxy_username=os.getenv("PROXY_USERNAME"),
            proxy_password=os.getenv("PROXY_PASSWORD"),
            proxy_timeout=int(os.getenv("PROXY_TIMEOUT", "30")),
            proxy_retry_count=int(os.getenv("PROXY_RETRY_COUNT", "3")),
        )


def ensure_directories(cfg: PubMedMCPConfig) -> None:
    """Create cache directories if they do not already exist."""

    cfg.cache_dir.mkdir(parents=True, exist_ok=True)
    cfg.paper_cache_dir.mkdir(parents=True, exist_ok=True)
    cfg.fulltext_cache_dir.mkdir(parents=True, exist_ok=True)
    cfg.endnote_cache_dir.mkdir(parents=True, exist_ok=True)

