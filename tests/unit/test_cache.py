"""Unit tests for cache utilities."""
import time

import pytest

from common.cache import SimpleTTLCache


class TestSimpleTTLCache:
    """Test the TTL cache implementation."""

    def test_cache_set_and_get(self):
        """Test basic set and get operations."""
        cache = SimpleTTLCache[str](ttl=60)
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_cache_get_nonexistent_key(self):
        """Test getting a key that doesn't exist returns None."""
        cache = SimpleTTLCache[str](ttl=60)
        
        assert cache.get("nonexistent") is None

    def test_cache_overwrite_value(self):
        """Test overwriting an existing key."""
        cache = SimpleTTLCache[str](ttl=60)
        
        cache.set("key1", "value1")
        cache.set("key1", "value2")
        
        assert cache.get("key1") == "value2"

    def test_cache_ttl_expiration(self):
        """Test that values expire after TTL."""
        cache = SimpleTTLCache[str](ttl=1)  # 1 second TTL
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(1.1)
        
        assert cache.get("key1") is None

    def test_cache_pop(self):
        """Test removing a key from cache."""
        cache = SimpleTTLCache[str](ttl=60)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        cache.pop("key1")
        
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_cache_pop_nonexistent(self):
        """Test popping a nonexistent key doesn't raise error."""
        cache = SimpleTTLCache[str](ttl=60)
        
        # Should not raise exception
        cache.pop("nonexistent")

    def test_cache_clear(self):
        """Test clearing all cache entries."""
        cache = SimpleTTLCache[str](ttl=60)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_cache_with_different_types(self):
        """Test cache with different value types."""
        int_cache = SimpleTTLCache[int](ttl=60)
        int_cache.set("count", 42)
        assert int_cache.get("count") == 42
        
        dict_cache = SimpleTTLCache[dict](ttl=60)
        dict_cache.set("data", {"name": "test", "value": 123})
        assert dict_cache.get("data") == {"name": "test", "value": 123}

    def test_cache_maxsize(self):
        """Test cache respects maxsize limit."""
        cache = SimpleTTLCache[str](ttl=60, maxsize=2)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # Should evict oldest
        
        # With LRU eviction, key1 should be removed
        # Note: TTLCache uses LRU when maxsize is reached
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
