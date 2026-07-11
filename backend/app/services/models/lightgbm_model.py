"""LightGBM forecaster with optimized incremental forecast loop.

Builds lag / rolling / calendar features from the value column, then trains
a regression model. Supports external regressors.
"""
from __future__ import annotations

import logging
import warnings
from collections import deque
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

_MAX_LAG = 28  # maximum lag window we need for rolling computations


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
    for lag in lags:
        df[f"lag_{lag}"] = df[value_col].shift(lag)
    for w in windows:
        roll = df[value_col].rolling(window=w, min_periods=1)
        df[f"rolling_mean_{w}"] = roll.mean()
        df[f"rolling_std_{w}"] = roll.std().fillna(0.0)
        df[f"rolling_min_{w}"] = roll.min()
        df[f"rolling_max_{w}"] = roll.max()
    return df


def _prep_exog_lookup(
    exog_data: Optional[Dict[str, pd.DataFrame]],
) -> Optional[Dict[str, Dict[str, float]]]:
    """Pre-aggregate exog sources into {date_str: {col: value}} lookups,
    avoiding repeated DataFrame merges during the forecast loop."""
    if not exog_data:
        return None
    lookup: Dict[str, Dict[str, float]] = {}
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
        if key == "economic":
            cols_to_use = [c for c in sub.columns
                           if c != "date" and pd.api.types.is_numeric_dtype(sub[c])]
        else:
            cols_to_use = [c for c in (value_cols or [])
                           if c in sub.columns and pd.api.types.is_numeric_dtype(sub[c])]
        if not cols_to_use:
            continue
        sub_agg = sub.groupby("date")[cols_to_use].agg(agg_func).reset_index()
        for _, row in sub_agg.iterrows():
            d = str(pd.Timestamp(row["date"]).strftime("%Y-%m-%d"))
            if d not in lookup:
                lookup[d] = {}
            for col in cols_to_use:
                v = row[col]
                lookup[d][f"{key}_{col}"] = float(v) if pd.notna(v) else 0.0
    return lookup if lookup else None


def _step_features(
    date_val: pd.Timestamp,
    recent_vals: List[float],
    lags: List[int],
    roll_windows: List[int],
    exog_lookup: Optional[Dict[str, Dict[str, float]]] = None,
    feature_cols: Optional[List[str]] = None,
) -> np.ndarray:
    """Compute a single feature row for one forecast step.

    Returns a 1D numpy array aligned to *feature_cols* (or in natural order
    if feature_cols is None).
    """
    d = pd.Timestamp(date_val)
    feats: Dict[str, float] = {
        "dayofweek": float(d.dayofweek),
        "dayofmonth": float(d.day),
        "month": float(d.month),
        "quarter": float(d.quarter),
        "year": float(d.year),
        "is_weekend": 1.0 if d.dayofweek in (5, 6) else 0.0,
        "is_month_start": 1.0 if d.is_month_start else 0.0,
        "is_month_end": 1.0 if d.is_month_end else 0.0,
    }
    try:
        feats["weekofyear"] = float(d.isocalendar().week)
    except Exception:
        feats["weekofyear"] = 0.0

    vals = np.array(recent_vals, dtype=float)
    for lag in lags:
        feats[f"lag_{lag}"] = float(vals[-lag]) if len(vals) >= lag else 0.0
    for w in roll_windows:
        if len(vals) >= w:
            window = vals[-w:]
            feats[f"rolling_mean_{w}"] = float(window.mean())
            feats[f"rolling_std_{w}"] = float(window.std()) if len(window) > 1 else 0.0
            feats[f"rolling_min_{w}"] = float(window.min())
            feats[f"rolling_max_{w}"] = float(window.max())
        else:
            feats[f"rolling_mean_{w}"] = float(vals.mean()) if len(vals) > 0 else 0.0
            feats[f"rolling_std_{w}"] = float(vals.std()) if len(vals) > 1 else 0.0
            feats[f"rolling_min_{w}"] = float(vals.min()) if len(vals) > 0 else 0.0
            feats[f"rolling_max_{w}"] = float(vals.max()) if len(vals) > 0 else 0.0

    # Exog lookup
    if exog_lookup:
        d_str = d.strftime("%Y-%m-%d")
        ex_row = exog_lookup.get(d_str)
        if ex_row:
            feats.update(ex_row)

    # Build array in feature_cols order if given
    if feature_cols:
        return np.array([feats.get(c, 0.0) for c in feature_cols], dtype=float)
    return np.array(list(feats.values()), dtype=float)


def _merge_exog(
    df: pd.DataFrame, date_col: str, exog_data: Optional[Dict[str, pd.DataFrame]]
) -> pd.DataFrame:
    """Merge external regressors on date.  Only NUMERIC columns are kept
    so the result is safe to feed into a regression model."""
    if not exog_data:
        return df

    exog_lookup = _prep_exog_lookup(exog_data)
    if not exog_lookup:
        return df

    df_out = df.copy()
    d_col = pd.to_datetime(df_out[date_col], errors="coerce")
    # Use the lookup instead of per-source merges
    all_exog_cols: set = set()
    for row_idx in range(len(df_out)):
        d_str = str(d_col.iloc[row_idx].strftime("%Y-%m-%d")) if pd.notna(d_col.iloc[row_idx]) else None
        if d_str and d_str in exog_lookup:
            for col, val in exog_lookup[d_str].items():
                df_out.at[row_idx, col] = val
                all_exog_cols.add(col)
    for c in all_exog_cols:
        df_out[c] = pd.to_numeric(df_out[c], errors="coerce").fillna(0.0)
    return df_out


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
        # Incremental forecast state
        self._exog_lookup: Optional[Dict[str, Dict[str, float]]] = None
        self._train_values: Optional[np.ndarray] = None

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
        self._frequency = kwargs.get("frequency") or self._infer_frequency(df, date_col)
        exog_data = kwargs.get("exog_data")
        self._exog_lookup = _prep_exog_lookup(exog_data)

        feat = self._build_features(df, date_col, value_col, exog_data, include_external=True)
        feat = feat.dropna(subset=[value_col])
        if len(feat) < 10:
            raise ValueError("LightGBM requires at least 10 rows after feature creation")

        self._last_date = feat[date_col].iloc[-1]
        self._train_df = feat.copy()
        self._train_values = feat[value_col].values.astype(float).copy()
        all_feature_cols = self._determine_feature_cols(feat, date_col, value_col)
        self._feature_cols = [
            c for c in all_feature_cols
            if pd.api.types.is_numeric_dtype(feat[c])
        ]
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

    def _iter_forecast(
        self,
        horizon: int,
        exog_data: Optional[Dict[str, pd.DataFrame]],
        include_external: bool,
        compute_shap: bool,
    ) -> List[Dict[str, Any]]:
        """Iterative 1-step-ahead forecast using array-based features.

        Avoids DataFrame concat + sort + full feature rebuild at every step.
        """
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

        # Keep a deque of recent values so lag/rolling features can be
        # computed incrementally without copying/growing a DataFrame.
        need = max(max(self.lags or [1]), max(self.roll_windows or [1]), _MAX_LAG)
        recent = deque(self._train_values[-need:].tolist() if self._train_values is not None and len(self._train_values) >= need
                       else (self._train_values.tolist() if self._train_values is not None else []),
                       maxlen=need + horizon)

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

            try:
                p = float(self._fitted_model.predict(X_step)[0])
            except Exception as e:
                logger.warning("LightGBM step predict failed at step %d: %s", step_idx, e)
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
