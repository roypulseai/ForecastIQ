import axios from 'axios'

const API_BASE = '/api/v1'

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface UploadResponse {
  file_id: string
  filename: string
  type: string
  size: number
  row_count: number
  columns: string[]
}

export interface AnalysisResponse {
  validation: {
    valid: boolean
    errors: string[]
    date_column: string
    value_column: string
    row_count: number
  }
  analysis: {
    data_characteristics: {
      length: number
      mean: number
      std: number
      cv: number
      trend: string
      seasonality: string
      stationarity: boolean
      outliers_pct: number
      missing_pct: number
    }
    model_recommendations: Array<{
      model: string
      score: number
      reason: string
    }>
  }
}

export interface ModelParameters {
  arima?: { p: number; d: number; q: number }
  sarimax?: { p: number; d: number; q: number; seasonal_p: number; seasonal_d: number; seasonal_q: number; seasonal_period: number }
  prophet?: { 
    seasonality_mode: string
    yearly_seasonality: boolean
    weekly_seasonality: boolean
    daily_seasonality: boolean
    changepoint_prior_scale: number
    seasonality_prior_scale: number
    holidays_prior_scale: number
  }
  lightgbm?: { n_estimators: number; learning_rate: number; max_depth: number; num_leaves: number; min_child_samples: number }
  xgboost?: { n_estimators: number; learning_rate: number; max_depth: number; min_child_weight: number; subsample: number; colsample_bytree: number }
  wma?: { window: number }
  ets?: { trend: string; seasonal: string; seasonal_periods: number }
  theta?: { period: number; deseasonalize: boolean }
  stl?: { period: number; robust: boolean }
}

export interface ForecastRequest {
  name: string
  target_column: string
  date_column: string
  frequency: 'D' | 'W' | 'M'
  horizon: number
  models: string[]
  parameters?: ModelParameters
  ensemble_models?: string[]
  ensemble_weights?: number[]
  include_media_plan: boolean
  include_promotions: boolean
  include_holidays: boolean
  include_events: boolean
  include_weather?: boolean
  include_competitor?: boolean
  include_economic?: boolean
  country?: string
  aggregation?: AggregationConfig
}

export interface AggregationConfig {
  time_rollup: string
  product_level: string
  region_level: string
  agg_function: string
}

export interface ForecastResponse {
  id: string
  status: string
  message: string
  best_model?: string
  model_rankings?: Array<{ model: string; mae: number; rmse: number }>
}

export interface ForecastValue {
  date: string
  forecast: number
  lower_ci: number
  upper_ci: number
  baseline?: number
  uplift?: number
}

export interface ModelResult {
  model_name: string
  forecast_values: ForecastValue[]
  baseline_values?: ForecastValue[]
  metrics: { mae: number; rmse: number; mape: number }
  feature_importance?: Record<string, number>
  components?: Record<string, any>
}

export interface ForecastResult {
  forecast_id: string
  name: string
  created_at: string
  request: ForecastRequest
  results: Record<string, ModelResult>
  ensemble?: {
    models_used: string[]
    weights: number[]
    forecast_values: ForecastValue[]
    baseline_values?: ForecastValue[]
    individual_results: ModelResult[]
  }
  external_factor_analysis?: {
    media_plan_impact?: Record<string, any>
    promotion_impact?: Record<string, any>
    holiday_impact?: Record<string, any>
    weather_impact?: Record<string, any>
    price_elasticity?: number
  }
}

export interface ForecastListItem {
  forecast_id: string
  name: string
  created_at: string
  horizon: number
  models: string[]
}

export const forecastApi = {
  uploadFile: async (fileType: string, file: File): Promise<UploadResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post(`/forecast/upload/${fileType}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  analyzeData: async (fileId: string): Promise<AnalysisResponse> => {
    const response = await api.post('/forecast/analyze', null, { params: { file_id: fileId } })
    return response.data
  },

  createForecast: async (request: ForecastRequest): Promise<ForecastResponse> => {
    const response = await api.post('/forecast/forecast', request)
    return response.data
  },

  getForecast: async (forecastId: string): Promise<ForecastResult> => {
    const response = await api.get(`/forecast/forecast/${forecastId}`)
    return response.data
  },

  listForecasts: async (): Promise<ForecastListItem[]> => {
    const response = await api.get('/forecast/forecasts')
    return response.data
  },

  deleteFile: async (fileId: string): Promise<void> => {
    await api.delete(`/forecast/file/${fileId}`)
  },
}
