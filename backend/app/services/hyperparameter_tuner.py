"""Hyperparameter tuning with time-series cross-validation for all models."""
from __future__ import annotations

import itertools
import logging
import random
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .model_selector import ModelSelector

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Parameter search spaces per model type
# Each entry is a dict of param_name -> list of candidate values.
# ---------------------------------------------------------------------------

SEARCH_SPACES: Dict[str, Dict[str, List[Any]]] = {
    "arima": {
        "p": [0, 1, 2, 3, 4, 5, 6],
        "d": [0, 1],
        "q": [0, 1, 2, 3, 4, 5, 6],
    },
    "sarimax": {
        "p": [1, 2, 3, 4],
        "d": [0, 1],
        "q": [1, 2, 3, 4],
        "seasonal_p": [0, 1, 2],
        "seasonal_d": [0, 1],
        "seasonal_q": [0, 1, 2],
        "seasonal_period": [7, 12, 30, 52],
    },
    "prophet": {
        "seasonality_mode": ["additive", "multiplicative"],
        "changepoint_prior_scale": [0.001, 0.005, 0.01, 0.05, 0.1, 0.2, 0.5],
        "seasonality_prior_scale": [0.01, 0.1, 0.5, 1.0, 5.0, 10.0],
        "holidays_prior_scale": [0.01, 0.1, 0.5, 1.0, 5.0, 10.0],
        "weekly_seasonality": [True, False],
        "yearly_seasonality": [True, False],
    },
    "lightgbm": {
        "n_estimators": [100, 200, 300, 500, 800],
        "learning_rate": [0.005, 0.01, 0.02, 0.05, 0.1],
        "max_depth": [3, 5, 7, 9, -1],
        "num_leaves": [15, 31, 63, 127],
        "min_child_samples": [5, 10, 20, 50, 100],
        "subsample": [0.7, 0.8, 0.9, 1.0],
        "colsample_bytree": [0.7, 0.8, 0.9, 1.0],
        "reg_alpha": [0.0, 0.001, 0.01, 0.1],
        "reg_lambda": [0.0, 0.001, 0.01, 0.1],
    },
    "xgboost": {
        "n_estimators": [100, 200, 300, 500, 800],
        "learning_rate": [0.005, 0.01, 0.02, 0.05, 0.1],
        "max_depth": [3, 5, 7, 9],
        "min_child_weight": [1, 3, 5, 7],
        "subsample": [0.6, 0.7, 0.8, 0.9, 1.0],
        "colsample_bytree": [0.6, 0.7, 0.8, 0.9, 1.0],
        "gamma": [0.0, 0.1, 0.2, 0.5],
        "reg_alpha": [0.0, 0.001, 0.01, 0.1],
        "reg_lambda": [0.0, 0.001, 0.01, 0.1],
    },
    "wma": {
        "window": [4, 8, 12, 20, 30, 52],
        "min_periods": [1, 2, 4, 8],
    },
    "ets": {
        "trend": ["add", "mul", None],
        "seasonal": ["add", "mul", None],
        "damped_trend": [True, False],
        "seasonal_periods": [7, 12, 30, 52],
    },
    "theta": {
        "period": [7, 12, 30, 52],
        "deseasonalize": [True, False],
    },
    "stl": {
        "period": [7, 12, 30, 52],
        "robust": [True, False],
        "seasonal_degree": [0, 1],
        "trend_degree": [0, 1],
    },
}


def detect_frequency(df: pd.DataFrame, date_col: str) -> Optional[int]:
    """Auto-detect the dominant seasonal period in the time series.

    Returns the likely seasonal period (7=daily→weekly, 12=monthly,
    52=weekly→yearly, etc.) or None if detection fails.
    """
    try:
        ts = df[[date_col]].copy()
        ts[date_col] = pd.to_datetime(ts[date_col], errors="coerce")
        ts = ts.dropna().sort_values(date_col).drop_duplicates()
        if len(ts) < 14:
            return None
        # Infer frequency from the median gap between consecutive dates
        deltas = ts[date_col].diff().dropna().dt.days
        if deltas.empty:
            return None
        median_gap = int(deltas.median())
        if median_gap <= 1:
            # Daily data: check for weekly pattern
            return 7
        elif median_gap <= 7:
            # Weekly data
            return 52  # yearly seasonality
        elif median_gap <= 31:
            # Monthly data
            return 12
        return None
    except Exception as e:
        logger.warning("Frequency detection failed: %s", e)
        return None



def _to_model_params(model_type: str, flat_params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrap flat param names into the nested structure expected by ModelSelector."""
    mapping: Dict[str, Any] = {}
    if model_type == "arima":
        mapping["arima"] = flat_params
    elif model_type == "sarimax":
        mapping["sarimax"] = flat_params
    elif model_type == "prophet":
        mapping["prophet"] = flat_params
    elif model_type == "lightgbm":
        mapping["lightgbm"] = flat_params
    elif model_type == "xgboost":
        mapping["xgboost"] = flat_params
    elif model_type == "wma":
        mapping["wma"] = flat_params
    elif model_type == "ets":
        mapping["ets"] = flat_params
    elif model_type == "theta":
        mapping["theta"] = flat_params
    elif model_type == "stl":
        mapping["stl"] = flat_params
    return mapping


# ---------------------------------------------------------------------------
# Time-series cross-validation (expanding window)
# ---------------------------------------------------------------------------

def time_series_cv_folds(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    n_folds: int = 5,
    min_train_size: int = 30,
    gap: int = 0,
) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
    """Generate expanding-window CV folds.

    Each fold uses an increasing training window and a fixed-size test window
    immediately after it.  Returns list of (train_df, test_df) tuples.
    """
    ts = df[[date_col, value_col]].copy()
    ts[date_col] = pd.to_datetime(ts[date_col], errors="coerce")
    ts[value_col] = pd.to_numeric(ts[value_col], errors="coerce")
    ts = ts.dropna().sort_values(date_col).reset_index(drop=True)
    n = len(ts)
    if n < min_train_size + n_folds:
        return []

    test_size = max(1, (n - min_train_size) // (n_folds + 1))
    test_size = min(test_size, max(1, n // (n_folds + 2)))

    folds: List[Tuple[pd.DataFrame, pd.DataFrame]] = []
    for i in range(1, n_folds + 1):
        train_end = min_train_size + i * test_size
        test_start = train_end + gap
        test_end = test_start + test_size
        if test_end > n:
            break
        train = ts.iloc[:train_end].reset_index(drop=True)
        test = ts.iloc[test_start:test_end].reset_index(drop=True)
        folds.append((train, test))
    return folds


def _compute_metrics(
    actuals: np.ndarray, predictions: np.ndarray,
) -> Dict[str, float]:
    m = min(len(predictions), len(actuals))
    if m == 0:
        return {"mae": None, "rmse": None, "mape": None}
    preds = predictions[:m]
    acts = actuals[:m]
    diff = preds - acts
    mae = float(np.mean(np.abs(diff)))
    rmse = float(np.sqrt(np.mean(diff ** 2)))
    denom = np.where(np.abs(acts) < 1e-9, 1e-9, np.abs(acts))
    mape = float(np.mean(np.abs(diff / denom)) * 100)
    return {"mae": mae, "rmse": rmse, "mape": mape}


# ---------------------------------------------------------------------------
# Tuning orchestrator
# ---------------------------------------------------------------------------

def _adaptive_search_round(
    selector: ModelSelector,
    model_type: str,
    space: Dict[str, List[Any]],
    folds: List[Tuple[pd.DataFrame, pd.DataFrame]],
    exog_data: Optional[Dict[str, pd.DataFrame]] = None,
    frequency: str = "D",
) -> Tuple[Dict[str, Any], List[Dict[str, float]], float]:
    """Single round of random search: sample candidates, evaluate on folds,
    return the best params, fold scores, and mean MAE."""
    keys = list(space.keys())
    all_combos = list(itertools.product(*space.values()))
    n_iter = min(40, len(all_combos))
    candidates = all_combos if len(all_combos) <= n_iter else random.sample(all_combos, n_iter)

    best_mae = float("inf")
    best_params: Dict[str, Any] = {}
    best_fold_scores: List[Dict[str, float]] = []

    for combo in candidates:
        candidate_params = dict(zip(keys, combo))
        fold_scores: List[Dict[str, float]] = []
        for train_df, test_df in folds:
            try:
                model = selector.get_model(model_type, _to_model_params(model_type, candidate_params))
                model.fit(train_df, date_col, value_col, exog_data=exog_data, frequency=frequency)
                preds = model.forecast(len(test_df), exog_data=exog_data)
                pred_values = np.array([_safe_float(p.get("forecast", 0.0)) for p in preds])
                actual_values = test_df[value_col].astype(float).values
                metrics = _compute_metrics(actual_values, pred_values)
                if metrics["mae"] is not None:
                    fold_scores.append(metrics)
            except Exception as e:
                logger.debug("Params %s failed on fold: %s", candidate_params, e)
        if len(fold_scores) < 2:
            continue
        mean_mae = float(np.mean([s["mae"] for s in fold_scores if s["mae"] is not None]))
        if mean_mae < best_mae:
            best_mae = mean_mae
            best_params = candidate_params
            best_fold_scores = fold_scores

    return best_params, best_fold_scores, best_mae


def tune_model(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    model_type: str,
    n_iter: int = 20,
    n_folds: int = 5,
    min_train_size: int = 30,
    random_seed: int = 42,
    exog_data: Optional[Dict[str, pd.DataFrame]] = None,
    frequency: str = "D",
) -> Dict[str, Any]:
    """Run two-round adaptive search with time-series CV for a single model type.

    Round 1 explores the full parameter space broadly.
    Round 2 narrows the search around the best region found in round 1,
    giving a more fine-grained search without exploding the candidate count.

    Returns
    -------
    dict with keys:
        best_params : Dict[str, Any]  — flat parameter dict (not nested)
        cv_scores   : Dict[str, float] — mean MAE / RMSE / MAPE across folds
        fold_scores : List[Dict[str, float]] — per-fold metrics
        tuned       : bool  — whether any tuning was actually performed
    """
    space = SEARCH_SPACES.get(model_type)
    if not space:
        logger.info("No search space defined for %s — using defaults", model_type)
        return {"best_params": {}, "cv_scores": {}, "fold_scores": [], "tuned": False}

    selector = ModelSelector()

    folds = time_series_cv_folds(df, date_col, value_col, n_folds, min_train_size)
    if len(folds) < 2:
        logger.warning("Not enough data for CV tuning (%d folds) — using defaults", len(folds))
        return {"best_params": {}, "cv_scores": {}, "fold_scores": [], "tuned": False}

    # ---- Round 1: broad exploration ----
    random.seed(random_seed)
    best_params, best_fold_scores, best_mae = _adaptive_search_round(
        selector, model_type, space, folds, exog_data=exog_data, frequency=frequency,
    )

    if not best_fold_scores or len(best_fold_scores) < 2:
        logger.warning("Initial tuning round for %s found no valid params — using defaults", model_type)
        return {"best_params": {}, "cv_scores": {}, "fold_scores": [], "tuned": False}

    # ---- Round 2: narrow around best params ----
    # For each numeric parameter, create a tighter grid around the best value.
    narrowed_space: Dict[str, List[Any]] = {}
    for key in space:
        vals = space[key]
        if all(isinstance(v, (int, float)) for v in vals if v is not None):
            bv = best_params.get(key)
            if bv is not None and len(vals) >= 3:
                idx = list(vals).index(bv) if bv in vals else -1
                if idx >= 0:
                    lo = max(0, idx - 1)
                    hi = min(len(vals), idx + 2)
                    narrowed = vals[lo:hi]
                    if len(narrowed) >= 2 and narrowed != vals:
                        narrowed_space[key] = narrowed
                        continue
        # Fallback: keep original space for this param
        narrowed_space[key] = list(vals)

    if any(len(v) < len(space.get(k, [])) for k, v in narrowed_space.items() if k in space):
        ref_params, ref_fold_scores, ref_mae = _adaptive_search_round(
            selector, model_type, narrowed_space, folds, exog_data=exog_data, frequency=frequency,
        )
        if ref_fold_scores and ref_mae < best_mae:
            best_params = ref_params
            best_fold_scores = ref_fold_scores
            best_mae = ref_mae

    mean_mae = float(np.mean([s["mae"] for s in best_fold_scores if s["mae"] is not None]))
    mean_rmse = float(np.mean([s["rmse"] for s in best_fold_scores if s["rmse"] is not None]))
    mean_mape = float(np.mean([s["mape"] for s in best_fold_scores if s["mape"] is not None]))

    logger.info(
        "Tuned %s: best params=%s  CV MAE=%.4f  RMSE=%.4f  MAPE=%.2f%%  (folds=%d)",
        model_type, best_params, mean_mae, mean_rmse, mean_mape, len(best_fold_scores),
    )

    return {
        "best_params": best_params,
        "cv_scores": {"mae": mean_mae, "rmse": mean_rmse, "mape": mean_mape},
        "fold_scores": best_fold_scores,
        "tuned": True,
    }


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
        if np.isnan(v) or np.isinf(v):
            return default
        return v
    except (TypeError, ValueError):
        return default
