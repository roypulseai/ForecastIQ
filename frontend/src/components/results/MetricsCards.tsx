import type { ReactNode } from 'react';
import { Box, Card, CardContent, Stack, Typography } from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import { alpha, useTheme } from '@mui/material/styles';
import { formatCurrency, formatNumber, formatPct } from '../../utils/format';
import type { ForecastSummary, ModelRanking } from '../../types';

interface MetricsCardsProps {
  summary: ForecastSummary | null;
  bestModel: string | null | undefined;
  rankings: ModelRanking[];
  targetCurrency?: string;
}

interface MetricCardProps {
  label: string;
  value: string;
  helper?: string;
  trend?: 'up' | 'down' | 'flat';
  tone?: 'primary' | 'success' | 'warning' | 'error' | 'info';
  icon?: ReactNode;
}

function MetricCard({ label, value, helper, trend, tone = 'primary', icon }: MetricCardProps): ReactNode {
  const theme = useTheme();
  const color = theme.palette[tone].main;
  const bg = `${alpha(color, 0.08)}`;
  const TrendIcon = trend === 'up' ? TrendingUpIcon : trend === 'down' ? TrendingDownIcon : null;
  const trendColor =
    trend === 'up' ? theme.palette.success.main : trend === 'down' ? theme.palette.error.main : color;

  return (
    <Card>
      <CardContent>
        <Stack direction="row" alignItems="flex-start" justifyContent="space-between" spacing={2}>
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
              width: 40,
              height: 40,
              borderRadius: 1.5,
              backgroundColor: bg,
              color,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {icon ?? (TrendIcon ? <TrendIcon sx={{ color: trendColor }} /> : <Box sx={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: color }} />)}
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
}

export function MetricsCards({
  summary,
  bestModel,
  rankings,
  targetCurrency,
}: MetricsCardsProps): ReactNode {
  const best = rankings.find((r) => r.model === bestModel) ?? rankings[0];
  const upliftTone: 'success' | 'error' | 'primary' =
    !summary || summary.total_uplift === 0
      ? 'primary'
      : summary.total_uplift > 0
        ? 'success'
        : 'error';
  const upliftTrend: 'up' | 'down' | 'flat' =
    !summary || summary.total_uplift === 0
      ? 'flat'
      : summary.total_uplift > 0
        ? 'up'
        : 'down';

  const accuracy = best?.forecast_accuracy ?? null;
  const grade = best?.accuracy_grade ?? null;
  const accuracyTone: 'success' | 'info' | 'warning' | 'error' =
    !accuracy ? 'info'
      : accuracy >= 90 ? 'success'
        : accuracy >= 80 ? 'info'
          : accuracy >= 70 ? 'warning'
            : 'error';
  const accuracyIcon =
    !accuracy ? null
      : accuracy >= 80 ? <CheckCircleIcon />
        : accuracy >= 70 ? <WarningAmberIcon />
          : <ErrorOutlineIcon />;

  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' },
        gap: 2,
      }}
    >
      <MetricCard
        label="Total forecast"
        value={targetCurrency ? formatCurrency(summary?.total_forecast, targetCurrency) : formatNumber(summary?.total_forecast)}
        helper={
          summary
            ? `avg ${formatNumber(summary.avg_daily_forecast, 2)} per period`
            : 'awaiting run'
        }
        tone="primary"
      />
      <MetricCard
        label="Forecast accuracy"
        value={accuracy != null ? `${accuracy.toFixed(0)}%` : '—'}
        helper={grade ? `Grade: ${grade} · ${best?.model ?? ''}` : 'awaiting run'}
        tone={accuracyTone}
        icon={accuracyIcon}
      />
      <MetricCard
        label="Total uplift"
        value={
          summary
            ? `${summary.total_uplift > 0 ? '+' : ''}${formatNumber(summary.total_uplift, 0)}`
            : '—'
        }
        helper={summary ? formatPct(summary.uplift_pct) : '—'}
        trend={upliftTrend}
        tone={upliftTone}
      />
      <MetricCard
        label="Best model"
        value={bestModel ? bestModel.toUpperCase() : '—'}
        helper={
          best
            ? `MAPE ${best.mape !== null && best.mape !== undefined ? `${best.mape.toFixed(1)}%` : '—'} · MAE ${formatNumber(best.mae, 1)}`
            : 'awaiting run'
        }
        tone="success"
      />
    </Box>
  );
}
