# Demand Forecaster 📦

A Python package for **demand forecasting** that combines simple statistical methods with empirical factors like promotions, holidays, and events.  
It is designed for **demand planners** (via CLI, simple workflows) and **analysts** (via Python API, notebooks).

---

## ✨ Features
- Forecast horizons: **Daily, Weekly, Monthly**
- Methods: Weighted Moving Average, Median (user-defined weights, trimmed median)
- Factors: Promotions, Discounts, Events, Holidays, Weather (optional)
- Supports **hierarchical forecasting** (Region, Store, Item, etc.)
- CLI tool for planners (no coding needed)
- Notebook + API for analysts (advanced recipes included)
- User-defined **lookback windows** per frequency

---

## 📂 Folder Structure
```
demand_forecaster_proj/
│── demand_forecaster/         # Core package
│── examples/                  # Example data & notebooks
│   ├── dummy_sales.csv
│   ├── dummy_events.csv
│   ├── dummy_promotions.csv
│   ├── dummy_weather.csv
│   ├── dummy_future_promos.csv
│   └── demo_notebook.ipynb
│── outputs/                   # Forecast results
│── README.md                  # This file
```

---

# 1️⃣ For Demand Planners (Non-Technical Users)

### Installation
```bash
pip install -r requirements.txt
pip install .
```

### Run a Forecast from CLI
Example: Daily forecast for 14 days
```bash
forecast-cli run --sales examples/dummy_sales.csv --events examples/dummy_events.csv --promos examples/dummy_promotions.csv --freq D --horizon 14 --output outputs/forecast_daily.csv
```

Weekly forecast for 8 weeks
```bash
forecast-cli run --sales examples/dummy_sales.csv --freq W --horizon 8 --output outputs/forecast_weekly.csv
```

Monthly forecast for 6 months
```bash
forecast-cli run --sales examples/dummy_sales.csv --freq M --horizon 6 --output outputs/forecast_monthly.csv
```

### Example CLI Output
```
2025-08-21, East, S1, I1, 120.5
2025-08-22, East, S1, I1, 130.2
...
```

### Example Chart (open in Excel / BI tool)
The `outputs/` folder will contain `.csv` forecasts that can be directly visualized.

---

# 2️⃣ For Analysts (Python Users)

### Import & Forecast in Python
```python
import pandas as pd
from demand_forecaster.forecaster import AttributeAwareForecaster

sales = pd.read_csv("examples/dummy_sales.csv")
events = pd.read_csv("examples/dummy_events.csv")
promos = pd.read_csv("examples/dummy_promotions.csv")

model = AttributeAwareForecaster(
    method="wma",
    attributes=["region","store","item"],
    horizon_freq="D",
    lookback_config={"D":8, "W":8, "M":5}
)

forecast = model.forecast(
    forecast_date="2025-08-21",
    horizon=14,
    sales_data=sales,
    event_data=events,
    promo_data=promos
)
print(forecast.head())
```

---

## 🔬 Advanced Recipes (Analysts)

These are available in `examples/demo_notebook.ipynb`

- **Custom Weighted Moving Average (Exponential Decay)**
- **Trimmed Median**
- **ML Uplift Model** (XGBoost on discounts/events)
- **Weather Factor** (rain/temp adjustment)
- **Hierarchical Overrides** (different methods per segment)
- **Forecast Reconciliation** (align store-level with region-level totals)

Example (Weather Uplift):
```python
import pandas as pd

weather = pd.read_csv("examples/dummy_weather.csv")

def weather_uplift(row):
    if row["rain_mm"] > 20: return 1.15
    if row["temp_c"] > 35: return 0.90
    return 1.0

forecast_weather = model.forecast(
    "2025-08-21", 14,
    future_factors={"weather": weather_uplift}
)
```

---

## 📊 Outputs
Forecasts are stored in `outputs/forecast_<freq>.csv` with columns:
```
date, region, store, item, forecast
```

---

## 🧑‍🤝‍🧑 Who Should Use This?
- **Planners** → Run forecasts via CLI without coding
- **Analysts** → Extend, customize, add ML/advanced factors in Python

---

## 🚀 Next Steps
- Try the CLI examples
- Explore the notebook in `examples/demo_notebook.ipynb`
- Customize advanced recipes for your business use case

---

© 2025 Demand Forecaster Team
