"""Main forecasting orchestrator: runs models, builds ensemble, persists results.

This is the single entry point used by the API to run a forecast. It:
  * Iterates over the requested models, fitting each in isolation
  * Falls back gracefully if a single model fails
  * Computes cross-validated MAE / RMSE / MAPE for model selection
  * Builds an optional weighted ensemble
  * Computes baseline forecasts and uplift
  * Returns a JSON-safe dict that the storage layer can persist
"""
from __future__ import annotations

import logging
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..core.utils import to_python
from .model_selector import ModelSelector
from .models.base import BaseForecaster

logger = logging.getLogger(__name__)


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


class ForecasterService:
    """High-level orchestration of forecast jobs."""

    def __init__(self) -> None:
        self.selector = ModelSelector()

    # ----------------------------------------------------------------- main
    def run(
        self,
        sales_df: pd.DataFrame,
        request: Dict[str, Any],
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> Dict[str, Any]:
        """Run a forecast end-to-end. Returns a JSON-safe dict.

        `request` is a ForecastRequest.model_dump() (Pydantic v2).  Exog
        data is a dict of already-normalized DataFrames keyed by type
        (sales / media_plan / promotions / holidays / events / weather /
        competitor / economic)."""
        date_col = request.get("date_column", "date")
        value_col = request.get("target_column", "value")
        horizon = int(request.get("horizon", 30))
        models = request.get("models") or ["prophet"]
        params = request.get("parameters") or {}
        ensemble_models = request.get("ensemble_models") or []
        ensemble_weights = request.get("ensemble_weights") or None

        # 1) Cross-validate each requested model in parallel logic (sequential here)
        cv_results: Dict[str, Dict[str, float]] = {}
        for m in models:
            try:
                cv_results[m] = self.selector.cross_validate(
                    sales_df, date_col, value_col, m, params, horizon=min(7, horizon)
                )
            except Exception as e:
                logger.warning("CV error for %s: %s", m, e)
                cv_results[m] = {"mae": None, "rmse": None, "mape": None, "error": str(e)}

        # 2) Fit + forecast each model on full data
        per_model: Dict[str, Dict[str, Any]] = {}
        successful_models: List[BaseForecaster] = []
        for m in models:
            try:
                model = self.selector.get_model(m, params)
                model.fit(sales_df, date_col, value_col, exog_data=exog_data or {})
                forecast = model.forecast(horizon, exog_data=exog_data)
                baseline = model.get_baseline(horizon, exog_data=exog_data)
                attach_uplift(forecast, baseline)
                per_model[m] = {
                    "model_name": model.name,
                    "model": m,
                    "metrics": {**self._model_metrics(model),
                                **{k: v for k, v in cv_results.get(m, {}).items()
                                   if k in ("mae", "rmse", "mape")}},
                    "forecast_values": forecast,
                    "baseline_values": baseline,
                    "feature_importance": _safe_fi(model.get_feature_importance()),
                    "components": _safe_dict(model.get_components()),
                }
                successful_models.append(model)
            except Exception as e:
                logger.error("Model %s failed: %s\n%s", m, e, traceback.format_exc())
                per_model[m] = {
                    "model_name": m,
                    "model": m,
                    "metrics": {"error": str(e)},
                    "forecast_values": [],
                    "baseline_values": [],
                    "feature_importance": {},
                    "components": {},
                    "error": str(e),
                }

        # 3) Build rankings from CV MAE
        rankings = _build_rankings(cv_results)

        # 4) Ensemble
        ensemble_result: Optional[Dict[str, Any]] = None
        if ensemble_models and len(ensemble_models) >= 2:
            try:
                # Filter ensemble_models to ones that succeeded
                chosen = [m for m in ensemble_models if m in per_model
                          and not per_model[m].get("error")]
                if len(chosen) >= 2:
                    members: List[BaseForecaster] = []
                    for m in chosen:
                        try:
                            inst = self.selector.get_model(m, params)
                            inst.fit(sales_df, date_col, value_col, exog_data=exog_data or {})
                            members.append(inst)
                        except Exception as e:
                            logger.warning("Ensemble member %s re-fit failed: %s", m, e)
                    if len(members) >= 2:
                        # Default weights: inverse MAE if available, else equal
                        if ensemble_weights and len(ensemble_weights) == len(members):
                            weights = list(ensemble_weights)
                        else:
                            weights = []
                            for m in chosen[:len(members)]:
                                cv = cv_results.get(m, {})
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
                                    "model_name": per_model[m].get("model_name", m),
                                    "metrics": per_model[m].get("metrics", {}),
                                    "forecast_values": per_model[m].get("forecast_values", []),
                                    "baseline_values": per_model[m].get("baseline_values", []),
                                    "feature_importance": per_model[m].get("feature_importance", {}),
                                    "components": per_model[m].get("components", {}),
                                }
                                for m in chosen[:len(members)]
                            ],
                        }
            except Exception as e:
                logger.warning("Ensemble build failed: %s", e)
                ensemble_result = None

        # 5) Best model
        best_model: Optional[str] = None
        if rankings:
            best_model = rankings[0]["model"]

        # 6) Summary
        summary = _build_summary(per_model, ensemble_result, horizon)

        # 7) External factor analysis
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
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        return to_python(result)

    # ----------------------------------------------------------------- helpers
    @staticmethod
    def _model_metrics(model: BaseForecaster) -> Dict[str, float]:
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
