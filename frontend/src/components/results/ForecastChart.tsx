import { useMemo, type ReactNode } from 'react';
import { Box, Card, CardContent, MenuItem, Stack, Switch, FormControlLabel, TextField, Typography } from '@mui/material';
import {
  Area,
  Brush,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useTheme } from '@mui/material/styles';
import type { ForecastDetail, ForecastValue, ModelResult } from '../../types';
import { formatNumber, formatShortDate } from '../../utils/format';

export interface ActualPoint {
  date: string;
  value: number;
}

interface ForecastChartProps {
  detail: ForecastDetail;
  selectedModel: string;
  onModelChange: (model: string) => void;
  showBaseline: boolean;
  onShowBaselineChange: (show: boolean) => void;
  actuals?: ActualPoint[];
  showActuals?: boolean;
  onShowActualsChange?: (show: boolean) => void;
  categoryResults?: Record<string, ModelResult> | null;
}

interface ChartPoint {
  date: string;
  forecast: number | null;
  lower: number | null;
  upper: number | null;
  baseline: number | null;
  actual: number | null;
}

function modelOptions(detail: ForecastDetail, categoryResults?: Record<string, ModelResult> | null): Array<{ value: string; label: string }> {
  const opts: Array<{ value: string; label: string }> = [];
  if (detail.ensemble && !categoryResults) {
    opts.push({ value: '__ensemble__', label: 'Ensemble (recommended)' });
  }
  const resultsSource = categoryResults ?? detail.results;
  for (const key of Object.keys(resultsSource)) {
    const r: ModelResult = resultsSource[key];
    opts.push({ value: key, label: r.model_name });
  }
  return opts;
}

function normalizeDate(d: unknown): string {
  if (d == null) return '';
  const s = String(d);
  return s.slice(0, 10);
}

export function ForecastChart({
  detail,
  selectedModel,
  onModelChange,
  showBaseline,
  actuals = [],
  showActuals = true,
  onShowActualsChange,
  categoryResults,
}: ForecastChartProps): ReactNode {
  const theme = useTheme();
  const isEnsemble = selectedModel === '__ensemble__';

  const resultsSource = categoryResults ?? detail.results;

  const getModelData = <T,>(selector: (r: ModelResult) => T | undefined | null, ensembleSelector?: (e: NonNullable<ForecastDetail['ensemble']>) => T | undefined | null): T | undefined | null => {
    if (isEnsemble && !categoryResults && detail.ensemble) {
      return ensembleSelector?.(detail.ensemble);
    }
    if (selectedModel && resultsSource[selectedModel]) {
      return selector(resultsSource[selectedModel]);
    }
    return undefined;
  };

  const forecastValues: ForecastValue[] = getModelData(
    (r) => r.forecast_values ?? [],
    (e) => e.forecast_values ?? [],
  ) ?? [];

  const baselineValues: ForecastValue[] | undefined = getModelData(
    (r) => r.baseline_values ?? undefined,
    (e) => e.baseline_values ?? undefined,
  ) ?? undefined;

  const backtestValues: ForecastValue[] | undefined = getModelData(
    (r) => r.backtest_forecast_values ?? undefined,
    (e) => e.backtest_forecast_values ?? undefined,
  ) ?? undefined;

  const data: ChartPoint[] = useMemo(() => {
    const byDate = new Map<string, ChartPoint>();

    if (showActuals) {
      for (const a of actuals) {
        const date = normalizeDate(a.date);
        if (!date) continue;
        byDate.set(date, {
          date,
          forecast: null,
          lower: null,
          upper: null,
          baseline: null,
          actual: a.value,
        });
      }
    }

    for (const v of forecastValues) {
      const date = normalizeDate(v.date);
      if (!date) continue;
      const existing = byDate.get(date);
      byDate.set(date, {
        date,
        forecast: v.forecast,
        lower: v.lower_ci,
        upper: v.upper_ci,
        baseline: existing?.baseline ?? null,
        actual: existing?.actual ?? null,
      });
    }

    if (showBaseline && baselineValues) {
      for (const v of baselineValues) {
        const date = normalizeDate(v.date);
        if (!date) continue;
        const existing = byDate.get(date);
        if (existing) {
          existing.baseline = v.forecast;
        } else {
          byDate.set(date, {
            date,
            forecast: null,
            lower: null,
            upper: null,
            baseline: v.forecast,
            actual: null,
          });
        }
      }
    }

    if (backtestValues) {
      for (const v of backtestValues) {
        const date = normalizeDate(v.date);
        if (!date) continue;
        const existing = byDate.get(date);
        if (existing) {
          existing.forecast = v.forecast;
          existing.lower = v.lower_ci;
          existing.upper = v.upper_ci;
        } else {
          byDate.set(date, {
            date,
            forecast: v.forecast,
            lower: v.lower_ci,
            upper: v.upper_ci,
            baseline: null,
            actual: null,
          });
        }
      }
    }

    return Array.from(byDate.values()).sort((a, b) => (a.date < b.date ? -1 : 1));
  }, [actuals, showActuals, showBaseline, forecastValues, baselineValues, backtestValues]);

  const boundary = detail.backtest_end_date
    ? normalizeDate(detail.backtest_end_date)
    : (actuals.length > 0 ? normalizeDate(actuals[actuals.length - 1].date) : null);

  // Use backend-provided backtest dates when available (most reliable).
  // Fall back to computing from actuals only if backend didn't provide dates.
  const hasBacktest = detail.auto_backtest
    || (detail.request.backtest_overlap != null && detail.request.backtest_overlap > 0)
    || (detail.backtest_start_date != null && detail.backtest_end_date != null);
  const backtestStartDate = detail.backtest_start_date
    ? normalizeDate(detail.backtest_start_date)
    : (hasBacktest && boundary ? (() => {
        // Fallback: find the date from the chart's unique dates
        const uniqueDates = data.map(d => d.date).filter((d): d is string => !!d);
        const backtestN = detail.backtest_overlap_n || detail.request.backtest_overlap || 0;
        if (backtestN > 0 && uniqueDates.length >= backtestN) {
          return uniqueDates[uniqueDates.length - backtestN];
        }
        return null;
      })() : null);

  const options = modelOptions(detail, categoryResults);

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
          <Stack direction="row" spacing={1.5} alignItems="center" flexWrap="wrap">
            <FormControlLabel
              control={
                <Switch
                  size="small"
                  checked={showActuals}
                  onChange={(_, c) => onShowActualsChange?.(c)}
                />
              }
              label="Actuals"
            />
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
                formatter={(value, name) => {
                  const v = typeof value === 'number' ? value : Number(value);
                  return Number.isFinite(v) ? [formatNumber(v, 2), name] : ['—', name];
                }}
              />
              <Legend />
              {backtestStartDate && boundary && (
                <ReferenceArea
                  x1={backtestStartDate}
                  x2={boundary}
                  fill={theme.palette.warning.light}
                  fillOpacity={0.08}
                  stroke="none"
                  label={{ value: detail.auto_backtest ? 'Auto backtest zone' : 'Backtest zone', position: 'insideTopLeft', fontSize: 10, fill: theme.palette.warning.main }}
                />
              )}
              {boundary && (
                <ReferenceLine
                  x={boundary}
                  stroke={theme.palette.text.disabled}
                  strokeDasharray="3 3"
                  label={{ value: 'Backtest end / Forecast start', position: 'top', fontSize: 10, fill: theme.palette.text.secondary }}
                />
              )}
              <Area
                type="monotone"
                dataKey="upper"
                stroke="transparent"
                fill="url(#ciFill)"
                name="Upper CI"
                legendType="none"
                connectNulls
              />
              <Area
                type="monotone"
                dataKey="lower"
                stroke="transparent"
                fill={theme.palette.background.paper}
                name="Lower CI"
                legendType="none"
                connectNulls
              />
              {showActuals && (
                <Line
                  type="monotone"
                  dataKey="actual"
                  stroke={theme.palette.text.primary}
                  strokeWidth={2}
                  dot={false}
                  name="Actuals"
                  connectNulls
                />
              )}
              <Line
                type="monotone"
                dataKey="forecast"
                stroke={theme.palette.primary.main}
                strokeWidth={2.5}
                dot={false}
                name="Forecast"
                connectNulls
              />
              {showBaseline && (
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
              <Brush
                dataKey="date"
                height={30}
                stroke={theme.palette.text.secondary}
                fill={theme.palette.background.paper}
                travellerWidth={10}
                gap={1}
                tickFormatter={(d: string) => formatShortDate(d)}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </Box>
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
          Black line: historical actuals · Blue line: forecast (backtest in yellow zone, future beyond dashed line) · Shaded area: 95% confidence interval · Yellow zone: model accuracy comparison (actual vs backtest forecast).
        </Typography>
      </CardContent>
    </Card>
  );
}
