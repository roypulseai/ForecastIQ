"""ARIMA and SARIMAX forecasters."""
from __future__ import annotations

import logging
import warnings
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .base import BaseForecaster

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)


def _prepare_ts(df: pd.DataFrame, date_col: str, value_col: str) -> pd.Series:
    """Prepare a clean, sorted, evenly-indexed time series for statsmodels."""
    ts = df[[date_col, value_col]].copy()
    ts[date_col] = pd.to_datetime(ts[date_col], errors="coerce")
    ts = ts.dropna(subset=[date_col, value_col])
    ts = ts.sort_values(date_col)
    ts = ts.set_index(date_col)[value_col].astype(float)
    # Drop duplicate dates (mean)
    if ts.index.has_duplicates:
        ts = ts.groupby(level=0).mean()
    return ts


def _infer_freq(ts: pd.Series) -> str:
    if len(ts) < 3:
        return "D"
    diffs = ts.index.to_series().diff().dropna()
    if diffs.empty:
        return "D"
    median = diffs.median()
    if median <= pd.Timedelta(days=1):
        return "D"
    if median <= pd.Timedelta(days=7):
        return "W"
    if median <= pd.Timedelta(days=31):
        return "M"
    return "D"


class ARIMAForecaster(BaseForecaster):
    name = "ARIMA"

    def __init__(
        self,
        order: Tuple[int, int, int] = (1, 1, 1),
        enforce_stationarity: bool = False,
        enforce_invertibility: bool = False,
    ) -> None:
        super().__init__(order=order, enforce_stationarity=enforce_stationarity,
                         enforce_invertibility=enforce_invertibility)
        self.order = order
        self.enforce_stationarity = enforce_stationarity
        self.enforce_invertibility = enforce_invertibility

    def fit(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        **kwargs: Any,
    ) -> "ARIMAForecaster":
        from statsmodels.tsa.arima.model import ARIMA

        self._date_col = date_col
        self._value_col = value_col
        ts = _prepare_ts(df, date_col, value_col)
        self._train_df = ts.reset_index()
        self._last_date = ts.index[-1] if len(ts) else None
        freq = kwargs.get("frequency")
        self._frequency = self._normalize_frequency(freq if freq else _infer_freq(ts))

        if len(ts) < 5:
            raise ValueError("ARIMA requires at least 5 data points")

        # Try the requested order, fall back to (1,1,1), then to (0,1,0)
        orders_to_try = [self.order, (1, 1, 1), (0, 1, 0)]
        last_err: Optional[Exception] = None
        for order in orders_to_try:
            try:
                model = ARIMA(
                    ts,
                    order=order,
                    enforce_stationarity=self.enforce_stationarity,
                    enforce_invertibility=self.enforce_invertibility,
                )
                self._fitted_model = model.fit(method_kwargs={"warn_convergence": False})
                self.order = order
                return self
            except Exception as e:
                last_err = e
                logger.warning("ARIMA order %s failed: %s", order, e)
                continue
        raise RuntimeError(f"ARIMA failed for all orders: {last_err}")

    def forecast(
        self,
        horizon: int,
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        if self._fitted_model is None or self._last_date is None:
            raise ValueError("Model not fitted")
        pred = self._fitted_model.get_forecast(steps=horizon)
        mean = pred.predicted_mean
        try:
            ci = pred.conf_int(alpha=0.05)
            lower = ci.iloc[:, 0].values
            upper = ci.iloc[:, 1].values
        except Exception:
            std = np.asarray(pred.predicted_mean).std() or 1.0
            lower = np.asarray(mean) - 1.96 * std
            upper = np.asarray(mean) + 1.96 * std

        results: List[Dict[str, Any]] = []
        freq = self._frequency or "D"
        for i, val in enumerate(mean):
            d = self._last_date + pd.tseries.frequencies.to_offset(freq) * (i + 1)
            results.append({
                "date": self._format_date(d),
                "forecast": self._safe_float(val),
                "lower_ci": self._safe_float(lower[i] if i < len(lower) else val * 0.85),
                "upper_ci": self._safe_float(upper[i] if i < len(upper) else val * 1.15),
            })
        return results

    def get_baseline(
        self,
        horizon: int,
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        # ARIMA baseline = forecast with no exog (same as forecast)
        return self.forecast(horizon, exog_data=None, **kwargs)

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


class SARIMAXForecaster(BaseForecaster):
    name = "SARIMAX"

    def __init__(
        self,
        order: Tuple[int, int, int] = (1, 1, 1),
        seasonal_order: Tuple[int, int, int, int] = (1, 1, 1, 7),
    ) -> None:
        super().__init__(order=order, seasonal_order=seasonal_order)
        self.order = order
        self.seasonal_order = seasonal_order

    def _build_exog(
        self,
        ts: pd.Series,
        exog_data: Optional[Dict[str, pd.DataFrame]],
    ) -> Optional[pd.Series]:
        """Build an in-sample exog series aligned to ts. Returns None if
        it cannot be aligned. Combines promotions / media / holidays."""
        if not exog_data:
            return None
        frames = []
        for key in ("promotions", "media_plan", "holidays", "events"):
            df = exog_data.get(key)
            if df is None or df.empty:
                continue
            if "date" not in df.columns:
                continue
            sub = df[["date"]].copy()
            sub["date"] = pd.to_datetime(sub["date"], errors="coerce")
            sub = sub.dropna()
            if sub.empty:
                continue
            sub[f"{key}_flag"] = 1
            frames.append(sub)
        if not frames:
            return None
        merged = frames[0]
        for f in frames[1:]:
            merged = pd.concat([merged, f], ignore_index=True)
        # Aggregate duplicate dates
        agg = merged.groupby("date").sum()
        # Align to ts index
        aligned = agg.reindex(ts.index, method="ffill").fillna(0.0)
        # Single combined column (sum of flags)
        cols = [c for c in aligned.columns]
        if not cols:
            return None
        return aligned[cols[0]].astype(float)

    def fit(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        **kwargs: Any,
    ) -> "SARIMAXForecaster":
        from statsmodels.tsa.statespace.sarimax import SARIMAX

        self._date_col = date_col
        self._value_col = value_col
        ts = _prepare_ts(df, date_col, value_col)
        self._train_df = ts.reset_index()
        self._last_date = ts.index[-1] if len(ts) else None
        freq = kwargs.get("frequency")
        self._frequency = self._normalize_frequency(freq if freq else _infer_freq(ts))

        if len(ts) < 10:
            raise ValueError("SARIMAX requires at least 10 data points")

        exog = self._build_exog(ts, kwargs.get("exog_data"))
        self._has_exog = exog is not None

        # Try multiple seasonal_orders — short series often fails on
        # seasonal terms. Fall back to a non-seasonal SARIMAX(p,d,q).
        order_candidates = [self.order, (1, 1, 1), (0, 1, 1)]
        seasonal_candidates = [self.seasonal_order, (1, 1, 1, 7), (0, 0, 0, 0)]

        last_err: Optional[Exception] = None
        for order in order_candidates:
            for sorder in seasonal_candidates:
                try:
                    model = SARIMAX(
                        ts,
                        exog=exog,
                        order=order,
                        seasonal_order=sorder,
                        enforce_stationarity=False,
                        enforce_invertibility=False,
                    )
                    self._fitted_model = model.fit(disp=False)
                    self.order = order
                    self.seasonal_order = sorder
                    self._exog = exog
                    return self
                except Exception as e:
                    last_err = e
                    continue
        # Final fallback: plain ARIMA-like
        try:
            from statsmodels.tsa.arima.model import ARIMA
            model = ARIMA(ts, order=(1, 1, 1), enforce_stationarity=False)
            self._fitted_model = model.fit()
            self.order = (1, 1, 1)
            self.seasonal_order = (0, 0, 0, 0)
            self._exog = None
            return self
        except Exception as e:
            raise RuntimeError(f"SARIMAX failed: {last_err or e}")

    def _future_exog(
        self,
        horizon: int,
        exog_data: Optional[Dict[str, pd.DataFrame]],
    ) -> Optional[np.ndarray]:
        if exog_data is None:
            return None
        # Build a future date index matching forecast horizon
        freq = self._frequency or "D"
        future_idx = pd.date_range(
            start=self._last_date + pd.tseries.frequencies.to_offset(freq),
            periods=horizon,
            freq=freq,
        )
        merged = pd.DataFrame({"date": future_idx})
        any_added = False
        for key in ("promotions", "media_plan", "holidays", "events"):
            df = exog_data.get(key)
            if df is None or df.empty or "date" not in df.columns:
                continue
            sub = df[["date"]].copy()
            sub["date"] = pd.to_datetime(sub["date"], errors="coerce")
            sub = sub.dropna()
            if sub.empty:
                continue
            sub[f"{key}_flag"] = 1
            sub = sub.drop_duplicates(subset=["date"])
            merged = merged.merge(sub, on="date", how="left")
            any_added = True
        if not any_added:
            return None
        flag_cols = [c for c in merged.columns if c.endswith("_flag")]
        if not flag_cols:
            return None
        merged["_exog"] = merged[flag_cols].sum(axis=1)
        return merged["_exog"].fillna(0.0).astype(float).values

    def forecast(
        self,
        horizon: int,
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        if self._fitted_model is None or self._last_date is None:
            raise ValueError("Model not fitted")
        future_exog = self._future_exog(horizon, exog_data) if getattr(self, "_has_exog", False) else None
        try:
            pred = self._fitted_model.get_forecast(steps=horizon, exog=future_exog)
            mean = pred.predicted_mean
            ci = pred.conf_int(alpha=0.05)
            lower = ci.iloc[:, 0].values
            upper = ci.iloc[:, 1].values
        except Exception as e:
            logger.warning("SARIMAX get_forecast failed: %s — using naive fallback", e)
            last = float(self._train_df[self._value_col].iloc[-1]) if self._train_df is not None else 0.0
            mean = np.array([last] * horizon)
            std = abs(last) * 0.1
            lower = mean - 1.96 * std
            upper = mean + 1.96 * std

        results: List[Dict[str, Any]] = []
        freq = self._frequency or "D"
        for i, val in enumerate(mean):
            d = self._last_date + pd.tseries.frequencies.to_offset(freq) * (i + 1)
            results.append({
                "date": self._format_date(d),
                "forecast": self._safe_float(val),
                "lower_ci": self._safe_float(lower[i] if i < len(lower) else val * 0.85),
                "upper_ci": self._safe_float(upper[i] if i < len(upper) else val * 1.15),
            })
        return results

    def get_baseline(
        self,
        horizon: int,
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Baseline: forecast with future exog forced to zero."""
        if self._fitted_model is None or self._last_date is None:
            raise ValueError("Model not fitted")
        zero_exog = np.zeros(horizon) if getattr(self, "_has_exog", False) else None
        try:
            pred = self._fitted_model.get_forecast(steps=horizon, exog=zero_exog)
            mean = pred.predicted_mean
            ci = pred.conf_int(alpha=0.05)
            lower = ci.iloc[:, 0].values
            upper = ci.iloc[:, 1].values
        except Exception:
            last = float(self._train_df[self._value_col].iloc[-1]) if self._train_df is not None else 0.0
            mean = np.array([last] * horizon)
            std = abs(last) * 0.1
            lower = mean - 1.96 * std
            upper = mean + 1.96 * std
        results: List[Dict[str, Any]] = []
        freq = self._frequency or "D"
        for i, val in enumerate(mean):
            d = self._last_date + pd.tseries.frequencies.to_offset(freq) * (i + 1)
            results.append({
                "date": self._format_date(d),
                "forecast": self._safe_float(val),
                "lower_ci": self._safe_float(lower[i] if i < len(lower) else val * 0.85),
                "upper_ci": self._safe_float(upper[i] if i < len(upper) else val * 1.15),
            })
        return results

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
