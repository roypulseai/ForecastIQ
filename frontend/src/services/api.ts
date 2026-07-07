import axios, { AxiosError, type AxiosResponse } from 'axios';
import type {
  AnalysisResponse,
  ApiKeyCreateResponse,
  ApiKeyListResponse,
  ApiKeyRecord,
  ApiKeyTier,
  ApiKeyTierInfo,
  FilesListResponse,
  ForecastDetail,
  ForecastListResponse,
  ForecastRequest,
  ForecastResponse,
  ForecastValue,
  HealthResponse,
  JobStatus,
  SavedModelMeta,
  SavedModelsListResponse,
  TrainRequest,
  TrainResult,
  UploadedFile,
} from '../types';

export const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 120000,
});

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail;
    const message = typeof detail === 'string' ? detail : error.message;
    console.error('[API]', error.config?.url, '->', error.response?.status, message);
    return Promise.reject(error);
  },
);

export const apiClient = {
  async uploadFile(fileType: string, file: File): Promise<UploadedFile> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await api.post<UploadedFile>(`/upload/${fileType}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  async listFiles(fileType?: string): Promise<FilesListResponse> {
    const res = await api.get<FilesListResponse>('/upload/files', {
      params: fileType ? { file_type: fileType } : undefined,
    });
    return res.data;
  },

  async deleteFile(fileId: string): Promise<void> {
    await api.delete(`/upload/files/${fileId}`);
  },

  async getFile(fileId: string): Promise<UploadedFile> {
    const res = await api.get<UploadedFile>(`/upload/files/${fileId}`);
    return res.data;
  },

  async getFileData(
    fileId: string,
    limit = 5000,
    offset = 0,
  ): Promise<{
    file_id: string;
    columns: string[];
    rows: Array<Record<string, unknown>>;
    total_rows: number;
    returned_rows: number;
    offset: number;
    limit: number;
  }> {
    const res = await api.get(`/upload/files/${fileId}/data`, {
      params: { limit, offset },
    });
    return res.data;
  },

  async analyze(fileId: string): Promise<AnalysisResponse> {
    const res = await api.post<AnalysisResponse>('/analyze', null, {
      params: { file_id: fileId },
    });
    return res.data;
  },

  async createForecast(request: ForecastRequest, asyncMode = true): Promise<ForecastResponse | { job_id: string; status: string; message: string }> {
    const res = await api.post<ForecastResponse | { job_id: string; status: string; message: string }>(
      '/forecast',
      request,
      { params: asyncMode ? { async: 'true' } : undefined },
    );
    return res.data;
  },

  async getJobStatus(jobId: string): Promise<JobStatus> {
    const res = await api.get<JobStatus>(`/forecast/jobs/${jobId}`);
    return res.data;
  },

  async getJobResult(jobId: string): Promise<{ job_id: string; status: string; result: ForecastDetail }> {
    const res = await api.get<{ job_id: string; status: string; result: ForecastDetail }>(
      `/forecast/jobs/${jobId}/result`,
    );
    return res.data;
  },

  async getForecast(id: string): Promise<ForecastDetail> {
    const res = await api.get<ForecastDetail>(`/forecast/${id}`);
    return res.data;
  },

  async listForecasts(): Promise<ForecastListResponse> {
    const res = await api.get<ForecastListResponse>('/forecasts');
    return res.data;
  },

  async deleteForecast(id: string): Promise<void> {
    await api.delete(`/forecast/${id}`);
  },

  async health(): Promise<HealthResponse> {
    const res = await api.get<HealthResponse>('/health');
    return res.data;
  },

  // ---- Saved model registry ----
  async listModels(params?: {
    model_type?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<SavedModelsListResponse> {
    const res = await api.get<SavedModelsListResponse>('/models', { params });
    return res.data;
  },

  async getModel(modelId: string): Promise<SavedModelMeta> {
    const res = await api.get<SavedModelMeta>(`/models/${modelId}`);
    return res.data;
  },

  async deleteModel(modelId: string): Promise<void> {
    await api.delete(`/models/${modelId}`);
  },

  async updateModel(
    modelId: string,
    updates: { name?: string; notes?: string; tags?: string[] },
  ): Promise<SavedModelMeta> {
    const res = await api.patch<SavedModelMeta>(`/models/${modelId}`, updates);
    return res.data;
  },

  async uploadModel(
    file: File,
    meta?: { name?: string; notes?: string; tags?: string[] },
  ): Promise<SavedModelMeta> {
    const formData = new FormData();
    formData.append('file', file);
    if (meta?.name) formData.append('name', meta.name);
    if (meta?.notes) formData.append('notes', meta.notes);
    if (meta?.tags) formData.append('tags', meta.tags.join(','));
    const res = await api.post<SavedModelMeta>('/models/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  async trainAndSave(request: TrainRequest): Promise<TrainResult> {
    const res = await api.post<TrainResult>('/models/train', request);
    return res.data;
  },

  async forecastWithSavedModel(
    modelId: string,
    request: { horizon: number; include_media_plan?: boolean; include_promotions?: boolean; include_holidays?: boolean; include_events?: boolean; include_weather?: boolean; include_competitor?: boolean; include_economic?: boolean },
  ): Promise<{
    model_id: string;
    model_name: string;
    model_meta: SavedModelMeta;
    forecast_values: ForecastValue[];
    baseline_values: ForecastValue[] | null;
    components: Record<string, unknown>;
    horizon: number;
  }> {
    const res = await api.post(`/models/${modelId}/forecast`, request);
    return res.data;
  },

  // ---- API Key management ----
  async listApiKeys(): Promise<ApiKeyListResponse> {
    const res = await api.get<ApiKeyListResponse>('/api-keys');
    return res.data;
  },

  async createApiKey(params: {
    name: string;
    tier?: ApiKeyTier;
    scopes?: string[];
    expires_at?: string;
  }): Promise<ApiKeyCreateResponse> {
    const res = await api.post<ApiKeyCreateResponse>('/api-keys', params);
    return res.data;
  },

  async updateApiKey(
    keyId: string,
    updates: { name?: string; tier?: ApiKeyTier; scopes?: string[]; expires_at?: string },
  ): Promise<ApiKeyRecord> {
    const res = await api.patch<ApiKeyRecord>(`/api-keys/${keyId}`, updates);
    return res.data;
  },

  async revokeApiKey(keyId: string): Promise<void> {
    await api.delete(`/api-keys/${keyId}`);
  },

  async listApiKeyTiers(): Promise<{ tiers: ApiKeyTierInfo[] }> {
    const res = await api.get<{ tiers: ApiKeyTierInfo[] }>('/api-keys/tiers');
    return res.data;
  },
};

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === 'string') return detail;
    if (detail && typeof detail === 'object') {
      const obj = detail as { message?: string; error?: string };
      if (obj.message) return obj.message;
      if (obj.error) return obj.error;
    }
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return 'An unexpected error occurred';
}
