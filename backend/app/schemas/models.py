from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class ForecastFrequency(str, Enum):
    DAILY = "D"
    WEEKLY = "W"
    FORTNIGHT = "F"
    MONTHLY = "M"
    QUARTERLY = "Q"
    YEARLY = "Y"

class TimeGranularity(str, Enum):
    DAILY = "D"
    WEEKLY = "W"
    FORTNIGHT = "F"
    MONTHLY = "M"
    QUARTERLY = "Q"
    YEARLY = "Y"

class ProductLevel(str, Enum):
    SKU = "sku"
    PRODUCT = "product"
    CATEGORY = "category"
    SUB_CATEGORY = "sub_category"
    PORTFOLIO = "portfolio"
    STORE = "store"
    REGION = "region"

class RegionLevel(str, Enum):
    STORE = "store"
    REGION = "region"
    NATIONAL = "national"

class ModelType(str, Enum):
    ARIMA = "arima"
    SARIMAX = "sarimax"
    PROPHET = "prophet"
    LIGHTGBM = "lightgbm"
    XGBOOST = "xgboost"
    WMA = "wma"
    ETS = "ets"
    THETA = "theta"
    STL = "stl"
    ENSEMBLE = "ensemble"

class DataStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"

class AggregationConfig(BaseModel):
    time_rollup: TimeGranularity = TimeGranularity.MONTHLY
    product_level: ProductLevel = ProductLevel.CATEGORY
    region_level: RegionLevel = RegionLevel.NATIONAL
    agg_function: str = "sum"

class UploadedFile(BaseModel):
    id: str
    filename: str
    file_type: str
    size: int
    uploaded_at: datetime
    status: DataStatus

class TimeSeriesData(BaseModel):
    date_column: str
    value_column: str
    entity_columns: List[str] = []
    frequency: ForecastFrequency = ForecastFrequency.DAILY

class MediaPlanData(BaseModel):
    channel: str
    spend: float
    start_date: str
    end_date: str
    reach: Optional[float] = None
    impressions: Optional[float] = None

class PromotionData(BaseModel):
    promo_id: str
    promo_type: str
    discount_percent: float
    start_date: str
    end_date: str

class HolidayEventData(BaseModel):
    date: str
    name: str
    type: str
    impact_factor: float = 1.0

class ARIMAParams(BaseModel):
    p: int = Field(default=1, ge=0, le=10, description="AR order")
    d: int = Field(default=1, ge=0, le=2, description="Differencing order")
    q: int = Field(default=1, ge=0, le=10, description="MA order")

class SARIMAXParams(BaseModel):
    p: int = Field(default=1, ge=0, le=10, description="AR order")
    d: int = Field(default=1, ge=0, le=2, description="Differencing order")
    q: int = Field(default=1, ge=0, le=10, description="MA order")
    seasonal_p: int = Field(default=1, ge=0, le=5, description="Seasonal AR order")
    seasonal_d: int = Field(default=1, ge=0, le=2, description="Seasonal differencing")
    seasonal_q: int = Field(default=1, ge=0, le=5, description="Seasonal MA order")
    seasonal_period: int = Field(default=7, ge=2, le=365, description="Seasonal period (days)")

class ProphetParams(BaseModel):
    seasonality_mode: str = Field(default="additive", description="additive or multiplicative")
    yearly_seasonality: bool = Field(default=True, description="Include yearly seasonality")
    weekly_seasonality: bool = Field(default=True, description="Include weekly seasonality")
    daily_seasonality: bool = Field(default=False, description="Include daily seasonality")
    changepoint_prior_scale: float = Field(default=0.05, ge=0.001, le=10, description="Trend changepoint flexibility")
    seasonality_prior_scale: float = Field(default=10.0, ge=0.01, le=100, description="Seasonality flexibility")
    holidays_prior_scale: float = Field(default=10.0, ge=0.01, le=100, description="Holidays flexibility")

class LightGBMParams(BaseModel):
    n_estimators: int = Field(default=100, ge=10, le=1000, description="Number of boosting iterations")
    learning_rate: float = Field(default=0.1, ge=0.01, le=1.0, description="Step size shrinkage")
    max_depth: int = Field(default=5, ge=1, le=20, description="Maximum tree depth")
    num_leaves: int = Field(default=31, ge=2, le=255, description="Number of leaves")
    min_child_samples: int = Field(default=20, ge=1, le=100, description="Minimum samples in leaf")

class XGBoostParams(BaseModel):
    n_estimators: int = Field(default=100, ge=10, le=1000, description="Number of boosting iterations")
    learning_rate: float = Field(default=0.1, ge=0.01, le=1.0, description="Step size shrinkage")
    max_depth: int = Field(default=5, ge=1, le=20, description="Maximum tree depth")
    min_child_weight: int = Field(default=1, ge=1, le=100, description="Minimum child weight")
    subsample: float = Field(default=1.0, ge=0.1, le=1.0, description="Subsample ratio")
    colsample_bytree: float = Field(default=1.0, ge=0.1, le=1.0, description="Column subsample ratio")

class WMAParams(BaseModel):
    window: int = Field(default=8, ge=2, le=365, description="Lookback window for weighted average")

class ETSParams(BaseModel):
    trend: str = Field(default="add", description="Trend type (add, mul, or None)")
    seasonal: str = Field(default="add", description="Seasonal type (add, mul, or None)")
    seasonal_periods: int = Field(default=7, ge=2, le=365, description="Seasonal period")

class ThetaParams(BaseModel):
    period: int = Field(default=7, ge=2, le=365, description="Period for deseasonalization")
    deseasonalize: bool = Field(default=True, description="Whether to deseasonalize")

class STLParams(BaseModel):
    period: int = Field(default=7, ge=2, le=365, description="Seasonal period")
    robust: bool = Field(default=True, description="Robust fitting")

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

class ForecastRequest(BaseModel):
    name: str
    target_column: str
    date_column: str
    frequency: ForecastFrequency
    horizon: int = Field(ge=1, le=365)
    models: List[ModelType] = [ModelType.PROPHET]
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
    include_hierarchy: bool = False
    aggregation: Optional[AggregationConfig] = None
    country: Optional[str] = None

class ForecastResponse(BaseModel):
    id: str
    status: DataStatus
    message: str
    best_model: Optional[ModelType] = None
    model_rankings: Optional[List[Dict[str, Any]]] = None

class WhatIfScenario(BaseModel):
    name: str
    scenario_type: str
    parameters: Dict[str, Any]

class WhatIfRequest(BaseModel):
    forecast_id: str
    scenarios: List[WhatIfScenario]

class WhatIfResponse(BaseModel):
    forecast_id: str
    scenarios: List[Dict[str, Any]]
    comparison: Dict[str, Any]

class AggregationRequest(BaseModel):
    forecast_id: str
    time_granularity: TimeGranularity = TimeGranularity.MONTHLY
    product_level: ProductLevel = ProductLevel.CATEGORY
    region_level: RegionLevel = RegionLevel.NATIONAL
    agg_function: str = "sum"

class ForecastValue(BaseModel):
    date: str
    forecast: float
    lower_ci: float
    upper_ci: float
    baseline: Optional[float] = None
    uplift: Optional[float] = None
    sku: Optional[str] = None
    product: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    portfolio: Optional[str] = None
    region: Optional[str] = None
    store: Optional[str] = None

class AggregatedForecast(BaseModel):
    granularity: str
    group_by: str
    values: List[Dict[str, Any]]
    summary: Optional[Dict[str, Any]] = None

class HierarchicalForecast(BaseModel):
    sku_level: Optional[List[ForecastValue]] = None
    product_level: Optional[List[ForecastValue]] = None
    category_level: Optional[List[ForecastValue]] = None
    sub_category_level: Optional[List[ForecastValue]] = None
    portfolio_level: Optional[List[ForecastValue]] = None
    region_level: Optional[List[ForecastValue]] = None
    national_level: Optional[List[ForecastValue]] = None
    time_granularity: TimeGranularity = TimeGranularity.MONTHLY

class ModelResult(BaseModel):
    model_name: str
    forecast_values: List[ForecastValue]
    baseline_values: Optional[List[ForecastValue]] = None
    metrics: Dict[str, float]
    feature_importance: Optional[Dict[str, float]] = None
    components: Optional[Dict[str, Any]] = None

class EnsembleResult(BaseModel):
    models_used: List[str]
    weights: List[float]
    forecast_values: List[ForecastValue]
    baseline_values: Optional[List[ForecastValue]] = None
    individual_results: List[ModelResult]

class ExternalFactorAnalysis(BaseModel):
    media_plan_impact: Optional[Dict[str, Any]] = None
    promotion_impact: Optional[Dict[str, Any]] = None
    holiday_impact: Optional[Dict[str, Any]] = None
    weather_impact: Optional[Dict[str, Any]] = None
    price_elasticity: Optional[float] = None

class ForecastResult(BaseModel):
    forecast_id: str
    request: ForecastRequest
    results: Dict[str, ModelResult]
    ensemble: Optional[EnsembleResult] = None
    external_factor_analysis: Optional[ExternalFactorAnalysis] = None
    hierarchical_forecast: Optional[HierarchicalForecast] = None
    aggregated_forecasts: Optional[Dict[str, AggregatedForecast]] = None
    created_at: datetime
