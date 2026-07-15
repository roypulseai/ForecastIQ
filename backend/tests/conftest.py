import os
import shutil
import tempfile
import uuid
import atexit

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

_tmp_data_dir = tempfile.mkdtemp()
atexit.register(lambda: shutil.rmtree(_tmp_data_dir, ignore_errors=True))

from app.core.config import settings

settings.DATA_DIR = _tmp_data_dir
settings.UPLOAD_DIR = os.path.join(_tmp_data_dir, "uploads")
settings.OUTPUT_DIR = os.path.join(_tmp_data_dir, "outputs")
settings.TEMPLATE_DIR = os.path.join(_tmp_data_dir, "templates")
settings.ensure_dirs()

from app.main import app


@pytest.fixture
def sample_sales_df():
    np.random.seed(42)
    dates = pd.date_range(start="2023-01-01", periods=90, freq="D")
    values = 100 + np.cumsum(np.random.randn(90) * 5)
    categories = np.random.choice(["A", "B", "C"], size=90)
    return pd.DataFrame({"date": dates, "value": values, "category": categories})


@pytest.fixture
def sample_sales_df_duplicate_dates():
    np.random.seed(42)
    dates = pd.date_range(start="2023-01-01", periods=30, freq="D")
    rows = []
    for d in dates:
        for cat in ["X", "Y"]:
            rows.append({"date": d, "value": np.random.uniform(50, 150), "category": cat})
    return pd.DataFrame(rows)


@pytest.fixture
def sample_exog_data():
    np.random.seed(42)
    dates = pd.date_range(start="2023-01-01", periods=90, freq="D")
    promotions = pd.DataFrame({
        "date": dates,
        "discount": np.random.choice([0, 5, 10, 15], size=90),
    })
    holidays = pd.DataFrame({
        "date": dates[::7],
        "holiday_impact": np.ones(13),
    })
    return {"promotions": promotions, "holidays": holidays}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_client():
    test_client = TestClient(app)
    username = f"testuser_{uuid.uuid4().hex[:8]}"
    password = "testpass123"
    register_resp = test_client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": password, "email": "test@example.com"},
    )
    if register_resp.status_code not in (200, 201, 409):
        raise RuntimeError(f"Failed to register test user: {register_resp.text}")
    login_resp = test_client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    if login_resp.status_code not in (200, 201):
        raise RuntimeError(f"Failed to login test user: {login_resp.text}")
    token = login_resp.json()["access_token"]
    test_client.headers["Authorization"] = f"Bearer {token}"
    return test_client
