"""Forecast request/response schemas."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .common import (
    BusinessStage,
    BusinessType,
    DataStatus,
    ForecastFrequency,
    LagAnalysisResult,
    ModelType,
    ProductLevel,
    RegionLevel,
    TimeGranularity,
)


class ARIMAParams(BaseModel):
    p: int = Field(default=1, ge=0, le=10)
    d: int = Field(default=1, ge=0, le=2)
    q: int = Field(default=1, ge=0, le=10)


class SARIMAXParams(BaseModel):
    p: int = Field(default=1, ge=0, le=10)
    d: int = Field(default=1, ge=0, le=2)
    q: int = Field(default=1, ge=0, le=10)
    seasonal_p: int = Field(default=1, ge=0, le=5)
    seasonal_d: int = Field(default=1, ge=0, le=2)
    seasonal_q: int = Field(default=1, ge=0, le=5)
    seasonal_period: int = Field(default=7, ge=2, le=365)


class ProphetParams(BaseModel):
    seasonality_mode: str = "additive"
    yearly_seasonality: bool = True
    weekly_seasonality: bool = True
    daily_seasonality: bool = False
    changepoint_prior_scale: float = Field(default=0.05, gt=0)
    seasonality_prior_scale: float = Field(default=10.0, gt=0)
    holidays_prior_scale: float = Field(default=10.0, gt=0)
    country: Optional[str] = None


class LightGBMParams(BaseModel):
    n_estimators: int = Field(default=200, ge=10, le=2000)
    learning_rate: float = Field(default=0.05, gt=0, le=1.0)
    max_depth: int = Field(default=5, ge=1, le=20)
    num_leaves: int = Field(default=31, ge=2, le=255)
    min_child_samples: int = Field(default=20, ge=1, le=200)


class XGBoostParams(BaseModel):
    n_estimators: int = Field(default=200, ge=10, le=2000)
    learning_rate: float = Field(default=0.05, gt=0, le=1.0)
    max_depth: int = Field(default=5, ge=1, le=20)
    min_child_weight: int = Field(default=1, ge=1, le=200)
    subsample: float = Field(default=0.9, gt=0, le=1.0)
    colsample_bytree: float = Field(default=0.9, gt=0, le=1.0)


class WMAParams(BaseModel):
    window: int = Field(default=8, ge=2, le=365)


class ETSParams(BaseModel):
    trend: str = "add"
    seasonal: str = "add"
    seasonal_periods: int = Field(default=7, ge=2, le=365)


class ThetaParams(BaseModel):
    period: int = Field(default=7, ge=2, le=365)
    deseasonalize: bool = True


class STLParams(BaseModel):
    period: int = Field(default=7, ge=2, le=365)
    robust: bool = True


class ModelParameters(BaseModel):
    arima: Optional[ARIMAParams] = None
    sarimax: Optional[SARIMAXParams] = None
    prophet: Optional[ProphetParams] = None
    lightgbm: Optional[LightGBMParams] = None
    xgboost: Optional[XGBoostParams] = None
    wma: Optional[WMAParams] = None
    ets: Optional[ETSParams] = None
    theta: Optional[ThetaParams] = None
    stl: Optional[STLParams] = None


class AggregationConfig(BaseModel):
    time_rollup: TimeGranularity = TimeGranularity.MONTHLY
    product_level: ProductLevel = ProductLevel.CATEGORY
    region_level: RegionLevel = RegionLevel.NATIONAL
    agg_function: str = "sum"


class ForecastRequest(BaseModel):
    name: str = "Forecast"
    target_column: str = "value"
    date_column: str = "date"
    frequency: ForecastFrequency = ForecastFrequency.DAILY
    horizon: int = Field(default=30, ge=1, le=365)
    models: List[ModelType] = Field(default_factory=lambda: [ModelType.PROPHET])
    parameters: Optional[ModelParameters] = None
    ensemble_models: Optional[List[ModelType]] = None
    ensemble_weights: Optional[List[float]] = None
    include_media_plan: bool = False
    include_promotions: bool = False
    include_holidays: bool = False
    include_events: bool = False
    include_weather: bool = False
    include_competitor: bool = False
    include_economic: bool = False
    aggregation: Optional[AggregationConfig] = None
    country: Optional[str] = None
    notes: Optional[str] = None
    # Train/test split for proper held-out evaluation.
    # When < 1.0, the last (1 - ratio) rows are held out as the test set.
    # Models are trained on the train portion; the test set is used to
    # compute honest MAE/RMSE/MAPE before generating the forecast.
    # 1.0 (default) = no split, train on all data.
    train_test_split: float = Field(default=1.0, ge=0.5, le=1.0)
    # How many of the last actuals to overlay with the forecast in the
    # results chart, for visual backtesting. 0 = no overlap (forecast only).
    backtest_overlap: int = Field(default=0, ge=0, le=365)
    # Business context — influences model selection and default parameters.
    business_type: Optional[BusinessType] = None
    business_stage: Optional[BusinessStage] = None
    # Save the best model to the registry after a successful run.
    save_model: bool = False
    save_model_name: Optional[str] = None
    save_model_tags: Optional[List[str]] = None
    save_model_notes: Optional[str] = None


class ForecastValue(BaseModel):
    date: str
    forecast: float
    lower_ci: float
    upper_ci: float
    baseline: Optional[float] = None
    uplift: Optional[float] = None


class ModelRanking(BaseModel):
    model: str
    name: Optional[str] = None
    mae: Optional[float] = None
    rmse: Optional[float] = None
    mape: Optional[float] = None
    score: Optional[float] = None


class ModelResult(BaseModel):
    model_name: str
    metrics: Dict[str, float] = Field(default_factory=dict)
    forecast_values: List[ForecastValue] = Field(default_factory=list)
    baseline_values: Optional[List[ForecastValue]] = None
    feature_importance: Optional[Dict[str, float]] = None
    components: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class EnsembleResult(BaseModel):
    models_used: List[str]
    weights: List[float]
    forecast_values: List[ForecastValue]
    baseline_values: Optional[List[ForecastValue]] = None
    individual_results: List[ModelResult] = Field(default_factory=list)


class ExternalFactorAnalysis(BaseModel):
    media_plan_impact: Optional[Dict[str, Any]] = None
    promotion_impact: Optional[Dict[str, Any]] = None
    holiday_impact: Optional[Dict[str, Any]] = None
    event_impact: Optional[Dict[str, Any]] = None
    weather_impact: Optional[Dict[str, Any]] = None
    price_elasticity: Optional[float] = None
    lag_analysis: Dict[str, LagAnalysisResult] = Field(default_factory=dict)


class ForecastSummary(BaseModel):
    total_forecast: float
    total_baseline: float
    total_uplift: float
    uplift_pct: float
    avg_daily_forecast: float


class ForecastResponse(BaseModel):
    """Lightweight response returned from POST /forecast."""
    id: str
    forecast_id: str
    status: DataStatus
    message: str
    best_model: Optional[str] = None
    model_rankings: List[ModelRanking] = Field(default_factory=list)
    summary: Optional[ForecastSummary] = None


class ForecastDetail(BaseModel):
    """Full forecast result returned from GET /forecast/{id}."""
    forecast_id: str
    name: str
    created_at: str
    request: ForecastRequest
    results: Dict[str, ModelResult]
    ensemble: Optional[EnsembleResult] = None
    external_factor_analysis: Optional[ExternalFactorAnalysis] = None
    summary: Optional[ForecastSummary] = None


class ForecastListItem(BaseModel):
    forecast_id: str
    name: str
    created_at: str
    horizon: int
    models: List[str] = Field(default_factory=list)
    best_model: Optional[str] = None


class ForecastListResponse(BaseModel):
    items: List[ForecastListItem]
    total: int
