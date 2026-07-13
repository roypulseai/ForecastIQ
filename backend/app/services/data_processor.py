"""Unified data processor for all supported file types.

Responsibilities:
    * Load CSV / Excel from disk
    * Detect + parse date columns robustly
    * Map arbitrary user column names to a standardized schema
    * Validate required columns per file type
    * Coerce numeric columns, fill missing values
    * Return a clean, standardized DataFrame per file type

Standard output schemas:
    * sales        : date, value, [entity columns...]
    * media_plan   : date, media_channel, media_spend, [reach, impressions, ...]
    * promotions   : date, discount, [promo_id, promo_type, ...]
    * holidays     : date, holiday_impact, [holiday_name, holiday_type]
    * events       : date, event_impact, [event_name, event_type]
    * weather      : date, temperature, [humidity, rainfall, snowfall]
    * competitor   : date, competitor_price, [competitor_name, market_share, ...]
    * economic     : date, [gdp, inflation, unemployment, cpi, ...]
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# File-type definitions
# --------------------------------------------------------------------------- #

DATE_ALIASES = [
    "date", "ds", "timestamp", "datetime", "order_date", "sales_date",
    "transaction_date", "day", "time", "report_date", "calendar_date",
]


@dataclass
class FileTypeSpec:
    """Describes how to normalize one file type."""
    name: str
    required_columns: List[str]
    optional_columns: List[str] = field(default_factory=list)
    date_column_aliases: List[str] = field(default_factory=lambda: list(DATE_ALIASES))
    # date column output (after standardization)
    standard_date: str = "date"
    # extra outputs to keep (after renaming)
    passthrough: List[str] = field(default_factory=list)


FILE_TYPE_SPECS: Dict[str, FileTypeSpec] = {
    "sales": FileTypeSpec(
        name="sales",
        required_columns=[],  # validation handled separately — date/value optional from spec
        optional_columns=["value", "y", "sales", "demand", "revenue",
                          "quantity", "qty", "units", "amount",
                          "sku", "product", "category", "sub_category",
                          "store", "region", "portfolio", "brand"],
    ),
    "media_plan": FileTypeSpec(
        name="media_plan",
        required_columns=["spend"],
        optional_columns=["channel", "reach", "impressions", "media_channel", "media_spend"],
        passthrough=["reach", "impressions"],
    ),
    "promotions": FileTypeSpec(
        name="promotions",
        required_columns=[],  # discount optional too — bare minimum is a date column
        optional_columns=["discount", "discount_pct", "discount_percent", "off", "promo_id",
                          "promo_type", "original_price", "promo_price"],
    ),
    "holidays": FileTypeSpec(
        name="holidays",
        required_columns=[],
        optional_columns=["name", "holiday_name", "type", "holiday_type",
                          "impact", "impact_factor", "holiday_impact"],
    ),
    "events": FileTypeSpec(
        name="events",
        required_columns=[],
        optional_columns=["name", "event_name", "type", "event_type",
                          "impact", "impact_factor", "event_impact"],
    ),
    "weather": FileTypeSpec(
        name="weather",
        required_columns=[],
        optional_columns=["temperature", "temp", "humidity", "rain", "rainfall",
                          "precipitation", "snow", "snowfall"],
    ),
    "competitor": FileTypeSpec(
        name="competitor",
        required_columns=[],
        optional_columns=["competitor_price", "price", "competitor_name", "name",
                          "market_share", "share", "promotion_flag"],
    ),
    "economic": FileTypeSpec(
        name="economic",
        required_columns=[],
        optional_columns=["gdp", "growth_rate", "consumer_confidence", "inflation",
                          "cpi", "unemployment", "interest_rate", "indicator_value"],
    ),
}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _normalize_col(col: str) -> str:
    return str(col).strip().lower().replace(" ", "_").replace("-", "_")


def _find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Find a column in df whose normalized name matches any candidate."""
    norm_map = {_normalize_col(c): c for c in df.columns}
    for cand in candidates:
        if _normalize_col(cand) in norm_map:
            return norm_map[_normalize_col(cand)]
    return None


def _find_date_column(df: pd.DataFrame, aliases: List[str]) -> Optional[str]:
    """Locate a date column by alias list, then by dtype sniffing."""
    # Explicit aliases
    found = _find_column(df, aliases)
    if found:
        return found
    # Fuzzy: any column whose normalized name contains "date"
    for c in df.columns:
        if "date" in _normalize_col(c):
            return c
    # Datetime dtype
    for c in df.columns:
        try:
            if pd.api.types.is_datetime64_any_dtype(df[c]):
                return c
        except Exception as e:
            logger.warning("Failed to check datetime dtype for column '%s': %s", c, e)
            continue
    return None


def _parse_date_column(df: pd.DataFrame, col: str) -> pd.Series:
    """Parse a date column robustly. Returns datetime64 Series."""
    s = df[col]
    if pd.api.types.is_datetime64_any_dtype(s):
        return s
    # Try ISO / common formats; fall back to inferred format
    result = pd.to_datetime(s, errors="coerce", format="mixed", utc=False)
    if result.isna().all():
        result = pd.to_datetime(s, errors="coerce", infer_datetime_format=True)
    return result


def _coerce_numeric(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


# --------------------------------------------------------------------------- #
# Column type inference
# --------------------------------------------------------------------------- #

REGION_ALIASES = {
    "region", "state", "city", "country", "store", "location", "area",
    "zone", "branch", "warehouse", "site", "territory", "district",
    "province", "county", "office", "department", "division",
}

ID_ALIASES = {
    "id", "sku", "upc", "code", "key", "product", "item", "article",
    "part", "catalog", "identifier", "account", "order", "invoice",
}


def _infer_column_types(df: pd.DataFrame) -> Dict[str, str]:
    """Classify each column as date/numeric/region/categorical/id/text/boolean."""
    types: Dict[str, str] = {}
    date_col = _find_date_column(df, DATE_ALIASES)
    for c in df.columns:
        if date_col and c == date_col:
            types[c] = "date"
        elif pd.api.types.is_bool_dtype(df[c]):
            types[c] = "boolean"
        elif pd.api.types.is_numeric_dtype(df[c]):
            types[c] = "numeric"
        elif pd.api.types.is_datetime64_any_dtype(df[c]):
            types[c] = "date"
        else:
            # string / object columns
            try:
                nunique = df[c].nunique()
                total = len(df)
                normalized = _normalize_col(c)
            except Exception as e:
                logger.warning("Failed to infer type for column '%s': %s", c, e)
                types[c] = "text"
                continue

            # Check ID/region aliases first
            if any(a in normalized for a in ID_ALIASES):
                types[c] = "id"
            elif any(a in normalized for a in REGION_ALIASES):
                types[c] = "region"
            elif nunique < max(2, total * 0.2):
                types[c] = "categorical"
            else:
                types[c] = "text"
    return types


# --------------------------------------------------------------------------- #
# Main processor
# --------------------------------------------------------------------------- #

class DataProcessor:
    """Unified loader + normalizer for all supported file types."""

    SUPPORTED_TYPES = list(FILE_TYPE_SPECS.keys())

    # ------------------------------------------------------------ loading
    @staticmethod
    def load_file(file_path: str) -> pd.DataFrame:
        """Load a CSV/Excel file. Uses chunked reading for large files."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".csv":
            return DataProcessor._read_csv_smart(file_path)
        if ext in (".xlsx", ".xls"):
            return pd.read_excel(file_path)
        if ext == ".parquet":
            return pd.read_parquet(file_path)
        raise ValueError(f"Unsupported file format: {ext}")

    @staticmethod
    def load_bytes(content: bytes, filename: str) -> pd.DataFrame:
        """Load CSV/Excel from raw bytes."""
        import io
        ext = os.path.splitext(filename)[1].lower()
        if ext == ".csv":
            # Peek at size to decide chunked read
            bio = io.BytesIO(content)
            size_mb = len(content) / (1024 * 1024)
            if size_mb > 50:
                # Read header first, then chunked
                header_df = pd.read_csv(bio, nrows=0)
                bio.seek(0)
                chunks = pd.read_csv(bio, chunksize=50_000)
                return DataProcessor._combine_chunks(chunks, header_df.columns.tolist())
            return pd.read_csv(bio)
        if ext in (".xlsx", ".xls"):
            return pd.read_excel(io.BytesIO(content))
        if ext == ".parquet":
            return pd.read_parquet(io.BytesIO(content))
        raise ValueError(f"Unsupported file format: {ext}")

    @staticmethod
    def _read_csv_smart(file_path: str) -> pd.DataFrame:
        """Read CSV using chunked reading for large files (>50MB or >500k rows)."""
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb < 50:
            try:
                # Use pyarrow engine if available for speed
                return pd.read_csv(file_path, engine="pyarrow")
            except Exception as e:
                logger.warning("pyarrow CSV engine failed, falling back to default: %s", e)
                return pd.read_csv(file_path)
        # Chunked read for large files
        chunks = pd.read_csv(file_path, chunksize=50_000)
        first_chunk = next(chunks)
        columns = first_chunk.columns.tolist()
        all_chunks = [first_chunk] + list(chunks)
        return DataProcessor._combine_chunks(all_chunks, columns)

    @staticmethod
    def _combine_chunks(chunks, columns: List[str]) -> pd.DataFrame:
        """Combine DataFrame chunks efficiently using categorical dtypes."""
        if not chunks:
            return pd.DataFrame(columns=columns)
        result = pd.concat(chunks, ignore_index=True)
        # Downcast numerics to save memory (no precision loss for typical data)
        for col in result.select_dtypes(include=["float64"]).columns:
            result[col] = pd.to_numeric(result[col], downcast="float")
        for col in result.select_dtypes(include=["int64"]).columns:
            result[col] = pd.to_numeric(result[col], downcast="integer")
        # Note: categorical conversion is done in optimize_dtypes() at end of process()
        return result

    # --------------------------------------------------------- normalization
    def process(self, df: pd.DataFrame, file_type: str) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """Normalize df for the given file_type. Returns (clean_df, column_mapping)."""
        if file_type not in FILE_TYPE_SPECS:
            raise ValueError(f"Unknown file_type: {file_type}. "
                             f"Supported: {self.SUPPORTED_TYPES}")
        spec = FILE_TYPE_SPECS[file_type]
        # Avoid full copy — only copy if we need to mutate (which we do for column adds)
        # But use shallow copy + copy-on-write pattern via assign
        df = df.copy()
        df.columns = [str(c) for c in df.columns]

        # Drop completely empty rows / cols
        df = df.dropna(how="all").dropna(axis=1, how="all")
        if df.empty:
            raise ValueError("File contains no data rows")

        # --- locate + parse date column
        date_col = _find_date_column(df, spec.date_column_aliases)
        if date_col is None:
            raise ValueError(
                f"{file_type} data must contain a date column. "
                f"Expected one of: {spec.date_column_aliases}"
            )
        df[spec.standard_date] = _parse_date_column(df, date_col)
        bad_dates = df[spec.standard_date].isna().sum()
        if bad_dates == len(df):
            raise ValueError(
                f"Could not parse any values in date column '{date_col}'. "
                f"Expected ISO or common date formats."
            )

        # Drop rows where date failed to parse
        if bad_dates > 0:
            logger.warning("Dropped %d rows with unparseable dates in %s data", bad_dates, file_type)
        df = df.dropna(subset=[spec.standard_date])

        # --- drop the original date column (we standardized to 'date')
        if date_col != spec.standard_date:
            df = df.drop(columns=[date_col])

        # --- type-specific normalization
        mapping: Dict[str, str] = {date_col: spec.standard_date}
        if file_type == "sales":
            df, m = self._normalize_sales(df)
        elif file_type == "media_plan":
            df, m = self._normalize_media_plan(df)
        elif file_type == "promotions":
            df, m = self._normalize_promotions(df)
        elif file_type == "holidays":
            df, m = self._normalize_holidays(df)
        elif file_type == "events":
            df, m = self._normalize_events(df)
        elif file_type == "weather":
            df, m = self._normalize_weather(df)
        elif file_type == "competitor":
            df, m = self._normalize_competitor(df)
        elif file_type == "economic":
            df, m = self._normalize_economic(df)
        else:
            m = {}

        mapping.update(m)

        # --- drop columns that were renamed (keep only standardized + passthrough)
        renamed_sources = set(mapping.keys()) - {spec.standard_date}
        df = df.drop(columns=[c for c in renamed_sources if c in df.columns],
                      errors="ignore")

        # --- final ordering: date first, then standardized cols, then any extras
        keep = [spec.standard_date]
        other = [c for c in df.columns if c not in keep]
        df = df[keep + other]

        # Deduplicate rows by date + all non-numeric columns to preserve
        # categorical/region breakdowns (e.g. same date + different region
        # yields 2 rows instead of collapsing into 1).
        non_num_cols = [
            c for c in df.columns
            if c != spec.standard_date and not pd.api.types.is_numeric_dtype(df[c])
        ]
        group_cols = [spec.standard_date] + non_num_cols
        num_cols = [c for c in df.columns if c not in group_cols]
        agg = {c: "sum" for c in num_cols} if num_cols else {}
        df = df.groupby(group_cols, as_index=False, sort=True).agg(agg) if agg else df.drop_duplicates(subset=group_cols)
        df = df.sort_values(spec.standard_date).reset_index(drop=True)

        # Memory optimization: downcast numerics, convert low-cardinality objects
        df = self.optimize_dtypes(df)

        return df, mapping

    # ----------------------------------------------------- type-specific ops
    @staticmethod
    def _normalize_sales(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
        mapping: Dict[str, str] = {}
        # Find value column
        value_col = _find_column(df, ["value", "y", "sales", "demand", "revenue",
                                       "quantity", "qty", "units", "amount"])
        if value_col is None:
            # Fallback: any numeric column other than date
            for c in df.columns:
                if c == "date":
                    continue
                if pd.api.types.is_numeric_dtype(df[c]):
                    value_col = c
                    break
        if value_col is None:
            raise ValueError("Sales data must have a numeric value column "
                             "(value / sales / revenue / quantity / etc.)")
        df[value_col] = _coerce_numeric(df[value_col])
        nan_count = df[value_col].isna().sum()
        if nan_count > 0:
            logger.warning("Forward/backward filling %d missing sales values", nan_count)
        df[value_col] = df[value_col].ffill().bfill().fillna(0.0)
        return df, mapping

    @staticmethod
    def _normalize_media_plan(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
        mapping: Dict[str, str] = {}

        # spend
        spend_col = _find_column(df, ["spend", "media_spend", "cost", "amount", "investment"])
        if spend_col is None:
            raise ValueError("Media plan requires a 'spend' column")
        if spend_col != "media_spend":
            df["media_spend"] = _coerce_numeric(df[spend_col]).fillna(0.0)
            mapping[spend_col] = "media_spend"
        else:
            df["media_spend"] = _coerce_numeric(df["media_spend"]).fillna(0.0)

        # channel
        channel_col = _find_column(df, ["channel", "media_channel", "platform"])
        if channel_col and channel_col != "media_channel":
            df["media_channel"] = df[channel_col].astype(str).fillna("unknown")
            mapping[channel_col] = "media_channel"
        elif "media_channel" not in df.columns:
            df["media_channel"] = "default"
        else:
            df["media_channel"] = df["media_channel"].astype(str).fillna("default")

        # optional reach / impressions
        for src_candidates, std_name in [
            (["reach"], "reach"),
            (["impressions", "imps"], "impressions"),
        ]:
            col = _find_column(df, src_candidates)
            if col and col != std_name:
                df[std_name] = _coerce_numeric(df[col]).fillna(0.0)
                mapping[col] = std_name
            elif std_name in df.columns:
                df[std_name] = _coerce_numeric(df[std_name]).fillna(0.0)

        return df, mapping

    @staticmethod
    def _normalize_promotions(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
        mapping: Dict[str, str] = {}
        discount_col = _find_column(df, ["discount", "discount_pct", "discount_percent",
                                          "discount_amount", "off", "pct_off"])
        if discount_col and discount_col != "discount":
            df["discount"] = _coerce_numeric(df[discount_col]).fillna(0.0)
            mapping[discount_col] = "discount"
        elif "discount" in df.columns:
            df["discount"] = _coerce_numeric(df["discount"]).fillna(0.0)
        else:
            df["discount"] = 0.0

        # If discount appears to be a percentage (0-100), keep as-is.  If a
        # fraction (0-1), it is still meaningful.  We do not transform it.
        promo_id_col = _find_column(df, ["promo_id", "id", "campaign_id"])
        if promo_id_col and promo_id_col != "promo_id":
            df["promo_id"] = df[promo_id_col].astype(str)
            mapping[promo_id_col] = "promo_id"

        promo_type_col = _find_column(df, ["promo_type", "type", "campaign_type"])
        if promo_type_col and promo_type_col != "promo_type":
            df["promo_type"] = df[promo_type_col].astype(str)
            mapping[promo_type_col] = "promo_type"

        return df, mapping

    @staticmethod
    def _normalize_holidays(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
        return DataProcessor._normalize_impact_table(
            df,
            holiday_or_event="holiday",
        )

    @staticmethod
    def _normalize_events(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
        return DataProcessor._normalize_impact_table(
            df,
            holiday_or_event="event",
        )

    @staticmethod
    def _normalize_impact_table(
        df: pd.DataFrame, holiday_or_event: str
    ) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """Holidays and events share an identical structure."""
        prefix = holiday_or_event
        mapping: Dict[str, str] = {}

        # impact: column is renamed to <prefix>_impact
        impact_col = _find_column(
            df,
            [f"{prefix}_impact", "impact", "impact_factor", "lift", "multiplier", "weight"],
        )
        if impact_col and impact_col != f"{prefix}_impact":
            df[f"{prefix}_impact"] = _coerce_numeric(df[impact_col]).fillna(1.0)
            mapping[impact_col] = f"{prefix}_impact"
        elif f"{prefix}_impact" in df.columns:
            df[f"{prefix}_impact"] = _coerce_numeric(df[f"{prefix}_impact"]).fillna(1.0)
        else:
            df[f"{prefix}_impact"] = 1.0

        # name
        name_col = _find_column(df, [f"{prefix}_name", "name", "label"])
        if name_col and name_col != f"{prefix}_name":
            df[f"{prefix}_name"] = df[name_col].astype(str).fillna("Unknown")
            mapping[name_col] = f"{prefix}_name"

        # type
        type_col = _find_column(df, [f"{prefix}_type", "type", "category", "kind"])
        if type_col and type_col != f"{prefix}_type":
            df[f"{prefix}_type"] = df[type_col].astype(str)
            mapping[type_col] = f"{prefix}_type"

        return df, mapping

    @staticmethod
    def _normalize_weather(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
        mapping: Dict[str, str] = {}
        # temperature
        temp_col = _find_column(df, ["temperature", "temp", "temp_c", "temp_f", "avg_temp"])
        if temp_col and temp_col != "temperature":
            df["temperature"] = _coerce_numeric(df[temp_col])
            mapping[temp_col] = "temperature"
        elif "temperature" in df.columns:
            df["temperature"] = _coerce_numeric(df["temperature"])
        else:
            df["temperature"] = np.nan
        df["temperature"] = df["temperature"].fillna(df["temperature"].mean()
                                                     if df["temperature"].notna().any()
                                                     else 20.0)

        for src_candidates, std_name in [
            (["humidity"], "humidity"),
            (["rainfall", "rain", "precipitation", "precip"], "rainfall"),
            (["snowfall", "snow"], "snowfall"),
        ]:
            col = _find_column(df, src_candidates)
            if col and col != std_name:
                df[std_name] = _coerce_numeric(df[col]).fillna(0.0)
                mapping[col] = std_name
            elif std_name in df.columns:
                df[std_name] = _coerce_numeric(df[std_name]).fillna(0.0)
            else:
                df[std_name] = 0.0

        return df, mapping

    @staticmethod
    def _normalize_competitor(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
        mapping: Dict[str, str] = {}
        price_col = _find_column(df, ["competitor_price", "price", "comp_price", "rival_price"])
        if price_col and price_col != "competitor_price":
            df["competitor_price"] = _coerce_numeric(df[price_col])
            mapping[price_col] = "competitor_price"
        elif "competitor_price" in df.columns:
            df["competitor_price"] = _coerce_numeric(df["competitor_price"])
        else:
            df["competitor_price"] = np.nan

        # If no price col, fall back to any numeric column
        if df["competitor_price"].isna().all():
            for c in df.columns:
                if c == "date":
                    continue
                if pd.api.types.is_numeric_dtype(df[c]):
                    df["competitor_price"] = _coerce_numeric(df[c])
                    mapping[c] = "competitor_price"
                    break
        df["competitor_price"] = df["competitor_price"].fillna(0.0)

        name_col = _find_column(df, ["competitor_name", "name", "competitor", "brand"])
        if name_col and name_col != "competitor_name":
            df["competitor_name"] = df[name_col].astype(str).fillna("Unknown")
            mapping[name_col] = "competitor_name"
        elif "competitor_name" in df.columns:
            df["competitor_name"] = df["competitor_name"].astype(str).fillna("Unknown")
        else:
            df["competitor_name"] = "Unknown"

        share_col = _find_column(df, ["market_share", "share"])
        if share_col and share_col != "market_share":
            df["market_share"] = _coerce_numeric(df[share_col]).fillna(0.0)
            mapping[share_col] = "market_share"
        elif "market_share" in df.columns:
            df["market_share"] = _coerce_numeric(df["market_share"]).fillna(0.0)
        else:
            df["market_share"] = 0.0

        promo_col = _find_column(df, ["promotion_flag", "is_promo", "on_promo"])
        if promo_col:
            df["promotion_flag"] = (
                _coerce_numeric(df[promo_col]).fillna(0).astype(int)
            )
        else:
            df["promotion_flag"] = 0

        return df, mapping

    @staticmethod
    def _normalize_economic(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """Economic: keep any numeric column found, with sensible fills."""
        mapping: Dict[str, str] = {}
        for c in list(df.columns):
            if c == "date":
                continue
            df[c] = _coerce_numeric(df[c])
            # Forward/backward fill then zero
            if df[c].isna().any():
                df[c] = df[c].ffill().bfill().fillna(0.0)
        return df, mapping

    # ---------------------------------------------------------- validation
    def validate_sales(self, df: pd.DataFrame) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []

        if df.empty:
            errors.append("DataFrame is empty")
            return {"valid": False, "errors": errors, "warnings": warnings,
                    "date_column": None, "value_column": None, "row_count": 0, "unique_dates": 0}

        date_col = "date" if "date" in df.columns else _find_date_column(df, DATE_ALIASES)
        value_col = "value" if "value" in df.columns else _find_column(
            df, ["value", "y", "sales", "demand", "revenue", "quantity", "qty", "units", "amount"]
        )
        if value_col is None:
            for c in df.columns:
                if c == date_col:
                    continue
                if pd.api.types.is_numeric_dtype(df[c]):
                    value_col = c
                    break

        if date_col is None:
            errors.append("Could not identify a date column")
        if value_col is None:
            errors.append("Could not identify a numeric value column")
        if value_col and value_col in df.columns and df[value_col].isna().sum() > 0:
            warnings.append(f"{df[value_col].isna().sum()} missing values filled with 0")
        if date_col and len(df) < 14:
            warnings.append("Series is short (<14 points) — forecasts may be unreliable")

        # Detect frequency — map median date gap to human-readable label
        frequency = None
        if date_col and not df.empty:
            try:
                ts = pd.to_datetime(df[date_col]).sort_values().drop_duplicates()
                if len(ts) >= 3:
                    diffs = ts.diff().dropna()
                    if not diffs.empty:
                        median = diffs.median()
                        if median <= pd.Timedelta(days=3):
                            frequency = "D"
                        elif median <= pd.Timedelta(days=10):
                            frequency = "W"
                        elif median <= pd.Timedelta(days=20):
                            frequency = "F"
                        elif median <= pd.Timedelta(days=60):
                            frequency = "M"
                        elif median <= pd.Timedelta(days=180):
                            frequency = "Q"
                        else:
                            frequency = "Y"
            except Exception as e:
                logger.warning("Frequency detection failed: %s", e)
                frequency = None

        extra_cols = [c for c in df.columns if c not in (date_col, value_col)]
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "date_column": date_col,
            "value_column": value_col,
            "row_count": int(len(df)),
            "unique_dates": int(df[date_col].nunique()) if date_col in df.columns else 0,
            "frequency": frequency,
            "extra_columns": extra_cols,
            "column_types": _infer_column_types(df),
        }

    @staticmethod
    def validate_upload_content(df: pd.DataFrame) -> dict:
        errors = []
        warnings = []
        
        if df.empty:
            errors.append("File contains no data rows")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        if len(df.columns) == 0:
            errors.append("File contains no columns")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        for col in df.columns:
            null_pct = df[col].isnull().mean()
            if null_pct > 0.5:
                warnings.append(f"Column '{col}' has {null_pct:.0%} missing values")
        
        dup_cols = [c for c in df.columns if list(df.columns).count(c) > 1]
        if dup_cols:
            errors.append(f"Duplicate column names: {list(set(dup_cols))}")
        
        if len(df) > 10_000_000:
            warnings.append(f"Very large dataset ({len(df):,} rows) — may be slow")
        
        all_null = [col for col in df.columns if df[col].isnull().all()]
        if all_null:
            errors.append(f"Columns with all null values: {all_null}")
        
        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    # ----------------------------------------------------- time features
    def add_calendar_features(
        self, df: pd.DataFrame, date_col: str = "date"
    ) -> pd.DataFrame:
        df = df.copy()
        if date_col not in df.columns:
            return df
        d = pd.to_datetime(df[date_col], errors="coerce")
        df["dayofweek"] = d.dt.dayofweek.astype("Int64")
        df["dayofmonth"] = d.dt.day.astype("Int64")
        df["dayofyear"] = d.dt.dayofyear.astype("Int64")
        df["weekofyear"] = d.dt.isocalendar().week.astype("Int64")
        df["month"] = d.dt.month.astype("Int64")
        df["quarter"] = d.dt.quarter.astype("Int64")
        df["year"] = d.dt.year.astype("Int64")
        df["is_weekend"] = d.dt.dayofweek.isin([5, 6]).astype("Int64")
        df["is_month_start"] = d.dt.is_month_start.astype("Int64")
        df["is_month_end"] = d.dt.is_month_end.astype("Int64")
        return df

    # ----------------------------------------------------- aggregation
    @staticmethod
    def resample(
        df: pd.DataFrame, date_col: str, value_col: str, freq: str = "D"
    ) -> pd.DataFrame:
        ts = df.set_index(date_col)[value_col].sort_index()
        ts.index = pd.to_datetime(ts.index)
        agg = ts.resample(freq).sum()
        out = pd.DataFrame({date_col: agg.index, value_col: agg.values})
        return out.dropna().reset_index(drop=True)

    # ----------------------------------------------------- downsampling
    @staticmethod
    def downsample_for_forecasting(
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        max_points: int = 5000,
        prefer_weekly: bool = False,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Reduce a long time series to <= max_points while preserving shape.

        Strategy:
            1. If len(df) <= max_points, return as-is.
            2. If we have 5+ years of daily data, aggregate to weekly (huge
               memory + speed win for ML models).
            3. Otherwise, take a representative subset: keep the most-recent
               `max_points` rows (recency is what matters for forecasting).

        Returns (downsampled_df, info_dict). info_dict explains what was done
        so the UI can show a notice to the user.
        """
        info: Dict[str, Any] = {
            "original_rows": int(len(df)),
            "downsample_applied": False,
            "reason": None,
            "new_rows": int(len(df)),
            "aggregation_level": None,
        }
        if df.empty or len(df) <= max_points:
            return df, info

        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=[date_col]).sort_values(date_col)

        n = len(df)
        # Compute date span
        span_days = (df[date_col].iloc[-1] - df[date_col].iloc[0]).days

        # If very long daily series (>= 5 years) AND we exceed the limit by 5x
        # aggregate to weekly — much faster for all downstream models.
        if n > max_points * 5 and span_days >= 365 * 5:
            weekly = (
                df.set_index(date_col)[[value_col]]
                .resample("W")
                .sum()
                .reset_index()
            )
            weekly.columns = [date_col, value_col]
            info.update({
                "downsample_applied": True,
                "reason": (
                    f"Series had {n:,} rows spanning {span_days:,} days. "
                    f"Aggregated to weekly ({len(weekly):,} rows) for performance."
                ),
                "new_rows": int(len(weekly)),
                "aggregation_level": "weekly",
            })
            return weekly, info

        # Otherwise, keep the most-recent max_points rows
        recent = df.tail(max_points).reset_index(drop=True)
        info.update({
            "downsample_applied": True,
            "reason": (
                f"Series had {n:,} rows; using the most recent {max_points:,} "
                f"to keep forecasting responsive."
            ),
            "new_rows": int(len(recent)),
            "aggregation_level": "tail",
        })
        return recent, info

    @staticmethod
    def optimize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
        """Downcast numeric and use categoricals to cut memory ~50%."""
        if df.empty:
            return df
        for col in df.select_dtypes(include=["float64"]).columns:
            df[col] = pd.to_numeric(df[col], downcast="float")
        for col in df.select_dtypes(include=["int64"]).columns:
            df[col] = pd.to_numeric(df[col], downcast="integer")
        for col in df.select_dtypes(include=["object"]).columns:
            nunique = df[col].nunique(dropna=True)
            if 0 < nunique < max(100, len(df) * 0.5):
                df[col] = df[col].astype("category")
        return df

    @staticmethod
    def memory_mb(df: pd.DataFrame) -> float:
        return float(df.memory_usage(deep=True).sum() / (1024 * 1024))
