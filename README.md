# ForecastIQ

Advanced Time Series Forecasting Platform with ML-powered model selection and ensemble methods.

## Features

- **Multiple Forecasting Models**: ARIMA, SARIMAX, Prophet, LightGBM, Weighted Moving Average
- **Auto Model Selection**: AI-powered recommendations based on data patterns
- **Baseline Trend Extraction**: Separate baseline trend from forecast impact
- **Ensemble Methods**: Combine 2-3 models with weighted averaging
- **External Factors**: Media plan, promotions, holidays, and events support
- **Power User Controls**: Fine-tune hyperparameters for each model
- **Professional Material UI**: Clean, modern interface for demand planning

## Tech Stack

- **Backend**: Python FastAPI
- **Frontend**: React + Material UI + Vite
- **ML Libraries**: statsmodels, prophet, lightgbm

---

## Installation Options

### Option 1: Docker (Recommended)

The easiest setup - everything packaged together with one command.

1. **Install Docker Desktop**
   - Download from: https://www.docker.com/products/docker-desktop/
   - Install and start Docker Desktop

2. **Run ForecastIQ**
   ```
   Double-click: start-with-docker.bat
   ```
   Or run in terminal:
   ```bash
   docker-compose up -d
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

**To stop:**
```
Double-click: stop-docker.bat
```
Or run:
```bash
docker-compose down
```

---

### Option 2: Manual Setup (Without Docker)

If you prefer not to use Docker, install dependencies manually.

**Requirements:**
- Python 3.10+
- Node.js 18+

**Quick Setup:**
1. Double-click: `setup-without-docker.bat`
2. Follow the instructions

**Manual Setup:**

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Visit http://localhost:3000

---

## Usage Guide

### 1. Upload Data

Go to **Data Upload** and upload your data files:
- **Sales Data** (required): Historical sales with dates and values
- **Media Plan** (optional): Marketing spend by channel
- **Promotions** (optional): Discount campaigns
- **Holidays** (optional): Holiday calendar
- **Events** (optional): Special events

### 2. Analyze

System automatically analyzes your data:
- Detects trend (increasing/decreasing/stable)
- Identifies seasonality (weekly/monthly)
- Measures data variability (CV)
- Recommends best models

### 3. Configure Forecast

Choose models and settings:
- Select forecasting models
- Set forecast horizon (days/weeks/months)
- Enable/disable external factors
- **Power users**: Click "Model Parameters" to fine-tune hyperparameters

### 4. View Results

- **Forecast Chart**: Visualize predictions
- **Baseline vs Forecast**: See impact of promotions/media
- **Model Comparison**: Compare accuracy metrics (MAE, RMSE, MAPE)
- **Export**: Download CSV with all forecasts

---

## Forecasting Models

| Model | Best For | Key Parameters |
|-------|----------|----------------|
| **Prophet** | Seasonal data, holidays | changepoint_prior_scale, seasonality_mode |
| **ARIMA** | Stationary data | p, d, q orders |
| **SARIMAX** | Seasonal patterns | seasonal P, D, Q, period |
| **LightGBM** | Complex patterns, high variance | n_estimators, learning_rate, max_depth |
| **WMA** | Simple baseline, stable demand | window size |

---

## Project Structure

```
ForecastIQ/
├── backend/
│   ├── app/
│   │   ├── api/              # API routes
│   │   ├── core/             # Config, settings
│   │   ├── schemas/          # Pydantic models
│   │   └── services/
│   │       ├── forecasting/  # ML models, ensemble
│   │       └── data_processor/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/            # Page views
│   │   ├── services/         # API client
│   │   └── store/            # Zustand state
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── start-with-docker.bat     # Docker launcher
├── stop-docker.bat           # Docker stopper
├── setup-without-docker.bat  # Manual setup
└── README.md
```

---

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/forecast/upload/{file_type}` | Upload data file |
| POST | `/api/v1/forecast/analyze` | Analyze uploaded data |
| POST | `/api/v1/forecast/forecast` | Run forecast |
| GET | `/api/v1/forecast/forecast/{id}` | Get forecast results |
| GET | `/api/v1/forecast/forecasts` | List all forecasts |

---

## Troubleshooting

### Docker Issues

**"Docker is not running"**
- Start Docker Desktop application
- Wait for it to fully initialize

**Port already in use**
```bash
docker-compose down
# Change ports in docker-compose.yml if needed
```

### Backend Issues

**Module not found errors**
```bash
pip install -r requirements.txt
```

**Port 8000 in use**
```bash
# Change port in backend/app/core/config.py
# Or kill the process using the port
```

### Frontend Issues

**npm install fails**
```bash
# Clear cache and retry
cd frontend
rm -rf node_modules package-lock.json
npm install
```

---

## License

MIT License
