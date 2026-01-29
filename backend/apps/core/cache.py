"""
Cache utilities for CTrack.

Provides decorators and helpers for Redis caching.
"""

import hashlib
import json
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

from django.core.cache import cache

logger = logging.getLogger(__name__)


def cache_key(*args: Any, **kwargs: Any) -> str:
    """
    Generate a cache key from arguments.

    Serializes args/kwargs to JSON and returns MD5 hash.
    """
    key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return hashlib.md5(key_data.encode()).hexdigest()


def cached(timeout: int = 300, key_prefix: str = "") -> Callable:
    """
    Decorator to cache function results in Redis.

    Args:
        timeout: Cache TTL in seconds (default 5 min)
        key_prefix: Prefix for cache key

    Usage:
        @cached(timeout=300, key_prefix='project_statuses')
        def get_statuses(project_id):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = f"{key_prefix}:{cache_key(*args, **kwargs)}"
            result = cache.get(key)
            if result is None:
                result = func(*args, **kwargs)
                cache.set(key, result, timeout)
            return result

        return wrapper

    return decorator


def invalidate_cache_pattern(pattern: str) -> int:
    """
    Invalidate all cache keys matching a pattern.

    Note: This works with Redis backend using SCAN + DELETE.
    For other backends, this is a no-op.

    Args:
        pattern: Pattern to match (e.g., 'project_statuses:*')

    Returns:
        Number of keys deleted (0 if not supported)
    """
    try:
        client = cache.client.get_client()
        keys = []
        cursor = 0
        while True:
            cursor, found_keys = client.scan(cursor, match=pattern, count=100)
            keys.extend(found_keys)
            if cursor == 0:
                break
        if keys:
            return client.delete(*keys)
        return 0
    except (AttributeError, Exception) as e:
        logger.warning(f"Cache pattern invalidation not supported: {e}")
        return 0


def invalidate_project_cache(project_id: str) -> None:
    """
    Invalidate all cached data for a project.

    Call this when project settings, statuses, or types are modified.
    """
    patterns = [
        f"project_statuses:{project_id}:*",
        f"project_types:{project_id}:*",
        f"project_data:{project_id}:*",
    ]
    for pattern in patterns:
        invalidate_cache_pattern(pattern)


def get_or_set(key: str, default_func: Callable, timeout: int = 300) -> Any:
    """
    Get value from cache or compute and store it.

    Args:
        key: Cache key
        default_func: Function to call if cache miss
        timeout: Cache TTL in seconds

    Returns:
        Cached or computed value
    """
    result = cache.get(key)
    if result is None:
        result = default_func()
        cache.set(key, result, timeout)
    return result
