"""AutoML forecaster — pattern-driven architecture selection.

Analyses the input time series (frequency, seasonality, trend, exog
correlation, lag structure) and selects + fits the optimal model
architecture automatically.  May build hybrid models (e.g. Prophet
backbone + XGBoost residual correction) when the data warrants it.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..pattern_recognizer import PatternProfile, PatternRecognizer
from .base import BaseForecaster

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Architecture strategies
# ---------------------------------------------------------------------------

_STRATEGY_LABELS = {
    "prophet_xgb": "Prophet + XGBoost residual correction",
    "lightgbm_feat": "LightGBM with auto-engineered features",
    "prophet": "Prophet with regressors",
    "sarimax": "SARIMAX with external factors",
    "theta_stl": "Theta / STL decomposition",
    "ets_simple": "ETS simple exponential smoothing",
    "wma_seasonal": "WMA with seasonal factors",
    "arima": "ARIMA with autocorrelation modelling",
    "lightgbm_default": "LightGBM (default config)",
}


class AutoMLForecaster(BaseForecaster):
    """Meta-model that analyses data patterns then selects and fits the
    optimal model architecture automatically."""

    name = "AutoML"

    def __init__(self, **params: Any) -> None:
        super().__init__(**params)
        self._recognizer = PatternRecognizer()
        self._profile: Optional[PatternProfile] = None
        self._strategy: str = "auto"
        self._inner_model: Optional[BaseForecaster] = None
        self._residual_model: Optional[BaseForecaster] = None
        self._df: Optional[pd.DataFrame] = None
        self._exog_data: Optional[Dict[str, pd.DataFrame]] = None

    # ------------------------------------------------------------------
    # Fit
    # ------------------------------------------------------------------
    def fit(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        **kwargs: Any,
    ) -> "AutoMLForecaster":
        self._date_col = date_col
        self._value_col = value_col
        self._frequency = self._infer_frequency(df, date_col)
        dates_sorted = pd.to_datetime(df[date_col].dropna(), errors="coerce").sort_values()
        self._last_date = dates_sorted.iloc[-1] if len(dates_sorted) else None
        exog_data: Optional[Dict[str, pd.DataFrame]] = kwargs.get("exog_data")

        # Run pattern recognition
        self._profile = self._recognizer.analyze(df, date_col, value_col, exog_data)
        self._df = df.copy()
        self._exog_data = exog_data

        # Select architecture
        self._strategy = self._select_architecture(self._profile, exog_data)
        self._profile.architecture = self._strategy

        logger.info(
            "AutoML strategy=%s profile=freq=%s season=period=%s/strength=%.2f "
            "trend=%s/slope=%.2f ar=%s ma=%s n=%d exog=%s",
            self._strategy,
            self._profile.frequency,
            self._profile.seasonal_period,
            self._profile.seasonal_strength,
            self._profile.trend_type,
            self._profile.trend_slope,
            self._profile.has_ar,
            self._profile.has_ma,
            self._profile.n_points,
            list(self._profile.exog_correlations.keys()),
        )

        # Build and fit the inner model
        self._inner_model = self._build_model(self._strategy, df, date_col, value_col, exog_data)
        if self._inner_model is not None:
            self._inner_model.fit(df, date_col, value_col, exog_data=exog_data or {})

        # Build residual model if strategy calls for it
        if self._strategy == "prophet_xgb" and self._inner_model is not None:
            self._fit_residual_model(df, date_col, value_col, exog_data)

        return self

    # ------------------------------------------------------------------
    # Forecast
    # ------------------------------------------------------------------
    def forecast(
        self,
        horizon: int,
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        if self._inner_model is None:
            return self._naive_forecast(horizon)

        primary = self._inner_model.forecast(horizon, exog_data=exog_data)

        if self._residual_model is not None and self._strategy == "prophet_xgb":
            residuals = self._residual_model.forecast(horizon, exog_data=exog_data)
            for i in range(min(len(primary), len(residuals))):
                primary[i]["forecast"] = float(
                    self._safe_float(primary[i].get("forecast")) +
                    self._safe_float(residuals[i].get("forecast")) * 0.3,
                )
                # Widen CI slightly to reflect residual uncertainty
                ci_half = (self._safe_float(primary[i].get("upper_ci", 0)) -
                           self._safe_float(primary[i].get("forecast", 0))) or (primary[i].get("forecast", 0) * 0.1)
                primary[i]["lower_ci"] = self._safe_float(primary[i].get("forecast")) - ci_half * 1.2
                primary[i]["upper_ci"] = self._safe_float(primary[i].get("forecast")) + ci_half * 1.2

        return primary

    # ------------------------------------------------------------------
    # Baseline
    # ------------------------------------------------------------------
    def get_baseline(
        self,
        horizon: int,
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        if self._inner_model is not None and self._strategy != "prophet_xgb":
            return self._inner_model.get_baseline(horizon, exog_data=None)
        return self.forecast(horizon, exog_data=None)

    # ------------------------------------------------------------------
    # Components
    # ------------------------------------------------------------------
    def get_components(self) -> Dict[str, Any]:
        comps: Dict[str, Any] = {
            "strategy": self._strategy,
            "strategy_label": _STRATEGY_LABELS.get(self._strategy, self._strategy),
        }
        if self._profile:
            comps["profile"] = {
                "frequency": self._profile.frequency,
                "seasonal_period": self._profile.seasonal_period,
                "seasonal_strength": round(self._profile.seasonal_strength, 3),
                "trend_type": self._profile.trend_type,
                "trend_strength": round(self._profile.trend_strength, 3),
                "trend_slope": round(self._profile.trend_slope, 3),
                "has_ar": self._profile.has_ar,
                "has_ma": self._profile.has_ma,
                "n_points": self._profile.n_points,
                "sparsity": round(self._profile.sparsity, 3),
                "exog_correlations": self._profile.exog_correlations,
                "exog_lags": self._profile.exog_lags,
            }
        if self._inner_model:
            inner_comps = self._inner_model.get_components()
            if inner_comps:
                comps["inner"] = inner_comps
        return comps

    # ------------------------------------------------------------------
    # Feature importance
    # ------------------------------------------------------------------
    def get_feature_importance(self) -> Dict[str, float]:
        if self._inner_model is not None:
            return self._inner_model.get_feature_importance()
        return {}

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------
    def get_metrics(self) -> Dict[str, float]:
        if self._inner_model is not None:
            return self._inner_model.get_metrics()
        return {}

    # ------------------------------------------------------------------
    # Architecture selection
    # ------------------------------------------------------------------
    @staticmethod
    def _select_architecture(
        prof: PatternProfile,
        exog_data: Optional[Dict[str, pd.DataFrame]],
    ) -> str:
        has_exog = exog_data is not None and any(
            v is not None and not v.empty for v in exog_data.values()
        )
        n = prof.n_points
        season = prof.seasonal_strength
        trend = prof.trend_strength
        slope = abs(prof.trend_slope)
        sparsity = prof.sparsity
        exog_corr = prof.exog_correlations
        has_strong_exog = any(abs(c) > 0.3 for c in exog_corr.values()) if exog_corr else False

        # Rule 1: High frequency data with strong exog → LightGBM with features
        if n >= 100 and (has_exog and has_strong_exog) and prof.frequency in ("D", "2D"):
            return "lightgbm_feat"

        # Rule 2: Strong seasonality + exog → Prophet + XGBoost residual correction
        if season > 0.3 and n >= 50 and has_exog:
            return "prophet_xgb"

        # Rule 3: Strong seasonality + moderate exog → Prophet
        if season > 0.3 and n >= 30:
            return "prophet"

        # Rule 4: Strong AR signature + exog → SARIMAX
        if prof.has_ar and has_exog and n >= 30:
            return "sarimax"

        # Rule 5: Monthly/quarterly with trend → Theta / STL
        if prof.frequency in ("MS", "QS") and trend > 0.2:
            return "theta_stl"

        # Rule 6: Sparse/intermittent → WMA with seasonal factors
        if sparsity > 0.3 or n < 30:
            return "wma_seasonal"

        # Rule 7: Strong AR/MA signature → ARIMA
        if prof.has_ar or prof.has_ma:
            return "arima"

        # Rule 8: fallback → ETS
        return "ets_simple"

    # ------------------------------------------------------------------
    # Model factory
    # ------------------------------------------------------------------
    def _build_model(
        self,
        strategy: str,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        exog_data: Optional[Dict[str, pd.DataFrame]],
    ) -> BaseForecaster:
        from ..model_selector import ModelSelector

        sel = ModelSelector()
        params: Dict[str, Any] = {}

        if strategy == "prophet_xgb":
            # Prophet with auto-configured seasonality
            p = self._profile
            season_mode = "multiplicative" if (p.trend_strength > 0.3) else "additive"
            params["prophet"] = {
                "seasonality_mode": season_mode,
                "yearly_seasonality": True,
                "weekly_seasonality": p.frequency == "D",
                "changepoint_prior_scale": 0.05,
            }
            return sel.get_model("prophet", params)

        if strategy == "lightgbm_feat":
            p = self._profile
            params["lightgbm"] = {
                "n_estimators": 500,
                "learning_rate": 0.03,
                "max_depth": 7,
                "num_leaves": 63,
                "min_child_samples": 10,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
            }
            return sel.get_model("lightgbm", params)

        if strategy == "prophet":
            p = self._profile
            season_mode = "multiplicative" if (p.trend_type == "linear" and p.trend_slope > 0.01) else "additive"
            params["prophet"] = {
                "seasonality_mode": season_mode,
                "yearly_seasonality": True,
                "weekly_seasonality": p.frequency == "D",
                "changepoint_prior_scale": 0.02 if p.trend_strength > 0.3 else 0.05,
            }
            return sel.get_model("prophet", params)

        if strategy == "sarimax":
            p = self._profile
            seasonal_p = p.seasonal_period or 7
            params["sarimax"] = {
                "p": 2 if p.has_ar else 1,
                "d": 1 if p.trend_type == "linear" else 0,
                "q": 2 if p.has_ma else 1,
                "seasonal_p": 1,
                "seasonal_d": 0,
                "seasonal_q": 1,
                "seasonal_period": seasonal_p,
            }
            return sel.get_model("sarimax", params)

        if strategy == "theta_stl":
            p = self._profile
            period = p.seasonal_period or 12
            return sel.get_model("theta", {"theta": {"period": period, "deseasonalize": True}})

        if strategy == "wma_seasonal":
            window = max(4, min(30, len(df) // 5))
            return sel.get_model("wma", {"wma": {"window": window}})

        if strategy == "arima":
            p = self._profile
            params["arima"] = {
                "p": 2 if p.has_ar else 1,
                "d": 1 if p.trend_type == "linear" else 0,
                "q": 2 if p.has_ma else 1,
            }
            return sel.get_model("arima", params)

        # Default: ETS
        p = self._profile
        period = p.seasonal_period or 7
        return sel.get_model("ets", {"ets": {"trend": "add", "seasonal": "add", "seasonal_periods": period}})

    # ------------------------------------------------------------------
    # Residual model (Prophet + XGBoost hybrid)
    # ------------------------------------------------------------------
    def _fit_residual_model(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        exog_data: Optional[Dict[str, pd.DataFrame]],
    ) -> None:
        if self._inner_model is None:
            return
        try:
            # Get in-sample predictions from Prophet
            horizon_insample = len(df)
            preds = self._inner_model.forecast(horizon_insample, exog_data=exog_data)
            actuals = pd.to_numeric(df[value_col], errors="coerce").values
            residuals = []
            for i, p in enumerate(preds[:len(actuals)]):
                av = float(actuals[i]) if i < len(actuals) else 0.0
                pv = self._safe_float(p.get("forecast", 0))
                residuals.append(av - pv)

            # Build a small XGBoost model on residuals using exog features
            from ..model_selector import ModelSelector
            sel = ModelSelector()
            residual_model = sel.get_model("xgboost", {"xgboost": {
                "n_estimators": 100,
                "learning_rate": 0.05,
                "max_depth": 3,
                "min_child_weight": 3,
            }})
            # Create a df with residuals as target
            res_df = df.copy()
            res_df[value_col] = residuals[:len(df)]
            residual_model.fit(res_df, date_col, value_col, exog_data=exog_data or {})
            self._residual_model = residual_model
            logger.info("Fitted XGBoost residual correction model on %d points", len(residuals))
        except Exception as e:
            logger.warning("Residual model fitting failed (continuing without): %s", e)

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------
    def _naive_forecast(self, horizon: int) -> List[Dict[str, Any]]:
        last_val = 0.0
        if self._df is not None and self._value_col:
            last_val = float(self._df[self._value_col].iloc[-1]) if len(self._df) else 0.0
        results = []
        for i in range(horizon):
            d = pd.Timestamp.now() + pd.Timedelta(days=i + 1)
            results.append({
                "date": self._format_date(d),
                "forecast": last_val,
                "lower_ci": last_val * 0.8,
                "upper_ci": last_val * 1.2,
            })
        return results

    # ------------------------------------------------------------------
    # Uplift (attach uplift to forecast values for what-if analysis)
    # ------------------------------------------------------------------
    def get_shap_importance(self) -> Dict[str, Any]:
        if self._inner_model is not None:
            return self._inner_model.get_shap_importance()
        return {"training_importance": {}, "per_step": None, "base_value": None}
