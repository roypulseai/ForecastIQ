import { useMemo, type ReactNode } from 'react';
import { Box, Card, CardContent, MenuItem, Stack, TextField, Typography } from '@mui/material';
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { alpha, useTheme } from '@mui/material/styles';
import type { ForecastDetail, ForecastValue, ModelResult } from '../../types';
import { formatNumber, formatShortDate } from '../../utils/format';

interface ForecastChartProps {
  detail: ForecastDetail;
  selectedModel: string;
  onModelChange: (model: string) => void;
  showBaseline: boolean;
  onShowBaselineChange: (show: boolean) => void;
}

interface ChartPoint {
  date: string;
  forecast: number;
  lower: number;
  upper: number;
  baseline: number | null;
}

function valuesToPoints(values: ForecastValue[]): ChartPoint[] {
  return values.map((v) => ({
    date: v.date,
    forecast: v.forecast,
    lower: v.lower_ci,
    upper: v.upper_ci,
    baseline: v.baseline ?? null,
  }));
}

function modelOptions(detail: ForecastDetail): Array<{ value: string; label: string }> {
  const opts: Array<{ value: string; label: string }> = [];
  if (detail.ensemble) {
    opts.push({ value: '__ensemble__', label: 'Ensemble (recommended)' });
  }
  for (const key of Object.keys(detail.results)) {
    const r: ModelResult = detail.results[key];
    opts.push({ value: r.model_name, label: r.model_name });
  }
  return opts;
}

export function ForecastChart({
  detail,
  selectedModel,
  onModelChange,
  showBaseline,
}: ForecastChartProps): ReactNode {
  const theme = useTheme();

  const isEnsemble = selectedModel === '__ensemble__';
  const data: ChartPoint[] = useMemo(() => {
    if (isEnsemble && detail.ensemble) {
      return valuesToPoints(detail.ensemble.forecast_values);
    }
    const found = Object.values(detail.results).find(
      (r) => r.model_name === selectedModel,
    );
    if (!found) return [];
    return valuesToPoints(found.forecast_values);
  }, [detail, isEnsemble, selectedModel]);

  const baselineData = useMemo(() => {
    if (!showBaseline) return null;
    if (isEnsemble && detail.ensemble?.baseline_values) {
      return valuesToPoints(detail.ensemble.baseline_values);
    }
    const found = Object.values(detail.results).find(
      (r) => r.model_name === selectedModel,
    );
    if (found?.baseline_values) return valuesToPoints(found.baseline_values);
    return null;
  }, [detail, isEnsemble, selectedModel, showBaseline]);

  const options = modelOptions(detail);

  return (
    <Card>
      <CardContent>
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          spacing={2}
          alignItems={{ xs: 'flex-start', sm: 'center' }}
          justifyContent="space-between"
          sx={{ mb: 2 }}
        >
          <Box>
            <Typography variant="h5">Forecast with confidence intervals</Typography>
            <Typography variant="body2" color="text.secondary">
              {detail.name} · horizon {detail.request.horizon} · frequency {detail.request.frequency}
            </Typography>
          </Box>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <TextField
              select
              size="small"
              label="Model"
              value={selectedModel}
              onChange={(e) => onModelChange(e.target.value)}
              sx={{ minWidth: 220 }}
              inputProps={{ 'aria-label': 'Select forecast model' }}
            >
              {options.map((o) => (
                <MenuItem key={o.value} value={o.value}>
                  {o.label}
                </MenuItem>
              ))}
            </TextField>
          </Stack>
        </Stack>
        <Box sx={{ width: '100%', height: 460 }}>
          <ResponsiveContainer>
            <ComposedChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
              <defs>
                <linearGradient id="ciFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={theme.palette.primary.main} stopOpacity={0.18} />
                  <stop offset="100%" stopColor={theme.palette.primary.main} stopOpacity={0.04} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis
                dataKey="date"
                tickFormatter={(d: string) => formatShortDate(d)}
                tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                stroke={theme.palette.divider}
                minTickGap={32}
              />
              <YAxis
                tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                stroke={theme.palette.divider}
                tickFormatter={(v: number) => formatNumber(v)}
              />
              <Tooltip
                contentStyle={{
                  borderRadius: 8,
                  border: `1px solid ${theme.palette.divider}`,
                  fontSize: 12,
                }}
                labelFormatter={(label: string) => formatShortDate(label)}
                formatter={(value: number, name: string) => [formatNumber(value, 2), name]}
              />
              <Legend />
              <Area
                type="monotone"
                dataKey="upper"
                stroke="transparent"
                fill="url(#ciFill)"
                name="Upper CI"
                legendType="none"
              />
              <Area
                type="monotone"
                dataKey="lower"
                stroke="transparent"
                fill={theme.palette.background.paper}
                name="Lower CI"
                legendType="none"
              />
              <Line
                type="monotone"
                dataKey="forecast"
                stroke={theme.palette.primary.main}
                strokeWidth={2.5}
                dot={false}
                name="Forecast"
              />
              {baselineData && (
                <Line
                  type="monotone"
                  dataKey="baseline"
                  stroke={theme.palette.text.secondary}
                  strokeWidth={1.5}
                  strokeDasharray="4 4"
                  dot={false}
                  name="Baseline (no uplift)"
                  connectNulls
                />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </Box>
        {showBaseline && !baselineData && (
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            Note: baseline not available for this model.
          </Typography>
        )}
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
          Shaded area: 95% confidence interval · {alpha(theme.palette.primary.main, 0.18)} →{' '}
          {alpha(theme.palette.primary.main, 0.04)}
        </Typography>
      </CardContent>
    </Card>
  );
}
