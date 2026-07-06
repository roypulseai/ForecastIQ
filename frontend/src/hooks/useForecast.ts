import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import { useStore } from '../store/appStore';
import type { ForecastRequest } from '../types';

export const forecastsQueryKey = ['forecasts'] as const;
export const forecastQueryKey = (id: string) => ['forecast', id] as const;

export function useCreateForecast() {
  const setCurrent = useStore((s) => s.setCurrentForecastId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (request: ForecastRequest) => {
      const res = await apiClient.createForecast(request);
      setCurrent(res.forecast_id);
      return res;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: forecastsQueryKey });
    },
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
