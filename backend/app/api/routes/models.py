"""Model registry endpoints: list, download, upload, delete trained models.

Endpoints:
    GET    /models                     List all saved models
    GET    /models/{id}                Get model metadata
    GET    /models/{id}/download       Download the .pkl file
    POST   /models/upload              Upload a pre-trained model pickle
    POST   /models/train               Train + save (proper train/test split)
    POST   /models/{id}/forecast       Use a saved model to forecast
    PATCH  /models/{id}                Update name/notes/tags
    DELETE /models/{id}                Delete a saved model
"""
from __future__ import annotations

import io
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from ...core.config import settings
from ...core.storage import FileMetadataStore
from ...core.utils import to_python
from ...schemas.forecast import ForecastRequest
from ...services.data_processor import DataProcessor
from ...services.forecaster import ForecasterService
from ...services.models.registry import (
    ModelArtifactMeta,
    ModelRegistry,
    get_model_registry,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models")
storage = FileMetadataStore()
processor = DataProcessor()
service = ForecasterService()


# Allowed model class names for upload validation
ALLOWED_MODEL_TYPES = {
    "arima", "sarimax", "prophet", "lightgbm", "xgboost",
    "wma", "ets", "theta", "stl", "automl",
}


def _to_public(meta: ModelArtifactMeta) -> Dict[str, Any]:
    return meta.to_dict()


@router.get("")
async def list_models(
    model_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """List all saved model artifacts with their metadata."""
    registry = get_model_registry()
    items = registry.list_models(
        model_type=model_type, search=search, limit=limit, offset=offset,
    )
    return to_python({
        "items": [_to_public(m) for m in items],
        "total": len(items),
        "limit": limit,
        "offset": offset,
    })


@router.get("/{model_id}")
async def get_model(model_id: str) -> Dict[str, Any]:
    registry = get_model_registry()
    meta = registry.get(model_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Model not found")
    return to_python(_to_public(meta))


@router.get("/{model_id}/download")
async def download_model(model_id: str):
    """Download a saved model as a .pkl file."""
    registry = get_model_registry()
    meta = registry.get(model_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Model not found")
    blob_path = registry.get_blob_path(model_id)
    if not blob_path:
        raise HTTPException(status_code=404, detail="Model blob missing")
    data = blob_path.read_bytes()
    safe_name = (meta.name or "model").replace('"', "").replace("/", "_")[:80]
    filename = f"{safe_name}-{model_id[:8]}.pkl"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{model_id}")
async def delete_model(model_id: str) -> Dict[str, Any]:
    registry = get_model_registry()
    if not registry.delete(model_id):
        raise HTTPException(status_code=404, detail="Model not found")
    return {"message": "Model deleted", "model_id": model_id}


@router.patch("/{model_id}")
async def update_model(
    model_id: str,
    payload: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    """Update model metadata: name, notes, tags."""
    registry = get_model_registry()
    meta = registry.update_meta(
        model_id,
        name=payload.get("name"),
        notes=payload.get("notes"),
        tags=payload.get("tags"),
    )
    if not meta:
        raise HTTPException(status_code=404, detail="Model not found")
    return to_python(_to_public(meta))


# -----------------------------------------------------------------------------
# Upload
# -----------------------------------------------------------------------------
async def _upload_model_impl(
    file: UploadFile,
    name: Optional[str],
    notes: str,
    tags: Optional[str],
) -> Dict[str, Any]:
    """Reusable upload handler. Used by both /api/v1/models/upload (Form) and
    /v1/models/upload (File)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    if not (file.filename.endswith(".pkl") or file.filename.endswith(".joblib")):
        raise HTTPException(
            status_code=400,
            detail="Model file must be .pkl or .joblib",
        )
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(content) > 200 * 1024 * 1024:  # 200MB cap
        raise HTTPException(status_code=413, detail="Model file too large (max 200MB)")

    # Try to deserialize. We import lazily to avoid loading the heavy
    # ML deps for a metadata-only call.
    import joblib
    import pickle

    payload: Optional[Dict[str, Any]] = None
    framework = "joblib"
    try:
        bio = io.BytesIO(content)
        payload = joblib.load(bio)
    except Exception:
        try:
            bio = io.BytesIO(content)
            payload = pickle.load(bio)
            framework = "pickle"
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Could not deserialize model file. "
                    "It must be a pickle/joblib blob produced by ForecastIQ. "
                    f"Underlying error: {e}"
                ),
            )

    if not isinstance(payload, dict) or "class_name" not in payload:
        raise HTTPException(
            status_code=400,
            detail=(
                "Model file is not a ForecastIQ artifact. "
                "Expected a dict with 'class_name' and 'state' keys."
            ),
        )

    model_type = payload.get("state", {}).get("name") or payload.get("class_name")
    if not model_type:
        raise HTTPException(status_code=400, detail="Model artifact missing 'name'")
    model_type = str(model_type).lower()
    if model_type not in ALLOWED_MODEL_TYPES:
        aliases = {"arimaforecaster": "arima", "sarimaxforecaster": "sarimax"}
        model_type = aliases.get(model_type, model_type)
    if model_type not in ALLOWED_MODEL_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported model type '{model_type}'. Allowed: {sorted(ALLOWED_MODEL_TYPES)}",
        )

    try:
        registry = get_model_registry()
        mid = registry._new_id()
        blob_path = registry.models_dir / f"{mid}.pkl"
        blob_path.write_bytes(content)
        sha = registry._hash_bytes(content)
        from datetime import datetime
        from ...services.models.registry import (
            ModelArtifactMeta, ModelFramework, ModelMetrics, TrainingConfig,
        )
        now = datetime.utcnow().isoformat() + "Z"
        state = payload.get("state", {})
        training_cfg = TrainingConfig(
            date_column=state.get("_date_col", "date"),
            value_column=state.get("_value_col", "value"),
            frequency=state.get("_frequency", "D"),
            hyperparameters=state.get("params", {}),
        )
        meta = ModelArtifactMeta(
            model_id=mid,
            name=name or file.filename.replace(".pkl", "").replace(".joblib", ""),
            model_type=model_type,
            framework=ModelFramework(framework),
            created_at=now,
            updated_at=now,
            file_size=len(content),
            sha256=sha,
            metrics=ModelMetrics(),
            training=training_cfg,
            tags=[t.strip() for t in (tags or "").split(",") if t.strip()],
            notes=notes,
        )
        meta_path = registry.models_dir / f"{mid}.meta.json"
        registry._write_json(meta_path, meta.to_dict())
        index = registry._read_json(registry._index_path)
        index[mid] = meta.to_dict()
        registry._write_index(index)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to register uploaded model")
        raise HTTPException(status_code=500, detail=f"Failed to register uploaded model: {e}")

    return _to_public(meta)


@router.post("/upload")
async def upload_model(
    file: UploadFile = File(...),
    name: Optional[str] = None,
    notes: str = "",
    tags: Optional[str] = None,
) -> Dict[str, Any]:
    """Upload a pre-trained model pickle.

    The file must be a pickle (or joblib) blob produced by ForecastIQ's
    model registry (or compatible). The endpoint validates the payload
    and re-registers it. The returned `model_id` can be used to forecast
    with `POST /models/{id}/forecast`.
    """
    return await _upload_model_impl(file, name, notes, tags)


# -----------------------------------------------------------------------------
# Train + save
# -----------------------------------------------------------------------------
async def _train_model_impl(
    request: Dict[str, Any],
    *,
    storage: FileMetadataStore,
    processor: DataProcessor,
    service: ForecasterService,
) -> Dict[str, Any]:
    """Reusable train-and-save handler."""
    file_id = request.get("file_id")
    if file_id:
        entry = storage.get_file(file_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Sales file not found")
        if entry.get("file_type") != "sales":
            raise HTTPException(status_code=400, detail="Only sales files can be used for training")
        sales_df = storage.get_dataframe(file_id)
    else:
        sales_entry = storage.find_sales_file()
        if not sales_entry:
            raise HTTPException(status_code=400, detail="No sales file uploaded")
        sales_df = storage.get_dataframe(sales_entry["file_id"])
    if sales_df is None or sales_df.empty:
        raise HTTPException(status_code=400, detail="Sales data is empty")

    from .forecast import _gather_exog
    flags = {
        "media_plan": request.get("include_media_plan", False),
        "promotions": request.get("include_promotions", False),
        "holidays": request.get("include_holidays", False),
        "events": request.get("include_events", False),
        "weather": request.get("include_weather", False),
        "competitor": request.get("include_competitor", False),
        "economic": request.get("include_economic", False),
    }
    forecast_req = ForecastRequest(
        name=request.get("name", "Training"),
        target_column=request.get("target_column", "value"),
        date_column=request.get("date_column", "date"),
        frequency=request.get("frequency", "D"),
        horizon=int(request.get("horizon", 30)),
        models=[request.get("model_type", "prophet")] if "model_type" in request else request.get("models", ["prophet"]),
        include_media_plan=flags["media_plan"],
        include_promotions=flags["promotions"],
        include_holidays=flags["holidays"],
        include_events=flags["events"],
        include_weather=flags["weather"],
        include_competitor=flags["competitor"],
        include_economic=flags["economic"],
    )
    exog_data = _gather_exog(forecast_req)

    try:
        result = service.train_and_save(
            sales_df,
            request,
            exog_data=exog_data,
            model_name=request.get("name"),
            notes=request.get("notes", ""),
            tags=request.get("tags"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Train-and-save failed")
        raise HTTPException(status_code=500, detail=f"Training failed: {e}")
    return to_python(result)


@router.post("/train")
async def train_model(
    request: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    """Train a model with proper train/test split and persist it.

    The request should include:
        * `model_type` (string) or `models` (list of strings) — which to train
        * `file_id` or implicit sales file — the training data
        * `train_test_split` (default 0.8) — fraction for training
        * `horizon` — also used as the test-set size (if > 0)
        * `date_column` (default 'date'), `target_column` (default 'value')
        * `frequency` (default 'D')
        * `parameters` (optional) — hyperparameters per model
        * `name` (optional) — display name for the saved model
        * `notes` (optional) — free-text notes
        * `tags` (optional list) — labels
        * `include_*` (booleans) — which external factors to include
    """
    return await _train_model_impl(
        request=request, storage=storage, processor=processor, service=service
    )


# -----------------------------------------------------------------------------
# Forecast with a saved model
# -----------------------------------------------------------------------------
async def _forecast_with_saved_model_impl(
    model_id: str,
    request: Dict[str, Any],
    *,
    storage: FileMetadataStore,
    service: ForecasterService,
) -> Dict[str, Any]:
    """Reusable forecast-with-saved-model handler."""
    horizon = int(request.get("horizon", 30))
    if horizon < 1 or horizon > 3650:
        raise HTTPException(status_code=400, detail="horizon must be in [1, 3650]")

    exog_data: Dict[str, Any] = {}
    type_to_flag = {
        "media_plan": "include_media_plan",
        "promotions": "include_promotions",
        "holidays": "include_holidays",
        "events": "include_events",
        "weather": "include_weather",
        "competitor": "include_competitor",
        "economic": "include_economic",
    }
    for ft, flag in type_to_flag.items():
        if request.get(flag, False):
            files = storage.find_files_by_type(ft)
            if files:
                df = storage.get_dataframe(files[0]["file_id"])
                if df is not None and not df.empty:
                    exog_data[ft] = df

    try:
        result = service.forecast_with_loaded_model(model_id, horizon, exog_data=exog_data or None)
    except FileNotFoundError:
        raise HTTPException(404, "Model not found")
    except Exception as e:
        logger.exception("Forecast with saved model failed")
        raise HTTPException(status_code=500, detail=f"Forecast failed: {e}")
    return to_python(result)


@router.post("/{model_id}/forecast")
async def forecast_with_saved_model(
    model_id: str,
    request: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    """Use a previously saved model to forecast without retraining.

    The request should include:
        * `horizon` (int, required) — how many periods ahead
        * `include_*` (booleans) — which exogenous data to pass in
    """
    return await _forecast_with_saved_model_impl(
        model_id=model_id, request=request, storage=storage, service=service
    )