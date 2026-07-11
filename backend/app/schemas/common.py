"""Common shared schemas."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DataStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


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
    AUTOML = "automl"


class BusinessType(str, Enum):
    """Industry / business domain — influences model selection and defaults."""
    RETAIL = "retail"
    ECOMMERCE = "ecommerce"
    SAAS = "saas"
    MANUFACTURING = "manufacturing"
    SUPPLY_CHAIN = "supply_chain"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    ENERGY = "energy"
    HOSPITALITY = "hospitality"
    MEDIA = "media"
    OTHER = "other"


class BusinessStage(str, Enum):
    """Growth stage — affects trend handling and uncertainty modelling."""
    HYPER_GROWTH = "hyper_growth"
    GROWTH = "growth"
    MATURE = "mature"
    DECLINING = "declining"
    SEASONAL = "seasonal"
    VOLATILE = "volatile"


class FileType(str, Enum):
    SALES = "sales"
    MEDIA_PLAN = "media_plan"
    PROMOTIONS = "promotions"
    HOLIDAYS = "holidays"
    EVENTS = "events"
    WEATHER = "weather"
    COMPETITOR = "competitor"
    ECONOMIC = "economic"


FILE_TYPE_VALUES = [t.value for t in FileType]


class UploadedFileInfo(BaseModel):
    file_id: str
    filename: str
    file_type: str
    size: int
    uploaded_at: str
    status: DataStatus = DataStatus.READY
    row_count: int = 0
    columns: List[str] = Field(default_factory=list)
    column_mapping: Dict[str, str] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    valid: bool
    errors: List[str]
    warnings: List[str] = Field(default_factory=list)
    date_column: Optional[str] = None
    value_column: Optional[str] = None
    row_count: int = 0
    unique_dates: int = 0
    frequency: Optional[str] = None
    extra_columns: List[str] = Field(default_factory=list)
    column_types: Dict[str, str] = Field(default_factory=dict)


class Insight(BaseModel):
    type: str  # "info" | "warning" | "success"
    text: str


class OrderRecommendation(BaseModel):
    p: int = 1
    d: int = 0
    q: int = 1


class SeasonalOrderRecommendation(BaseModel):
    p: int = 1
    d: int = 0
    q: int = 1
    s: int = 7


class PDQRecommendation(BaseModel):
    order: OrderRecommendation
    seasonal_order: Optional[SeasonalOrderRecommendation] = None
    reason: str = ""


class LagAnalysisResult(BaseModel):
    lag: int = 0
    correlation: Optional[float] = None
    strength: str = ""  # "strong" | "moderate" | "weak"
    message: str = ""


class DataCharacteristics(BaseModel):
    length: int
    mean: float
    std: float
    cv: float
    trend: str
    seasonality: str
    stationarity: bool
    outliers_pct: float
    missing_pct: float
    min_date: Optional[str] = None
    max_date: Optional[str] = None
    pdq_recommendation: Optional[PDQRecommendation] = None
    insights: List[Insight] = Field(default_factory=list)


class ModelRecommendation(BaseModel):
    model: str
    score: float
    reason: str


class AnalysisResponse(BaseModel):
    validation: ValidationResult
    data_characteristics: DataCharacteristics
    model_recommendations: List[ModelRecommendation]


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str
    components: Dict[str, str] = Field(default_factory=dict)
