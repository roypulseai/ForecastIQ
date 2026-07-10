import { useEffect, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  IconButton,
  LinearProgress,
  Stack,
  Typography,
} from '@mui/material';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import DownloadIcon from '@mui/icons-material/Download';
import InsightsIcon from '@mui/icons-material/Insights';
import StorageIcon from '@mui/icons-material/Storage';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import { PageContainer } from '../components/layout/PageContainer';
import { FileUploader } from '../components/upload/FileUploader';
import { DataPreview } from '../components/upload/DataPreview';
import { useDeleteFile, useFiles, useUploadFile } from '../hooks/useFiles';
import { useAnalyze } from '../hooks/useAnalysis';
import { useStore } from '../store/appStore';
import { getErrorMessage } from '../services/api';
import { FILE_TYPE_DESCRIPTIONS, FILE_TYPE_LABELS, FILE_TYPES, type FileType, type UploadedFile } from '../types';
import { downloadBlob } from '../utils/csv';
import { useState } from 'react';
import { formatDate, formatNumber } from '../utils/format';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { useToast } from '../components/common/ToastProvider';

export function DataUploadPage(): ReactNode {
  const navigate = useNavigate();
  const uploadedFiles = useStore((s) => s.uploadedFiles);
  const analysisData = useStore((s) => s.analysisData);
  const salesFileId = useStore((s) => s.salesFileId);
  const setAnalysisData = useStore((s) => s.setAnalysisData);
  const { showToast } = useToast();

  const filesQuery = useFiles();
  const uploadMut = useUploadFile();
  const deleteMut = useDeleteFile();
  const analyzeMut = useAnalyze();
  const [activeUpload, setActiveUpload] = useState<FileType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmDeleteFile, setConfirmDeleteFile] = useState<UploadedFile | null>(null);

  useEffect(() => {
    if (!filesQuery.data) return;
    if (filesQuery.data.length === 0 && analysisData) {
      setAnalysisData(null);
    }
  }, [filesQuery.data, analysisData, setAnalysisData]);

  const salesFile = uploadedFiles.find((f) => f.type === 'sales');
  const otherFiles = uploadedFiles.filter((f) => f.type !== 'sales');

  const handleFile = async (fileType: FileType, file: File) => {
    setError(null);
    setActiveUpload(fileType);
    try {
      const uploaded = await uploadMut.mutateAsync({ fileType, file });
      showToast(`${file.name} uploaded successfully`);
      if (fileType === 'sales' && !analysisData) {
        try {
          await analyzeMut.mutateAsync(uploaded.file_id);
        } catch (e) {
          console.warn('Auto-analyze failed:', e);
        }
      }
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setActiveUpload(null);
    }
  };

  const handleAnalyze = async (navigateToExplore = true) => {
    if (!salesFile) return;
    setError(null);
    try {
      await analyzeMut.mutateAsync(salesFile.file_id);
      if (navigateToExplore) navigate('/explore');
    } catch (e) {
      setError(getErrorMessage(e));
    }
  };

  const handleDelete = async (file: UploadedFile) => {
    setError(null);
    try {
      await deleteMut.mutateAsync(file.file_id);
      showToast(`${file.filename} deleted`, 'info');
    } catch (e) {
      setError(getErrorMessage(e));
    }
  };

  const handleTemplate = async (fileType: FileType) => {
    const mapping: Record<FileType, string> = {
      sales: '01_sales_template.csv',
      media_plan: '02_media_plan_template.csv',
      promotions: '03_promotions_template.csv',
      holidays: '04_holidays_template.csv',
      events: '05_events_template.csv',
      weather: '06_weather_template.csv',
      competitor: '07_competitor_template.csv',
      economic: '08_economic_template.csv',
    };
    const filename = mapping[fileType];
    const url = `/templates/${filename}`;
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`Template unavailable (${res.status})`);
      const text = await res.text();
      downloadBlob(text, filename, 'text/csv');
    } catch (e) {
      setError(getErrorMessage(e));
    }
  };

  return (
    <PageContainer
      title="Data upload"
      subtitle="Upload your primary business data (sales, orders, traffic, etc.) plus any supporting data sources (media plan, promotions, holidays, etc.)."
      actions={
        salesFile && (
          <Button
            variant="contained"
            startIcon={
              analyzeMut.isPending ? <CircularProgress size={16} color="inherit" /> : <InsightsIcon />
            }
            disabled={analyzeMut.isPending}
            onClick={() => handleAnalyze()}
          >
            {analyzeMut.isPending ? 'Analyzing…' : 'Analyze & explore'}
          </Button>
        )
      }
    >
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {filesQuery.isLoading && <LinearProgress sx={{ mb: 3 }} />}

      <Grid container spacing={3}>
        <Grid item xs={12} lg={4}>
          <Card sx={{ position: { lg: 'sticky' }, top: { lg: 80 } }}>
            <CardContent>
              <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 2 }}>
                <Box
                  sx={{
                    width: 40,
                    height: 40,
                    borderRadius: 1.5,
                    backgroundColor: 'primary.lighter',
                    color: 'primary.main',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <StorageIcon />
                </Box>
                <Box>
                  <Typography variant="h5">Business metrics</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Required — sales, orders, traffic, etc.
                  </Typography>
                </Box>
              </Stack>
              <FileUploader
                fileType="sales"
                label="Upload CSV"
                description={FILE_TYPE_DESCRIPTIONS.sales}
                isLoading={activeUpload === 'sales'}
                onFileSelected={(f) => handleFile('sales', f)}
              />
              {salesFile && (
                <Box sx={{ mt: 2 }}>
                  <Stack
                    direction="row"
                    spacing={1}
                    alignItems="center"
                    justifyContent="space-between"
                    sx={{ mb: 1.5 }}
                  >
                    <Typography variant="subtitle2">Current</Typography>
                    <Chip
                      label={`${formatNumber(salesFile.row_count)} rows`}
                      size="small"
                      color="success"
                    />
                  </Stack>
                  <Stack spacing={0.5}>
                    <Row label="Filename" value={salesFile.filename} />
                    <Row label="Columns" value={salesFile.columns.join(', ') || '—'} />
                    {salesFile.column_mapping && Object.keys(salesFile.column_mapping).length > 0 && (
                      <Row
                        label="Mapping"
                        value={Object.entries(salesFile.column_mapping)
                          .map(([k, v]) => `${k}←${v}`)
                          .join(', ')}
                      />
                    )}
                  </Stack>
                </Box>
              )}
              {analysisData && (
                <Box sx={{ mt: 2, p: 1.5, borderRadius: 1.5, backgroundColor: 'success.lighter' }}>
                  <Typography variant="caption" color="success.dark" sx={{ fontWeight: 600 }}>
                    ✓ Analysis complete
                  </Typography>
                  <Typography variant="body2" color="success.dark" sx={{ mt: 0.5 }}>
                    {formatNumber(analysisData.data_characteristics.length)} observations,{' '}
                    {analysisData.data_characteristics.trend} trend,{' '}
                    {analysisData.data_characteristics.seasonality} seasonality.
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} lg={8}>
          {salesFile && (
            <Box sx={{ mb: 3 }}>
              <DataPreview file={salesFile} onDelete={(id) => void handleDelete(uploadedFiles.find((f) => f.file_id === id) ?? { file_id: id, filename: '', type: '', size: 0, row_count: 0, columns: [] })} showDownloadTemplate onDownloadTemplate={() => handleTemplate('sales')} />
            </Box>
          )}

          <Typography variant="h4" sx={{ mb: 2 }}>
            Supporting data sources
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Optional files that enrich the forecast. Models can incorporate them as exogenous variables.
          </Typography>
          <Grid container spacing={2}>
            {FILE_TYPES.filter((t) => t !== 'sales').map((t) => (
              <Grid key={t} item xs={12} sm={6}>
                <Card sx={{ height: '100%' }}>
                  <CardContent>
                    <Stack
                      direction="row"
                      alignItems="center"
                      justifyContent="space-between"
                      sx={{ mb: 1.5 }}
                    >
                      <Typography variant="h5">{FILE_TYPE_LABELS[t]}</Typography>
                      <Button
                        size="small"
                        startIcon={<DownloadIcon />}
                        onClick={() => handleTemplate(t)}
                      >
                        Template
                      </Button>
                    </Stack>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      {FILE_TYPE_DESCRIPTIONS[t]}
                    </Typography>
                    <FileUploader
                      fileType={t}
                      label={`Upload ${FILE_TYPE_LABELS[t].toLowerCase()}`}
                      isLoading={activeUpload === t}
                      onFileSelected={(f) => handleFile(t, f)}
                    />
                    {otherFiles
                      .filter((f) => f.type === t)
                      .map((f) => (
                        <Box key={f.file_id} sx={{ mt: 1.5 }}>
                          <DataPreview
                            file={f}
                            onDelete={() => void handleDelete(f)}
                            showDownloadTemplate={false}
                          />
                        </Box>
                      ))}
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>

          {analysisData && salesFileId && (
            <Box sx={{ mt: 4 }}>
              <Divider sx={{ mb: 3 }} />
              <Stack
                direction={{ xs: 'column', sm: 'row' }}
                spacing={2}
                alignItems={{ xs: 'flex-start', sm: 'center' }}
                justifyContent="space-between"
              >
                <Box>
                  <Typography variant="h5">Ready to forecast?</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {formatNumber(analysisData.data_characteristics.length)} observations ·{' '}
                    {analysisData.data_characteristics.trend} trend ·{' '}
                    {analysisData.data_characteristics.seasonality} seasonality
                  </Typography>
                </Box>
                <Stack direction="row" spacing={1.5}>
                  <Button
                    variant="outlined"
                    startIcon={<RestartAltIcon />}
                    onClick={() => handleAnalyze(false)}
                    disabled={analyzeMut.isPending}
                  >
                    Re-analyze
                  </Button>
                  <Button variant="contained" onClick={() => navigate('/explore')}>
                    Explore data
                  </Button>
                  <Button variant="contained" color="secondary" onClick={() => navigate('/forecast')}>
                    Configure forecast
                  </Button>
                </Stack>
              </Stack>
            </Box>
          )}

          {uploadedFiles.length > 0 && (
            <Box sx={{ mt: 4 }}>
              <Typography variant="overline" color="text.secondary">
                All files
              </Typography>
              <Stack spacing={1.5} sx={{ mt: 1 }}>
                {uploadedFiles
                  .slice()
                  .sort((a, b) => (a.uploaded_at ?? '').localeCompare(b.uploaded_at ?? ''))
                  .reverse()
                  .map((f) => (
                    <Stack
                      key={f.file_id}
                      direction="row"
                      alignItems="center"
                      spacing={2}
                      sx={{
                        p: 1.5,
                        borderRadius: 1.5,
                        border: '1px solid',
                        borderColor: 'divider',
                      }}
                    >
                      <Box sx={{ flexGrow: 1 }}>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {f.filename}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {FILE_TYPE_LABELS[f.type as FileType] ?? f.type} ·{' '}
                          {formatNumber(f.row_count)} rows · uploaded{' '}
                          {f.uploaded_at ? formatDate(f.uploaded_at, true) : 'just now'}
                        </Typography>
                      </Box>
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => setConfirmDeleteFile(f)}
                        aria-label={`Delete ${f.filename}`}
                      >
                        <DeleteOutlineIcon fontSize="small" />
                      </IconButton>
                    </Stack>
                  ))}
              </Stack>
            </Box>
          )}
        </Grid>
      </Grid>

      <ConfirmDialog
        open={confirmDeleteFile != null}
        title="Delete file"
        message={`Delete "${confirmDeleteFile?.filename}"?`}
        onConfirm={() => {
          if (confirmDeleteFile) handleDelete(confirmDeleteFile);
          setConfirmDeleteFile(null);
        }}
        onCancel={() => setConfirmDeleteFile(null)}
      />
    </PageContainer>
  );
}

function Row({ label, value }: { label: string; value: string }): ReactNode {
  return (
    <Stack direction="row" spacing={1} alignItems="flex-start">
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ minWidth: 80, fontWeight: 600, pt: 0.25 }}
      >
        {label}
      </Typography>
      <Typography variant="body2" sx={{ wordBreak: 'break-word' }}>
        {value}
      </Typography>
    </Stack>
  );
}
