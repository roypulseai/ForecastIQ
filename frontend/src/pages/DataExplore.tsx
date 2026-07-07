import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  MenuItem,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import InsightsIcon from '@mui/icons-material/Insights';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import TimelineIcon from '@mui/icons-material/Timeline';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { PageContainer } from '../components/layout/PageContainer';
import { DataSummary } from '../components/explore/DataSummary';
import { TimeSeriesChart } from '../components/explore/TimeSeriesChart';
import { DistributionChart } from '../components/explore/DistributionChart';
import { DecompositionChart } from '../components/explore/DecompositionChart';
import { useStore } from '../store/appStore';
import { useAnalyze } from '../hooks/useAnalysis';
import { useFileData, useFiles } from '../hooks/useFiles';
import { getErrorMessage } from '../services/api';
import { formatNumber } from '../utils/format';
import { MODEL_DESCRIPTIONS, MODEL_LABELS } from '../types';

const PRESETS = [
  { value: 7, label: '7 days (weekly)' },
  { value: 14, label: '14 days' },
  { value: 30, label: '30 days (monthly)' },
  { value: 90, label: '90 days (quarterly)' },
  { value: 365, label: '365 days (yearly)' },
];

export function DataExplorePage(): ReactNode {
  const navigate = useNavigate();
  const analysisData = useStore((s) => s.analysisData);
  const analysisFileId = useStore((s) => s.analysisFileId);
  const uploadedFiles = useStore((s) => s.uploadedFiles);
  const setAnalysisData = useStore((s) => s.setAnalysisData);
  const filesQuery = useFiles();
  const analyzeMut = useAnalyze();
  const [error, setError] = useState<string | null>(null);
  const [decompPeriod, setDecompPeriod] = useState<number>(7);
  const [bins, setBins] = useState<number>(25);

  const salesFile = useMemo(
    () => uploadedFiles.find((f) => f.type === 'sales') ?? null,
    [uploadedFiles],
  );
  const fileIdToUse = salesFile?.file_id;
  const fileDataQuery = useFileData(fileIdToUse);

  // If we have a file but no analysis, kick one off automatically.
  useEffect(() => {
    if (fileIdToUse && !analysisData && !analyzeMut.isPending) {
      analyzeMut.mutate(fileIdToUse, {
        onError: (e) => setError(getErrorMessage(e)),
      });
    }
    // If the file changed (new upload) and the cached analysis is for a
    // different file, clear it so we re-analyze.
    if (fileIdToUse && analysisFileId && analysisFileId !== fileIdToUse) {
      setAnalysisData(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fileIdToUse, analysisData]);

  // Build real series from the file rows
  const { dates, values, errorMsg } = useMemo(() => {
    if (!analysisData) {
      return { dates: [] as string[], values: [] as number[], errorMsg: null as string | null };
    }
    if (!fileDataQuery.data) {
      return { dates: [] as string[], values: [] as number[], errorMsg: fileDataQuery.error ? getErrorMessage(fileDataQuery.error) : null };
    }
    const dc = analysisData.validation.date_column || 'date';
    const vc = analysisData.validation.value_column || 'value';
    const rows = fileDataQuery.data.rows;
    if (!rows || rows.length === 0) {
      return { dates: [] as string[], values: [] as number[], errorMsg: `No rows returned for file` };
    }
    const ds: string[] = [];
    const vs: number[] = [];
    for (const r of rows) {
      const rawDate = r[dc];
      const rawVal = r[vc];
      if (rawDate == null || rawVal == null) continue;
      const d = String(rawDate).slice(0, 10);
      const v = Number(rawVal);
      if (!Number.isFinite(v)) continue;
      ds.push(d);
      vs.push(v);
    }
    // Sort by date
    const pairs = ds.map((d, i) => [d, vs[i]] as const).sort((a, b) => (a[0] < b[0] ? -1 : 1));
    return {
      dates: pairs.map((p) => p[0]),
      values: pairs.map((p) => p[1]),
      errorMsg: null,
    };
  }, [analysisData, fileDataQuery.data, fileDataQuery.error]);

  const handleAnalyze = async () => {
    if (!fileIdToUse) return;
    setError(null);
    try {
      await analyzeMut.mutateAsync(fileIdToUse);
    } catch (e) {
      setError(getErrorMessage(e));
    }
  };

  if (filesQuery.isLoading || (fileIdToUse && (fileDataQuery.isLoading || fileDataQuery.isFetching))) {
    return (
      <PageContainer title="Explore data">
        <Stack alignItems="center" sx={{ py: 8 }}>
          <CircularProgress />
          <Typography sx={{ mt: 2 }}>Loading data…</Typography>
        </Stack>
      </PageContainer>
    );
  }

  if (!salesFile) {
    return (
      <PageContainer title="Explore data">
        <Card sx={{ p: 4, textAlign: 'center' }}>
          <InsightsIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
          <Typography variant="h5" gutterBottom>
            No sales data uploaded yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Upload a sales CSV to unlock interactive exploration.
          </Typography>
          <Button variant="contained" onClick={() => navigate('/upload')}>
            Go to upload
          </Button>
        </Card>
      </PageContainer>
    );
  }

  // While auto-analyze is running, show progress
  if (!analysisData) {
    return (
      <PageContainer title="Explore data">
        <Card sx={{ p: 4, textAlign: 'center' }}>
          <ShowChartIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
          <Typography variant="h5" gutterBottom>
            {analyzeMut.isPending ? 'Analyzing your data…' : 'Analysis required'}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            {analyzeMut.isPending
              ? 'Computing characteristics and model recommendations.'
              : 'Run an analysis on your sales file to view interactive charts.'}
          </Typography>
          {analyzeMut.isPending && <CircularProgress />}
          {!analyzeMut.isPending && (
            <Button
              variant="contained"
              onClick={handleAnalyze}
              disabled={analyzeMut.isPending}
            >
              Analyze now
            </Button>
          )}
          {error && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {error}
            </Alert>
          )}
        </Card>
      </PageContainer>
    );
  }

  const data = analysisData;
  const totalRowsLoaded = dates.length;
  const totalRowsAvailable = fileDataQuery.data?.total_rows ?? data.validation.row_count;

  const dateRange: [string, string] | null =
    data.data_characteristics.min_date && data.data_characteristics.max_date
      ? [data.data_characteristics.min_date, data.data_characteristics.max_date]
      : null;

  return (
    <PageContainer
      title="Explore data"
      subtitle="Interactive diagnostics for your sales history."
      actions={
        <Stack direction="row" spacing={1.5}>
          <Button
            variant="outlined"
            onClick={handleAnalyze}
            disabled={analyzeMut.isPending}
            startIcon={
              analyzeMut.isPending ? <CircularProgress size={16} color="inherit" /> : <InsightsIcon />
            }
          >
            {analyzeMut.isPending ? 'Analyzing…' : 'Re-analyze'}
          </Button>
          <Button variant="contained" onClick={() => navigate('/forecast')}>
            Configure forecast
          </Button>
        </Stack>
      }
    >
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {errorMsg && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          {errorMsg}
        </Alert>
      )}

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={7}>
              <Stack direction="row" spacing={1.5} alignItems="center">
                <Box
                  sx={{
                    width: 44,
                    height: 44,
                    borderRadius: 1.5,
                    backgroundColor: 'primary.lighter',
                    color: 'primary.main',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <InsightsIcon />
                </Box>
                <Box>
                  <Typography variant="h5">{salesFile.filename}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {data.validation.date_column} / {data.validation.value_column} ·{' '}
                    {formatNumber(totalRowsLoaded)} of {formatNumber(totalRowsAvailable)} observations loaded
                  </Typography>
                </Box>
              </Stack>
            </Grid>
            <Grid item xs={12} md={5}>
              <Stack direction="row" spacing={1.5} justifyContent={{ xs: 'flex-start', md: 'flex-end' }} flexWrap="wrap">
                <Chip
                  label={data.validation.valid ? 'Valid' : 'Has warnings'}
                  color={data.validation.valid ? 'success' : 'warning'}
                  size="small"
                />
                {data.validation.warnings.slice(0, 2).map((w, i) => (
                  <Chip key={i} label={w} size="small" variant="outlined" color="warning" />
                ))}
              </Stack>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Box sx={{ mb: 3 }}>
        <DataSummary
          characteristics={data.data_characteristics}
          dateRange={dateRange}
          dateColumn={data.validation.date_column}
          valueColumn={data.validation.value_column}
          totalRows={totalRowsLoaded}
        />
      </Box>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} lg={8}>
          <TimeSeriesChart
            data={values.map((v, i) => ({ date: dates[i] ?? '', value: v }))}
            title="Sales over time"
          />
        </Grid>
        <Grid item xs={12} lg={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
                <Typography variant="h5">Value distribution</Typography>
                <TextField
                  size="small"
                  select
                  label="Bins"
                  value={bins}
                  onChange={(e) => setBins(Number(e.target.value))}
                  sx={{ width: 110 }}
                >
                  {[10, 15, 20, 25, 30, 50].map((n) => (
                    <MenuItem key={n} value={n}>
                      {n}
                    </MenuItem>
                  ))}
                </TextField>
              </Stack>
              <DistributionChart values={values} bins={bins} title="" height={300} />
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={2}
            alignItems={{ xs: 'flex-start', sm: 'center' }}
            justifyContent="space-between"
            sx={{ mb: 1 }}
          >
            <Stack direction="row" spacing={1.5} alignItems="center">
              <TimelineIcon color="action" />
              <Typography variant="h5">Decomposition</Typography>
            </Stack>
            <TextField
              size="small"
              select
              label="Period"
              value={decompPeriod}
              onChange={(e) => setDecompPeriod(Number(e.target.value))}
              sx={{ width: 200 }}
            >
              {PRESETS.map((p) => (
                <MenuItem key={p.value} value={p.value}>
                  {p.label}
                </MenuItem>
              ))}
            </TextField>
          </Stack>
          <DecompositionChart
            dates={dates}
            values={values}
            period={decompPeriod}
            title="Trend / Seasonality / Residual"
          />
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
            <Typography variant="h5">Recommended models</Typography>
            <Tooltip title="These recommendations are derived from the detected data characteristics: trend, seasonality, stationarity, and coefficient of variation.">
              <InfoOutlinedIcon sx={{ fontSize: 18, color: 'text.secondary' }} />
            </Tooltip>
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Based on {formatNumber(data.data_characteristics.length)} observations ·{' '}
            trend: <b>{data.data_characteristics.trend}</b> ·{' '}
            seasonality: <b>{data.data_characteristics.seasonality}</b> ·{' '}
            CV: <b>{data.data_characteristics.cv.toFixed(2)}</b>
          </Typography>
          <Grid container spacing={2}>
            {data.model_recommendations.map((r) => (
              <Grid key={r.model} item xs={12} sm={6} md={4}>
                <Box
                  sx={{
                    p: 2,
                    borderRadius: 1.5,
                    border: '1px solid',
                    borderColor: r.model === data.model_recommendations[0]?.model ? 'primary.main' : 'divider',
                    borderWidth: r.model === data.model_recommendations[0]?.model ? 2 : 1,
                    height: '100%',
                    bgcolor: r.model === data.model_recommendations[0]?.model ? 'primary.lighter' : 'transparent',
                  }}
                >
                  <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 0.5 }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                      {MODEL_LABELS[r.model] ?? r.model.toUpperCase()}
                    </Typography>
                    <Chip
                      label={`Score ${(r.score * 100).toFixed(0)}%`}
                      color="primary"
                      size="small"
                    />
                  </Stack>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    {r.reason}
                  </Typography>
                  {MODEL_DESCRIPTIONS[r.model] && (
                    <Typography variant="caption" color="text.disabled">
                      {MODEL_DESCRIPTIONS[r.model]}
                    </Typography>
                  )}
                </Box>
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>
    </PageContainer>
  );
}
