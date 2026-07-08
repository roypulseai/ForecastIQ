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
  sales: 'Business Metrics',
  media_plan: 'Media Plan',
  promotions: 'Promotions',
  holidays: 'Holidays',
  events: 'Events',
  weather: 'Weather',
  competitor: 'Competitor',
  economic: 'Economic',
};

export const FILE_TYPE_DESCRIPTIONS: Record<FileType, string> = {
  sales: 'Primary time-series data (sales, orders, traffic, revenue — any business metric with date and value columns)',
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
  column_types: Record<string, string>;
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
  pdq_recommendation?: PDQRecommendation | null;
  insights?: Insight[];
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

export type BusinessType =
  | 'retail' | 'ecommerce' | 'saas' | 'manufacturing' | 'supply_chain'
  | 'finance' | 'healthcare' | 'energy' | 'hospitality' | 'media' | 'other';

export type BusinessStage =
  | 'hyper_growth' | 'growth' | 'mature' | 'declining' | 'seasonal' | 'volatile';

export const BUSINESS_TYPE_LABELS: Record<string, string> = {
  retail: 'Retail',
  ecommerce: 'E-commerce',
  saas: 'SaaS / Subscription',
  manufacturing: 'Manufacturing',
  supply_chain: 'Supply Chain',
  finance: 'Finance',
  healthcare: 'Healthcare',
  energy: 'Energy',
  hospitality: 'Hospitality',
  media: 'Media / Advertising',
  other: 'Other',
};

export const BUSINESS_STAGE_LABELS: Record<string, string> = {
  hyper_growth: 'Hyper-growth (50%+ YoY)',
  growth: 'Growth (10-50% YoY)',
  mature: 'Mature / Stable',
  declining: 'Declining',
  seasonal: 'Highly seasonal',
  volatile: 'Volatile / Unpredictable',
};

export interface Insight {
  type: 'info' | 'warning' | 'success';
  text: string;
}

export interface OrderRecommendation {
  p: number;
  d: number;
  q: number;
}

export interface SeasonalOrderRecommendation {
  p: number;
  d: number;
  q: number;
  s: number;
}

export interface PDQRecommendation {
  order: OrderRecommendation;
  seasonal_order?: SeasonalOrderRecommendation | null;
  reason: string;
}

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

export interface CountryOption {
  code: string;
  name: string;
  flag?: string;
}

export const COMMON_COUNTRIES: CountryOption[] = [
  { code: 'US', name: 'United States', flag: '\u{1F1FA}\u{1F1F8}' },
  { code: 'GB', name: 'United Kingdom', flag: '\u{1F1EC}\u{1F1E7}' },
  { code: 'IN', name: 'India', flag: '\u{1F1EE}\u{1F1F3}' },
  { code: 'CA', name: 'Canada', flag: '\u{1F1E8}\u{1F1E6}' },
  { code: 'AU', name: 'Australia', flag: '\u{1F1E6}\u{1F1FA}' },
  { code: 'DE', name: 'Germany', flag: '\u{1F1E9}\u{1F1EA}' },
  { code: 'FR', name: 'France', flag: '\u{1F1EB}\u{1F1F7}' },
  { code: 'IT', name: 'Italy', flag: '\u{1F1EE}\u{1F1F9}' },
  { code: 'ES', name: 'Spain', flag: '\u{1F1EA}\u{1F1F8}' },
  { code: 'BR', name: 'Brazil', flag: '\u{1F1E7}\u{1F1F7}' },
  { code: 'MX', name: 'Mexico', flag: '\u{1F1F2}\u{1F1FD}' },
  { code: 'JP', name: 'Japan', flag: '\u{1F1EF}\u{1F1F5}' },
  { code: 'CN', name: 'China', flag: '\u{1F1E8}\u{1F1F3}' },
  { code: 'KR', name: 'South Korea', flag: '\u{1F1F0}\u{1F1F7}' },
  { code: 'RU', name: 'Russia', flag: '\u{1F1F7}\u{1F1FA}' },
  { code: 'ZA', name: 'South Africa', flag: '\u{1F1FF}\u{1F1E6}' },
  { code: 'AE', name: 'UAE', flag: '\u{1F1E6}\u{1F1EA}' },
  { code: 'SG', name: 'Singapore', flag: '\u{1F1F8}\u{1F1EC}' },
  { code: 'MY', name: 'Malaysia', flag: '\u{1F1F2}\u{1F1FE}' },
  { code: 'ID', name: 'Indonesia', flag: '\u{1F1EE}\u{1F1E9}' },
  { code: 'PH', name: 'Philippines', flag: '\u{1F1F5}\u{1F1ED}' },
  { code: 'TH', name: 'Thailand', flag: '\u{1F1F9}\u{1F1ED}' },
  { code: 'VN', name: 'Vietnam', flag: '\u{1F1FB}\u{1F1F3}' },
  { code: 'NL', name: 'Netherlands', flag: '\u{1F1F3}\u{1F1F1}' },
  { code: 'SE', name: 'Sweden', flag: '\u{1F1F8}\u{1F1EA}' },
  { code: 'NO', name: 'Norway', flag: '\u{1F1F3}\u{1F1F4}' },
  { code: 'DK', name: 'Denmark', flag: '\u{1F1E9}\u{1F1F0}' },
  { code: 'FI', name: 'Finland', flag: '\u{1F1EB}\u{1F1EE}' },
  { code: 'CH', name: 'Switzerland', flag: '\u{1F1E8}\u{1F1ED}' },
  { code: 'BE', name: 'Belgium', flag: '\u{1F1E7}\u{1F1EA}' },
  { code: 'AT', name: 'Austria', flag: '\u{1F1E6}\u{1F1F9}' },
  { code: 'PT', name: 'Portugal', flag: '\u{1F1F5}\u{1F1F9}' },
  { code: 'PL', name: 'Poland', flag: '\u{1F1F5}\u{1F1F1}' },
  { code: 'TR', name: 'Turkey', flag: '\u{1F1F9}\u{1F1F7}' },
  { code: 'SA', name: 'Saudi Arabia', flag: '\u{1F1F8}\u{1F1E6}' },
  { code: 'AR', name: 'Argentina', flag: '\u{1F1E6}\u{1F1F7}' },
  { code: 'CL', name: 'Chile', flag: '\u{1F1E8}\u{1F1F1}' },
  { code: 'CO', name: 'Colombia', flag: '\u{1F1E8}\u{1F1F4}' },
  { code: 'PE', name: 'Peru', flag: '\u{1F1F5}\u{1F1EA}' },
  { code: 'EG', name: 'Egypt', flag: '\u{1F1EA}\u{1F1EC}' },
  { code: 'NG', name: 'Nigeria', flag: '\u{1F1F3}\u{1F1EC}' },
  { code: 'KE', name: 'Kenya', flag: '\u{1F1F0}\u{1F1EA}' },
  { code: 'NZ', name: 'New Zealand', flag: '\u{1F1F3}\u{1F1FF}' },
  { code: 'HK', name: 'Hong Kong', flag: '\u{1F1ED}\u{1F1F0}' },
  { code: 'TW', name: 'Taiwan', flag: '\u{1F1F9}\u{1F1FC}' },
  { code: 'IL', name: 'Israel', flag: '\u{1F1EE}\u{1F1F1}' },
];

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
  // Auto-detect regional events using holidays library + moveable feast algorithms
  auto_detect_events: boolean;
  // ISO country code for auto-detect (e.g. "IN", "US", "GB", "CN")
  auto_event_country?: string | null;
  // Optional region values within the country to focus on
  auto_event_regions?: string[];
  aggregation?: AggregationConfig;
  country?: string;
  notes?: string;
  // Business context — influences model selection and default parameters
  business_type?: BusinessType | null;
  business_stage?: BusinessStage | null;
  // Train/test split for proper evaluation (0..1). Default 1.0 = no split.
  // When < 1.0, the last (1-ratio) rows are held out and the test metrics
  // are computed before forecasting the next horizon.
  train_test_split?: number;
  // How many of the last actuals to overlay with the forecast (backtesting).
  // E.g. 30 means the chart shows the last 30 days of actuals alongside the
  // forecast so you can visually compare. 0 = no overlap.
  backtest_overlap?: number;
  // Hyperparameter tuning via randomized search with time-series CV.
  tune_hyperparameters?: boolean;
  // Optional categorical column(s) for hierarchical forecasting.
  category_column?: string;
  category_columns?: string[];
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
  category?: string;
  // Extra fields from multi-category forecasting (e.g. store, sku)
  [key: string]: string | number | null | undefined;
}

export interface ModelRanking {
  model: string;
  name?: string | null;
  mae?: number | null;
  rmse?: number | null;
  mape?: number | null;
  r2?: number | null;
  score?: number | null;
  forecast_accuracy?: number | null;
  accuracy_grade?: string | null;
  backtest_forecast_accuracy?: number | null;
  backtest_accuracy_grade?: string | null;
  backtest_mae?: number | null;
  backtest_mape?: number | null;
  cv_forecast_accuracy?: number | null;
  cv_accuracy_grade?: string | null;
  cv_mae?: number | null;
  cv_mape?: number | null;
}

export interface ModelResult {
  model_name: string;
  metrics: Record<string, number>;
  forecast_values: ForecastValue[];
  baseline_values?: ForecastValue[] | null;
  backtest_forecast_values?: ForecastValue[] | null;
  backtest_metrics?: Record<string, number>;
  feature_importance?: Record<string, number> | null;
  components?: Record<string, unknown> | null;
  error?: string | null;
  accuracy_grade?: string | null;
  test_accuracy_grade?: string | null;
}

export interface EnsembleResult {
  models_used: string[];
  weights: number[];
  forecast_values: ForecastValue[];
  baseline_values?: ForecastValue[] | null;
  backtest_forecast_values?: ForecastValue[] | null;
  backtest_metrics?: Record<string, number>;
  metrics?: Record<string, number>;
  individual_results: ModelResult[];
}

export interface LagAnalysisResult {
  lag: number;
  correlation?: number | null;
  strength: string;
  message: string;
}

export interface ExternalFactorAnalysis {
  media_plan_impact?: Record<string, unknown> | null;
  promotion_impact?: Record<string, unknown> | null;
  holiday_impact?: Record<string, unknown> | null;
  event_impact?: Record<string, unknown> | null;
  weather_impact?: Record<string, unknown> | null;
  price_elasticity?: number | null;
  lag_analysis?: Record<string, LagAnalysisResult>;
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
  test_metrics?: Record<string, { mae: number | null; rmse: number | null; mape: number | null; test_rows?: number }>;
  saved_model?: SavedModelMeta | null;
  downsample_info?: DownsampleInfo | null;
  best_model?: string | null;
  model_rankings?: ModelRanking[];
  tuning_results?: Record<string, {
    best_params: Record<string, unknown>;
    cv_scores: { mae: number; rmse: number; mape: number };
    tuned: boolean;
  }>;
  category_column?: string | null;
  category_columns?: string[] | null;
  category_values?: string[];
  category_forecasts?: Record<string, {
    results: Record<string, ModelResult>;
    summary?: ForecastSummary | null;
  }>;
  category_column_values?: Record<string, Record<string, string>>;
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
