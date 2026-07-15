"""API key management for the public ForecastIQ API.

Design
------
* Each key has the form `fiq_<prefix>_<secret>` (e.g. `fiq_live_a3f...c91`).
  - The prefix is a short, non-secret identifier users can see (also
    used for the lookup index, so we don't have to scan all keys).
  - The secret is hashed (SHA-256) before being stored. The plain secret
    is shown to the user EXACTLY ONCE at creation time and never again.
* Keys are scoped per-user. The current model has a single "default" user
  (the self-hosted installation). In a multi-tenant deployment, the
  `owner` field would be the user id.
* Keys have a tier (free / pro / enterprise) that maps to rate limits.
  For self-hosted: `free` is the only tier but can be configured via env.
* Last-used timestamp is updated on each request (best-effort, async).

Storage
-------
* Keys index lives in `DATA_DIR/api_keys.json`:
    { "<key_id>": { "name", "prefix", "hash", "tier", "owner",
                     "scopes": [...], "created_at", "last_used_at",
                     "expires_at" (optional), "revoked": false } }
* Plain secret is NEVER written to disk.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import settings

logger = logging.getLogger(__name__)

# In-process rate limiter: { (key_id, minute_bucket): count }
_RATE_LIMIT_BUCKET: Dict[str, int] = {}
_RATE_LOCK = threading.Lock()


class ApiKeyTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# Default rate limits (requests per minute) per tier
TIER_LIMITS: Dict[ApiKeyTier, int] = {
    ApiKeyTier.FREE: 60,         # 60 req/min
    ApiKeyTier.PRO: 600,         # 600 req/min
    ApiKeyTier.ENTERPRISE: 6000, # 6000 req/min
}


@dataclass
class ApiKeyRecord:
    """A single API key record. The plain secret is NEVER stored —
    only its SHA-256 hash + a short prefix for human reference."""
    key_id: str
    name: str
    prefix: str           # human-visible, e.g. "fiq_live_a3f8c2"
    hash: str             # SHA-256 hex of the secret
    tier: ApiKeyTier = ApiKeyTier.FREE
    owner: str = "default"
    scopes: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    last_used_at: Optional[str] = None
    expires_at: Optional[str] = None
    revoked: bool = False
    # Usage stats (updated on each request, async)
    request_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["tier"] = self.tier.value
        return d

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ApiKeyRecord":
        d = dict(d)
        d["tier"] = ApiKeyTier(d.get("tier", "free"))
        return ApiKeyRecord(**d)

    def is_active(self) -> bool:
        if self.revoked:
            return False
        if self.expires_at:
            try:
                exp = datetime.fromisoformat(self.expires_at.rstrip("Z"))
                if datetime.utcnow() > exp:
                    return False
            except Exception as e:
                logger.warning("Failed to parse expiry date '%s': %s", self.expires_at, e)
                return False
            return True
        return True


class ApiKeyStore:
    """Persistent store of API keys."""

    INDEX_FILE = "api_keys.json"

    def __init__(self, data_dir: Optional[str] = None) -> None:
        self.data_dir = Path(data_dir or settings.DATA_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self.data_dir / self.INDEX_FILE
        self._lock = threading.RLock()
        if not self._index_path.exists():
            self._write_index({})

    @staticmethod
    def _read_json(path: Path) -> Dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _write_json(path: Path, data: Dict[str, Any]) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(tmp, path)

    def _write_index(self, data: Dict[str, Any]) -> None:
        self._write_json(self._index_path, data)

    def list_keys(self, owner: Optional[str] = None) -> List[ApiKeyRecord]:
        with self._lock:
            index = self._read_json(self._index_path)
        items = [ApiKeyRecord.from_dict(v) for v in index.values()]
        if owner:
            items = [k for k in items if k.owner == owner]
        items.sort(key=lambda k: k.created_at, reverse=True)
        return items

    def get(self, key_id: str) -> Optional[ApiKeyRecord]:
        with self._lock:
            index = self._read_json(self._index_path)
        entry = index.get(key_id)
        if not entry:
            return None
        return ApiKeyRecord.from_dict(entry)

    def get_by_prefix(self, prefix: str) -> Optional[ApiKeyRecord]:
        with self._lock:
            index = self._read_json(self._index_path)
        for v in index.values():
            if v.get("prefix") == prefix:
                return ApiKeyRecord.from_dict(v)
        return None

    def save(self, record: ApiKeyRecord) -> None:
        with self._lock:
            index = self._read_json(self._index_path)
            index[record.key_id] = record.to_dict()
            self._write_index(index)

    def delete(self, key_id: str) -> bool:
        with self._lock:
            index = self._read_json(self._index_path)
            if key_id not in index:
                return False
            index.pop(key_id, None)
            self._write_index(index)
        return True

    def increment_usage(self, key_id: str) -> None:
        with self._lock:
            index = self._read_json(self._index_path)
            entry = index.get(key_id)
            if not entry:
                return
            entry["request_count"] = int(entry.get("request_count", 0)) + 1
            entry["last_used_at"] = datetime.utcnow().isoformat() + "Z"
            self._write_index(index)


# ============================================================================
# Key generation + validation
# ============================================================================

def generate_api_key(
    name: str,
    owner: str = "default",
    tier: ApiKeyTier = ApiKeyTier.FREE,
    scopes: Optional[List[str]] = None,
    expires_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a new API key. Returns {record, plain_secret}.

    The plain secret is shown to the caller EXACTLY ONCE and never stored.
    """
    key_id = uuid.uuid4().hex
    # 32 random bytes -> 64 hex chars (256 bits of entropy)
    secret_bytes = secrets.token_bytes(32)
    secret = secret_bytes.hex()
    prefix = f"fiq_live_{key_id[:6]}"
    full_key = f"{prefix}_{secret}"
    record = ApiKeyRecord(
        key_id=key_id,
        name=name,
        prefix=prefix,
        hash=hashlib.sha256(secret.encode("utf-8")).hexdigest(),
        tier=tier,
        owner=owner,
        scopes=scopes or [],
        expires_at=expires_at,
    )
    store = _get_store()
    store.save(record)
    return {"record": record, "plain_key": full_key, "prefix": prefix}


def validate_api_key(full_key: str) -> Optional[ApiKeyRecord]:
    """Validate an API key from a request. Returns the record or None.

    The full key has the form `fiq_live_<6hex>_<64hex>`. We look up by
    prefix, then compare SHA-256 hashes (constant-time).
    """
    if not full_key or not isinstance(full_key, str):
        return None
    parts = full_key.split("_")
    if len(parts) < 4 or parts[0] != "fiq":
        return None
    prefix = "_".join(parts[:3])  # "fiq_live_xxxxxx"
    secret = parts[3]
    store = _get_store()
    record = store.get_by_prefix(prefix)
    if not record:
        return None
    if not record.is_active():
        return None
    expected = hashlib.sha256(secret.encode("utf-8")).hexdigest()
    # Constant-time compare
    if not _ct_eq(expected, record.hash):
        return None
    return record


def _ct_eq(a: str, b: str) -> bool:
    """Constant-time string comparison to thwart timing attacks."""
    if len(a) != len(b):
        return False
    result = 0
    for ca, cb in zip(a, b):
        result |= ord(ca) ^ ord(cb)
    return result == 0


# ============================================================================
# Rate limiting
# ============================================================================

def check_rate_limit(record: ApiKeyRecord) -> tuple[bool, int, int]:
    """Check if this key is within its rate limit. Returns (allowed, used, limit).

    Uses a fixed-window counter keyed by (key_id, minute). For self-hosted
    deployments this is sufficient. For multi-process deployments, swap in
    Redis (TODO if needed).
    """
    limit = TIER_LIMITS.get(record.tier, 60)
    now_minute = int(time.time() // 60)
    bucket_key = f"{record.key_id}:{now_minute}"
    with _RATE_LOCK:
        # GC: drop old buckets to avoid unbounded growth
        if len(_RATE_LIMIT_BUCKET) > 100_000:
            cutoff = now_minute - 5
            for k in list(_RATE_LIMIT_BUCKET.keys()):
                try:
                    bucket_min = int(k.split(":", 1)[1])
                    if bucket_min < cutoff:
                        _RATE_LIMIT_BUCKET.pop(k, None)
                except Exception as e:
                    logger.warning("Rate limiter GC failed to parse bucket key '%s': %s", k, e)
                    _RATE_LIMIT_BUCKET.pop(k, None)
        current = _RATE_LIMIT_BUCKET.get(bucket_key, 0)
        if current >= limit:
            return False, current, limit
        _RATE_LIMIT_BUCKET[bucket_key] = current + 1
        return True, current + 1, limit


# ============================================================================
# Singleton accessor
# ============================================================================

_store: Optional[ApiKeyStore] = None
_store_lock = threading.Lock()


def _get_store() -> ApiKeyStore:
    global _store
    with _store_lock:
        if _store is None:
            _store = ApiKeyStore()
    return _store


def get_api_key_store() -> ApiKeyStore:
    return _get_store()
