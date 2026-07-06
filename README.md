# ForecastIQ

Advanced Time Series Forecasting Platform with ML-powered model selection and ensemble methods.

## Features

- **Multiple Forecasting Models**: ARIMA, SARIMAX, Prophet, LightGBM, Weighted Moving Average
- **Auto Model Selection**: AI-powered recommendations based on data patterns
- **Ensemble Methods**: Combine 2-3 models with weighted averaging
- **External Factors**: Media plan, promotions, holidays, and events support
- **Professional Material UI**: Clean, modern interface for demand planning

## Tech Stack

- **Backend**: Python FastAPI
- **Frontend**: React + Material UI + Vite
- **ML Libraries**: statsmodels, prophet, lightgbm

## Quick Start

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:3000

## Project Structure

```
ForecastIQ/
├── backend/
│   ├── app/
│   │   ├── api/           # API routes
│   │   ├── core/          # Config, settings
│   │   ├── schemas/       # Pydantic models
│   │   └── services/     # Business logic
│   │       ├── forecasting/  # ML models, ensemble
│   │       └── data_processor/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page views
│   │   ├── services/      # API client
│   │   └── store/         # Zustand state
│   └── package.json
└── demand_forecaster/     # Your existing forecaster
```

## Usage

1. **Upload Data**: Go to Data Upload and upload your sales data (CSV/Excel)
2. **Analyze**: System automatically analyzes data patterns and recommends models
3. **Configure**: Select models, set horizon, choose external factors
4. **Forecast**: Run forecast and view results with charts and metrics

## API Endpoints

- `POST /api/v1/forecast/upload/{file_type}` - Upload data files
- `POST /api/v1/forecast/analyze` - Analyze uploaded data
- `POST /api/v1/forecast/forecast` - Run forecast
- `GET /api/v1/forecast/forecast/{id}` - Get forecast results
- `GET /api/v1/forecast/forecasts` - List all forecasts
