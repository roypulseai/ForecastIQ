import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import type { ApiKeyTier } from '../types';

export const apiKeysQueryKey = ['api-keys'] as const;
export const apiKeyTiersQueryKey = ['api-key-tiers'] as const;

export function useListApiKeys() {
  return useQuery({
    queryKey: apiKeysQueryKey,
    queryFn: async () => apiClient.listApiKeys(),
    staleTime: 30_000,
  });
}

export function useListApiKeyTiers() {
  return useQuery({
    queryKey: apiKeyTiersQueryKey,
    queryFn: async () => apiClient.listApiKeyTiers(),
    staleTime: 5 * 60_000,
  });
}

export function useCreateApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (params: { name: string; tier?: ApiKeyTier; scopes?: string[]; expires_at?: string }) =>
      apiClient.createApiKey(params),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: apiKeysQueryKey });
    },
  });
}

export function useUpdateApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      updates,
    }: {
      id: string;
      updates: { name?: string; tier?: ApiKeyTier; scopes?: string[]; expires_at?: string };
    }) => apiClient.updateApiKey(id, updates),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: apiKeysQueryKey });
    },
  });
}

export function useDeleteApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.revokeApiKey(id);
      return id;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: apiKeysQueryKey });
    },
  });
}
