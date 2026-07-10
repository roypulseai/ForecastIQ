"""Forecast CRUD endpoints.

The /forecast POST endpoint supports two modes:
  * Synchronous (default, for small/quick jobs): returns the full response when done.
  * Async (?async=true): returns {job_id} immediately; the client polls
    /forecast/jobs/{job_id} for status and /forecast/jobs/{job_id}/result for the
    final payload.

Async is recommended for large datasets (50k+ rows) or when running 5+ models.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import ValidationError

from ...core.config import settings
from ...core.jobs import get_job_manager
from ...core.storage import FileMetadataStore
from ...core.utils import to_python
from ...schemas.common import DataStatus
from ...schemas.forecast import (
    ForecastDetail,
    ForecastListResponse,
    ForecastRequest,
    ForecastResponse,
    ForecastSummary,
    ModelRanking,
)
from ...services.auto_events import AutoEventDetector
from ...services.data_processor import DataProcessor, _infer_column_types
from ...services.forecaster import ForecasterService
from ...services.model_selector import ModelSelector

logger = logging.getLogger(__name__)

router = APIRouter()
storage = FileMetadataStore()
processor = DataProcessor()
service = ForecasterService()


def _gather_exog(
    request: ForecastRequest,
    sales_df: Optional[pd.DataFrame] = None,
    date_col: str = "date",
    value_col: str = "value",
) -> Dict[str, Any]:
    """Pull all requested external data from storage into a dict keyed by
    internal name. Returns a DataFrame dict ready for the models.

    When `auto_detect_events=True`, generates a synthetic events DataFrame
    using the AutoEventDetector and adds it under the 'holidays' key so it
    flows into the same exogenous pipeline (for SARIMAX, LightGBM, XGBoost,
    and Prophet).
    """
    out: Dict[str, Any] = {}
    type_to_key = {
        "media_plan": "media_plan",
        "promotions": "promotions",
        "holidays": "holidays",
        "events": "events",
        "weather": "weather",
        "competitor": "competitor",
        "economic": "economic",
    }
    flags = {
        "media_plan": request.include_media_plan,
        "promotions": request.include_promotions,
        "holidays": request.include_holidays,
        "events": request.include_events,
        "weather": request.include_weather,
        "competitor": request.include_competitor,
        "economic": request.include_economic,
    }
    for ft, key in type_to_key.items():
        if not flags.get(ft, False):
            continue
        files = storage.find_files_by_type(ft)
        if not files:
            continue
        df = storage.get_dataframe(files[0]["file_id"])
        if df is not None and not df.empty:
            out[key] = df

    # Auto-detect events: generate synthetic events from holidays + feasts
    if request.auto_detect_events and sales_df is not None and not sales_df.empty:
        country = request.auto_event_country or request.country or "US"
        region_col = None
        # Detect region column from column types (passed through validation)
        if request.auto_event_regions:
            pass  # User specified explicit regions; we still compute per-region impact

        try:
            # Find region column from sales_df column types
            col_types = _infer_column_types(sales_df)
            for col, ctype in col_types.items():
                if ctype == "region":
                    region_col = col
                    break

            detector = AutoEventDetector(
                country=country,
                sales_df=sales_df,
                date_col=date_col,
                value_col=value_col,
                region_col=region_col,
            )
            events_df = detector.run(
                start_date=pd.to_datetime(sales_df[date_col]).min().date(),
                end_date=pd.to_datetime(sales_df[date_col]).max().date(),
            )

            if events_df is not None and not events_df.empty:
                # Merge auto-detected events into existing holidays if present,
                # otherwise create a new entry
                events_df = events_df.rename(columns={"holiday_name": "name",
                                                       "holiday_type": "type"})
                if "holidays" in out and out["holidays"] is not None:
                    existing = out["holidays"]
                    combined = pd.concat([existing, events_df], ignore_index=True)
                    combined = combined.drop_duplicates(subset=["date"]).sort_values("date")
                    out["holidays"] = combined
                else:
                    out["holidays"] = events_df
                logger.info(
                    "Auto-detected %d event dates for %s (region_col=%s)",
                    len(events_df), country, region_col,
                )
            else:
                logger.info("No auto-detected events for %s", country)
        except Exception as e:
            logger.warning("Auto-event detection failed (continuing): %s", e)

    return out


def _build_response_from_result(
    result: Dict[str, Any], forecast_id: str
) -> Dict[str, Any]:
    """Build the ForecastResponse payload from a service.run() result dict."""
    rankings = [
        ModelRanking(
            model=r.get("model", ""),
            name=r.get("name"),
            mae=r.get("mae"),
            rmse=r.get("rmse"),
            mape=r.get("mape"),
            score=r.get("score"),
        )
        for r in (result.get("model_rankings") or [])
    ]
    summary = result.get("summary") or {}
    summary_obj = ForecastSummary(
        total_forecast=float(summary.get("total_forecast", 0.0) or 0.0),
        total_baseline=float(summary.get("total_baseline", 0.0) or 0.0),
        total_uplift=float(summary.get("total_uplift", 0.0) or 0.0),
        uplift_pct=float(summary.get("uplift_pct", 0.0) or 0.0),
        avg_daily_forecast=float(summary.get("avg_daily_forecast", 0.0) or 0.0),
    )
    response = ForecastResponse(
        id=forecast_id,
        forecast_id=forecast_id,
        status=DataStatus.READY,
        message="Forecast completed successfully",
        best_model=result.get("best_model"),
        model_rankings=rankings,
        summary=summary_obj,
    )
    out = to_python(response.model_dump())
    # Augment with extras the schema doesn't capture
    out["test_metrics"] = result.get("test_metrics") or {}
    out["saved_model"] = result.get("saved_model")
    out["downsample_info"] = result.get("downsample_info")
    out["ensemble"] = result.get("ensemble")
    return out


@router.post("/forecast")
async def create_forecast(
    request: ForecastRequest,
    async_mode: bool = Query(False, alias="async", description="Run asynchronously and return job_id"),
) -> Dict[str, Any]:
    return await _create_forecast_impl(
        request=request,
        async_mode=async_mode,
        storage=storage,
        processor=processor,
        service=service,
    )


async def _create_forecast_impl(
    request: ForecastRequest,
    *,
    async_mode: bool,
    storage: FileMetadataStore,
    processor: DataProcessor,
    service: ForecasterService,
) -> Dict[str, Any]:
    """Reusable forecast-create handler. Used by both internal /api/v1/forecast
    and public /v1/forecast routes."""
    sales_entry = storage.find_sales_file()
    if sales_entry is None:
        raise HTTPException(status_code=400, detail="No sales file uploaded")
    sales_df = storage.get_dataframe(sales_entry["file_id"])
    if sales_df is None or sales_df.empty:
        raise HTTPException(status_code=400, detail="Sales data is empty")

    # Clamp backtest_overlap to 20% of unique dates
    try:
        n_dates = int(sales_df["date"].nunique())
    except Exception:
        n_dates = len(sales_df)
    max_backtest = max(0, int(n_dates * 0.2))
    if request.backtest_overlap > max_backtest:
        request.backtest_overlap = max_backtest

    try:
        request_dict = request.model_dump(mode="json")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {e}")

    date_col = request.date_column
    value_col = request.target_column
    exog_data = _gather_exog(
        request,
        sales_df=sales_df,
        date_col=date_col,
        value_col=value_col,
    )

    if async_mode:
        jm = get_job_manager()

        def _task() -> Dict[str, Any]:
            result = service.run(sales_df, request_dict, exog_data=exog_data)
            result["data_file_id"] = sales_entry["file_id"]
            forecast_id = storage.save_forecast(result)
            return {"result": result, "forecast_id": forecast_id}

        job_id = jm.submit(
            job_type="forecast",
            func=_task,
            request=request_dict,
        )
        return {
            "job_id": job_id,
            "status": "pending",
            "message": "Forecast submitted. Poll /forecast/jobs/{job_id} for status.",
        }

    try:
        result = service.run(sales_df, request_dict, exog_data=exog_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Forecast failed")
        raise HTTPException(status_code=500, detail=f"Forecast failed: {e}")

    result["data_file_id"] = sales_entry["file_id"]
    forecast_id = storage.save_forecast(result)
    return _build_response_from_result(result, forecast_id)


@router.get("/forecast/jobs/{job_id}")
async def get_job_status(job_id: str) -> Dict[str, Any]:
    jm = get_job_manager()
    info = jm.status(job_id)
    if info is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return info


@router.get("/forecast/jobs/{job_id}/result")
async def get_job_result(job_id: str) -> Dict[str, Any]:
    """Blocking endpoint: waits for the job to complete and returns the full
    forecast response. If the job is already done, returns immediately.
    Times out after `timeout` seconds (default 300s)."""
    jm = get_job_manager()
    job = jm.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status.value == "completed":
        # Already done — return the forecast_id; client fetches the full detail
        return {"job_id": job_id, "status": "completed", "result": job.result}
    if job.status.value == "failed":
        raise HTTPException(status_code=500, detail=job.error or "Job failed")

    # Otherwise, block until done (or timeout)
    import asyncio
    timeout = 300
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: jm.result(job_id, timeout=timeout)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Re-read the job after completion
    job = jm.get(job_id)
    return {"job_id": job_id, "status": job.status.value, "result": job.result}


@router.get("/forecast/jobs")
async def list_jobs(
    job_type: Optional[str] = None, limit: int = Query(20, ge=1, le=100)
) -> Dict[str, Any]:
    jm = get_job_manager()
    return {"items": jm.list_jobs(job_type=job_type, limit=limit)}


@router.get("/forecast/{forecast_id}")
async def get_forecast(forecast_id: str) -> Dict[str, Any]:
    rec = storage.get_forecast(forecast_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Forecast not found")
    return to_python(rec)


@router.get("/forecasts")
async def list_forecasts(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)) -> Dict[str, Any]:
    items = storage.list_forecasts()
    return to_python({
        "items": items[offset:offset + limit],
        "total": len(items),
        "limit": limit,
        "offset": offset,
    })


@router.delete("/forecast/{forecast_id}")
async def delete_forecast(forecast_id: str) -> Dict[str, Any]:
    ok = storage.delete_forecast(forecast_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Forecast not found")
    return {"message": "Forecast deleted", "forecast_id": forecast_id}


@router.post("/forecast/{forecast_id}/what-if")
async def what_if_forecast(
    forecast_id: str,
    factor_adjustments: Dict[str, Any],
) -> Dict[str, Any]:
    """Run a what-if scenario by adjusting external factor values.

    Body example:
    ```json
    {
      "media_plan": {"media_spend_multiplier": 1.5},
      "promotions": {"discount_multiplier": 2.0}
    }
    ```

    This loads the original forecast's data, modifies the external factors
    per the adjustments, re-fits the best model, and returns the scenario
    forecast alongside the original for comparison.
    """
    rec = storage.get_forecast(forecast_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Forecast not found")

    request_dict = rec.get("request", {})
    data_file_id = rec.get("data_file_id")
    if not data_file_id:
        raise HTTPException(status_code=400, detail="No data file associated with this forecast")

    sales_df = storage.get_dataframe(data_file_id)
    if sales_df is None or sales_df.empty:
        raise HTTPException(status_code=400, detail="Sales data not found")

    date_col = request_dict.get("date_column", "date")
    value_col = request_dict.get("target_column", "value")
    horizon = int(request_dict.get("horizon", 30))
    best_model_key = rec.get("best_model") or "prophet"
    models = request_dict.get("models") or ["prophet"]
    if best_model_key not in models:
        models = [best_model_key]
    params = request_dict.get("parameters") or {}

    # Rebuild original exog data from storage (same logic as _gather_exog)
    from pydantic import BaseModel

    class _FakeRequest(BaseModel):
        include_media_plan: bool = False
        include_promotions: bool = False
        include_holidays: bool = False
        include_events: bool = False
        include_weather: bool = False
        include_competitor: bool = False
        include_economic: bool = False
        auto_detect_events: bool = False
        auto_event_country: Optional[str] = None
        auto_event_regions: Optional[List[str]] = None
        country: Optional[str] = None
        date_column: str = "date"
        target_column: str = "value"

    fake_req = _FakeRequest(**{
        k: request_dict.get(k, False)
        for k in ("include_media_plan", "include_promotions", "include_holidays",
                  "include_events", "include_weather", "include_competitor",
                  "include_economic", "auto_detect_events", "auto_event_country",
                  "auto_event_regions", "country", "date_column", "target_column")
    })
    exog_data = _gather_exog(fake_req, sales_df=sales_df, date_col=date_col, value_col=value_col)  # type: ignore[arg-type]

    # Apply factor adjustments
    for factor, adjustments in factor_adjustments.items():
        if factor not in exog_data or exog_data[factor] is None:
            continue
        df = exog_data[factor].copy()
        numeric_cols = [c for c in df.columns if c != "date" and pd.api.types.is_numeric_dtype(df[c])]
        for col in numeric_cols:
            multiplier_key = f"{col}_multiplier"
            if multiplier_key in adjustments:
                mult = float(adjustments[multiplier_key])
                df[col] = pd.to_numeric(df[col], errors="coerce") * mult
            add_key = f"{col}_add"
            if add_key in adjustments:
                add_val = float(adjustments[add_key])
                df[col] = pd.to_numeric(df[col], errors="coerce") + add_val
            set_key = f"{col}_set"
            if set_key in adjustments:
                df[col] = float(adjustments[set_key])
        exog_data[factor] = df

    # Fit the best model with modified exog
    selector = ModelSelector()
    try:
        model = selector.get_model(best_model_key, params)
        model.fit(sales_df, date_col, value_col, exog_data=exog_data or {})
        forecast = model.forecast(horizon, exog_data=exog_data)
        baseline = model.get_baseline(horizon, exog_data=exog_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"What-if model failed: {e}")

    # Get original forecast for comparison (from saved result)
    original_forecast: List[Dict[str, Any]] = []
    original_baseline: List[Dict[str, Any]] = []
    if rec.get("results") and best_model_key in rec["results"]:
        original_forecast = rec["results"][best_model_key].get("forecast_values", [])
        original_baseline = rec["results"][best_model_key].get("baseline_values", [])
    elif rec.get("ensemble"):
        original_forecast = rec["ensemble"].get("forecast_values", [])
        original_baseline = rec["ensemble"].get("baseline_values", [])

    return {
        "forecast_id": forecast_id,
        "best_model": best_model_key,
        "horizon": horizon,
        "original_forecast": original_forecast,
        "scenario_forecast": forecast,
        "original_baseline": original_baseline,
        "scenario_baseline": baseline,
        "factors_adjusted": list(factor_adjustments.keys()),
        "adjustments": factor_adjustments,
    }
