"""STL decomposition forecaster.

Decomposes series into trend + seasonal + residual via STL, fits a
linear trend on the seasonally-adjusted values, then projects forward.
"""
from __future__ import annotations

import logging
import warnings
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .base import BaseForecaster

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)


def _prepare_ts(df: pd.DataFrame, date_col: str, value_col: str) -> pd.Series:
    ts = df[[date_col, value_col]].copy()
    ts[date_col] = pd.to_datetime(ts[date_col], errors="coerce")
    ts[value_col] = pd.to_numeric(ts[value_col], errors="coerce")
    ts = ts.dropna().sort_values(date_col)
    ts = ts.groupby(date_col, as_index=False)[value_col].sum()
    ts = ts.set_index(date_col)[value_col].astype(float)
    return ts


def _infer_freq(ts: pd.Series) -> str:
    if len(ts) < 3:
        return "D"
    diffs = ts.index.to_series().diff().dropna()
    if diffs.empty:
        return "D"
    m = diffs.median()
    if m <= pd.Timedelta(days=1):
        return "D"
    if m <= pd.Timedelta(days=7):
        return "W"
    if m <= pd.Timedelta(days=31):
        return "M"
    return "D"


class STLForecaster(BaseForecaster):
    name = "STL"

    def __init__(self, period: int = 7, robust: bool = True) -> None:
        super().__init__(period=period, robust=robust)
        self.period = max(2, int(period))
        self.robust = bool(robust)
        self._trend_slope: float = 0.0
        self._trend_intercept: float = 0.0
        self._seasonal_pattern: np.ndarray = np.array([])
        self._resid_std: float = 0.0
        self._seasonal_strength: float = 0.0

    def fit(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        **kwargs: Any,
    ) -> "STLForecaster":
        from statsmodels.tsa.seasonal import STL as STLDecomposition

        self._date_col = date_col
        self._value_col = value_col
        ts = _prepare_ts(df, date_col, value_col)
        if len(ts) < 2 * self.period + 1:
            # Fallback: use a period that is half the data length
            self.period = max(2, len(ts) // 4)
        if len(ts) < 4:
            raise ValueError("STL requires at least 4 data points")
        self._train_df = ts.reset_index()
        self._last_date = ts.index[-1]
        freq = kwargs.get("frequency")
        self._frequency = self._normalize_frequency(freq if freq else _infer_freq(ts))

        try:
            stl = STLDecomposition(ts, period=self.period, robust=self.robust)
            result = stl.fit()
            self._fitted_model = result
            # Fit a linear trend on the TREND component so the projection
            # is in absolute units. (seasonal + resid) is mean-zero, so
            # fitting a linear trend on it yields near-zero slope/intercept.
            trend_component = np.asarray(result.trend)
            x = np.arange(len(trend_component))
            if np.std(trend_component) == 0:
                self._trend_slope = 0.0
                self._trend_intercept = float(trend_component.mean())
            else:
                slope, intercept = np.polyfit(x, trend_component, 1)
                self._trend_slope = float(slope)
                self._trend_intercept = float(intercept)
            # Take the last full cycle of the seasonal pattern
            sp = np.asarray(result.seasonal)
            self._seasonal_pattern = sp[-self.period:] if len(sp) >= self.period else sp
            self._resid_std = float(np.nanstd(np.asarray(result.resid)))
            # Seasonal strength: max(0, 1 - var(resid) / var(resid + seasonal))
            try:
                var_r = float(np.nanvar(np.asarray(result.resid)))
                var_rs = float(np.nanvar(np.asarray(result.resid + result.seasonal)))
                self._seasonal_strength = max(0.0, 1.0 - var_r / var_rs) if var_rs > 0 else 0.0
            except Exception:
                self._seasonal_strength = 0.0
        except Exception as e:
            logger.warning("STL fit failed: %s — using linear trend fallback", e)
            self._fitted_model = None
            x = np.arange(len(ts))
            slope, intercept = np.polyfit(x, ts.values, 1)
            self._trend_slope = float(slope)
            self._trend_intercept = float(intercept)
            self._seasonal_pattern = np.zeros(self.period)
            self._resid_std = float(np.std(ts.values))
            self._seasonal_strength = 0.0
        return self

    def _future_index(self, horizon: int) -> pd.DatetimeIndex:
        freq = self._frequency or "D"
        try:
            return pd.date_range(
                start=self._last_date + pd.tseries.frequencies.to_offset(freq),
                periods=horizon, freq=freq,
            )
        except Exception:
            return pd.date_range(
                start=self._last_date + pd.Timedelta(days=1),
                periods=horizon, freq="D",
            )

    def _predict(
        self, horizon: int, exog_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> List[Dict[str, Any]]:
        if self._last_date is None:
            raise ValueError("Model not fitted")
        n_history = len(self._train_df) if self._train_df is not None else 0
        future_idx = self._future_index(horizon)
        results: List[Dict[str, Any]] = []
        sp = self._seasonal_pattern
        sp_len = len(sp)
        for i, d in enumerate(future_idx):
            x = n_history + i
            trend = self._trend_intercept + self._trend_slope * x
            # Add the seasonal pattern. The pattern is one cycle of length
            # `period`, indexed by the future step counter.
            if sp_len > 0:
                seasonal_idx = i % sp_len
                seasonal = float(sp[seasonal_idx])
            else:
                seasonal = 0.0
            forecast = trend + seasonal
            # CI based on residual std
            if self._resid_std > 0:
                lo = forecast - 1.96 * self._resid_std
                hi = forecast + 1.96 * self._resid_std
            else:
                lo = forecast * 0.85
                hi = forecast * 1.15
            results.append({
                "date": self._format_date(d),
                "forecast": self._safe_float(max(0.0, forecast)),
                "lower_ci": self._safe_float(max(0.0, lo)),
                "upper_ci": self._safe_float(hi),
            })
        return results

    def forecast(
        self,
        horizon: int,
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        return self._predict(horizon, exog_data)

    def get_baseline(
        self,
        horizon: int,
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        return self._predict(horizon, exog_data=None)

    def get_components(self) -> Dict[str, Any]:
        if self._fitted_model is None:
            return {}
        try:
            return {
                "trend_slope": self._safe_float(self._trend_slope),
                "seasonal_strength": self._safe_float(self._seasonal_strength),
                "residual_std": self._safe_float(self._resid_std),
            }
        except Exception:
            return {}
