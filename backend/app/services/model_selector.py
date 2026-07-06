"""Model factory + analysis helpers."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .models.arima import ARIMAForecaster, SARIMAXForecaster
from .models.base import BaseForecaster
from .models.ets_model import ETSForecaster
from .models.lightgbm_model import LightGBMForecaster
from .models.prophet_model import ProphetForecaster
from .models.stl_model import STLForecaster
from .models.theta_model import ThetaForecaster
from .models.wma_model import WMAForecaster
from .models.xgboost_model import XGBoostForecaster

logger = logging.getLogger(__name__)


class ModelSelector:
    """Factory + advisor for all forecasting models."""

    MODEL_CLASSES = {
        "arima": ARIMAForecaster,
        "sarimax": SARIMAXForecaster,
        "prophet": ProphetForecaster,
        "lightgbm": LightGBMForecaster,
        "xgboost": XGBoostForecaster,
        "wma": WMAForecaster,
        "ets": ETSForecaster,
        "theta": ThetaForecaster,
        "stl": STLForecaster,
    }

    def __init__(self) -> None:
        self.last_characteristics: Dict[str, Any] = {}

    # ----------------------------------------------------------- factory
    def get_model(self, model_type: str, params: Optional[Dict[str, Any]] = None) -> BaseForecaster:
        model_type = (model_type or "").lower()
        if model_type not in self.MODEL_CLASSES:
            raise ValueError(f"Unknown model type: {model_type}. "
                             f"Available: {list(self.MODEL_CLASSES.keys())}")
        p = params or {}
        m = self.MODEL_CLASSES[model_type]

        if model_type == "arima":
            ap = p.get("arima") or {}
            return m(order=(ap.get("p", 1), ap.get("d", 1), ap.get("q", 1)))
        if model_type == "sarimax":
            sp = p.get("sarimax") or {}
            return m(
                order=(sp.get("p", 1), sp.get("d", 1), sp.get("q", 1)),
                seasonal_order=(
                    sp.get("seasonal_p", 1),
                    sp.get("seasonal_d", 1),
                    sp.get("seasonal_q", 1),
                    sp.get("seasonal_period", 7),
                ),
            )
        if model_type == "prophet":
            pp = p.get("prophet") or {}
            return m(
                seasonality_mode=pp.get("seasonality_mode", "additive"),
                yearly_seasonality=pp.get("yearly_seasonality", True),
                weekly_seasonality=pp.get("weekly_seasonality", True),
                daily_seasonality=pp.get("daily_seasonality", False),
                changepoint_prior_scale=pp.get("changepoint_prior_scale", 0.05),
                seasonality_prior_scale=pp.get("seasonality_prior_scale", 10.0),
                holidays_prior_scale=pp.get("holidays_prior_scale", 10.0),
                country=pp.get("country"),
            )
        if model_type == "lightgbm":
            lp = p.get("lightgbm") or {}
            return m(
                n_estimators=lp.get("n_estimators", 200),
                learning_rate=lp.get("learning_rate", 0.05),
                max_depth=lp.get("max_depth", 5),
                num_leaves=lp.get("num_leaves", 31),
                min_child_samples=lp.get("min_child_samples", 20),
            )
        if model_type == "xgboost":
            xp = p.get("xgboost") or {}
            return m(
                n_estimators=xp.get("n_estimators", 200),
                learning_rate=xp.get("learning_rate", 0.05),
                max_depth=xp.get("max_depth", 5),
                min_child_weight=xp.get("min_child_weight", 1),
                subsample=xp.get("subsample", 0.9),
                colsample_bytree=xp.get("colsample_bytree", 0.9),
            )
        if model_type == "wma":
            wp = p.get("wma") or {}
            return m(window=wp.get("window", 8))
        if model_type == "ets":
            ep = p.get("ets") or {}
            return m(
                trend=ep.get("trend", "add"),
                seasonal=ep.get("seasonal", "add"),
                seasonal_periods=ep.get("seasonal_periods", 7),
            )
        if model_type == "theta":
            tp = p.get("theta") or {}
            return m(period=tp.get("period", 7), deseasonalize=tp.get("deseasonalize", True))
        if model_type == "stl":
            sp = p.get("stl") or {}
            return m(period=sp.get("period", 7), robust=sp.get("robust", True))
        return m()

    # ----------------------------------------------------------- analysis
    def analyze_data(self, df: pd.DataFrame, date_col: str, value_col: str) -> Dict[str, Any]:
        if df.empty or value_col not in df.columns or date_col not in df.columns:
            return {
                "length": 0, "mean": 0.0, "std": 0.0, "cv": 0.0,
                "trend": "unknown", "seasonality": "none", "stationarity": True,
                "outliers_pct": 0.0, "missing_pct": 0.0,
                "min_date": None, "max_date": None,
            }
        ts = df[[date_col, value_col]].copy()
        ts[date_col] = pd.to_datetime(ts[date_col], errors="coerce")
        ts[value_col] = pd.to_numeric(ts[value_col], errors="coerce")
        ts = ts.dropna().sort_values(date_col)
        ts_s = ts.set_index(date_col)[value_col]
        if ts_s.index.has_duplicates:
            ts_s = ts_s.groupby(level=0).mean()
        n = len(ts_s)
        mean = float(ts_s.mean()) if n else 0.0
        std = float(ts_s.std()) if n else 0.0
        cv = float(std / mean) if mean else 0.0
        chars: Dict[str, Any] = {
            "length": n,
            "mean": mean,
            "std": std,
            "cv": cv,
            "trend": self._detect_trend(ts_s),
            "seasonality": self._detect_seasonality(ts_s),
            "stationarity": self._test_stationarity(ts_s),
            "outliers_pct": self._detect_outliers(ts_s),
            "missing_pct": float(df[value_col].isna().sum() / max(1, len(df)) * 100),
            "min_date": ts_s.index.min().strftime("%Y-%m-%d") if n else None,
            "max_date": ts_s.index.max().strftime("%Y-%m-%d") if n else None,
        }
        self.last_characteristics = chars
        return chars

    def _detect_trend(self, ts: pd.Series) -> str:
        if len(ts) < 10:
            return "unknown"
        x = np.arange(len(ts))
        slope, _ = np.polyfit(x, ts.values, 1)
        pct = slope / ts.mean() * 100 if ts.mean() else 0
        if pct > 1:
            return "increasing"
        if pct < -1:
            return "decreasing"
        return "stable"

    def _detect_seasonality(self, ts: pd.Series) -> str:
        if len(ts) < 14:
            return "none"
        try:
            ac7 = float(ts.autocorr(lag=7)) if not pd.isna(ts.autocorr(lag=7)) else 0.0
        except Exception:
            ac7 = 0.0
        if abs(ac7) > 0.5:
            return "weekly"
        if len(ts) > 30:
            try:
                ac30 = float(ts.autocorr(lag=30)) if not pd.isna(ts.autocorr(lag=30)) else 0.0
            except Exception:
                ac30 = 0.0
            if abs(ac30) > 0.5:
                return "monthly"
        if len(ts) > 365:
            try:
                ac365 = float(ts.autocorr(lag=365)) if not pd.isna(ts.autocorr(lag=365)) else 0.0
            except Exception:
                ac365 = 0.0
            if abs(ac365) > 0.5:
                return "yearly"
        return "none"

    def _test_stationarity(self, ts: pd.Series) -> bool:
        if len(ts) < 30:
            return True
        try:
            from statsmodels.tsa.stattools import adfuller
            result = adfuller(ts.dropna(), autolag="AIC")
            return bool(result[1] < 0.05)
        except Exception:
            return True

    def _detect_outliers(self, ts: pd.Series) -> float:
        if len(ts) < 4:
            return 0.0
        q1, q3 = ts.quantile(0.25), ts.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            return 0.0
        n = int(((ts < (q1 - 1.5 * iqr)) | (ts > (q3 + 1.5 * iqr))).sum())
        return float(n / len(ts) * 100)

    def recommend_models(
        self, data_chars: Dict[str, Any], has_external: bool = False
    ) -> List[Dict[str, Any]]:
        recs: List[Dict[str, Any]] = []
        n = data_chars.get("length", 0)
        cv = data_chars.get("cv", 0.0)
        season = data_chars.get("seasonality", "none")
        stationary = data_chars.get("stationarity", True)
        if n < 14:
            recs.append({"model": "wma", "score": 0.9, "reason": "Short series, simple methods preferred"})
            recs.append({"model": "theta", "score": 0.85, "reason": "Effective for short series"})
            recs.append({"model": "ets", "score": 0.8, "reason": "Adaptive smoothing"})
            return recs[:5]
        if cv > 0.5:
            recs.append({"model": "lightgbm", "score": 0.88, "reason": "High variance — ML captures patterns"})
            recs.append({"model": "xgboost", "score": 0.85, "reason": "Robust boosting for complex patterns"})
        elif cv < 0.2:
            recs.append({"model": "wma", "score": 0.82, "reason": "Low variance — moving average sufficient"})
            recs.append({"model": "ets", "score": 0.80, "reason": "Exponential smoothing for stable demand"})
        if season != "none":
            recs.append({"model": "prophet", "score": 0.92, "reason": f"Detected {season} seasonality"})
            recs.append({"model": "sarimax", "score": 0.85, "reason": "Captures seasonal patterns"})
            recs.append({"model": "stl", "score": 0.82, "reason": "STL decomposition"})
            recs.append({"model": "theta", "score": 0.78, "reason": "Seasonal decomposition"})
        if stationary:
            recs.append({"model": "arima", "score": 0.78, "reason": "Series is stationary"})
        if has_external:
            recs.append({"model": "prophet", "score": 0.9, "reason": "Native support for external regressors"})
            recs.append({"model": "lightgbm", "score": 0.87, "reason": "Handles multiple features well"})
            recs.append({"model": "xgboost", "score": 0.85, "reason": "Robust to feature interactions"})
        # Always include theta as a robust baseline
        recs.append({"model": "theta", "score": 0.7, "reason": "Strong general-purpose baseline"})
        recs.sort(key=lambda x: x["score"], reverse=True)
        seen, unique = set(), []
        for r in recs:
            if r["model"] in seen:
                continue
            seen.add(r["model"])
            unique.append(r)
        return unique[:5]

    # --------------------------------------------------------- validation
    def cross_validate(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        model_type: str,
        params: Optional[Dict[str, Any]] = None,
        horizon: int = 7,
    ) -> Dict[str, float]:
        """One-step hold-out cross-validation on the last `horizon` points."""
        if df.empty or value_col not in df.columns or date_col not in df.columns:
            return {"mae": None, "rmse": None, "mape": None}
        ts = df[[date_col, value_col]].copy()
        ts[date_col] = pd.to_datetime(ts[date_col], errors="coerce")
        ts[value_col] = pd.to_numeric(ts[value_col], errors="coerce")
        ts = ts.dropna().sort_values(date_col)
        ts = ts.groupby(date_col, as_index=False)[value_col].mean()
        n = len(ts)
        if n < max(horizon * 2, 10):
            return {"mae": None, "rmse": None, "mape": None, "note": "insufficient_data"}
        train = ts.iloc[:-horizon]
        test = ts.iloc[-horizon:]
        train_df = train.rename(columns={date_col: date_col, value_col: value_col})
        try:
            model = self.get_model(model_type, params)
            model.fit(train_df, date_col, value_col)
            preds = model.forecast(horizon)
            pred_values = np.array([self._safe_float(p.get("forecast", 0.0)) for p in preds])
            actuals = test[value_col].astype(float).values
            if len(pred_values) != len(actuals):
                m = min(len(pred_values), len(actuals))
                pred_values = pred_values[:m]
                actuals = actuals[:m]
            mae = float(np.mean(np.abs(pred_values - actuals)))
            rmse = float(np.sqrt(np.mean((pred_values - actuals) ** 2)))
            denom = np.where(np.abs(actuals) < 1e-9, 1e-9, np.abs(actuals))
            mape = float(np.mean(np.abs((pred_values - actuals) / denom)) * 100)
            return {"mae": mae, "rmse": rmse, "mape": mape}
        except Exception as e:
            logger.warning("CV failed for %s: %s", model_type, e)
            return {"mae": None, "rmse": None, "mape": None, "error": str(e)}

    @staticmethod
    def _safe_float(x: Any, default: float = 0.0) -> float:
        try:
            v = float(x)
            if np.isnan(v) or np.isinf(v):
                return default
            return v
        except (TypeError, ValueError):
            return default
