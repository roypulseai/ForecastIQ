"""File upload endpoints for all 8 supported data types."""
from __future__ import annotations

import os
import shutil
import tempfile
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from ...core.config import settings
from ...core.storage import FileMetadataStore
from ...core.utils import to_python
from ...schemas.common import FILE_TYPE_VALUES, DataStatus, UploadedFileInfo
from ...services.data_processor import DataProcessor

# Use a prefix that matches the frontend's API service expectations.
# Routes are mounted under /api/v1/upload by main.py, so we don't add a
# prefix here — that would produce /api/v1/upload/upload/... double prefix.
router = APIRouter()
storage = FileMetadataStore()
processor = DataProcessor()


async def _process_and_save(
    file_type: str,
    file: UploadFile,
    storage: FileMetadataStore,
    processor: DataProcessor,
) -> Dict[str, Any]:
    """Reusable upload handler. Returns the JSON-serializable upload summary.
    Raises HTTPException on validation/processing errors. Used by both the
    internal /api/v1/upload/* and the public /v1/files/upload/* routes.
    """
    if file_type not in FILE_TYPE_VALUES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file_type '{file_type}'. Allowed: {FILE_TYPE_VALUES}",
        )
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{ext}'. "
                   f"Allowed: {settings.ALLOWED_EXTENSIONS}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds max upload size of {settings.MAX_UPLOAD_SIZE} bytes",
        )

    tmp_dir = tempfile.mkdtemp(prefix="upload_")
    tmp_path = os.path.join(tmp_dir, file.filename)
    try:
        with open(tmp_path, "wb") as f:
            f.write(content)

        try:
            raw_df = processor.load_file(tmp_path)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")
        try:
            clean_df, mapping = processor.process(raw_df, file_type)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Processing error: {e}")
        finally:
            try:
                del raw_df
            except Exception:
                pass

        warnings_list: list = []
        if file_type == "sales":
            v = processor.validate_sales(clean_df)
            if not v["valid"]:
                raise HTTPException(
                    status_code=400,
                    detail={"message": "Invalid sales data", "errors": v["errors"]},
                )
            warnings_list = v.get("warnings", [])

        entry = storage.save_upload(
            original_filename=file.filename,
            file_type=file_type,
            raw_path=tmp_path,
            size=len(content),
            df=clean_df,
            column_mapping=mapping,
        )
        entry["warnings"] = warnings_list
        entry["status"] = DataStatus.READY.value
        entry["memory_mb"] = round(DataProcessor.memory_mb(clean_df), 2)

        return to_python({
            "file_id": entry["file_id"],
            "filename": entry["original_filename"],
            "type": entry["file_type"],
            "size": entry["size"],
            "row_count": entry["row_count"],
            "columns": entry["columns"],
            "column_mapping": entry["column_mapping"],
            "warnings": warnings_list,
            "status": entry["status"],
            "memory_mb": entry["memory_mb"],
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.post("/upload/{file_type}")
async def upload_file(file_type: str, file: UploadFile = File(...)) -> Dict[str, Any]:
    return await _process_and_save(file_type, file, storage, processor)


@router.get("/upload/files")
async def list_files(file_type: Optional[str] = None) -> Dict[str, Any]:
    items = storage.list_files(file_type=file_type)
    # Ensure each item has a `type` field (mapped from `file_type`)
    # for consistency with the upload response.
    for item in items:
        if "type" not in item and "file_type" in item:
            item["type"] = item["file_type"]
    return to_python({"items": items, "total": len(items)})


@router.get("/upload/files/{file_id}")
async def get_file(file_id: str) -> Dict[str, Any]:
    entry = storage.get_file(file_id)
    if not entry:
        raise HTTPException(status_code=404, detail="File not found")
    if "type" not in entry and "file_type" in entry:
        entry["type"] = entry["file_type"]
    return to_python(entry)


@router.get("/upload/files/{file_id}/data")
async def get_file_data(
    file_id: str,
    limit: int = Query(5000, ge=1, le=50000, description="Max rows to return"),
    offset: int = Query(0, ge=0, description="Rows to skip"),
) -> Dict[str, Any]:
    """Return the actual rows of a file for visualization / exploration.

    Defaults to 5000 rows max to keep responses fast. Use offset/limit
    pagination for larger files.
    """
    entry = storage.get_file(file_id)
    if not entry:
        raise HTTPException(status_code=404, detail="File not found")
    df = storage.get_dataframe(file_id)
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="File data is empty or missing")
    total = len(df)
    # Apply pagination
    page = df.iloc[offset:offset + limit]
    # Records: list of {col: value} dicts with numpy -> python conversion
    records: List[Dict[str, Any]] = []
    for _, row in page.iterrows():
        records.append({c: to_python(row[c]) for c in page.columns})
    return to_python({
        "file_id": file_id,
        "columns": [str(c) for c in df.columns],
        "rows": records,
        "total_rows": int(total),
        "returned_rows": int(len(records)),
        "offset": int(offset),
        "limit": int(limit),
    })


@router.delete("/upload/files/{file_id}")
async def delete_file(file_id: str) -> Dict[str, Any]:
    ok = storage.delete_file(file_id)
    if not ok:
        raise HTTPException(status_code=404, detail="File not found")
    return {"message": "File deleted", "file_id": file_id}
