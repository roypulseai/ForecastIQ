"""Time-series decomposition and seasonality detection."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def detect_seasonal_periods(
    series: pd.Series,
    max_period: int = 365,
    top_k: int = 3,
) -> List[int]:
    """Detect the dominant seasonal periods in a time series using FFT.

    Returns the top-k periods sorted by strength (strongest first).
    Only returns periods that are at least 2 and at most max_period.
    """
    try:
        vals = series.dropna().values
        if len(vals) < max_period * 2:
            max_period = max(7, len(vals) // 4)

        n = len(vals)
        fft = np.fft.rfft(vals - np.mean(vals))
        freqs = np.fft.rfftfreq(n)
        magnitudes = np.abs(fft)

        # Skip DC component and very low frequencies
        periods = []
        for i in range(1, len(freqs)):
            if freqs[i] > 0 and magnitudes[i] > 1e-6:
                period = int(round(1.0 / freqs[i]))
                if 2 <= period <= max_period:
                    periods.append((period, magnitudes[i]))

        periods.sort(key=lambda x: x[1], reverse=True)
        # Deduplicate near-duplicate periods (e.g., 6 and 7)
        unique: List[Tuple[int, float]] = []
        for p, m in periods:
            if not any(abs(p - up) / max(up, 1) < 0.2 for up, _ in unique):
                unique.append((p, m))

        return [p for p, _ in unique[:top_k]]
    except Exception as e:
        logger.debug("FFT period detection failed: %s", e)
        return []


def detect_seasonal_periods_acf(
    series: pd.Series,
    max_lag: int = 365,
    top_k: int = 3,
) -> List[int]:
    """Detect seasonal periods using autocorrelation (ACF).

    Looks for significant lags where autocorrelation peaks.
    """
    try:
        vals = series.dropna().values
        n = len(vals)
        max_lag = min(max_lag, n // 3)
        if max_lag < 7:
            return []

        mean = np.mean(vals)
        std = np.std(vals)
        if std < 1e-9:
            return []

        acf = np.correlate(vals - mean, vals - mean, mode="full")[n - 1:] / (std * std * np.arange(n, 0, -1))
        acf = acf[:max_lag + 1]

        # Find peaks: local maxima above significance threshold (2/sqrt(n))
        threshold = 2.0 / np.sqrt(n)
        peaks: List[Tuple[int, float]] = []
        for i in range(2, len(acf) - 1):
            if acf[i] > threshold and acf[i] > acf[i - 1] and acf[i] > acf[i + 1]:
                peaks.append((i, acf[i]))

        peaks.sort(key=lambda x: x[1], reverse=True)
        # Deduplicate near-duplicate
        unique: List[Tuple[int, float]] = []
        for p, m in peaks:
            if not any(abs(p - up) / max(up, 1) < 0.2 for up, _ in unique):
                unique.append((p, m))

        return [p for p, _ in unique[:top_k]]
    except Exception as e:
        logger.debug("ACF period detection failed: %s", e)
        return []


def decompose_series(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    period: Optional[int] = None,
) -> Dict[str, Any]:
    """Decompose a time series into trend, seasonal, and residual components.

    Uses STL decomposition from statsmodels (robust to outliers).
    If period is not provided, auto-detects the dominant seasonal period.

    Returns a dict with:
        period: int — the seasonal period used
        trend: List[float] — trend component
        seasonal: List[float] — seasonal component
        residual: List[float] — residual/noise component
        seasonal_strength: float — 0-1, how strong the seasonal pattern is
        dates: List[str] — aligned date labels
    """
    try:
        from statsmodels.tsa.seasonal import STL

        ts = df[[date_col, value_col]].copy()
        ts[date_col] = pd.to_datetime(ts[date_col], errors="coerce")
        ts[value_col] = pd.to_numeric(ts[value_col], errors="coerce")
        ts = ts.dropna().sort_values(date_col).reset_index(drop=True)

        if len(ts) < 14:
            return {"period": None, "error": "Not enough data for decomposition (<14 points)"}

        # Auto-detect period if not provided
        if period is None or period < 2:
            detected = detect_seasonal_periods(ts[value_col], max_period=min(365, len(ts) // 2))
            period = detected[0] if detected else max(2, len(ts) // 10)

        period = max(2, min(period, len(ts) // 2))

        stl_result = STL(ts[value_col], period=period, robust=True).fit()

        seasonal_arr = np.array(stl_result.seasonal, copy=True)
        trend_arr = np.array(stl_result.trend, copy=True)
        resid_arr = np.array(stl_result.resid, copy=True)
        # Replace NaN in trend (STL pads trend with NaN at edges)
        trend_arr = np.nan_to_num(trend_arr, nan=np.nanmean(trend_arr) if not np.all(np.isnan(trend_arr)) else 0.0)

        seasonal_vals = seasonal_arr.tolist()
        trend_vals = trend_arr.tolist()
        residual_vals = resid_arr.tolist()
        dates = ts[date_col].dt.strftime("%Y-%m-%d").tolist()

        # Compute seasonal strength (0-1): how much of the variance is explained by seasonality
        combined = resid_arr + seasonal_arr + trend_arr
        var_total = float(np.var(combined)) if len(combined) > 0 else 0
        var_seasonal = float(np.var(seasonal_arr)) if var_total > 1e-9 else 0
        seasonal_strength = min(1.0, var_seasonal / var_total) if var_total > 1e-9 else 0.0

        return {
            "period": period,
            "dates": dates,
            "trend": trend_vals,
            "seasonal": seasonal_vals,
            "residual": residual_vals,
            "seasonal_strength": round(seasonal_strength, 4),
            "error": None,
        }
    except Exception as e:
        logger.warning("Decomposition failed: %s", e)
        return {"period": None, "error": str(e)}


def recommend_seasonal_params(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    model_type: str,
) -> Dict[str, Any]:
    """Return model-specific seasonality recommendations based on detected patterns.

    For example, if weekly seasonality is detected in daily data, sets
    seasonal_periods=7 for ETS/Theta/STL, or adds weekly_seasonality=True for Prophet.
    """
    series = pd.to_numeric(df[value_col], errors="coerce").dropna()
    if len(series) < 14:
        return {}

    periods = detect_seasonal_periods(series, max_period=min(365, len(series) // 2))
    if not periods:
        periods = detect_seasonal_periods_acf(series, max_period=min(365, len(series) // 2))
    if not periods:
        return {}

    primary = periods[0]
    params: Dict[str, Any] = {}

    if model_type in ("ets", "theta", "stl", "wma"):
        params["seasonal_periods"] = primary
    elif model_type == "sarimax":
        params["seasonal_period"] = primary
    elif model_type == "prophet":
        # Enable yearly seasonality if period >= 52 (weekly data) or ~365 (daily data)
        if primary in (52, 53):
            params["yearly_seasonality"] = True
            params["weekly_seasonality"] = False
        elif primary == 12:
            params["yearly_seasonality"] = True
        elif primary == 7:
            params["weekly_seasonality"] = True
        elif primary == 30:
            params["yearly_seasonality"] = True
        if len(periods) > 1:
            secondary = periods[1]
            if secondary == 7 and primary != 7:
                params["weekly_seasonality"] = True
            elif secondary == 30 and primary != 30:
                params["yearly_seasonality"] = False  # monthly pattern

    return params
