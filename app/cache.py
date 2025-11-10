import json
import os
from typing import Any, Optional

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
PRODUTOS_CACHE_TTL = int(os.getenv("PRODUTOS_CACHE_TTL", "60"))

_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> Optional[redis.Redis]:
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.Redis.from_url(REDIS_URL)
        except redis.RedisError:
            _redis_client = None
    return _redis_client


def cache_set(client: Optional[redis.Redis], key: str, value: Any, ttl: int = PRODUTOS_CACHE_TTL) -> None:
    if client is None:
        return
    try:
        payload = json.dumps(value)
        client.setex(key, ttl, payload)
    except (TypeError, ValueError, redis.RedisError):
        pass


def cache_get(client: Optional[redis.Redis], key: str):
    if client is None:
        return None
    try:
        data = client.get(key)
        if data is None:
            return None
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        return json.loads(data)
    except (json.JSONDecodeError, redis.RedisError, UnicodeDecodeError):
        return None


__all__ = ["get_redis_client", "cache_get", "cache_set", "PRODUTOS_CACHE_TTL"]
