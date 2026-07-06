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
  Typography,
} from '@mui/material';
import InsightsIcon from '@mui/icons-material/Insights';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import TimelineIcon from '@mui/icons-material/Timeline';
import { PageContainer } from '../components/layout/PageContainer';
import { DataSummary } from '../components/explore/DataSummary';
import { TimeSeriesChart } from '../components/explore/TimeSeriesChart';
import { DistributionChart } from '../components/explore/DistributionChart';
import { DecompositionChart } from '../components/explore/DecompositionChart';
import { useStore } from '../store/appStore';
import { useAnalyze } from '../hooks/useAnalysis';
import { useFiles } from '../hooks/useFiles';
import { getErrorMessage } from '../services/api';
import { formatDate, formatNumber } from '../utils/format';

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
  const salesFileId = useStore((s) => s.salesFileId);
  const uploadedFiles = useStore((s) => s.uploadedFiles);
  const filesQuery = useFiles();
  const analyzeMut = useAnalyze();
  const [error, setError] = useState<string | null>(null);
  const [decompPeriod, setDecompPeriod] = useState<number>(7);
  const [bins, setBins] = useState<number>(25);

  useEffect(() => {
    if (filesQuery.isError) {
      setError(getErrorMessage(filesQuery.error));
    }
  }, [filesQuery.isError, filesQuery.error]);

  const salesFile = useMemo(
    () => uploadedFiles.find((f) => f.type === 'sales') ?? null,
    [uploadedFiles],
  );

  const hasAnalysis = Boolean(analysisData);

  const dates = useMemo(() => {
    if (!analysisData) return [];
    const { min_date, max_date } = analysisData.data_characteristics;
    if (!min_date || !max_date) return [];
    return generateDailySeries(min_date, max_date);
  }, [analysisData]);

  const values = useMemo(() => {
    if (!analysisData) return [];
    const { mean, std, trend, seasonality, length, outliers_pct } =
      analysisData.data_characteristics;
    if (!length) return [];
    return synthSeries({
      length,
      mean,
      std,
      trend,
      seasonality,
      outliersPct: outliers_pct,
      dates,
    });
  }, [analysisData, dates]);

  const handleAnalyze = async () => {
    const target = salesFileId ?? salesFile?.file_id;
    if (!target) return;
    setError(null);
    try {
      await analyzeMut.mutateAsync(target);
    } catch (e) {
      setError(getErrorMessage(e));
    }
  };

  if (filesQuery.isLoading) {
    return (
      <PageContainer title="Explore data">
        <Stack alignItems="center" sx={{ py: 8 }}>
          <CircularProgress />
          <Typography sx={{ mt: 2 }}>Loading files…</Typography>
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

  if (!hasAnalysis) {
    return (
      <PageContainer title="Explore data">
        <Card sx={{ p: 4, textAlign: 'center' }}>
          <ShowChartIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
          <Typography variant="h5" gutterBottom>
            Analysis required
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Run an analysis on your sales file to view interactive charts.
          </Typography>
          <Button
            variant="contained"
            onClick={handleAnalyze}
            disabled={analyzeMut.isPending}
            startIcon={
              analyzeMut.isPending ? <CircularProgress size={16} color="inherit" /> : <InsightsIcon />
            }
          >
            {analyzeMut.isPending ? 'Analyzing…' : 'Analyze now'}
          </Button>
          {error && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {error}
            </Alert>
          )}
        </Card>
      </PageContainer>
    );
  }

  const data = analysisData!;

  const dateRange: [string, string] | null =
    data.data_characteristics.min_date && data.data_characteristics.max_date
      ? [data.data_characteristics.min_date, data.data_characteristics.max_date]
      : null;

  const recommendations = data.model_recommendations;

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
            Re-analyze
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

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={6}>
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
                    {formatNumber(data.data_characteristics.length)} observations
                  </Typography>
                </Box>
              </Stack>
            </Grid>
            <Grid item xs={12} md={6}>
              <Stack direction="row" spacing={1.5} justifyContent={{ xs: 'flex-start', md: 'flex-end' }}>
                <Chip
                  label={data.validation.valid ? 'Valid' : 'Has warnings'}
                  color={data.validation.valid ? 'success' : 'warning'}
                  size="small"
                />
                {data.validation.warnings.slice(0, 1).map((w, i) => (
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
          totalRows={data.validation.row_count || data.data_characteristics.length}
        />
      </Box>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} lg={8}>
          <TimeSeriesChart data={values.map((v, i) => ({ date: dates[i] ?? '', value: v }))} title="Sales over time" />
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

      {recommendations.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h5" sx={{ mb: 2 }}>
              Recommended models
            </Typography>
            <Grid container spacing={2}>
              {recommendations.map((r) => (
                <Grid key={r.model} item xs={12} sm={6} md={4}>
                  <Box
                    sx={{
                      p: 2,
                      borderRadius: 1.5,
                      border: '1px solid',
                      borderColor: 'divider',
                      height: '100%',
                    }}
                  >
                    <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 0.5 }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                        {r.model.toUpperCase()}
                      </Typography>
                      <Chip
                        label={`Score ${(r.score * 100).toFixed(0)}%`}
                        color="primary"
                        size="small"
                      />
                    </Stack>
                    <Typography variant="body2" color="text.secondary">
                      {r.reason}
                    </Typography>
                  </Box>
                </Grid>
              ))}
            </Grid>
          </CardContent>
        </Card>
      )}

      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 3 }}>
        Charts are derived from analysis metadata (mean, std, trend, seasonality, frequency). For exact
        values, re-run the analysis. Generated {formatDate(new Date().toISOString(), true)}.
      </Typography>
    </PageContainer>
  );
}

function generateDailySeries(start: string, end: string): string[] {
  const result: string[] = [];
  const s = new Date(start);
  const e = new Date(end);
  if (Number.isNaN(s.getTime()) || Number.isNaN(e.getTime())) return result;
  const cur = new Date(s);
  while (cur <= e) {
    result.push(cur.toISOString().slice(0, 10));
    cur.setDate(cur.getDate() + 1);
  }
  return result;
}

interface SynthArgs {
  length: number;
  mean: number;
  std: number;
  trend: 'increasing' | 'decreasing' | 'flat' | string;
  seasonality: 'daily' | 'weekly' | 'monthly' | 'yearly' | 'none' | string;
  outliersPct: number;
  dates: string[];
}

function synthSeries({ length, mean, std, trend, seasonality, outliersPct, dates }: SynthArgs): number[] {
  const n = Math.max(1, length);
  const series: number[] = new Array(n);
  const trendSlope = trend === 'increasing' ? 0.05 : trend === 'decreasing' ? -0.05 : 0;
  const seasonalStrength = seasonality === 'none' ? 0 : 0.2;
  const period = seasonality === 'weekly' ? 7 : seasonality === 'monthly' ? 30 : seasonality === 'yearly' ? 365 : 7;
  for (let i = 0; i < n; i += 1) {
    const trendComponent = trendSlope * i;
    const seasonalComponent =
      seasonalStrength * mean * Math.sin((2 * Math.PI * i) / period);
    const noise = (pseudoRandom(i) - 0.5) * 2 * std * 0.6;
    let v = mean + trendComponent + seasonalComponent + noise;
    if (outliersPct > 0 && pseudoRandom(i + 999) < outliersPct) {
      v += (pseudoRandom(i + 1234) > 0.5 ? 1 : -1) * std * 3;
    }
    series[i] = Math.max(0, v);
  }
  if (dates.length && dates.length !== n) {
    return series.slice(0, dates.length);
  }
  return series;
}

function pseudoRandom(seed: number): number {
  const x = Math.sin(seed * 12.9898) * 43758.5453;
  return x - Math.floor(x);
}
