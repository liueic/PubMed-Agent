"""HTTP utilities for PubMed MCP backend."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass
class ProxyConfig:
    enabled: bool
    http_proxy: Optional[str]
    https_proxy: Optional[str]
    username: Optional[str]
    password: Optional[str]

    def as_requests_proxies(self) -> Optional[Dict[str, str]]:
        if not self.enabled:
            return None

        proxies: Dict[str, str] = {}
        if self.http_proxy:
            proxies["http"] = self._inject_credentials(self.http_proxy)
        if self.https_proxy:
            proxies["https"] = self._inject_credentials(self.https_proxy)
        if not proxies:
            return None
        return proxies

    def _inject_credentials(self, url: str) -> str:
        if self.username and self.password and "@" not in url.split("//", 1)[-1]:
            scheme, remainder = url.split("//", 1)
            return f"{scheme}//{self.username}:{self.password}@{remainder}"
        return url


class PubMedHTTPClient:
    """Minimal HTTP client with rate limiting and proxy support."""

    def __init__(
        self,
        proxy_config: ProxyConfig,
        request_timeout_ms: int,
        rate_limit_delay_ms: int,
        proxy_timeout: int,
        proxy_retry_count: int,
    ) -> None:
        self._rate_limit_delay = rate_limit_delay_ms / 1000.0
        self._timeout = request_timeout_ms / 1000.0
        self._last_request_ts = 0.0
        self._lock = threading.Lock()

        self._session = requests.Session()

        retry = Retry(
            total=proxy_retry_count,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry, pool_maxsize=20, pool_block=True, pool_connections=20)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

        self._session.trust_env = False
        self._session.timeout = proxy_timeout

        self._proxies = proxy_config.as_requests_proxies()

    def _enforce_rate_limit(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_ts
            if elapsed < self._rate_limit_delay:
                time.sleep(self._rate_limit_delay - elapsed)
            self._last_request_ts = time.monotonic()

    def get(self, url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> requests.Response:
        self._enforce_rate_limit()
        response = self._session.get(
            url,
            params=params,
            headers=headers,
            timeout=self._timeout,
            proxies=self._proxies,
        )
        response.raise_for_status()
        return response

    def post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        self._enforce_rate_limit()
        response = self._session.post(
            url,
            data=data,
            json=json,
            headers=headers,
            timeout=self._timeout,
            proxies=self._proxies,
        )
        response.raise_for_status()
        return response

