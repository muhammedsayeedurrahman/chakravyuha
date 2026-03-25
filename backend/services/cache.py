"""Pipeline cache — thread-safe LRU cache for classification + response results.

Keyed on (query_text, language). Cache hit skips classification through
translation layers entirely, giving instant responses for repeated queries.
"""

from __future__ import annotations

import hashlib
import logging
import threading
from collections import OrderedDict
from typing import Any

logger = logging.getLogger("chakravyuha")

_DEFAULT_MAXSIZE = 500


class PipelineCache:
    """Thread-safe LRU cache for pipeline responses.

    Immutable: get() returns cached values, put() stores new ones.
    Evicts least-recently-used entries when maxsize is exceeded.
    """

    def __init__(self, maxsize: int = _DEFAULT_MAXSIZE) -> None:
        self._maxsize = maxsize
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _make_key(query: str, language: str) -> str:
        """Create a deterministic cache key from query text and language."""
        raw = f"{query.strip().lower()}|{language}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, query: str, language: str) -> Any | None:
        """Return cached response or None on miss."""
        key = self._make_key(query, language)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._hits += 1
                logger.info("Cache HIT (%d hits, %d misses)", self._hits, self._misses)
                return self._cache[key]
            self._misses += 1
            return None

    def put(self, query: str, language: str, value: Any) -> None:
        """Store a response in the cache, evicting LRU if full."""
        key = self._make_key(query, language)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = value
                return
            self._cache[key] = value
            if len(self._cache) > self._maxsize:
                evicted_key, _ = self._cache.popitem(last=False)
                logger.debug("Cache evicted entry: %s", evicted_key[:12])

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    @property
    def size(self) -> int:
        """Current number of cached entries."""
        with self._lock:
            return len(self._cache)

    @property
    def stats(self) -> dict[str, int]:
        """Return cache hit/miss statistics."""
        with self._lock:
            return {"hits": self._hits, "misses": self._misses, "size": len(self._cache)}
