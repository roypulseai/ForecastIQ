import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  FormControlLabel,
  Grid,
  IconButton,
  LinearProgress,
  MenuItem,
  Stack,
  Switch,
  Tab,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import AssessmentIcon from '@mui/icons-material/Assessment';
import { PageContainer } from '../components/layout/PageContainer';
import { ForecastChart } from '../components/results/ForecastChart';
import { ModelComparison } from '../components/results/ModelComparison';
import { ResultsTable } from '../components/results/ResultsTable';
import { ExportButton } from '../components/results/ExportButton';
import { MetricsCards } from '../components/results/MetricsCards';
import { useDeleteForecast, useForecastList } from '../hooks/useForecast';
import { useForecastResult } from '../hooks/useForecastResults';
import { useStore } from '../store/appStore';
import { getErrorMessage } from '../services/api';
import { formatDate } from '../utils/format';
import type { ForecastListItem, ModelResult } from '../types';

export function ResultsPage(): ReactNode {
  const navigate = useNavigate();
  const currentForecastId = useStore((s) => s.currentForecastId);
  const setCurrentForecastId = useStore((s) => s.setCurrentForecastId);
  const forecasts = useStore((s) => s.forecasts);
  const listQuery = useForecastList();
  const resultQuery = useForecastResult(currentForecastId);
  const deleteMut = useDeleteForecast();
  const [tab, setTab] = useState(0);
  const [selectedModel, setSelectedModel] = useState<string>('__ensemble__');
  const [showBaseline, setShowBaseline] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (listQuery.isError) setError(getErrorMessage(listQuery.error));
  }, [listQuery.isError, listQuery.error]);

  useEffect(() => {
    if (resultQuery.isError) setError(getErrorMessage(resultQuery.error));
  }, [resultQuery.isError, resultQuery.error]);

  useEffect(() => {
    if (resultQuery.data) {
      setSelectedModel(resultQuery.data.ensemble ? '__ensemble__' : firstModelKey(resultQuery.data.results));
    }
  }, [resultQuery.data]);

  const activeValues = useMemo(() => {
    if (!resultQuery.data) return [];
    if (selectedModel === '__ensemble__' && resultQuery.data.ensemble) {
      return resultQuery.data.ensemble.forecast_values;
    }
    const found = Object.values(resultQuery.data.results).find(
      (r) => r.model_name === selectedModel,
    );
    return found?.forecast_values ?? [];
  }, [resultQuery.data, selectedModel]);

  const activeModelLabel = useMemo(() => {
    if (selectedModel === '__ensemble__') return 'Ensemble';
    return selectedModel;
  }, [selectedModel]);

  if (listQuery.isLoading) {
    return (
      <PageContainer title="Results">
        <Stack alignItems="center" sx={{ py: 8 }}>
          <CircularProgress />
        </Stack>
      </PageContainer>
    );
  }

  if (!forecasts.length) {
    return (
      <PageContainer title="Results">
        <Card sx={{ p: 4, textAlign: 'center' }}>
          <AssessmentIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
          <Typography variant="h5" gutterBottom>
            No forecasts yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Run a forecast to see results here.
          </Typography>
          <Button variant="contained" onClick={() => navigate('/forecast')}>
            Configure a forecast
          </Button>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer
      title="Results"
      subtitle={resultQuery.data ? `${resultQuery.data.name} · ${formatDate(resultQuery.data.created_at, true)}` : 'Pick a forecast to view details'}
      actions={
        <Stack direction="row" spacing={1.5} alignItems="center">
          <TextField
            select
            size="small"
            label="Forecast"
            value={currentForecastId ?? ''}
            onChange={(e) => setCurrentForecastId(e.target.value)}
            sx={{ minWidth: 260 }}
          >
            {forecasts.map((f) => (
              <MenuItem key={f.forecast_id} value={f.forecast_id}>
                {f.name} · {formatDate(f.created_at)}
              </MenuItem>
            ))}
          </TextField>
          {currentForecastId && (
            <Tooltip title="Refresh">
              <IconButton
                onClick={() => resultQuery.refetch()}
                aria-label="Refresh forecast"
              >
                <RefreshIcon />
              </IconButton>
            </Tooltip>
          )}
          {currentForecastId && (
            <Tooltip title="Delete">
              <IconButton
                color="error"
                onClick={async () => {
                  if (!currentForecastId) return;
                  if (!window.confirm('Delete this forecast?')) return;
                  try {
                    await deleteMut.mutateAsync(currentForecastId);
                    setCurrentForecastId(null);
                    setError(null);
                  } catch (e) {
                    setError(getErrorMessage(e));
                  }
                }}
                aria-label="Delete forecast"
              >
                <DeleteOutlineIcon />
              </IconButton>
            </Tooltip>
          )}
          {resultQuery.data && activeValues.length > 0 && (
            <ExportButton
              detail={resultQuery.data}
              values={activeValues}
              modelName={activeModelLabel}
            />
          )}
        </Stack>
      }
    >
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {resultQuery.isLoading && <LinearProgress sx={{ mb: 3 }} />}

      {!resultQuery.data && currentForecastId && (
        <Card sx={{ p: 4, textAlign: 'center' }}>
          <CircularProgress />
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            Loading forecast…
          </Typography>
        </Card>
      )}

      {!currentForecastId && (
        <Card>
          <CardContent>
            <Typography variant="h5" sx={{ mb: 2 }}>
              Pick a forecast
            </Typography>
            <Stack divider={<Box sx={{ borderBottom: '1px solid', borderBottomColor: 'divider' }} />}>
              {forecasts.map((f) => (
                <ForecastRow
                  key={f.forecast_id}
                  forecast={f}
                  onSelect={() => setCurrentForecastId(f.forecast_id)}
                />
              ))}
            </Stack>
          </CardContent>
        </Card>
      )}

      {resultQuery.data && (
        <>
          <Box sx={{ mb: 3 }}>
            <MetricsCards
              summary={resultQuery.data.summary ?? null}
              bestModel={resultQuery.data.ensemble ? 'ensemble' : resultQuery.data.request.models[0] ?? null}
              rankings={
                resultQuery.data.ensemble
                  ? [{ model: 'ensemble', mae: null, rmse: null, mape: null, score: 1, name: 'Ensemble' }]
                  : Object.values(resultQuery.data.results).map((r) => ({
                      model: r.model_name,
                      mae: r.metrics.mae ?? null,
                      rmse: r.metrics.rmse ?? null,
                      mape: r.metrics.mape ?? null,
                      score: r.metrics.score ?? null,
                      name: r.model_name,
                    }))
              }
            />
          </Box>

          <Card sx={{ mb: 3 }}>
            <Tabs
              value={tab}
              onChange={(_, v) => setTab(v)}
              variant="scrollable"
              scrollButtons="auto"
              sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}
            >
              <Tab label="Forecast chart" />
              <Tab label="Model comparison" />
              <Tab label="Detailed data" />
              <Tab label="Metrics" />
            </Tabs>
            <CardContent>
              {tab === 0 && (
                <Stack spacing={2}>
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <FormControlLabel
                      control={
                        <Switch
                          checked={showBaseline}
                          onChange={(_, c) => setShowBaseline(c)}
                        />
                      }
                      label="Show baseline"
                    />
                  </Stack>
                  <ForecastChart
                    detail={resultQuery.data}
                    selectedModel={selectedModel}
                    onModelChange={setSelectedModel}
                    showBaseline={showBaseline}
                    onShowBaselineChange={setShowBaseline}
                  />
                </Stack>
              )}
              {tab === 1 && (
                <ModelComparison
                  rankings={Object.values(resultQuery.data.results).map((r) => ({
                    model: r.model_name,
                    name: r.model_name,
                    mae: r.metrics.mae ?? null,
                    rmse: r.metrics.rmse ?? null,
                    mape: r.metrics.mape ?? null,
                    score: r.metrics.score ?? null,
                  }))}
                  bestModel={resultQuery.data.ensemble ? 'ensemble' : resultQuery.data.request.models[0] ?? null}
                />
              )}
              {tab === 2 && (
                <ResultsTable
                  values={activeValues}
                  modelName={activeModelLabel}
                />
              )}
              {tab === 3 && (
                <Grid container spacing={2}>
                  {Object.values(resultQuery.data.results).map((r) => (
                    <Grid key={r.model_name} item xs={12} sm={6} md={4}>
                      <ModelMetricsCard result={r} />
                    </Grid>
                  ))}
                </Grid>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </PageContainer>
  );
}

function firstModelKey(results: Record<string, ModelResult>): string {
  const first = Object.values(results)[0];
  return first ? first.model_name : '';
}

function ForecastRow({
  forecast,
  onSelect,
}: {
  forecast: ForecastListItem;
  onSelect: () => void;
}): ReactNode {
  return (
    <Box
      onClick={onSelect}
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        py: 1.5,
        cursor: 'pointer',
        '&:hover': { backgroundColor: 'background.subtle' },
        px: 1,
        borderRadius: 1,
      }}
    >
      <Box>
        <Typography variant="subtitle2">{forecast.name}</Typography>
        <Typography variant="caption" color="text.secondary">
          {formatDate(forecast.created_at, true)} · horizon {forecast.horizon} · {forecast.models.length} model
          {forecast.models.length === 1 ? '' : 's'}
        </Typography>
      </Box>
      <Stack direction="row" spacing={1}>
        {forecast.best_model && (
          <Chip label={forecast.best_model} size="small" color="primary" variant="outlined" />
        )}
        <Button component={RouterLink} to="/forecast" size="small">
          New run
        </Button>
      </Stack>
    </Box>
  );
}

function ModelMetricsCard({ result }: { result: ModelResult }): ReactNode {
  const m = result.metrics;
  return (
    <Card>
      <CardContent>
        <Typography variant="overline" color="text.secondary">
          {result.model_name.toUpperCase()}
        </Typography>
        <Stack spacing={1} sx={{ mt: 1 }}>
          <MetricRow label="MAE" value={m.mae} />
          <MetricRow label="RMSE" value={m.rmse} />
          <MetricRow label="MAPE" value={m.mape} fmt="pct" />
          <MetricRow label="R²" value={m.r2} />
          {result.error && (
            <Alert severity="warning">
              {result.error}
            </Alert>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}

function MetricRow({
  label,
  value,
  fmt = 'num',
}: {
  label: string;
  value: number | undefined | null;
  fmt?: 'num' | 'pct';
}): ReactNode {
  return (
    <Stack direction="row" justifyContent="space-between" alignItems="center">
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body2" sx={{ fontWeight: 600 }}>
        {value === null || value === undefined || !Number.isFinite(value)
          ? '—'
          : fmt === 'pct'
            ? `${(value * 100).toFixed(2)}%`
            : value.toFixed(2)}
      </Typography>
    </Stack>
  );
}
