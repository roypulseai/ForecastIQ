# ForecastIQ Public API

A versioned, API-key-authenticated HTTP API for programmatically interacting with ForecastIQ — for notebooks, scripts, ETL pipelines, BI tools, and other integrations.

- **Base URL**: `http://<your-host>/v1`
- **Auth**: `Authorization: Bearer fiq_live_...` or `X-API-Key: fiq_live_...`
- **Format**: JSON request/response
- **Versioning**: URL-based (`/v1/...`). Breaking changes will be released as `/v2/...` with a deprecation period for `/v1`.
- **Interactive docs**: `http://<your-host>/docs` (Swagger UI) and `/redoc`
- **OpenAPI spec**: `http://<your-host>/openapi.json`

## 1. Quickstart

```bash
# 1. Create an API key in the UI: Settings → API keys → New API key
#    (or via the internal API: see "Managing API keys" below)

# 2. Use it in a request
curl -H "Authorization: Bearer fiq_live_abc123_yoursecret..." \
     http://localhost:8000/v1/files
```

```python
import requests
BASE = "http://localhost:8000/v1"
HEADERS = {"Authorization": "Bearer fiq_live_abc123_yoursecret..."}

# List uploaded files
r = requests.get(f"{BASE}/files", headers=HEADERS)
print(r.json())
```

```javascript
const BASE = "http://localhost:8000/v1";
const HEADERS = { Authorization: "Bearer fiq_live_abc123_yoursecret..." };
const r = await fetch(`${BASE}/files`, { headers: HEADERS });
console.log(await r.json());
```

## 2. Authentication

All `/v1/*` endpoints require a valid API key. Two header formats are accepted:

| Header | Value |
| --- | --- |
| `Authorization` | `Bearer fiq_live_<prefix>_<secret>` |
| `X-API-Key` | `fiq_live_<prefix>_<secret>` |

The key has three parts:
- `fiq_live_` — fixed prefix
- `<prefix>` — 6-character identifier (e.g. `a3f8c2`). Visible in the UI; helps you tell keys apart.
- `<secret>` — 64 hex characters. Shown ONCE at creation time. Stored as a SHA-256 hash on the server.

A missing or invalid key returns `401 Unauthorized`. A revoked or expired key also returns 401. The response includes a `WWW-Authenticate: Bearer realm="ForecastIQ"` header.

### Tiers and rate limits

Each key has a tier that determines its per-minute request budget:

| Tier | Requests / minute | Typical use |
| --- | --- | --- |
| `free` | 60 | Default for self-hosted. Enough for ad-hoc scripts. |
| `pro` | 600 | Frequent use, dashboards, batch jobs. |
| `enterprise` | 6,000 | Production pipelines, many users. |

The server enforces a fixed-window counter (per minute). When you hit the limit you get `429 Too Many Requests` with `Retry-After: 60`. Every successful response includes:

- `X-RateLimit-Limit` — the configured limit for this key's tier
- `X-RateLimit-Remaining` — requests left in the current minute
- `X-RateLimit-Tier` — your tier name

## 3. Common conventions

### Pagination

List endpoints accept `limit` (1–200, default 50) and `offset` (≥0). The response includes `total`, `limit`, `offset` so you can paginate. Example:

```bash
curl -H "Authorization: Bearer ..." \
  "http://localhost:8000/v1/forecasts?limit=20&offset=0"
```

```json
{
  "items": [...],
  "total": 47,
  "limit": 20,
  "offset": 0
}
```

### Async forecasts

Long forecasts (large data + multiple models) can take 30–90 seconds. To avoid blocking, POST with `?async=true`:

```bash
# Submit
curl -X POST -H "Authorization: Bearer ..." -H "Content-Type: application/json" \
  -d '{"name":"My forecast", "target_column":"value", "date_column":"date", "frequency":"D", "horizon":30, "models":["prophet","lightgbm"], "include_media_plan":false, "include_promotions":false, "include_holidays":false, "include_events":false, "include_weather":false, "include_competitor":false, "include_economic":false}' \
  "http://localhost:8000/v1/forecast?async=true"

# Response
{"job_id": "abc123...", "status": "pending", "message": "Forecast submitted. Poll /v1/jobs/{job_id} for status."}

# Poll
curl -H "Authorization: Bearer ..." http://localhost:8000/v1/jobs/abc123
# {"job_id": "abc123", "status": "running", "progress": 0.45, "message": "Trained 3/7 models"}

# Block until done
curl -H "Authorization: Bearer ..." http://localhost:8000/v1/jobs/abc123/result
# {"job_id": "abc123", "status": "completed", "result": {...full forecast...}}
```

### File types

`file_type` must be one of: `sales`, `media_plan`, `promotions`, `holidays`, `events`, `weather`, `competitor`, `economic`.

### Model types

`models` array may contain: `arima`, `sarimax`, `prophet`, `lightgbm`, `xgboost`, `wma`, `ets`, `theta`, `stl`. The special value `ensemble` may appear in results when ensemble is enabled.

## 4. Endpoints

### 4.1 Files

#### `POST /v1/files/upload/{file_type}`
Upload a CSV or Excel file (max 100 MB). The file is parsed, normalized, and stored.

```bash
curl -X POST -H "Authorization: Bearer ..." \
  -F "file=@sales.csv" \
  http://localhost:8000/v1/files/upload/sales
```

Response (200):
```json
{
  "file_id": "abc123def456",
  "filename": "sales.csv",
  "type": "sales",
  "size": 85420,
  "row_count": 365,
  "columns": ["date", "value", "sku", "store"],
  "column_mapping": {"date": "date", "value": "value"},
  "warnings": [],
  "status": "ready",
  "memory_mb": 0.13
}
```

#### `GET /v1/files`
List uploaded files. Query: `file_type`, `limit`, `offset`.

#### `GET /v1/files/{file_id}`
Get file metadata.

#### `GET /v1/files/{file_id}/data`
Get the actual rows. Query: `limit` (default 5000, max 50000), `offset`.

```bash
curl -H "Authorization: Bearer ..." \
  "http://localhost:8000/v1/files/abc123/data?limit=100&offset=0"
```

```json
{
  "file_id": "abc123",
  "columns": ["date", "value"],
  "rows": [
    {"date": "2024-01-01", "value": 100.5},
    ...
  ],
  "total_rows": 365,
  "returned_rows": 100,
  "offset": 0,
  "limit": 100
}
```

#### `DELETE /v1/files/{file_id}`
Delete a file and its parsed data. The `file_id` is no longer usable.

### 4.2 Analysis

#### `POST /v1/analyze?file_id=...`
Compute data characteristics and model recommendations for a sales file. Use the returned `validation.date_column` and `validation.value_column` when configuring a forecast.

```bash
curl -X POST -H "Authorization: Bearer ..." \
  "http://localhost:8000/v1/analyze?file_id=abc123"
```

```json
{
  "validation": {
    "valid": true,
    "errors": [],
    "warnings": [],
    "date_column": "date",
    "value_column": "value",
    "row_count": 365,
    "frequency": "D",
    "extra_columns": ["sku", "store"]
  },
  "data_characteristics": {
    "length": 365,
    "mean": 100.5,
    "std": 25.3,
    "cv": 0.25,
    "trend": "increasing",
    "seasonality": "weekly",
    "stationarity": false,
    "outliers_pct": 1.2,
    "missing_pct": 0.0,
    "min_date": "2024-01-01",
    "max_date": "2024-12-30"
  },
  "model_recommendations": [
    {"model": "prophet", "score": 0.92, "reason": "Detected weekly seasonality"},
    {"model": "sarimax", "score": 0.85, "reason": "Captures seasonal patterns"}
  ],
  "memory_mb": 0.13
}
```

### 4.3 Forecasts

#### `POST /v1/forecast`
Train new models and produce a forecast. Request body:

```json
{
  "name": "Q1 2025 forecast",
  "target_column": "value",
  "date_column": "date",
  "frequency": "D",
  "horizon": 30,
  "models": ["prophet", "lightgbm", "theta"],
  "parameters": {
    "prophet": {"seasonality_mode": "additive"},
    "lightgbm": {"n_estimators": 200, "learning_rate": 0.05}
  },
  "ensemble_models": ["prophet", "lightgbm"],
  "include_media_plan": true,
  "include_promotions": true,
  "include_holidays": true,
  "include_events": false,
  "include_weather": false,
  "include_competitor": false,
  "include_economic": false,
  "country": "US"
}
```

For async, append `?async=true` and poll the job. The sync response is a `ForecastResponse` with `forecast_id`, `best_model`, `model_rankings`, and `summary`.

#### `GET /v1/forecasts`
List saved forecasts. Supports `limit` and `offset`.

#### `GET /v1/forecasts/{forecast_id}`
Get the full forecast detail with per-model `forecast_values`, `baseline_values`, `metrics`, etc.

#### `DELETE /v1/forecasts/{forecast_id}`
Delete a forecast.

#### `GET /v1/jobs/{job_id}`
Get async job status. Includes `progress` (0..1) and `message`.

#### `GET /v1/jobs/{job_id}/result`
Block until a job completes, return the full result. Times out after 300s.

### 4.4 Models (the data-science workflow)

Train once, save the artifact, then load and forecast any time without retraining. This is the data-science workflow you asked for.

#### `POST /v1/models/train`
Train one or more models with proper train/test split, evaluate on the held-out test set, persist the best to the model registry.

```json
{
  "models": ["prophet", "lightgbm", "theta"],
  "file_id": "abc123",
  "train_test_split": 0.8,
  "horizon": 30,
  "date_column": "date",
  "target_column": "value",
  "frequency": "D",
  "name": "Production prophet v1",
  "notes": "Trained on 2024 data, baseline for production",
  "tags": ["production", "weekly", "v1"],
  "include_media_plan": true,
  "include_promotions": true,
  "include_holidays": true
}
```

Response (200) — includes per-model test metrics and the saved `saved_model` block:
```json
{
  "split": {
    "train_rows": 292,
    "test_rows": 73,
    "train_start": "2024-01-01",
    "train_end": "2024-10-20",
    "test_start": "2024-10-21",
    "test_end": "2024-12-31",
    "train_ratio": 0.8
  },
  "results": [
    {"model_type": "prophet", "model_name": "Prophet", "metrics": {"mae": 8.5, "rmse": 11.2, "mape": 7.3, "cv_mae": 9.1}, "error": null},
    {"model_type": "lightgbm", "model_name": "LightGBM", "metrics": {"mae": 12.1, ...}, "error": null}
  ],
  "saved_model": {
    "model_id": "model_abc123",
    "name": "Production prophet v1",
    "model_type": "prophet",
    "metrics": {"mae": 8.5, "rmse": 11.2, "mape": 7.3},
    "training": {...},
    "train_start": "2024-01-01",
    ...
  }
}
```

#### `POST /v1/models/{model_id}/forecast`
Load a saved model and forecast WITHOUT retraining. Fast path.

```json
{ "horizon": 30 }
```

Response (200):
```json
{
  "model_id": "model_abc123",
  "model_name": "Prophet",
  "model_meta": {...full saved-model metadata...},
  "forecast_values": [
    {"date": "2025-01-01", "forecast": 105.3, "lower_ci": 95.2, "upper_ci": 115.4, "baseline": 100.0, "uplift": 5.3}
  ],
  "baseline_values": [...],
  "components": {...},
  "horizon": 30
}
```

#### `GET /v1/models`
List saved models. Query: `model_type`, `search`, `limit`, `offset`.

#### `GET /v1/models/{model_id}`
Get full metadata for a saved model.

#### `POST /v1/models/upload`
Upload a pre-trained model pickle. Use a multipart form with the file plus optional name/notes/tags.

```bash
curl -X POST -H "Authorization: Bearer ..." \
  -F "file=@mymodel.pkl" -F "name=My model" -F "tags=production,v1" \
  http://localhost:8000/v1/models/upload
```

The model must be a pickle or joblib blob in ForecastIQ's format (with `class_name`, `state`, `fitted`, `extra` keys).

#### `DELETE /v1/models/{model_id}`
Delete a saved model.

### 4.5 API keys (internal — for the UI)

These endpoints are under `/api/v1/*` and are used by the ForecastIQ UI to manage keys. They do not require an API key (they're protected by being browser-only). If you want to manage keys from a script, you can call them from inside the same self-hosted installation.

#### `GET /api/v1/api-keys`
List all keys (without their plain secrets).

#### `POST /api/v1/api-keys`
Create a new key. Returns the plain secret exactly once.

```json
{ "name": "Notebook", "tier": "pro" }
```

Response includes `plain_key` (save it now), `prefix`, and a `warning`.

#### `PATCH /api/v1/api-keys/{key_id}`
Update name, tier, scopes, or expiry.

#### `DELETE /api/v1/api-keys/{key_id}`
Revoke a key.

#### `GET /api/v1/api-keys/tiers`
List tiers with their rate limits.

## 5. Error responses

Errors come back as a JSON body with `detail` (and sometimes structured fields):

```json
{
  "detail": "Invalid or revoked API key."
}
```

| Status | Meaning |
| --- | --- |
| 400 | Bad request — payload validation failed, missing required field, etc. |
| 401 | Missing or invalid API key. |
| 404 | Resource not found (file, forecast, model, job). |
| 413 | Upload too large. |
| 422 | Validation error — see `errors` array. |
| 429 | Rate limit exceeded. Includes `Retry-After`. |
| 500 | Server error. The `detail` field is safe to display. |

## 6. End-to-end examples

### A. Notebook: load data, run a forecast, save the result as a CSV

```python
import requests, pandas as pd, io
BASE = "http://localhost:8000/v1"
H = {"Authorization": "Bearer fiq_live_abc123_yoursecret..."}

# 1. Upload sales
with open("sales_2024.csv", "rb") as f:
    r = requests.post(f"{BASE}/files/upload/sales",
                      files={"file": ("sales.csv", f, "text/csv")}, headers=H)
file_id = r.json()["file_id"]

# 2. Analyze
analysis = requests.post(f"{BASE}/analyze", params={"file_id": file_id}, headers=H).json()
date_col = analysis["validation"]["date_column"]
value_col = analysis["validation"]["value_column"]
print(f"Recommended: {[m['model'] for m in analysis['model_recommendations'][:3]]}")

# 3. Run a forecast asynchronously
req = {
    "name": "Notebook forecast",
    "target_column": value_col,
    "date_column": date_col,
    "frequency": "D",
    "horizon": 30,
    "models": ["prophet", "theta", "ets"],
    "include_media_plan": False, "include_promotions": False,
    "include_holidays": False, "include_events": False,
    "include_weather": False, "include_competitor": False,
    "include_economic": False,
}
job = requests.post(f"{BASE}/forecast", json=req, params={"async": "true"}, headers=H).json()
job_id = job["job_id"]

# 4. Poll until done
import time
while True:
    status = requests.get(f"{BASE}/jobs/{job_id}", headers=H).json()
    print(f"  {status['status']} — {status.get('progress', 0)*100:.0f}% — {status.get('message', '')}")
    if status["status"] in ("completed", "failed"):
        break
    time.sleep(2)

# 5. Get the result and save as CSV
result = requests.get(f"{BASE}/jobs/{job_id}/result", headers=H).json()
detail = result["result"]
# Pick the best model
best = detail.get("best_model", "prophet")
forecast_values = detail["results"][best]["forecast_values"]
df = pd.DataFrame(forecast_values)
df.to_csv("forecast_2025.csv", index=False)
print("Saved to forecast_2025.csv")
```

### B. Script: use a previously-saved model

```python
# After running POST /v1/models/train once, you have a model_id.
# Now you can forecast as many times as you want without retraining.
model_id = "model_abc123"
r = requests.post(
    f"{BASE}/models/{model_id}/forecast",
    json={"horizon": 30},
    headers=H,
).json()
print(r["forecast_values"][:5])
```

### C. ETL pipeline: retrain on a schedule, save, alert

```python
# 1. Upload the new month's data
file_id = upload(...)

# 2. Train & save (the new model replaces the old one in your pipeline)
result = train_and_save({
    "models": ["prophet", "lightgbm"],
    "file_id": file_id,
    "train_test_split": 0.85,
    "horizon": 30,
    "name": f"weekly-{today.isoformat()}",
    "tags": ["scheduled", "weekly"],
}).json()

# 3. If the new model's test MAE is too high, alert
new_mae = result["saved_model"]["metrics"]["mae"]
if new_mae > MAX_ACCEPTABLE_MAE:
    send_alert(f"Model retrain failed quality check: MAE={new_mae:.2f}")
```

## 7. Best practices

- **Never commit your API key to git.** Treat it like a password.
- **Use a separate key per consumer** (notebook, ETL job, dashboard) so you can revoke individually.
- **Use the smallest tier you need.** The free tier is enough for most ad-hoc use.
- **Cache `forecast_data` results** — they're deterministic given the same input and config.
- **For repeated forecasts, use the model registry** (train once, save, then `POST /v1/models/{id}/forecast` is much faster).
- **Use `?async=true` for anything that might take >5 seconds.** Sync mode is fine for small data and 1-2 models.
- **Page through list endpoints** rather than fetching everything.

## 8. Versioning

The API is at `/v1/*`. Breaking changes will be released as `/v2/*` with a 6-month deprecation period for `/v1/*`. New fields added to existing responses are non-breaking.

Schema changes are tracked in [`CHANGELOG.md`](./CHANGELOG.md).

## 9. See also

- [API_KEYS.md](./API_KEYS.md) — managing API keys
- [DATA_FORMAT.md](./DATA_FORMAT.md) — CSV column formats for each file type
- [MODELS.md](./MODELS.md) — model types, parameters, and tuning
- Interactive docs at `http://<your-host>/docs` (Swagger UI)
