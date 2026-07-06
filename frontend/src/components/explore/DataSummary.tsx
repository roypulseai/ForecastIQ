import type { ReactNode } from 'react';
import { Box, Card, CardContent, Stack, Typography } from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import TrendingFlatIcon from '@mui/icons-material/TrendingFlat';
import { formatNumber, formatPercent } from '../../utils/format';
import type { DataCharacteristics } from '../../types';

interface MetricProps {
  label: string;
  value: string;
  helper?: string;
  trend?: 'up' | 'down' | 'flat';
  tone?: 'default' | 'primary' | 'success' | 'warning' | 'error';
}

function MetricCard({
  label,
  value,
  helper,
  trend,
  tone = 'default',
}: MetricProps): ReactNode {
  const colorMap: Record<NonNullable<MetricProps['tone']>, string> = {
    default: 'text.primary',
    primary: 'primary.main',
    success: 'success.main',
    warning: 'warning.main',
    error: 'error.main',
  };
  const bgMap: Record<NonNullable<MetricProps['tone']>, string> = {
    default: 'primary.lighter',
    primary: 'primary.lighter',
    success: 'success.lighter',
    warning: 'warning.lighter',
    error: 'error.lighter',
  };
  const TrendIcon = trend === 'up' ? TrendingUpIcon : trend === 'down' ? TrendingDownIcon : TrendingFlatIcon;
  const trendColor = trend === 'up' ? 'success.main' : trend === 'down' ? 'error.main' : 'text.secondary';

  return (
    <Card>
      <CardContent>
        <Stack spacing={1}>
          <Box
            sx={{
              width: 36,
              height: 36,
              borderRadius: 1.5,
              backgroundColor: bgMap[tone],
              color: colorMap[tone],
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {trend ? <TrendIcon fontSize="small" sx={{ color: trendColor }} /> : <Box sx={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: 'currentColor' }} />}
          </Box>
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500 }}>
            {label}
          </Typography>
          <Typography variant="h4" sx={{ fontWeight: 700, lineHeight: 1.1 }}>
            {value}
          </Typography>
          {helper && (
            <Typography variant="caption" color="text.secondary">
              {helper}
            </Typography>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}

interface DataSummaryProps {
  characteristics: DataCharacteristics;
  dateRange: [string, string] | null;
  dateColumn: string | null;
  valueColumn: string | null;
  totalRows: number;
}

export function DataSummary({
  characteristics,
  dateRange,
  dateColumn,
  valueColumn,
  totalRows,
}: DataSummaryProps): ReactNode {
  const trend: 'up' | 'down' | 'flat' =
    characteristics.trend === 'increasing'
      ? 'up'
      : characteristics.trend === 'decreasing'
        ? 'down'
        : 'flat';

  const trendLabel =
    characteristics.trend === 'increasing'
      ? 'Upward'
      : characteristics.trend === 'decreasing'
        ? 'Downward'
        : 'Flat';

  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: {
          xs: '1fr',
          sm: 'repeat(2, 1fr)',
          md: 'repeat(4, 1fr)',
        },
        gap: 2,
      }}
    >
      <MetricCard
        label="Observations"
        value={formatNumber(totalRows)}
        helper={
          dateRange
            ? `${dateRange[0]} → ${dateRange[1]}`
            : 'date range unavailable'
        }
      />
      <MetricCard
        label="Mean value"
        value={formatNumber(characteristics.mean, 2)}
        helper={`std ${formatNumber(characteristics.std, 2)}`}
        tone="primary"
      />
      <MetricCard
        label="Coefficient of variation"
        value={formatPercent(characteristics.cv, 2)}
        helper={characteristics.cv < 0.1 ? 'low variability' : characteristics.cv < 0.3 ? 'moderate' : 'high'}
        tone={characteristics.cv < 0.1 ? 'success' : characteristics.cv < 0.3 ? 'warning' : 'error'}
      />
      <MetricCard
        label="Trend"
        value={trendLabel}
        helper={`Seasonality: ${characteristics.seasonality}`}
        trend={trend}
        tone={trend === 'up' ? 'success' : trend === 'down' ? 'error' : 'default'}
      />
      <MetricCard
        label="Outliers"
        value={formatPercent(characteristics.outliers_pct, 2)}
        helper="of observations"
        tone={
          characteristics.outliers_pct < 0.05
            ? 'success'
            : characteristics.outliers_pct < 0.1
              ? 'warning'
              : 'error'
        }
      />
      <MetricCard
        label="Missing values"
        value={formatPercent(characteristics.missing_pct, 2)}
        helper="of observations"
        tone={
          characteristics.missing_pct < 0.01
            ? 'success'
            : characteristics.missing_pct < 0.05
              ? 'warning'
              : 'error'
        }
      />
      <MetricCard
        label="Stationarity"
        value={characteristics.stationarity ? 'Stationary' : 'Non-stationary'}
        helper="ADF test result"
        tone={characteristics.stationarity ? 'success' : 'warning'}
      />
      <MetricCard
        label="Columns"
        value={dateColumn && valueColumn ? `${dateColumn} / ${valueColumn}` : '—'}
        helper="date / value"
      />
    </Box>
  );
}
