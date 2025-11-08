"""Cache utilities mirroring the Node MCP server behaviour."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class MemoryCacheStats:
    hits: int = 0
    misses: int = 0
    sets: int = 0
    evictions: int = 0


@dataclass
class MemoryCache:
    timeout_ms: int
    max_size: int
    data: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    stats: MemoryCacheStats = field(default_factory=MemoryCacheStats)

    def get(self, key: str, now_ms: int) -> Optional[Any]:
        entry = self.data.get(key)
        if not entry:
            self.stats.misses += 1
            return None
        if now_ms - entry["ts"] > self.timeout_ms:
            self.data.pop(key, None)
            self.stats.misses += 1
            return None
        self.stats.hits += 1
        return entry["value"]

    def set(self, key: str, value: Any, now_ms: int) -> None:
        if len(self.data) >= self.max_size:
            # remove oldest entry
            oldest_key = min(self.data.items(), key=lambda item: item[1]["ts"])[0]
            self.data.pop(oldest_key, None)
            self.stats.evictions += 1
        self.data[key] = {"value": value, "ts": now_ms}
        self.stats.sets += 1

    def clear(self) -> None:
        self.data.clear()
        self.stats = MemoryCacheStats()

    def clean_expired(self, now_ms: int) -> int:
        removed = [key for key, entry in self.data.items() if now_ms - entry["ts"] > self.timeout_ms]
        for key in removed:
            self.data.pop(key, None)
        return len(removed)


def read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    except Exception:
        return None


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)

