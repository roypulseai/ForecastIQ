import type { ReactNode } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  LinearProgress,
  Stack,
  Typography,
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import InsightsIcon from '@mui/icons-material/Insights';
import TimelineIcon from '@mui/icons-material/Timeline';
import AssessmentIcon from '@mui/icons-material/Assessment';
import StorageIcon from '@mui/icons-material/Storage';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import { useTheme, alpha } from '@mui/material/styles';
import { PageContainer } from '../components/layout/PageContainer';
import { useFiles } from '../hooks/useFiles';
import { useForecastList } from '../hooks/useForecast';
import { useForecastResult } from '../hooks/useForecastResults';
import { useStore } from '../store/appStore';
import { FILE_TYPE_LABELS, type FileType } from '../types';
import { formatDate, formatNumber, formatPercent } from '../utils/format';

interface QuickAction {
  to: string;
  title: string;
  description: string;
  icon: ReactNode;
  cta: string;
  ready: boolean;
}

export function Dashboard(): ReactNode {
  const theme = useTheme();
  const navigate = useNavigate();
  const uploadedFiles = useStore((s) => s.uploadedFiles);
  const analysisData = useStore((s) => s.analysisData);
  const currentForecastId = useStore((s) => s.currentForecastId);
  const forecasts = useStore((s) => s.forecasts);

  const filesQuery = useFiles();
  const forecastsQuery = useForecastList();
  const resultQuery = useForecastResult(currentForecastId);

  const salesFile = uploadedFiles.find((f) => f.type === 'sales');
  const hasSales = Boolean(salesFile);
  const hasAnalysis = Boolean(analysisData);
  const hasForecast = Boolean(currentForecastId) && Boolean(resultQuery.data);

  const filesByType = uploadedFiles.reduce<Record<string, number>>((acc, f) => {
    acc[f.type] = (acc[f.type] ?? 0) + 1;
    return acc;
  }, {});

  const quickActions: QuickAction[] = [
    {
      to: '/upload',
      title: 'Upload data',
      description: hasSales
        ? `${filesByType.sales ?? 0} business metrics file${filesByType.sales === 1 ? '' : 's'} loaded`
        : 'Start by uploading your business metrics CSV',
      icon: <CloudUploadIcon />,
      cta: hasSales ? 'Manage files' : 'Upload data',
      ready: true,
    },
    {
      to: '/explore',
      title: 'Explore your data',
      description: hasAnalysis
        ? 'Visualize trends, seasonality, and outliers'
        : 'Upload + analyze business data first',
      icon: <InsightsIcon />,
      cta: hasAnalysis ? 'Open explorer' : 'Locked',
      ready: hasAnalysis,
    },
    {
      to: '/forecast',
      title: 'Configure forecast',
      description: hasAnalysis
        ? 'Choose models, horizon, and external factors'
        : 'Analyze data before configuring',
      icon: <TimelineIcon />,
      cta: hasAnalysis ? 'Configure' : 'Locked',
      ready: hasAnalysis,
    },
    {
      to: '/results',
      title: 'View results',
      description: hasForecast
        ? 'Latest run complete and ready to export'
        : 'Run a forecast to see results here',
      icon: <AssessmentIcon />,
      cta: hasForecast ? 'View results' : 'Locked',
      ready: hasForecast,
    },
  ];

  return (
    <PageContainer
      title="Dashboard"
      subtitle="End-to-end time series forecasting. Upload data, explore patterns, run models, and export results."
    >
      <Grid container spacing={2} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            label="Files loaded"
            value={formatNumber(uploadedFiles.length)}
            helper={`${Object.keys(filesByType).length} unique types`}
            tone="primary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            label="Observations"
            value={formatNumber(analysisData?.data_characteristics.length ?? 0)}
            helper={
              hasAnalysis
                ? `mean ${formatNumber(analysisData?.data_characteristics.mean, 1)}`
                : 'no analysis yet'
            }
            tone="info"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            label="Forecasts"
            value={formatNumber(forecastsQuery.data?.total ?? forecasts.length)}
            helper={forecastsQuery.data ? 'all-time' : 'loading'}
            tone="secondary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            label="Status"
            value={hasForecast ? 'Ready' : hasAnalysis ? 'Configured' : hasSales ? 'Loaded' : 'New'}
            helper={
              hasForecast
                ? 'Latest forecast available'
                : hasAnalysis
                  ? 'Run a forecast to continue'
                  : hasSales
                    ? 'Explore or run a forecast'
                    : 'Upload business data to begin'
            }
            tone={hasForecast ? 'success' : hasAnalysis ? 'primary' : 'warning'}
          />
        </Grid>
      </Grid>

      <Card sx={{ mb: 4, background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.08)} 0%, ${alpha(theme.palette.secondary.main, 0.06)} 100%)` }}>
        <CardContent sx={{ p: 4 }}>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={3} alignItems="center">
            <Box
              sx={{
                width: 64,
                height: 64,
                borderRadius: 2,
                background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
                color: 'common.white',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <ShowChartIcon sx={{ fontSize: 32 }} />
            </Box>
            <Box sx={{ flex: 1 }}>
              <Typography variant="h4" gutterBottom>
                {hasForecast
                  ? 'Latest forecast is ready'
                  : hasAnalysis
                    ? 'Ready to run a forecast'
                    : hasSales
                      ? 'Sales data loaded — explore or forecast'
                      : 'Welcome to ForecastIQ'}
              </Typography>
              <Typography variant="body1" color="text.secondary">
                {hasForecast
                  ? `Last run completed on ${formatDate(resultQuery.data?.created_at, true)}. Open the results page to review and export.`
                  : hasAnalysis
                    ? `${formatNumber(analysisData?.data_characteristics.length ?? 0)} observations analyzed. Choose models and run the forecast.`
                    : hasSales
                      ? 'Inspect patterns in the Explore page or jump to the Forecast page to configure a run.'
                      : 'Get started by uploading a business metrics CSV. You can add other data sources (media, holidays, etc.) on the same page.'}
              </Typography>
            </Box>
            <Stack direction="row" spacing={1.5}>
              {!hasSales && (
                <Button
                  variant="contained"
                  size="large"
                  endIcon={<ArrowForwardIcon />}
                  onClick={() => navigate('/upload')}
                >
                  Upload data
                </Button>
              )}
              {hasSales && !hasAnalysis && (
                <Button
                  variant="contained"
                  size="large"
                  endIcon={<ArrowForwardIcon />}
                  onClick={() => navigate('/upload')}
                >
                  Analyze
                </Button>
              )}
              {hasAnalysis && !hasForecast && (
                <Button
                  variant="contained"
                  size="large"
                  endIcon={<ArrowForwardIcon />}
                  onClick={() => navigate('/forecast')}
                >
                  Configure forecast
                </Button>
              )}
              {hasForecast && (
                <Button
                  variant="contained"
                  size="large"
                  endIcon={<ArrowForwardIcon />}
                  onClick={() => navigate('/results')}
                >
                  View results
                </Button>
              )}
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      <Typography variant="h4" sx={{ mb: 2 }}>
        Workflow
      </Typography>
      <Grid container spacing={2} sx={{ mb: 4 }}>
        {quickActions.map((action) => (
          <Grid key={action.to} item xs={12} sm={6} md={3}>
            <Card
              component={RouterLink}
              to={action.to}
              sx={{
                textDecoration: 'none',
                height: '100%',
                display: 'block',
                transition: 'all 200ms ease',
                opacity: action.ready ? 1 : 0.6,
                '&:hover': action.ready
                  ? {
                      transform: 'translateY(-2px)',
                      boxShadow: '0 4px 16px rgba(0, 0, 0, 0.08)',
                    }
                  : undefined,
              }}
            >
              <CardContent>
                <Stack spacing={2}>
                  <Box
                    sx={{
                      width: 44,
                      height: 44,
                      borderRadius: 1.5,
                      backgroundColor: action.ready ? 'primary.lighter' : 'background.subtle',
                      color: action.ready ? 'primary.main' : 'text.disabled',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    {action.icon}
                  </Box>
                  <Box>
                    <Typography variant="h5">{action.title}</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, minHeight: 40 }}>
                      {action.description}
                    </Typography>
                  </Box>
                  <Stack direction="row" alignItems="center" justifyContent="space-between">
                    <Chip
                      label={action.ready ? 'Ready' : 'Locked'}
                      size="small"
                      color={action.ready ? 'success' : 'default'}
                      variant={action.ready ? 'filled' : 'outlined'}
                    />
                    <ArrowForwardIcon
                      fontSize="small"
                      sx={{ color: action.ready ? 'primary.main' : 'text.disabled' }}
                    />
                  </Stack>
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {uploadedFiles.length > 0 && (
        <Card sx={{ mb: 4 }}>
          <CardContent>
            <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 2 }}>
              <Box>
                <Typography variant="h5">Loaded data</Typography>
                <Typography variant="body2" color="text.secondary">
                  {uploadedFiles.length} file{uploadedFiles.length === 1 ? '' : 's'} across{' '}
                  {Object.keys(filesByType).length} type
                  {Object.keys(filesByType).length === 1 ? '' : 's'}
                </Typography>
              </Box>
              <Button size="small" onClick={() => navigate('/upload')}>
                Manage
              </Button>
            </Stack>
            <Grid container spacing={1.5}>
              {Object.entries(filesByType).map(([type, count]) => (
                <Grid key={type} item xs={6} sm={4} md={3}>
                  <Box
                    sx={{
                      p: 2,
                      borderRadius: 1.5,
                      border: '1px solid',
                      borderColor: 'divider',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 1.5,
                    }}
                  >
                    <Box
                      sx={{
                        width: 36,
                        height: 36,
                        borderRadius: 1.5,
                        backgroundColor: 'primary.lighter',
                        color: 'primary.main',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <StorageIcon fontSize="small" />
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        {FILE_TYPE_LABELS[type as FileType] ?? type}
                      </Typography>
                      <Typography variant="body1" sx={{ fontWeight: 600 }}>
                        {count} file{count === 1 ? '' : 's'}
                      </Typography>
                    </Box>
                  </Box>
                </Grid>
              ))}
            </Grid>
          </CardContent>
        </Card>
      )}

      {forecasts.length > 0 && (
        <Card>
          <CardContent>
            <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 2 }}>
              <Typography variant="h5">Recent forecasts</Typography>
              <Button size="small" onClick={() => navigate('/results')}>
                View all
              </Button>
            </Stack>
            <Stack divider={<Box sx={{ borderBottom: '1px solid', borderBottomColor: 'divider' }} />}>
              {forecasts.slice(0, 5).map((f) => (
                <Box
                  key={f.forecast_id}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    py: 1.5,
                    cursor: 'pointer',
                  }}
                  onClick={() => {
                    useStore.getState().setCurrentForecastId(f.forecast_id);
                    navigate('/results');
                  }}
                >
                  <Box>
                    <Typography variant="subtitle2">{f.name}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {formatDate(f.created_at, true)} · horizon {f.horizon} · {f.models.length} model
                      {f.models.length === 1 ? '' : 's'}
                    </Typography>
                  </Box>
                  {f.best_model && (
                    <Chip label={f.best_model} size="small" color="primary" variant="outlined" />
                  )}
                </Box>
              ))}
            </Stack>
          </CardContent>
        </Card>
      )}

      {filesQuery.isLoading && <LinearProgress sx={{ mt: 2 }} />}
      {filesQuery.isError && (
        <Typography variant="body2" color="error" sx={{ mt: 2 }}>
          Could not load files from the API. Make sure the backend is running.
        </Typography>
      )}
      {!hasSales && !filesQuery.isLoading && (
        <Card sx={{ mt: 4, p: 3, border: '1px dashed', borderColor: 'divider' }}>
          <Stack direction="row" spacing={2} alignItems="center">
            <CircularProgress size={20} />
            <Typography variant="body2" color="text.secondary">
              No business data loaded yet. Head to the{' '}
              <Box component={RouterLink} to="/upload" sx={{ color: 'primary.main', fontWeight: 600, textDecoration: 'none' }}>
                Data
              </Box>{' '}
              page to upload a CSV (or download a template).
            </Typography>
          </Stack>
        </Card>
      )}
      {analysisData && (
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 2 }}>
          Latest analysis: CV {formatPercent(analysisData.data_characteristics.cv, 2)} ·{' '}
          {analysisData.data_characteristics.trend} trend ·{' '}
          {analysisData.data_characteristics.seasonality} seasonality
        </Typography>
      )}
    </PageContainer>
  );
}

interface KpiCardProps {
  label: string;
  value: string;
  helper?: string;
  tone: 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'info';
}

function KpiCard({ label, value, helper, tone }: KpiCardProps): ReactNode {
  const theme = useTheme();
  const color = theme.palette[tone].main;
  return (
    <Card>
      <CardContent>
        <Stack direction="row" alignItems="flex-start" justifyContent="space-between">
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
              {label}
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 700, mt: 0.5, lineHeight: 1.1 }}>
              {value}
            </Typography>
            {helper && (
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                {helper}
              </Typography>
            )}
          </Box>
          <Box
            sx={{
              width: 8,
              height: 36,
              borderRadius: 1,
              backgroundColor: color,
            }}
          />
        </Stack>
      </CardContent>
    </Card>
  );
}
