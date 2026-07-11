"""Authentication middleware for the public API.

Two auth surfaces:
    1. The UI (browser) — uses session-like access via the existing SPA.
       No API key required for /api/v1/* when CORS allows the origin.
    2. The public API at /v1/* — REQUIRES an API key in the
       `Authorization: Bearer <key>` header. The key is validated by
       `validate_api_key` and rate-limited by tier.

When the public API is enabled, the dependency `require_api_key` is
applied to every /v1/* route. If the key is invalid, the request
returns 401 with a clear WWW-Authenticate header.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from .api_keys import (
    ApiKeyRecord,
    TIER_LIMITS,
    check_rate_limit,
    get_api_key_store,
    validate_api_key,
)

logger = logging.getLogger(__name__)


# Allow disabling auth for self-hosted single-user mode by setting
# FORECASTIQ_PUBLIC_API_DISABLED=true (defaults to false = API enabled).
def _public_api_enabled() -> bool:
    from .config import settings
    return bool(getattr(settings, "PUBLIC_API_ENABLED", True))


async def require_api_key(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> ApiKeyRecord:
    """FastAPI dependency: extracts and validates the API key from the
    request headers. Returns the resolved ApiKeyRecord on success,
    raises HTTPException(401/429) on failure.

    Accepted formats:
        Authorization: Bearer fiq_live_xxxxxx_secretsecret...
        X-API-Key: fiq_live_xxxxxx_secretsecret...
    """
    if not _public_api_enabled():
        # If public API is disabled, return a synthetic "internal" key
        return ApiKeyRecord(
            key_id="internal",
            name="internal",
            prefix="internal",
            hash="",
        )

    full_key: Optional[str] = None
    if authorization and authorization.lower().startswith("bearer "):
        full_key = authorization[7:].strip()
    elif x_api_key:
        full_key = x_api_key.strip()

    if not full_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Missing API key. Pass it as "
                "'Authorization: Bearer fiq_live_...' or "
                "'X-API-Key: fiq_live_...'."
            ),
            headers={"WWW-Authenticate": 'Bearer realm="ForecastIQ"'},
        )

    record = validate_api_key(full_key)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key.",
            headers={"WWW-Authenticate": 'Bearer realm="ForecastIQ"'},
        )

    # Rate limit
    allowed, used, limit = check_rate_limit(record)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Rate limit exceeded for tier '{record.tier.value}': "
                f"{used}/{limit} requests/minute. "
                "Wait a minute or upgrade your plan."
            ),
            headers={
                "Retry-After": "60",
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
            },
        )

    # Best-effort: increment usage counter (don't block request on this)
    try:
        get_api_key_store().increment_usage(record.key_id)
    except Exception as e:
        logger.debug("Failed to increment usage: %s", e)

    return record


# Optional dependency for routes that work both with and without auth
async def optional_api_key(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> Optional[ApiKeyRecord]:
    """Like require_api_key but returns None instead of raising on
    missing/invalid keys. Use for endpoints that have both an internal
    (UI) and external (API) view of the same resource."""
    if not _public_api_enabled():
        return None
    if not authorization and not x_api_key:
        return None
    try:
        return await require_api_key(authorization=authorization, x_api_key=x_api_key)
    except HTTPException:
        return None


# Inject rate-limit headers into successful responses
def rate_limit_headers(record: ApiKeyRecord) -> dict:
    """Return headers to add to successful API responses, exposing the
    current rate-limit state to the client."""
    limit = TIER_LIMITS.get(record.tier, 60)
    return {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(max(0, limit - _current_count(record))),
        "X-RateLimit-Tier": record.tier.value,
    }


def _current_count(record: ApiKeyRecord) -> int:
    """Best-effort current count for the key (current minute)."""
    try:
        from .api_keys import _RATE_LIMIT_BUCKET, _RATE_LOCK
        import time
        now_minute = int(time.time() // 60)
        bucket_key = f"{record.key_id}:{now_minute}"
        with _RATE_LOCK:
            return _RATE_LIMIT_BUCKET.get(bucket_key, 0)
    except Exception as e:
        logger.warning("Rate limit count retrieval failed: %s", e)
        return 0
