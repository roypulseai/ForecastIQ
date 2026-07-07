import axios, { AxiosError, type AxiosResponse } from 'axios';
import type {
  AnalysisResponse,
  FilesListResponse,
  ForecastDetail,
  ForecastListResponse,
  ForecastRequest,
  ForecastResponse,
  HealthResponse,
  JobStatus,
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
