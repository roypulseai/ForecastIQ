"""Model registry: persists trained model artifacts to disk and provides
load/save semantics consistent with the typical data-science workflow.

Why we built this:
    A data scientist trains a model, evaluates it on a held-out test set,
    and saves it as a pickle/joblib artifact. When new data arrives, they
    load the artifact and call `predict` without retraining. ForecastIQ
    needs to support this pattern so users can:

        1. Train + save a model after a successful forecast run
        2. Re-load that model later (or upload a model trained elsewhere)
        3. Forecast with the loaded model on new data without re-fitting

Design notes:
    * We store each model as a `.pkl` file using joblib (preferred for
      scikit-learn-style objects with large numpy arrays) or pickle as
      fallback. We wrap the raw fitted object in a `ModelArtifact`
      dataclass that also captures everything needed to re-use it:
      - which model class was used
      - which hyperparameters
      - the date/value column names
      - the date range the model was trained on
      - training metrics (MAE/RMSE/MAPE on the test set)
      - a content hash for integrity
    * The artifact is JSON-serializable *metadata* + binary *blob*. The
      blob is the actual fitted model; the metadata is what the UI shows
      and what we use to decide whether the model is compatible with a
      given dataset.
    * When loading, the registry re-instantiates the model class, sets
      the hyperparameters, and unpickles the fitted state. If the
      model is from an older version of ForecastIQ, we still try
      best-effort recovery.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import pickle
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import pandas as pd

from ...core.config import settings
from ..model_selector import ModelSelector

logger = logging.getLogger(__name__)


class ModelFramework(str, Enum):
    PICKLE = "pickle"  # vanilla pickle
    JOBLIB = "joblib"  # joblib.dump (faster for sklearn-style)
    PROPHET = "prophet"  # Prophet has its own json serialization
    STATSMODELS = "statsmodels"  # statsmodels ARIMA/ETS/Theta/STL


@dataclass
class ModelMetrics:
    """Metrics captured at training time, on the held-out test set."""
    mae: Optional[float] = None
    rmse: Optional[float] = None
    mape: Optional[float] = None
    r2: Optional[float] = None
    train_rows: int = 0
    test_rows: int = 0
    # Cross-validated metrics (computed during forecast run)
    cv_mae: Optional[float] = None
    cv_rmse: Optional[float] = None
    cv_mape: Optional[float] = None


@dataclass
class TrainingConfig:
    """Configuration used to train the model. Used to verify compatibility
    when reloading on a new dataset."""
    date_column: str = "date"
    value_column: str = "value"
    frequency: str = "D"
    train_test_split: float = 0.8  # 80% train, 20% test
    horizon_used: int = 0  # Horizon used during evaluation
    extra_columns: List[str] = field(default_factory=list)
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    exogenous_used: List[str] = field(default_factory=list)  # e.g. ['media_plan', 'promotions']


@dataclass
class ModelArtifactMeta:
    """Lightweight, JSON-serializable metadata about a saved model."""
    model_id: str
    name: str  # user-supplied display name
    model_type: str  # 'prophet', 'arima', 'lightgbm', etc.
    framework: ModelFramework
    created_at: str  # ISO datetime
    updated_at: str
    file_size: int  # bytes
    sha256: str  # content hash
    metrics: ModelMetrics
    training: TrainingConfig
    # Date range the model was trained on
    train_start: Optional[str] = None
    train_end: Optional[str] = None
    test_start: Optional[str] = None
    test_end: Optional[str] = None
    # Reference to the source sales file (if any)
    source_file_id: Optional[str] = None
    source_forecast_id: Optional[str] = None
    # Tags / labels for organizing
    tags: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["framework"] = self.framework.value
        return d

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ModelArtifactMeta":
        d = dict(d)
        d["framework"] = ModelFramework(d.get("framework", "joblib"))
        if "metrics" in d and isinstance(d["metrics"], dict):
            d["metrics"] = ModelMetrics(**d["metrics"])
        if "training" in d and isinstance(d["training"], dict):
            d["training"] = TrainingConfig(**d["training"])
        return ModelArtifactMeta(**d)


class ModelRegistry:
    """Thread-safe disk-backed registry of trained model artifacts.

    Layout on disk:
        DATA_DIR/
            models/
                index.json              # index of all model metadata
                <model_id>.pkl          # binary blob of fitted model
                <model_id>.meta.json    # metadata for the model
    """

    MODELS_DIR = "models"
    INDEX_FILE = "index.json"

    def __init__(self, data_dir: Optional[str] = None) -> None:
        self.data_dir = Path(data_dir or settings.DATA_DIR)
        self.models_dir = self.data_dir / self.MODELS_DIR
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self.models_dir / self.INDEX_FILE
        self._lock = threading.RLock()
        if not self._index_path.exists():
            self._write_index({})

    # ------------------------------------------------------------- utils
    @staticmethod
    def _read_json(path: Path) -> Dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _write_json(path: Path, data: Dict[str, Any]) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(tmp, path)

    @staticmethod
    def _new_id() -> str:
        return uuid.uuid4().hex

    @staticmethod
    def _hash_bytes(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    # ------------------------------------------------------------- save
    def save(
        self,
        *,
        name: str,
        model,  # BaseForecaster instance, fitted
        metrics: ModelMetrics,
        training: TrainingConfig,
        train_start: Optional[str] = None,
        train_end: Optional[str] = None,
        test_start: Optional[str] = None,
        test_end: Optional[str] = None,
        source_file_id: Optional[str] = None,
        source_forecast_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        notes: str = "",
        model_id: Optional[str] = None,
    ) -> ModelArtifactMeta:
        """Serialize a fitted model to disk. Returns the artifact metadata.

        The model is wrapped in a payload dict with class info + fitted
        state, then pickled. This makes the artifact somewhat self-describing
        so we can rebuild the class on load.
        """
        with self._lock:
            mid = model_id or self._new_id()
            now = datetime.utcnow().isoformat() + "Z"

            # Serialize the fitted state. We use joblib for sklearn-compatible
            # models (LightGBM, XGBoost, ETS) and pickle for everything else.
            framework = self._pick_framework(model.name if hasattr(model, "name") else "")

            blob = self._serialize_model(model, framework)

            # Persist blob
            blob_path = self.models_dir / f"{mid}.pkl"
            with open(blob_path, "wb") as f:
                f.write(blob)

            sha = self._hash_bytes(blob)
            size = len(blob)

            meta = ModelArtifactMeta(
                model_id=mid,
                name=name,
                model_type=model.name if hasattr(model, "name") else "unknown",
                framework=framework,
                created_at=now,
                updated_at=now,
                file_size=size,
                sha256=sha,
                metrics=metrics,
                training=training,
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                source_file_id=source_file_id,
                source_forecast_id=source_forecast_id,
                tags=tags or [],
                notes=notes,
            )
            # Persist metadata
            meta_path = self.models_dir / f"{mid}.meta.json"
            self._write_json(meta_path, meta.to_dict())

            # Update index
            index = self._read_json(self._index_path)
            index[mid] = meta.to_dict()
            self._write_index(index)

            logger.info(
                "Saved model %s (%s, %d bytes, sha256=%s)",
                mid, model.name if hasattr(model, "name") else "?", size, sha[:12],
            )
            return meta

    @staticmethod
    def _pick_framework(model_name: str) -> ModelFramework:
        n = (model_name or "").lower()
        if n == "prophet":
            return ModelFramework.PROPHET
        if n in ("arima", "sarimax", "ets", "theta", "stl"):
            return ModelFramework.STATSMODELS
        if n in ("lightgbm", "xgboost"):
            return ModelFramework.JOBLIB
        return ModelFramework.PICKLE

    def _serialize_model(self, model, framework: ModelFramework) -> bytes:
        """Serialize a fitted model into bytes.

        We use a wrapped payload so the class can be reconstructed on load:
            payload = {
                "class_name": str(type(model).__name__),
                "module": type(model).__module__,
                "params": getattr(model, "params", {}),
                "state": <pickled fitted state>
            }
        """
        # Capture lightweight state that we know all BaseForecaster subclasses
        # have, so we can restore them on load.
        state = {
            "_date_col": getattr(model, "_date_col", None),
            "_value_col": getattr(model, "_value_col", None),
            "_last_date": getattr(model, "_last_date", None),
            "_frequency": getattr(model, "_frequency", "D"),
            "_feature_cols": list(getattr(model, "_feature_cols", [])),
            "params": dict(getattr(model, "params", {})),
            "name": getattr(model, "name", type(model).__name__),
        }
        # Capture the underlying fitted object (varies per model type).
        fitted = getattr(model, "_fitted_model", None)
        # Some models store additional state we need to preserve
        extra = {}
        for attr in (
            "_holidays_df", "_promo_effects", "_seasonal_factors",
            "_scaler", "_train_df", "_last_values",
        ):
            if hasattr(model, attr):
                val = getattr(model, attr)
                if val is not None and not callable(val):
                    try:
                        # Test pickleability cheaply
                        pickle.dumps(val, protocol=pickle.HIGHEST_PROTOCOL)
                        extra[attr] = val
                    except Exception:
                        logger.debug("Skipping non-picklable attr %s on %s", attr, type(model).__name__)

        payload = {
            "schema_version": 1,
            "class_name": type(model).__name__,
            "module": type(model).__module__,
            "state": state,
            "fitted": fitted,
            "extra": extra,
        }

        buf = io.BytesIO()
        try:
            if framework in (ModelFramework.JOBLIB, ModelFramework.STATSMODELS):
                joblib.dump(payload, buf, compress=3)
            else:
                pickle.dump(payload, buf, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception:
            # Fall back to pickle if joblib fails (e.g. on Prophet)
            buf = io.BytesIO()
            pickle.dump(payload, buf, protocol=pickle.HIGHEST_PROTOCOL)
        return buf.getvalue()

    # ------------------------------------------------------------- load
    def load(self, model_id: str) -> "LoadedModel":
        """Load a saved model and return a wrapper that can forecast directly
        without retraining. Raises FileNotFoundError if not found."""
        with self._lock:
            index = self._read_json(self._index_path)
            entry = index.get(model_id)
            if not entry:
                raise FileNotFoundError(f"Model not found: {model_id}")
            meta = ModelArtifactMeta.from_dict(entry)
            blob_path = self.models_dir / f"{model_id}.pkl"
            if not blob_path.exists():
                raise FileNotFoundError(f"Model blob missing: {blob_path}")
            with open(blob_path, "rb") as f:
                blob = f.read()

        # Verify integrity
        sha = self._hash_bytes(blob)
        if sha != meta.sha256:
            raise ValueError(f"Model blob hash mismatch for {model_id} — file may be corrupted")

        payload = self._deserialize_model(blob, meta.framework)
        model = self._reconstruct_model(payload, meta)

        return LoadedModel(meta=meta, model=model, payload=payload)

    def _deserialize_model(self, blob: bytes, framework: ModelFramework) -> Dict[str, Any]:
        buf = io.BytesIO(blob)
        if framework in (ModelFramework.JOBLIB, ModelFramework.STATSMODELS):
            try:
                return joblib.load(buf)
            except Exception:
                buf.seek(0)
                return pickle.load(buf)
        return pickle.load(buf)

    def _reconstruct_model(self, payload: Dict[str, Any], meta: ModelArtifactMeta) -> Any:
        """Rebuild a fitted model instance from the serialized payload."""
        selector = ModelSelector()
        # Re-instantiate via the selector with the same hyperparameters
        try:
            model = selector.get_model(meta.model_type, payload["state"].get("params", {}))
        except Exception as e:
            logger.error("Failed to re-instantiate model %s: %s", meta.model_type, e)
            raise

        # Restore state
        state = payload.get("state", {})
        for k, v in state.items():
            if k == "params":
                continue
            if hasattr(model, k):
                try:
                    setattr(model, k, v)
                except Exception:
                    logger.debug("Could not restore state %s on %s", k, type(model).__name__)

        # Restore the underlying fitted object
        if payload.get("fitted") is not None:
            try:
                model._fitted_model = payload["fitted"]
            except Exception as e:
                logger.warning("Could not restore _fitted_model: %s", e)

        # Restore extra attrs
        for k, v in payload.get("extra", {}).items():
            try:
                setattr(model, k, v)
            except Exception:
                pass

        return model

    # ------------------------------------------------------------- list
    def list_models(
        self,
        model_type: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ModelArtifactMeta]:
        with self._lock:
            index = self._read_json(self._index_path)
        items = list(index.values())
        if model_type:
            items = [i for i in items if i.get("model_type") == model_type]
        if search:
            q = search.lower()
            items = [
                i for i in items
                if q in (i.get("name") or "").lower()
                or q in (i.get("notes") or "").lower()
                or any(q in (t or "").lower() for t in i.get("tags", []))
            ]
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        sliced = items[offset:offset + limit]
        return [ModelArtifactMeta.from_dict(i) for i in sliced]

    def get(self, model_id: str) -> Optional[ModelArtifactMeta]:
        with self._lock:
            index = self._read_json(self._index_path)
        entry = index.get(model_id)
        if not entry:
            return None
        return ModelArtifactMeta.from_dict(entry)

    def get_blob_path(self, model_id: str) -> Optional[Path]:
        with self._lock:
            index = self._read_json(self._index_path)
        if model_id not in index:
            return None
        path = self.models_dir / f"{model_id}.pkl"
        return path if path.exists() else None

    # ------------------------------------------------------------- delete
    def delete(self, model_id: str) -> bool:
        with self._lock:
            index = self._read_json(self._index_path)
            if model_id not in index:
                return False
            index.pop(model_id, None)
            self._write_index(index)
        # Best-effort cleanup
        for ext in (".pkl", ".meta.json"):
            p = self.models_dir / f"{model_id}{ext}"
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass
        return True

    def update_meta(
        self,
        model_id: str,
        *,
        name: Optional[str] = None,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[ModelArtifactMeta]:
        with self._lock:
            index = self._read_json(self._index_path)
            entry = index.get(model_id)
            if not entry:
                return None
            if name is not None:
                entry["name"] = name
            if notes is not None:
                entry["notes"] = notes
            if tags is not None:
                entry["tags"] = list(tags)
            entry["updated_at"] = datetime.utcnow().isoformat() + "Z"
            self._write_index(index)
            # Also rewrite the standalone meta file
            meta_path = self.models_dir / f"{model_id}.meta.json"
            self._write_json(meta_path, entry)
        return ModelArtifactMeta.from_dict(entry)

    # ------------------------------------------------------------- helper
    def _write_index(self, data: Dict[str, Any]) -> None:
        self._write_json(self._index_path, data)


@dataclass
class LoadedModel:
    """In-memory representation of a model loaded from disk.

    The `model` attribute is a fully-instantiated and fitted
    BaseForecaster that can immediately call `forecast()`.
    """
    meta: ModelArtifactMeta
    model: Any  # BaseForecaster instance
    payload: Dict[str, Any]


# Module-level singleton
_registry: Optional[ModelRegistry] = None
_registry_lock = threading.Lock()


def get_model_registry() -> ModelRegistry:
    global _registry
    with _registry_lock:
        if _registry is None:
            _registry = ModelRegistry()
    return _registry


# =========================================================================
# Train / Test Split utilities
# =========================================================================

def time_series_split(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    train_ratio: float = 0.8,
    horizon: int = 0,
) -> Dict[str, pd.DataFrame]:
    """Split a time series into train and test sets.

    Three modes:
        * If horizon > 0: the last `horizon` rows are the test set.
        * If train_ratio is in (0, 1): use that fraction for training.
        * Otherwise: 80/20 split.

    Returns dict with keys 'train' and 'test'.
    """
    df = df[[date_col, value_col]].copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    df = df.dropna().sort_values(date_col).reset_index(drop=True)
    n = len(df)
    if n < 10:
        raise ValueError(f"Series too short to split (n={n})")
    if horizon > 0:
        test_size = min(horizon, max(1, n // 5))
    else:
        test_size = max(1, int(n * (1 - train_ratio)))
    test_size = min(test_size, n - 5)  # leave at least 5 rows for training
    split_idx = n - test_size
    return {
        "train": df.iloc[:split_idx].reset_index(drop=True),
        "test": df.iloc[split_idx:].reset_index(drop=True),
    }


def evaluate_on_test(
    forecast_values: List[Dict[str, Any]],
    test_df: pd.DataFrame,
    date_col: str,
    value_col: str,
) -> ModelMetrics:
    """Compare a list of forecast dicts against a held-out test set.

    Returns ModelMetrics with MAE/RMSE/MAPE.
    """
    # Build a {date_str: actual} map from the test set
    actuals: Dict[str, float] = {}
    for _, row in test_df.iterrows():
        d = pd.Timestamp(row[date_col]).strftime("%Y-%m-%d")
        actuals[d] = float(row[value_col])
    # Match forecasts to actuals by date
    pred_vals: List[float] = []
    actual_vals: List[float] = []
    for fv in forecast_values:
        d = str(fv.get("date", ""))[:10]
        if d in actuals:
            pred_vals.append(float(fv.get("forecast", 0.0)))
            actual_vals.append(actuals[d])
    if not pred_vals:
        return ModelMetrics()
    preds = pd.Series(pred_vals, dtype=float)
    acts = pd.Series(actual_vals, dtype=float)
    diff = preds - acts
    mae = float(diff.abs().mean())
    rmse = float((diff ** 2).mean() ** 0.5)
    # MAPE: avoid div by zero
    denom = acts.abs().clip(lower=1e-9)
    mape = float((diff.abs() / denom).mean() * 100.0)
    return ModelMetrics(
        mae=mae,
        rmse=rmse,
        mape=mape,
        train_rows=0,
        test_rows=len(pred_vals),
    )