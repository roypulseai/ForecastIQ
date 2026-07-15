"""Theta method forecaster."""
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


class ThetaForecaster(BaseForecaster):
    name = "Theta"

    def __init__(self, period: int = 7, deseasonalize: bool = True) -> None:
        super().__init__(period=period, deseasonalize=deseasonalize)
        self.period = max(2, int(period))
        self.deseasonalize = deseasonalize

    def fit(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        **kwargs: Any,
    ) -> "ThetaForecaster":
        from statsmodels.tsa.forecasting.theta import ThetaModel

        self._date_col = date_col
        self._value_col = value_col
        ts = _prepare_ts(df, date_col, value_col)
        if len(ts) < 4:
            raise ValueError("Theta requires at least 4 data points")
        self._train_df = ts.reset_index()
        self._last_date = ts.index[-1]
        freq = kwargs.get("frequency")
        self._frequency = self._normalize_frequency(freq if freq else _infer_freq(ts))
        self._resid_std: float = 0.0

        period = min(self.period, max(2, len(ts) // 2))
        last_err: Optional[Exception] = None
        for use_test in (False, True):
            for des in (self.deseasonalize, True, False):
                try:
                    model = ThetaModel(ts, period=period,
                                       deseasonalize=des, use_test=use_test)
                    self._fitted_model = model.fit()
                    self.period = period
                    self.deseasonalize = des
                    try:
                        resid = np.asarray(self._fitted_model.resid, dtype=float)
                    except Exception:
                        resid = np.asarray(ts.diff().dropna().values, dtype=float)
                    self._resid_std = float(np.nanstd(resid)) if len(resid) > 0 else 0.0
                    return self
                except Exception as e:
                    last_err = e
                    continue
        raise RuntimeError(f"ThetaModel failed: {last_err}")

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
        if self._fitted_model is None or self._last_date is None:
            raise ValueError("Model not fitted")
        future_idx = self._future_index(horizon)
        try:
            pred = self._fitted_model.forecast(horizon)
            values = np.asarray(pred, dtype=float)
        except Exception as e:
            logger.warning("Theta forecast failed: %s", e)
            last = float(self._train_df[self._value_col].iloc[-1])
            values = np.array([last] * horizon)
        if self._resid_std > 0:
            margin = 1.96 * self._resid_std * np.sqrt(horizon)
        else:
            margin = 0.0
        return [
            {
                "date": self._format_date(d),
                "forecast": self._safe_float(v),
                "lower_ci": self._safe_float(v - margin if margin > 0 else v * 0.85),
                "upper_ci": self._safe_float(v + margin if margin > 0 else v * 1.15),
            }
            for d, v in zip(future_idx, values)
        ]

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
