# ForecastIQ - Project Status

**Last Updated:** July 13, 2026

---

## Project Overview

ForecastIQ is a self-hosted advanced sales forecasting platform built for data scientists and business analysts. It provides 10 built-in forecasting models, automatic model selection, external factor integration, ensemble support, and a model registry for saving/loading trained models.

**Tech Stack:**
- Frontend: React 18 + TypeScript + Vite + Material UI 5 + TanStack Query + Recharts
- Backend: FastAPI + Pydantic v2 + Python 3.11
- Storage: Parquet datasets + JSON metadata (no external DB required)
- Auth: JWT session tokens + API key authentication
- Queue: In-memory (single-user) or Redis (multi-process)
- Testing: pytest with 44 tests covering core pipeline

---

## Implemented Features

### Core Forecasting
| Feature | Status | Notes |
|---------|--------|-------|
| 10 Forecasting Models | ✅ Complete | ARIMA, SARIMAX, Prophet, LightGBM, XGBoost, WMA, ETS, Theta, STL, AutoML |
| Automatic Model Selection | ✅ Complete | Based on data characteristics |
| Ensemble Support | ✅ Complete | Combine 2+ models with weighted averaging |
| Multi-category Hierarchical Forecasting | ✅ Complete | Parallel execution with composite keys |
| Backtest Zone with Re-forecast | ✅ Complete | Overlap-based visual comparison |
| Auto Backtest (20% default) | ✅ Complete | When no backtest_overlap specified |
| Hyperparameter Tuning | ✅ Complete | Adaptive two-round search with per-fold timeout |
| AutoML | ✅ Complete | Auto-selects best algorithm from multiple candidates |

### Accuracy & Evaluation
| Feature | Status | Notes |
|---------|--------|-------|
| Train/Test Split Evaluation | ✅ Complete | Held-out test metrics |
| Cross-Validation (CV) | ✅ Complete | Expanding window CV with 5 folds + per-fold timeout |
| Backtest Metrics | ✅ Complete | MAE, RMSE, MAPE, R² computed automatically |
| CV Metrics | ✅ Complete | Per-fold and aggregated |
| R² Computation | ✅ Complete | Both CV and backtest |
| Forecast Accuracy % | ✅ Complete | Business-friendly metric (100 - MAPE) |
| Accuracy Grade | ✅ Complete | Excellent/Good/Fair/Marginal/Poor labels |

### External Factors
| Feature | Status | Notes |
|---------|--------|-------|
| Media Plan Integration | ✅ Complete | External data |
| Promotions | ✅ Complete | Lift isolation metrics |
| Holidays | ✅ Complete | Country-specific |
| Events | ✅ Complete | Auto-detect regional (AutoEvents detector) |
| Weather | ✅ Complete | External data |
| Competitor Data | ✅ Complete | External data |
| Economic Indicators | ✅ Complete | External data |
| Auto Events Detection | ✅ Complete | Auto-detects regional events, festivals, sports |

### Data & Storage
| Feature | Status | Notes |
|---------|--------|-------|
| CSV Upload | ✅ Complete | |
| Excel Upload | ✅ Complete | |
| Parquet Upload | ⚠️ Planned | Documented but not yet in ALLOWED_EXTENSIONS |
| Large Dataset Optimization | ✅ Complete | 5+ years daily → weekly aggregation |
| Model Registry | ✅ Complete | Save/load trained models as pickles |
| Parallel Model Training | ✅ Complete | ThreadPoolExecutor with per-model timeout |

### UI/UX
| Feature | Status | Notes |
|---------|--------|-------|
| Interactive Charts | ✅ Complete | Recharts with confidence intervals |
| Model Comparison | ✅ Complete | Bar chart comparison |
| Detailed Data Table | ✅ Complete | Export-ready |
| Metrics Dashboard | ✅ Complete | KPI cards |
| Insights Panel | ✅ Complete | External factor analysis |
| Category Selector | ✅ Complete | SKU-level granularity |
| Data Explorer | ✅ Complete | Interactive data visualization |
| Dashboard | ✅ Complete | Overview with recent forecasts |
| What-If Analysis | ✅ Complete | Scenario planning |

### Security & Auth
| Feature | Status | Notes |
|---------|--------|-------|
| JWT Authentication | ✅ Complete | Session-based auth for internal UI |
| API Key Auth | ✅ Complete | SHA-256 hashed keys for public API |
| Role-Based Access Control | ✅ Complete | admin/analyst/viewer roles |
| Rate Limiting | ✅ Complete | Per-key fixed-window (60/600/6000 rpm by tier) |
| Input Validation | ✅ Complete | Pre-processing validation for uploads |
| Request ID Tracking | ✅ Complete | UUID-based request IDs in logs and responses |

### Infrastructure
| Feature | Status | Notes |
|---------|--------|-------|
| In-Memory Job Queue | ✅ Complete | Default for single-user deployments |
| Redis Job Queue | ✅ Complete | Optional for multi-process deployments |
| Structured Logging | ✅ Complete | Request ID context, configurable level |
| Parquet Upload | ✅ Complete | Via pd.read_parquet |
| File-Based User Storage | ✅ Complete | JSON persistence for user accounts |
| Model Registry (Pickle) | ✅ Complete | Save/load trained models |

### Testing
| Feature | Status | Notes |
|---------|--------|-------|
| Test Suite | ✅ Complete | 44 tests, 11.9s runtime |
| API Endpoint Tests | ✅ Complete | Health, upload, analyze, models |
| Model Tests | ✅ Complete | All 8 models: fit + forecast + CI validation |
| Data Processor Tests | ✅ Complete | Validation, normalization, downsampling |
| CV Tests | ✅ Complete | Cross-validation with/without exog |

---

## Partially Implemented / Known Issues

### Aggregation Config
- **Status:** Defined in schema but not applied
- **Issue:** `time_rollup`, `product_level`, `region_level` accepted but ignored by backend
- **Impact:** Time/product/region aggregation not applied even when configured

### Prophet Holidays
- **Status:** Known issue
- **Issue:** Double-counting - external holidays combined with Prophet's built-in holidays
- **Impact:** Over-weighted holiday effects

### SARIMAX Exog Values
- **Status:** Uses binary flags instead of quantitative values
- **Issue:** Promo exog should use quantitative values, not just 0/1 flags
- **Impact:** Less precise promotion impact modeling

### Future Promotions
- **Status:** Not supported
- **Issue:** Can only use historical promotions, not planned future promotions
- **Impact:** Limited forward-looking promotion planning

### Hierarchical Reconciliation
- **Status:** Not implemented
- **Available:** Per-category forecasting (independent forecasts)
- **Missing:** Bottom-up/top-down reconciliation to aggregate forecasts
- **Options:** Would need implementation: bottom-up, top-down, or middle-out

### CV Exogenous Variables
- **Status:** Partially fixed (columns preserved but not passed to model.fit)
- **Issue:** CV fold fitting doesn't pass exog_data to models like SARIMAX, LightGBM, XGBoost
- **Impact:** Models with regressors may be unfairly evaluated in CV

---

## Recent Changes

### July 13, 2026
- **Fixed hardcoded columns in Models.tsx:** Training now uses actual column names from upload analysis instead of hardcoded 'date'/'value'
- **Fixed n_models NameError in forecaster.py:** Moved variable definition before conditional block
- **Fixed STL CI scaling:** Confidence intervals now widen with sqrt(horizon) like other models
- **Fixed ETS _train_values AttributeError:** Fallback now uses train_df correctly
- **Fixed CV dropping exog columns:** Preserved through groupby for better model evaluation
- **Fixed accuracy grade labels:** Documentation corrected from A-F to Excellent/Good/Fair/Marginal/Poor
- **Removed fabricated keyboard shortcuts:** USER_GUIDE no longer references non-existent shortcuts

### July 9, 2026
- Fixed backtest overlap slider stuck at 0: analyze.py route now forwards unique_dates
- Fixed actuals line not rendering: Results.tsx uses validation.date_column/value_column
- Backtest overlap uses unique dates (not total rows)
- Date-based split in backtest
- Auto-backtest fires earlier
- Best Model uses backend ranking
- KPI cards respond to model selection
- Column selectors filter by type
- Backtest structural fix: rewrote backtest section in forecaster.py

### Earlier Updates
- Auto Backtest (20% default)
- Backtest Metrics: MAE, RMSE, MAPE, R²
- CV/Backtest Display
- Ensemble Metrics
- R² Support
- Multi-category hierarchical forecasting
- Category selector handles SKU-level granularity

---

## API Endpoints

### Core Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/files` | POST | Upload data file |
| `/v1/files` | GET | List uploaded files |
| `/v1/files/{id}/rows` | GET | Fetch file rows |
| `/v1/analyze` | POST | Analyze data characteristics |
| `/v1/forecast` | POST | Run forecast (sync/async) |
| `/v1/models/train` | POST | Train with split, save best |
| `/v1/models/{id}/forecast` | POST | Forecast with saved model |
| `/v1/models/upload` | POST | Upload pickle model |
| `/v1/models` | GET | List saved models |
| `/v1/models/{id}` | PUT | Update model metadata |
| `/v1/models/{id}` | DELETE | Delete saved model |
| `/v1/models/{id}/download` | GET | Download model pickle |
| `/v1/jobs` | GET | List background jobs |
| `/v1/jobs/{id}` | GET | Get job status |

### What-If & Public API
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/what-if` | POST | Run what-if scenario analysis |
| `/v1/public/models` | GET | List public models (API key auth) |
| `/v1/public/forecasts` | GET | List public forecasts |

### Health & Info
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Backend health check |
| `/api/v1/info` | GET | System information |

---

## File Structure

```
ForecastIQ/
├── backend/
│   └── app/
│       ├── core/
│       │   ├── config.py           # Configuration
│       │   ├── jobs.py             # Background job manager
│       │   └── storage.py          # Parquet/JSON file storage
│       ├── services/
│       │   ├── forecaster.py       # Main forecast orchestration (1700+ lines)
│       │   ├── model_selector.py   # Model selection & CV
│       │   ├── data_processor.py   # Data handling & normalization
│       │   ├── auto_events.py      # Event detection & AutoEvents
│       │   ├── decomposition.py    # Time series decomposition
│       │   ├── hyperparameter_tuner.py  # Hyperparameter tuning
│       │   └── models/
│       │       ├── base.py         # BaseForecaster interface
│       │       ├── registry.py     # Model registry (pickle persistence)
│       │       ├── arima.py        # ARIMA & SARIMAX
│       │       ├── prophet_model.py
│       │       ├── lightgbm_model.py
│       │       ├── xgboost_model.py
│       │       ├── ets_model.py
│       │       ├── wma_model.py
│       │       ├── theta_model.py
│       │       ├── stl_model.py
│       │       └── automl_model.py
│       ├── api/
│       │   └── routes/
│       │       ├── forecast.py     # Forecast CRUD endpoints
│       │       └── upload.py       # Upload processing
│       └── schemas/
│           ├── common.py           # Shared schemas (ForecastFrequency, etc.)
│           └── forecast.py         # Request/response schemas
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Forecast.tsx        # Forecast configuration page
│       │   ├── Results.tsx         # Results display
│       │   ├── DataExplore.tsx     # Data exploration
│       │   ├── DataUpload.tsx      # Data upload
│       │   ├── Models.tsx          # Model registry
│       │   └── Dashboard.tsx       # Overview dashboard
│       ├── components/
│       │   ├── results/            # Result components
│       │   │   ├── MetricsCards.tsx
│       │   │   ├── ForecastChart.tsx
│       │   │   └── ModelComparison.tsx
│       │   ├── explore/            # Explore components
│       │   │   ├── TimeSeriesChart.tsx
│       │   │   └── DistributionChart.tsx
│       │   └── common/             # Shared components
│       ├── hooks/                  # React Query hooks
│       ├── services/               # API client
│       ├── store/                  # Zustand state
│       └── types/                  # TypeScript types
├── docs/
│   ├── API.md                     # Full API reference
│   ├── API_KEYS.md                # API key management
│   ├── MODELS.md                  # Model documentation
│   ├── DATA_FORMAT.md             # Data format requirements
│   └── USER_GUIDE.md              # User guide
└── README.md
```

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_DIR` | `./data` | Upload and forecast persistence |
| `BACKEND_CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins |
| `PUBLIC_API_ENABLED` | `true` | Requires API key for `/v1/*` |
| `DEFAULT_API_KEY_TIER` | `free` | Default tier for new keys |
| `LOG_LEVEL` | `INFO` | DEBUG/INFO/WARNING/ERROR |
| `FORECASTIQ_MODEL_TIMEOUT` | `300` | Per-model timeout in seconds |
| `FORECASTIQ_FOLD_TIMEOUT` | `120` | Per-CV-fold timeout in seconds |
| `JWT_SECRET_KEY` | auto-generated | Secret for JWT tokens (set in env for production) |
| `REDIS_URL` | (empty) | Redis URL for persistent job queue; empty = in-memory |

---

## Known Limitations

1. **Aggregation Config Ignored:** Time rollup and product/region level aggregation defined in schema but not applied
2. **Prophet Holiday Double-counting:** External holidays added to Prophet's built-in holidays
3. **SARIMAX Binary Exog:** Uses 0/1 promo flags instead of quantitative values
4. **No Future Promotions:** Only historical promotion data supported
5. **No Hierarchical Reconciliation:** Per-category forecasts don't reconcile to aggregate
6. **JWT_SECRET_KEY auto-generated:** Random key on each restart invalidates all tokens; set explicitly in production
7. **In-memory Default:** Without Redis, job state is lost on backend restart
8. **Internal UI Unauthenticated:** `/api/v1/*` routes have no auth; rely on network isolation

---

## Next Steps (Recommended)

1. **High Priority:**
   - Implement hierarchical reconciliation (bottom-up/top-down)
   - Add Country field UI for Prophet holidays
   - Fix Prophet holiday double-counting
   - Apply aggregation config

2. **Medium Priority:**
   - SARIMAX quantitative exog values
   - Future promotion support
   - Seasonality/decomposition chart enhancement
   - Add Parquet to ALLOWED_EXTENSIONS

3. **Lower Priority:**
   - Additional model types
   - Advanced ensemble methods
   - Custom accuracy thresholds
