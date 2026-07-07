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
from ...services.data_processor import DataProcessor
from ...services.forecaster import ForecasterService

logger = logging.getLogger(__name__)

router = APIRouter()
storage = FileMetadataStore()
processor = DataProcessor()
service = ForecasterService()


def _gather_exog(request: ForecastRequest) -> Dict[str, Any]:
    """Pull all requested external data from storage into a dict keyed by
    internal name. Returns a DataFrame dict ready for the models."""
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
    return to_python(response.model_dump())


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

    try:
        request_dict = request.model_dump(mode="json")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {e}")

    exog_data = _gather_exog(request)

    if async_mode:
        sales_copy = sales_df.copy()
        exog_copy = {k: v.copy() for k, v in (exog_data or {}).items()}
        jm = get_job_manager()

        def _task() -> Dict[str, Any]:
            result = service.run(sales_copy, request_dict, exog_data=exog_copy)
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
