"""
Fixed-window rate limiting against Upstash Redis's REST API. REST
(rather than a persistent TCP connection) is the right fit here because
Render free instances cold-start and sleep -- a pooled Redis connection
wouldn't survive that cycle anyway, so paying the small per-request
HTTP overhead is actually simpler and more reliable.
"""
import time

import httpx
from fastapi import HTTPException, status

from app.config import get_settings


async def _upstash_command(*parts: str) -> dict:
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


async def check_rate_limit(user_id: str) -> None:
    settings = get_settings()
    window = int(time.time() // 60)  # 60-second fixed window
    key = f"ratelimit:{user_id}:{window}"

    result = await _upstash_command("incr", key)
    count = result.get("result", 0)
    if count == 1:
        await _upstash_command("expire", key, "65")

    if count > settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded ({settings.rate_limit_per_minute} requests/minute). Try again shortly.",
        )
