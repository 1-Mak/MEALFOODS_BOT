"""Simple in-memory TTL cache for 1C data.

Keeps data in a plain dict. No external dependencies.
Thread-safe concerns are irrelevant — asyncio is single-threaded.
"""
from __future__ import annotations

import time
from typing import Any

_cache: dict[str, tuple[Any, float]] = {}  # {key: (data, expires_at)}


def get(key: str) -> Any | None:
    """Return cached value if it exists and has not expired."""
    entry = _cache.get(key)
    if entry is None:
        return None
    data, expires_at = entry
    if time.monotonic() > expires_at:
        return None
    return data


def get_stale(key: str) -> Any | None:
    """Return cached value even if expired (fallback when 1C is down)."""
    entry = _cache.get(key)
    if entry is None:
        return None
    return entry[0]


def set(key: str, data: Any, ttl: float) -> None:
    """Store value with a TTL in seconds."""
    _cache[key] = (data, time.monotonic() + ttl)


def invalidate(prefix: str) -> None:
    """Remove all keys that start with the given prefix."""
    keys = [k for k in _cache if k.startswith(prefix)]
    for k in keys:
        del _cache[k]


def clear() -> None:
    """Remove all cached entries."""
    _cache.clear()
