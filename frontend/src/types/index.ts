export type FileType =
  | 'sales'
  | 'media_plan'
  | 'promotions'
  | 'holidays'
  | 'events'
  | 'weather'
  | 'competitor'
  | 'economic';

export const FILE_TYPES: FileType[] = [
  'sales',
  'media_plan',
  'promotions',
  'holidays',
  'events',
  'weather',
  'competitor',
  'economic',
];

export const FILE_TYPE_LABELS: Record<FileType, string> = {
  sales: 'Sales Data',
  media_plan: 'Media Plan',
  promotions: 'Promotions',
  holidays: 'Holidays',
  events: 'Events',
  weather: 'Weather',
  competitor: 'Competitor',
  economic: 'Economic',
};

export const FILE_TYPE_DESCRIPTIONS: Record<FileType, string> = {
  sales: 'Primary sales history with date and value columns',
  media_plan: 'Marketing spend across channels',
  promotions: 'Discount and promotion events',
  holidays: 'Holiday calendar with impact factors',
  events: 'Special events affecting demand',
  weather: 'Weather data by date and region',
  competitor: 'Competitor pricing and activity',
  economic: 'Macroeconomic indicators',
};

export interface UploadedFile {
  file_id: string;
  filename: string;
  type: string;
  size: number;
  row_count: number;
  columns: string[];
  column_mapping?: Record<string, string>;
  warnings?: string[];
  status?: string;
  uploaded_at?: string;
}

export interface FilesListResponse {
  items: UploadedFile[];
  total: number;
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  date_column: string | null;
  value_column: string | null;
  row_count: number;
  frequency: string | null;
  extra_columns: string[];
}

export interface DataCharacteristics {
  length: number;
  mean: number;
  std: number;
  cv: number;
  trend: string;
  seasonality: string;
  stationarity: boolean;
  outliers_pct: number;
  missing_pct: number;
  min_date: string | null;
  max_date: string | null;
}

export interface ModelRecommendation {
  model: string;
  score: number;
  reason: string;
}

export interface AnalysisResponse {
  validation: ValidationResult;
  data_characteristics: DataCharacteristics;
  model_recommendations: ModelRecommendation[];
}

export type ModelType =
  | 'arima'
  | 'sarimax'
  | 'prophet'
  | 'lightgbm'
  | 'xgboost'
  | 'wma'
  | 'ets'
  | 'theta'
  | 'stl'
  | 'ensemble';

export const MODEL_TYPES: ModelType[] = [
  'arima',
  'sarimax',
  'prophet',
  'lightgbm',
  'xgboost',
  'wma',
  'ets',
  'theta',
  'stl',
];

export const MODEL_LABELS: Record<string, string> = {
  arima: 'ARIMA',
  sarimax: 'SARIMAX',
  prophet: 'Prophet',
  lightgbm: 'LightGBM',
  xgboost: 'XGBoost',
  wma: 'Weighted Moving Average',
  ets: 'ETS',
  theta: 'Theta',
  stl: 'STL',
  ensemble: 'Ensemble',
};

export const MODEL_DESCRIPTIONS: Record<string, string> = {
  arima: 'Classical statistical model for stationary series. Best for short, stable data.',
  sarimax: 'Seasonal ARIMA with exogenous regressors. Handles seasonality + external factors.',
  prophet: 'Facebook Prophet. Robust to missing data, holidays, and changepoints.',
  lightgbm: 'Gradient boosting on lagged features. Captures complex nonlinear patterns.',
  xgboost: 'XGBoost regressor. Fast, accurate, handles many features.',
  wma: 'Weighted Moving Average. Simple baseline for stable demand.',
  ets: 'Exponential smoothing with trend + seasonality.',
  theta: 'Theta method. Reliable for trend-seasonal series.',
  stl: 'STL decomposition + ARIMA on deseasonalized series.',
  ensemble: 'Weighted average of the best-performing models.',
};

export type Frequency = 'D' | 'W' | 'F' | 'M' | 'Q' | 'Y';
export type TimeGranularity = 'D' | 'W' | 'M' | 'Q' | 'Y';
export type ProductLevel =
  | 'sku'
  | 'product'
  | 'category'
  | 'sub_category'
  | 'portfolio'
  | 'store'
  | 'region';
export type RegionLevel = 'store' | 'region' | 'national';

export interface ModelParameters {
  arima?: { p: number; d: number; q: number };
  sarimax?: {
    p: number;
    d: number;
    q: number;
    seasonal_p: number;
    seasonal_d: number;
    seasonal_q: number;
    seasonal_period: number;
  };
  prophet?: {
    seasonality_mode: 'additive' | 'multiplicative';
    yearly_seasonality: boolean;
    weekly_seasonality: boolean;
    daily_seasonality: boolean;
    changepoint_prior_scale: number;
    seasonality_prior_scale: number;
    holidays_prior_scale: number;
  };
  lightgbm?: {
    n_estimators: number;
    learning_rate: number;
    max_depth: number;
    num_leaves: number;
    min_child_samples: number;
  };
  xgboost?: {
    n_estimators: number;
    learning_rate: number;
    max_depth: number;
    min_child_weight: number;
    subsample: number;
    colsample_bytree: number;
  };
  wma?: { window: number };
  ets?: { trend: 'add' | 'mul' | 'none'; seasonal: 'add' | 'mul' | 'none'; seasonal_periods: number };
  theta?: { period: number; deseasonalize: boolean };
  stl?: { period: number; robust: boolean };
}

export interface AggregationConfig {
  time_rollup: TimeGranularity;
  product_level: ProductLevel;
  region_level: RegionLevel;
  agg_function: 'sum' | 'mean' | 'median';
}

export interface ForecastRequest {
  name: string;
  target_column: string;
  date_column: string;
  frequency: Frequency;
  horizon: number;
  models: ModelType[];
  parameters?: ModelParameters;
  ensemble_models?: ModelType[];
  ensemble_weights?: number[];
  include_media_plan: boolean;
  include_promotions: boolean;
  include_holidays: boolean;
  include_events: boolean;
  include_weather: boolean;
  include_competitor: boolean;
  include_economic: boolean;
  aggregation?: AggregationConfig;
  country?: string;
  notes?: string;
  // Train/test split for proper evaluation (0..1). Default 1.0 = no split.
  // When < 1.0, the last (1-ratio) rows are held out and the test metrics
  // are computed before forecasting the next horizon.
  train_test_split?: number;
  // How many of the last actuals to overlay with the forecast (backtesting).
  // E.g. 30 means the chart shows the last 30 days of actuals alongside the
  // forecast so you can visually compare. 0 = no overlap.
  backtest_overlap?: number;
  // Save the best model to the registry after a successful run.
  save_model?: boolean;
  // Optional name for the saved model.
  save_model_name?: string;
}

export interface ForecastValue {
  date: string;
  forecast: number;
  lower_ci: number;
  upper_ci: number;
  baseline?: number | null;
  uplift?: number | null;
}

export interface ModelRanking {
  model: string;
  name?: string | null;
  mae?: number | null;
  rmse?: number | null;
  mape?: number | null;
  score?: number | null;
}

export interface ModelResult {
  model_name: string;
  metrics: Record<string, number>;
  forecast_values: ForecastValue[];
  baseline_values?: ForecastValue[] | null;
  feature_importance?: Record<string, number> | null;
  components?: Record<string, unknown> | null;
  error?: string | null;
}

export interface EnsembleResult {
  models_used: string[];
  weights: number[];
  forecast_values: ForecastValue[];
  baseline_values?: ForecastValue[] | null;
  individual_results: ModelResult[];
}

export interface ExternalFactorAnalysis {
  media_plan_impact?: Record<string, unknown> | null;
  promotion_impact?: Record<string, unknown> | null;
  holiday_impact?: Record<string, unknown> | null;
  event_impact?: Record<string, unknown> | null;
  weather_impact?: Record<string, unknown> | null;
  price_elasticity?: number | null;
}

export interface ForecastSummary {
  total_forecast: number;
  total_baseline: number;
  total_uplift: number;
  uplift_pct: number;
  avg_daily_forecast: number;
}

export interface ForecastResponse {
  id: string;
  forecast_id: string;
  status: string;
  message: string;
  best_model?: string | null;
  model_rankings: ModelRanking[];
  summary: ForecastSummary | null;
}

export interface ForecastDetail {
  forecast_id: string;
  name: string;
  created_at: string;
  request: ForecastRequest;
  results: Record<string, ModelResult>;
  ensemble?: EnsembleResult | null;
  external_factor_analysis?: ExternalFactorAnalysis | null;
  summary?: ForecastSummary | null;
}

export interface ForecastListItem {
  forecast_id: string;
  name: string;
  created_at: string;
  horizon: number;
  models: string[];
  best_model?: string | null;
}

export interface ForecastListResponse {
  items: ForecastListItem[];
  total: number;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  timestamp: string;
  components: Record<string, string>;
}

export type JobStatusValue = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface JobStatus {
  job_id: string;
  job_type: string;
  status: JobStatusValue;
  progress: number;
  message: string;
  error?: string | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  request?: Record<string, unknown> | null;
}

export interface DownsampleInfo {
  downsample_applied: boolean;
  original_rows: number;
  new_rows: number;
  reason: string | null;
  aggregation_level: string | null;
}

// ============================================================================
// Model registry
// ============================================================================
export interface ModelMetricsSaved {
  mae: number | null;
  rmse: number | null;
  mape: number | null;
  r2?: number | null;
  train_rows?: number;
  test_rows?: number;
  cv_mae?: number | null;
  cv_rmse?: number | null;
  cv_mape?: number | null;
}

export interface TrainingConfig {
  date_column: string;
  value_column: string;
  frequency: string;
  train_test_split: number;
  horizon_used: number;
  extra_columns: string[];
  hyperparameters: Record<string, unknown>;
  exogenous_used: string[];
}

export interface SavedModelMeta {
  model_id: string;
  name: string;
  model_type: string;
  framework: 'pickle' | 'joblib' | 'prophet' | 'statsmodels';
  created_at: string;
  updated_at: string;
  file_size: number;
  sha256: string;
  metrics: ModelMetricsSaved;
  training: TrainingConfig;
  train_start: string | null;
  train_end: string | null;
  test_start: string | null;
  test_end: string | null;
  source_file_id: string | null;
  source_forecast_id: string | null;
  tags: string[];
  notes: string;
}

export interface SavedModelsListResponse {
  items: SavedModelMeta[];
  total: number;
  limit: number;
  offset: number;
}

export interface TrainRequest {
  model_type?: string;
  models?: string[];
  file_id?: string;
  train_test_split?: number;
  horizon?: number;
  date_column?: string;
  target_column?: string;
  frequency?: Frequency;
  parameters?: ModelParameters;
  name?: string;
  notes?: string;
  tags?: string[];
  include_media_plan?: boolean;
  include_promotions?: boolean;
  include_holidays?: boolean;
  include_events?: boolean;
  include_weather?: boolean;
  include_competitor?: boolean;
  include_economic?: boolean;
}

export interface TrainResult {
  split: {
    train_rows: number;
    test_rows: number;
    train_start: string | null;
    train_end: string | null;
    test_start: string | null;
    test_end: string | null;
    train_ratio: number;
  };
  results: Array<{
    model_type: string;
    model_name: string;
    metrics: ModelMetricsSaved;
    error: string | null;
  }>;
  saved_model: SavedModelMeta | null;
  created_at: string;
}

// ============================================================================
// API Keys
// ============================================================================
export type ApiKeyTier = 'free' | 'pro' | 'enterprise';

export interface ApiKeyRecord {
  key_id: string;
  name: string;
  prefix: string;
  tier: ApiKeyTier;
  owner: string;
  scopes: string[];
  created_at: string;
  updated_at: string;
  last_used_at: string | null;
  expires_at: string | null;
  revoked: boolean;
  request_count: number;
}

export interface ApiKeyListResponse {
  items: ApiKeyRecord[];
  total: number;
}

export interface ApiKeyCreateResponse {
  record: ApiKeyRecord;
  plain_key: string;
  prefix: string;
  warning: string;
}

export interface ApiKeyTierInfo {
  tier: ApiKeyTier;
  rate_limit_per_minute: number;
  description: string;
}
