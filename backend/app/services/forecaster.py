"""Main forecasting orchestrator: runs models, builds ensemble, persists results.

This is the single entry point used by the API to run a forecast. It:
  * Iterates over the requested models, fitting each in isolation
  * Falls back gracefully if a single model fails
  * Computes cross-validated MAE / RMSE / MAPE for model selection
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
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..core.utils import to_python
from .data_processor import DataProcessor
from .model_selector import ModelSelector
from .models.base import BaseForecaster

logger = logging.getLogger(__name__)


# Tunable thresholds
MAX_PARALLEL_WORKERS = max(2, min(os.cpu_count() or 4, 4))
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
                progress_cb=lambda p, m: jm._jobs.__setitem__(
                    jm._jobs.get(list(jm._jobs.keys())[-1], type("X", (), {"progress": 0.0, "message": ""})()).job_id
                    if False else "",
                    None,
                ) if False else None,
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
        date_col = request.get("date_column", "date")
        value_col = request.get("target_column", "value")
        horizon = int(request.get("horizon", 30))
        models = request.get("models") or ["prophet"]
        params = request.get("parameters") or {}
        ensemble_models = request.get("ensemble_models") or []
        ensemble_weights = request.get("ensemble_weights") or None

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

        # ---- 1) Cross-validate each requested model in parallel ----
        cv_results: Dict[str, Dict[str, float]] = {}
        cv_workers = min(len(models), MAX_PARALLEL_WORKERS)
        if cv_workers > 1:
            with ThreadPoolExecutor(max_workers=cv_workers) as ex:
                fut_to_model = {
                    ex.submit(
                        self.selector.cross_validate,
                        sales_df, date_col, value_col, m, params,
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
                        sales_df, date_col, value_col, m, params, horizon=min(7, horizon)
                    )
                except Exception as e:
                    logger.warning("CV error for %s: %s", m, e)
                    cv_results[m] = {"mae": None, "rmse": None, "mape": None, "error": str(e)}

        if progress_cb:
            progress_cb(0.20, "Cross-validation complete")

        # ---- 2) Fit + forecast each model in parallel ----
        per_model: Dict[str, Dict[str, Any]] = {}
        n_models = len(models)
        completed = 0
        fit_workers = min(n_models, MAX_PARALLEL_WORKERS)
        if fit_workers > 1:
            with ThreadPoolExecutor(max_workers=fit_workers) as ex:
                fut_to_model = {
                    ex.submit(
                        _fit_and_forecast_one,
                        m, params, sales_df, date_col, value_col,
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
                    m, params, sales_df, date_col, value_col, horizon, exog_data
                )
                per_model[m] = _assemble_model_result(m, result, cv_results)
                completed += 1
                if progress_cb:
                    progress_cb(0.20 + 0.55 * (completed / n_models), f"Trained {completed}/{n_models} models")

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
                        ensemble_result = {
                            "models_used": [mm.name for mm in members],
                            "weights": ens.weights,
                            "forecast_values": ens_fc,
                            "baseline_values": ens_base,
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
        best_model: Optional[str] = rankings[0]["model"] if rankings else None
        summary = _build_summary(per_model, ensemble_result, horizon)
        external = _build_external_analysis(exog_data, per_model)

        result: Dict[str, Any] = {
            "name": request.get("name", "Forecast"),
            "request": request,
            "results": per_model,
            "model_rankings": rankings,
            "best_model": best_model,
            "ensemble": ensemble_result,
            "summary": summary,
            "external_factor_analysis": external,
            "downsample_info": downsample_info,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        if progress_cb:
            progress_cb(1.0, "Done")
        return to_python(result)

    # ----------------------------------------------------------------- helpers
    @staticmethod
    def _model_metrics(model: BaseForecaster) -> Dict[str, float]:
        try:
            m = model.get_metrics() or {}
            return {k: float(v) for k, v in m.items() if v is not None}
        except Exception:
            return {}


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
    return {
        "model_name": model.name,
        "model": model_type,
        "metrics": metrics,
        "forecast_values": forecast,
        "baseline_values": baseline,
        "feature_importance": fi,
        "components": comp,
    }


def _safe_metrics(model: BaseForecaster) -> Dict[str, float]:
    try:
        m = model.get_metrics() or {}
        return {k: float(v) for k, v in m.items() if v is not None}
    except Exception:
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
            except Exception:
                score = None
        out.append({
            "model": m,
            "name": m,
            "mae": _safe_float(mae) if mae is not None else None,
            "rmse": _safe_float(rmse) if rmse is not None else None,
            "mape": _safe_float(mape) if mape is not None else None,
            "score": score,
        })
    # Rank: valid metrics first (lower MAE is better), then no-metric entries
    valid = [r for r in out if r["mae"] is not None]
    invalid = [r for r in out if r["mae"] is None]
    valid.sort(key=lambda r: r["mae"])
    invalid.sort(key=lambda r: r["model"])
    return valid + invalid


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


def _build_external_analysis(
    exog_data: Optional[Dict[str, pd.DataFrame]],
    per_model: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if not exog_data:
        return out
    if "media_plan" in exog_data and exog_data["media_plan"] is not None:
        mp = exog_data["media_plan"]
        if "media_spend" in mp.columns:
            out["media_plan_impact"] = {
                "total_spend": float(pd.to_numeric(mp["media_spend"], errors="coerce").sum()),
                "rows": int(len(mp)),
            }
    if "promotions" in exog_data and exog_data["promotions"] is not None:
        p = exog_data["promotions"]
        if "discount" in p.columns:
            out["promotion_impact"] = {
                "total_discount": float(pd.to_numeric(p["discount"], errors="coerce").sum()),
                "rows": int(len(p)),
            }
    if "holidays" in exog_data and exog_data["holidays"] is not None:
        h = exog_data["holidays"]
        if "holiday_impact" in h.columns:
            out["holiday_impact"] = {
                "total_impact": float(pd.to_numeric(h["holiday_impact"], errors="coerce").sum()),
                "rows": int(len(h)),
            }
    if "events" in exog_data and exog_data["events"] is not None:
        e = exog_data["events"]
        out["event_impact"] = {
            "rows": int(len(e)),
        }
    if "weather" in exog_data and exog_data["weather"] is not None:
        w = exog_data["weather"]
        out["weather_impact"] = {"rows": int(len(w))}
    if "competitor" in exog_data and exog_data["competitor"] is not None:
        c = exog_data["competitor"]
        out["price_elasticity"] = None  # not enough info to estimate
        out["competitor_impact"] = {"rows": int(len(c))}
    if "economic" in exog_data and exog_data["economic"] is not None:
        econ = exog_data["economic"]
        out["economic_impact"] = {
            "rows": int(len(econ)),
            "columns": [c for c in econ.columns if c != "date"],
        }
    return out
