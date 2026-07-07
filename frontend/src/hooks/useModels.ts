import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import type { TrainRequest } from '../types';

export const modelsQueryKey = ['models'] as const;
export const modelQueryKey = (id: string) => ['model', id] as const;

export function useSavedModels(params?: { model_type?: string; search?: string }) {
  return useQuery({
    queryKey: [...modelsQueryKey, params ?? {}],
    queryFn: async () => apiClient.listModels(params),
    staleTime: 30_000,
  });
}

export function useSavedModel(id: string | null | undefined) {
  return useQuery({
    queryKey: id ? modelQueryKey(id) : ['model', 'none'],
    queryFn: async () => {
      if (!id) return null;
      return apiClient.getModel(id);
    },
    enabled: !!id,
    staleTime: 30_000,
  });
}

export function useDeleteSavedModel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.deleteModel(id);
      return id;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: modelsQueryKey });
    },
  });
}

export function useUpdateSavedModel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      updates,
    }: {
      id: string;
      updates: { name?: string; notes?: string; tags?: string[] };
    }) => apiClient.updateModel(id, updates),
    onSuccess: (_data, vars) => {
      void qc.invalidateQueries({ queryKey: modelsQueryKey });
      void qc.invalidateQueries({ queryKey: modelQueryKey(vars.id) });
    },
  });
}

export function useUploadSavedModel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      file,
      meta,
    }: {
      file: File;
      meta?: { name?: string; notes?: string; tags?: string[] };
    }) => apiClient.uploadModel(file, meta),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: modelsQueryKey });
    },
  });
}

export function useTrainAndSave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (request: TrainRequest) => apiClient.trainAndSave(request),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: modelsQueryKey });
    },
  });
}

export function useForecastWithSavedModel() {
  return useMutation({
    mutationFn: async ({
      modelId,
      request,
    }: {
      modelId: string;
      request: { horizon: number; include_media_plan?: boolean; include_promotions?: boolean; include_holidays?: boolean; include_events?: boolean; include_weather?: boolean; include_competitor?: boolean; include_economic?: boolean };
    }) => apiClient.forecastWithSavedModel(modelId, request),
  });
}
