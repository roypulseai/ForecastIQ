"""Internal API-key management endpoints for the UI.

These let users create, list, rename, and revoke their API keys. The
plain secret is shown exactly once at creation time.

Mounted at /api/v1/api-keys (no prefix on the router — main.py applies it).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException

from ...core.api_keys import (
    ApiKeyRecord,
    ApiKeyTier,
    generate_api_key,
    get_api_key_store,
)
from ...core.users import User
from ...core.utils import to_python
from ...core.config import settings
from ...middleware.auth import require_jwt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api-keys")


@router.get("")
async def list_keys(user: User = Depends(require_jwt)) -> Dict[str, Any]:
    """List all API keys. Plain secrets are NEVER returned."""
    store = get_api_key_store()
    items = store.list_keys()
    # Strip the hash from the public view (defense-in-depth)
    public = []
    for r in items:
        d = r.to_dict()
        d.pop("hash", None)
        public.append(d)
    return to_python({"items": public, "total": len(items)})


@router.post("")
async def create_key(
    payload: Dict[str, Any] = Body(...),
    user: User = Depends(require_jwt),
) -> Dict[str, Any]:
    """Create a new API key.

    Request body:
        * `name` (string, required) — human label
        * `tier` (string, default 'free') — 'free' | 'pro' | 'enterprise'
        * `scopes` (list of strings, optional) — reserved for future use
        * `expires_at` (ISO datetime string, optional)

    Returns:
        * `record` — the saved record (no secret)
        * `plain_key` — the full key. THIS IS SHOWN ONLY ONCE.
        * `prefix` — short identifier for easy reference
    """
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "name is required")
    tier_str = (payload.get("tier") or settings.DEFAULT_API_KEY_TIER).lower()
    try:
        tier = ApiKeyTier(tier_str)
    except ValueError:
        raise HTTPException(400, f"Invalid tier. Allowed: {[t.value for t in ApiKeyTier]}")
    scopes = payload.get("scopes") or []
    expires_at = payload.get("expires_at")

    result = generate_api_key(
        name=name, tier=tier, scopes=scopes, expires_at=expires_at,
    )
    record: ApiKeyRecord = result["record"]
    return to_python({
        "record": {**record.to_dict(), "hash": "***"},  # never expose the hash
        "plain_key": result["plain_key"],
        "prefix": result["prefix"],
        "warning": (
            "Store this key now. The plain secret cannot be retrieved later — "
            "only the prefix and a SHA-256 hash are kept on disk."
        ),
    })


@router.patch("/{key_id}")
async def update_key(
    key_id: str,
    payload: Dict[str, Any] = Body(...),
    user: User = Depends(require_jwt),
) -> Dict[str, Any]:
    """Update a key's name, tier, scopes, or expiry. To revoke, use DELETE."""
    store = get_api_key_store()
    rec = store.get(key_id)
    if not rec:
        raise HTTPException(404, "API key not found")
    if "name" in payload:
        rec.name = str(payload["name"]).strip() or rec.name
    if "tier" in payload:
        try:
            rec.tier = ApiKeyTier(str(payload["tier"]).lower())
        except ValueError:
            raise HTTPException(400, f"Invalid tier")
    if "scopes" in payload:
        rec.scopes = list(payload["scopes"])
    if "expires_at" in payload:
        rec.expires_at = payload["expires_at"]
    store.save(rec)
    d = rec.to_dict()
    d.pop("hash", None)
    return to_python(d)


@router.delete("/{key_id}")
async def revoke_key(key_id: str, user: User = Depends(require_jwt)) -> Dict[str, Any]:
    """Permanently revoke a key. Cannot be undone — the caller must create
    a new key to restore access."""
    store = get_api_key_store()
    rec = store.get(key_id)
    if not rec:
        raise HTTPException(404, "API key not found")
    rec.revoked = True
    store.save(rec)
    return {"message": "API key revoked", "key_id": key_id, "prefix": rec.prefix}


@router.get("/tiers")
async def list_tiers(user: User = Depends(require_jwt)) -> Dict[str, Any]:
    """Return the available tiers and their rate limits."""
    from ...core.api_keys import TIER_LIMITS
    return to_python({
        "tiers": [
            {
                "tier": t.value,
                "rate_limit_per_minute": limit,
                "description": {
                    "free": "Default tier for self-hosted installations.",
                    "pro": "For higher-throughput scripts and notebooks.",
                    "enterprise": "For production pipelines and large teams.",
                }.get(t.value, ""),
            }
            for t, limit in TIER_LIMITS.items()
        ]
    })
