"""Exponential Smoothing (ETS) forecaster."""
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
    ts = ts.groupby(date_col, as_index=False)[value_col].mean()
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


class ETSForecaster(BaseForecaster):
    name = "ETS"

    def __init__(
        self,
        trend: str = "add",
        seasonal: str = "add",
        seasonal_periods: int = 7,
    ) -> None:
        super().__init__(trend=trend, seasonal=seasonal, seasonal_periods=seasonal_periods)
        self.trend = trend
        self.seasonal = seasonal
        self.seasonal_periods = max(2, int(seasonal_periods))

    def fit(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        **kwargs: Any,
    ) -> "ETSForecaster":
        from statsmodels.tsa.holtwinters import ExponentialSmoothing

        self._date_col = date_col
        self._value_col = value_col
        ts = _prepare_ts(df, date_col, value_col)
        if len(ts) < 5:
            raise ValueError("ETS requires at least 5 data points")
        self._train_df = ts.reset_index()
        self._last_date = ts.index[-1]
        self._frequency = _infer_freq(ts)

        # Try multiple combinations — many short series fail with
        # multiplicative seasonal components.
        seasonal_periods = min(self.seasonal_periods, max(2, len(ts) // 2))
        candidates: List[Dict[str, Any]] = [
            {"trend": self.trend, "seasonal": self.seasonal,
             "seasonal_periods": seasonal_periods, "damped_trend": True},
            {"trend": self.trend, "seasonal": None, "damped_trend": True},
            {"trend": "add", "seasonal": None, "damped_trend": True},
            {"trend": None, "seasonal": None},
        ]
        last_err: Optional[Exception] = None
        for kw in candidates:
            try:
                if "seasonal_periods" in kw and kw.get("seasonal") is not None:
                    pass
                model = ExponentialSmoothing(ts, **kw, use_boxcox=False)
                self._fitted_model = model.fit(optimized=True)
                return self
            except Exception as e:
                last_err = e
                continue
        # Last-ditch fallback: simple mean
        self._fitted_model = None
        self._fallback_mean = float(ts.mean())
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
        future_idx = self._future_index(horizon)
        if self._fitted_model is not None:
            try:
                mean = self._fitted_model.forecast(horizon)
                mean_arr = np.asarray(mean, dtype=float)
            except Exception as e:
                logger.warning("ETS forecast failed: %s", e)
                mean_arr = np.array([self._fallback_mean] * horizon)
        else:
            mean_arr = np.array([self._fallback_mean] * horizon)
        # Use residual std for CI
        std = 0.0
        try:
            resid = np.asarray(self._fitted_model.resid) if self._fitted_model is not None else np.array([0.0])
            std = float(np.nanstd(resid)) if len(resid) else 0.0
        except Exception:
            std = 0.0
        results: List[Dict[str, Any]] = []
        for i, val in enumerate(mean_arr):
            if std > 0:
                lo = val - 1.96 * std
                hi = val + 1.96 * std
            else:
                lo = val * 0.85
                hi = val * 1.15
            results.append({
                "date": self._format_date(future_idx[i]),
                "forecast": self._safe_float(val),
                "lower_ci": self._safe_float(lo),
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

    def get_metrics(self) -> Dict[str, float]:
        if self._fitted_model is None:
            return {}
        out: Dict[str, float] = {}
        for attr in ("aic", "bic"):
            v = getattr(self._fitted_model, attr, None)
            if v is not None:
                try:
                    out[attr] = self._safe_float(v)
                except Exception:
                    pass
        return out
