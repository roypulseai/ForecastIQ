"""JSON serialization helpers — convert numpy / pandas / datetime to JSON-safe Python natives."""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd


def to_python(obj: Any) -> Any:
    """Recursively convert numpy / pandas / datetime / enum objects to JSON-safe Python natives."""
    if obj is None:
        return None
    if isinstance(obj, (bool,)):
        return bool(obj)
    # Enum (including str-enum) — use its .value if available
    if isinstance(obj, Enum):
        v = obj.value
        if isinstance(v, (str, int, float, bool)):
            return to_python(v)
        return to_python(str(v))
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        v = float(obj)
        if np.isnan(v) or np.isinf(v):
            return None
        return v
    if isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj
    if isinstance(obj, (int, str)):
        return obj
    if isinstance(obj, np.ndarray):
        return to_python(obj.tolist())
    if isinstance(obj, (pd.Timestamp,)):
        if pd.isna(obj):
            return None
        return obj.isoformat()
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, pd.Series):
        return to_python(obj.tolist())
    if isinstance(obj, pd.DataFrame):
        return to_python(obj.to_dict(orient="records"))
    if isinstance(obj, dict):
        return {str(k): to_python(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_python(v) for v in obj]
    # Numpy scalar subtypes that aren't caught above
    if hasattr(obj, "item") and not isinstance(obj, (str, bytes, list, dict, tuple)):
        try:
            return to_python(obj.item())
        except (ValueError, TypeError):
            pass
    return obj


def safe_float(x: Any, default: float = 0.0) -> float:
    """Convert to float, replacing NaN / inf with `default`."""
    if x is None:
        return default
    try:
        v = float(x)
        if np.isnan(v) or np.isinf(v):
            return default
        return v
    except (TypeError, ValueError):
        return default


def safe_int(x: Any, default: int = 0) -> int:
    """Convert to int, replacing None / NaN with `default`."""
    if x is None:
        return default
    try:
        v = float(x)
        if np.isnan(v) or np.isinf(v):
            return default
        return int(v)
    except (TypeError, ValueError):
        return default


def jsonable(obj: Any) -> Any:
    """Public alias of to_python — used at the API boundary."""
    return to_python(obj)
