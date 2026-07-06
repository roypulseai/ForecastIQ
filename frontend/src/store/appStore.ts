import { create } from 'zustand';
import type { AnalysisResponse, ForecastListItem, UploadedFile } from '../types';

interface AppState {
  uploadedFiles: UploadedFile[];
  salesFileId: string | null;
  analysisData: AnalysisResponse | null;
  analysisFileId: string | null;
  currentForecastId: string | null;
  forecasts: ForecastListItem[];

  setUploadedFiles: (files: UploadedFile[]) => void;
  addUploadedFile: (file: UploadedFile) => void;
  removeUploadedFile: (fileId: string) => void;
  setSalesFileId: (fileId: string | null) => void;
  setAnalysisData: (data: AnalysisResponse | null, fileId?: string | null) => void;
  setCurrentForecastId: (forecastId: string | null) => void;
  setForecasts: (forecasts: ForecastListItem[]) => void;
  reset: () => void;
}

export const useStore = create<AppState>((set) => ({
  uploadedFiles: [],
  salesFileId: null,
  analysisData: null,
  analysisFileId: null,
  currentForecastId: null,
  forecasts: [],

  setUploadedFiles: (files) => set({ uploadedFiles: files }),

  addUploadedFile: (file) =>
    set((state) => ({
      uploadedFiles: [
        ...state.uploadedFiles.filter((f) => f.file_id !== file.file_id),
        file,
      ],
      salesFileId:
        state.salesFileId === file.file_id || file.type !== 'sales'
          ? state.salesFileId
          : file.file_id,
    })),

  removeUploadedFile: (fileId) =>
    set((state) => ({
      uploadedFiles: state.uploadedFiles.filter((f) => f.file_id !== fileId),
      salesFileId: state.salesFileId === fileId ? null : state.salesFileId,
      analysisData: state.analysisFileId === fileId ? null : state.analysisData,
      analysisFileId: state.analysisFileId === fileId ? null : state.analysisFileId,
    })),

  setSalesFileId: (fileId) => set({ salesFileId: fileId }),

  setAnalysisData: (data, fileId) =>
    set({
      analysisData: data,
      analysisFileId: fileId === undefined ? null : fileId,
    }),

  setCurrentForecastId: (forecastId) => set({ currentForecastId: forecastId }),

  setForecasts: (forecasts) => set({ forecasts }),

  reset: () =>
    set({
      uploadedFiles: [],
      salesFileId: null,
      analysisData: null,
      analysisFileId: null,
      currentForecastId: null,
      forecasts: [],
    }),
}));
