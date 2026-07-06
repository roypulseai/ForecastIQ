import { create } from 'zustand'

interface UploadedFile {
  file_id: string
  filename: string
  type: string
  size: number
  row_count: number
  columns: string[]
}

interface AnalysisData {
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
  hierarchy?: {
    has_hierarchy: boolean
    levels: string[]
    sku_count?: number
    product_count?: number
    category_count?: number
  }
}

interface ForecastListItem {
  forecast_id: string
  name: string
  created_at: string
  horizon: number
  models: string[]
}

interface AppState {
  uploadedFiles: UploadedFile[]
  salesFileId: string | null
  analysisData: AnalysisData | null
  currentForecast: string | null
  forecasts: ForecastListItem[]

  addUploadedFile: (file: UploadedFile) => void
  removeUploadedFile: (fileId: string) => void
  setSalesFileId: (fileId: string) => void
  setAnalysisData: (data: AnalysisData) => void
  setCurrentForecast: (forecastId: string) => void
  setForecasts: (forecasts: ForecastListItem[]) => void
}

export const useStore = create<AppState>((set) => ({
  uploadedFiles: [],
  salesFileId: null,
  analysisData: null,
  currentForecast: null,
  forecasts: [],

  addUploadedFile: (file) =>
    set((state) => ({
      uploadedFiles: [
        ...state.uploadedFiles.filter((f) => f.file_id !== file.file_id),
        file,
      ],
    })),

  removeUploadedFile: (fileId) =>
    set((state) => ({
      uploadedFiles: state.uploadedFiles.filter((f) => f.file_id !== fileId),
    })),

  setSalesFileId: (fileId) => set({ salesFileId: fileId }),

  setAnalysisData: (data) => set({ analysisData: data }),

  setCurrentForecast: (forecastId) => set({ currentForecast: forecastId }),

  setForecasts: (forecasts) => set({ forecasts }),
}))
