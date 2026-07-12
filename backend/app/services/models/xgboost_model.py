"""XGBoost forecaster with optimized incremental forecast loop.

Same architecture as LightGBM but using XGBoost. Shares the incremental
step-feature helpers from lightgbm_model.
"""
from __future__ import annotations

import logging
import warnings
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .base import BaseForecaster
from .lightgbm_model import (
    _add_calendar,
    _add_lag_rolling,
    _merge_exog,
    _prep_exog_lookup,
    _step_features,
)

try:
    from sklearn.preprocessing import StandardScaler
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False
    StandardScaler = None  # type: ignore

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

try:
    import shap
    _SHAP_AVAILABLE = True
except ImportError:
    _SHAP_AVAILABLE = False
    shap = None

_MAX_LAG = 28


class XGBoostForecaster(BaseForecaster):
    name = "XGBoost"

    def __init__(
        self,
        n_estimators: int = 200,
        learning_rate: float = 0.05,
        max_depth: int = 5,
        min_child_weight: int = 1,
        subsample: float = 0.9,
        colsample_bytree: float = 0.9,
        lags: Optional[List[int]] = None,
        roll_windows: Optional[List[int]] = None,
    ) -> None:
        super().__init__(
            n_estimators=n_estimators, learning_rate=learning_rate,
            max_depth=max_depth, min_child_weight=min_child_weight,
            subsample=subsample, colsample_bytree=colsample_bytree,
        )
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.min_child_weight = min_child_weight
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.lags = lags or [1, 2, 3, 7, 14]
        self.roll_windows = roll_windows or [7, 14, 28]
        self._shap_values: Optional[List[Dict[str, Any]]] = None
        self._shap_base_value: Optional[float] = None
        self._shap_explainer: Any = None
        self._exog_lookup: Optional[Dict[str, Dict[str, float]]] = None
        self._train_values: Optional[np.ndarray] = None
        self._scaler: Optional[Any] = None

    def _build_features(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
        include_external: bool = True,
    ) -> pd.DataFrame:
        out = df[[date_col, value_col]].copy()
        out[date_col] = pd.to_datetime(out[date_col], errors="coerce")
        out[value_col] = pd.to_numeric(out[value_col], errors="coerce")
        out = out.dropna(subset=[date_col])
        out = out.sort_values(date_col).reset_index(drop=True)
        out = _add_calendar(out, date_col)
        out = _add_lag_rolling(out, value_col, self.lags, self.roll_windows)
        if include_external:
            out = _merge_exog(out, date_col, exog_data)
        return out

    def fit(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        **kwargs: Any,
    ) -> "XGBoostForecaster":
        from xgboost import XGBRegressor

        self._date_col = date_col
        self._value_col = value_col
        self._frequency = self._normalize_frequency(kwargs.get("frequency") or self._infer_frequency(df, date_col))
        exog_data = kwargs.get("exog_data")
        self._exog_lookup = _prep_exog_lookup(exog_data)

        feat = self._build_features(df, date_col, value_col, exog_data, include_external=True)
        feat = feat.dropna(subset=[value_col])
        if len(feat) < 10:
            raise ValueError("XGBoost requires at least 10 rows after feature creation")

        self._last_date = feat[date_col].iloc[-1]
        self._train_df = feat.copy()
        self._train_values = feat[value_col].values.astype(float).copy()
        all_feature_cols = [c for c in feat.columns
                            if c not in (date_col, value_col)]
        self._feature_cols = [
            c for c in all_feature_cols
            if pd.api.types.is_numeric_dtype(feat[c])
        ]
        X = feat[self._feature_cols].astype(float)
        y = feat[value_col].astype(float).values
        valid_mask = X.notna().all(axis=1)
        X = X[valid_mask]
        y = y[valid_mask]
        feat = feat[valid_mask].reset_index(drop=True)

        # StandardScaler: fit on training features, reused during forecast
        self._scaler = StandardScaler() if _SKLEARN_AVAILABLE else None
        X_arr = X.values
        if self._scaler is not None:
            X_arr = self._scaler.fit_transform(X_arr)

        try:
            self._fitted_model = XGBRegressor(
                n_estimators=self.n_estimators,
                learning_rate=self.learning_rate,
                max_depth=self.max_depth,
                min_child_weight=self.min_child_weight,
                subsample=self.subsample,
                colsample_bytree=self.colsample_bytree,
                random_state=42,
                verbosity=0,
            )
            self._fitted_model.fit(X_arr, y)
        except Exception as e:
            raise RuntimeError(f"XGBoost fit failed: {e}")

        try:
            if _SHAP_AVAILABLE:
                self._shap_explainer = shap.TreeExplainer(self._fitted_model)
                shap_vals = self._shap_explainer.shap_values(X_arr)
                self._shap_base_value = float(self._shap_explainer.expected_value)
                self._shap_training_importance = {
                    self._feature_cols[i]: float(np.abs(shap_vals[:, i]).mean())
                    for i in range(len(self._feature_cols))
                }
            else:
                self._shap_training_importance = {}
        except Exception as e:
            logger.debug("SHAP explainer init failed: %s", e)
            self._shap_explainer = None
            self._shap_training_importance = {}
        return self

    def _iter_forecast(
        self,
        horizon: int,
        exog_data: Optional[Dict[str, pd.DataFrame]],
        include_external: bool,
        compute_shap: bool,
    ) -> List[Dict[str, Any]]:
        freq = self._frequency or "D"
        try:
            future_dates = pd.date_range(
                start=self._last_date + pd.tseries.frequencies.to_offset(freq),
                periods=horizon, freq=freq,
            )
        except Exception:
            future_dates = pd.date_range(
                start=self._last_date + pd.Timedelta(days=1), periods=horizon, freq="D",
            )

        need = max(max(self.lags or [1]), max(self.roll_windows or [1]), _MAX_LAG)
        recent_vals = (self._train_values[-need:].tolist()
                       if self._train_values is not None and len(self._train_values) >= need
                       else (self._train_values.tolist() if self._train_values is not None else []))

        from collections import deque
        recent = deque(recent_vals, maxlen=need + horizon)

        preds: List[float] = []
        shap_per_step: Optional[List[Dict[str, float]]] = None
        if compute_shap and _SHAP_AVAILABLE and self._shap_explainer is not None:
            shap_per_step = []

        for step_idx, fut_date in enumerate(future_dates):
            X_step = _step_features(
                fut_date, list(recent),
                self.lags, self.roll_windows,
                self._exog_lookup if include_external else None,
                self._feature_cols,
            ).reshape(1, -1)

            if self._scaler is not None:
                X_step = self._scaler.transform(X_step)

            try:
                p = float(self._fitted_model.predict(X_step)[0])
            except Exception as e:
                logger.warning("XGBoost step predict failed at step %d: %s", step_idx, e)
                p = float(recent[-1]) if recent else 0.0
            p = max(0.0, p)
            preds.append(p)
            recent.append(p)

            if shap_per_step is not None:
                try:
                    shap_vals = self._shap_explainer.shap_values(X_step)
                    step_shap = {self._feature_cols[i]: self._safe_float(shap_vals[0, i])
                                 for i in range(len(self._feature_cols))}
                    shap_per_step.append(step_shap)
                except Exception as e:
                    logger.debug("SHAP step failed at step %d: %s", step_idx, e)
                    shap_per_step.append({})

        self._shap_values = shap_per_step

        results = []
        for i, (d, p) in enumerate(zip(future_dates, preds)):
            entry: Dict[str, Any] = {
                "date": self._format_date(d),
                "forecast": self._safe_float(p),
                "lower_ci": self._safe_float(max(0.0, p * 0.85)),
                "upper_ci": self._safe_float(p * 1.15),
            }
            if shap_per_step is not None and i < len(shap_per_step):
                entry["shap"] = shap_per_step[i]
                if self._shap_base_value is not None:
                    entry["shap_base"] = self._shap_base_value
            results.append(entry)
        return results

    def forecast(
        self,
        horizon: int,
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        if self._fitted_model is None:
            raise ValueError("Model not fitted")
        compute_shap = kwargs.get("compute_shap", False)
        return self._iter_forecast(horizon, exog_data, include_external=True, compute_shap=compute_shap)

    def get_baseline(
        self,
        horizon: int,
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        if self._fitted_model is None:
            raise ValueError("Model not fitted")
        return self._iter_forecast(horizon, exog_data, include_external=False, compute_shap=False)

    def get_feature_importance(self) -> Dict[str, float]:
        if self._fitted_model is None:
            return {}
        try:
            imp = self._fitted_model.feature_importances_
            return {n: self._safe_float(v) for n, v in zip(self._feature_cols, imp)}
        except Exception:
            return {}

    def get_shap_importance(self) -> Dict[str, Any]:
        shap_values = getattr(self, '_shap_values', None)
        shap_base = getattr(self, '_shap_base_value', None)
        shap_train = getattr(self, '_shap_training_importance', {})
        return {
            "training_importance": shap_train,
            "per_step": shap_values,
            "base_value": shap_base,
        }
