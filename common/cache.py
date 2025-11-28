"""Simple TTL cache helpers for frequently accessed data."""
from __future__ import annotations

from typing import Generic, Optional, TypeVar

from cachetools import TTLCache

T = TypeVar("T")


class SimpleTTLCache(Generic[T]):
    def __init__(self, ttl: int, maxsize: int = 256) -> None:
        self._cache: TTLCache[str, T] = TTLCache(maxsize=maxsize, ttl=ttl)

    def get(self, key: str) -> Optional[T]:
        return self._cache.get(key)

    def set(self, key: str, value: T) -> None:
        self._cache[key] = value

    def pop(self, key: str) -> None:
        self._cache.pop(key, None)

    def clear(self) -> None:
        self._cache.clear()
