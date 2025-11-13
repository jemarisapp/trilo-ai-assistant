"""
Query Cache
Caches query results to avoid reprocessing similar queries
"""

from typing import Dict, Optional, Tuple
import time
from .query_normalizer import get_query_signature


class QueryCache:
    """
    Simple in-memory cache for query results
    Helps ensure consistent responses for similar queries
    """
    
    def __init__(self, max_size: int = 500, ttl_seconds: int = 3600):
        """
        Initialize query cache
        
        Args:
            max_size: Maximum number of cached entries
            ttl_seconds: Time-to-live for cache entries (default 1 hour)
        """
        self._cache: Dict[str, Tuple[str, float]] = {}  # signature -> (response, timestamp)
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._hits = 0
        self._misses = 0
    
    def get(self, query: str, server_id: str) -> Optional[str]:
        """
        Get cached response for query
        
        Args:
            query: User query
            server_id: Server ID (for server-specific caching)
            
        Returns:
            Cached response if found and not expired, None otherwise
        """
        # Create cache key (includes server_id for server-specific caching)
        signature = get_query_signature(query)
        cache_key = f"{server_id}:{signature}"
        
        # Check if in cache
        if cache_key not in self._cache:
            self._misses += 1
            return None
        
        response, timestamp = self._cache[cache_key]
        
        # Check if expired
        if time.time() - timestamp > self.ttl_seconds:
            # Expired, remove from cache
            del self._cache[cache_key]
            self._misses += 1
            return None
        
        # Cache hit
        self._hits += 1
        print(f"[Query Cache] HIT for '{query}' (signature: {signature})")
        return response
    
    def set(self, query: str, server_id: str, response: str):
        """
        Cache a query response
        
        Args:
            query: User query
            server_id: Server ID
            response: Response to cache
        """
        signature = get_query_signature(query)
        cache_key = f"{server_id}:{signature}"
        
        # Check cache size
        if len(self._cache) >= self.max_size:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        # Store with timestamp
        self._cache[cache_key] = (response, time.time())
        print(f"[Query Cache] STORE for '{query}' (signature: {signature})")
    
    def clear(self):
        """Clear all cached entries"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2)
        }
    
    def invalidate_pattern(self, pattern: str, server_id: str):
        """
        Invalidate cache entries matching a pattern
        Useful when data changes (e.g., team assignments change)
        
        Args:
            pattern: Pattern to match (e.g., "team_ownership")
            server_id: Server ID
        """
        keys_to_remove = []
        
        for cache_key in self._cache.keys():
            # Check if key matches server and pattern
            if cache_key.startswith(f"{server_id}:") and pattern in cache_key:
                keys_to_remove.append(cache_key)
        
        for key in keys_to_remove:
            del self._cache[key]
        
        if keys_to_remove:
            print(f"[Query Cache] Invalidated {len(keys_to_remove)} entries for pattern '{pattern}'")


# Global cache instance
_query_cache = QueryCache()


def get_query_cache() -> QueryCache:
    """Get the global query cache instance"""
    return _query_cache


def should_cache_query(query: str, response: str) -> bool:
    """
    Determine if a query/response should be cached
    
    Args:
        query: User query
        response: Bot response
        
    Returns:
        True if should cache, False otherwise
    """
    # Don't cache error responses
    error_indicators = ['⚠️', '❌', 'error', 'failed', 'couldn\'t']
    if any(indicator in response.lower() for indicator in error_indicators):
        return False
    
    # Don't cache very short responses (likely incomplete)
    if len(response) < 10:
        return False
    
    # Don't cache queries with attachments (images are dynamic)
    if 'image' in query.lower() or 'attachment' in query.lower():
        return False
    
    # Cache everything else
    return True




