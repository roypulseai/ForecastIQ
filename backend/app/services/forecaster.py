"""Main forecasting orchestrator: runs models, builds ensemble, persists results.

This is the single entry point used by the API to run a forecast. It:
  * Iterates over the requested models, fitting each in isolation
  * Falls back gracefully if a single model fails
  * Computes cross-validated MAE / RMSE / MAPE for model selection
  * Optionally splits train/test for held-out evaluation
  * Builds an optional weighted ensemble
  * Computes baseline forecasts and uplift
  * Returns a JSON-safe dict that the storage layer can persist

Performance optimizations:
  * Models run in parallel via ThreadPoolExecutor (ML libraries release the
    GIL during C-level work, so threads are effective)
  * Large datasets are downsampled intelligently (weekly aggregation for 5+
    year daily data, or recency-bounded tail for very long series)
  * The whole `run` method takes an optional `progress_cb` so callers (e.g.
    the JobManager) can publish incremental progress.
"""
from __future__ import annotations

import logging
import os
import traceback
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..core.utils import to_python
from .data_processor import DataProcessor
from .decomposition import (
    decompose_series,
    recommend_seasonal_params,
)
from .hyperparameter_tuner import tune_model
from .model_selector import ModelSelector
from .models.base import BaseForecaster
from .models.registry import (
    ModelMetrics,
    ModelRegistry,
    TrainingConfig,
    get_model_registry,
    time_series_split,
    evaluate_on_test,
)

logger = logging.getLogger(__name__)


# Tunable thresholds
MAX_PARALLEL_WORKERS = max(2, min(os.cpu_count() or 4, int(os.environ.get("FORECASTIQ_WORKERS", 8))))
DOWNSAMPLE_THRESHOLD = 5000  # rows
WEEKLY_AGG_SPAN_DAYS = 365 * 5


class EnsembleForecaster:
    """Weighted-average ensemble of fitted forecasters."""

    def __init__(
        self,
        models: List[BaseForecaster],
        weights: Optional[List[float]] = None,
    ) -> None:
        if not models:
            raise ValueError("Ensemble requires at least one model")
        self.models = models
        if weights is None:
            weights = [1.0 / len(models)] * len(models)
        if len(weights) != len(models):
            raise ValueError("weights length must match models length")
        total = sum(max(0.0, w) for w in weights) or 1.0
        self.weights: List[float] = [max(0.0, w) / total for w in weights]

    def forecast(
        self,
        horizon: int,
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        all_preds: List[List[Dict[str, Any]]] = []
        weights_used: List[float] = []
        for m, w in zip(self.models, self.weights):
            try:
                preds = m.forecast(horizon, exog_data=exog_data, **kwargs)
                if preds and len(preds) == horizon:
                    all_preds.append(preds)
                    weights_used.append(w)
            except Exception as e:
                logger.warning("Ensemble member %s failed: %s", m.name, e)
        if not all_preds:
            raise ValueError("No ensemble member produced a forecast")
        if weights_used:
            total = sum(weights_used) or 1.0
            weights_used = [w / total for w in weights_used]
        else:
            weights_used = [1.0 / len(all_preds)] * len(all_preds)
        results: List[Dict[str, Any]] = []
        for i in range(horizon):
            date = all_preds[0][i]["date"]
            vals = [p[i]["forecast"] for p in all_preds]
            lo = [p[i].get("lower_ci", p[i]["forecast"] * 0.85) for p in all_preds]
            hi = [p[i].get("upper_ci", p[i]["forecast"] * 1.15) for p in all_preds]
            ens_fc = float(sum(v * w for v, w in zip(vals, weights_used)))
            results.append({
                "date": date,
                "forecast": ens_fc,
                "lower_ci": float(min(lo)),
                "upper_ci": float(max(hi)),
            })
        return results

    def get_baseline(
        self,
        horizon: int,
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        all_preds: List[List[Dict[str, Any]]] = []
        weights_used: List[float] = []
        for m, w in zip(self.models, self.weights):
            try:
                preds = m.get_baseline(horizon, exog_data=None, **kwargs)
                if preds and len(preds) == horizon:
                    all_preds.append(preds)
                    weights_used.append(w)
            except Exception as e:
                logger.warning("Ensemble baseline member %s failed: %s", m.name, e)
        if not all_preds:
            raise ValueError("No ensemble member produced a baseline")
        total = sum(weights_used) or 1.0
        weights_used = [w / total for w in weights_used]
        results: List[Dict[str, Any]] = []
        for i in range(horizon):
            date = all_preds[0][i]["date"]
            vals = [p[i]["forecast"] for p in all_preds]
            lo = [p[i].get("lower_ci", p[i]["forecast"] * 0.85) for p in all_preds]
            hi = [p[i].get("upper_ci", p[i]["forecast"] * 1.15) for p in all_preds]
            ens_fc = float(sum(v * w for v, w in zip(vals, weights_used)))
            results.append({
                "date": date,
                "forecast": ens_fc,
                "lower_ci": float(min(lo)),
                "upper_ci": float(max(hi)),
            })
        return results


def _fit_and_forecast_one(
    model_type: str,
    params: Dict[str, Any],
    sales_df: pd.DataFrame,
    date_col: str,
    value_col: str,
    horizon: int,
    exog_data: Optional[Dict[str, pd.DataFrame]],
) -> Tuple[str, Optional[BaseForecaster], List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any], Dict[str, Any], Dict[str, Any], Optional[str]]:
    """Worker function: fit one model + forecast + baseline. Returns a tuple
    that's easy to assemble into the per_model dict. Defined at module level
    so it's picklable for ProcessPoolExecutor if we ever need it."""
    try:
        selector = ModelSelector()
        model = selector.get_model(model_type, params)
        model.fit(sales_df, date_col, value_col, exog_data=exog_data or {})
        forecast = model.forecast(horizon, exog_data=exog_data)
        baseline = model.get_baseline(horizon, exog_data=exog_data)
        attach_uplift(forecast, baseline)
        metrics = _safe_metrics(model)
        fi = _safe_fi(model.get_feature_importance())
        comp = _safe_dict(model.get_components())
        return (
            model_type, model, forecast, baseline,
            {"mae": None, "rmse": None, "mape": None, **metrics},
            fi, comp, None,
        )
    except Exception as e:
        logger.error("Model %s failed: %s\n%s", model_type, e, traceback.format_exc())
        return (
            model_type, None, [], [], {"error": str(e)}, {}, {}, str(e),
        )


class ForecasterService:
    """High-level orchestration of forecast jobs.

    `run_async` submits a job to the JobManager and returns a job_id.
    `run` is the synchronous version, used internally and by the JobManager.
    """

    def __init__(self) -> None:
        self.selector = ModelSelector()
        self.processor = DataProcessor()

    # ----------------------------------------------------------------- async
    def submit(
        self,
        sales_df: pd.DataFrame,
        request: Dict[str, Any],
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> str:
        """Submit a forecast job to the JobManager. Returns the job_id."""
        from ..core.jobs import get_job_manager
        jm = get_job_manager()

        def _task() -> Dict[str, Any]:
            return self.run(
                sales_df, request, exog_data=exog_data,
                progress_cb=None,
            )

        # Use a simpler progress callback that finds the job by request id
        # We don't have a clean way to thread the job_id here, so we just
        # report 0% and 100% via the future's result.
        job_id = jm.submit(
            job_type="forecast",
            func=self.run,
            request=request,
            sales_df=sales_df,
            exog_data=exog_data,
        )
        return job_id

    # ----------------------------------------------------------------- main
    def run(
        self,
        sales_df: pd.DataFrame,
        request: Dict[str, Any],
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Dict[str, Any]:
        """Run a forecast end-to-end. Returns a JSON-safe dict.

        Args:
            sales_df: Pre-loaded sales DataFrame (already normalized).
            request: ForecastRequest.model_dump() (Pydantic v2).
            exog_data: Dict of normalized DataFrames keyed by type.
            progress_cb: Optional callback (progress_fraction, message).

        Performance optimizations:
            * Very large sales_df is downsampled before model fitting.
            * Models are fit + forecasted in parallel via a thread pool.
            * Ensemble members reuse the CV results to avoid re-computation.
        """
        # Defensive copy — we may mutate sales_df (e.g. add composite key col)
        sales_df = sales_df.copy()
        date_col = request.get("date_column", "date")
        value_col = request.get("target_column", "value")
        horizon = int(request.get("horizon", 30))
        models = request.get("models") or ["prophet"]
        params = request.get("parameters") or {}
        ensemble_models = request.get("ensemble_models") or []
        ensemble_weights = request.get("ensemble_weights") or None
        tune_hyperparameters = bool(request.get("tune_hyperparameters", False))
        # New options
        train_test_split = float(request.get("train_test_split", 1.0))
        backtest_overlap = int(request.get("backtest_overlap", 0))
        save_model = bool(request.get("save_model", False))
        save_model_name = request.get("save_model_name")
        save_model_tags = request.get("save_model_tags") or []
        save_model_notes = request.get("save_model_notes", "")
        # ---- Pre-step: hierarchical / per-category forecasting ----
        # Accept either new `category_columns` (list) or deprecated `category_column` (str).
        category_columns: List[str] = []
        raw_col_val = request.get("category_columns") or request.get("category_column") or None
        if isinstance(raw_col_val, str):
            category_columns = [raw_col_val]
        elif isinstance(raw_col_val, list):
            category_columns = [c for c in raw_col_val if isinstance(c, str) and c in sales_df.columns]

        category_values: List[str] = []
        category_filtered: Dict[str, pd.DataFrame] = {}
        category_column_values: Dict[str, Dict[str, str]] = {}
        COMPOSITE_SEP = " ||| "

        if category_columns:
            # Create a composite key column from all category columns
            composite_key_col = "_composite_cat_key"
            sales_df[composite_key_col] = (
                sales_df[category_columns].astype(str).apply(
                    lambda r: COMPOSITE_SEP.join(r.values), axis=1
                )
            )
            # Build the mapping from composite key → individual column values
            for _, row in sales_df[category_columns + [composite_key_col]].drop_duplicates(
                subset=[composite_key_col]
            ).iterrows():
                key = row[composite_key_col]
                category_column_values[key] = {c: str(row[c]) for c in category_columns}

            # Aggregate the main sales_df: group by date, sum value across all categories
            agg_df = sales_df.groupby(date_col, as_index=False, sort=True)[value_col].sum()

            # Efficient single-pass grouping: group by composite key + date, then split
            grouped = sales_df.groupby([composite_key_col, date_col], as_index=False, sort=True)[value_col].sum()
            for key, grp in grouped.groupby(composite_key_col):
                cat_df = grp.drop(columns=[composite_key_col]).reset_index(drop=True)
                if len(cat_df) >= 20:
                    category_filtered[key] = cat_df

            category_values = sorted(category_filtered.keys())

            # Replace sales_df with the aggregate for the main pipeline
            if len(agg_df) >= 20:
                sales_df = agg_df
            else:
                category_columns = []  # too few rows, fall back to flat

        # ---- Pre-step: optional train/test split for ML models ----
        # Train/test split only applies to ML-capable models (xgboost,
        # lightgbm, automl). Time-series models (ARIMA, SARIMAX, Prophet,
        # ETS, WMA, Theta, STL) always train on 100% of the data.
        ml_models = {"xgboost", "lightgbm", "automl"}
        has_ml = any(m in ml_models for m in models)
        test_df: Optional[pd.DataFrame] = None
        train_df: Optional[pd.DataFrame] = None
        if has_ml and 0.5 <= train_test_split < 1.0 and len(sales_df) >= 30:
            split = time_series_split(
                sales_df, date_col, value_col,
                train_ratio=train_test_split,
                horizon=0,
            )
            train_df = split["train"]
            test_df = split["test"]
            logger.info(
                "Train/test split: %d train / %d test (ratio=%.2f) — for ML models",
                len(train_df), len(test_df), train_test_split,
            )

        # ---- Pre-step: intelligent downsampling for huge datasets ----
        downsample_info: Dict[str, Any] = {
            "downsample_applied": False,
            "original_rows": int(len(sales_df)),
        }
        if len(sales_df) > DOWNSAMPLE_THRESHOLD:
            try:
                sales_df, ds_info = DataProcessor.downsample_for_forecasting(
                    sales_df, date_col, value_col,
                    max_points=DOWNSAMPLE_THRESHOLD,
                )
                downsample_info.update(ds_info)
                if downsample_info.get("downsample_applied"):
                    logger.info(
                        "Downsampled sales data: %d -> %d rows (%s)",
                        downsample_info["original_rows"],
                        downsample_info["new_rows"],
                        downsample_info.get("aggregation_level"),
                    )
            except Exception as e:
                logger.warning("Downsampling failed (continuing with full data): %s", e)

        if progress_cb:
            progress_cb(0.05, "Data prepared")

        # Compute split/data stats for downstream use (tuning, seasonality)
        has_split = train_df is not None and test_df is not None
        n_unique_dates = int(sales_df[date_col].nunique())

        # ---- 0) Optional hyperparameter tuning ----
        # Runs adaptive two-round search with expanding-window CV for each model.
        # Tuned parameters are merged into the user-supplied params.
        tuning_results: Dict[str, Any] = {}
        if tune_hyperparameters:
            cv_df = (train_df if has_split else sales_df)
            n_models = len(models)
            for idx, m in enumerate(models):
                try:
                    if progress_cb:
                        progress_cb(0.05 + 0.10 * (idx / n_models), f"Tuning {m}…")
                    result = tune_model(
                        cv_df, date_col, value_col, m,
                        n_iter=30, n_folds=max(3, min(7, int(n_unique_dates * 0.1))),
                        exog_data=exog_data,
                    )
                    if result.get("tuned") and result["best_params"]:
                        tuning_results[m] = result
                        m_key = m
                        existing = params.get(m_key, {})
                        # Merge: tuned params override user defaults
                        params[m_key] = {**existing, **result["best_params"]}
                        logger.info(
                            "Tuned %s: %s  → CV MAE=%.4f",
                            m, result["best_params"], result["cv_scores"].get("mae", 0),
                        )
                except Exception as e:
                    logger.warning("Tuning failed for %s: %s", m, e)
            if progress_cb:
                progress_cb(0.15, "Tuning complete")

        # ---- 0.5) Seasonality analysis & auto-param injection ----
        # Decompose the series, detect dominant seasonal periods, and
        # inject the discovered periods into each model's parameters so
        # downstream models (ETS, Prophet, SARIMAX, etc.) use them.
        decomposition: Dict[str, Any] = {}
        try:
            if progress_cb:
                progress_cb(0.15, "Analyzing seasonality…")
            cv_df_seas = (train_df if has_split else sales_df)
            decomposition = decompose_series(cv_df_seas, date_col, value_col)
            if decomposition.get("period") and not decomposition.get("error"):
                logger.info(
                    "Detected seasonal period=%d  strength=%.2f",
                    decomposition["period"],
                    decomposition.get("seasonal_strength", 0),
                )
                if decomposition.get("seasonal_strength", 0) > 0.15:
                    for m in models:
                        seas_params = recommend_seasonal_params(
                            cv_df_seas, date_col, value_col, m,
                        )
                        if seas_params:
                            m_key = m
                            existing = params.get(m_key, {})
                            # Auto params are lower priority than user/tuned params
                            merged = {**seas_params, **existing}
                            if merged != existing:
                                params[m_key] = merged
                                logger.info("Auto-applied seasonal params for %s: %s", m, seas_params)
        except Exception as e:
            logger.warning("Seasonality analysis failed (continuing): %s", e)

        # ---- 1) Cross-validate each requested model in parallel ----
        # CV uses the training portion only for ML models (to avoid leakage),
        # and full data for time-series models.
        has_split = train_df is not None

        def _cv_input(m: str) -> pd.DataFrame:
            if has_split and m in ml_models:
                return train_df  # type: ignore[return-value]
            return sales_df

        cv_results: Dict[str, Dict[str, float]] = {}
        cv_workers = min(len(models), MAX_PARALLEL_WORKERS)
        if cv_workers > 1:
            with ThreadPoolExecutor(max_workers=cv_workers) as ex:
                fut_to_model = {
                    ex.submit(
                        self.selector.cross_validate,
                        _cv_input(m), date_col, value_col, m, params,
                        min(7, horizon),
                    ): m
                    for m in models
                }
                for fut in as_completed(fut_to_model):
                    m = fut_to_model[fut]
                    try:
                        cv_results[m] = fut.result()
                    except Exception as e:
                        logger.warning("CV error for %s: %s", m, e)
                        cv_results[m] = {"mae": None, "rmse": None, "mape": None, "error": str(e)}
        else:
            for m in models:
                try:
                    cv_results[m] = self.selector.cross_validate(
                        _cv_input(m), date_col, value_col, m, params, horizon=min(7, horizon)
                    )
                except Exception as e:
                    logger.warning("CV error for %s: %s", m, e)
                    cv_results[m] = {"mae": None, "rmse": None, "mape": None, "error": str(e)}

        if progress_cb:
            progress_cb(0.20, "Cross-validation complete")

        # ---- 2) Fit + forecast each model in parallel ----
        per_model: Dict[str, Dict[str, Any]] = {}
        # When a train/test split is in effect, ML-capable models (xgboost,
        # lightgbm, automl) use the training portion for fitting.
        # Time-series models always train on 100% of the data.
        has_split = train_df is not None
        fit_workers = min(len(models), MAX_PARALLEL_WORKERS)
        completed = 0

        def _fit_input(m: str) -> pd.DataFrame:
            if has_split and m in ml_models:
                return train_df  # type: ignore[return-value]
            return sales_df

        if fit_workers > 1:
            with ThreadPoolExecutor(max_workers=fit_workers) as ex:
                fut_to_model = {
                    ex.submit(
                        _fit_and_forecast_one,
                        m, params, _fit_input(m), date_col, value_col,
                        horizon, exog_data,
                    ): m
                    for m in models
                }
                for fut in as_completed(fut_to_model):
                    m = fut_to_model[fut]
                    try:
                        result = fut.result()
                    except Exception as e:
                        logger.error("Model %s crashed: %s", m, e)
                        result = (m, None, [], [], {"error": str(e)}, {}, {}, str(e))
                    per_model[m] = _assemble_model_result(m, result, cv_results)
                    completed += 1
                    if progress_cb:
                        progress_cb(0.20 + 0.55 * (completed / n_models), f"Trained {completed}/{n_models} models")
        else:
            for m in models:
                result = _fit_and_forecast_one(
                    m, params, _fit_input(m), date_col, value_col, horizon, exog_data
                )
                per_model[m] = _assemble_model_result(m, result, cv_results)
                completed += 1
                if progress_cb:
                    progress_cb(0.20 + 0.55 * (completed / n_models), f"Trained {completed}/{n_models} models")

        # ---- 2b) If train/test split: evaluate on test set + refit on all data ----
        # Test metrics are computed only for ML models (which were fit on train
        # portion). Time-series models train on full data so no test evaluation.
        test_metrics_per_model: Dict[str, Dict[str, float]] = {}
        if test_df is not None and not test_df.empty:
            for m in models:
                if m not in ml_models:
                    continue
                pm = per_model.get(m)
                if not pm or pm.get("error"):
                    continue
                # Use the model's own forecast values over the test horizon
                fc_vals = pm.get("forecast_values", [])
                test_metrics = evaluate_on_test(fc_vals, test_df, date_col, value_col)
                if test_metrics.mae is not None:
                    test_metrics_per_model[m] = {
                        "mae": test_metrics.mae,
                        "rmse": test_metrics.rmse,
                        "mape": test_metrics.mape,
                        "r2": test_metrics.r2,
                        "test_rows": test_metrics.test_rows,
                    }
                    # Merge into the per-model metrics dict
                    if "metrics" not in pm:
                        pm["metrics"] = {}
                    test_acc = _compute_forecast_accuracy(test_metrics.mape)
                    pm["metrics"].update({
                        "test_mae": test_metrics.mae,
                        "test_rmse": test_metrics.rmse,
                        "test_mape": test_metrics.mape,
                        "test_r2": test_metrics.r2,
                        "test_forecast_accuracy": test_acc,
                        "test_accuracy_grade": _accuracy_grade(test_acc),
                    })
            logger.info(
                "Test metrics per model: %s",
                {k: round(v["mae"], 2) for k, v in test_metrics_per_model.items() if v.get("mae") is not None},
            )
            # Refit each successful ML model on full data so the final forecast
            # covers dates beyond ALL actuals (not just beyond the training split).
            for m in models:
                if m not in ml_models:
                    continue
                pm = per_model.get(m)
                if not pm or pm.get("error"):
                    continue
                try:
                    full_model = self.selector.get_model(m, params)
                    full_model.fit(sales_df, date_col, value_col, exog_data=exog_data or {})
                    full_fc = full_model.forecast(horizon, exog_data=exog_data)
                    full_base = full_model.get_baseline(horizon, exog_data=exog_data)
                    attach_uplift(full_fc, full_base)
                    pm["forecast_values"] = full_fc
                    pm["baseline_values"] = full_base
                    # Update metrics from the full-data model
                    full_metrics = _safe_metrics(full_model)
                    mape = full_metrics.get("mape")
                    forecast_accuracy = _compute_forecast_accuracy(mape)
                    pm["metrics"].update({
                        **full_metrics,
                        "forecast_accuracy": forecast_accuracy,
                        "accuracy_grade": _accuracy_grade(forecast_accuracy),
                    })
                    pm["feature_importance"] = _safe_fi(full_model.get_feature_importance())
                    pm["components"] = _safe_dict(full_model.get_components())
                except Exception as e:
                    logger.warning("Full-data refit failed for %s (using train-only forecast): %s", m, e)

        # ---- 2c) Factor contribution analysis: isolate each external factor's uplift ----
        factor_contributions: Dict[str, Any] = {}
        if per_model and exog_data:
            try:
                best_key_for_factors = min(
                    [k for k, v in per_model.items() if not v.get("error")],
                    key=lambda k: per_model[k].get("metrics", {}).get("test_mae")
                    or per_model[k].get("metrics", {}).get("mae")
                    or float("inf"),
                    default=None,
                )
                if best_key_for_factors:
                    fc_model = self.selector.get_model(best_key_for_factors, params)
                    fc_model.fit(sales_df, date_col, value_col, exog_data=exog_data or {})
                    baseline_fc = fc_model.get_baseline(horizon, exog_data=exog_data)
                    factor_contributions = _compute_factor_contributions(
                        fc_model, exog_data, horizon, baseline_fc,
                    )
            except Exception as e:
                logger.warning("Factor contribution analysis failed: %s", e)

        # ---- 2d) Optionally save the best model to the registry ----
        saved_model_meta: Optional[Dict[str, Any]] = None
        if save_model and per_model:
            try:
                best_key = min(
                    [k for k, v in per_model.items() if not v.get("error")],
                    key=lambda k: per_model[k].get("metrics", {}).get("test_mae")
                    or per_model[k].get("metrics", {}).get("mae")
                    or float("inf"),
                    default=None,
                )
                if best_key is not None:
                    # Re-fit the best model on FULL data so the saved model
                    # is the most up-to-date version.
                    best_model_instance = self.selector.get_model(best_key, params)
                    best_model_instance.fit(sales_df, date_col, value_col, exog_data=exog_data or {})
                    best_metrics = test_metrics_per_model.get(best_key, {})
                    cv = cv_results.get(best_key, {})
                    registry_metrics = ModelMetrics(
                        mae=best_metrics.get("mae") or cv.get("mae"),
                        rmse=best_metrics.get("rmse") or cv.get("rmse"),
                        mape=best_metrics.get("mape") or cv.get("mape"),
                        train_rows=len(sales_df) - (len(test_df) if test_df is not None else 0),
                        test_rows=len(test_df) if test_df is not None else 0,
                        cv_mae=cv.get("mae"),
                        cv_rmse=cv.get("rmse"),
                        cv_mape=cv.get("mape"),
                    )
                    training_cfg = TrainingConfig(
                        date_column=date_col,
                        value_column=value_col,
                        frequency=request.get("frequency", "D"),
                        train_test_split=train_test_split,
                        horizon_used=horizon,
                        extra_columns=[c for c in sales_df.columns if c not in (date_col, value_col)],
                        hyperparameters=params.get(best_key, {}),
                        exogenous_used=sorted((exog_data or {}).keys()),
                    )
                    registry = get_model_registry()
                    from .models.registry import ModelFramework
                    framework = ModelRegistry._pick_framework(best_key)
                    display_name = save_model_name or f"{best_model_instance.name} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
                    meta = registry.save(
                        name=display_name,
                        model=best_model_instance,
                        metrics=registry_metrics,
                        training=training_cfg,
                        train_start=(
                            pd.Timestamp(sales_df[date_col].iloc[0]).strftime("%Y-%m-%d")
                            if not sales_df.empty else None
                        ),
                        train_end=(
                            pd.Timestamp(sales_df[date_col].iloc[-1]).strftime("%Y-%m-%d")
                            if not sales_df.empty else None
                        ),
                        test_start=(
                            pd.Timestamp(test_df[date_col].iloc[0]).strftime("%Y-%m-%d")
                            if test_df is not None and not test_df.empty else None
                        ),
                        test_end=(
                            pd.Timestamp(test_df[date_col].iloc[-1]).strftime("%Y-%m-%d")
                            if test_df is not None and not test_df.empty else None
                        ),
                        tags=list(save_model_tags) if save_model_tags else [],
                        notes=save_model_notes or "",
                    )
                    saved_model_meta = meta.to_dict()
                    logger.info("Saved model %s (%s) to registry", meta.model_id, best_key)
            except Exception as e:
                logger.exception("Failed to save model to registry")
                saved_model_meta = {"error": str(e)}

        # ---- 3) Build rankings from CV MAE ----
        rankings = _build_rankings(cv_results)
        if progress_cb:
            progress_cb(0.80, "Rankings ready")

        # ---- 4) Ensemble ----
        ensemble_result: Optional[Dict[str, Any]] = None
        if ensemble_models and len(ensemble_models) >= 2:
            try:
                chosen = [m for m in ensemble_models if m in per_model
                          and not per_model[m].get("error")]
                if len(chosen) >= 2:
                    members: List[BaseForecaster] = []
                    # Fit ensemble members in parallel too
                    def _refit(m: str) -> Tuple[str, Optional[BaseForecaster]]:
                        try:
                            inst = self.selector.get_model(m, params)
                            inst.fit(sales_df, date_col, value_col, exog_data=exog_data or {})
                            return m, inst
                        except Exception as e:
                            logger.warning("Ensemble member %s re-fit failed: %s", m, e)
                            return m, None
                    if len(chosen) > 1:
                        with ThreadPoolExecutor(max_workers=min(len(chosen), MAX_PARALLEL_WORKERS)) as ex:
                            for mname, inst in ex.map(_refit, chosen):
                                if inst is not None:
                                    members.append(inst)
                    else:
                        for c in chosen:
                            _, inst = _refit(c)
                            if inst is not None:
                                members.append(inst)
                    if len(members) >= 2:
                        if ensemble_weights and len(ensemble_weights) == len(members):
                            weights = list(ensemble_weights)
                        else:
                            weights = []
                            for c in chosen[:len(members)]:
                                cv = cv_results.get(c, {})
                                mae = cv.get("mae")
                                if mae and mae > 0:
                                    weights.append(1.0 / (mae + 1e-3))
                                else:
                                    weights.append(1.0)
                        ens = EnsembleForecaster(members, weights)
                        ens_fc = ens.forecast(horizon, exog_data=exog_data)
                        ens_base = ens.get_baseline(horizon, exog_data=exog_data)
                        attach_uplift(ens_fc, ens_base)

                        # Compute ensemble metrics if test data exists
                        ens_metrics: Dict[str, float] = {}
                        if test_df is not None and len(test_df) > 0:
                            try:
                                actual_vals = test_df[value_col].values
                                pred_vals = [fv.get("forecast", 0.0) for fv in ens_fc]
                                n = min(len(actual_vals), len(pred_vals))
                                if n > 0:
                                    actuals_arr = np.array(actual_vals[:n])
                                    preds_arr = np.array(pred_vals[:n])
                                    errors = np.abs(actuals_arr - preds_arr)
                                    mae = float(np.mean(errors))
                                    rmse = float(np.sqrt(np.mean(errors ** 2)))
                                    mape_vals = np.where(actuals_arr == 0, 1e-9, np.abs(actuals_arr))
                                    mape = float(np.mean(np.abs(errors) / mape_vals) * 100)
                                    ens_metrics = {
                                        "mae": mae,
                                        "rmse": rmse,
                                        "mape": mape,
                                        "forecast_accuracy": _compute_forecast_accuracy(mape),
                                        "accuracy_grade": _accuracy_grade(_compute_forecast_accuracy(mape)),
                                    }
                            except Exception as e:
                                logger.warning("Failed to compute ensemble metrics: %s", e)

                        ensemble_result = {
                            "models_used": [mm.name for mm in members],
                            "weights": ens.weights,
                            "forecast_values": ens_fc,
                            "baseline_values": ens_base,
                            "metrics": ens_metrics,
                            "individual_results": [
                                {
                                    "model_name": per_model[c].get("model_name", c),
                                    "metrics": per_model[c].get("metrics", {}),
                                    "forecast_values": per_model[c].get("forecast_values", []),
                                    "baseline_values": per_model[c].get("baseline_values", []),
                                    "feature_importance": per_model[c].get("feature_importance", {}),
                                    "components": per_model[c].get("components", {}),
                                }
                                for c in chosen[:len(members)]
                            ],
                        }
            except Exception as e:
                logger.warning("Ensemble build failed: %s", e)
                ensemble_result = None
        if progress_cb:
            progress_cb(0.90, "Ensemble ready")

        # ---- 5) Best model + summary + external analysis ----
        # When test metrics are available, prefer them for ranking
        if test_metrics_per_model:
            rankings = _build_rankings_from_test(test_metrics_per_model, cv_results)
        best_model: Optional[str] = rankings[0]["model"] if rankings else None
        summary = _build_summary(per_model, ensemble_result, horizon)
        external = _build_external_analysis(
            exog_data, per_model,
            sales_df=sales_df, date_col=date_col, value_col=value_col,
        )

        # ---- 2b.5) Backtest re-forecast ----
        # When backtest_overlap > 0, re-train each model on data truncated by
        # `backtest_overlap` and forecast that window.  The resulting forecast
        # values overlap the last N actuals, giving users a visual comparison
        # of "what the model would have predicted" vs what actually happened.
        # When backtest_overlap == 0 and train_test_split == 1.0 (no explicit split),
        # auto-use latest 20% of data as backtest period for business users.
        auto_backtest = False
        overlap_n = 0
        backtest_start_date: Optional[str] = None
        backtest_end_date: Optional[str] = None

        # Compute overlap in terms of UNIQUE DATES, not row count
        n_unique_dates = int(sales_df[date_col].nunique()) if date_col in sales_df.columns else len(sales_df)
        if backtest_overlap == 0 and n_unique_dates > 50:
            auto_backtest = True
            overlap_n = max(1, int(n_unique_dates * 0.2))
            logger.info("Auto-backtest: using last %d unique dates (~20%% of %d)", overlap_n, n_unique_dates)
        elif backtest_overlap > 0:
            overlap_n = min(backtest_overlap, n_unique_dates - 5)

        if overlap_n > 0 and n_unique_dates > overlap_n + 5:
            # Date-based split: train on data before split_date, test on data after
            unique_dates = sorted(sales_df[date_col].unique())
            split_date = unique_dates[-overlap_n]
            backtest_df = sales_df[sales_df[date_col] < split_date].copy()
            backtest_actuals = sales_df[sales_df[date_col] >= split_date].copy()
            backtest_start_date = str(backtest_actuals[date_col].iloc[0])[:10]
            backtest_end_date = str(backtest_actuals[date_col].iloc[-1])[:10]
            logger.info("Backtest overlap_n=%d dates, train=%d rows, test=%d rows", overlap_n, len(backtest_df), len(backtest_actuals))

            for m_name, pm in per_model.items():
                if pm.get("error"):
                    continue
                try:
                    bt_model = self.selector.get_model(m_name, params)
                    bt_model.fit(backtest_df, date_col, value_col, exog_data=exog_data or {})
                    bt_fc = bt_model.forecast(overlap_n, exog_data=exog_data)
                    pm["backtest_forecast_values"] = bt_fc
                    bt_metrics = _compute_backtest_metrics(bt_fc, backtest_actuals, date_col, value_col)
                    pm["backtest_metrics"] = bt_metrics
                except Exception as e:
                    logger.warning("Backtest re-forecast failed for %s: %s", m_name, e)
                    pm["backtest_forecast_values"] = []
                    pm["backtest_metrics"] = {}

            if ensemble_result:
                try:
                    bt_members: List[BaseForecaster] = []
                    for m_name in ensemble_result.get("models_used", []):
                        try:
                            inst = self.selector.get_model(m_name, params)
                            inst.fit(backtest_df, date_col, value_col, exog_data=exog_data or {})
                            bt_members.append(inst)
                        except Exception:
                            pass
                    if len(bt_members) >= 1:
                        ens = EnsembleForecaster(bt_members)
                        bt_fc = ens.forecast(overlap_n, exog_data=exog_data)
                        ensemble_result["backtest_forecast_values"] = bt_fc
                        bt_metrics = _compute_backtest_metrics(bt_fc, backtest_actuals, date_col, value_col)
                        ensemble_result["backtest_metrics"] = bt_metrics
                except Exception as e:
                    logger.warning("Ensemble backtest re-forecast failed: %s", e)
        elif overlap_n > 0:
            logger.warning("Backtest skipped: overlap=%d unique dates, but only %d available", overlap_n, n_unique_dates)

        # ---- 6) Per-category forecasts (parallel) ----
        # Run forecasts for each category value in parallel for speed.
        # Each (category, model) pair is submitted to a thread pool.
        category_forecasts: Dict[str, Dict[str, Any]] = {}
        if category_columns and category_values:
            cat_futures: Dict[Future, Tuple[str, str]] = {}
            cat_results: Dict[str, Dict[str, Any]] = {}
            cat_cv_results: Dict[str, Dict[str, Dict[str, float]]] = {}
            cat_workers = min(len(category_values) * len(models), MAX_PARALLEL_WORKERS)

            # Run CV for each category in parallel (fast, uses small folds)
            for cat_val in category_values:
                cat_df = category_filtered.get(cat_val)
                if cat_df is None or len(cat_df) < 20:
                    continue
                cat_cv_results[cat_val] = {}
                for m in models:
                    try:
                        cat_cv = self.selector.cross_validate(
                            cat_df, date_col, value_col, m, params,
                            min(7, horizon),
                        )
                        cat_cv_results[cat_val][m] = cat_cv
                    except Exception as e:
                        logger.debug("CV for category %s model %s failed: %s", cat_val, m, e)
                        cat_cv_results[cat_val][m] = {"mae": None, "rmse": None, "mape": None}

            with ThreadPoolExecutor(max_workers=cat_workers) as ex:
                for cat_val in category_values:
                    cat_df = category_filtered.get(cat_val)
                    if cat_df is None or len(cat_df) < 20:
                        continue
                    cat_results.setdefault(cat_val, {})
                    for m in models:
                        fut = ex.submit(
                            _fit_and_forecast_one,
                            m, params, cat_df, date_col, value_col, horizon, exog_data,
                        )
                        cat_futures[fut] = (cat_val, m)

                cat_done = 0
                cat_total = len(cat_futures)
                for fut in as_completed(cat_futures):
                    cat_val, m = cat_futures[fut]
                    try:
                        result_tuple = fut.result()
                        cv_for_cat = cat_cv_results.get(cat_val, {})
                        cat_results[cat_val][m] = _assemble_model_result(m, result_tuple, cv_for_cat)
                    except Exception as e:
                        logger.warning("Category %s model %s failed: %s", cat_val, m, e)
                        cat_results[cat_val][m] = {
                            "model_name": m, "metrics": {"error": str(e)},
                            "forecast_values": [], "error": str(e),
                        }
                    cat_done += 1
                    if progress_cb and cat_total > 0:
                        progress_cb(0.90 + 0.05 * (cat_done / cat_total), f"Category forecasts {cat_done}/{cat_total}")

            # Stitch results: add category metadata + build summary
            for cat_val, per_model in cat_results.items():
                for m_res in per_model.values():
                    for fv in m_res.get("forecast_values", []):
                        fv["category"] = cat_val
                        for col, val in category_column_values.get(cat_val, {}).items():
                            fv[col] = val
                cat_summary = _build_summary(per_model, None, horizon)
                # Embed per-category historical actuals so the frontend chart
                # shows category-specific data instead of aggregate.
                cat_actuals: List[Dict[str, Any]] = []
                cat_src = category_filtered.get(cat_val)
                if cat_src is not None and date_col in cat_src.columns and value_col in cat_src.columns:
                    for _, row in cat_src.iterrows():
                        d = row[date_col]
                        v = row[value_col]
                        try:
                            if pd.notna(d) and pd.notna(v):
                                cat_actuals.append({"date": str(d)[:10], "value": float(v)})
                        except Exception:
                            pass
                    if cat_actuals:
                        cat_actuals.sort(key=lambda x: x["date"])
                category_forecasts[cat_val] = {
                    "results": per_model,
                    "summary": cat_summary,
                    "historical_actuals": cat_actuals,
                }

            # ---- 6b) Per-category backtest forecasts ----
            # Re-fit each model on truncated category data and forecast the
            # backtest window so the chart shows a forecast overlay in the
            # backtest zone for each category.
            if overlap_n > 0:
                for cat_val in category_values:
                    cat_df = category_filtered.get(cat_val)
                    if cat_df is None or len(cat_df) < 20 or cat_val not in category_forecasts:
                        continue
                    cat_unique_dates = sorted(cat_df[date_col].unique())
                    if len(cat_unique_dates) <= overlap_n + 5:
                        continue
                    cat_split_date = cat_unique_dates[-overlap_n]
                    cat_bt_df = cat_df[cat_df[date_col] < cat_split_date].copy()
                    cat_bt_actuals = cat_df[cat_df[date_col] >= cat_split_date].copy()
                    cat_per_model = category_forecasts[cat_val].get("results", {})
                    for m_name, pm in cat_per_model.items():
                        if pm.get("error"):
                            continue
                        try:
                            bt_model = self.selector.get_model(m_name, params)
                            bt_model.fit(cat_bt_df, date_col, value_col, exog_data=exog_data or {})
                            bt_fc = bt_model.forecast(overlap_n, exog_data=exog_data)
                            pm["backtest_forecast_values"] = bt_fc
                            bt_metrics = _compute_backtest_metrics(
                                bt_fc, cat_bt_actuals, date_col, value_col,
                            )
                            pm["backtest_metrics"] = bt_metrics
                        except Exception as e:
                            logger.warning("Category %s backtest for %s failed: %s", cat_val, m_name, e)
            if progress_cb:
                progress_cb(0.95, "Category forecasts done")

        # Embed the source historical data so the frontend never needs to fetch
        # the file separately or guess column names for the chart.
        historical: List[Dict[str, Any]] = []
        if date_col in sales_df.columns and value_col in sales_df.columns:
            for _, row in sales_df.iterrows():
                d = row[date_col]
                v = row[value_col]
                try:
                    if pd.notna(d) and pd.notna(v):
                        historical.append({
                            "date": str(d)[:10],
                            "value": float(v),
                        })
                except Exception:
                    pass
        if historical:
            historical.sort(key=lambda x: x["date"])

        result: Dict[str, Any] = {
            "name": request.get("name", "Forecast"),
            "request": request,
            "results": per_model,
            "model_rankings": rankings,
            "best_model": best_model,
            "ensemble": ensemble_result,
            "summary": summary,
            "external_factor_analysis": external,
            "factor_contributions": factor_contributions,
            "downsample_info": downsample_info,
            "test_metrics": test_metrics_per_model,
            "saved_model": saved_model_meta,
            "tuning_results": tuning_results,
            "category_column": category_columns[0] if len(category_columns) == 1 else None,
            "category_columns": category_columns or None,
            "category_values": category_values if category_columns else [],
            "category_forecasts": category_forecasts,
            "category_column_values": category_column_values if category_columns else {},
            "auto_backtest": auto_backtest,
            "backtest_overlap_n": overlap_n if overlap_n > 0 else (request.get("backtest_overlap") or 0),
            "backtest_start_date": backtest_start_date,
            "backtest_end_date": backtest_end_date,
            "historical_actuals": historical,
            "decomposition": decomposition if decomposition.get("period") else None,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        if progress_cb:
            progress_cb(1.0, "Done")
        return to_python(result)

    # ----------------------------------------------------------------- train / save
    def train_and_save(
        self,
        sales_df: pd.DataFrame,
        request: Dict[str, Any],
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
        model_name: Optional[str] = None,
        notes: str = "",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Train one or more models on a train split, evaluate on a held-out
        test split, and persist the best one to the model registry.

        `request` should specify:
            * `model_type` or `models` (list) — which model(s) to train
            * `train_test_split` (default 0.8) — fraction for training
            * `horizon` — also used as the test-set size (if > 0)
            * `date_column`, `target_column` — column names
            * `frequency` — date frequency ('D', 'W', 'M')
            * `parameters` (optional) — hyperparameters per model

        Returns a JSON-safe dict with: train/test split info, evaluation
        metrics per model, the saved model_id, and the registry metadata.
        """
        date_col = request.get("date_column", "date")
        value_col = request.get("target_column", "value")
        frequency = request.get("frequency", "D")
        horizon = int(request.get("horizon", 30))
        train_ratio = float(request.get("train_test_split", 0.8))
        params = request.get("parameters") or {}

        # Models to train: either explicit list or single model_type
        if "models" in request and request["models"]:
            models_to_train = list(request["models"])
        elif "model_type" in request and request["model_type"]:
            models_to_train = [request["model_type"]]
        else:
            models_to_train = ["prophet"]

        # Split the data
        split = time_series_split(
            sales_df, date_col, value_col,
            train_ratio=train_ratio,
            horizon=horizon if horizon > 0 else 0,
        )
        train_df = split["train"]
        test_df = split["test"]

        train_start = (
            pd.Timestamp(train_df[date_col].iloc[0]).strftime("%Y-%m-%d")
            if not train_df.empty else None
        )
        train_end = (
            pd.Timestamp(train_df[date_col].iloc[-1]).strftime("%Y-%m-%d")
            if not train_df.empty else None
        )
        test_start = (
            pd.Timestamp(test_df[date_col].iloc[0]).strftime("%Y-%m-%d")
            if not test_df.empty else None
        )
        test_end = (
            pd.Timestamp(test_df[date_col].iloc[-1]).strftime("%Y-%m-%d")
            if not test_df.empty else None
        )

        # Train each model, evaluate on test set, then save the best one
        results: List[Dict[str, Any]] = []
        best: Optional[Tuple[BaseForecaster, ModelMetrics, str]] = None  # (model, metrics, name)

        for mtype in models_to_train:
            try:
                model = self.selector.get_model(mtype, params)
                # Fit on TRAIN only (data-science best practice)
                model.fit(train_df, date_col, value_col, exog_data=exog_data or {})

                # Predict on the test set to evaluate
                test_horizon = len(test_df)
                test_predictions = model.forecast(
                    test_horizon, exog_data=exog_data
                )

                # Compute evaluation metrics on the test set
                eval_metrics = evaluate_on_test(
                    test_predictions, test_df, date_col, value_col
                )
                # Augment with training-time metrics
                try:
                    train_metrics = model.get_metrics() or {}
                    for k, v in train_metrics.items():
                        if v is not None and k not in eval_metrics.__dict__:
                            setattr(eval_metrics, k, float(v))
                except Exception as e:
                    logger.warning("Failed to augment training metrics: %s", e)
                eval_metrics.train_rows = len(train_df)
                eval_metrics.test_rows = len(test_df)

                # CV metrics (separate from test-set evaluation)
                try:
                    cv = self.selector.cross_validate(
                        train_df, date_col, value_col, mtype, params,
                        horizon=min(7, test_horizon),
                    )
                    eval_metrics.cv_mae = cv.get("mae")
                    eval_metrics.cv_rmse = cv.get("rmse")
                    eval_metrics.cv_mape = cv.get("mape")
                except Exception as e:
                    logger.warning("CV metrics computation failed for %s: %s", mtype, e)

                results.append({
                    "model_type": mtype,
                    "model_name": model.name,
                    "metrics": eval_metrics.__dict__,
                    "error": None,
                })

                # Track the best (lowest MAE) for persistence
                if eval_metrics.mae is not None:
                    if best is None or eval_metrics.mae < best[1].mae:
                        best = (model, eval_metrics, mtype)
            except Exception as e:
                logger.exception("Training %s failed", mtype)
                results.append({
                    "model_type": mtype,
                    "model_name": mtype,
                    "metrics": {},
                    "error": str(e),
                })

        # Persist the best model
        saved_meta: Optional[Dict[str, Any]] = None
        if best is not None:
            best_model, best_metrics, best_type = best
            registry = get_model_registry()
            exog_used = sorted((exog_data or {}).keys())
            display_name = model_name or f"{best_model.name} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            training_cfg = TrainingConfig(
                date_column=date_col,
                value_column=value_col,
                frequency=frequency,
                train_test_split=train_ratio,
                horizon_used=horizon,
                extra_columns=[c for c in train_df.columns if c not in (date_col, value_col)],
                hyperparameters=params.get(best_type, {}),
                exogenous_used=exog_used,
            )
            meta = registry.save(
                name=display_name,
                model=best_model,
                metrics=best_metrics,
                training=training_cfg,
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                tags=tags or [],
                notes=notes,
            )
            saved_meta = meta.to_dict()

        return to_python({
            "split": {
                "train_rows": int(len(train_df)),
                "test_rows": int(len(test_df)),
                "train_start": train_start,
                "train_end": train_end,
                "test_start": test_start,
                "test_end": test_end,
                "train_ratio": train_ratio,
            },
            "results": results,
            "saved_model": saved_meta,
            "created_at": datetime.utcnow().isoformat() + "Z",
        })

    # ----------------------------------------------------------------- load + forecast
    def forecast_with_loaded_model(
        self,
        model_id: str,
        horizon: int,
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> Dict[str, Any]:
        """Load a saved model and use it to forecast without retraining.

        This is the key workflow for the data scientist: train once, save,
        then load and predict many times on new data.
        """
        registry = get_model_registry()
        loaded = registry.load(model_id)
        model = loaded.model
        meta = loaded.meta

        # Forecast
        forecast = model.forecast(horizon, exog_data=exog_data)
        try:
            baseline = model.get_baseline(horizon, exog_data=exog_data)
            attach_uplift(forecast, baseline)
        except Exception as e:
            logger.warning("Baseline computation failed for loaded model: %s", e)
            baseline = []
        # Components
        try:
            components = _safe_dict(model.get_components())
        except Exception as e:
            logger.warning("Components extraction failed for loaded model: %s", e)
            components = {}

        return to_python({
            "model_id": model_id,
            "model_name": model.name if hasattr(model, "name") else meta.model_type,
            "model_meta": meta.to_dict(),
            "forecast_values": forecast,
            "baseline_values": baseline,
            "components": components,
            "horizon": horizon,
        })

    # ----------------------------------------------------------------- helpers
    @staticmethod
    def _model_metrics(model: BaseForecaster) -> Dict[str, float]:
        try:
            m = model.get_metrics() or {}
            return {k: float(v) for k, v in m.items() if v is not None}
        except Exception as e:
            logger.warning("Failed to extract model metrics: %s", e)
            return {}


def _compute_forecast_accuracy(mape: Optional[float]) -> Optional[float]:
    """Convert MAPE (%) to a business-friendly accuracy percentage (0-100).

    MAPE is already a percentage (e.g. 1.5 = 1.5% error), so accuracy
    is simply 100 - MAPE, clamped to [0, 100].
    """
    if mape is None or (isinstance(mape, float) and np.isnan(mape)):
        return None
    return max(0.0, min(100.0, 100.0 - mape))


def _accuracy_grade(accuracy: Optional[float]) -> Optional[str]:
    """Letter-style grade based on forecast accuracy."""
    if accuracy is None:
        return None
    if accuracy >= 90:
        return "Excellent"
    if accuracy >= 80:
        return "Good"
    if accuracy >= 70:
        return "Fair"
    if accuracy >= 60:
        return "Marginal"
    return "Poor"


def _assemble_model_result(
    model_type: str,
    result_tuple: Tuple,
    cv_results: Dict[str, Dict[str, float]],
) -> Dict[str, Any]:
    """Convert a worker-function tuple into the per_model dict entry."""
    _, model, forecast, baseline, metrics, fi, comp, error = result_tuple
    if error is not None:
        return {
            "model_name": model_type,
            "model": model_type,
            "metrics": {"error": error},
            "forecast_values": [],
            "baseline_values": [],
            "feature_importance": {},
            "components": {},
            "error": error,
        }
    # Merge CV metrics
    cv = cv_results.get(model_type, {})
    for k in ("mae", "rmse", "mape"):
        if cv.get(k) is not None and not (isinstance(cv[k], float) and np.isnan(cv[k])):
            metrics[k] = float(cv[k])
    mape = metrics.get("mape")
    forecast_accuracy = _compute_forecast_accuracy(mape)
    return {
        "model_name": model.name,
        "model": model_type,
        "metrics": {
            **metrics,
            "forecast_accuracy": forecast_accuracy,
            "accuracy_grade": _accuracy_grade(forecast_accuracy),
        },
        "forecast_values": forecast,
        "baseline_values": baseline,
        "feature_importance": fi,
        "components": comp,
    }


def _safe_metrics(model: BaseForecaster) -> Dict[str, float]:
    try:
        m = model.get_metrics() or {}
        return {k: float(v) for k, v in m.items() if v is not None}
    except Exception as e:
        logger.warning("Failed to get safe metrics: %s", e)
        return {}


# =========================================================================
# Module-level helpers
# =========================================================================

def attach_uplift(forecast: List[Dict[str, Any]], baseline: List[Dict[str, Any]]) -> None:
    """In-place: attach baseline + uplift to each forecast entry."""
    if not forecast or not baseline:
        return
    n = min(len(forecast), len(baseline))
    for i in range(n):
        b = baseline[i]
        f = forecast[i]
        b_val = _safe_float(b.get("forecast"))
        f_val = _safe_float(f.get("forecast"))
        f["baseline"] = b_val
        if b_val:
            f["uplift"] = float((f_val - b_val) / abs(b_val) * 100.0)
        else:
            f["uplift"] = 0.0


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
        if np.isnan(v) or np.isinf(v):
            return default
        return v
    except (TypeError, ValueError):
        return default


def _safe_fi(d: Any) -> Dict[str, float]:
    if not isinstance(d, dict):
        return {}
    return {str(k): _safe_float(v) for k, v in d.items()}


def _safe_dict(d: Any) -> Dict[str, Any]:
    if not isinstance(d, dict):
        return {}
    return to_python(d)


def _build_rankings(cv: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for m, metrics in cv.items():
        mae = metrics.get("mae")
        rmse = metrics.get("rmse")
        mape = metrics.get("mape")
        score = None
        if mae is not None and not (isinstance(mae, float) and np.isnan(mae)):
            try:
                score = float(1.0 / (float(mae) + 1.0))
            except Exception as e:
                logger.warning("Failed to compute ranking score: %s", e)
                score = None
        forecast_accuracy = _compute_forecast_accuracy(mape)
        out.append({
            "model": m,
            "name": m,
            "mae": _safe_float(mae) if mae is not None else None,
            "rmse": _safe_float(rmse) if rmse is not None else None,
            "mape": _safe_float(mape) if mape is not None else None,
            "score": score,
            "forecast_accuracy": forecast_accuracy,
            "accuracy_grade": _accuracy_grade(forecast_accuracy),
        })
    # Rank: valid metrics first (lower MAE is better), then no-metric entries
    valid = [r for r in out if r["mae"] is not None]
    invalid = [r for r in out if r["mae"] is None]
    valid.sort(key=lambda r: r["mae"])
    invalid.sort(key=lambda r: r["model"])
    return valid + invalid


def _build_rankings_from_test(
    test_metrics: Dict[str, Dict[str, float]],
    cv_metrics: Dict[str, Dict[str, float]],
) -> List[Dict[str, Any]]:
    """Build rankings preferring held-out test metrics over CV metrics."""
    out: List[Dict[str, Any]] = []
    for m in set(list(test_metrics.keys()) + list(cv_metrics.keys())):
        tm = test_metrics.get(m, {})
        cv = cv_metrics.get(m, {})
        mae = tm.get("mae") if tm.get("mae") is not None else cv.get("mae")
        rmse = tm.get("rmse") if tm.get("rmse") is not None else cv.get("rmse")
        mape = tm.get("mape") if tm.get("mape") is not None else cv.get("mape")
        r2 = tm.get("r2") if tm.get("r2") is not None else cv.get("r2")
        score = None
        if mae is not None and not (isinstance(mae, float) and np.isnan(mae)):
            try:
                score = float(1.0 / (float(mae) + 1.0))
            except Exception as e:
                logger.warning("Failed to compute test ranking score: %s", e)
                score = None
        forecast_accuracy = _compute_forecast_accuracy(mape)
        out.append({
            "model": m,
            "name": m,
            "mae": _safe_float(mae) if mae is not None else None,
            "rmse": _safe_float(rmse) if rmse is not None else None,
            "mape": _safe_float(mape) if mape is not None else None,
            "r2": _safe_float(r2) if r2 is not None else None,
            "score": score,
            "forecast_accuracy": forecast_accuracy,
            "accuracy_grade": _accuracy_grade(forecast_accuracy),
            "source": "test" if tm.get("mae") is not None else "cv",
            "test_rows": tm.get("test_rows"),
        })
    valid = [r for r in out if r["mae"] is not None]
    invalid = [r for r in out if r["mae"] is None]
    valid.sort(key=lambda r: r["mae"])
    invalid.sort(key=lambda r: r["model"])
    return valid + invalid


def _compute_backtest_metrics(
    forecast_values: List[Dict[str, Any]],
    actuals_df: pd.DataFrame,
    date_col: str,
    value_col: str,
) -> Dict[str, float]:
    """Compute MAE, MAPE, R2 from backtest forecast vs actuals."""
    if not forecast_values or actuals_df.empty:
        return {}
    try:
        actuals: Dict[str, float] = {}
        for _, row in actuals_df.iterrows():
            d = pd.Timestamp(row[date_col]).strftime("%Y-%m-%d")
            actuals[d] = float(row[value_col])
        pred_vals: List[float] = []
        actual_vals: List[float] = []
        for fv in forecast_values:
            d = str(fv.get("date", ""))[:10]
            if d in actuals:
                pred_vals.append(float(fv.get("forecast", 0.0)))
                actual_vals.append(actuals[d])
        if not pred_vals:
            return {}
        preds = np.array(pred_vals)
        acts = np.array(actual_vals)
        diff = preds - acts
        mae = float(np.mean(np.abs(diff)))
        rmse = float(np.sqrt(np.mean(diff ** 2)))
        denom = np.where(np.abs(acts) < 1e-9, 1e-9, np.abs(acts))
        mape = float(np.mean(np.abs(diff) / denom) * 100.0)
        ss_res = float(np.sum(diff ** 2))
        ss_tot = float(np.sum((acts - acts.mean()) ** 2))
        r2 = 1 - ss_res / ss_tot if ss_tot != 0 else None
        forecast_accuracy = _compute_forecast_accuracy(mape)
        return {
            "mae": mae,
            "rmse": rmse,
            "mape": mape,
            "r2": r2,
            "forecast_accuracy": forecast_accuracy,
            "accuracy_grade": _accuracy_grade(forecast_accuracy),
            "backtest_rows": len(pred_vals),
        }
    except Exception as e:
        logger.warning("Failed to compute backtest metrics: %s", e)
        return {}


def _build_summary(
    per_model: Dict[str, Dict[str, Any]],
    ensemble: Optional[Dict[str, Any]],
    horizon: int,
) -> Dict[str, Any]:
    fc: List[Dict[str, Any]] = []
    base: List[Dict[str, Any]] = []
    if ensemble and ensemble.get("forecast_values"):
        fc = ensemble["forecast_values"]
        base = ensemble.get("baseline_values") or []
    else:
        # Pick the first model with a forecast
        for v in per_model.values():
            if v.get("forecast_values"):
                fc = v["forecast_values"]
                base = v.get("baseline_values") or []
                break
    if not fc:
        return {
            "total_forecast": 0.0, "total_baseline": 0.0,
            "total_uplift": 0.0, "uplift_pct": 0.0,
            "avg_daily_forecast": 0.0, "horizon": horizon,
        }
    total_fc = float(sum(_safe_float(v.get("forecast", 0.0)) for v in fc))
    total_base = float(sum(_safe_float(v.get("forecast", 0.0)) for v in base)) if base else total_fc
    total_uplift = total_fc - total_base
    uplift_pct = (total_uplift / abs(total_base) * 100.0) if total_base else 0.0
    return {
        "total_forecast": total_fc,
        "total_baseline": total_base,
        "total_uplift": total_uplift,
        "uplift_pct": uplift_pct,
        "avg_daily_forecast": total_fc / max(1, len(fc)),
        "horizon": horizon,
    }


def _compute_factor_contributions(
    best_model: Optional[BaseForecaster],
    exog_data: Optional[Dict[str, pd.DataFrame]],
    horizon: int,
    baseline_forecast: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if best_model is None or not exog_data or not baseline_forecast:
        return {}
    contributions: Dict[str, Any] = {}
    baseline_vals = [f["forecast"] for f in baseline_forecast]
    factor_names = [k for k in exog_data if k in ("media_plan", "promotions", "holidays", "events", "weather", "competitor", "economic")]
    for name in factor_names:
        try:
            single_exog = {name: exog_data[name]}
            fc = best_model.forecast(horizon, exog_data=single_exog)
            fc_vals = [f["forecast"] for f in fc]
            per_step = [float(fc_vals[i] - baseline_vals[i]) for i in range(horizon)]
            total_contribution = float(sum(per_step))
            contributions[name] = {
                "total_contribution": total_contribution,
                "average_contribution": total_contribution / horizon if horizon > 0 else 0.0,
                "per_step": per_step,
                "direction": "positive" if total_contribution > 0 else "negative",
            }
        except Exception as e:
            logger.debug("Factor contribution for %s failed: %s", name, e)
    return contributions


def _build_external_analysis(
    exog_data: Optional[Dict[str, pd.DataFrame]],
    per_model: Dict[str, Dict[str, Any]],
    sales_df: Optional[pd.DataFrame] = None,
    date_col: str = "date",
    value_col: str = "value",
) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    lag_analysis: Dict[str, Dict[str, Any]] = {}
    if not exog_data:
        return out

    if sales_df is None or len(sales_df) < 20:
        _lag_default = {"lag": 0, "correlation": None, "strength": "", "message": "Not enough data"}
    else:
        _lag_default = None

    def _lag_for(exog_name: str, exog: pd.DataFrame) -> Dict[str, Any]:
        if _lag_default:
            return _lag_default
        try:
            return ModelSelector().compute_lag_analysis(
                sales_df, date_col, value_col, exog, exog_name  # type: ignore[arg-type]
            )
        except Exception:
            return {"lag": 0, "correlation": None, "strength": "", "message": "Analysis failed"}

    if "media_plan" in exog_data and exog_data["media_plan"] is not None:
        mp = exog_data["media_plan"]
        lag_analysis["media_plan"] = _lag_for("media_plan", mp)
        if "media_spend" in mp.columns:
            out["media_plan_impact"] = {
                "total_spend": float(pd.to_numeric(mp["media_spend"], errors="coerce").sum()),
                "rows": int(len(mp)),
            }
    if "promotions" in exog_data and exog_data["promotions"] is not None:
        p = exog_data["promotions"]
        lag_analysis["promotions"] = _lag_for("promotions", p)
        if "discount" in p.columns:
            out["promotion_impact"] = {
                "total_discount": float(pd.to_numeric(p["discount"], errors="coerce").sum()),
                "rows": int(len(p)),
            }
    if "holidays" in exog_data and exog_data["holidays"] is not None:
        h = exog_data["holidays"]
        lag_analysis["holidays"] = _lag_for("holidays", h)
        if "holiday_impact" in h.columns:
            out["holiday_impact"] = {
                "total_impact": float(pd.to_numeric(h["holiday_impact"], errors="coerce").sum()),
                "rows": int(len(h)),
            }
    if "events" in exog_data and exog_data["events"] is not None:
        e = exog_data["events"]
        lag_analysis["events"] = _lag_for("events", e)
        out["event_impact"] = {"rows": int(len(e))}
    if "weather" in exog_data and exog_data["weather"] is not None:
        w = exog_data["weather"]
        lag_analysis["weather"] = _lag_for("weather", w)
        out["weather_impact"] = {"rows": int(len(w))}
    if "competitor" in exog_data and exog_data["competitor"] is not None:
        c = exog_data["competitor"]
        lag_analysis["competitor"] = _lag_for("competitor", c)
        out["price_elasticity"] = None  # not enough info to estimate
        out["competitor_impact"] = {"rows": int(len(c))}
    if "economic" in exog_data and exog_data["economic"] is not None:
        econ = exog_data["economic"]
        lag_analysis["economic"] = _lag_for("economic", econ)
        out["economic_impact"] = {
            "rows": int(len(econ)),
            "columns": [c for c in econ.columns if c != "date"],
        }
    if lag_analysis:
        out["lag_analysis"] = lag_analysis
    return out
