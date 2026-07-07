"""Public API at /v1/* — versioned, API-key-authenticated, rate-limited.

This is the surface other tools / notebooks / scripts use to interact
with ForecastIQ programmatically. The internal UI uses /api/v1/* with
no auth (relying on the SPA's session).

The endpoints mirror the internal ones, but with:
    * `require_api_key` dependency (Authorization: Bearer <key> or X-API-Key)
    * Rate limits per tier
    * Clean, documented request/response schemas
    * Pagination conventions
    * OpenAPI tags grouped under "Public API"

What's exposed
--------------
    * Sales data upload + list/delete/get + row fetch
    * Analysis (analyze sales file -> characteristics + recommendations)
    * Forecast (create / get / list / delete)
    * Async job status (for long-running forecasts)
    * Model registry (list / train+save / upload / download / forecast with saved)

What's NOT exposed
-------------------
    * Templates download (static — use the /templates/* static mount)
    * Health check (use /api/v1/health on the internal API)
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Path, Query, UploadFile

from ..core.api_keys import (
    ApiKeyRecord,
    ApiKeyTier,
    generate_api_key,
)
from ..core.auth import require_api_key
from ..core.storage import FileMetadataStore
from ..core.utils import to_python
from ..schemas.forecast import (
    ForecastDetail,
    ForecastListResponse,
    ForecastRequest,
    ForecastResponse,
)
from ..schemas.common import FILE_TYPE_VALUES
from ..services.data_processor import DataProcessor
from ..services.forecaster import ForecasterService

logger = logging.getLogger(__name__)


def build_public_router() -> APIRouter:
    """Build the /v1 public API router. Returned router is meant to be
    mounted with prefix='/v1' on the FastAPI app."""
    r = APIRouter(
        prefix="",
        tags=["Public API"],
        responses={
            401: {"description": "Missing or invalid API key"},
            429: {"description": "Rate limit exceeded"},
        },
    )

    storage = FileMetadataStore()
    processor = DataProcessor()
    service = ForecasterService()

    # ------------------------------------------------------------------
    # Files
    # ------------------------------------------------------------------
    @r.post(
        "/files/upload/{file_type}",
        summary="Upload a data file",
        description=(
            "Upload a CSV or Excel file for one of the supported types: "
            "`sales`, `media_plan`, `promotions`, `holidays`, `events`, "
            "`weather`, `competitor`, `economic`. The response contains "
            "the `file_id` you'll need for analysis and forecasting."
        ),
        response_model=Dict[str, Any],
    )
    async def upload_file(
        file_type: str = Path(..., description="One of: " + ", ".join(FILE_TYPE_VALUES)),
        file: UploadFile = File(...),
        _key: ApiKeyRecord = Depends(require_api_key),
    ):
        if file_type not in FILE_TYPE_VALUES:
            raise HTTPException(400, f"Invalid file_type. Allowed: {FILE_TYPE_VALUES}")
        # Reuse the existing upload route's body via internal helper
        from .routes.upload import _process_and_save
        return await _process_and_save(file_type, file, storage, processor)

    @r.get(
        "/files",
        summary="List uploaded files",
        response_model=Dict[str, Any],
    )
    async def list_files(
        file_type: Optional[str] = Query(None, description="Filter by file type"),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        _key: ApiKeyRecord = Depends(require_api_key),
    ):
        items = storage.list_files(file_type=file_type)
        sliced = items[offset:offset + limit]
        return to_python({
            "items": sliced,
            "total": len(items),
            "limit": limit,
            "offset": offset,
        })

    @r.get("/files/{file_id}", summary="Get file metadata", response_model=Dict[str, Any])
    async def get_file(file_id: str, _key: ApiKeyRecord = Depends(require_api_key)):
        entry = storage.get_file(file_id)
        if not entry:
            raise HTTPException(404, "File not found")
        return to_python(entry)

    @r.delete("/files/{file_id}", summary="Delete a file", response_model=Dict[str, Any])
    async def delete_file(file_id: str, _key: ApiKeyRecord = Depends(require_api_key)):
        if not storage.delete_file(file_id):
            raise HTTPException(404, "File not found")
        return {"message": "File deleted", "file_id": file_id}

    @r.get(
        "/files/{file_id}/data",
        summary="Fetch the actual rows of a file",
        description=(
            "Returns the parsed rows of an uploaded file (paginated, max "
            "5000 rows per request). Useful for fetching the sales "
            "history to feed into another tool, or for visualization."
        ),
        response_model=Dict[str, Any],
    )
    async def get_file_data(
        file_id: str,
        limit: int = Query(5000, ge=1, le=50000),
        offset: int = Query(0, ge=0),
        _key: ApiKeyRecord = Depends(require_api_key),
    ):
        entry = storage.get_file(file_id)
        if not entry:
            raise HTTPException(404, "File not found")
        df = storage.get_dataframe(file_id)
        if df is None or df.empty:
            raise HTTPException(404, "File data is empty or missing")
        total = len(df)
        page = df.iloc[offset:offset + limit]
        records = [{c: to_python(row[c]) for c in page.columns} for _, row in page.iterrows()]
        return to_python({
            "file_id": file_id,
            "columns": [str(c) for c in df.columns],
            "rows": records,
            "total_rows": int(total),
            "returned_rows": int(len(records)),
            "offset": int(offset),
            "limit": int(limit),
        })

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------
    @r.post(
        "/analyze",
        summary="Analyze an uploaded sales file",
        description=(
            "Runs data-quality checks, computes time-series characteristics "
            "(mean, std, trend, seasonality, stationarity, outliers, missing), "
            "and returns model recommendations. Use the returned `date_column` "
            "and `value_column` when configuring a forecast."
        ),
        response_model=Dict[str, Any],
    )
    async def analyze(
        file_id: str = Query(..., description="ID of the uploaded sales file"),
        _key: ApiKeyRecord = Depends(require_api_key),
    ):
        from .routes.analyze import _analyze_file
        return await _analyze_file(file_id, storage, processor)

    # ------------------------------------------------------------------
    # Forecast
    # ------------------------------------------------------------------
    @r.post(
        "/forecast",
        summary="Create a forecast",
        description=(
            "Train new models on the uploaded sales data and produce a forecast. "
            "Pass `async=true` to run in the background; poll `/jobs/{job_id}` "
            "for progress. Synchronous mode blocks until completion (recommended "
            "only for small/quick jobs)."
        ),
        response_model=Dict[str, Any],
    )
    async def create_forecast(
        request: ForecastRequest,
        async_mode: bool = Query(False, alias="async"),
        _key: ApiKeyRecord = Depends(require_api_key),
    ):
        from .routes.forecast import _create_forecast_impl
        return await _create_forecast_impl(
            request=request,
            async_mode=async_mode,
            storage=storage,
            processor=processor,
            service=service,
        )

    @r.get(
        "/jobs/{job_id}",
        summary="Get the status of an async forecast job",
        response_model=Dict[str, Any],
    )
    async def get_job(
        job_id: str,
        _key: ApiKeyRecord = Depends(require_api_key),
    ):
        from ..core.jobs import get_job_manager
        info = get_job_manager().status(job_id)
        if not info:
            raise HTTPException(404, "Job not found")
        return info

    @r.get(
        "/jobs/{job_id}/result",
        summary="Block until an async forecast job completes",
        response_model=Dict[str, Any],
    )
    async def get_job_result(
        job_id: str,
        _key: ApiKeyRecord = Depends(require_api_key),
    ):
        from ..core.jobs import get_job_manager
        import asyncio
        jm = get_job_manager()
        job = jm.get(job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        if job.status.value == "completed":
            return {"job_id": job_id, "status": "completed", "result": job.result}
        if job.status.value == "failed":
            raise HTTPException(500, job.error or "Job failed")
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: jm.result(job_id, timeout=300)
            )
        except Exception as e:
            raise HTTPException(500, str(e))
        job = jm.get(job_id)
        return {"job_id": job_id, "status": job.status.value, "result": job.result}

    @r.get(
        "/forecasts",
        summary="List saved forecasts",
        response_model=Dict[str, Any],
    )
    async def list_forecasts(
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        _key: ApiKeyRecord = Depends(require_api_key),
    ):
        items = storage.list_forecasts()
        return to_python({
            "items": items[offset:offset + limit],
            "total": len(items),
            "limit": limit,
            "offset": offset,
        })

    @r.get(
        "/forecasts/{forecast_id}",
        summary="Get a saved forecast (full results)",
        response_model=Dict[str, Any],
    )
    async def get_forecast(forecast_id: str, _key: ApiKeyRecord = Depends(require_api_key)):
        rec = storage.get_forecast(forecast_id)
        if not rec:
            raise HTTPException(404, "Forecast not found")
        return to_python(rec)

    @r.delete(
        "/forecasts/{forecast_id}",
        summary="Delete a forecast",
        response_model=Dict[str, Any],
    )
    async def delete_forecast(forecast_id: str, _key: ApiKeyRecord = Depends(require_api_key)):
        if not storage.delete_forecast(forecast_id):
            raise HTTPException(404, "Forecast not found")
        return {"message": "Forecast deleted", "forecast_id": forecast_id}

    # ------------------------------------------------------------------
    # Models
    # ------------------------------------------------------------------
    @r.get(
        "/models",
        summary="List saved models",
        response_model=Dict[str, Any],
    )
    async def list_models(
        model_type: Optional[str] = Query(None),
        search: Optional[str] = Query(None),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        _key: ApiKeyRecord = Depends(require_api_key),
    ):
        from ..services.models.registry import get_model_registry
        items = get_model_registry().list_models(
            model_type=model_type, search=search, limit=limit, offset=offset,
        )
        return to_python({
            "items": [m.to_dict() for m in items],
            "total": len(items),
            "limit": limit,
            "offset": offset,
        })

    @r.get(
        "/models/{model_id}",
        summary="Get a saved model's metadata",
        response_model=Dict[str, Any],
    )
    async def get_model(model_id: str, _key: ApiKeyRecord = Depends(require_api_key)):
        from ..services.models.registry import get_model_registry
        meta = get_model_registry().get(model_id)
        if not meta:
            raise HTTPException(404, "Model not found")
        return to_python(meta.to_dict())

    @r.post(
        "/models/train",
        summary="Train and save a model",
        description=(
            "Train one or more models on a train split, evaluate on a held-out "
            "test split, and persist the best to the registry. The best model "
            "is chosen by lowest test MAE."
        ),
        response_model=Dict[str, Any],
    )
    async def train_model(
        request: Dict[str, Any] = Body(...),
        _key: ApiKeyRecord = Depends(require_api_key),
    ):
        from .routes.models import _train_model_impl
        return await _train_model_impl(
            request=request, storage=storage, processor=processor, service=service
        )

    @r.post(
        "/models/{model_id}/forecast",
        summary="Forecast with a saved model (no retraining)",
        description=(
            "Load a previously saved model and produce a forecast. This is the "
            "fast path — no training, no CV. Use it in scripts and notebooks "
            "where you want consistent predictions from a known-good model."
        ),
        response_model=Dict[str, Any],
    )
    async def forecast_with_saved_model(
        model_id: str,
        request: Dict[str, Any] = Body(...),
        _key: ApiKeyRecord = Depends(require_api_key),
    ):
        from .routes.models import _forecast_with_saved_model_impl
        return await _forecast_with_saved_model_impl(
            model_id=model_id,
            request=request,
            storage=storage,
            service=service,
        )

    @r.post(
        "/models/upload",
        summary="Upload a pre-trained model pickle",
        response_model=Dict[str, Any],
    )
    async def upload_model(
        file: UploadFile = File(...),
        name: Optional[str] = Form(None),
        notes: str = Form(""),
        tags: Optional[str] = Form(None),
        _key: ApiKeyRecord = Depends(require_api_key),
    ):
        from .routes.models import _upload_model_impl
        return await _upload_model_impl(
            file=file, name=name, notes=notes, tags=tags
        )

    @r.delete(
        "/models/{model_id}",
        summary="Delete a saved model",
        response_model=Dict[str, Any],
    )
    async def delete_model(model_id: str, _key: ApiKeyRecord = Depends(require_api_key)):
        from ..services.models.registry import get_model_registry
        if not get_model_registry().delete(model_id):
            raise HTTPException(404, "Model not found")
        return {"message": "Model deleted", "model_id": model_id}

    return r
