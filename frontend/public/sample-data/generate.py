"""
Generate realistic sample data files for ForecastIQ.

Outputs (in this script's directory):
  - realistic_sales_3y.csv   : 5 SKUs x 3 stores x ~1096 days
  - media_plan_sample.csv    : 4 channels x ~1096 days
  - promotions_sample.csv    : ~75 promotional events
  - holidays_sample.csv      : ~30 multi-country holidays
"""

import csv
import math
import os
import random
from datetime import date, timedelta

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

random.seed(42)

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

START = date(2022, 1, 1)
END   = date(2024, 12, 31)
NUM_DAYS = (END - START).days + 1  # 1096 days (3 calendar years, 2024 is leap)

DATES = [START + timedelta(days=i) for i in range(NUM_DAYS)]

# SKUs: (id, baseline_share, annual_growth_rate)
# share of total per-day base that this SKU commands
SKUS = [
    ("SKU001", 1.00, 0.12),  # flagship - baseline performer
    ("SKU002", 0.70, 0.10),  # budget line - smaller, slower growth
    ("SKU003", 1.30, 0.15),  # bestseller - higher share, stronger growth
    ("SKU004", 0.85, 0.08),  # mature product - small, slow
    ("SKU005", 1.15, 0.20),  # new premium launch - aggressive growth
]

# Stores: (id, scale_factor)
STORES = [
    ("NYC", 1.20),  # biggest market
    ("LA",  1.00),
    ("CHI", 0.80),  # smallest market
]

# Daily base = $5000/day average in 2022 across all SKU x store cells.
# 5 x 3 = 15 cells -> average cell base in 2022 ~= $333.
BASE_TOTAL_2022 = 5000.0
N_CELLS = len(SKUS) * len(STORES)

# Holiday spikes (date -> multiplier on top of all other seasonality)
HOLIDAY_SPIKES = {
    # New Year - moderate
    "2022-01-01": 1.40, "2023-01-01": 1.40, "2024-01-01": 1.40,
    # Valentine's Day
    "2022-02-14": 1.40, "2023-02-14": 1.40, "2024-02-14": 1.40,
    # Independence Day
    "2022-07-04": 1.30, "2023-07-04": 1.30, "2024-07-04": 1.30,
    # Singles Day
    "2022-11-11": 1.30, "2023-11-11": 1.30, "2024-11-11": 1.30,
    # Black Friday - massive spike
    "2022-11-25": 2.50, "2023-11-24": 2.50, "2024-11-29": 2.50,
    # Christmas Day - big dip (sales collapse, stores often closed-ish)
    "2022-12-25": 0.40, "2023-12-25": 0.40, "2024-12-25": 0.40,
}

# Promotional events (~6 per year, scattered)
# Format: date_str -> uplift multiplier (1.15-1.20)
PROMO_DATES = {
    # 2022
    "2022-03-15": 1.18, "2022-04-08": 1.15, "2022-06-20": 1.15,
    "2022-09-10": 1.17, "2022-10-22": 1.20, "2022-12-10": 1.16,
    # 2023
    "2023-02-25": 1.18, "2023-03-04": 1.16, "2023-05-13": 1.16,
    "2023-08-19": 1.17, "2023-10-14": 1.19, "2023-12-09": 1.15,
    # 2024
    "2024-02-17": 1.15, "2024-04-20": 1.18, "2024-06-15": 1.15,
    "2024-09-21": 1.17, "2024-10-26": 1.20, "2024-12-14": 1.16,
}

# ---------------------------------------------------------------------------
# Seasonality helpers
# ---------------------------------------------------------------------------

def trend_growth(d, base_year, growth_rate):
    """Compound annual growth applied from a base year."""
    days_from_base = (d - date(base_year, 1, 1)).days
    years = days_from_base / 365.25
    return (1.0 + growth_rate) ** years


def weekly_factor(d):
    """Higher on weekends, lower Mon-Wed."""
    wd = d.weekday()  # 0=Mon ... 6=Sun
    if wd in (0, 1, 2):    # Mon-Wed
        return 0.85
    if wd in (3, 4):       # Thu-Fri
        return 1.00
    return 1.30            # Sat-Sun


def yearly_factor(d):
    """
    Q4 holiday peak (Nov-Dec), January post-holiday dip, summer baseline.
    Smooth ramps so neighbouring days don't look disjointed.
    """
    m, day = d.month, d.day
    # Day-of-year 1..366
    doy = d.timetuple().tm_yday

    # Base curve: cosine with peak around day 350 (mid-Dec), trough day 15 (mid-Jan)
    # 365-day period centred so doy=350 -> peak, doy=15 -> trough.
    phase = (doy - 350) / 365.0 * 2.0 * math.pi
    seasonal = 1.15 + 0.30 * math.cos(phase)   # 0.85 .. 1.45

    # January clamp to 0.75 minimum (post-holiday dip)
    if m == 1:
        seasonal = min(seasonal, 0.80)
        if day <= 10:
            seasonal = 0.75

    return seasonal


# ---------------------------------------------------------------------------
# Sales generation
# ---------------------------------------------------------------------------

def compute_value(d, sku_share, sku_growth, store_factor):
    base = (BASE_TOTAL_2022 / N_CELLS) * sku_share * store_factor
    base *= trend_growth(d, 2022, sku_growth)
    base *= weekly_factor(d)
    base *= yearly_factor(d)

    ds = d.isoformat()
    if ds in HOLIDAY_SPIKES:
        base *= HOLIDAY_SPIKES[ds]
    if ds in PROMO_DATES:
        base *= PROMO_DATES[ds]

    # Gaussian noise: ~10% of base, then floored at zero.
    # Across 15 cells, total daily std ~ 0.10 * 5000 / sqrt(15) ~= $130,
    # which combined with seasonality and holidays reads as realistic.
    noise = random.gauss(0.0, 0.10 * base)
    return max(0.0, base + noise)


def write_sales():
    out = os.path.join(OUT_DIR, "realistic_sales_3y.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "sku", "store", "value"])
        for d in DATES:
            for sku, share, growth in SKUS:
                for store, sf in STORES:
                    v = compute_value(d, share, growth, sf)
                    w.writerow([d.isoformat(), sku, store, f"{v:.2f}"])
    return out, NUM_DAYS * len(SKUS) * len(STORES)


# ---------------------------------------------------------------------------
# Media plan
# ---------------------------------------------------------------------------

CHANNELS = [
    # (name, base_spend_per_day)
    ("TV",     3000.0),
    ("Digital",1500.0),
    ("Social",  800.0),
    ("Search",  500.0),
]


def media_yearly_factor(d):
    m, day = d.month, d.day
    if m == 1:
        # Post-holiday spend cut
        return 0.50 if day <= 15 else 0.70
    if m in (11, 12):
        return 1.50
    if m in (6, 7, 8):
        return 0.95
    return 1.00


def media_weekly_factor(d):
    # Marketers spend more Mon-Fri, less on weekends
    wd = d.weekday()
    if wd in (0, 1, 2, 3, 4):
        return 1.05
    return 0.80


def write_media():
    out = os.path.join(OUT_DIR, "media_plan_sample.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "channel", "spend", "reach", "impressions"])
        for d in DATES:
            yf = media_yearly_factor(d)
            wf = media_weekly_factor(d)
            for ch, base in CHANNELS:
                # Slight trend growth (~6%/yr) for media spend
                trend = trend_growth(d, 2022, 0.06)
                expected = base * yf * wf * trend
                spend = max(0.0, random.gauss(expected, 0.15 * expected))
                # Reach ~ spend * 80, impressions ~ spend * 150 (channel-dependent)
                ch_factor = {"TV": (80, 150), "Digital": (200, 800),
                             "Social": (250, 600), "Search": (180, 400)}[ch]
                reach = int(spend * ch_factor[0] * random.uniform(0.9, 1.1))
                imps  = int(spend * ch_factor[1] * random.uniform(0.9, 1.1))
                w.writerow([d.isoformat(), ch, f"{spend:.2f}", reach, imps])
    return out, NUM_DAYS * len(CHANNELS)


# ---------------------------------------------------------------------------
# Promotions
# ---------------------------------------------------------------------------

PROMO_TYPES = ["percent", "bogo", "bundle", "flash_sale"]


def write_promotions():
    out = os.path.join(OUT_DIR, "promotions_sample.csv")
    rng = random.Random(7)
    rows = []

    # Build ~6 events/year x 3 years = 18 "anchor" events that match PROMO_DATES
    for ds in PROMO_DATES.keys():
        rows.append((ds, rng.choice(PROMO_TYPES), rng.randint(5, 30)))

    # Add ~60 additional scattered events through the period
    extra = 60
    used = set(rows)
    while len(rows) < 18 + extra:
        offset = rng.randint(0, NUM_DAYS - 1)
        d = START + timedelta(days=offset)
        ds = d.isoformat()
        if ds in used:
            continue
        used.add(ds)
        # discount: percent & flash_sale tend to be larger, bogo/bundle smaller
        t = rng.choice(PROMO_TYPES)
        if t in ("percent", "flash_sale"):
            disc = rng.randint(10, 30)
        else:
            disc = rng.randint(5, 20)
        rows.append((ds, t, disc))

    rows.sort(key=lambda r: r[0])
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "promo_type", "discount"])
        for ds, t, disc in rows:
            w.writerow([ds, t, disc])
    return out, len(rows)


# ---------------------------------------------------------------------------
# Holidays (multi-country)
# ---------------------------------------------------------------------------

HOLIDAYS = [
    # US holidays
    ("2022-01-01", "New Year's Day",          "US", 1.5),
    ("2022-01-17", "Martin Luther King Jr.",  "US", 1.2),
    ("2022-02-21", "Presidents' Day",         "US", 1.2),
    ("2022-05-30", "Memorial Day",            "US", 1.6),
    ("2022-07-04", "Independence Day",        "US", 1.8),
    ("2022-09-05", "Labor Day",               "US", 1.5),
    ("2022-11-24", "Thanksgiving",            "US", 2.2),
    ("2022-11-25", "Black Friday",            "US", 3.0),
    ("2022-11-28", "Cyber Monday",            "US", 2.8),
    ("2022-12-25", "Christmas Day",           "US", 1.3),
    # 2023
    ("2023-01-01", "New Year's Day",          "US", 1.5),
    ("2023-07-04", "Independence Day",        "US", 1.8),
    ("2023-11-23", "Thanksgiving",            "US", 2.2),
    ("2023-11-24", "Black Friday",            "US", 3.0),
    ("2023-11-27", "Cyber Monday",            "US", 2.8),
    ("2023-12-25", "Christmas Day",           "US", 1.3),
    # 2024
    ("2024-01-01", "New Year's Day",          "US", 1.5),
    ("2024-07-04", "Independence Day",        "US", 1.8),
    ("2024-11-28", "Thanksgiving",            "US", 2.2),
    ("2024-11-29", "Black Friday",            "US", 3.0),
    ("2024-12-02", "Cyber Monday",            "US", 2.8),
    ("2024-12-25", "Christmas Day",           "US", 1.3),
    # UK
    ("2022-04-15", "Good Friday",             "UK", 1.6),
    ("2022-04-18", "Easter Monday",           "UK", 1.4),
    ("2022-08-29", "Summer Bank Holiday",     "UK", 1.5),
    ("2022-12-26", "Boxing Day",              "UK", 2.0),
    ("2023-04-07", "Good Friday",             "UK", 1.6),
    ("2023-04-10", "Easter Monday",           "UK", 1.4),
    ("2023-12-26", "Boxing Day",              "UK", 2.0),
    ("2024-03-29", "Good Friday",             "UK", 1.6),
    ("2024-04-01", "Easter Monday",           "UK", 1.4),
    # India
    ("2022-10-24", "Diwali",                  "IN", 2.5),
    ("2022-11-08", "Dhanteras",               "IN", 1.8),
    ("2023-11-12", "Diwali",                  "IN", 2.5),
    ("2023-11-10", "Dhanteras",               "IN", 1.8),
    ("2024-11-01", "Diwali",                  "IN", 2.5),
    ("2024-10-29", "Dhanteras",               "IN", 1.8),
]


def write_holidays():
    out = os.path.join(OUT_DIR, "holidays_sample.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "name", "country", "impact"])
        for ds, name, country, impact in HOLIDAYS:
            w.writerow([ds, name, country, impact])
    return out, len(HOLIDAYS)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sales_path, sales_rows = write_sales()
    media_path, media_rows = write_media()
    promo_path, promo_rows = write_promotions()
    holi_path,  holi_rows  = write_holidays()

    print(f"days         : {NUM_DAYS}")
    print(f"sales        : {sales_rows:>6} rows  -> {sales_path}")
    print(f"media        : {media_rows:>6} rows  -> {media_path}")
    print(f"promotions   : {promo_rows:>6} rows  -> {promo_path}")
    print(f"holidays     : {holi_rows:>6} rows  -> {holi_path}")
