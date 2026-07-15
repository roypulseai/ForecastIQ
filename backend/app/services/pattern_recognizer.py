"""Time-series pattern recognition: frequency, seasonality, trend,
external-factor correlation, and lag-structure analysis.

The PatternProfile produced by this module drives the AutoML model's
architecture-selection logic.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public profile types
# ---------------------------------------------------------------------------


@dataclass
class PatternProfile:
    """Structural description of a time series."""

    # Frequency
    frequency: str = "D"
    freq_gap_days: float = 1.0

    # Seasonality
    seasonal_period: Optional[int] = None  # e.g. 7, 12, 52
    seasonal_strength: float = 0.0

    # Trend
    trend_type: str = "none"  # "linear", "polynomial", "logistic", "none"
    trend_strength: float = 0.0
    trend_slope: float = 0.0

    # Autocorrelation (up to 30 lags)
    acf_peaks: List[int] = field(default_factory=list)
    pacf_peaks: List[int] = field(default_factory=list)
    has_ar: bool = False
    has_ma: bool = False

    # External factors
    exog_correlations: Dict[str, float] = field(default_factory=dict)
    exog_lags: Dict[str, int] = field(default_factory=dict)  # best lag per factor
    best_exog_lag_corr: Dict[str, float] = field(default_factory=dict)

    # Data shape
    n_points: int = 0
    n_unique_dates: int = 0
    sparsity: float = 0.0  # fraction of zero values
    variance: float = 0.0
    cv: float = 0.0  # coefficient of variation

    # Recommended model architecture
    architecture: str = "auto"  # will be set by AutoML


# ---------------------------------------------------------------------------
# Pattern analyzer
# ---------------------------------------------------------------------------


class PatternRecognizer:
    """Analyse a time series and produce a PatternProfile."""

    def analyze(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> PatternProfile:
        dates = pd.to_datetime(df[date_col], errors="coerce")
        values = pd.to_numeric(df[value_col], errors="coerce")
        mask = dates.notna() & values.notna()
        dates = dates[mask].reset_index(drop=True)
        values = values[mask].reset_index(drop=True)

        if len(dates) < 3:
            return PatternProfile(n_points=len(dates), n_unique_dates=len(dates))

        sorted_idx = np.argsort(dates)
        dates = dates.iloc[sorted_idx].reset_index(drop=True)
        values = values.iloc[sorted_idx].reset_index(drop=True)

        prof = PatternProfile(
            n_points=len(values),
            n_unique_dates=dates.nunique(),
            sparsity=float((values == 0).mean()),
            variance=float(values.var()) if len(values) > 1 else 0.0,
            cv=float(values.std() / values.mean()) if values.mean() != 0 else 0.0,
        )

        self._detect_frequency(dates, prof)
        self._detect_seasonality(dates, values, prof)
        self._detect_trend(values, prof)
        self._detect_acf_pacf(values, prof)
        self._detect_exog(df, date_col, value_col, exog_data, prof)

        return prof

    # ------------------------------------------------------------------
    # Frequency
    # ------------------------------------------------------------------
    @staticmethod
    def _detect_frequency(dates: pd.Series, prof: PatternProfile) -> None:
        deltas = dates.diff().dropna()
        if deltas.empty:
            return
        median_gap = deltas.median()
        prof.freq_gap_days = float(median_gap.days) if hasattr(median_gap, "days") else float(median_gap / pd.Timedelta(days=1))
        if prof.freq_gap_days <= 1.5:
            prof.frequency = "D"
        elif prof.freq_gap_days <= 3.5:
            prof.frequency = "2D"
        elif prof.freq_gap_days <= 10:
            prof.frequency = "W"
        elif prof.freq_gap_days <= 20:
            prof.frequency = "2W"
        elif prof.freq_gap_days <= 45:
            prof.frequency = "MS"
        elif prof.freq_gap_days <= 100:
            prof.frequency = "QS"
        else:
            prof.frequency = "YS"

    # ------------------------------------------------------------------
    # Seasonality
    # ------------------------------------------------------------------
    @staticmethod
    def _detect_seasonality(dates: pd.Series, values: pd.Series, prof: PatternProfile) -> None:
        if len(values) < 14:
            return
        ts = values.set_axis(dates)
        # Try a few candidate periods based on frequency
        if prof.frequency == "D":
            candidates = [7, 14, 30, 365]
        elif prof.frequency == "W":
            candidates = [4, 13, 52]
        elif prof.frequency in ("MS", "QS"):
            candidates = [6, 12]
        else:
            candidates = [4]

        best_period = None
        best_strength = 0.0
        for period in candidates:
            if len(ts) < period * 2:
                continue
            try:
                # Seasonal strength via STL decomposition heuristic:
                # detrend by diff, then measure autocorrelation at period
                detrended = ts.diff().dropna()
                if len(detrended) < period + 5:
                    continue
                ac = detrended.autocorr(lag=period)
                strength = max(0.0, ac)
                if strength > best_strength:
                    best_strength = strength
                    best_period = period
            except Exception:
                continue

        prof.seasonal_period = best_period
        prof.seasonal_strength = best_strength

    # ------------------------------------------------------------------
    # Trend
    # ------------------------------------------------------------------
    @staticmethod
    def _detect_trend(values: pd.Series, prof: PatternProfile) -> None:
        if len(values) < 5:
            return
        x = np.arange(len(values))
        y = values.values
        # Linear trend
        try:
            coeffs = np.polyfit(x, y, 1)
            trend_line = np.polyval(coeffs, x)
            residuals = y - trend_line
            ss_res = np.sum(residuals ** 2)
            ss_tot = np.sum((y - y.mean()) ** 2)
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
            if r2 > 0.2:
                prof.trend_type = "linear"
                prof.trend_strength = float(r2)
                prof.trend_slope = float(coeffs[0])
                return
        except Exception:
            pass
        # Check for no trend
        try:
            ac1 = pd.Series(y).autocorr(lag=1) or 0.0
            if abs(ac1) < 0.05:
                prof.trend_type = "none"
        except Exception:
            pass

    # ------------------------------------------------------------------
    # ACF / PACF
    # ------------------------------------------------------------------
    @staticmethod
    def _detect_acf_pacf(values: pd.Series, prof: PatternProfile) -> None:
        if len(values) < 10:
            return
        y = values.values
        n = len(y)
        max_lag = min(30, n // 3)
        if max_lag < 2:
            return
        # Simple ACF
        mean_y = y.mean()
        var_y = y.var()
        if var_y == 0:
            return
        acf = np.array([
            np.corrcoef(y[:-lag], y[lag:])[0, 1] if lag < n else 0.0
            for lag in range(1, max_lag + 1)
        ])
        threshold = 1.96 / np.sqrt(n)
        significant = np.where(np.abs(acf) > threshold)[0] + 1
        prof.acf_peaks = significant.tolist()
        # AR signature: acf decays exponentially → AR likely
        if len(acf) > 3:
            acf_decline = np.abs(acf[:3] - 0).sum() / max(1, len(acf[:3]))
            prof.has_ar = acf_decline > threshold * 2
        # MA signature: acf has sharp cut-off after lag q
        prof.has_ma = len(significant) <= 2  # simple heuristic

    # ------------------------------------------------------------------
    # External factor correlations
    # ------------------------------------------------------------------
    @staticmethod
    def _detect_exog(
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        exog_data: Optional[Dict[str, pd.DataFrame]],
        prof: PatternProfile,
    ) -> None:
        if not exog_data:
            return
        target = df[[date_col, value_col]].copy()
        target[date_col] = pd.to_datetime(target[date_col], errors="coerce")
        target[value_col] = pd.to_numeric(target[value_col], errors="coerce")
        target = target.dropna().sort_values(date_col).reset_index(drop=True)
        if len(target) < 10:
            return

        for factor_name, factor_df in exog_data.items():
            if factor_df is None or factor_df.empty:
                continue
            merged = target.merge(
                factor_df, left_on=date_col, right_on="date", how="inner",
                suffixes=("_target", "_exog"),
            )
            if len(merged) < 5:
                continue
            target_val_col = f"{value_col}_target"
            if target_val_col not in merged.columns:
                target_val_col = value_col if value_col in merged.columns else "value"
            numeric_cols = merged.select_dtypes(include=[np.number]).columns.tolist()
            exog_cols = [c for c in numeric_cols if c != target_val_col and c != date_col]
            if not exog_cols:
                continue

            for exog_col in exog_cols:
                key = f"{factor_name}/{exog_col}"
                corr = merged[target_val_col].corr(merged[exog_col])
                prof.exog_correlations[key] = float(corr) if pd.notna(corr) else 0.0

                best_lag = 0
                best_xcorr = 0.0
                y = merged[target_val_col].values
                x = merged[exog_col].values
                for lag in range(0, min(30, len(y) // 3)):
                    if lag == 0:
                        xcorr = float(np.corrcoef(y, x)[0, 1]) if len(y) > 2 else 0.0
                    elif lag < len(y):
                        xcorr = float(np.corrcoef(y[lag:], x[:-lag])[0, 1]) if len(y) - lag > 2 else 0.0
                    else:
                        break
                    xcorr = abs(xcorr) if pd.notna(xcorr) else 0.0
                    if xcorr > best_xcorr:
                        best_xcorr = xcorr
                        best_lag = lag
                if best_xcorr > 0.1:
                    prof.exog_lags[key] = best_lag
                    prof.best_exog_lag_corr[key] = best_xcorr
