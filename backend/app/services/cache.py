"""
A1: Response Caching Service.

Caches LLM responses for frequently asked / identical questions using
Upstash Redis REST API (same pattern as rate_limit.py). Reduces LLM
cost and latency for repeat queries.

Gate: enable_response_cache (bool) in config.py
"""
import hashlib
import logging
import re
from urllib.parse import quote

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

CACHE_PREFIX = "response_cache"


def _normalize_query(query: str) -> str:
    """Lowercase, strip whitespace, remove punctuation for cache key normalization."""
    normalized = query.lower().strip()
    normalized = re.sub(r"[^\w\s]", "", normalized)
    return normalized.strip()


def _make_cache_key(user_id: str, query: str, conversation_id: str = "") -> str:
    """Create a deterministic cache key from user_id + conversation_id + normalized query."""
    normalized = _normalize_query(query)
    raw = f"{user_id}:{conversation_id}:{normalized}"
    hash_digest = hashlib.sha256(raw.encode()).hexdigest()
    return f"{CACHE_PREFIX}:{hash_digest}"


async def _upstash_command(*parts: str) -> dict:
    """Send a REST command to Upstash Redis."""
    settings = get_settings()
    base_url = settings.upstash_redis_rest_url.strip()
    token = settings.upstash_redis_rest_token.strip()
    url = f"{base_url}/{'/'.join(parts)}"
    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.get(
            url, headers={"Authorization": f"Bearer {token}"}
        )
        resp.raise_for_status()
        return resp.json()


async def get_cached_response(user_id: str, query: str, conversation_id: str = "") -> str | None:
    """Return cached answer if one exists, otherwise None."""
    settings = get_settings()
    if not settings.enable_response_cache:
        return None
    try:
        key = _make_cache_key(user_id, query, conversation_id)
        result = await _upstash_command("get", key)
        cached = result.get("result")
        return cached if cached else None
    except httpx.HTTPError as exc:
        logger.warning("Cache GET failed (cache degraded): %s", exc)
        return None


async def set_cached_response(user_id: str, query: str, response: str, conversation_id: str = "") -> None:
    """Cache the response with a TTL."""
    settings = get_settings()
    if not settings.enable_response_cache:
        return
    try:
        key = _make_cache_key(user_id, query, conversation_id)
        ttl = str(settings.response_cache_ttl_seconds)
        await _upstash_command("setex", key, ttl, quote(response, safe=""))
    except httpx.HTTPError as exc:
        logger.warning("Cache SET failed (cache degraded): %s", exc)


async def invalidate_user_cache(user_id: str) -> None:
    """
    Invalidate all cached responses for a user.
    Upstash REST doesn't support SCAN, so this is a best-effort no-op
    that logs the intent. Full cache invalidation would require a
    dedicated Redis instance with SCAN/lua support.
    """
    logger.info("Cache invalidation requested for user %s (not supported via Upstash REST)", user_id)