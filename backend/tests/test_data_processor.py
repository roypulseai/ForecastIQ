import numpy as np
import pandas as pd
import pytest

from app.services.data_processor import DataProcessor


@pytest.fixture
def processor():
    return DataProcessor()


def test_validate_sales_valid(processor, sample_sales_df):
    clean, _ = processor.process(sample_sales_df, "sales")
    result = processor.validate_sales(clean)
    assert result["valid"] is True
    assert len(result["errors"]) == 0
    assert result["date_column"] is not None
    assert result["value_column"] is not None
    assert result["row_count"] > 0


def test_validate_sales_missing_date(processor):
    df = pd.DataFrame({"value": [1, 2, 3]})
    result = processor.validate_sales(df)
    assert result["valid"] is False
    assert any("date" in e.lower() for e in result["errors"])


def test_validate_sales_missing_value(processor):
    df = pd.DataFrame({"date": pd.date_range("2023-01-01", periods=5)})
    result = processor.validate_sales(df)
    assert result["valid"] is False
    assert any("value" in e.lower() or "numeric" in e.lower() for e in result["errors"])


def test_validate_sales_non_numeric_value(processor):
    dates = pd.date_range(start="2023-01-01", periods=20, freq="D")
    df = pd.DataFrame({"date": dates, "value": ["foo"] * 20})
    clean, _ = processor.process(df, "sales")
    assert (clean["value"] == 0.0).all()


def test_normalize_sales_sum_duplicates(processor):
    dates = pd.date_range(start="2023-01-01", periods=5, freq="D")
    df = pd.DataFrame({
        "date": [dates[0], dates[0], dates[1], dates[1], dates[2]],
        "value": [10, 20, 30, 40, 50],
    })
    clean, _ = processor.process(df, "sales")
    row_for_date0 = clean[clean["date"] == dates[0]]
    assert len(row_for_date0) == 1
    assert float(row_for_date0["value"].iloc[0]) == 30.0


def test_normalize_sales_preserves_column_names(processor, sample_sales_df):
    clean, mapping = processor.process(sample_sales_df, "sales")
    assert "date" in clean.columns
    assert "value" in clean.columns


def test_downsample_for_forecasting_weekly(processor):
    np.random.seed(42)
    dates = pd.date_range(start="2015-01-01", periods=2500, freq="D")
    df = pd.DataFrame({"date": dates, "value": np.random.rand(2500) * 100})
    result, exog_data, info = DataProcessor.downsample_for_forecasting(
        df, "date", "value", max_points=500
    )
    assert info["downsample_applied"] is True
    assert len(result) <= 500
    assert exog_data is None


def test_downsample_for_forecasting_insufficient_data(processor):
    np.random.seed(42)
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    df = pd.DataFrame({"date": dates, "value": np.random.rand(100) * 100})
    result, exog_data, info = DataProcessor.downsample_for_forecasting(
        df, "date", "value", max_points=500
    )
    assert info["downsample_applied"] is False
    assert len(result) == 100
    assert exog_data is None
