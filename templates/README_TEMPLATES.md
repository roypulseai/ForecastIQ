# ForecastIQ Data Templates

This folder contains CSV templates for all supported external data types.

## How to Use

1. Download the template for your data type
2. Fill in your data following the column structure
3. Upload via the ForecastIQ Data Upload page

## Template Guide

| Template | Required | Description |
|----------|----------|-------------|
| `01_sales_template.csv` | **Yes** | Historical sales data with dates and values |
| `02_media_plan_template.csv` | No | Marketing spend by channel (TV, digital, social, etc.) |
| `03_promotions_template.csv` | No | Promotional campaigns with discount details |
| `04_holidays_template.csv` | No | Holiday calendar with impact factors |
| `05_events_template.csv` | No | Special events that affect demand |
| `06_weather_template.csv` | No | Weather conditions (temperature, rain, snow) |
| `07_competitor_template.csv` | No | Competitor pricing and market share |
| `08_economic_template.csv` | No | Economic indicators (GDP, inflation, etc.) |

## Column Definitions

### Sales (Required)
- `date` - Date in YYYY-MM-DD format
- `sales` - Sales value/revenue/quantity
- `region` - Geographic region (optional)
- `store` - Store identifier (optional)
- `item` - Product/item identifier (optional)

### Media Plan
- `date` - Date in YYYY-MM-DD format
- `channel` - Marketing channel (tv, digital, social, print, radio, outdoor)
- `spend` - Amount spent in currency
- `reach` - Audience reach (optional)
- `impressions` - Number of impressions (optional)
- `ctr` - Click-through rate (optional)
- `cpc` - Cost per click (optional)

### Promotions
- `date` - Start date of promotion
- `promo_id` - Unique promotion identifier
- `promo_type` - Type (percentage, buy_x_get_y, cash_discount, bogo)
- `discount` - Discount percentage
- `original_price` - Original price before promo
- `promo_price` - Promo price
- `eligible_items` - Items covered by promotion

### Holidays
- `date` - Holiday date
- `holiday_name` - Name of holiday
- `holiday_type` - Type (national, religious, commercial, observance)
- `impact_factor` - Multiplier for holiday effect (1.0 = no effect, 2.0 = double)
- `affected_region` - Geographic scope (all, US, UK, etc.)

### Events
- `date` - Event date
- `event_name` - Name of event
- `event_type` - Type (festival, sports, concert, community, commercial)
- `impact_factor` - Expected demand multiplier
- `expected_attendance` - Number of attendees (optional)
- `location` - Event location (optional)

### Weather
- `date` - Date
- `temperature` - Temperature in Celsius
- `rain_mm` - Rainfall in millimeters
- `snow_mm` - Snowfall in millimeters (optional)
- `humidity` - Humidity percentage (optional)
- `wind_speed` - Wind speed km/h (optional)
- `weather_code` - Code (clear, cloudy, rain, snow, storm)

### Competitor Data
- `date` - Date
- `competitor_name` - Name of competitor
- `competitor_price` - Competitor's price
- `market_share` - Competitor's market share percentage
- `promotion_flag` - 1 if competitor is running promo, 0 otherwise

### Economic Indicators
- `date` - Date (typically monthly)
- `gdp` - GDP value
- `growth_rate` - GDP growth rate percentage
- `consumer_confidence` - Consumer confidence index
- `inflation` - Inflation rate percentage
- `cpi` - Consumer Price Index

## Tips

1. **Date Format**: Always use YYYY-MM-DD format
2. **Missing Data**: Leave cells empty or use NA for missing values
3. **Currency**: Use consistent currency across all files
4. **Units**: Ensure consistent units (e.g., Celsius vs Fahrenheit)
5. **File Size**: Maximum file size is 100MB
6. **Encoding**: Use UTF-8 encoding
