import { useMutation } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import { useStore } from '../store/appStore';

export function useAnalyze() {
  const setAnalysis = useStore((s) => s.setAnalysisData);
  return useMutation({
    mutationFn: async (fileId: string) => {
      const data = await apiClient.analyze(fileId);
      setAnalysis(data, fileId);
      return data;
    },
  });
}
