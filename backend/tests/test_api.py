import io
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient


def _ensure_pyarrow():
    try:
        import pyarrow
        return True
    except ImportError:
        pass
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyarrow"])
        import pyarrow
        return True
    except Exception:
        return False


def test_health_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_info_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data


def test_upload_csv(auth_client):
    np.random.seed(42)
    dates = pd.date_range(start="2023-01-01", periods=30, freq="D")
    df = pd.DataFrame({"date": dates, "value": np.random.rand(30) * 100})
    csv_bytes = df.to_csv(index=False).encode()
    response = auth_client.post(
        "/api/v1/upload/sales",
        files={"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "file_id" in data


def test_upload_empty_file(auth_client):
    response = auth_client.post(
        "/api/v1/upload/sales",
        files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
    )
    assert response.status_code == 400


def test_upload_unsupported_extension(auth_client):
    response = auth_client.post(
        "/api/v1/upload/sales",
        files={"file": ("data.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert response.status_code == 400


def test_analyze_endpoint(auth_client):
    np.random.seed(42)
    dates = pd.date_range(start="2023-01-01", periods=30, freq="D")
    df = pd.DataFrame({"date": dates, "value": np.random.rand(30) * 100})
    csv_bytes = df.to_csv(index=False).encode()
    upload_resp = auth_client.post(
        "/api/v1/upload/sales",
        files={"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert upload_resp.status_code == 200
    file_id = upload_resp.json()["file_id"]
    response = auth_client.post(f"/api/v1/analyze?file_id={file_id}")
    assert response.status_code == 200
    data = response.json()
    assert "data_characteristics" in data or "validation" in data


def test_list_models(auth_client):
    response = auth_client.get("/api/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["total"], int)


def test_upload_parquet(auth_client):
    if not _ensure_pyarrow():
        pytest.skip("pyarrow not installed and could not be installed")
    np.random.seed(42)
    dates = pd.date_range(start="2023-01-01", periods=30, freq="D")
    df = pd.DataFrame({"date": dates, "value": np.random.rand(30) * 100})
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    response = auth_client.post(
        "/api/v1/upload/sales",
        files={"file": ("test.parquet", buf, "application/octet-stream")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "file_id" in data
