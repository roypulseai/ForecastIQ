import type { ReactNode } from 'react';
import { Box, Card, CardContent, Stack, Tooltip, Typography } from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { alpha, useTheme } from '@mui/material/styles';
import { formatCurrency, formatNumber, formatPct } from '../../utils/format';
import type { ForecastSummary, ModelRanking } from '../../types';

interface MetricsCardsProps {
  summary: ForecastSummary | null;
  bestModel: string | null | undefined;
  selectedModel?: string | null;
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
  selectedModel,
  rankings,
  targetCurrency,
}: MetricsCardsProps): ReactNode {
  // Pick the right ranking entry: selected model, or best model, or first
  const activeModelKey = selectedModel ?? bestModel;
  const activeRank: ModelRanking | undefined = activeModelKey
    ? rankings.find((r) => r.model === activeModelKey) ?? rankings[0]
    : rankings[0];
  // For the "Best model" card, always point at the actual best model (not the selected one)
  const bestRank: ModelRanking | undefined = bestModel
    ? rankings.find((r) => r.model === bestModel) ?? rankings[0]
    : rankings[0];
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

  // --- Accuracy: use selected model (or best) ---
  const activeBtAcc = activeRank?.backtest_forecast_accuracy ?? activeRank?.forecast_accuracy ?? null;
  const activeBtGrade = activeRank?.backtest_accuracy_grade ?? activeRank?.accuracy_grade ?? null;
  const activeCvAcc = activeRank?.cv_forecast_accuracy ?? null;
  const activeCvGrade = activeRank?.cv_accuracy_grade ?? null;
  const hasBacktest = activeRank?.backtest_mae != null;
  const primaryAccuracy = hasBacktest ? activeBtAcc : (activeCvAcc ?? activeBtAcc);
  const primaryGrade = hasBacktest ? activeBtGrade : (activeCvGrade ?? activeBtGrade);
  const primaryTone: 'success' | 'info' | 'warning' | 'error' =
    !primaryAccuracy ? 'info'
      : primaryAccuracy >= 90 ? 'success'
        : primaryAccuracy >= 80 ? 'info'
          : primaryAccuracy >= 70 ? 'warning'
            : 'error';
  const primaryIcon =
    !primaryAccuracy ? null
      : primaryAccuracy >= 80 ? <CheckCircleIcon />
        : primaryAccuracy >= 70 ? <WarningAmberIcon />
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
        label={activeModelKey && activeModelKey !== bestModel ? `${activeRank?.name ?? activeModelKey}` : 'Forecast accuracy'}
        value={primaryAccuracy != null ? `${primaryAccuracy.toFixed(0)}%` : '—'}
        helper={
          (primaryGrade ? `Grade: ${primaryGrade}` : '') + (
            hasBacktest && activeRank?.backtest_mape != null
              ? ` · Backtest MAPE ${activeRank.backtest_mape.toFixed(1)}%`
              : activeRank?.mape != null
                ? ` · CV MAPE ${activeRank.mape.toFixed(1)}%`
                : ''
          )
        }
        tone={primaryTone}
        icon={
          <Stack direction="row" spacing={0.5} alignItems="center">
            {primaryIcon}
            <Tooltip title={`${hasBacktest ? 'Backtest: model re-forecasts on held-out historical data' : 'Cross-validation: average across multiple train/test splits'}`}>
              <InfoOutlinedIcon sx={{ fontSize: 14, color: 'text.disabled' }} />
            </Tooltip>
          </Stack>
        }
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
          bestRank
            ? `MAE ${formatNumber(bestRank.backtest_mae ?? bestRank.mae, 1)}`
            : '—'
        }
        tone="success"
      />
    </Box>
  );
}
