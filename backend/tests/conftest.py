import os
import tempfile

import numpy as np
import pandas as pd
import pytest


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
def tmp_data_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)
