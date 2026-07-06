import argparse
import sys
import pandas as pd
from demand_forecaster.forecaster import AttributeAwareForecaster

def forecast_cli():
    parser = argparse.ArgumentParser(description="Demand Forecaster CLI")

    parser.add_argument("--sales", help="Path to sales CSV file")
    parser.add_argument("--events", help="Path to events CSV file (optional)")
    parser.add_argument("--freq", help="Forecast frequency: D, W, M")
    parser.add_argument("--horizon", type=int, help="Number of periods ahead")
    parser.add_argument("--horizon_start", help="Start date for forecast (YYYY-MM-DD)")
    parser.add_argument("--attributes", help="Comma-separated attribute columns")
    parser.add_argument("--output", help="Output forecast CSV filename")

    args = parser.parse_args()

    # -----------------------------
    # Interactive Mode if no flags
    # -----------------------------
    if len(sys.argv) == 1:
        print("\nWelcome to Demand Forecaster CLI (Interactive Mode) 🚀\n")

        args.sales = input("Step 1/7: Enter path to sales CSV: ").strip()
        use_events = input("Step 2/7: Do you have events CSV? (y/n): ").strip().lower()
        if use_events == "y":
            args.events = input("Please enter path to events CSV: ").strip()

        args.freq = input("Step 3/7: Forecast frequency (D/W/M): ").strip()
        args.horizon = int(input("Step 4/7: Horizon (number of periods): ").strip())
        args.horizon_start = input("Step 5/7: Forecast start date (YYYY-MM-DD): ").strip()

        use_attr = input("Step 6/7: Use attributes (Region, SKU, etc.)? (y/n): ").strip().lower()
        if use_attr == "y":
            args.attributes = input("Enter attribute columns (comma separated): ").strip()

        args.output = input("Step 7/7: Output file name [forecast.csv]: ").strip() or "forecast.csv"

    # -----------------------------
    # Load Data
    # -----------------------------
    sales_df = pd.read_csv(args.sales)
    events_df = pd.read_csv(args.events) if args.events else None
    attributes = args.attributes.split(",") if args.attributes else None

    # -----------------------------
    # Run Forecast
    # -----------------------------
    forecaster = AttributeAwareForecaster(
        horizon_freq=args.freq,
        attributes=attributes
    )
    forecaster.fit(sales_df, events_df=events_df)
    forecast_df = forecaster.forecast(
        horizon_start=args.horizon_start,
        horizon_periods=args.horizon
    )

    forecast_df.to_csv(args.output, index=False)
    print(f"\n✅ Forecast complete! Saved to {args.output}\n")

if __name__ == "__main__":
    forecast_cli()
