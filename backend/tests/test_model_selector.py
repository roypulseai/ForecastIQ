import numpy as np
import pandas as pd
import pytest

from app.services.model_selector import ModelSelector


@pytest.fixture
def selector():
    return ModelSelector()


def test_cross_validate_returns_metrics(selector, sample_sales_df):
    result = selector.cross_validate(
        sample_sales_df, "date", "value", "ets", horizon=7, n_folds=3
    )
    assert "mae" in result
    assert "rmse" in result
    assert "mape" in result
    assert result["mae"] is not None
    assert result["rmse"] is not None
    assert result["mape"] is not None


def test_cross_validate_with_exog(selector, sample_sales_df, sample_exog_data):
    result = selector.cross_validate(
        sample_sales_df, "date", "value", "wma",
        horizon=7, n_folds=3, exog_data=sample_exog_data
    )
    assert "mae" in result
    assert "rmse" in result
    assert "mape" in result


def test_cross_validate_insufficient_data(selector):
    df = pd.DataFrame({
        "date": pd.date_range("2023-01-01", periods=5),
        "value": [1, 2, 3, 4, 5],
    })
    result = selector.cross_validate(df, "date", "value", "ets", horizon=7)
    assert result["mae"] is None
    assert result["rmse"] is None
    assert result["mape"] is None


def test_analyze_data_returns_characteristics(selector, sample_sales_df):
    chars = selector.analyze_data(sample_sales_df, "date", "value")
    assert "trend" in chars
    assert "seasonality" in chars
    assert "stationarity" in chars
    assert "mean" in chars
    assert "std" in chars
    assert chars["length"] > 0
    assert chars["trend"] in ("increasing", "decreasing", "stable", "unknown")
    assert chars["seasonality"] in ("none", "weekly", "monthly", "yearly")
