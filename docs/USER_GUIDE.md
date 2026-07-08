# ForecastIQ User Guide

**Version:** 1.0
**Last Updated:** July 8, 2026

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Running Your First Forecast](#running-your-first-forecast)
3. [Understanding Results](#understanding-results)
4. [Advanced Features](#advanced-features)
5. [Interpreting Accuracy Metrics](#interpreting-accuracy-metrics)
6. [FAQ & Troubleshooting](#faq--troubleshooting)

---

## Getting Started

### System Requirements

- **Browser:** Modern browser (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+)
- **Backend:** Python 3.11+, 4GB RAM minimum (8GB recommended)
- **Storage:** 10GB free disk space for data and models

### Installation

#### With Docker (Recommended)

```bash
# macOS / Linux
./start-with-docker.sh

# Windows
start-with-docker.bat
```

Then open:
- **UI:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/api/v1/health

#### Without Docker

```bash
# macOS / Linux
./setup-without-docker.sh

# Windows
setup-without-docker.bat
```

---

## Running Your First Forecast

### Step 1: Upload Your Data

1. Navigate to the **Forecast** page
2. Click **Upload Data** or drag-and-drop your file
3. Supported formats: CSV, Excel (.xlsx), Parquet

**Data Format Requirements:**

| Column | Required | Description |
|--------|----------|-------------|
| `date` | Yes | Date column (YYYY-MM-DD or similar) |
| `value` | Yes | Target metric to forecast (sales, units, revenue) |
| Category columns | No | e.g., `region`, `sku`, `store`, `product` |

**Example CSV:**
```csv
date,value,region,sku
2024-01-01,150,North,SKU001
2024-01-02,165,North,SKU001
2024-01-01,200,South,SKU002
```

### Step 2: Configure Your Forecast

| Setting | Description | Default |
|---------|-------------|---------|
| **Horizon** | Number of periods to forecast | 30 |
| **Frequency** | Data granularity | Daily |
| **Models** | Select forecasting models | Prophet |
| **Include Factors** | External data (promotions, holidays, etc.) | None |
| **Backtest Period** | Historical period to evaluate accuracy | Auto (20%) |

#### Key Settings Explained:

**Horizon:**
- Number of future periods to forecast
- Examples: 30 days, 12 weeks, 12 months

**Backtest Period:**
- **Auto (20%):** System uses latest 20% of data for accuracy evaluation
- **Custom:** Specify exact number of periods
- **None:** No accuracy evaluation (faster, no metrics)

**Models:**
- **Prophet:** Best for daily data with holidays/seasonality
- **ARIMA/SARIMAX:** Classical time series
- **LightGBM/XGBoost:** ML-based with external features
- **Ensemble:** Combine multiple models

### Step 3: Run Forecast

Click **Run Forecast** and wait for results (typically 30 seconds - 5 minutes depending on data size and model complexity).

---

## Understanding Results

### Results Page Overview

After running a forecast, you'll see:

```
┌─────────────────────────────────────────────────────────────┐
│  [Total Forecast]  [Forecast Accuracy]  [CV Accuracy]   │
│      $45,230            87% (Grade B)       85% (Grade B)   │
│                                                             │
│  [Total Uplift]    [Best Model]                             │
│      +12.3%              PROPHET                            │
└─────────────────────────────────────────────────────────────┘
```

### Forecast Chart Tab

- **Blue line:** Forecast values with confidence intervals
- **Gray line:** Baseline (what would happen without factors)
- **Shaded area:** Uplift attributed to external factors
- **Dots (if backtest enabled):** Actual historical values

**Interactions:**
- Hover for exact values
- Click legend to show/hide lines
- Zoom by clicking and dragging

### Model Comparison Tab

Bar chart comparing models across metrics:
- **MAE** (Mean Absolute Error) - Lower is better
- **RMSE** (Root Mean Square Error) - Lower is better
- **MAPE** (Mean Absolute Percentage Error) - Lower is better

### Accuracy Metrics Explained

| Metric | What It Measures | Ideal Value |
|--------|-----------------|-------------|
| **MAE** | Average absolute error in actual units | 0 |
| **RMSE** | Penalizes large errors more | 0 |
| **MAPE** | Average percentage error | 0% |
| **R²** | How well model fits data | 1.0 |
| **Forecast Accuracy %** | 100 - MAPE | 100% |
| **Accuracy Grade** | Letter grade (A-F) | A |

---

## Advanced Features

### Multi-Category Forecasting

Run separate forecasts for each category value (e.g., each SKU or region):

1. In forecast configuration, add category columns (e.g., `sku`, `region`)
2. System generates forecasts for each unique combination
3. Use category selector in results to switch between views

**Benefits:**
- More accurate per-SKU predictions
- Parallel execution for speed
- Category-level rankings

### Ensemble Models

Combine multiple models for better accuracy:

1. Select 2+ models in configuration
2. Choose ensemble method:
   - **Weighted Average:** Manual weights based on model performance
   - **Auto:** System optimizes weights based on CV performance

### External Factors

Include external data to improve forecast accuracy:

| Factor | Description | Data Needed |
|--------|-------------|-------------|
| **Promotions** | Sales lift from discounts | Historical promo dates and uplift % |
| **Holidays** | Country-specific holidays | Auto-detected or custom list |
| **Events** | Regional events, sports, etc. | Auto-detected |
| **Weather** | Temperature, precipitation | Historical + forecast weather |
| **Media Plan** | Ad spend by channel | Spend data by date |
| **Competitor** | Competitor pricing/activity | Historical competitor data |
| **Economic** | GDP, CPI, unemployment | Economic indicators |

### Train/Test Split

For proper held-out evaluation:

1. Set `train_test_split` (e.g., 0.8 = 80% train, 20% test)
2. Models train on 80% of data
3. Accuracy metrics computed on held-out 20%
4. Final forecast uses all data

**Recommended:** Use 0.8 for most cases (80/20 split)

### Backtest Zone

Visual comparison of forecast vs actuals:

1. Set `backtest_overlap` to number of periods (e.g., 30)
2. System re-trains model on data minus last 30 periods
3. Forecasts last 30 periods
4. Compare forecasted vs actual values in chart

**Use case:** "What would the model have predicted last month?"

---

## Interpreting Accuracy Metrics

### Forecast Accuracy % (Business-Friendly)

```
Accuracy % = 100 - MAPE

Example: MAPE of 13% → 87% Accuracy
```

**Interpretation:**
| Accuracy | Grade | Meaning |
|----------|-------|---------|
| 90-100% | A | Excellent - Highly reliable forecast |
| 80-89% | B | Good - Reliable for planning |
| 70-79% | C | Fair - Use with caution |
| 60-69% | D | Poor - Consider different approach |
| <60% | F | Failing - Review model/data |

### CV Accuracy vs Backtest Accuracy

| Metric | When Used | Business Meaning |
|--------|-----------|------------------|
| **Backtest Accuracy** | When `train_test_split < 1.0` or `backtest_overlap > 0` | Real held-out evaluation on unseen data |
| **CV Accuracy** | Always computed | Average across multiple folds of cross-validation |

**Which to trust?**
- **Backtest accuracy** is more representative of real-world performance
- **CV accuracy** provides stability indication across different train/test splits

### R² (Coefficient of Determination)

```
R² = 1 - (SS_res / SS_tot)

Where:
- SS_res = Sum of squared residuals (prediction errors)
- SS_tot = Sum of squared deviations from mean
```

**Interpretation:**
| R² Value | Meaning |
|----------|---------|
| 1.0 | Perfect prediction |
| 0.9-0.99 | Very good |
| 0.7-0.89 | Good |
| 0.5-0.69 | Moderate |
| <0.5 | Poor |

**Note:** R² can be negative if model is worse than simple average prediction.

---

## FAQ & Troubleshooting

### Q: Why is my forecast accuracy low?

**Common causes:**
1. Insufficient data (need at least 2x horizon periods)
2. High random variation in data
3. Missing important external factors (promotions, holidays)
4. Data quality issues (missing values, outliers)
5. Model not suited for data pattern

**Solutions:**
- Add more historical data
- Include relevant external factors
- Try different models
- Check for outliers/anomalies in data

### Q: How do I improve forecast accuracy?

1. **Add more data:** 2+ years of history preferred
2. **Include promotions:** Promotions significantly impact sales
3. **Add holidays:** Especially important for retail
4. **Use ensemble:** Combine multiple models
5. **Tune hyperparameters:** Advanced option in settings

### Q: What's the difference between backtest and CV accuracy?

- **CV (Cross-Validation):** System tests multiple train/test splits internally
- **Backtest:** System holds out explicit test period (last 20% or custom)

**Both are valid;** backtest is often more intuitive for business users.

### Q: Can I save and reuse models?

Yes! Use the **Model Registry**:

1. After running forecast, click **Save Model**
2. Give it a name and optional tags
3. Later, load saved model for quick forecasts
4. Or call `/v1/models/{id}/forecast` via API

### Q: How do I handle multiple SKUs or regions?

Use **Category Forecasting**:

1. Add category columns to your data (e.g., `sku`, `region`)
2. Select category columns in forecast configuration
3. System generates separate forecasts for each category
4. Compare performance across categories

### Q: What if my data has missing values?

**Options:**
1. **Let system handle it:** Built-in interpolation
2. **Pre-process:** Fill missing values before upload
3. **Use interpolation:** Linear or forward-fill

**Warning:** Large gaps (>30% missing) may significantly impact accuracy.

### Q: How far ahead can I forecast?

**General guidelines:**
- **Daily data:** Up to 365 days
- **Weekly data:** Up to 104 weeks (2 years)
- **Monthly data:** Up to 36 months (3 years)

**Note:** Accuracy typically decreases for longer horizons due to inherent uncertainty.

### Q: Why do I see different results on re-runs?

Possible causes:
1. **Stochastic models:** Some models (like ML) have randomness
2. **Different train/test splits:** If not using fixed seed
3. **Data changes:** New data uploaded
4. **Model updates:** Algorithm improvements

**Solution:** Use saved models for reproducible results.

---

## Appendix: Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl/Cmd + K` | Open command palette |
| `Ctrl/Cmd + S` | Save current forecast |
| `Ctrl/Cmd + E` | Export results |
| `Ctrl/Cmd + R` | Re-run forecast |
| `Esc` | Close modal/dialog |

---

## Appendix: API Quick Reference

### Run Forecast via API

```bash
curl -X POST http://localhost:8000/v1/forecast \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "data_file_id": "file-uuid",
    "horizon": 30,
    "models": ["prophet", "lightgbm"],
    "train_test_split": 0.8,
    "backtest_overlap": 0,
    "include_promotions": true,
    "include_holidays": true
  }'
```

### Get Results

```bash
curl http://localhost:8000/v1/forecast/result/forecast-uuid \
  -H "X-API-Key: your-api-key"
```

For full API documentation, visit http://localhost:8000/docs

---

## Support

- **Documentation:** [docs/](.)
- **API Docs:** http://localhost:8000/docs
- **Issues:** Report via GitHub Issues

---

*ForecastIQ - Advanced Forecasting for Data Scientists and Business Analysts*
