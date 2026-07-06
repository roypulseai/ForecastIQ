from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class ForecastFrequency(str, Enum):
    DAILY = "D"
    WEEKLY = "W"
    MONTHLY = "M"

class ModelType(str, Enum):
    ARIMA = "arima"
    SARIMAX = "sarimax"
    PROPHET = "prophet"
    LIGHTGBM = "lightgbm"
    WMA = "wma"
    ENSEMBLE = "ensemble"

class DataStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"

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

class ForecastRequest(BaseModel):
    name: str
    target_column: str
    date_column: str
    frequency: ForecastFrequency
    horizon: int = Field(ge=1, le=365)
    models: List[ModelType] = [ModelType.PROPHET]
    ensemble_models: Optional[List[ModelType]] = None
    ensemble_weights: Optional[List[float]] = None
    include_media_plan: bool = False
    include_promotions: bool = False
    include_holidays: bool = False
    include_events: bool = False
    seasonality_mode: str = "additive"
    country: Optional[str] = None

class ForecastResponse(BaseModel):
    id: str
    status: DataStatus
    message: str
    best_model: Optional[ModelType] = None
    model_rankings: Optional[List[Dict[str, Any]]] = None

class ModelResult(BaseModel):
    model_name: str
    forecast_values: List[Dict[str, Any]]
    metrics: Dict[str, float]
    feature_importance: Optional[Dict[str, float]] = None

class EnsembleResult(BaseModel):
    models_used: List[str]
    weights: List[float]
    forecast_values: List[Dict[str, Any]]
    individual_results: List[ModelResult]

class ForecastResult(BaseModel):
    forecast_id: str
    request: ForecastRequest
    results: Dict[str, ModelResult]
    ensemble: Optional[EnsembleResult] = None
    created_at: datetime
