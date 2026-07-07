import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import { useStore } from '../store/appStore';
import type { ForecastRequest } from '../types';

export const forecastsQueryKey = ['forecasts'] as const;
export const forecastQueryKey = (id: string) => ['forecast', id] as const;
export const jobQueryKey = (jobId: string) => ['job', jobId] as const;

export function useCreateForecast() {
  const setCurrent = useStore((s) => s.setCurrentForecastId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (request: ForecastRequest) => {
      // Always use async mode for non-trivial requests so the UI doesn't
      // block on long-running forecasts. The backend will queue the job
      // and return a job_id immediately.
      const res = await apiClient.createForecast(request, true);
      // Detect sync vs async response
      if ('job_id' in res) {
        return { jobId: res.job_id } as const;
      }
      setCurrent(res.forecast_id);
      return { forecastId: res.forecast_id, response: res } as const;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: forecastsQueryKey });
    },
  });
}

/**
 * Poll a job's status. Stops when status is terminal (completed/failed).
 */
export function useJobStatus(jobId: string | null, enabled = true) {
  return useQuery({
    queryKey: jobId ? jobQueryKey(jobId) : ['job', 'none'],
    queryFn: async () => {
      if (!jobId) return null;
      return apiClient.getJobStatus(jobId);
    },
    enabled: enabled && !!jobId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 1000;
      if (data.status === 'completed' || data.status === 'failed') return false;
      return 1000;
    },
    staleTime: 0,
  });
}

export function useForecastList() {
  const setForecasts = useStore((s) => s.setForecasts);
  return useQuery({
    queryKey: forecastsQueryKey,
    queryFn: async () => {
      const res = await apiClient.listForecasts();
      setForecasts(res.items);
      return res;
    },
    staleTime: 30_000,
  });
}

export function useDeleteForecast() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.deleteForecast(id);
      return id;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: forecastsQueryKey });
    },
  });
}
