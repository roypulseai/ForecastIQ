# Data Formats

Each file type has a recommended set of columns. The processor auto-detects common alternatives (case-insensitive, snake_case or camelCase, etc.) and standardizes them.

## Sales data (`file_type: "sales"`)

Required:
- A **date** column (any of: `date`, `ds`, `timestamp`, `datetime`, `order_date`, `sales_date`, `transaction_date`, `day`, `time`, `report_date`, `calendar_date`).
- A **numeric value** column (any of: `value`, `y`, `sales`, `demand`, `revenue`, `quantity`, `qty`, `units`, `amount`).

Optional (preserved as-is):
- Entity columns: `sku`, `product`, `category`, `sub_category`, `store`, `region`, `portfolio`, `brand`.

Example:
```csv
date,sku,store,value
2024-01-01,SKU001,NYC,150.50
2024-01-01,SKU001,LA,120.00
2024-01-02,SKU001,NYC,165.25
2024-01-02,SKU001,LA,130.00
```

## Media plan (`file_type: "media_plan"`)

Required:
- A **spend** column (any of: `spend`, `media_spend`, `cost`, `amount`, `investment`).
- A **date** column.
- A **channel** column (recommended; default: `default`).

Optional:
- `reach`, `impressions`

Example:
```csv
date,channel,spend
2024-01-01,TV,5000
2024-01-01,Digital,3000
2024-01-01,Social,1500
```

## Promotions (`file_type: "promotions"`)

Required:
- A **date** column.
- A **discount** column (any of: `discount`, `discount_pct`, `discount_percent`, `discount_amount`, `off`, `pct_off`).

Optional:
- `promo_id`, `promo_type`, `original_price`, `promo_price`

Example:
```csv
date,discount,promo_type
2024-01-15,20,percent
2024-02-10,15,percent
2024-03-25,10,bundle
```

## Holidays (`file_type: "holidays"`)

Required:
- A **date** column.
- An **impact** column (any of: `impact`, `impact_factor`, `lift`, `multiplier`, `weight`, `holiday_impact`).

Optional:
- `name`, `type`

Example:
```csv
date,name,impact
2024-01-01,New Year,2.5
2024-07-04,Independence Day,2.0
2024-12-25,Christmas,3.0
```

Impact values are multipliers: `1.0` = no effect, `2.0` = doubles demand, `0.5` = halves it. These get fed into the models as exogenous regressors.

## Events (`file_type: "events"`)

Same structure as holidays:

```csv
date,name,impact
2024-02-14,Valentine's Day,1.8
2024-11-29,Black Friday,3.0
```

## Weather (`file_type: "weather"`)

Required:
- A **date** column.
- A **temperature** column (any of: `temperature`, `temp`, `temp_c`, `temp_f`, `avg_temp`).

Optional:
- `humidity`, `rainfall` / `rain` / `precipitation`, `snowfall` / `snow`

Example:
```csv
date,temperature,humidity,rainfall
2024-01-01,2.5,65,0.0
2024-01-02,3.1,72,2.3
2024-01-03,4.8,80,5.1
```

## Competitor (`file_type: "competitor"`)

Required:
- A **date** column.
- A **competitor price** column (any of: `competitor_price`, `price`, `comp_price`, `rival_price`).

Optional:
- `competitor_name` / `name`, `market_share` / `share`, `promotion_flag` / `is_promo` / `on_promo`

Example:
```csv
date,competitor_price,market_share
2024-01-01,29.99,0.15
2024-01-15,27.50,0.18
2024-02-01,29.99,0.15
```

## Economic indicators (`file_type: "economic"`)

Required:
- A **date** column.

Optional (any of these can be included):
- `gdp`, `growth_rate`, `consumer_confidence`, `inflation`, `cpi`, `unemployment`, `interest_rate`, `indicator_value`

All numeric columns are kept and used as exogenous regressors.

Example:
```csv
date,inflation,unemployment,consumer_confidence
2024-01-01,3.2,3.7,102.5
2024-04-01,3.4,3.9,98.1
2024-07-01,2.9,4.1,101.3
2024-10-01,2.6,4.0,104.2
```

## Tips

- **Dates**: ISO format (`YYYY-MM-DD`) is preferred. Other formats are auto-detected but may have edge cases.
- **Encoding**: UTF-8. Excel files (`.xlsx`) are also supported.
- **Duplicates**: Rows with the same date are aggregated (sum for numeric, first for categorical).
- **Missing values**: Numeric NaNs are filled with 0 (sales) or column mean (weather).
- **Large files**: Files >50 MB are read in chunks with dtype downcasting. The DataProcessor's `downsample_for_forecasting()` is applied to very long sales series.

## Sample data

`public_data/` in the repository contains small example files for each type.
