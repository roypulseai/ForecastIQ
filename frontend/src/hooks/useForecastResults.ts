import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import { forecastQueryKey } from './useForecast';

export function useForecastResult(id: string | null | undefined) {
  return useQuery({
    queryKey: id ? forecastQueryKey(id) : ['forecast', 'none'],
    queryFn: async () => {
      if (!id) return null;
      return apiClient.getForecast(id);
    },
    enabled: Boolean(id),
    staleTime: 60_000,
    refetchInterval: (query) => {
      const data = query.state.data as Record<string, unknown> | null | undefined;
      if (!data) return false;
      // When metrics_pending is true, poll every 2s until metrics are ready
      if (data.metrics_pending) return 2000;
      return false;
    },
  });
}
