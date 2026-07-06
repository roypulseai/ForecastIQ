# Public Sample Data

This folder contains sample datasets for demonstrating ForecastIQ's capabilities.

## Sales Data

### sku_daily_sales.csv
Multi-level retail sales data with product hierarchy:
- **10 SKUs** across different categories
- **Daily sales** for 10+ days (extendable)
- **4 Regions**: North, South, East, West
- **Multiple Stores**: One per region

### Product Hierarchy
```
SKU → Product → Category → Sub-Category → Portfolio

Examples:
SKU_001 (Organic Almonds 500g)
  → Product: Organic Almonds 500g
  → Category: Snacks
  → Sub-Category: Nuts
  → Portfolio: Healthy Snacks
```

## External Data

### media_plan.csv
Multi-channel marketing spend data:
- TV, Digital, Social, Print, Radio, Outdoor
- Daily spend in currency units

### promotions.csv
Promotional campaign data:
- Percentage discounts, BOGO, Cash discounts
- Applies to specific SKUs

### holidays.csv
Holiday calendar with impact factors:
- National, religious, commercial holidays
- Impact factor (0.3 = very low, 2.8 = very high)

### events.csv
Special events data:
- Festivals, concerts, community events
- Expected attendance and impact

### weather.csv
Weather conditions:
- Temperature, rainfall, humidity
- Weather codes for conditions

### competitor_pricing.csv
Competitor data:
- Competitor pricing and market share
- Promotion activity flags

### economic_indicators.csv
Economic indicators (monthly):
- GDP growth, Consumer confidence
- CPI, Unemployment, Retail sales index

## Usage

1. Upload `sku_daily_sales.csv` as your sales data
2. Upload external data files as needed
3. Run forecasting at SKU level
4. Aggregate results to higher levels (product, category, portfolio)

## Aggregation Capabilities

### Time Rolling
- Daily → Weekly
- Daily → Fortnight (2 weeks)
- Daily → Monthly
- Daily → Quarterly
- Daily → Yearly

### Product Aggregation
- SKU Level (most granular)
- Product Level
- Category Level
- Sub-Category Level
- Portfolio Level (least granular)

### Regional Aggregation
- Store Level
- Region Level
- National (All Stores Combined)

## Sample Hierarchy

| SKU | Product | Category | Sub-Category | Portfolio |
|-----|---------|----------|--------------|-----------|
| SKU_001 | Organic Almonds 500g | Snacks | Nuts | Healthy Snacks |
| SKU_002 | Premium Cashews 250g | Snacks | Nuts | Premium Snacks |
| SKU_003 | Greek Yogurt 500g | Dairy | Yogurt | Dairy Products |
| SKU_004 | Sparkling Water 6-Pack | Beverages | Water | Soft Drinks |
| SKU_005 | Green Tea 100 Bags | Beverages | Tea | Hot Beverages |
| SKU_006 | Dark Chocolate 200g | Snacks | Chocolate | Confectionery |
| SKU_007 | Whole Milk 1L | Dairy | Milk | Dairy Products |
| SKU_008 | Orange Juice 2L | Beverages | Juice | Fresh Juice |
| SKU_009 | Chicken Breast 500g | Meat | Poultry | Fresh Meat |
| SKU_010 | Olive Oil 500ml | Pantry | Cooking Oil | Premium Pantry |
