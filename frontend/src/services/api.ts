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

export interface ForecastRequest {
  name: string
  target_column: string
  date_column: string
  frequency: 'D' | 'W' | 'M'
  horizon: number
  models: string[]
  ensemble_models?: string[]
  ensemble_weights?: number[]
  include_media_plan: boolean
  include_promotions: boolean
  include_holidays: boolean
  include_events: boolean
  seasonality_mode: 'additive' | 'multiplicative'
  country?: string
}

export interface ForecastResponse {
  id: string
  status: string
  message: string
  best_model?: string
  model_rankings?: Array<{ model: string; mae: number; rmse: number }>
}

export interface ForecastResult {
  forecast_id: string
  name: string
  created_at: string
  request: ForecastRequest
  results: Record<string, {
    model_name: string
    metrics: { mae: number; rmse: number; mape: number }
    forecast_values: Array<{ date: string; forecast: number; lower_ci: number; upper_ci: number }>
  }>
  ensemble?: {
    models_used: string[]
    weights: number[]
    forecast_values: Array<{ date: string; forecast: number; lower_ci: number; upper_ci: number }>
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
