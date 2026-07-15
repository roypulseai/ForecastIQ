"""Disk-backed persistent storage for uploaded files and forecast results.

Uses simple JSON files + a thread lock. Designed to be replaced with a real
database in production but sufficient for self-hosted deployment without
losing state across restarts.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import threading
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .config import settings
from .utils import to_python

logger = logging.getLogger(__name__)


class FileMetadataStore:
    """Thread-safe persistent store for uploaded file metadata.

    Each uploaded file is recorded as a JSON entry in `files.json` inside
    `DATA_DIR`. The raw upload is kept on disk under `UPLOAD_DIR` and the
    parsed DataFrame is serialized as Parquet (or CSV as fallback) in
    `DATA_DIR/datasets/<file_id>.parquet`.
    """

    FILES_INDEX = "files.json"
    FORECASTS_INDEX = "forecasts.json"
    DATASETS_DIR = "datasets"
    FORECAST_RESULTS_DIR = "forecast_results"

    def __init__(self, data_dir: Optional[str] = None) -> None:
        self.data_dir = Path(data_dir or settings.DATA_DIR)
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.output_dir = Path(settings.OUTPUT_DIR)
        self.datasets_dir = self.data_dir / self.DATASETS_DIR
        self.results_dir = self.data_dir / self.FORECAST_RESULTS_DIR
        for d in (self.data_dir, self.upload_dir, self.output_dir,
                  self.datasets_dir, self.results_dir):
            d.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._files_index = self.data_dir / self.FILES_INDEX
        self._forecasts_index = self.data_dir / self.FORECASTS_INDEX
        self._df_cache: OrderedDict[str, pd.DataFrame] = OrderedDict()
        if not self._files_index.exists():
            self._write_json(self._files_index, {})

    # ------------------------------------------------------------------ utils
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

    # ------------------------------------------------------------------ files
    def save_upload(
        self,
        *,
        original_filename: str,
        file_type: str,
        raw_path: str,
        size: int,
        df: pd.DataFrame,
        column_mapping: Optional[Dict[str, str]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Persist a freshly uploaded file: raw bytes + parsed DataFrame + metadata."""
        with self._lock:
            file_id = self._new_id()
            file_id_safe = file_id
            # Move raw file into UPLOAD_DIR
            raw_name = f"{file_id_safe}_{Path(original_filename).name}"
            stored_raw = self.upload_dir / raw_name
            shutil.move(raw_path, stored_raw)

            # Persist DataFrame as Parquet (or CSV fallback)
            dataset_path = self.datasets_dir / f"{file_id_safe}.parquet"
            try:
                df.to_parquet(dataset_path, index=False)
            except Exception as e:
                logger.warning("Parquet write failed, falling back to CSV: %s", e)
                dataset_path = self.datasets_dir / f"{file_id_safe}.csv"
                df.to_csv(dataset_path, index=False)

            entry = {
                "file_id": file_id_safe,
                "original_filename": original_filename,
                "stored_filename": raw_name,
                "file_type": file_type,
                "size": int(size),
                "uploaded_at": datetime.now(timezone.utc).isoformat() + "Z",
                "row_count": int(len(df)),
                "columns": [str(c) for c in df.columns],
                "dataset_path": str(dataset_path),
                "raw_path": str(stored_raw),
                "column_mapping": column_mapping or {},
                "extra": extra or {},
            }
            index = self._read_json(self._files_index)
            index[file_id_safe] = entry
            self._write_json(self._files_index, index)
            return entry

    def list_files(self, file_type: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            index = self._read_json(self._files_index)
        out = list(index.values())
        if file_type:
            out = [f for f in out if f.get("file_type") == file_type]
        out.sort(key=lambda x: x.get("uploaded_at", ""), reverse=True)
        return out

    def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            index = self._read_json(self._files_index)
        return index.get(file_id)

    def get_dataframe(self, file_id: str) -> Optional[pd.DataFrame]:
        if file_id in self._df_cache:
            self._df_cache.move_to_end(file_id)
            return self._df_cache[file_id]
        entry = self.get_file(file_id)
        if not entry:
            return None
        path = Path(entry.get("dataset_path", ""))
        if not path.exists():
            return None
        try:
            if path.suffix == ".parquet":
                df = pd.read_parquet(path)
            else:
                df = pd.read_csv(path)
            self._df_cache[file_id] = df
            if len(self._df_cache) > 32:
                self._df_cache.popitem(last=False)
            return df
        except Exception as e:
            logger.warning("Failed to read dataset for file '%s': %s", file_id, e)
            return None

    def delete_file(self, file_id: str) -> bool:
        with self._lock:
            index = self._read_json(self._files_index)
            entry = index.pop(file_id, None)
            if entry is None:
                return False
            self._write_json(self._files_index, index)
            self._df_cache.pop(file_id, None)
        # Remove from disk (best effort)
        for p in (entry.get("dataset_path"), entry.get("raw_path")):
            if p:
                try:
                    Path(p).unlink(missing_ok=True)
                except Exception as e:
                    logger.warning("Failed to delete file '%s': %s", p, e)
                    pass
        return True

    def find_sales_file(self) -> Optional[Dict[str, Any]]:
        sales = self.list_files(file_type="sales")
        return sales[0] if sales else None

    def find_files_by_type(self, file_type: str) -> List[Dict[str, Any]]:
        return self.list_files(file_type=file_type)

    # -------------------------------------------------------------- forecasts
    def save_forecast(self, result: Dict[str, Any]) -> str:
        """Save a forecast result. `result` must include 'forecast_id'."""
        with self._lock:
            forecast_id = result.get("forecast_id") or self._new_id()
            result["forecast_id"] = forecast_id
            result["saved_at"] = datetime.now(timezone.utc).isoformat() + "Z"
            clean = to_python(result)
            # Persist a per-forecast JSON for full retrieval
            path = self.results_dir / f"{forecast_id}.json"
            self._write_json(path, clean)
            # Update the index with a slim summary
            index = self._read_json(self._forecasts_index)
            index[forecast_id] = {
                "forecast_id": forecast_id,
                "name": clean.get("name") or clean.get("request", {}).get("name", "Forecast"),
                "created_at": clean.get("created_at"),
                "horizon": clean.get("request", {}).get("horizon"),
                "models": list((clean.get("results") or {}).keys()),
                "best_model": clean.get("best_model"),
                "summary": clean.get("summary", {}),
            }
            self._write_json(self._forecasts_index, index)
            return forecast_id

    def list_forecasts(self) -> List[Dict[str, Any]]:
        with self._lock:
            index = self._read_json(self._forecasts_index)
        out = list(index.values())
        out.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return out

    def get_forecast(self, forecast_id: str) -> Optional[Dict[str, Any]]:
        path = self.results_dir / f"{forecast_id}.json"
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def get_forecast_summary(self, forecast_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            index = self._read_json(self._forecasts_index)
        return index.get(forecast_id)

    def delete_forecast(self, forecast_id: str) -> bool:
        with self._lock:
            index = self._read_json(self._forecasts_index)
            if forecast_id not in index:
                return False
            index.pop(forecast_id, None)
            self._write_json(self._forecasts_index, index)
        path = self.results_dir / f"{forecast_id}.json"
        try:
            path.unlink(missing_ok=True)
        except Exception as e:
            logger.warning("Failed to delete forecast file '%s': %s", path, e)
        return True
