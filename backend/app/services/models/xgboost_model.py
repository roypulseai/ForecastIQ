"""XGBoost forecaster.

Same architecture as LightGBM but using XGBoost. Lag/rolling features are
computed on the VALUE column (not date), which was the original bug.
"""
from __future__ import annotations

import logging
import warnings
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .base import BaseForecaster
from .lightgbm_model import _add_calendar, _add_lag_rolling, _merge_exog

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

try:
    import shap
    _SHAP_AVAILABLE = True
except ImportError:
    _SHAP_AVAILABLE = False
    shap = None


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
        exog_data = kwargs.get("exog_data")
        feat = self._build_features(df, date_col, value_col, exog_data, include_external=True)
        feat = feat.dropna(subset=[value_col])
        if len(feat) < 10:
            raise ValueError("XGBoost requires at least 10 rows after feature creation")

        self._last_date = feat[date_col].iloc[-1]
        self._train_df = feat.copy()
        all_feature_cols = [c for c in feat.columns
                            if c not in (date_col, value_col)]
        # Filter to numeric columns only
        self._feature_cols = [
            c for c in all_feature_cols
            if pd.api.types.is_numeric_dtype(feat[c])
        ]
        X = feat[self._feature_cols].astype(float).fillna(0.0).values
        y = feat[value_col].astype(float).values

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
            self._fitted_model.fit(X, y)
        except Exception as e:
            raise RuntimeError(f"XGBoost fit failed: {e}")

        try:
            if _SHAP_AVAILABLE:
                self._shap_explainer = shap.TreeExplainer(self._fitted_model)
                shap_vals = self._shap_explainer.shap_values(X)
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

    def _make_future_frame(
        self, horizon: int, exog_data: Optional[Dict[str, pd.DataFrame]],
        include_external: bool,
    ) -> pd.DataFrame:
        if self._train_df is None:
            raise ValueError("Model not fitted")
        last_date = self._last_date
        freq = self._frequency or "D"
        try:
            future_idx = pd.date_range(
                start=last_date + pd.tseries.frequencies.to_offset(freq),
                periods=horizon, freq=freq,
            )
        except Exception:
            future_idx = pd.date_range(start=last_date + pd.Timedelta(days=1),
                                       periods=horizon, freq="D")
        hist = self._train_df[[self._date_col, self._value_col]].copy()
        fut = pd.DataFrame({self._date_col: future_idx,
                            self._value_col: [np.nan] * horizon})
        full = pd.concat([hist, fut], ignore_index=True)
        full = full.sort_values(self._date_col).reset_index(drop=True)
        full = self._build_features(full, self._date_col, self._value_col,
                                    exog_data=exog_data,
                                    include_external=include_external)
        full = full[full[self._date_col] > last_date].reset_index(drop=True)
        return full

    def forecast(
        self,
        horizon: int,
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        if self._fitted_model is None:
            raise ValueError("Model not fitted")
        fut = self._make_future_frame(horizon, exog_data, include_external=True)
        for c in self._feature_cols:
            if c not in fut.columns:
                fut[c] = 0.0
        Xf = fut[self._feature_cols].astype(float).fillna(0.0).values
        try:
            preds = self._fitted_model.predict(Xf)
        except Exception as e:
            logger.warning("XGBoost predict failed: %s", e)
            preds = np.array([float(self._train_df[self._value_col].iloc[-1])] * horizon)

        shap_per_step: Optional[List[Dict[str, float]]] = None
        if _SHAP_AVAILABLE and self._shap_explainer is not None:
            try:
                shap_vals = self._shap_explainer.shap_values(Xf)
                shap_per_step = [
                    {self._feature_cols[i]: self._safe_float(shap_vals[j, i])
                     for i in range(len(self._feature_cols))}
                    for j in range(len(preds))
                ]
            except Exception as e:
                logger.debug("SHAP forecast computation failed: %s", e)

        self._shap_values = shap_per_step

        results = []
        for i, (d, p) in enumerate(zip(fut[self._date_col], preds)):
            entry: Dict[str, Any] = {
                "date": self._format_date(d),
                "forecast": self._safe_float(max(0.0, p)),
                "lower_ci": self._safe_float(max(0.0, p * 0.85)),
                "upper_ci": self._safe_float(p * 1.15),
            }
            if shap_per_step is not None:
                entry["shap"] = shap_per_step[i]
                if self._shap_base_value is not None:
                    entry["shap_base"] = self._shap_base_value
            results.append(entry)
        return results

    def get_baseline(
        self,
        horizon: int,
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        if self._fitted_model is None:
            raise ValueError("Model not fitted")
        fut = self._make_future_frame(horizon, exog_data=None, include_external=False)
        for c in self._feature_cols:
            if c not in fut.columns:
                fut[c] = 0.0
        Xf = fut[self._feature_cols].astype(float).fillna(0.0).values
        try:
            preds = self._fitted_model.predict(Xf)
        except Exception as e:
            logger.warning("XGBoost baseline predict failed: %s", e)
            preds = np.array([float(self._train_df[self._value_col].iloc[-1])] * horizon)
        return [
            {
                "date": self._format_date(d),
                "forecast": self._safe_float(max(0.0, p)),
                "lower_ci": self._safe_float(max(0.0, p * 0.85)),
                "upper_ci": self._safe_float(p * 1.15),
            }
            for d, p in zip(fut[self._date_col], preds)
        ]

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
