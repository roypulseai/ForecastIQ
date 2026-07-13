import io

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient


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


def test_upload_csv(client):
    np.random.seed(42)
    dates = pd.date_range(start="2023-01-01", periods=30, freq="D")
    df = pd.DataFrame({"date": dates, "value": np.random.rand(30) * 100})
    csv_bytes = df.to_csv(index=False).encode()
    response = client.post(
        "/api/v1/upload/sales",
        files={"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "file_id" in data


def test_upload_empty_file(client):
    response = client.post(
        "/api/v1/upload/sales",
        files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
    )
    assert response.status_code == 400


def test_upload_unsupported_extension(client):
    response = client.post(
        "/api/v1/upload/sales",
        files={"file": ("data.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert response.status_code == 400


def test_analyze_endpoint(client):
    np.random.seed(42)
    dates = pd.date_range(start="2023-01-01", periods=30, freq="D")
    df = pd.DataFrame({"date": dates, "value": np.random.rand(30) * 100})
    csv_bytes = df.to_csv(index=False).encode()
    upload_resp = client.post(
        "/api/v1/upload/sales",
        files={"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    file_id = upload_resp.json()["file_id"]
    response = client.post(f"/api/v1/analyze?file_id={file_id}")
    assert response.status_code == 200
    data = response.json()
    assert "data_characteristics" in data or "validation" in data


def test_list_models(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_upload_parquet(client):
    pdpytest = pytest.importorskip("pyarrow", reason="pyarrow not installed for parquet tests")
    np.random.seed(42)
    dates = pd.date_range(start="2023-01-01", periods=30, freq="D")
    df = pd.DataFrame({"date": dates, "value": np.random.rand(30) * 100})
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    response = client.post(
        "/api/v1/upload/sales",
        files={"file": ("test.parquet", buf, "application/octet-stream")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "file_id" in data
