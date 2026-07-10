"""LightGBM forecaster.

Builds lag / rolling / calendar features from the value column (NOT the
date column), then trains a regression model. Supports external regressors
(promotions, media, holidays, events, weather, competitor, economic).
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

try:
    import shap
    _SHAP_AVAILABLE = True
except ImportError:
    _SHAP_AVAILABLE = False
    shap = None


def _add_calendar(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    d = pd.to_datetime(df[date_col], errors="coerce")
    df["dayofweek"] = d.dt.dayofweek.astype("Int64")
    df["dayofmonth"] = d.dt.day.astype("Int64")
    df["month"] = d.dt.month.astype("Int64")
    df["quarter"] = d.dt.quarter.astype("Int64")
    df["year"] = d.dt.year.astype("Int64")
    df["weekofyear"] = d.dt.isocalendar().week.astype("Int64")
    df["is_weekend"] = d.dt.dayofweek.isin([5, 6]).astype("Int64")
    df["is_month_start"] = d.dt.is_month_start.astype("Int64")
    df["is_month_end"] = d.dt.is_month_end.astype("Int64")
    return df


def _add_lag_rolling(
    df: pd.DataFrame, value_col: str, lags: List[int], windows: List[int]
) -> pd.DataFrame:
    """Lag and rolling features computed on the VALUE column."""
    for lag in lags:
        df[f"lag_{lag}"] = df[value_col].shift(lag)
    for w in windows:
        roll = df[value_col].rolling(window=w, min_periods=1)
        df[f"rolling_mean_{w}"] = roll.mean()
        df[f"rolling_std_{w}"] = roll.std().fillna(0.0)
        df[f"rolling_min_{w}"] = roll.min()
        df[f"rolling_max_{w}"] = roll.max()
    return df


def _merge_exog(
    df: pd.DataFrame, date_col: str, exog_data: Optional[Dict[str, pd.DataFrame]]
) -> pd.DataFrame:
    """Merge external regressors on date.  Only NUMERIC columns are kept
    so the result is safe to feed into a regression model."""
    if not exog_data:
        return df
    out = df.copy()
    out[date_col] = pd.to_datetime(out[date_col], errors="coerce")
    # Exogenous data sources: only numeric columns are kept
    source_specs = [
        ("promotions", ["discount"], "sum"),
        ("media_plan", ["media_spend", "reach", "impressions"], "sum"),
        ("holidays", ["holiday_impact"], "max"),
        ("events", ["event_impact"], "max"),
        ("weather", ["temperature", "humidity", "rainfall", "snowfall"], "mean"),
        ("competitor", ["competitor_price", "market_share", "promotion_flag"], "mean"),
        ("economic", None, "mean"),
    ]
    for key, value_cols, agg_func in source_specs:
        ex = exog_data.get(key)
        if ex is None or ex.empty or "date" not in ex.columns:
            continue
        sub = ex.copy()
        sub["date"] = pd.to_datetime(sub["date"], errors="coerce")
        sub = sub.dropna(subset=["date"])
        if sub.empty:
            continue
        # Determine which columns to merge (numeric only)
        if key == "economic":
            cols_to_use = [c for c in sub.columns
                           if c != "date" and pd.api.types.is_numeric_dtype(sub[c])]
        else:
            cols_to_use = [c for c in (value_cols or [])
                           if c in sub.columns and pd.api.types.is_numeric_dtype(sub[c])]
        if not cols_to_use:
            continue
        # Aggregate duplicate dates — numeric only, so single agg function
        sub_agg = sub.groupby("date")[cols_to_use].agg(agg_func).reset_index()
        sub_agg = sub_agg.rename(columns={"date": date_col})
        out = out.merge(sub_agg, on=date_col, how="left")
    # Fill NaNs introduced by merges
    numeric_cols = [c for c in out.columns
                    if c != date_col and pd.api.types.is_numeric_dtype(out[c])]
    for c in numeric_cols:
        out[c] = out[c].fillna(0.0)
    return out


class LightGBMForecaster(BaseForecaster):
    name = "LightGBM"

    def __init__(
        self,
        n_estimators: int = 200,
        learning_rate: float = 0.05,
        max_depth: int = 5,
        num_leaves: int = 31,
        min_child_samples: int = 20,
        lags: Optional[List[int]] = None,
        roll_windows: Optional[List[int]] = None,
    ) -> None:
        super().__init__(
            n_estimators=n_estimators, learning_rate=learning_rate,
            max_depth=max_depth, num_leaves=num_leaves,
            min_child_samples=min_child_samples,
        )
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.num_leaves = num_leaves
        self.min_child_samples = min_child_samples
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

    def _determine_feature_cols(self, df_feat: pd.DataFrame, date_col: str, value_col: str) -> List[str]:
        return [c for c in df_feat.columns if c not in (date_col, value_col)]

    def fit(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        **kwargs: Any,
    ) -> "LightGBMForecaster":
        from lightgbm import LGBMRegressor

        self._date_col = date_col
        self._value_col = value_col
        self._frequency = self._infer_frequency(df, date_col)
        exog_data = kwargs.get("exog_data")
        feat = self._build_features(df, date_col, value_col, exog_data, include_external=True)
        # Drop rows with NaN in target (first max(lag, window) rows after lag/rolling)
        feat = feat.dropna(subset=[value_col])
        if len(feat) < 10:
            raise ValueError("LightGBM requires at least 10 rows after feature creation")

        self._last_date = feat[date_col].iloc[-1]
        self._train_df = feat.copy()
        all_feature_cols = self._determine_feature_cols(feat, date_col, value_col)
        # Filter to numeric columns only (defensive — _merge_exog already
        # restricts to numeric, but external callers may add other columns)
        self._feature_cols = [
            c for c in all_feature_cols
            if pd.api.types.is_numeric_dtype(feat[c])
        ]
        # Fill any remaining NaN with 0
        X = feat[self._feature_cols].astype(float).fillna(0.0)
        y = feat[value_col].astype(float).values

        try:
            self._fitted_model = LGBMRegressor(
                n_estimators=self.n_estimators,
                learning_rate=self.learning_rate,
                max_depth=self.max_depth,
                num_leaves=self.num_leaves,
                min_child_samples=self.min_child_samples,
                random_state=42,
                verbose=-1,
            )
            self._fitted_model.fit(X.values, y)
        except Exception as e:
            raise RuntimeError(f"LightGBM fit failed: {e}")

        try:
            if _SHAP_AVAILABLE:
                self._shap_explainer = shap.TreeExplainer(self._fitted_model)
                shap_vals = self._shap_explainer.shap_values(X.values)
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

    def _make_future_frame(self, horizon: int, exog_data: Optional[Dict[str, pd.DataFrame]], include_external: bool) -> pd.DataFrame:
        # Build a frame that contains history + future dates for feature continuity
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
            future_idx = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon, freq="D")
        hist = self._train_df[[self._date_col, self._value_col]].copy()
        fut = pd.DataFrame({self._date_col: future_idx, self._value_col: [np.nan] * horizon})
        full = pd.concat([hist, fut], ignore_index=True)
        full = full.sort_values(self._date_col).reset_index(drop=True)
        full = self._build_features(full, self._date_col, self._value_col,
                                    exog_data=exog_data, include_external=include_external)
        # Take only the future rows
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

        compute_shap = kwargs.get("compute_shap", False)

        # Iterative 1-step-ahead prediction to avoid cascading NaN in lag features.
        # Each step's prediction is injected as the value for the next step,
        # so lag/rolling features always reference real (predicted) values.
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

        preds = []
        shap_per_step: Optional[List[Dict[str, float]]] = None
        if compute_shap and _SHAP_AVAILABLE and self._shap_explainer is not None:
            shap_per_step = []

        # Start with the training history so lag features can be built
        roll_df = self._train_df[[self._date_col, self._value_col]].copy()

        for step_idx, fut_date in enumerate(future_dates):
            step_df = pd.DataFrame({self._date_col: [fut_date], self._value_col: [np.nan]})
            full = pd.concat([roll_df, step_df], ignore_index=True)
            full = full.sort_values(self._date_col).reset_index(drop=True)
            full = self._build_features(full, self._date_col, self._value_col,
                                        exog_data=exog_data, include_external=True)
            # Feature row for this future date
            row = full[full[self._date_col] == fut_date]
            if row.empty:
                preds.append(float(roll_df[self._value_col].iloc[-1]))
                continue
            for c in self._feature_cols:
                if c not in row.columns:
                    row[c] = 0.0
            X_step = row[self._feature_cols].astype(float).fillna(0.0).values
            try:
                p = float(self._fitted_model.predict(X_step)[0])
            except Exception as e:
                logger.warning("LightGBM step predict failed at step %d: %s", step_idx, e)
                p = float(roll_df[self._value_col].iloc[-1])
            p = max(0.0, p)
            preds.append(p)

            if shap_per_step is not None:
                try:
                    shap_vals = self._shap_explainer.shap_values(X_step)
                    step_shap = {self._feature_cols[i]: self._safe_float(shap_vals[0, i])
                                 for i in range(len(self._feature_cols))}
                    shap_per_step.append(step_shap)
                except Exception as e:
                    logger.debug("SHAP step failed at step %d: %s", step_idx, e)
                    shap_per_step.append({})

            # Append prediction to rolling history so next step's lags are correct
            roll_df = pd.concat([
                roll_df,
                pd.DataFrame({self._date_col: [fut_date], self._value_col: [p]})
            ], ignore_index=True)

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

    def get_baseline(
        self,
        horizon: int,
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        if self._fitted_model is None:
            raise ValueError("Model not fitted")
        # Use iterative prediction (same approach as forecast) but without external regressors
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
        preds = []
        roll_df = self._train_df[[self._date_col, self._value_col]].copy()
        for fut_date in future_dates:
            step_df = pd.DataFrame({self._date_col: [fut_date], self._value_col: [np.nan]})
            full = pd.concat([roll_df, step_df], ignore_index=True)
            full = full.sort_values(self._date_col).reset_index(drop=True)
            full = self._build_features(full, self._date_col, self._value_col,
                                        exog_data=None, include_external=False)
            row = full[full[self._date_col] == fut_date]
            if row.empty:
                preds.append(float(roll_df[self._value_col].iloc[-1]))
                continue
            for c in self._feature_cols:
                if c not in row.columns:
                    row[c] = 0.0
            X_step = row[self._feature_cols].astype(float).fillna(0.0).values
            try:
                p = float(self._fitted_model.predict(X_step)[0])
            except Exception:
                p = float(roll_df[self._value_col].iloc[-1])
            p = max(0.0, p)
            preds.append(p)
            roll_df = pd.concat([
                roll_df,
                pd.DataFrame({self._date_col: [fut_date], self._value_col: [p]})
            ], ignore_index=True)
        return [
            {
                "date": self._format_date(d),
                "forecast": self._safe_float(p),
                "lower_ci": self._safe_float(max(0.0, p * 0.85)),
                "upper_ci": self._safe_float(p * 1.15),
            }
            for d, p in zip(future_dates, preds)
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
