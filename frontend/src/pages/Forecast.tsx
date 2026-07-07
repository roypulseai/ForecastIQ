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
  Divider,
  FormControlLabel,
  Grid,
  LinearProgress,
  MenuItem,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
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
import { useStore } from '../store/appStore';
import { getErrorMessage } from '../services/api';
import {
  FILE_TYPE_LABELS,
  type AggregationConfig,
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
  aggregation: DEFAULT_AGGREGATION,
});

interface ExternalState {
  media_plan: boolean;
  promotions: boolean;
  holidays: boolean;
  events: boolean;
  weather: boolean;
  competitor: boolean;
  economic: boolean;
}

const initialExternal: ExternalState = {
  media_plan: false,
  promotions: false,
  holidays: false,
  events: false,
  weather: false,
  competitor: false,
  economic: false,
};

export function ForecastPage(): ReactNode {
  const navigate = useNavigate();
  const analysisData = useStore((s) => s.analysisData);
  const uploadedFiles = useStore((s) => s.uploadedFiles);
  const setCurrentForecastId = useStore((s) => s.setCurrentForecastId);
  const filesQuery = useFiles();
  const createMut = useCreateForecast();
  const [jobId, setJobId] = useState<string | null>(null);
  const jobQuery = useJobStatus(jobId);
  const [error, setError] = useState<string | null>(null);

  // When the job completes, fetch the result and navigate
  useEffect(() => {
    if (!jobQuery.data) return;
    if (jobQuery.data.status === 'completed') {
      const result = jobQuery.data as { result?: { forecast_id?: string } };
      const forecastId = result.result?.forecast_id;
      if (forecastId) {
        setCurrentForecastId(forecastId);
        setJobId(null);
        navigate('/results');
      }
    } else if (jobQuery.data.status === 'failed') {
      setError(jobQuery.data.error || 'Forecast failed');
      setJobId(null);
    }
  }, [jobQuery.data, navigate, setCurrentForecastId]);

  const dateColumn = analysisData?.validation.date_column ?? 'date';
  const valueColumn = analysisData?.validation.value_column ?? 'value';
  const columns = useMemo(() => {
    const sales = uploadedFiles.find((f) => f.type === 'sales');
    return sales?.columns ?? [];
  }, [uploadedFiles]);

  const [request, setRequest] = useState<ForecastRequest>(() => initialRequest(dateColumn, valueColumn));
  const [external, setExternal] = useState<ExternalState>(initialExternal);
  const [useEnsemble, setUseEnsemble] = useState<boolean>(false);
  const [useAdvanced, setUseAdvanced] = useState<boolean>(false);
  const [useAggregation, setUseAggregation] = useState<boolean>(false);

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
      ensemble_models: useEnsemble && request.ensemble_models?.length ? request.ensemble_models : undefined,
      aggregation: useAggregation ? request.aggregation : undefined,
      parameters: Object.keys(request.parameters ?? {}).length > 0 ? request.parameters : undefined,
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
        <Button
          variant="contained"
          size="large"
          startIcon={createMut.isPending || jobId ? <CircularProgress size={16} color="inherit" /> : <PlayArrowIcon />}
          onClick={handleSubmit}
          disabled={createMut.isPending || !!jobId || !request.models.length}
        >
          {createMut.isPending ? 'Submitting…' : jobId ? 'Forecasting…' : 'Run forecast'}
        </Button>
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
                    disabled={!columns.length}
                    helperText={columns.length ? `${columns.length} columns available` : 'no columns detected'}
                  >
                    {columns.map((c) => (
                      <MenuItem key={c} value={c}>
                        {c}
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
                    disabled={!columns.length}
                    helperText={columns.length ? `${columns.length} columns available` : 'no columns detected'}
                  >
                    {columns.map((c) => (
                      <MenuItem key={c} value={c}>
                        {c}
                      </MenuItem>
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
