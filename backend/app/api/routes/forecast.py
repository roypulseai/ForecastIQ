"""Forecast CRUD endpoints."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import ValidationError

from ...core.config import settings
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


@router.post("/forecast")
async def create_forecast(request: ForecastRequest) -> Dict[str, Any]:
    # Find sales file
    sales_entry = storage.find_sales_file()
    if sales_entry is None:
        raise HTTPException(status_code=400, detail="No sales file uploaded")
    sales_df = storage.get_dataframe(sales_entry["file_id"])
    if sales_df is None or sales_df.empty:
        raise HTTPException(status_code=400, detail="Sales data is empty")

    # Normalize request dict — use mode="json" so Enum values become their .value (e.g. "wma")
    try:
        request_dict = request.model_dump(mode="json")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {e}")

    exog_data = _gather_exog(request)

    try:
        result = service.run(sales_df, request_dict, exog_data=exog_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Forecast failed")
        raise HTTPException(status_code=500, detail=f"Forecast failed: {e}")

    # Persist
    forecast_id = storage.save_forecast(result)

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


@router.get("/forecast/{forecast_id}")
async def get_forecast(forecast_id: str) -> Dict[str, Any]:
    rec = storage.get_forecast(forecast_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Forecast not found")
    return to_python(rec)


@router.get("/forecasts")
async def list_forecasts() -> Dict[str, Any]:
    items = storage.list_forecasts()
    return to_python({"items": items, "total": len(items)})


@router.delete("/forecast/{forecast_id}")
async def delete_forecast(forecast_id: str) -> Dict[str, Any]:
    ok = storage.delete_forecast(forecast_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Forecast not found")
    return {"message": "Forecast deleted", "forecast_id": forecast_id}
