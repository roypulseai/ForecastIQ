"""Smart regional event detection for forecasting.

Provides:
  * Country holidays via the `holidays` library (100+ countries)
  * Moveable / cultural feast date computation (Easter, CNY, Diwali, Holi,
    Ramadan/Eid, Black Friday, etc.)
  * Historical impact analysis — compares sales on event dates vs. a rolling
    baseline window to compute per-event impact factors
  * Per-region segmentation when the sales DataFrame contains region columns

Usage:
    detector = AutoEventDetector(country="IN", sales_df=df,
                                  date_col="date", value_col="value")
    events_df = detector.run()  # DataFrame matching the 'holidays' schema
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# =========================================================================
# Moveable feast date computation
# =========================================================================

# ------------------------------------------------------------------ Easter

def _easter_western(year: int) -> date:
    """Computus (Anonymous Gregorian algorithm)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    month = (h + l_ - 7 * m + 114) // 31
    day = ((h + l_ - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _eastern_orthodox(year: int) -> date:
    """Orthodox Easter (Julian computus + Gregorian offset)."""
    a = year % 4
    b = year % 7
    c = year % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    month = (d + e + 114) // 31
    day = ((d + e + 114) % 31) + 1
    offset = 13  # Valid for 1900-2099
    return date(year, month, day) + timedelta(days=offset)


# ------------------------------------------------------------ Lunar events

CHINESE_NEW_YEAR_DATES: Dict[int, date] = {
    2020: date(2020, 1, 25), 2021: date(2021, 2, 12),
    2022: date(2022, 2, 1), 2023: date(2023, 1, 22),
    2024: date(2024, 2, 10), 2025: date(2025, 1, 29),
    2026: date(2026, 2, 17), 2027: date(2027, 2, 6),
    2028: date(2028, 1, 26), 2029: date(2029, 2, 13),
    2030: date(2030, 2, 3), 2031: date(2031, 1, 23),
    2032: date(2032, 2, 11), 2033: date(2033, 1, 31),
    2034: date(2034, 2, 19), 2035: date(2035, 2, 8),
}

DIWALI_DATES: Dict[int, date] = {
    2020: date(2020, 11, 14), 2021: date(2021, 11, 4),
    2022: date(2022, 10, 24), 2023: date(2023, 11, 12),
    2024: date(2024, 10, 31), 2025: date(2025, 10, 20),
    2026: date(2026, 11, 8), 2027: date(2027, 10, 29),
    2028: date(2028, 11, 16), 2029: date(2029, 11, 5),
    2030: date(2030, 10, 26), 2031: date(2031, 11, 14),
    2032: date(2032, 11, 2), 2033: date(2033, 10, 22),
    2034: date(2034, 11, 10), 2035: date(2035, 10, 31),
}

HOLI_DATES: Dict[int, date] = {
    2020: date(2020, 3, 10), 2021: date(2021, 3, 29),
    2022: date(2022, 3, 18), 2023: date(2023, 3, 8),
    2024: date(2024, 3, 25), 2025: date(2025, 3, 14),
    2026: date(2026, 3, 3), 2027: date(2027, 3, 22),
    2028: date(2028, 3, 11), 2029: date(2029, 3, 29),
    2030: date(2030, 3, 19), 2031: date(2031, 3, 8),
    2032: date(2032, 3, 26), 2033: date(2033, 3, 15),
    2034: date(2034, 3, 5), 2035: date(2035, 3, 24),
}

RAMADAN_START_DATES: Dict[int, date] = {
    2020: date(2020, 4, 24), 2021: date(2021, 4, 13),
    2022: date(2022, 4, 2), 2023: date(2023, 3, 23),
    2024: date(2024, 3, 11), 2025: date(2025, 3, 1),
    2026: date(2026, 2, 18), 2027: date(2027, 2, 7),
    2028: date(2028, 1, 28), 2029: date(2029, 1, 16),
    2030: date(2030, 1, 5),     2031: date(2031, 2, 20),
    2032: date(2032, 1, 15), 2033: date(2033, 1, 4),
    2034: date(2034, 12, 15), 2035: date(2035, 12, 5),
}


# -------------------------------------------------------------- US retail

def _nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date:
    """Return the n-th occurrence of `weekday` (Mon=0 … Sun=6) in the month."""
    first = date(year, month, 1)
    first_dow = first.weekday()
    delta = (weekday - first_dow) % 7
    return first + timedelta(days=delta + 7 * (n - 1))


def _last_weekday_of_month(year: int, month: int, weekday: int) -> date:
    """Return the last occurrence of `weekday` in the month."""
    last = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    delta = (last.weekday() - weekday) % 7
    return last - timedelta(days=delta)


def _thanksgiving_us(year: int) -> date:
    return _nth_weekday_of_month(year, 11, 3, 4)  # 4th Thursday of Nov


def _black_friday(year: int) -> date:
    return _thanksgiving_us(year) + timedelta(days=1)  # Friday after Thanksgiving


def _cyber_monday(year: int) -> date:
    return _thanksgiving_us(year) + timedelta(days=4)  # Monday after Thanksgiving


def _mothers_day_us(year: int) -> date:
    return _nth_weekday_of_month(year, 5, 6, 2)  # 2nd Sunday of May


def _fathers_day_us(year: int) -> date:
    return _nth_weekday_of_month(year, 6, 6, 3)  # 3rd Sunday of Jun


# --------------------------------------------------------------- Sports

SPORTS_EVENTS: List[Dict[str, Any]] = [
    # FIFA World Cup years (every 4 years, Jun-Jul)
    {"name": "fifa_world_cup_start", "label": "FIFA World Cup",
     "type": "sports", "years": [2018, 2022, 2026, 2030, 2034],
     "start_month": 6, "start_day": 11, "duration_days": 32},
    # Summer Olympics (every 4 years, Jul-Aug)
    {"name": "summer_olympics_start", "label": "Summer Olympics",
     "type": "sports", "years": [2020, 2024, 2028, 2032],
     "start_month": 7, "start_day": 23, "duration_days": 17},
    # Super Bowl (1st Sunday of Feb)
    {"name": "super_bowl", "label": "Super Bowl",
     "type": "sports", "years": "__annual__",
     "compute": lambda y: _nth_weekday_of_month(y, 2, 6, 1)},
    # IPL (Indian Premier League, ~Mar-May, approximate start)
    {"name": "ipl_start", "label": "IPL Season",
     "type": "sports", "years": "__annual__",
     "start_month": 3, "start_day": 23, "duration_days": 60},
    # Cricket World Cup (every 4 years)
    {"name": "cricket_world_cup_start", "label": "Cricket World Cup",
     "type": "sports", "years": [2019, 2023, 2027, 2031],
     "start_month": 10, "start_day": 5, "duration_days": 46},
    # Tour de France (annual, Jul)
    {"name": "tour_de_france_start", "label": "Tour de France",
     "type": "sports", "years": "__annual__",
     "start_month": 7, "start_day": 1, "duration_days": 23},
]


# =========================================================================
# Event-to-country relevance map
# =========================================================================

# Maps event names to ISO country codes where they are relevant.
# "__all__" means relevant everywhere (New Year, Christmas).
# "__western__" means countries that observe Western Christian holidays.
# "__muslim__" means countries with significant Muslim population.
EVENT_COUNTRY_MAP: Dict[str, List[str] | str] = {
    # Global
    "new_year": "__all__",
    "new_year_eve": "__all__",
    "christmas": "__all__",
    "christmas_eve": "__all__",
    "valentines_day": "__all__",
    "halloween": "__all__",

    # Western Christian
    "easter_sunday": "__western__",
    "easter_monday": "__western__",
    "good_friday": "__western__",
    "ash_wednesday": "__western__",
    "pentecost": "__western__",

    # Orthodox
    "orthodox_easter": ["RU", "UA", "BY", "GR", "CY", "RO", "BG", "RS",
                        "MK", "MD", "GE", "AM"],

    # Islamic
    "ramadan_start": "__muslim__",
    "eid_al_fitr": "__muslim__",
    "eid_al_adha": "__muslim__",

    # Lunar / Asian
    "chinese_new_year": ["CN", "TW", "HK", "SG", "MY", "VN", "PH", "ID",
                         "TH", "KH", "LA", "MM", "BN"],
    "diwali": ["IN", "FJ", "GY", "MU", "MY", "NP", "SG", "SR", "TT", "LK",
               "AE", "QA", "OM", "BH", "KW", "SA"],
    "holi": ["IN", "NP"],

    # US-specific
    "thanksgiving": ["US"],
    "black_friday": ["US", "CA", "GB"],  # Spreading globally
    "cyber_monday": ["US", "CA", "GB"],
    "mothers_day": ["US", "CA", "AU", "NZ", "DE", "JP", "IN"],
    "fathers_day": ["US", "CA", "AU", "NZ", "DE", "JP", "IN"],
    "independence_day": ["US"],
    "memorial_day": ["US"],
    "labor_day": ["US"],

    # India
    "republic_day": ["IN"],
    "independence_day_india": ["IN"],
    "gandhi_jayanti": ["IN"],

    # UK / Commonwealth
    "boxing_day": ["GB", "AU", "NZ", "ZA", "CA", "HK", "MY", "SG"],

    # Japan
    "golden_week_japan": ["JP"],

    # China
    "golden_week_china": ["CN"],
    "singles_day": ["CN", "SG", "MY"],

    # Sports (global)
    "fifa_world_cup": "__all__",
    "summer_olympics": "__all__",
    "super_bowl": ["US", "CA"],
    "ipl": ["IN"],
    "cricket_world_cup": ["IN", "GB", "AU", "NZ", "ZA", "PK", "BD", "SL",
                          "AE", "SG", "MY", "KE"],
}

# Countries with majority Muslim population
MUSLIM_COUNTRIES: List[str] = [
    "SA", "IQ", "IR", "EG", "DZ", "MA", "SD", "PK", "BD", "ID",
    "MY", "NG", "TR", "AF", "YE", "SY", "TN", "SO", "NE", "ML",
    "SN", "LB", "JO", "PS", "AE", "QA", "KW", "OM", "BH",
]

# Western Christian countries 
WESTERN_COUNTRIES: List[str] = [
    "US", "CA", "GB", "DE", "FR", "IT", "ES", "PT", "NL", "BE",
    "CH", "AT", "PL", "CZ", "SK", "HU", "RO", "HR", "SI", "LT",
    "LV", "EE", "IE", "NO", "SE", "DK", "FI", "IS", "AU", "NZ",
    "ZA", "AR", "BR", "CL", "CO", "PE", "MX",
]


def _event_applies_to_country(event_name: str, country: str) -> bool:
    """Check whether an event is relevant for the given ISO country code."""
    mapping = EVENT_COUNTRY_MAP.get(event_name)
    if mapping is None:
        return False
    if mapping == "__all__":
        return True
    if mapping == "__western__":
        return country in WESTERN_COUNTRIES
    if mapping == "__muslim__":
        return country in MUSLIM_COUNTRIES
    if isinstance(mapping, list):
        return country in mapping
    return False


# =========================================================================
# Event date generator
# =========================================================================

_COUNTRY_HOLIDAY_CACHE: Dict[str, Any] = {}


def _get_country_holidays(country: str, years: List[int]) -> pd.DataFrame:
    """Get country-level public holidays from the `holidays` library.

    Returns a DataFrame with columns: date, holiday_name, holiday_type
    """
    import holidays as pyholidays
    key = (country, tuple(years))
    if key in _COUNTRY_HOLIDAY_CACHE:
        return _COUNTRY_HOLIDAY_CACHE[key]

    try:
        cal = pyholidays.country_holidays(country, years=years)
    except Exception:
        logger.warning("No holidays data for country %s", country)
        _COUNTRY_HOLIDAY_CACHE[key] = pd.DataFrame(columns=["date", "holiday_name", "holiday_type"])
        return _COUNTRY_HOLIDAY_CACHE[key]

    rows: List[Dict[str, Any]] = []
    for d, name in sorted(cal.items()):
        if isinstance(d, date):
            rows.append({
                "date": d,
                "holiday_name": str(name).split(" (")[0],
                "holiday_type": "public_holiday",
            })
    df = pd.DataFrame(rows)
    _COUNTRY_HOLIDAY_CACHE[key] = df
    return df


def _generate_moveable_feasts(country: str, years: List[int]) -> pd.DataFrame:
    """Generate moveable feast dates for the given country and years.

    These are cultural/religious events not (or not fully) covered by the
    standard country-level holidays library.
    """
    rows: List[Dict[str, Any]] = []

    for yr in years:
        # Easter
        if _event_applies_to_country("easter_sunday", country):
            d = _easter_western(yr)
            rows.append({"date": d, "holiday_name": "Easter Sunday", "holiday_type": "religious"})
            rows.append({"date": d - timedelta(days=2), "holiday_name": "Good Friday", "holiday_type": "religious"})
            rows.append({"date": d + timedelta(days=1), "holiday_name": "Easter Monday", "holiday_type": "religious"})

        if _event_applies_to_country("orthodox_easter", country):
            d = _eastern_orthodox(yr)
            rows.append({"date": d, "holiday_name": "Orthodox Easter Sunday", "holiday_type": "religious"})

        # Chinese New Year
        if _event_applies_to_country("chinese_new_year", country):
            if yr in CHINESE_NEW_YEAR_DATES:
                d = CHINESE_NEW_YEAR_DATES[yr]
                rows.append({"date": d, "holiday_name": "Chinese New Year", "holiday_type": "cultural"})
                # 15-day festival
                for i in range(1, 15):
                    rows.append({"date": d + timedelta(days=i),
                                 "holiday_name": f"CNY Day {i+1}",
                                 "holiday_type": "cultural"})

        # Diwali
        if _event_applies_to_country("diwali", country):
            if yr in DIWALI_DATES:
                d = DIWALI_DATES[yr]
                rows.append({"date": d, "holiday_name": "Diwali", "holiday_type": "cultural"})
                rows.append({"date": d - timedelta(days=1), "holiday_name": "Naraka Chaturdashi (Choti Diwali)",
                             "holiday_type": "cultural"})
                # 5-day festival: Dhanteras (2 days before), Naraka, Diwali, Govardhan, Bhai Dooj
                rows.append({"date": d - timedelta(days=2), "holiday_name": "Dhanteras", "holiday_type": "cultural"})
                rows.append({"date": d + timedelta(days=1), "holiday_name": "Govardhan Puja", "holiday_type": "cultural"})
                rows.append({"date": d + timedelta(days=2), "holiday_name": "Bhai Dooj", "holiday_type": "cultural"})

        # Holi
        if _event_applies_to_country("holi", country):
            if yr in HOLI_DATES:
                d = HOLI_DATES[yr]
                rows.append({"date": d, "holiday_name": "Holi", "holiday_type": "cultural"})
                rows.append({"date": d - timedelta(days=1), "holiday_name": "Holika Dahan",
                             "holiday_type": "cultural"})

        # Ramadan / Eid
        if _event_applies_to_country("ramadan_start", country):
            if yr in RAMADAN_START_DATES:
                rs = RAMADAN_START_DATES[yr]
                rows.append({"date": rs, "holiday_name": "Ramadan Start", "holiday_type": "religious"})
                # Eid al-Fitr ~29-30 days after Ramadan start
                eid_fitr = rs + timedelta(days=29)
                rows.append({"date": eid_fitr, "holiday_name": "Eid al-Fitr", "holiday_type": "religious"})
                # Eid al-Adha ~70 days after Ramadan start
                eid_adha = rs + timedelta(days=70)
                rows.append({"date": eid_adha, "holiday_name": "Eid al-Adha", "holiday_type": "religious"})

        # US retail events
        if _event_applies_to_country("black_friday", country):
            rows.append({"date": _black_friday(yr), "holiday_name": "Black Friday", "holiday_type": "retail"})
            rows.append({"date": _cyber_monday(yr), "holiday_name": "Cyber Monday", "holiday_type": "retail"})
        if _event_applies_to_country("thanksgiving", country):
            rows.append({"date": _thanksgiving_us(yr), "holiday_name": "Thanksgiving", "holiday_type": "public_holiday"})
        if _event_applies_to_country("mothers_day", country):
            rows.append({"date": _mothers_day_us(yr), "holiday_name": "Mother's Day", "holiday_type": "cultural"})
        if _event_applies_to_country("fathers_day", country):
            rows.append({"date": _fathers_day_us(yr), "holiday_name": "Father's Day", "holiday_type": "cultural"})

    return pd.DataFrame(rows)


def _generate_sports_events(country: str, years: List[int]) -> pd.DataFrame:
    """Generate major sports tournament dates relevant to the country."""
    rows: List[Dict[str, Any]] = []

    for yr in years:
        for evt in SPORTS_EVENTS:
            ename = evt["name"]
            label = evt["label"]
            etype = evt["type"]

            if not _event_applies_to_country(ename, country):
                continue

            # Determine if the event occurs this year
            occurs = False
            if evt.get("years") == "__annual__":
                occurs = True
            elif isinstance(evt.get("years"), list) and yr in evt["years"]:
                occurs = True

            if not occurs:
                continue

            if "compute" in evt:
                d = evt["compute"](yr)
                rows.append({"date": d, "holiday_name": label, "holiday_type": etype})
            elif "start_month" in evt:
                d = date(yr, evt["start_month"], evt["start_day"])
                days = evt.get("duration_days", 1)
                for i in range(days):
                    rows.append({
                        "date": d + timedelta(days=i),
                        "holiday_name": label,
                        "holiday_type": etype,
                    })

    return pd.DataFrame(rows)


def generate_event_dates(
    country: str,
    start_date: date,
    end_date: date,
    include_sports: bool = True,
    include_cultural: bool = True,
) -> pd.DataFrame:
    """Generate all event dates for a country within a date range.

    Returns a DataFrame with columns: date, holiday_name, holiday_type, country.
    This is the combined output of country holidays + moveable feasts + sports.
    """
    years = list(range(start_date.year, end_date.year + 1))

    parts: List[pd.DataFrame] = []

    # 1. Country holidays
    try:
        ch = _get_country_holidays(country, years)
        if not ch.empty:
            parts.append(ch)
    except Exception as e:
        logger.warning("Country holidays failed for %s: %s", country, e)

    # 2. Moveable feasts
    if include_cultural:
        try:
            mf = _generate_moveable_feasts(country, years)
            if not mf.empty:
                parts.append(mf)
        except Exception as e:
            logger.warning("Moveable feasts failed for %s: %s", country, e)

    # 3. Sports events
    if include_sports:
        try:
            sp = _generate_sports_events(country, years)
            if not sp.empty:
                parts.append(sp)
        except Exception as e:
            logger.warning("Sports events failed for %s: %s", country, e)

    if not parts:
        return pd.DataFrame(columns=["date", "holiday_name", "holiday_type", "country"])

    combined = pd.concat(parts, ignore_index=True)
    combined["country"] = country

    # Deduplicate by date + name (a holiday might appear in both holidays lib and our generator)
    combined = combined.drop_duplicates(subset=["date", "holiday_name"])

    # Ensure date column is datetime type for safe comparison
    combined["date"] = pd.to_datetime(combined["date"])
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)
    combined = combined[
        (combined["date"] >= start_ts) &
        (combined["date"] <= end_ts)
    ].copy()

    return combined.sort_values("date").reset_index(drop=True)


# =========================================================================
# Historical impact analysis
# =========================================================================

SIGNIFICANCE_THRESHOLD = 0.03  # Minimum |impact| to consider an event significant
MIN_EVENT_OCCURRENCES = 1      # Minimum times an event must appear in history


def _compute_event_impact(
    sales_df: pd.DataFrame,
    event_name: str,
    event_date: date,
    date_col: str,
    value_col: str,
    region_col: Optional[str] = None,
    region_value: Optional[str] = None,
    baseline_window: int = 21,
    event_window_before: int = 0,
    event_window_after: int = 1,
) -> Optional[float]:
    """Compute the historical sales impact of a single event occurrence.

    Compares sales during the event window vs a rolling baseline.
    Returns the impact factor (1.0 = no impact, 1.3 = +30%).
    Returns None if there isn't enough data.
    """
    s = sales_df.copy()
    if region_col and region_value:
        s = s[s[region_col] == region_value]

    if date_col in s.columns:
        s = s.set_index(date_col)
    s.index = pd.to_datetime(s.index)
    s = s.sort_index()
    s_val = pd.to_numeric(s[value_col], errors="coerce")

    event_ts = pd.Timestamp(event_date)

    # Baseline: up to `baseline_window` days before the event
    baseline_start = event_ts - timedelta(days=baseline_window)
    baseline_end = event_ts - timedelta(days=event_window_before + 1)
    baseline = s_val.loc[baseline_start:baseline_end].dropna()

    # Event window
    event_start = event_ts - timedelta(days=event_window_before)
    event_end = event_ts + timedelta(days=event_window_after)
    event_period = s_val.loc[event_start:event_end].dropna()

    if len(baseline) < 3 or len(event_period) < 1:
        return None

    baseline_mean = float(baseline.mean())
    event_mean = float(event_period.mean())

    if baseline_mean == 0:
        return None

    impact = event_mean / baseline_mean
    return impact


def compute_event_impacts(
    events_df: pd.DataFrame,
    sales_df: pd.DataFrame,
    date_col: str = "date",
    value_col: str = "value",
    region_col: Optional[str] = None,
    baseline_window: int = 21,
    event_window_before: int = 0,
    event_window_after: int = 1,
    per_region: bool = False,
) -> pd.DataFrame:
    """Augment the events DataFrame with impact factors.

    For each event occurrence, computes the historical sales impact
    by comparing sales during the event window vs a rolling baseline.

    Strategy:
      * If `per_region=True` AND the sales data has a region column, emits
        one row per (date, region) with per-region impact. This enables
        models that support region-aware exog features.
      * Otherwise (default), computes a single weighted-average impact per
        event date. Per-region impacts are computed internally but aggregated
        using sales volume as weights — regions with heavier sales during the
        baseline period have more influence on the final impact factor.

    The returned DataFrame always matches the existing 'holidays' schema:
        date, holiday_name, holiday_type, holiday_impact
    (plus optional `region` column when per_region=True).

    Events with |impact-1| < SIGNIFICANCE_THRESHOLD get impact=1.0 (neutral),
    preserving model capacity for truly impactful events.
    """
    if events_df.empty:
        events_df = events_df.copy()
        events_df["holiday_impact"] = 1.0
        return events_df

    # Determine whether to segment by region
    do_per_region = (
        per_region
        and region_col is not None
        and region_col in sales_df.columns
        and "region" not in events_df.columns
    )

    # Collect per-region impacts (or overall if no region segmentation)
    region_impacts: Dict[Tuple, Dict[Optional[str], float]] = {}
    region_weights: Dict[Tuple, Dict[Optional[str], float]] = {}
    event_meta: Dict[Tuple, str] = {}

    regions_to_compute: List[Optional[str]] = [None]
    if do_per_region:
        region_vals = sales_df[region_col].dropna().unique().tolist()
        regions_to_compute = [None] + list(region_vals)

    grouped = events_df.groupby(["date", "holiday_name"], sort=False)

    for (evt_date, evt_name), group in grouped:
        evt_date_py = evt_date if isinstance(evt_date, date) else evt_date.date()
        evt_type = group["holiday_type"].iloc[0] if "holiday_type" in group.columns else "unknown"
        key = (evt_date, evt_name)
        event_meta[key] = evt_type

        region_impacts[key] = {}
        region_weights[key] = {}

        for region in regions_to_compute:
            impact = _compute_event_impact(
                sales_df, evt_name, evt_date_py,
                date_col, value_col,
                region_col=region_col, region_value=region,
                baseline_window=baseline_window,
                event_window_before=event_window_before,
                event_window_after=event_window_after,
            )
            if impact is not None:
                region_impacts[key][region] = round(max(0.1, min(impact, 5.0)), 4)
                # Weight = average sales in baseline period for this region
                weight = _compute_baseline_sales(
                    sales_df, evt_date_py, date_col, value_col,
                    region_col=region_col, region_value=region,
                    window=baseline_window,
                )
                region_weights[key][region] = weight if weight is not None else 1.0
            else:
                region_impacts[key][region] = 1.0
                region_weights[key][region] = 0.0

    # Build result rows
    result_rows: List[Dict[str, Any]] = []

    for key, impacts in region_impacts.items():
        evt_date, evt_name = key
        evt_type = event_meta.get(key, "unknown")

        if do_per_region:
            # Emit one row per region
            for region, impact_val in impacts.items():
                if region is None:
                    continue  # Skip overall average when per-region
                result_rows.append({
                    "date": evt_date,
                    "holiday_name": evt_name,
                    "holiday_type": evt_type,
                    "holiday_impact": impact_val,
                    "region": region,
                })
        else:
            # Aggregate: weighted average across regions
            weights = region_weights.get(key, {})
            total_weight = sum(w for r, w in weights.items() if r is not None and w > 0)
            if total_weight > 0:
                weighted_impact = sum(
                    impacts.get(r, 1.0) * weights.get(r, 0.0)
                    for r in weights
                    if r is not None
                ) / total_weight
            else:
                weighted_impact = impacts.get(None, 1.0)

            result_rows.append({
                "date": evt_date,
                "holiday_name": evt_name,
                "holiday_type": evt_type,
                "holiday_impact": round(max(0.1, min(weighted_impact, 5.0)), 4),
            })

    if not result_rows:
        for _, row in events_df.iterrows():
            result_rows.append({
                "date": row["date"],
                "holiday_name": row["holiday_name"],
                "holiday_type": row.get("holiday_type", "unknown"),
                "holiday_impact": 1.0,
            })

    result = pd.DataFrame(result_rows)
    result["date"] = pd.to_datetime(result["date"])
    return result.sort_values("date").reset_index(drop=True)


def _compute_baseline_sales(
    sales_df: pd.DataFrame,
    event_date: date,
    date_col: str,
    value_col: str,
    region_col: Optional[str] = None,
    region_value: Optional[str] = None,
    window: int = 21,
) -> Optional[float]:
    """Compute average baseline sales to use as a weight."""
    s = sales_df.copy()
    if region_col and region_value:
        s = s[s[region_col] == region_value]
    if date_col in s.columns:
        s = s.set_index(date_col)
    s.index = pd.to_datetime(s.index)
    s = s.sort_index()
    s_val = pd.to_numeric(s[value_col], errors="coerce")
    event_ts = pd.Timestamp(event_date)
    baseline = s_val.loc[event_ts - timedelta(days=window):event_ts - timedelta(days=1)].dropna()
    return float(baseline.mean()) if len(baseline) >= 3 else None


# =========================================================================
# AutoEventDetector — public interface
# =========================================================================

COUNTRY_NAME_MAP: Dict[str, str] = {
    "US": "United States", "GB": "United Kingdom", "IN": "India",
    "CA": "Canada", "AU": "Australia", "DE": "Germany", "FR": "France",
    "IT": "Italy", "ES": "Spain", "BR": "Brazil", "MX": "Mexico",
    "JP": "Japan", "CN": "China", "KR": "South Korea", "RU": "Russia",
    "ZA": "South Africa", "AE": "UAE", "SG": "Singapore", "MY": "Malaysia",
    "ID": "Indonesia", "PH": "Philippines", "TH": "Thailand", "VN": "Vietnam",
    "NL": "Netherlands", "SE": "Sweden", "NO": "Norway", "DK": "Denmark",
    "FI": "Finland", "CH": "Switzerland", "BE": "Belgium", "AT": "Austria",
    "PT": "Portugal", "PL": "Poland", "TR": "Turkey", "SA": "Saudi Arabia",
}

# Prominent events with known regional celebration patterns within a country.
# Maps event_name -> { country -> [region values] }
# These help the impact analysis know which regions to focus on.
# The key insight: if we don't know, we let the data tell us via impact analysis.
REGION_EVENT_HINTS: Dict[str, Dict[str, List[str]]] = {
    "Durga Puja": {"IN": ["west_bengal", "assam", "odisha", "jharkhand", "bihar", "tripura"]},
    "Ganesh Chaturthi": {"IN": ["maharashtra", "goa", "gujarat", "karnataka", "andhra_pradesh"]},
    "Pongal": {"IN": ["tamil_nadu", "pondicherry", "kerala"]},
    "Onam": {"IN": ["kerala"]},
    "Lohri": {"IN": ["punjab", "haryana", "delhi"]},
    "Makar Sankranti": {"IN": ["gujarat", "maharashtra", "karnataka", "andhra_pradesh",
                               "tamil_nadu", "odisha", "bihar", "uttar_pradesh", "west_bengal"]},
    "Raksha Bandhan": {"IN": ["all"]},
    "Janmashtami": {"IN": ["all"]},
    "Maha Shivaratri": {"IN": ["all"]},
    "Navratri": {"IN": ["all"]},
    "Dussehra": {"IN": ["all"]},
}


class AutoEventDetector:
    """Detect and analyse regional events for forecasting.

    Usage:
        detector = AutoEventDetector(
            country="IN",
            sales_df=sales_data,
            date_col="date",
            value_col="value",
            region_col="state",  # optional
        )
        events_df = detector.run(start_date, end_date)
        # events_df has columns: date, holiday_name, holiday_type, holiday_impact
        # This matches the existing 'holidays' external data schema
    """

    def __init__(
        self,
        country: str,
        sales_df: pd.DataFrame,
        date_col: str = "date",
        value_col: str = "value",
        region_col: Optional[str] = None,
        baseline_window: int = 21,
    ):
        self.country = country.upper()
        self.sales_df = sales_df
        self.date_col = date_col
        self.value_col = value_col
        self.region_col = region_col
        self.baseline_window = baseline_window

    def run(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        include_sports: bool = True,
        include_cultural: bool = True,
        per_region: bool = True,
    ) -> pd.DataFrame:
        """Run the full detection pipeline.

        Args:
            start_date: Start of date range for event detection.
            end_date: End of date range for event detection.
            include_sports: Whether to include major sports events.
            include_cultural: Whether to include cultural/religious feasts.
            per_region: If True and region columns exist, emit per-region
                impact rows. Otherwise aggregate to a single weighted impact.

        Returns a DataFrame matching the 'holidays' external data schema:
            date, holiday_name, holiday_type, holiday_impact
        (optionally with a `region` column if per_region=True and region data exists)
        """
        if start_date is None:
            start_date = pd.to_datetime(self.sales_df[self.date_col]).min().date()
        if end_date is None:
            end_date = pd.to_datetime(self.sales_df[self.date_col]).max().date()

        logger.info(
            "AutoEventDetector: country=%s, range=%s..%s, region_col=%s",
            self.country, start_date, end_date, self.region_col,
        )

        # 1. Generate all possible event dates
        raw_events = generate_event_dates(
            country=self.country,
            start_date=start_date,
            end_date=end_date,
            include_sports=include_sports,
            include_cultural=include_cultural,
        )

        if raw_events.empty:
            logger.info("No events detected for %s", self.country)
            return pd.DataFrame(columns=["date", "holiday_name", "holiday_type",
                                         "holiday_impact"])

        logger.info("Generated %d raw event dates for %s", len(raw_events), self.country)

        # 2. Compute historical impact for each event
        result = compute_event_impacts(
            raw_events,
            self.sales_df,
            date_col=self.date_col,
            value_col=self.value_col,
            region_col=self.region_col,
            baseline_window=self.baseline_window,
            per_region=per_region,
        )

        logger.info(
            "Event detection complete: %d events with impact factors for %s",
            len(result), self.country,
        )
        return result

    def get_event_summary(self, events_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Return a human-readable summary of detected events for the UI."""
        if events_df.empty:
            return []

        summary: List[Dict[str, Any]] = []
        for _, row in events_df.iterrows():
            impact = row.get("holiday_impact", 1.0)
            pct = round((impact - 1.0) * 100, 1)
            summary.append({
                "date": str(row["date"].date()) if hasattr(row["date"], "date") else str(row["date"]),
                "name": row.get("holiday_name", "Unknown"),
                "type": row.get("holiday_type", "unknown"),
                "impact_pct": pct,
                "region": row.get("region"),
            })
        return summary


# =========================================================================
# Convenience: registry of known country codes for UI dropdowns
# =========================================================================

COMMON_COUNTRIES: List[Dict[str, str]] = [
    {"code": "US", "name": "United States"},
    {"code": "GB", "name": "United Kingdom"},
    {"code": "IN", "name": "India"},
    {"code": "CA", "name": "Canada"},
    {"code": "AU", "name": "Australia"},
    {"code": "DE", "name": "Germany"},
    {"code": "FR", "name": "France"},
    {"code": "IT", "name": "Italy"},
    {"code": "ES", "name": "Spain"},
    {"code": "BR", "name": "Brazil"},
    {"code": "MX", "name": "Mexico"},
    {"code": "JP", "name": "Japan"},
    {"code": "CN", "name": "China"},
    {"code": "KR", "name": "South Korea"},
    {"code": "RU", "name": "Russia"},
    {"code": "ZA", "name": "South Africa"},
    {"code": "AE", "name": "UAE"},
    {"code": "SG", "name": "Singapore"},
    {"code": "MY", "name": "Malaysia"},
    {"code": "ID", "name": "Indonesia"},
    {"code": "PH", "name": "Philippines"},
    {"code": "TH", "name": "Thailand"},
    {"code": "VN", "name": "Vietnam"},
    {"code": "NL", "name": "Netherlands"},
    {"code": "SE", "name": "Sweden"},
    {"code": "NO", "name": "Norway"},
    {"code": "DK", "name": "Denmark"},
    {"code": "FI", "name": "Finland"},
    {"code": "CH", "name": "Switzerland"},
    {"code": "BE", "name": "Belgium"},
    {"code": "AT", "name": "Austria"},
    {"code": "PT", "name": "Portugal"},
    {"code": "PL", "name": "Poland"},
    {"code": "TR", "name": "Turkey"},
    {"code": "SA", "name": "Saudi Arabia"},
    {"code": "AR", "name": "Argentina"},
    {"code": "CL", "name": "Chile"},
    {"code": "CO", "name": "Colombia"},
    {"code": "PE", "name": "Peru"},
    {"code": "EG", "name": "Egypt"},
    {"code": "NG", "name": "Nigeria"},
    {"code": "KE", "name": "Kenya"},
    {"code": "NZ", "name": "New Zealand"},
    {"code": "HK", "name": "Hong Kong"},
    {"code": "TW", "name": "Taiwan"},
    {"code": "IL", "name": "Israel"},
]
