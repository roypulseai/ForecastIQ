# Managing API Keys

API keys let you call ForecastIQ from notebooks, scripts, ETL pipelines, and other tools. The key is a secret credential — treat it like a password.

## How keys work

A ForecastIQ API key has the form:

```
fiq_live_<6-char-prefix>_<64-char-secret>
       └─ prefix ─┘  └────── secret ──────┘
```

- **`fiq_live_`** — fixed, identifies this as a ForecastIQ key
- **`<prefix>`** — 6 hex characters. Human-visible in the UI. Used to tell keys apart.
- **`<secret>`** — 64 hex characters (256 bits of entropy). The actual credential.

The **plain secret is shown only once** — at creation time. The server stores only a SHA-256 hash of the secret. If you lose it, you can't retrieve it; you must create a new key.

## Creating a key

### In the UI

1. Go to **API** in the top navigation (or visit `/api-keys`).
2. Click **New API key**.
3. Fill in:
   - **Name** — a human label, e.g. `My notebook`, `Production ETL`, `Team dashboard`
   - **Tier** — `free` (60 req/min), `pro` (600 req/min), or `enterprise` (6,000 req/min)
   - **Expires** (optional) — an expiry date. After this date the key is rejected.
4. Click **Create key**.
5. **Copy the key immediately and store it somewhere safe.** A modal will show it; once you close it, it's gone forever.
6. Confirm by clicking "I have stored this key".

### Programmatically (internal endpoint)

The internal `/api/v1/api-keys` endpoints let you manage keys from the UI. These are mounted under `/api/v1/*` (the internal surface) and don't require an API key themselves — they assume the request is from the same self-hosted browser session.

```bash
# Create a key
curl -X POST -H "Content-Type: application/json" \
  -d '{"name": "My ETL", "tier": "pro"}' \
  http://localhost:8000/api/v1/api-keys

# Response
{
  "record": {
    "key_id": "abc123def456...",
    "name": "My ETL",
    "prefix": "fiq_live_abc123",
    "tier": "pro",
    "owner": "default",
    "scopes": [],
    "created_at": "2026-07-07T12:00:00Z",
    ...
  },
  "plain_key": "fiq_live_abc123_4f8b2c1e...longhexsecret...",
  "prefix": "fiq_live_abc123",
  "warning": "Store this key now. The plain secret cannot be retrieved later — only the prefix and a SHA-256 hash are kept on disk."
}
```

> **Save the `plain_key` immediately.** This is the only time it will be returned.

## Listing keys

```bash
curl http://localhost:8000/api/v1/api-keys
```

The response includes each key's metadata but **never** the plain secret:

```json
{
  "items": [
    {
      "key_id": "abc123def456",
      "name": "My ETL",
      "prefix": "fiq_live_abc123",
      "tier": "pro",
      "owner": "default",
      "scopes": [],
      "created_at": "2026-07-07T12:00:00Z",
      "last_used_at": "2026-07-07T15:23:11Z",
      "expires_at": null,
      "revoked": false,
      "request_count": 142
    }
  ],
  "total": 1
}
```

## Editing a key

```bash
curl -X PATCH -H "Content-Type: application/json" \
  -d '{"name": "Renamed", "tier": "enterprise"}' \
  http://localhost:8000/api/v1/api-keys/abc123def456
```

Editable fields: `name`, `tier`, `scopes`, `expires_at`. To change the secret itself, revoke the old key and create a new one.

## Revoking a key

```bash
curl -X DELETE http://localhost:8000/api/v1/api-keys/abc123def456
```

This immediately invalidates the key. Any request using it gets `401 Unauthorized`. The record stays in the index (marked `revoked: true`) for audit purposes but cannot be re-enabled.

## Tiers and rate limits

```bash
curl http://localhost:8000/api/v1/api-keys/tiers
```

| Tier | Requests / minute | When to use |
| --- | --- | --- |
| `free` | 60 | Default. Enough for occasional scripts, exploratory notebooks. |
| `pro` | 600 | Frequent use, batch jobs, dashboard refresh, multi-user team. |
| `enterprise` | 6,000 | Production pipelines, large teams, many parallel consumers. |

The limit is per-key, per-minute, using a fixed window. If you hit the limit you get `429 Too Many Requests` with a `Retry-After: 60` header. Every successful response includes `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Tier` headers.

## Storage and security

- Keys are stored at `DATA_DIR/api_keys.json` (`api_keys.json` is the index). The plain secret is **never** written to disk.
- The server stores `hash = SHA-256(secret)`. When a request comes in, it looks up by prefix, recomputes the hash, and uses constant-time comparison to thwart timing attacks.
- The key prefix is **not** a secret — it appears in the UI and in audit logs.
- The full key is what authenticates. Treat it as a credential: don't commit it to git, don't put it in URLs, don't email it.
- If you suspect a key has leaked, **revoke it immediately** and create a new one.

## Operational tips

- **One key per consumer.** Don't share keys between a notebook and an ETL job. If one leaks, you can revoke just that one.
- **Use the smallest tier you need.** The free tier is enough for ad-hoc exploration.
- **Set an expiry for shared environments.** A 90-day expiry forces rotation.
- **Watch the `request_count` field.** A sudden jump may indicate something is wrong.
- **Tag your keys with names that explain the consumer**, e.g. `notebook-mary`, `etl-nightly`, `dashboard-prod`.
- **Check `last_used_at`** to find keys that are no longer in use — candidates for revocation.

## Troubleshooting

**`401 Unauthorized: Missing API key`** — you didn't pass the `Authorization: Bearer ...` or `X-API-Key` header.

**`401 Unauthorized: Invalid or revoked API key`** — the key doesn't exist, was revoked, or has expired. Check the key in the UI.

**`429 Too Many Requests`** — you've exceeded your tier's per-minute limit. Wait a minute, or upgrade the tier via PATCH.

**`Public API not enabled`** — if `PUBLIC_API_ENABLED=false` is set in the backend config, all `/v1/*` requests are accepted without a key (internal mode). Set it to `true` to enforce authentication.

## See also

- [API.md](./API.md) — full API reference
- [DATA_FORMAT.md](./DATA_FORMAT.md) — CSV column formats
- [MODELS.md](./MODELS.md) — model registry and persistence
