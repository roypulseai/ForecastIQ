import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Collapse,
  Divider,
  FormControl,
  FormControlLabel,
  Grid,
  InputLabel,
  LinearProgress,
  MenuItem,
  Select,
  Slider,
  Stack,
  Switch,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { PageContainer } from '../components/layout/PageContainer';
import { ModelSelector } from '../components/forecast/ModelSelector';
import { ParametersPanel } from '../components/forecast/ParametersPanel';
import { ExternalFactors } from '../components/forecast/ExternalFactors';
import { AggregationPanel } from '../components/forecast/AggregationPanel';
import { ForecastSummaryCard } from '../components/forecast/ForecastSummary';
import { useFiles } from '../hooks/useFiles';
import { useCreateForecast, useJobStatus } from '../hooks/useForecast';
import { useSavedModels, useForecastWithSavedModel } from '../hooks/useModels';
import { useStore } from '../store/appStore';
import { apiClient, getErrorMessage } from '../services/api';
import {
  BUSINESS_STAGE_LABELS,
  BUSINESS_TYPE_LABELS,
  FILE_TYPE_LABELS,
  MODEL_LABELS,
  type AggregationConfig,
  type BusinessStage,
  type BusinessType,
  type FileType,
  type Frequency,
  type ForecastRequest,
  type ModelParameters,
} from '../types';


const FREQ_OPTIONS: Array<{ value: Frequency; label: string }> = [
  { value: 'D', label: 'Daily' },
  { value: 'W', label: 'Weekly' },
  { value: 'F', label: 'Fortnightly' },
  { value: 'M', label: 'Monthly' },
  { value: 'Q', label: 'Quarterly' },
  { value: 'Y', label: 'Yearly' },
];

const DEFAULT_AGGREGATION: AggregationConfig = {
  time_rollup: 'M',
  product_level: 'category',
  region_level: 'national',
  agg_function: 'sum',
};

const DEFAULT_PARAMETERS: ModelParameters = {};

const initialRequest = (dateColumn: string, valueColumn: string): ForecastRequest => ({
  name: 'Untitled forecast',
  target_column: valueColumn,
  date_column: dateColumn,
  frequency: 'D',
  horizon: 30,
  models: ['prophet'],
  parameters: DEFAULT_PARAMETERS,
  ensemble_models: ['prophet', 'ets'],
  include_media_plan: false,
  include_promotions: false,
  include_holidays: false,
  include_events: false,
  include_weather: false,
  include_competitor: false,
  include_economic: false,
  auto_detect_events: false,
  auto_event_country: 'US',
  auto_event_regions: [],
  aggregation: DEFAULT_AGGREGATION,
  train_test_split: 1.0,
  backtest_overlap: 0,
  tune_hyperparameters: false,
  category_column: '',
  category_columns: [],
  save_model: false,
  save_model_name: '',
});

interface ExternalState {
  media_plan: boolean;
  promotions: boolean;
  holidays: boolean;
  events: boolean;
  weather: boolean;
  competitor: boolean;
  economic: boolean;
  auto_detect_events: boolean;
  auto_event_country: string | null;
  auto_event_regions: string[];
}

const initialExternal: ExternalState = {
  media_plan: false,
  promotions: false,
  holidays: false,
  events: false,
  weather: false,
  competitor: false,
  economic: false,
  auto_detect_events: false,
  auto_event_country: 'US',
  auto_event_regions: [],
};

export function ForecastPage(): ReactNode {
  const navigate = useNavigate();
  const analysisData = useStore((s) => s.analysisData);
  const uploadedFiles = useStore((s) => s.uploadedFiles);
  const setCurrentForecastId = useStore((s) => s.setCurrentForecastId);
  const filesQuery = useFiles();
  const createMut = useCreateForecast();
  const savedModelsQuery = useSavedModels();
  const useSavedMut = useForecastWithSavedModel();
  const [jobId, setJobId] = useState<string | null>(null);
  const jobQuery = useJobStatus(jobId);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<'train' | 'saved'>('train');
  const [selectedSavedId, setSelectedSavedId] = useState<string>('');
  const [savedForecastResult, setSavedForecastResult] = useState<{
    model_name: string;
    forecast_values: Array<{ date: string; forecast: number; lower_ci: number; upper_ci: number; baseline?: number | null; uplift?: number | null }>;
  } | null>(null);

  // When the job completes, fetch the full result to get forecast_id
  const [completedJobId, setCompletedJobId] = useState<string | null>(null);
  useEffect(() => {
    if (!jobQuery.data) return;
    if (jobQuery.data.status === 'completed') {
      setCompletedJobId(jobId);
    } else if (jobQuery.data.status === 'failed') {
      setError(jobQuery.data.error || 'Forecast failed');
      setJobId(null);
    }
  }, [jobQuery.data, jobId]);

  useEffect(() => {
    if (!completedJobId) return;
    let cancelled = false;
    (async () => {
      try {
        const result = await apiClient.getJobResult(completedJobId);
        if (cancelled) return;
        const forecastId = result.result?.forecast_id;
        if (forecastId) {
          setCurrentForecastId(forecastId);
          setJobId(null);
          setCompletedJobId(null);
          navigate('/results');
        } else {
          setError('Forecast completed but no result ID returned');
          setJobId(null);
          setCompletedJobId(null);
        }
      } catch (e) {
        if (cancelled) return;
        setError(getErrorMessage(e));
        setJobId(null);
        setCompletedJobId(null);
      }
    })();
    return () => { cancelled = true; };
  }, [completedJobId, navigate, setCurrentForecastId]);

  const dateColumn = analysisData?.validation.date_column ?? 'date';
  const valueColumn = analysisData?.validation.value_column ?? 'value';
  const salesFile = uploadedFiles.find((f) => f.type === 'sales');
  // Pull real columns from the file metadata. If the file's `columns` is empty
  // (older uploads), try the analysis validation's column names.
  const columns = useMemo(() => {
    const fromFile = salesFile?.columns ?? [];
    if (fromFile.length > 0) return fromFile;
    // Fall back to deriving columns from the analysis — at minimum we have
    // date_column and value_column.
    const fallback: string[] = [];
    if (analysisData?.validation.date_column) fallback.push(analysisData.validation.date_column);
    if (analysisData?.validation.value_column) fallback.push(analysisData.validation.value_column);
    if (analysisData?.validation.extra_columns?.length) {
      fallback.push(...analysisData.validation.extra_columns);
    }
    return fallback;
  }, [salesFile, analysisData]);

  // Column type detection — frontend gets the same types the backend inferred
  const columnTypes = analysisData?.validation.column_types ?? {};
  const typeColor = (t: string) => {
    switch (t) {
      case 'date': return 'primary';
      case 'numeric': return 'success';
      case 'region': return 'warning';
      case 'boolean': return 'info';
      default: return 'default';
    }
  };
  const sortedForDate = useMemo(
    () => [...columns]
      .filter((c) => columnTypes[c] === 'date')
      .sort((a, b) => a.localeCompare(b)),
    [columns, columnTypes],
  );
  const sortedForTarget = useMemo(
    () => [...columns]
      .filter((c) => columnTypes[c] === 'numeric')
      .sort((a, b) => a.localeCompare(b)),
    [columns, columnTypes],
  );
  // Category-eligible columns: categorical, region, or id type columns
  const categoryTypeSet = useMemo(() => new Set(['categorical', 'region', 'id']), []);
  const [request, setRequest] = useState<ForecastRequest>(() => initialRequest(dateColumn, valueColumn));
  const [external, setExternal] = useState<ExternalState>(initialExternal);
  const [useEnsemble, setUseEnsemble] = useState<boolean>(false);
  const [useAdvanced, setUseAdvanced] = useState<boolean>(false);
  const [useAggregation, setUseAggregation] = useState<boolean>(false);
  // sortedForCategory depends on request, so it must be declared after useState
  const sortedForCategory = useMemo(
    () => [...columns]
      .filter((c) => c !== request.date_column && c !== request.target_column && categoryTypeSet.has(columnTypes[c]))
      .sort((a, b) => a.localeCompare(b)),
    [columns, columnTypes, request.date_column, request.target_column, categoryTypeSet],
  );

  useEffect(() => {
    if (analysisData && request.date_column === 'date' && request.target_column === 'value') {
      setRequest((r) => ({
        ...r,
        date_column: dateColumn,
        target_column: valueColumn,
      }));
    }
  }, [analysisData, dateColumn, valueColumn, request.date_column, request.target_column]);

  if (!analysisData) {
    return (
      <PageContainer title="Forecast">
        <Card sx={{ p: 4, textAlign: 'center' }}>
          <Alert severity="info" sx={{ mb: 2 }}>
            No sales analysis available. Upload data and run analysis first.
          </Alert>
          <Button variant="contained" onClick={() => navigate('/upload')}>
            Go to upload
          </Button>
        </Card>
      </PageContainer>
    );
  }

  const recommendations = analysisData.model_recommendations.map((r) => r.model);

  // Backtest overlap capped at 20% of unique dates
  const maxBacktestOverlap = useMemo(() => {
    const nDates = analysisData?.validation?.unique_dates;
    if (!nDates || nDates <= 0) return 0;
    return Math.max(1, Math.floor(nDates * 0.2));
  }, [analysisData]);

  const update = <K extends keyof ForecastRequest>(key: K, value: ForecastRequest[K]) =>
    setRequest((r) => ({ ...r, [key]: value }));

  const updateParam = (next: ModelParameters) => setRequest((r) => ({ ...r, parameters: next }));

  const updateAggregation = (next: AggregationConfig) =>
    setRequest((r) => ({ ...r, aggregation: useAggregation ? next : undefined }));

  const handleSubmit = async () => {
    setError(null);
    if (!request.models.length) {
      setError('Select at least one model');
      return;
    }
    if (request.horizon < 1) {
      setError('Horizon must be at least 1 period');
      return;
    }
    const payload: ForecastRequest = {
      ...request,
      include_media_plan: external.media_plan,
      include_promotions: external.promotions,
      include_holidays: external.holidays,
      include_events: external.events,
      include_weather: external.weather,
      include_competitor: external.competitor,
      include_economic: external.economic,
      auto_detect_events: external.auto_detect_events,
      auto_event_country: external.auto_event_country,
      auto_event_regions: external.auto_event_regions,
      ensemble_models: useEnsemble && request.ensemble_models?.length ? request.ensemble_models : undefined,
      aggregation: useAggregation ? request.aggregation : undefined,
      parameters: Object.keys(request.parameters ?? {}).length > 0 ? request.parameters : undefined,
      train_test_split: request.train_test_split ?? 1.0,
      backtest_overlap: request.backtest_overlap ?? 0,
      tune_hyperparameters: request.tune_hyperparameters ?? false,
      save_model: request.save_model ?? false,
      save_model_name: request.save_model_name || undefined,
    };
    try {
      setError(null);
      const res = await createMut.mutateAsync(payload);
      if ('jobId' in res && res.jobId) {
        // Async path: poll job status (handled by useJobStatus effect above)
        setJobId(res.jobId);
      } else if ('forecastId' in res && res.forecastId) {
        // Sync path (small/fast forecast)
        setCurrentForecastId(res.forecastId);
        navigate('/results');
      }
    } catch (e) {
      setError(getErrorMessage(e));
    }
  };

  return (
    <PageContainer
      title="Configure forecast"
      subtitle="Choose models, set parameters, and add external factors."
      actions={
        mode === 'train' ? (
        <Button
          variant="contained"
          size="large"
          startIcon={createMut.isPending || jobId ? <CircularProgress size={16} color="inherit" /> : <PlayArrowIcon />}
          onClick={handleSubmit}
          disabled={createMut.isPending || !!jobId || !request.models.length}
        >
          {createMut.isPending ? 'Submitting…' : jobId ? 'Forecasting…' : 'Run forecast'}
        </Button>
        ) : null
      }
    >
      {jobId && jobQuery.data && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Stack spacing={2}>
              <Stack direction="row" alignItems="center" justifyContent="space-between">
                <Typography variant="subtitle1" fontWeight={600}>
                  {jobQuery.data.status === 'completed' ? 'Forecast complete' : 'Running forecast…'}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {Math.round(jobQuery.data.progress * 100)}%
                </Typography>
              </Stack>
              <LinearProgress
                variant="determinate"
                value={Math.round(jobQuery.data.progress * 100)}
              />
              {jobQuery.data.message && (
                <Typography variant="body2" color="text.secondary">
                  {jobQuery.data.message}
                </Typography>
              )}
            </Stack>
          </CardContent>
        </Card>
      )}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ sm: 'center' }} justifyContent="space-between">
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>Forecast mode</Typography>
              <Typography variant="body2" color="text.secondary">
                {mode === 'train'
                  ? 'Train new models on the current data, then forecast.'
                  : 'Load a previously saved model and forecast — no retraining.'}
              </Typography>
            </Box>
            <FormControlLabel
              control={
                <Switch
                  checked={mode === 'saved'}
                  onChange={(_, c) => setMode(c ? 'saved' : 'train')}
                />
              }
              label={mode === 'saved' ? 'Use saved model' : 'Train new'}
            />
          </Stack>
          {mode === 'saved' && (
            <Box sx={{ mt: 2 }}>
              {savedModelsQuery.isLoading ? (
                <CircularProgress size={20} />
              ) : (savedModelsQuery.data?.items?.length ?? 0) === 0 ? (
                <Alert severity="info">
                  No saved models yet. Go to <b>Saved models</b> to train and save one first.
                </Alert>
              ) : (
                <Grid container spacing={2} alignItems="center">
                  <Grid item xs={12} md={6}>
                    <FormControl fullWidth size="small">
                      <InputLabel>Saved model</InputLabel>
                      <Select
                        value={selectedSavedId}
                        label="Saved model"
                        onChange={(e) => {
                          setSelectedSavedId(e.target.value);
                          setSavedForecastResult(null);
                        }}
                      >
                        {(savedModelsQuery.data?.items ?? []).map((m) => (
                          <MenuItem key={m.model_id} value={m.model_id}>
                            {m.name} · {MODEL_LABELS[m.model_type] ?? m.model_type} · test MAE{' '}
                            {m.metrics.mae != null ? m.metrics.mae.toFixed(2) : '—'}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <TextField
                      fullWidth
                      size="small"
                      type="number"
                      label="Horizon (days)"
                      value={request.horizon}
                      onChange={(e) => update('horizon', Math.max(1, Math.min(3650, Number(e.target.value) || 30)))}
                      inputProps={{ min: 1, max: 3650 }}
                    />
                  </Grid>
                  <Grid item xs={12} md={2}>
                    <Button
                      fullWidth
                      variant="contained"
                      disabled={!selectedSavedId || useSavedMut.isPending}
                      onClick={async () => {
                        setError(null);
                        try {
                          const res = await useSavedMut.mutateAsync({
                            modelId: selectedSavedId,
                            request: { horizon: request.horizon },
                          });
                          setSavedForecastResult({
                            model_name: res.model_name,
                            forecast_values: res.forecast_values,
                          });
                        } catch (e) {
                          setError(getErrorMessage(e));
                        }
                      }}
                    >
                      {useSavedMut.isPending ? 'Forecasting…' : 'Forecast'}
                    </Button>
                  </Grid>
                </Grid>
              )}
              {savedForecastResult && (
                <Box sx={{ mt: 2, p: 2, borderRadius: 1.5, bgcolor: 'background.default' }}>
                  <Typography variant="subtitle2" sx={{ mb: 1 }}>
                    Forecast with <b>{savedForecastResult.model_name}</b> — {savedForecastResult.forecast_values.length} points
                  </Typography>
                  <Box sx={{ maxHeight: 240, overflow: 'auto' }}>
                    {savedForecastResult.forecast_values.slice(0, 10).map((v, i) => (
                      <Box key={i} sx={{ display: 'flex', justifyContent: 'space-between', py: 0.25 }}>
                        <Typography variant="caption" color="text.secondary">{v.date}</Typography>
                        <Typography variant="caption" sx={{ fontWeight: 600 }}>
                          {v.forecast.toFixed(2)}{' '}
                          <span style={{ color: '#888' }}>
                            ({v.lower_ci.toFixed(1)}–{v.upper_ci.toFixed(1)})
                          </span>
                        </Typography>
                      </Box>
                    ))}
                    {savedForecastResult.forecast_values.length > 10 && (
                      <Typography variant="caption" color="text.disabled" sx={{ display: 'block', mt: 0.5 }}>
                        …and {savedForecastResult.forecast_values.length - 10} more
                      </Typography>
                    )}
                  </Box>
                </Box>
              )}
            </Box>
          )}
        </CardContent>
      </Card>

      {mode === 'train' && (
      <Grid container spacing={3}>
        <Grid item xs={12} lg={8}>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h5" gutterBottom>
                1. Basic configuration
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Forecast name"
                    value={request.name}
                    onChange={(e) => update('name', e.target.value)}
                    inputProps={{ maxLength: 80 }}
                  />
                </Grid>
                <Grid item xs={12} sm={3}>
                  <TextField
                    fullWidth
                    select
                    label="Frequency"
                    value={request.frequency}
                    onChange={(e) => update('frequency', e.target.value as Frequency)}
                  >
                    {FREQ_OPTIONS.map((o) => (
                      <MenuItem key={o.value} value={o.value}>
                        {o.label}
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>
                <Grid item xs={12} sm={3}>
                  <TextField
                    fullWidth
                    type="number"
                    label={`Horizon (${request.frequency})`}
                    value={request.horizon}
                    inputProps={{ min: 1, max: 365 }}
                    onChange={(e) => update('horizon', Math.max(1, Math.min(365, Number(e.target.value) || 1)))}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    select
                    label="Date column"
                    value={request.date_column}
                    onChange={(e) => update('date_column', e.target.value)}
                    helperText={
                      columns.length
                        ? `${columns.length} columns · date columns shown first`
                        : 'no columns detected — re-upload your file'
                    }
                  >
                    {columns.length === 0 && (
                      <MenuItem value={request.date_column} disabled>
                        {request.date_column}
                      </MenuItem>
                    )}
                    {sortedForDate.map((c) => (
                      <MenuItem key={c} value={c}>
                        <Stack direction="row" alignItems="center" spacing={1}>
                          <Typography variant="body2">{c}</Typography>
                          <Chip label={columnTypes[c] || '?'} size="small" color={typeColor(columnTypes[c] || '')} variant="outlined" sx={{ height: 18, fontSize: 10 }} />
                        </Stack>
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    select
                    label="Target column"
                    value={request.target_column}
                    onChange={(e) => update('target_column', e.target.value)}
                    helperText={
                      columns.length
                        ? `${columns.length} columns · numeric columns shown first`
                        : 'no columns detected — re-upload your file'
                    }
                  >
                    {columns.length === 0 && (
                      <MenuItem value={request.target_column} disabled>
                        {request.target_column}
                      </MenuItem>
                    )}
                    {sortedForTarget.map((c) => (
                      <MenuItem key={c} value={c}>
                        <Stack direction="row" alignItems="center" spacing={1}>
                          <Typography variant="body2">{c}</Typography>
                          <Chip label={columnTypes[c] || '?'} size="small" color={typeColor(columnTypes[c] || '')} variant="outlined" sx={{ height: 18, fontSize: 10 }} />
                        </Stack>
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Autocomplete
                    multiple
                    size="small"
                    options={sortedForCategory}
                    value={request.category_columns ?? []}
                    onChange={(_, newVal) => update('category_columns', newVal)}
                    disableCloseOnSelect
                    renderTags={(value, getTagProps) =>
                      value.map((option, index) => (
                        <Chip label={option} size="small" {...getTagProps({ index })} />
                      ))
                    }
                    renderOption={(props, option) => (
                      <li {...props}>
                        <Stack direction="row" alignItems="center" spacing={1}>
                          <Typography variant="body2">{option}</Typography>
                          <Chip label={columnTypes[option] || '?'} size="small" color={typeColor(columnTypes[option] || '')} variant="outlined" sx={{ height: 18, fontSize: 10 }} />
                        </Stack>
                      </li>
                    )}
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        label="Category breakdown (optional)"
                        helperText={
                          sortedForCategory.length
                            ? 'Run a separate forecast for each combination of selected columns'
                            : 'No categorical columns detected'
                        }
                      />
                    )}
                  />
                </Grid>
              </Grid>

              <Divider sx={{ my: 3 }} />
              <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
                Evaluation & persistence
              </Typography>
              <Grid container spacing={3}>
                <Grid item xs={12} sm={6}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Train/test split <Chip label="ML models only" size="small" color="info" variant="outlined" sx={{ ml: 0.5, height: 18, fontSize: 10 }} />
                    <Tooltip title="Fraction of data used for training. The rest is held out for evaluation of ML models (XGBoost, LightGBM). Time-series models always train on 100% of data.">
                      <InfoOutlinedIcon sx={{ fontSize: 14, ml: 0.5, verticalAlign: 'text-top', color: 'text.disabled' }} />
                    </Tooltip>
                  </Typography>
                  <Slider
                    value={request.train_test_split ?? 1.0}
                    min={0.5}
                    max={1.0}
                    step={0.05}
                    marks={[
                      { value: 0.5, label: '50%' },
                      { value: 0.8, label: '80%' },
                      { value: 1.0, label: '100%' },
                    ]}
                    onChange={(_, v) => update('train_test_split', v as number)}
                    valueLabelDisplay="auto"
                    valueLabelFormat={(v) => `${(v * 100).toFixed(0)}%`}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Backtest overlap (days)
                    <Tooltip title="Number of recent actual days to overlay on the forecast chart for visual comparison. 0 = no overlap.">
                      <InfoOutlinedIcon sx={{ fontSize: 14, ml: 0.5, verticalAlign: 'text-top', color: 'text.disabled' }} />
                    </Tooltip>
                  </Typography>
                  <Slider
                    value={Math.min(request.backtest_overlap ?? 0, maxBacktestOverlap)}
                    min={0}
                    max={maxBacktestOverlap}
                    step={1}
                    marks={
                      maxBacktestOverlap > 0
                        ? [
                            { value: 0, label: '0' },
                            ...(maxBacktestOverlap >= 30 ? [{ value: Math.min(30, maxBacktestOverlap), label: '30d' }] : []),
                            ...(maxBacktestOverlap >= 90 ? [{ value: Math.min(90, maxBacktestOverlap), label: '90d' }] : []),
                            { value: maxBacktestOverlap, label: `${maxBacktestOverlap}d` },
                          ]
                        : [{ value: 0, label: '0' }]
                    }
                    onChange={(_, v) => update('backtest_overlap', v as number)}
                    valueLabelDisplay="auto"
                    valueLabelFormat={(v) => `${v}d`}
                  />
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                    Maximum {maxBacktestOverlap}d (20% of data span)
                  </Typography>
                </Grid>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={request.tune_hyperparameters ?? false}
                        onChange={(_, c) => update('tune_hyperparameters', c)}
                      />
                    }
                    label="Tune hyperparameters (time-series CV randomized search)"
                  />
                </Grid>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={request.save_model ?? false}
                        onChange={(_, c) => update('save_model', c)}
                      />
                    }
                    label="Save best model to registry after run"
                  />
                  <Collapse in={request.save_model ?? false}>
                    <Box sx={{ mt: 1.5, pl: 4 }}>
                      <TextField
                        fullWidth
                        size="small"
                        label="Model name (optional)"
                        placeholder="Leave blank for auto-name"
                        value={request.save_model_name ?? ''}
                        onChange={(e) => update('save_model_name', e.target.value)}
                        inputProps={{ maxLength: 120 }}
                      />
                    </Box>
                  </Collapse>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Stack
                direction="row"
                alignItems="center"
                justifyContent="space-between"
                sx={{ mb: 2 }}
              >
                <Box>
                  <Typography variant="h5">2. Models</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {recommendations.length > 0
                      ? 'Pre-selected from the model recommender. Toggle to customize.'
                      : 'Select one or more models to run.'}
                  </Typography>
                </Box>
                <FormControlLabel
                  control={
                    <Switch
                      checked={useEnsemble}
                      onChange={(_, c) => setUseEnsemble(c)}
                    />
                  }
                  label="Ensemble"
                />
              </Stack>
              <ModelSelector
                models={[]}
                selected={request.models}
                onChange={(m) => update('models', m)}
                recommended={recommendations}
              />
              {analysisData.model_recommendations.length > 0 && (
                <Box
                  sx={{
                    mt: 2,
                    p: 2,
                    borderRadius: 1.5,
                    border: '1px dashed',
                    borderColor: 'divider',
                    bgcolor: 'background.default',
                  }}
                >
                  <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary' }}>
                    Why these models?
                  </Typography>
                  <Stack spacing={0.5} sx={{ mt: 0.5 }}>
                    {analysisData.model_recommendations.map((rec) => (
                      <Typography key={rec.model} variant="caption" color="text.secondary">
                        • <b>{MODEL_LABELS[rec.model] ?? rec.model.toUpperCase()}</b> —{' '}
                        {rec.reason} (score {(rec.score * 100).toFixed(0)}%)
                      </Typography>
                    ))}
                  </Stack>
                </Box>
              )}
              {useEnsemble && (
                <Box sx={{ mt: 3 }}>
                  <Divider sx={{ mb: 2 }} />
                  <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
                    Ensemble members
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Choose which models to combine. The ensemble weights are auto-computed from cross-validation
                    performance.
                  </Typography>
                  <ModelSelector
                    models={request.models}
                    selected={request.ensemble_models ?? []}
                    onChange={(m) => update('ensemble_models', m)}
                  />
                </Box>
              )}
            </CardContent>
          </Card>

          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Stack
                direction="row"
                alignItems="center"
                justifyContent="space-between"
                sx={{ mb: 1 }}
              >
                <Typography variant="h5">3. External factors</Typography>
                <Chip
                  label={`${uploadedFiles.length} file${uploadedFiles.length === 1 ? '' : 's'} loaded`}
                  size="small"
                  variant="outlined"
                />
              </Stack>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Enable to feed additional signals to models that support exogenous regressors (SARIMAX, LightGBM, XGBoost).
              </Typography>
              <ExternalFactors files={uploadedFiles} values={external} onChange={setExternal} />
            </CardContent>
          </Card>

          {/* Business context card */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h5" sx={{ mb: 1 }}>3b. Business context</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Helps the system recommend the right models and defaults for your industry and growth stage.
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    select
                    label="Industry / Business type"
                    value={request.business_type ?? ''}
                    onChange={(e) => update('business_type', (e.target.value || null) as BusinessType | null)}
                  >
                    <MenuItem value=""><em>Auto (not specified)</em></MenuItem>
                    {Object.entries(BUSINESS_TYPE_LABELS).map(([k, v]) => (
                      <MenuItem key={k} value={k}>{v}</MenuItem>
                    ))}
                  </TextField>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    select
                    label="Growth stage"
                    value={request.business_stage ?? ''}
                    onChange={(e) => update('business_stage', (e.target.value || null) as BusinessStage | null)}
                  >
                    <MenuItem value=""><em>Auto (not specified)</em></MenuItem>
                    {Object.entries(BUSINESS_STAGE_LABELS).map(([k, v]) => (
                      <MenuItem key={k} value={k}>{v}</MenuItem>
                    ))}
                  </TextField>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Stack
                direction="row"
                alignItems="center"
                justifyContent="space-between"
                sx={{ mb: 1 }}
              >
                <Typography variant="h5">4. Advanced</Typography>
                <FormControlLabel
                  control={
                    <Switch
                      checked={useAdvanced}
                      onChange={(_, c) => setUseAdvanced(c)}
                    />
                  }
                  label="Customize parameters"
                />
              </Stack>
              {useAdvanced ? (
                <ParametersPanel models={request.models} value={request.parameters ?? {}} onChange={updateParam} />
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Defaults work for most use cases. Toggle on to fine-tune individual model hyperparameters.
                </Typography>
              )}
              <Divider sx={{ my: 3 }} />
              <FormControlLabel
                control={
                  <Switch
                    checked={useAggregation}
                    onChange={(_, c) => setUseAggregation(c)}
                  />
                }
                label="Aggregate data before forecasting"
              />
              {useAggregation && (
                <Box sx={{ mt: 2 }}>
                  <AggregationPanel
                    value={request.aggregation ?? DEFAULT_AGGREGATION}
                    onChange={updateAggregation}
                  />
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} lg={4}>
          <Box sx={{ position: { lg: 'sticky' }, top: { lg: 80 } }}>
            <ForecastSummaryCard
              name={request.name}
              horizon={request.horizon}
              frequency={request.frequency}
              dateColumn={request.date_column}
              targetColumn={request.target_column}
              models={request.models}
              external={Object.entries(external)
                .filter(([, v]) => v)
                .map(([k]) => FILE_TYPE_LABELS[k as FileType] ?? k)}
              ensemble={useEnsemble}
              hasAggregation={useAggregation}
            />
            <Card sx={{ mt: 3 }}>
              <CardContent>
                <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 1 }}>
                  <CheckCircleIcon color="success" />
                  <Typography variant="h5">Quick start</Typography>
                </Stack>
                <Stack spacing={1.5}>
                  <Tip
                    title="Pick 2–3 models"
                    body="Prophet for trend+seasonality, ETS as a smooth baseline, LightGBM for non-linear patterns."
                  />
                  <Tip
                    title="External factors matter"
                    body="Add holidays + promotions for a quick uplift — they often drive 10–20% of the lift."
                  />
                  <Tip
                    title="30-day horizon"
                    body="Daily data with a 30-day horizon is a sweet spot for retail forecasting."
                  />
                </Stack>
              </CardContent>
            </Card>
          </Box>
        </Grid>
      </Grid>
      )}

      {filesQuery.isError && (
        <Alert severity="warning" sx={{ mt: 3 }}>
          {getErrorMessage(filesQuery.error)}
        </Alert>
      )}
    </PageContainer>
  );
}

function Tip({ title, body }: { title: string; body: string }): ReactNode {
  return (
    <Box>
      <Typography variant="body2" sx={{ fontWeight: 600 }}>
        {title}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        {body}
      </Typography>
    </Box>
  );
}
