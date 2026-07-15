# ForecastIQ

**Advanced time series forecasting for data scientists.**

ForecastIQ is a self-hosted platform for sales forecasting with 10 built-in models, automatic model selection, external factor integration, and a built-in model registry (train/save/load) that mirrors the typical data-science workflow.

## Features

- **10 forecasting models**: ARIMA, SARIMAX, Prophet, LightGBM, XGBoost, WMA, ETS, Theta, STL, AutoML
- **Automatic model selection** based on data characteristics
- **External factors**: media plan, promotions, holidays, events, weather, competitor, economic
- **Ensemble support**: combine 2+ models with weighted averaging
- **Train/test split** for proper held-out evaluation
- **Model registry**: save trained models as pickles, reload and forecast without retraining
- **Built-in optimization** for large datasets (5+ years daily → weekly aggregation, parallel model training, in-memory rate limiting)
- **REST API** at `/api/v1/*` (UI) and `/v1/*` (programmatic, API-key auth)
- **Interactive charts** with confidence intervals, model comparison, decomposition
- **CSV / Excel / Parquet** support
- **Modern React + Material UI** frontend

## Quick start

### With Docker (recommended)

```bash
# macOS / Linux
./start-with-docker.sh

# Windows
start-with-docker.bat
```

Then open:
- **UI**: http://localhost:3000
- **API docs**: http://localhost:8000/docs
- **Backend health**: http://localhost:8000/api/v1/health

### Without Docker

```bash
# macOS / Linux
./setup-without-docker.sh

# Windows
setup-without-docker.bat
```

These scripts install Python and Node dependencies. The macOS / Linux script also starts the backend and frontend; the Windows batch file only installs dependencies, so you must start the backend and frontend manually afterward.

## The data-science workflow

```
1. Upload sales data (CSV)
         │
         ▼
2. Analyze    ──▶ detect trend, seasonality, stationarity
         │      ──▶ recommend models with reasoning
         ▼
3. Train     ──▶ split train/test
         │      ──▶ train candidate models
         │      ──▶ evaluate on held-out test (MAE, RMSE, MAPE)
         │      ──▶ save best as pickle
         ▼
4. Forecast  ──▶ load saved model, predict (no retraining)
         │      ──▶ overlay actuals on chart
         │      ──▶ export CSV / JSON
         ▼
5. Repeat user ──▶ upload pickle from another environment
                    ──▶ or call /v1/forecast from a notebook
```

See [MODELS.md](docs/MODELS.md) for the full model registry workflow.

## Programmatic API

The full HTTP API is documented in [API.md](docs/API.md) and at `http://localhost:8000/docs`. Highlights:

- `/v1/files` — upload, list, fetch rows
- `/v1/analyze` — characteristics + recommendations
- `/v1/forecast` — train new and forecast (sync or async)
- `/v1/models/train` — train with proper train/test split, save best
- `/v1/models/{id}/forecast` — forecast with a saved model (no retraining)
- `/v1/models/upload` — upload a pickle

API keys: see [API_KEYS.md](docs/API_KEYS.md).

## Documentation

- **[API.md](docs/API.md)** — full HTTP API reference
- **[API_KEYS.md](docs/API_KEYS.md)** — managing API keys
- **[MODELS.md](docs/MODELS.md)** — model registry, training, saving
- **[DATA_FORMAT.md](docs/DATA_FORMAT.md)** — expected CSV column formats

## Architecture

```
┌─────────────┐  ┌──────────────┐  ┌────────────────┐
│  React +    │  │   FastAPI    │  │  Disk-based    │
│  Material   │  │   (Python    │  │  Storage       │
│  UI (SPA)   │  │   3.11)      │  │  (Parquet +     │
│             │◀─▶│              │◀─▶  JSON index)   │
└─────────────┘  └──────────────┘  └────────────────┘
                       │
                       ▼
              ┌────────────────┐
               │  10 ML models  │
              │  + Model       │
              │  registry      │
              └────────────────┘
```

- **Frontend**: React 18 + TypeScript + Vite + Material UI 5 + TanStack Query + Recharts
- **Backend**: FastAPI + Pydantic v2 + pandas + scikit-learn-style models (ARIMA, ETS, Theta, STL, WMA), Prophet, LightGBM, XGBoost
- **Storage**: Parquet datasets + JSON metadata on disk. No external DB required.

## Configuration

The backend reads from environment variables. Most have sensible defaults for self-hosted use.

| Variable | Default | Description |
| --- | --- | --- |
| `DATA_DIR` | `./data` | Where uploads, datasets, and forecasts are persisted |
| `BACKEND_CORS_ORIGINS` | `["http://localhost:3000", "http://127.0.0.1:3000"]` | Allowed CORS origins |
| `PUBLIC_API_ENABLED` | `true` | When true, `/v1/*` requires an API key |
| `DEFAULT_API_KEY_TIER` | `free` | Default tier for newly created keys |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `REDIS_URL` | (empty) | Redis URL for persistent job queue; empty = in-memory |
| `JWT_SECRET_KEY` | auto-generated | Secret for JWT tokens; set in env for production |
| `MAX_UPLOAD_SIZE` | `104857600` | Maximum upload size in bytes (default 100 MB) |
| `FORECASTIQ_JOB_TIMEOUT` | `900` | Job timeout in seconds |
| `FORECASTIQ_FOLD_TIMEOUT` | `120` | Per-CV-fold timeout in seconds |
| `FORECASTIQ_MODEL_TIMEOUT` | `300` | Per-model timeout in seconds |

For a self-hosted single-user install, the defaults are fine.

## License

MIT
