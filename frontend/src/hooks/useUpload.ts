import { useMutation } from '@tanstack/react-query';
import { apiClient } from '../services/api';

export function useUpload() {
  return useMutation({
    mutationFn: async ({ fileType, file }: { fileType: string; file: File }) => {
      return apiClient.uploadFile(fileType, file);
    },
  });
}
