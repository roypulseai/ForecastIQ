# ForecastIQ

Advanced Time Series Forecasting Platform with ML-powered model selection, ensemble methods, and comprehensive external factor modeling.

## Features

### Forecasting Models (9 Total)

| Model | Description | Best For |
|-------|-------------|----------|
| **Prophet** | Facebook's time series forecasting | Seasonal data, holidays |
| **ARIMA** | AutoRegressive Integrated Moving Average | Stationary data |
| **SARIMAX** | Seasonal ARIMAX with exogenous variables | Complex seasonality |
| **LightGBM** | Gradient boosting for time series | High variance, complex patterns |
| **XGBoost** | Extreme gradient boosting | Robust alternative to LightGBM |
| **WMA** | Weighted Moving Average | Simple baseline, stable demand |
| **ETS** | Error-Trend-Seasonal | Interpretable forecasting |
| **Theta** | Theta method (M3 competition winner) | Fast, accurate for short series |
| **STL** | Seasonal-Trend decomposition | Flexible seasonality |

### Auto Model Selection

AI-powered recommendations based on data patterns:
- **Trend detection**: increasing, decreasing, stable
- **Seasonality detection**: weekly, monthly, none
- **Variability analysis**: CV (coefficient of variation)
- **Stationarity testing**: ADF test

### External Factors (8 Types)

| Factor | Description | Template |
|--------|-------------|----------|
| **Sales Data** | Historical sales with dates and values | Required |
| **Media Plan** | Marketing spend by channel (TV, digital, social) | Optional |
| **Promotions** | Discount campaigns with price elasticity | Optional |
| **Holidays** | Holiday calendar with pre/post effects | Optional |
| **Events** | Special events (sports, festivals) | Optional |
| **Weather** | Temperature, rain, snow conditions | Optional |
| **Competitor** | Competitor pricing and market share | Optional |
| **Economic** | GDP, inflation, consumer confidence | Optional |

### Marketing Mix Modeling

- **Adstock**: Geometric decay curves for media carryover
- **Saturation**: Hill saturation curves (diminishing returns)
- **Price Elasticity**: Non-linear discount impact modeling

### Baseline Trend Extraction

Separates baseline trend from forecast impact:
- **Baseline**: What would happen without external factors
- **Forecast**: Full prediction with promotions/media/holidays
- **Uplift %**: Impact of external factors

### What-If Scenario Simulator

Simulate business scenarios:
- **Promotion**: Discount depth, duration, elasticity
- **Media Spend**: Channel, spend increase, ROI
- **Price Change**: Price changes with promo depth

### Ensemble Methods

Combine 2-3 models with weighted averaging for improved accuracy.

### Power User Controls

Fine-tune hyperparameters for each model:
- ARIMA: p, d, q orders
- SARIMAX: seasonal P, D, Q with period
- Prophet: changepoint_prior_scale, seasonality_prior_scale
- LightGBM/XGBoost: n_estimators, learning_rate, max_depth

## Installation Options

### Option 1: Docker (Recommended)

```bash
# Start ForecastIQ
Double-click: start-with-docker.bat

# Access at http://localhost:3000
```

### Option 2: Manual Setup

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## Data Templates

Download templates from `/templates` folder:

| File | Purpose |
|------|---------|
| `01_sales_template.csv` | Historical sales data (REQUIRED) |
| `02_media_plan_template.csv` | Marketing spend by channel |
| `03_promotions_template.csv` | Promotional campaigns |
| `04_holidays_template.csv` | Holiday calendar |
| `05_events_template.csv` | Special events |
| `06_weather_template.csv` | Weather conditions |
| `07_competitor_template.csv` | Competitor data |
| `08_economic_template.csv` | Economic indicators |

## Usage Guide

### 1. Upload Data
- Download and fill in the appropriate templates
- Upload sales data first (required)
- Upload optional external factors as available

### 2. Analyze
System automatically:
- Detects data patterns (trend, seasonality)
- Measures variability (CV)
- Recommends best models

### 3. Configure Forecast
- Select one or more models
- Set forecast horizon
- Choose external factors to include
- **Power users**: Click "Model Parameters" for hyperparameter tuning

### 4. What-If Analysis
After running a forecast:
- Click "What-If Simulator"
- Test promotion scenarios
- Simulate media spend changes
- Model price elasticity

### 5. View Results
- **Forecast Chart**: Visualize predictions
- **Baseline vs Forecast**: See external factor impact
- **Model Comparison**: MAE, RMSE, MAPE metrics
- **Export**: Download CSV with all forecasts

## API Documentation

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/forecast/upload/{file_type}` | Upload data file |
| POST | `/api/v1/forecast/analyze` | Analyze uploaded data |
| POST | `/api/v1/forecast/forecast` | Run forecast |
| GET | `/api/v1/forecast/forecast/{id}` | Get forecast results |
| GET | `/api/v1/forecast/forecasts` | List all forecasts |

### File Types for Upload

- `sales` - Historical sales data
- `media_plan` - Marketing spend
- `promotions` - Promotional campaigns
- `holidays` - Holiday calendar
- `events` - Special events
- `weather` - Weather conditions
- `competitor` - Competitor data
- `economic` - Economic indicators

## Project Structure

```
ForecastIQ/
├── backend/
│   ├── app/
│   │   ├── api/routes/         # API endpoints
│   │   ├── schemas/            # Pydantic models
│   │   └── services/
│   │       ├── forecasting/
│   │       │   ├── models/     # 9 forecasting models
│   │       │   ├── model_selector.py  # Auto-selection
│   │       │   ├── ensemble.py        # Ensemble methods
│   │       │   └── marketing_mix.py   # Adstock/saturation
│   │       └── data_processor/  # Data handling
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/              # Dashboard, Upload, Forecast, Results
│       ├── components/         # FileUploader, ParametersPanel, WhatIfSimulator
│       └── services/api.ts     # API client
├── templates/                  # CSV templates for external data
├── docker-compose.yml
└── start-with-docker.bat
```

## Tech Stack

- **Backend**: Python FastAPI
- **Frontend**: React + Material UI + Vite
- **ML**: statsmodels, prophet, lightgbm, xgboost
- **Charts**: Chart.js

## License

MIT License
