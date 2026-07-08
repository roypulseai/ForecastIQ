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
        "p": [0, 1, 2, 3, 5],
        "d": [0, 1],
        "q": [0, 1, 2, 3, 5],
    },
    "sarimax": {
        "p": [1, 2, 3],
        "d": [0, 1],
        "q": [1, 2, 3],
        "seasonal_p": [0, 1],
        "seasonal_d": [0, 1],
        "seasonal_q": [0, 1],
        "seasonal_period": [7, 12, 30],
    },
    "prophet": {
        "seasonality_mode": ["additive", "multiplicative"],
        "changepoint_prior_scale": [0.001, 0.01, 0.05, 0.1, 0.5],
        "seasonality_prior_scale": [0.01, 1.0, 10.0],
        "holidays_prior_scale": [0.01, 1.0, 10.0],
    },
    "lightgbm": {
        "n_estimators": [100, 200, 500],
        "learning_rate": [0.01, 0.05, 0.1],
        "max_depth": [3, 5, 7, -1],
        "num_leaves": [15, 31, 63],
        "min_child_samples": [5, 20, 50],
    },
    "xgboost": {
        "n_estimators": [100, 200, 500],
        "learning_rate": [0.01, 0.05, 0.1],
        "max_depth": [3, 5, 7],
        "min_child_weight": [1, 3, 5],
        "subsample": [0.7, 0.9, 1.0],
        "colsample_bytree": [0.7, 0.9, 1.0],
    },
    "wma": {
        "window": [4, 8, 12, 20, 30],
    },
    "ets": {
        "trend": ["add", "mul", None],
        "seasonal": ["add", "mul", None],
        "seasonal_periods": [7, 12, 30],
    },
    "theta": {
        "period": [7, 12, 30],
        "deseasonalize": [True, False],
    },
    "stl": {
        "period": [7, 12, 30],
        "robust": [True, False],
    },
}


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

def tune_model(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    model_type: str,
    n_iter: int = 20,
    n_folds: int = 5,
    min_train_size: int = 30,
    random_seed: int = 42,
) -> Dict[str, Any]:
    """Run randomized search with time-series CV for a single model type.

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

    # Pre-compute folds once
    folds = time_series_cv_folds(df, date_col, value_col, n_folds, min_train_size)
    if len(folds) < 2:
        logger.warning("Not enough data for CV tuning (%d folds) — using defaults", len(folds))
        return {"best_params": {}, "cv_scores": {}, "fold_scores": [], "tuned": False}

    # Generate candidate parameter combinations
    keys = list(space.keys())
    all_combos = list(itertools.product(*space.values()))
    if len(all_combos) <= n_iter:
        candidates = all_combos
    else:
        rng = random.Random(random_seed)
        candidates = rng.sample(all_combos, n_iter)

    best_mae = float("inf")
    best_params: Dict[str, Any] = {}
    best_fold_scores: List[Dict[str, float]] = []

    for combo in candidates:
        candidate_params = dict(zip(keys, combo))
        fold_scores: List[Dict[str, float]] = []
        for train_df, test_df in folds:
            try:
                model = selector.get_model(model_type, _to_model_params(model_type, candidate_params))
                model.fit(train_df, date_col, value_col)
                preds = model.forecast(len(test_df))
                pred_values = np.array([
                    _safe_float(p.get("forecast", 0.0)) for p in preds
                ])
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

    if not best_fold_scores:
        logger.warning("Tuning for %s found no valid parameter set — using defaults", model_type)
        return {"best_params": {}, "cv_scores": {}, "fold_scores": [], "tuned": False}

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
