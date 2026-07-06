
import argparse, json, sys, pandas as pd
from .forecaster import AttributeAwareForecaster

def main():
    p = argparse.ArgumentParser(description='Demand Forecaster CLI')
    p.add_argument('--sales', required=True, help='Path to sales CSV')
    p.add_argument('--events', required=False, default=None, help='Path to events CSV')
    p.add_argument('--future_plan', required=False, default=None, help='Path to future plan CSV')
    p.add_argument('--attributes', nargs='*', default=[], help='Attribute columns, e.g., region store item')
    p.add_argument('--horizon_freq', choices=['D','W','M'], default='D', help='Forecast frequency')
    # Horizon options
    p.add_argument('--horizon_start', help='Start date (YYYY-MM-DD)')
    p.add_argument('--horizon_periods', type=int, help='Number of periods')
    p.add_argument('--horizon_csv', help='Optional CSV with a date column for explicit horizon dates')
    # Method & flags
    p.add_argument('--method', choices=['wma','median'], default='wma')
    p.add_argument('--use_trends', action='store_true')
    p.add_argument('--use_promotions', action='store_true')
    p.add_argument('--use_events', action='store_true')
    p.add_argument('--event_lag_days', type=int, default=0, help='Shift events by N days (can be negative)')
    p.add_argument('--week_start', choices=['MON','TUE','WED','THU','FRI','SAT','SUN'], default='MON')
    # Lookback config
    p.add_argument('--lookback_json', help='JSON string or path to JSON file for lookback config')
    # Column names
    p.add_argument('--date_col', default='date')
    p.add_argument('--target_col', default='sales')
    p.add_argument('--promo_col', default='promo_flag')
    p.add_argument('--discount_col', default='discount')
    p.add_argument('--event_name_col', default='event_name')
    # Output
    p.add_argument('--out', required=True, help='Output CSV path')

    args = p.parse_args()

    # Load datasets
    sales = pd.read_csv(args.sales, parse_dates=[args.date_col])
    events = pd.read_csv(args.events) if args.events else None
    future_plan = pd.read_csv(args.future_plan, parse_dates=[args.date_col]) if args.future_plan else None

    # Load/parse lookback config
    lb = {'default': {'D':8,'W':6,'M':5}}
    if args.lookback_json:
        txt = args.lookback_json
        try:
            if txt.strip().endswith('.json'):
                with open(txt, 'r') as f:
                    lb = json.load(f)
            else:
                lb = json.loads(txt)
        except Exception as e:
            print(f"Failed to parse lookback_json: {e}", file=sys.stderr)

    # Build model
    model = AttributeAwareForecaster(method=args.method,
                                     attributes=args.attributes,
                                     horizon_freq=args.horizon_freq,
                                     lookback_config=lb,
                                     use_trends=args.use_trends,
                                     use_promotions=args.use_promotions,
                                     use_events=args.use_events,
                                     date_col=args.date_col,
                                     target_col=args.target_col,
                                     promo_col=args.promo_col,
                                     discount_col=args.discount_col,
                                     event_name_col=args.event_name_col,
                                     week_start=args.week_start,
                                     event_lag_days=args.event_lag_days)

    model.fit(sales_df=sales, events_df=events)

    # Horizon
    horizon_dates = None
    if args.horizon_csv:
        hd = pd.read_csv(args.horizon_csv, parse_dates=[args.date_col])
        horizon_dates = hd[args.date_col].values

    fcst = model.forecast(horizon_dates=horizon_dates,
                          horizon_start=args.horizon_start,
                          horizon_periods=args.horizon_periods,
                          future_plan=future_plan,
                          future_events=events)

    fcst.to_csv(args.out, index=False)
    print(f"Forecast saved to {args.out}")

if __name__ == '__main__':
    main()
