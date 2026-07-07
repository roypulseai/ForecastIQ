import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import { useStore } from '../store/appStore';
import type { FileType, UploadedFile } from '../types';

export const filesQueryKey = ['files'] as const;
export const fileDataQueryKey = (fileId: string | null | undefined) =>
  ['fileData', fileId] as const;

export function useFiles() {
  const setFiles = useStore((s) => s.setUploadedFiles);
  return useQuery({
    queryKey: filesQueryKey,
    queryFn: async () => {
      const res = await apiClient.listFiles();
      setFiles(res.items);
      return res.items;
    },
    staleTime: 30_000,
  });
}

/**
 * Fetch the actual rows of a file. Defaults to 5000 rows (max). For
 * longer histories, pass `limit` and use `offset` for pagination.
 */
export function useFileData(fileId: string | null | undefined, limit = 5000) {
  return useQuery({
    queryKey: fileId ? fileDataQueryKey(fileId) : ['fileData', 'none'],
    queryFn: async () => {
      if (!fileId) return null;
      return apiClient.getFileData(fileId, limit);
    },
    enabled: !!fileId,
    staleTime: 30_000,
    retry: 2,
    retryDelay: 1000,
  });
}

export function useUploadFile() {
  const qc = useQueryClient();
  const addFile = useStore((s) => s.addUploadedFile);
  return useMutation({
    mutationFn: async ({ fileType, file }: { fileType: FileType; file: File }) => {
      const uploaded = await apiClient.uploadFile(fileType, file);
      addFile(uploaded);
      return uploaded as UploadedFile;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: filesQueryKey });
    },
  });
}

export function useDeleteFile() {
  const qc = useQueryClient();
  const remove = useStore((s) => s.removeUploadedFile);
  return useMutation({
    mutationFn: async (fileId: string) => {
      await apiClient.deleteFile(fileId);
      return fileId;
    },
    onSuccess: (fileId) => {
      remove(fileId);
      void qc.invalidateQueries({ queryKey: filesQueryKey });
    },
  });
}
