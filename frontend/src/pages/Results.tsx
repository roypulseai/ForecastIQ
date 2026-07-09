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
  Divider,
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
import { useFileData, useFiles } from '../hooks/useFiles';
import { useStore } from '../store/appStore';
import { getErrorMessage } from '../services/api';
import { formatDate } from '../utils/format';
import type { AnalysisResponse, ExternalFactorAnalysis, ForecastListItem, LagAnalysisResult, ModelResult } from '../types';

export function ResultsPage(): ReactNode {
  const navigate = useNavigate();
  const currentForecastId = useStore((s) => s.currentForecastId);
  const setCurrentForecastId = useStore((s) => s.setCurrentForecastId);
  const forecasts = useStore((s) => s.forecasts);
  const uploadedFiles = useStore((s) => s.uploadedFiles);
  const listQuery = useForecastList();
  const filesQuery = useFiles();
  const resultQuery = useForecastResult(currentForecastId);
  const deleteMut = useDeleteForecast();
  const [tab, setTab] = useState(0);
  const [selectedModel, setSelectedModel] = useState<string>('__ensemble__');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [showBaseline, setShowBaseline] = useState<boolean>(true);
  const [showActuals, setShowActuals] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const analysisData = useStore((s) => s.analysisData);

  // Find the sales file used by the current forecast.
  // Prefer the global sales file, but fall back to the file_id stored in the
  // forecast result (so that fresh navigations always find the source data).
  const salesFile = useMemo(() => {
    const fromQuery = filesQuery.data?.find((f) => f.type === 'sales') ?? null;
    if (fromQuery) return fromQuery;
    const fromUploaded = uploadedFiles.find((f) => f.type === 'sales') ?? null;
    if (fromUploaded) return fromUploaded;
    const forecastFileId = resultQuery.data?.data_file_id;
    if (forecastFileId) {
      const fromForecast =
        filesQuery.data?.find((f) => f.file_id === forecastFileId) ?? null;
      if (fromForecast) return fromForecast;
      // Return a stub so the file-data query is enabled with the right id
      return { file_id: forecastFileId } as any;
    }
    return null;
  }, [filesQuery.data, uploadedFiles, resultQuery.data?.data_file_id]);
  const fileDataQuery = useFileData(salesFile?.file_id, 5000);

  // Compute historical actuals for the chart.
  // Try exact match from request/analysis column names first, then
  // fall back to case-insensitive matching so old forecasts created
  // before column-name detection still show actuals.
  const actuals = useMemo(() => {
    if (!fileDataQuery.data || !resultQuery.data) return [] as Array<{ date: string; value: number }>;
    const rows = fileDataQuery.data.rows;
    if (rows.length === 0) return [];
    const columns: string[] = fileDataQuery.data.columns ?? Object.keys(rows[0]);

    const findCol = (...candidates: (string | null | undefined)[]): string | null => {
      for (const c of candidates) {
        if (c && columns.includes(c)) return c;
      }
      for (const c of candidates) {
        if (!c) continue;
        const m = columns.find((col) => col.toLowerCase() === c.toLowerCase());
        if (m) return m;
      }
      return null;
    };

    const dc = findCol(
      resultQuery.data.request.date_column,
      analysisData?.validation?.date_column,
      'date', 'Date', 'ds', 'timestamp', 'datetime',
    );
    const vc = findCol(
      resultQuery.data.request.target_column,
      analysisData?.validation?.value_column,
      'value', 'Value', 'y', 'sales', 'Sales', 'revenue', 'Revenue',
    );
    if (!dc || !vc) return [];

    const out: Array<{ date: string; value: number }> = [];
    for (const r of rows) {
      const rawDate = r[dc];
      const rawVal = r[vc];
      if (rawDate == null || rawVal == null) continue;
      const d = String(rawDate).slice(0, 10);
      const v = Number(rawVal);
      if (!Number.isFinite(v)) continue;
      out.push({ date: d, value: v });
    }
    out.sort((a, b) => (a.date < b.date ? -1 : 1));
    return out;
  }, [fileDataQuery.data, resultQuery.data, analysisData]);

  useEffect(() => {
    if (listQuery.isError) setError(getErrorMessage(listQuery.error));
  }, [listQuery.isError, listQuery.error]);

  useEffect(() => {
    if (resultQuery.isError) setError(getErrorMessage(resultQuery.error));
  }, [resultQuery.isError, resultQuery.error]);

  useEffect(() => {
    if (resultQuery.data) {
      setSelectedModel(resultQuery.data.ensemble ? '__ensemble__' : firstModelKey(resultQuery.data.results));
      // Reset category when the forecast changes
      setSelectedCategory('');
    }
  }, [resultQuery.data]);

  // When a category is selected, use its per-category results; otherwise use aggregate.
  const activeResults = useMemo(() => {
    const data = resultQuery.data;
    if (!data) return null;
    if (selectedCategory && data.category_forecasts?.[selectedCategory]) {
      return data.category_forecasts[selectedCategory].results;
    }
    return data.results;
  }, [resultQuery.data, selectedCategory]);

  const activeSummary = useMemo(() => {
    const data = resultQuery.data;
    if (!data) return null;
    if (selectedCategory && data.category_forecasts?.[selectedCategory]) {
      return data.category_forecasts[selectedCategory].summary ?? null;
    }
    return data.summary ?? null;
  }, [resultQuery.data, selectedCategory]);

  const activeTestMetrics = useMemo(() => {
    // Category forecasts have no test metrics; use aggregate when showing aggregate
    if (selectedCategory) return {};
    return resultQuery.data?.test_metrics ?? {};
  }, [resultQuery.data, selectedCategory]);

  const activeValues = useMemo(() => {
    if (!resultQuery.data || !activeResults) return [];
    if (selectedModel === '__ensemble__' && resultQuery.data.ensemble && !selectedCategory) {
      return resultQuery.data.ensemble.forecast_values;
    }
    const found = Object.values(activeResults).find(
      (r) => r.model_name === selectedModel,
    );
    return found?.forecast_values ?? [];
  }, [resultQuery.data, activeResults, selectedModel, selectedCategory]);

  const activeModelLabel = useMemo(() => {
    if (selectedModel === '__ensemble__') return 'Ensemble';
    return selectedModel;
  }, [selectedModel]);

  // Handle both old single-column and new multi-column category formats.
  const categoryColumns = useMemo(() => {
    const data = resultQuery.data;
    if (data?.category_columns?.length) return data.category_columns;
    if (data?.category_column) return [data.category_column];
    return [];
  }, [resultQuery.data]);

  const hasCategory = categoryColumns.length > 0;

  const categoryLabel = hasCategory
    ? `Category${categoryColumns.length > 1 ? 'ies' : ''}: ${categoryColumns.join(', ')}`
    : '';

  // Format a composite key for display (replace ||| separator with ·).
  const formatCategoryValue = (cv: string, columnValues?: Record<string, string>): string => {
    if (columnValues) {
      return Object.values(columnValues).join(' · ');
    }
    return cv.replace(/\s*\|\|\|\s*/g, ' · ');
  };

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
          {/* Category selector — shown when category columns were used */}
          {hasCategory && resultQuery.data.category_values && resultQuery.data.category_values.length > 0 && (
            <Box sx={{ mb: 2 }}>
              <TextField
                select
                size="small"
                label={categoryLabel}
                value={selectedCategory}
                onChange={(e) => {
                  const catKey = e.target.value;
                  setSelectedCategory(catKey);
                  // For categories, don't use ensemble - use first model of the category
                  if (catKey && resultQuery.data?.category_forecasts?.[catKey]) {
                    const catResults = resultQuery.data.category_forecasts[catKey].results;
                    setSelectedModel(firstModelKey(catResults));
                  } else {
                    setSelectedModel(resultQuery.data?.ensemble ? '__ensemble__' : firstModelKey(resultQuery.data?.results ?? {}));
                  }
                }}
                sx={{ minWidth: 240 }}
              >
                <MenuItem value="">
                  <em>Aggregate (all categories)</em>
                </MenuItem>
                {resultQuery.data!.category_values.map((cv) => (
                  <MenuItem key={cv} value={cv}>
                    {formatCategoryValue(cv, resultQuery.data!.category_column_values?.[cv])}
                  </MenuItem>
                ))}
              </TextField>
            </Box>
          )}
          <Box sx={{ mb: 3 }}>
            <MetricsCards
              summary={activeSummary}
              bestModel={resultQuery.data.best_model ?? (resultQuery.data.ensemble ? 'ensemble' : null)}
              selectedModel={selectedModel === '__ensemble__' ? null : selectedModel}
              rankings={
                selectedCategory
                  ? Object.values(activeResults ?? {}).map((r) => {
                      const btMetrics = r.backtest_metrics ?? {};
                      const cvAcc = r.metrics.forecast_accuracy;
                      const cvGrade = r.metrics.accuracy_grade != null ? String(r.metrics.accuracy_grade) : null;
                      const btAcc = btMetrics.forecast_accuracy ?? r.metrics.test_forecast_accuracy;
                      const btGradeRaw = btMetrics.accuracy_grade ?? r.metrics.test_accuracy_grade;
                      const btGrade = btGradeRaw != null ? String(btGradeRaw) : null;
                      return {
                        model: r.model_name,
                        mae: r.metrics.test_mae ?? r.metrics.mae ?? null,
                        rmse: r.metrics.test_rmse ?? r.metrics.rmse ?? null,
                        mape: r.metrics.test_mape ?? r.metrics.mape ?? null,
                        r2: r.metrics.test_r2 ?? r.metrics.r2 ?? null,
                        score: r.metrics.score ?? null,
                        forecast_accuracy: btAcc ?? cvAcc ?? null,
                        accuracy_grade: btGrade ?? cvGrade ?? null,
                        cv_forecast_accuracy: cvAcc ?? null,
                        cv_accuracy_grade: cvGrade ?? null,
                        cv_mae: r.metrics.mae ?? null,
                        cv_mape: r.metrics.mape ?? null,
                        backtest_forecast_accuracy: btAcc,
                        backtest_accuracy_grade: btGrade ?? null,
                        backtest_mae: btMetrics.mae ?? r.metrics.test_mae ?? null,
                        backtest_mape: btMetrics.mape ?? r.metrics.test_mape ?? null,
                        name: r.model_name,
                      };
                    })
                  : resultQuery.data.ensemble
                    ? (() => {
                        const ens = resultQuery.data.ensemble;
                        const ensBt = ens.backtest_metrics ?? {};
                        const ensMetrics = ens.metrics ?? {};
                        const ensGradeRaw = ensBt.accuracy_grade ?? ensMetrics.accuracy_grade;
                        const ensGrade = ensGradeRaw != null ? String(ensGradeRaw) : null;
                        return [{
                          model: 'ensemble',
                          mae: ensBt.mae ?? ensMetrics.mae ?? null,
                          rmse: ensBt.rmse ?? ensMetrics.rmse ?? null,
                          mape: ensBt.mape ?? ensMetrics.mape ?? null,
                          r2: ensBt.r2 ?? ensMetrics.r2 ?? null,
                          score: 1,
                          forecast_accuracy: ensBt.forecast_accuracy ?? ensMetrics.forecast_accuracy ?? null,
                          accuracy_grade: ensGrade,
                          cv_forecast_accuracy: ensMetrics.forecast_accuracy ?? null,
                          cv_accuracy_grade: ensMetrics.accuracy_grade != null ? String(ensMetrics.accuracy_grade) : null,
                          backtest_forecast_accuracy: ensBt.forecast_accuracy ?? null,
                          backtest_accuracy_grade: ensBt.accuracy_grade != null ? String(ensBt.accuracy_grade) : null,
                          backtest_mae: ensBt.mae ?? null,
                          backtest_mape: ensBt.mape ?? null,
                          name: 'Ensemble',
                        }];
                      })()
                    : Object.values(activeResults ?? {}).map((r) => {
                      const btMetrics = r.backtest_metrics ?? {};
                      const cvAcc = r.metrics.forecast_accuracy;
                      const cvGrade = r.metrics.accuracy_grade != null ? String(r.metrics.accuracy_grade) : null;
                      const btAcc = btMetrics.forecast_accuracy ?? r.metrics.test_forecast_accuracy;
                      const btGradeRaw = btMetrics.accuracy_grade ?? r.metrics.test_accuracy_grade;
                      const btGrade = btGradeRaw != null ? String(btGradeRaw) : null;
                      return {
                        model: r.model_name,
                        mae: r.metrics.test_mae ?? r.metrics.mae ?? null,
                        rmse: r.metrics.test_rmse ?? r.metrics.rmse ?? null,
                        mape: r.metrics.test_mape ?? r.metrics.mape ?? null,
                        r2: r.metrics.test_r2 ?? r.metrics.r2 ?? null,
                        score: r.metrics.score ?? null,
                        forecast_accuracy: btAcc ?? cvAcc ?? null,
                        accuracy_grade: btGrade ?? cvGrade ?? null,
                        cv_forecast_accuracy: cvAcc ?? null,
                        cv_accuracy_grade: cvGrade ?? null,
                        cv_mae: r.metrics.mae ?? null,
                        cv_mape: r.metrics.mape ?? null,
                        backtest_forecast_accuracy: btAcc,
                        backtest_accuracy_grade: btGrade ?? null,
                        backtest_mae: btMetrics.mae ?? r.metrics.test_mae ?? null,
                        backtest_mape: btMetrics.mape ?? r.metrics.test_mape ?? null,
                        name: r.model_name,
                      };
                    })
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
              <Tab label="Insights" />
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
                    actuals={actuals}
                    showActuals={showActuals}
                    onShowActualsChange={setShowActuals}
                    categoryResults={hasCategory ? activeResults : null}
                  />
                </Stack>
              )}
              {tab === 1 && (
                <ModelComparison
                  rankings={Object.values(activeResults ?? {}).map((r) => {
                    const btMetrics = r.backtest_metrics ?? {};
                    return {
                      model: r.model_name,
                      name: r.model_name,
                      mae: btMetrics.mae ?? r.metrics.test_mae ?? r.metrics.mae ?? null,
                      rmse: btMetrics.rmse ?? r.metrics.test_rmse ?? r.metrics.rmse ?? null,
                      mape: btMetrics.mape ?? r.metrics.test_mape ?? r.metrics.mape ?? null,
                      score: r.metrics.score ?? null,
                      forecast_accuracy: btMetrics.forecast_accuracy ?? r.metrics.test_forecast_accuracy ?? r.metrics.forecast_accuracy ?? null,
                    };
                  })}
                  bestModel={selectedCategory ? firstModelKey(activeResults ?? {}) : resultQuery.data.best_model ?? (resultQuery.data.ensemble ? 'ensemble' : null)}
                />
              )}
              {tab === 2 && resultQuery.data && (
                <ResultsTable
                  values={activeValues}
                  modelName={activeModelLabel}
                  modelOptions={[
                    ...(!selectedCategory && resultQuery.data.ensemble ? [{ value: '__ensemble__', label: 'Ensemble (recommended)' }] : []),
                    ...Object.values(activeResults ?? {}).map((r) => ({ value: r.model_name, label: r.model_name })),
                  ]}
                  selectedModel={selectedModel}
                  onModelChange={setSelectedModel}
                />
              )}
              {tab === 3 && (
                <Grid container spacing={2}>
                  {Object.values(activeResults ?? {}).map((r) => (
                    <Grid key={r.model_name} item xs={12} sm={6} md={4}>
                      <ModelMetricsCard
                        result={r}
                        testMetrics={activeTestMetrics?.[r.model_name] ?? null}
                      />
                    </Grid>
                  ))}
                </Grid>
              )}
              {tab === 4 && (
                <InsightsDetail
                  analysisData={analysisData}
                  externalAnalysis={resultQuery.data.external_factor_analysis}
                />
              )}
            </CardContent>
          </Card>
        </>
      )}
    </PageContainer>
  );
}

function firstModelKey(results: Record<string, ModelResult>): string {
  const firstKey = Object.keys(results)[0];
  return firstKey ?? '';
}

function InsightsDetail({
  analysisData,
  externalAnalysis,
}: {
  analysisData: AnalysisResponse | null;
  externalAnalysis?: ExternalFactorAnalysis | null;
}): ReactNode {
  const insights = analysisData?.data_characteristics?.insights;
  const pdq = analysisData?.data_characteristics?.pdq_recommendation;
  const lagAnalysis = externalAnalysis?.lag_analysis;

  return (
    <Stack spacing={2.5}>
      {/* Data pattern insights */}
      {insights && insights.length > 0 && (
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
            Data pattern insights
          </Typography>
          <Stack spacing={1}>
            {insights.map((ins, i) => (
              <Alert key={i} severity={ins.type === 'warning' ? 'warning' : ins.type === 'success' ? 'success' : 'info'} sx={{ py: 0.5 }}>
                {ins.text}
              </Alert>
            ))}
          </Stack>
        </Box>
      )}

      {/* PDQ recommendation */}
      {pdq && (
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
            Recommended ARIMA parameters
          </Typography>
          <Card variant="outlined" sx={{ p: 1.5 }}>
            <Stack spacing={0.5}>
              <Typography variant="body2">
                Order (p,d,q): <Chip label={`p=${pdq.order.p}`} size="small" sx={{ mx: 0.25 }} />
                <Chip label={`d=${pdq.order.d}`} size="small" color={pdq.order.d > 0 ? 'warning' : 'default'} sx={{ mx: 0.25 }} />
                <Chip label={`q=${pdq.order.q}`} size="small" sx={{ mx: 0.25 }} />
              </Typography>
              {pdq.seasonal_order && (
                <Typography variant="body2">
                  Seasonal (P,D,Q,S):{' '}
                  <Chip label={`P=${pdq.seasonal_order.p}`} size="small" sx={{ mx: 0.25 }} />
                  <Chip label={`D=${pdq.seasonal_order.d}`} size="small" sx={{ mx: 0.25 }} />
                  <Chip label={`Q=${pdq.seasonal_order.q}`} size="small" sx={{ mx: 0.25 }} />
                  <Chip label={`S=${pdq.seasonal_order.s}`} size="small" color="primary" sx={{ mx: 0.25 }} />
                </Typography>
              )}
              {pdq.reason && (
                <Typography variant="caption" color="text.secondary">
                  {pdq.reason}
                </Typography>
              )}
            </Stack>
          </Card>
        </Box>
      )}

      {/* Lag analysis for external factors */}
      {lagAnalysis && Object.keys(lagAnalysis).length > 0 && (
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
            External factor lag analysis
          </Typography>
          <Stack spacing={1}>
            {Object.entries(lagAnalysis).map(([key, lag]: [string, LagAnalysisResult]) => (
              <Alert key={key} severity={lag.correlation && lag.correlation > 0.3 ? 'info' : 'warning'} sx={{ py: 0.5 }}>
                <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                  <Chip label={key} size="small" color="primary" variant="outlined" />
                  <Typography variant="body2">
                    Lag: <strong>{lag.lag}</strong> period{lag.lag !== 1 ? 's' : ''} · Correlation: {lag.correlation?.toFixed(3) ?? 'N/A'}
                    {lag.strength && <Chip label={lag.strength} size="small" color={lag.strength === 'strong' ? 'success' : lag.strength === 'moderate' ? 'info' : 'default'} variant="outlined" sx={{ ml: 0.5, height: 18, fontSize: 10 }} />}
                  </Typography>
                </Stack>
              </Alert>
            ))}
          </Stack>
        </Box>
      )}

      {!insights && !pdq && !lagAnalysis && (
        <Typography variant="body2" color="text.secondary">
          No insights available yet. Run a data analysis on the Upload page to populate data pattern insights and ARIMA recommendations.
        </Typography>
      )}
    </Stack>
  );
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

function ModelMetricsCard({ result, testMetrics }: { result: ModelResult; testMetrics?: { mae: number | null; rmse: number | null; mape: number | null } | null }): ReactNode {
  const m = result.metrics;
  const bt = result.backtest_metrics ?? {};
  const cvAccuracy = m?.forecast_accuracy ?? null;
  const cvGrade = m?.accuracy_grade ?? null;
  const testAccuracy = m?.test_forecast_accuracy ?? null;
  const accuracyTone: 'success' | 'info' | 'warning' | 'error' =
    !cvAccuracy ? 'info'
      : cvAccuracy >= 90 ? 'success'
        : cvAccuracy >= 80 ? 'info'
          : cvAccuracy >= 70 ? 'warning'
            : 'error';
  return (
    <Card>
      <CardContent>
        <Typography variant="overline" color="text.secondary">
          {result.model_name.toUpperCase()}
        </Typography>
        <Stack spacing={1} sx={{ mt: 1 }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
            Cross-validation
          </Typography>
          <MetricRow label="MAE" value={m.mae} />
          <MetricRow label="RMSE" value={m.rmse} />
          <MetricRow label="MAPE" value={m.mape} fmt="pct" />
          <MetricRow label="R²" value={m.r2} />
          {cvAccuracy != null && <MetricRow label="CV accuracy" value={cvAccuracy} fmt="pct" tone={accuracyTone} />}
          {cvGrade != null && <MetricRow label="CV grade" value={cvGrade} fmt="str" />}

          {bt.mae != null && (
            <>
              <Divider sx={{ my: 0.5 }} />
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                Backtest (held-out actuals)
              </Typography>
              <MetricRow label="MAE" value={bt.mae} />
              <MetricRow label="RMSE" value={bt.rmse} />
              {bt.mape != null && <MetricRow label="MAPE" value={bt.mape} fmt="pct" />}
              {bt.r2 != null && <MetricRow label="R²" value={bt.r2} />}
              {bt.forecast_accuracy != null && <MetricRow label="Accuracy" value={bt.forecast_accuracy} fmt="pct" />}
              {bt.accuracy_grade != null && <MetricRow label="Grade" value={bt.accuracy_grade} fmt="str" />}
            </>
          )}

          {testMetrics && testMetrics.mae != null && (
            <>
              <Divider sx={{ my: 0.5 }} />
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                Held-out test (ML only)
              </Typography>
              <MetricRow label="MAE" value={testMetrics.mae} />
              <MetricRow label="RMSE" value={testMetrics.rmse} />
              <MetricRow label="MAPE" value={testMetrics.mape} fmt="pct" />
              {testAccuracy != null && <MetricRow label="Accuracy" value={testAccuracy} fmt="pct" />}
            </>
          )}
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
  tone,
}: {
  label: string;
  value: number | string | undefined | null;
  fmt?: 'num' | 'pct' | 'str';
  tone?: 'success' | 'info' | 'warning' | 'error';
}): ReactNode {
  return (
    <Stack direction="row" justifyContent="space-between" alignItems="center">
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body2" sx={{ fontWeight: 600, color: tone ? `${tone}.main` : undefined }}>
        {value === null || value === undefined || value === '' || (typeof value === 'number' && !Number.isFinite(value))
          ? '—'
          : fmt === 'pct'
            ? `${Number(value).toFixed(1)}%`
            : fmt === 'str'
              ? String(value)
              : Number(value).toFixed(2)}
      </Typography>
    </Stack>
  );
}
