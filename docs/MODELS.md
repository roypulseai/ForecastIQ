# Model Registry & Persistence

ForecastIQ includes a built-in model registry that mirrors the data-science pattern of train-once-save-load-many.

## Workflow

```
                  ┌────────────────────────────────┐
                  │   Train & save (POST /train)   │
                  │  - train/test split             │
                  │  - train one or more models     │
                  │  - evaluate on held-out test    │
                  │  - persist best as a pickle     │
                  └────────────────┬───────────────┘
                                   │
                                   ▼
                  ┌────────────────────────────────┐
                  │   Model Registry (data/models/) │
                  │  - <id>.pkl    (binary blob)    │
                  │  - <id>.meta.json (metadata)    │
                  │  - index.json   (lookup)        │
                  └────────────────┬───────────────┘
                                   │
                ┌──────────────────┴──────────────────┐
                ▼                                     ▼
   ┌────────────────────────┐         ┌──────────────────────────┐
   │  Forecast              │         │  Upload (POST /upload)   │
   │  (POST /{id}/forecast) │         │  - ingest a pickle       │
   │  - load + predict      │         │  - validate compatibility│
   │  - no retraining       │         │  - register               │
   │  - fast                │         └──────────────────────────┘
   └────────────────────────┘
```

## What gets saved

Each saved model is a directory entry under `DATA_DIR/models/`:

```
data/models/
├── index.json                 # lookup: { model_id: metadata }
├── abc123def456.pkl           # binary blob: pickled fitted model
└── abc123def456.meta.json     # full metadata (same as in index)
```

The pickle is wrapped in a self-describing payload:

```python
payload = {
    "schema_version": 1,
    "class_name": "ProphetForecaster",
    "module": "app.services.models.prophet_model",
    "state": {
        "_date_col": "date",
        "_value_col": "value",
        "_last_date": pd.Timestamp("2024-12-30"),
        "_frequency": "D",
        "_feature_cols": [],
        "params": {"seasonality_mode": "additive", ...},
        "name": "Prophet",
    },
    "fitted": <the actual fitted Prophet model>,
    "extra": {  # any extra state the model needs
        "_scaler": <StandardScaler>,
        ...
    }
}
```

This makes the artifact self-describing — we can re-instantiate the right class on load and restore its state. The `schema_version` lets us evolve the format over time without breaking older pickles.

## Metadata

Each saved model has a rich `SavedModelMeta`:

| Field | Type | Description |
| --- | --- | --- |
| `model_id` | string | Unique identifier (UUID hex) |
| `name` | string | User-supplied display name |
| `model_type` | string | `arima`, `sarimax`, `prophet`, `lightgbm`, etc. |
| `framework` | string | `pickle`, `joblib`, `prophet`, `statsmodels` |
| `created_at` | ISO datetime | |
| `updated_at` | ISO datetime | |
| `file_size` | int | bytes |
| `sha256` | string | Content hash for integrity check |
| `metrics` | object | `{mae, rmse, mape, train_rows, test_rows, cv_mae, cv_rmse, cv_mape}` |
| `training` | object | `{date_column, value_column, frequency, train_test_split, horizon_used, hyperparameters, exogenous_used}` |
| `train_start`, `train_end` | string | Date range the model was trained on |
| `test_start`, `test_end` | string | Date range of the held-out test set |
| `source_file_id` | string | Sales file the model was trained from |
| `tags` | list of strings | |
| `notes` | string | Free-text |

## Train/test split

When you call `POST /v1/models/train`, ForecastIQ:

1. Loads the sales file from the latest upload
2. Splits the data 80/20 (configurable via `train_test_split`) or uses the last `horizon` rows as the test set
3. Trains each requested model on the **train** split only (no leakage)
4. Predicts the test split
5. Computes MAE / RMSE / MAPE
6. Picks the model with the lowest test MAE
7. Persists it to the registry with full metadata

The persisted model is the one trained on the train split, so you can re-use it for forecasting. The reported metrics are on the held-out test set, giving you an honest estimate of how the model will perform on new data.

## Upload a pickle

You can upload a `.pkl` or `.joblib` file produced by ForecastIQ (or a compatible third-party tool). The endpoint validates:

- It deserializes successfully
- The payload has the expected shape (`class_name`, `state`, `fitted`, `extra`)
- The `model_type` is one of the supported models

If accepted, the model is registered with a new `model_id` and you can immediately use it for forecasting.

## Forecasting with a saved model

`POST /v1/models/{model_id}/forecast` with `{"horizon": 30}`:

- Loads the model from disk
- Verifies the SHA-256 hash matches
- Re-instantiates the right class
- Restores all state (params, fitted model, scaler, etc.)
- Calls `forecast(horizon)` — no retraining
- Returns the forecast values

This is the **fast path** — typically <100ms even for large models.

## Best practices

- **Tag your models**: `production`, `weekly`, `baseline`, `experiment-2024-q1`. Makes them easy to filter.
- **Add notes**: document what changed, what you observed, any caveats.
- **Use the smallest train ratio that gives you enough test data**: 80/20 is the default. For very long series, 90/10 is fine.
- **Check `metrics.cv_mae`**: this is the cross-validated MAE from the forecast run, which is a more honest estimate than the test MAE (the test set is a single slice).
- **Use the API** for retraining on a schedule — POST to `/v1/models/train` from a cron job, check the returned metrics, alert if quality regresses.
- **Re-upload after a Prophet upgrade**: Prophet's internal format can change between versions. If you upgrade ForecastIQ, re-train (don't just rely on the old pickle).

## API reference

See [API.md](API.md#44-models-the-data-science-workflow) for full request/response shapes.

Key endpoints:
- `POST /v1/models/train` — train with TTS, save best
- `POST /v1/models/{id}/forecast` — load + forecast (no retraining)
- `POST /v1/models/upload` — upload a pickle
- `GET /v1/models` — list with search and filter
- `GET /v1/models/{id}` — full metadata
- `DELETE /v1/models/{id}` — delete
