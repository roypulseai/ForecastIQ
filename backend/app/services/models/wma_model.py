"""Weighted Moving Average forecaster.

Captures day-of-week seasonality and applies a configurable weighted
average over a trailing window. External factors (promotions) are
applied as a multiplier on the moving average.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .base import BaseForecaster

logger = logging.getLogger(__name__)


def _linear_weights(window: int) -> np.ndarray:
    """Linearly increasing weights, normalized to sum=1."""
    if window <= 0:
        return np.array([1.0])
    w = np.arange(1, window + 1, dtype=float)
    return w / w.sum()


class WMAForecaster(BaseForecaster):
    name = "WMA"

    def __init__(self, window: int = 8) -> None:
        super().__init__(window=window)
        self.window = max(2, int(window))
        self._historical_mean: Optional[float] = None
        self._seasonal_factors: Dict[int, float] = {}
        self._wma_value: Optional[float] = None
        self._last_values: Optional[pd.Series] = None
        self._exog_multiplier: Dict[pd.Timestamp, float] = {}

    def fit(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        **kwargs: Any,
    ) -> "WMAForecaster":
        self._date_col = date_col
        self._value_col = value_col
        ts = df[[date_col, value_col]].copy()
        ts[date_col] = pd.to_datetime(ts[date_col], errors="coerce")
        ts[value_col] = pd.to_numeric(ts[value_col], errors="coerce")
        ts = ts.dropna().sort_values(date_col)
        ts = ts.groupby(date_col, as_index=False)[value_col].sum()
        ts = ts.set_index(date_col)[value_col].astype(float)
        self._last_values = ts
        self._last_date = ts.index[-1] if len(ts) else None
        self._frequency = self._normalize_frequency(kwargs.get("frequency") or self._infer_frequency(df, date_col))

        self._historical_mean = float(ts.mean()) if len(ts) else 0.0

        # Day-of-week seasonal factors
        if len(ts) >= 14:
            grp = ts.groupby(ts.index.dayofweek).mean()
            overall = float(ts.mean()) or 1.0
            self._seasonal_factors = {
                int(d): float(v / overall) if overall else 1.0
                for d, v in grp.items()
            }
        else:
            self._seasonal_factors = {d: 1.0 for d in range(7)}

        # Trailing WMA
        w = min(self.window, len(ts))
        if w > 0:
            weights = _linear_weights(w)
            tail = ts.iloc[-w:].values
            self._wma_value = float(np.dot(weights, tail))
        else:
            self._wma_value = self._historical_mean

        # Exog → multiplier map keyed by Timestamp
        exog = kwargs.get("exog_data") or {}
        self._exog_multiplier = self._build_exog_multiplier(exog)
        return self

    def _build_exog_multiplier(
        self, exog_data: Optional[Dict[str, pd.DataFrame]]
    ) -> Dict[pd.Timestamp, float]:
        out: Dict[pd.Timestamp, float] = {}
        if not exog_data:
            return out

        def _normalize_date(val: Any) -> Optional[pd.Timestamp]:
            try:
                d = pd.Timestamp(pd.to_datetime(val, errors="coerce"))
                if pd.isna(d):
                    return None
                return d.normalize()
            except Exception:
                return None

        def _first_numeric(df: pd.DataFrame) -> Optional[str]:
            for col in df.columns:
                if col == "date":
                    continue
                if pd.api.types.is_numeric_dtype(df[col]):
                    return col
            return None

        def _get_multiplier(factor_type: str, row: pd.Series, df: pd.DataFrame) -> Optional[float]:
            preferred = {
                "promotions": "discount",
                "events": "event_impact",
                "holidays": "holiday_impact",
                "media_plan": "media_spend",
            }
            col = preferred.get(factor_type)
            if col and col in df.columns:
                val = pd.to_numeric(row.get(col), errors="coerce")
            else:
                num_col = _first_numeric(df)
                if num_col is None:
                    return None
                val = pd.to_numeric(row.get(num_col), errors="coerce")
            if pd.isna(val):
                return None
            if factor_type == "promotions":
                return 1.0 + max(0.0, min(float(val), 100.0)) / 100.0
            return float(val)

        for factor_type, df in exog_data.items():
            if df is None or df.empty or "date" not in df.columns:
                continue
            for _, row in df.iterrows():
                d = _normalize_date(row.get("date"))
                if d is None:
                    continue
                mult = _get_multiplier(factor_type, row, df)
                if mult is None:
                    continue
                out[d] = out.get(d, 1.0) * mult

        return out

    def _generate(
        self,
        horizon: int,
        exog_data: Optional[Dict[str, pd.DataFrame]],
        apply_exog: bool,
    ) -> List[Dict[str, Any]]:
        if self._wma_value is None or self._last_date is None:
            raise ValueError("Model not fitted")
        freq = self._frequency or "D"
        try:
            future_idx = pd.date_range(
                start=self._last_date + pd.tseries.frequencies.to_offset(freq),
                periods=horizon, freq=freq,
            )
        except Exception:
            future_idx = pd.date_range(
                start=self._last_date + pd.Timedelta(days=1), periods=horizon, freq="D",
            )
        results: List[Dict[str, Any]] = []
        base = self._wma_value
        # Exog lookup (timestamp → multiplier)
        exog_map = self._exog_multiplier if apply_exog else {}
        for d in future_idx:
            factor = self._seasonal_factors.get(d.dayofweek, 1.0)
            mult = exog_map.get(d.normalize(), 1.0)
            val = base * factor * mult
            results.append({
                "date": self._format_date(d),
                "forecast": self._safe_float(max(0.0, val)),
                "lower_ci": self._safe_float(max(0.0, val * 0.85)),
                "upper_ci": self._safe_float(val * 1.15),
            })
        return results

    def forecast(
        self,
        horizon: int,
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        return self._generate(horizon, exog_data, apply_exog=True)

    def get_baseline(
        self,
        horizon: int,
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        return self._generate(horizon, exog_data, apply_exog=False)

    def get_components(self) -> Dict[str, Any]:
        return {
            "seasonal_factors": {str(k): self._safe_float(v)
                                  for k, v in self._seasonal_factors.items()},
            "wma": self._safe_float(self._wma_value),
            "historical_mean": self._safe_float(self._historical_mean),
        }
