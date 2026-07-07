"""Analyze uploaded sales data: data characteristics + model recommendations."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query

from ...core.storage import FileMetadataStore
from ...core.utils import to_python
from ...schemas.common import (
    AnalysisResponse,
    DataCharacteristics,
    ModelRecommendation,
    ValidationResult,
)
from ...services.data_processor import DataProcessor
from ...services.model_selector import ModelSelector

router = APIRouter()
storage = FileMetadataStore()
processor = DataProcessor()
selector = ModelSelector()


@router.post("/analyze")
async def analyze_data(
    file_id: str = Query(..., description="ID of the uploaded sales file to analyze"),
) -> Dict[str, Any]:
    entry = storage.get_file(file_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
    if entry.get("file_type") != "sales":
        raise HTTPException(
            status_code=400,
            detail="Only sales files can be analyzed. Upload a sales file first.",
        )
    df = storage.get_dataframe(file_id)
    if df is None or df.empty:
        raise HTTPException(status_code=400, detail="Sales file is empty or unreadable")

    validation = processor.validate_sales(df)
    if not validation["valid"]:
        raise HTTPException(
            status_code=400,
            detail={"message": "Invalid sales data", "errors": validation["errors"]},
        )

    date_col = validation["date_column"] or "date"
    value_col = validation["value_column"] or "value"

    characteristics = selector.analyze_data(df, date_col, value_col)

    # Detect external factors
    has_external = bool([
        ft for ft in ("media_plan", "promotions", "holidays", "events",
                      "weather", "competitor", "economic")
        if storage.find_files_by_type(ft)
    ])

    recommendations = selector.recommend_models(characteristics, has_external=has_external)

    payload = {
        "validation": ValidationResult(
            valid=validation["valid"],
            errors=validation["errors"],
            warnings=validation.get("warnings", []),
            date_column=date_col,
            value_column=value_col,
            row_count=validation["row_count"],
            frequency=validation.get("frequency"),
            extra_columns=validation.get("extra_columns", []),
        ),
        "data_characteristics": DataCharacteristics(**characteristics),
        "model_recommendations": [ModelRecommendation(**r) for r in recommendations],
    }
    response = to_python(AnalysisResponse(**payload).model_dump())
    # Add memory footprint for the UI
    response["memory_mb"] = DataProcessor.memory_mb(df)
    return response
