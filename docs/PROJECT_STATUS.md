# ForecastIQ - Project Status

**Last Updated:** July 8, 2026

---

## Project Overview

ForecastIQ is a self-hosted advanced sales forecasting platform built for data scientists and business analysts. It provides 9 built-in forecasting models, automatic model selection, external factor integration, ensemble support, and a model registry for saving/loading trained models.

**Tech Stack:**
- Frontend: React 18 + TypeScript + Vite + Material UI 5 + TanStack Query + Recharts
- Backend: FastAPI + Pydantic v2 + Python 3.11
- Storage: Parquet datasets + JSON metadata (no external DB required)

---

## Implemented Features

### Core Forecasting
| Feature | Status | Notes |
|---------|--------|-------|
| 9 Forecasting Models | ✅ Complete | ARIMA, SARIMAX, Prophet, LightGBM, XGBoost, WMA, ETS, Theta, STL |
| Automatic Model Selection | ✅ Complete | Based on data characteristics |
| Ensemble Support | ✅ Complete | Combine 2+ models with weighted averaging |
| Multi-category Hierarchical Forecasting | ✅ Complete | Parallel execution with composite keys |
| Backtest Zone with Re-forecast | ✅ Complete | Overlap-based visual comparison |
| Auto Backtest (20% default) | ✅ Complete | When no backtest_overlap specified |

### Accuracy & Evaluation
| Feature | Status | Notes |
|---------|--------|-------|
| Train/Test Split Evaluation | ✅ Complete | Held-out test metrics |
| Cross-Validation (CV) | ✅ Complete | Expanding window CV with 5 folds |
| Backtest Metrics | ✅ Complete | MAE, RMSE, MAPE, R² computed automatically |
| CV Metrics | ✅ Complete | Per-fold and aggregated |
| R² Computation | ✅ Complete | Both CV and backtest |
| Forecast Accuracy % | ✅ Complete | Business-friendly metric |
| Accuracy Grade | ✅ Complete | A/B/C/D/F grading |
| Separate CV & Backtest Display | ✅ Complete | Clear labels in UI |

### External Factors
| Feature | Status | Notes |
|---------|--------|-------|
| Media Plan Integration | ✅ Complete | External data |
| Promotions | ✅ Complete | Lift isolation metrics |
| Holidays | ✅ Complete | Country-specific |
| Events | ✅ Complete | Auto-detect regional |
| Weather | ✅ Complete | External data |
| Competitor Data | ✅ Complete | External data |
| Economic Indicators | ✅ Complete | External data |

### Data & Storage
| Feature | Status | Notes |
|---------|--------|-------|
| CSV Upload | ✅ Complete | |
| Excel Upload | ✅ Complete | |
| Parquet Upload | ✅ Complete | |
| Large Dataset Optimization | ✅ Complete | 5+ years daily → weekly aggregation |
| Model Registry | ✅ Complete | Save/load trained models |
| Parallel Model Training | ✅ Complete | ThreadPoolExecutor |

### UI/UX
| Feature | Status | Notes |
|---------|--------|-------|
| Interactive Charts | ✅ Complete | Recharts with confidence intervals |
| Model Comparison | ✅ Complete | Bar chart comparison |
| Detailed Data Table | ✅ Complete | Export-ready |
| Metrics Dashboard | ✅ Complete | KPI cards |
| Insights Panel | ✅ Complete | External factor analysis |
| Category Selector | ✅ Complete | SKU-level granularity |

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

---

## Recent Changes

### July 8, 2026
- **Auto Backtest (20% default):** When no `backtest_overlap` specified, system now automatically uses latest 20% of data as backtest period for business users
- **Backtest Metrics:** MAE, RMSE, MAPE, R² computed from backtest forecasts vs actuals
- **CV/Backtest Display:** UI now shows both "Forecast accuracy" (backtest) and "CV accuracy" with clear labels
- **Ensemble Metrics:** Ensemble models now compute and display accuracy metrics
- **R² Support:** Added R² computation to CV (per-fold and aggregated) and backtest metrics

### Earlier Updates
- Multi-category hierarchical forecasting with parallel execution
- Category selector handles SKU-level granularity
- Fixed backtest zone overlap handling
- Results table dynamic category columns
- ForecastChart category results support

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
│       ├── services/
│       │   ├── forecaster.py          # Main forecast orchestration
│       │   ├── model_selector.py     # Model selection & CV
│       │   ├── data_processor.py      # Data handling
│       │   ├── auto_events.py         # Event detection
│       │   └── models/                # Individual model implementations
│       │       ├── registry.py        # Model registry
│       │       ├── prophet_model.py
│       │       ├── arima.py
│       │       ├── lightgbm_model.py
│       │       └── ...
│       └── schemas/
│           └── forecast.py            # Request/response schemas
├── frontend/
│   └── src/
│       ├── pages/
│       │   └── Results.tsx            # Main results page
│       ├── components/
│       │   └── results/               # Result components
│       │       ├── MetricsCards.tsx   # KPI cards
│       │       ├── ForecastChart.tsx  # Forecast visualization
│       │       ├── ModelComparison.tsx
│       │       └── ...
│       └── types/
│           └── index.ts               # TypeScript types
├── docs/
│   ├── API.md
│   ├── MODELS.md
│   ├── DATA_FORMAT.md
│   └── API_KEYS.md
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

---

## Known Limitations

1. **Aggregation Config Ignored:** Time rollup and product/region level aggregation defined in schema but not applied
2. **Prophet Holiday Double-counting:** External holidays added to Prophet's built-in holidays
3. **SARIMAX Binary Exog:** Uses 0/1 promo flags instead of quantitative values
4. **No Future Promotions:** Only historical promotion data supported
5. **No Hierarchical Reconciliation:** Per-category forecasts don't reconcile to aggregate

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

3. **Lower Priority:**
   - Additional model types
   - Advanced ensemble methods
   - Custom accuracy thresholds
