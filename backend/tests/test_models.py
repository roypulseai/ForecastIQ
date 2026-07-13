import numpy as np
import pandas as pd
import pytest


FORECAST_MODELS = [
    ("ets", {"ets": {"trend": "add", "seasonal": None, "seasonal_periods": 7}}),
    ("stl", {"stl": {"period": 7, "robust": True}}),
    ("theta", {"theta": {"period": 7, "deseasonalize": True}}),
    ("wma", {"wma": {"window": 8}}),
    ("arima", {"arima": {"p": 1, "d": 1, "q": 1}}),
    ("sarimax", {"sarimax": {"p": 1, "d": 1, "q": 1, "seasonal_p": 0, "seasonal_d": 0, "seasonal_q": 0, "seasonal_period": 7}}),
    ("lightgbm", {"lightgbm": {"n_estimators": 50, "learning_rate": 0.1, "max_depth": 3}}),
    ("xgboost", {"xgboost": {"n_estimators": 50, "learning_rate": 0.1, "max_depth": 3}}),
]


def test_ets_fit_and_forecast(sample_sales_df):
    from app.services.models.ets_model import ETSForecaster
    model = ETSForecaster()
    model.fit(sample_sales_df, "date", "value", frequency="D")
    result = model.forecast(7)
    assert len(result) == 7
    assert all("date" in r and "forecast" in r and "lower_ci" in r and "upper_ci" in r for r in result)


def test_stl_fit_and_forecast(sample_sales_df):
    from app.services.models.stl_model import STLForecaster
    model = STLForecaster()
    model.fit(sample_sales_df, "date", "value", frequency="D")
    result = model.forecast(7)
    assert len(result) == 7
    assert all("date" in r and "forecast" in r and "lower_ci" in r and "upper_ci" in r for r in result)


def test_theta_fit_and_forecast(sample_sales_df):
    from app.services.models.theta_model import ThetaForecaster
    model = ThetaForecaster()
    model.fit(sample_sales_df, "date", "value", frequency="D")
    result = model.forecast(7)
    assert len(result) == 7
    assert all("date" in r and "forecast" in r and "lower_ci" in r and "upper_ci" in r for r in result)


def test_wma_fit_and_forecast(sample_sales_df):
    from app.services.models.wma_model import WMAForecaster
    model = WMAForecaster()
    model.fit(sample_sales_df, "date", "value", frequency="D")
    result = model.forecast(7)
    assert len(result) == 7
    assert all("date" in r and "forecast" in r and "lower_ci" in r and "upper_ci" in r for r in result)


def test_arima_fit_and_forecast(sample_sales_df):
    from app.services.models.arima import ARIMAForecaster
    model = ARIMAForecaster()
    model.fit(sample_sales_df, "date", "value", frequency="D")
    result = model.forecast(7)
    assert len(result) == 7
    assert all("date" in r and "forecast" in r and "lower_ci" in r and "upper_ci" in r for r in result)


def test_sarimax_fit_and_forecast(sample_sales_df):
    from app.services.models.arima import SARIMAXForecaster
    model = SARIMAXForecaster()
    model.fit(sample_sales_df, "date", "value", frequency="D")
    result = model.forecast(7)
    assert len(result) == 7
    assert all("date" in r and "forecast" in r and "lower_ci" in r and "upper_ci" in r for r in result)


def test_lightgbm_fit_and_forecast(sample_sales_df):
    from app.services.models.lightgbm_model import LightGBMForecaster
    model = LightGBMForecaster(n_estimators=50, learning_rate=0.1, max_depth=3)
    model.fit(sample_sales_df, "date", "value", frequency="D")
    result = model.forecast(7)
    assert len(result) == 7
    assert all("date" in r and "forecast" in r and "lower_ci" in r and "upper_ci" in r for r in result)


def test_xgboost_fit_and_forecast(sample_sales_df):
    from app.services.models.xgboost_model import XGBoostForecaster
    model = XGBoostForecaster(n_estimators=50, learning_rate=0.1, max_depth=3)
    model.fit(sample_sales_df, "date", "value", frequency="D")
    result = model.forecast(7)
    assert len(result) == 7
    assert all("date" in r and "forecast" in r and "lower_ci" in r and "upper_ci" in r for r in result)


@pytest.mark.parametrize("model_type,params", FORECAST_MODELS)
def test_model_forecast_correct_length(sample_sales_df, model_type, params):
    from app.services.model_selector import ModelSelector
    selector = ModelSelector()
    horizon = 10
    model = selector.get_model(model_type, params)
    model.fit(sample_sales_df, "date", "value", frequency="D")
    result = model.forecast(horizon)
    assert len(result) == horizon


@pytest.mark.parametrize("model_type,params", FORECAST_MODELS)
def test_model_forecast_has_required_keys(sample_sales_df, model_type, params):
    from app.services.model_selector import ModelSelector
    selector = ModelSelector()
    model = selector.get_model(model_type, params)
    model.fit(sample_sales_df, "date", "value", frequency="D")
    result = model.forecast(5)
    for r in result:
        assert "date" in r
        assert "forecast" in r
        assert "lower_ci" in r
        assert "upper_ci" in r


def test_model_forecast_ci_widens_with_horizon(sample_sales_df):
    from app.services.models.stl_model import STLForecaster
    from app.services.models.ets_model import ETSForecaster

    for ForecasterCls in [STLForecaster, ETSForecaster]:
        model = ForecasterCls()
        model.fit(sample_sales_df, "date", "value", frequency="D")
        result = model.forecast(14)
        widths = [r["upper_ci"] - r["lower_ci"] for r in result]
        assert widths[-1] >= widths[0]
