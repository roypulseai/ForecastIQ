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
  /** When a category is selected, pass the category-specific results here so the chart shows them instead of aggregate results. */
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

function valuesToPoints(values: ForecastValue[]): ChartPoint[] {
  return values.map((v) => ({
    date: v.date,
    forecast: v.forecast,
    lower: v.lower_ci,
    upper: v.upper_ci,
    baseline: v.baseline ?? null,
    actual: null,
  }));
}

function actualsToPoints(actuals: ActualPoint[]): ChartPoint[] {
  return actuals.map((a) => ({
    date: a.date,
    forecast: null,
    lower: null,
    upper: null,
    baseline: null,
    actual: a.value,
  }));
}

function modelOptions(detail: ForecastDetail, categoryResults?: Record<string, ModelResult> | null): Array<{ value: string; label: string }> {
  const opts: Array<{ value: string; label: string }> = [];
  // Only show ensemble option when NOT in category mode
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

  // Build the merged series: actuals first, forecast points, then baseline.
  // We merge on date so a single ComposedChart can show them together.
  const data: ChartPoint[] = useMemo(() => {
    const byDate = new Map<string, ChartPoint>();

    // Debug: log actuals range
    if (actuals.length > 0) {
      console.log('[ForecastChart] Actuals range:', actuals[0].date, 'to', actuals[actuals.length - 1].date, 'count:', actuals.length);
    }

    if (showActuals) {
      for (const p of actualsToPoints(actuals)) {
        byDate.set(p.date, p);
      }
    }
    // Use category results if a category is selected, otherwise use aggregate results.
    const resultsSource = categoryResults ?? detail.results;
    const forecastValues = (() => {
      if (isEnsemble && !categoryResults && detail.ensemble) {
        return detail.ensemble.forecast_values ?? [];
      }
      if (selectedModel && resultsSource[selectedModel]) {
        return resultsSource[selectedModel].forecast_values ?? [];
      }
      return [];
    })();

    // Debug: log selected model info
    console.log('[ForecastChart] selectedModel:', selectedModel, 'isEnsemble:', isEnsemble);
    console.log('[ForecastChart] resultsSource keys:', Object.keys(resultsSource));
    console.log('[ForecastChart] forecastValues count:', forecastValues.length);
    if (forecastValues.length > 0) {
      console.log('[ForecastChart] Forecast range:', forecastValues[0].date, 'to', forecastValues[forecastValues.length - 1].date);
    }

    for (const p of valuesToPoints(forecastValues)) {
      const existing = byDate.get(p.date);
      if (existing) {
        byDate.set(p.date, { ...existing, ...p, actual: existing.actual });
      } else {
        byDate.set(p.date, p);
      }
    }
    // Merge baseline into the same data array (avoids Recharts issues with
    // separate `data` props on child elements).
    if (showBaseline) {
      const baselineValues = (() => {
        if (isEnsemble && !categoryResults && detail.ensemble) {
          return detail.ensemble.baseline_values;
        }
        if (selectedModel) {
          return resultsSource[selectedModel]?.baseline_values;
        }
        return undefined;
      })();
      if (baselineValues) {
        for (const v of baselineValues) {
          const existing = byDate.get(v.date);
          if (existing) {
            byDate.set(v.date, { ...existing, baseline: v.forecast });
          } else {
            byDate.set(v.date, {
              date: v.date,
              forecast: null,
              lower: null,
              upper: null,
              baseline: v.forecast,
              actual: null,
            });
          }
        }
      }
    }
    // Merge backtest forecast into the `forecast` field so the blue "Forecast"
    // line extends through the backtest zone, allowing visual comparison with
    // actuals.
    const backtestValues = (() => {
      if (isEnsemble && !categoryResults && detail.ensemble) {
        return detail.ensemble.backtest_forecast_values;
      }
      if (selectedModel) {
        return resultsSource[selectedModel]?.backtest_forecast_values;
      }
      return undefined;
    })();
    if (backtestValues) {
      for (const v of backtestValues) {
        const existing = byDate.get(v.date);
        if (existing) {
          byDate.set(v.date, { ...existing, forecast: v.forecast, lower: v.lower_ci, upper: v.upper_ci, actual: existing.actual });
        } else {
          byDate.set(v.date, {
            date: v.date,
            forecast: v.forecast,
            lower: v.lower_ci,
            upper: v.upper_ci,
            baseline: null,
            actual: null,
          });
        }
      }
    }
    const sortedData = Array.from(byDate.values()).sort((a, b) => (a.date < b.date ? -1 : 1));
    console.log('[ForecastChart] Final data count:', sortedData.length);
    if (sortedData.length > 0) {
      console.log('[ForecastChart] Data date range:', sortedData[0].date, 'to', sortedData[sortedData.length - 1].date);
      const withForecast = sortedData.filter(p => p.forecast !== null).length;
      const withActual = sortedData.filter(p => p.actual !== null).length;
      console.log('[ForecastChart] Points with forecast:', withForecast, 'with actual:', withActual);
    }
    return sortedData;
  }, [actuals, showActuals, showBaseline, isEnsemble, detail, selectedModel, categoryResults]);

  // Reference line at the boundary between actuals and forecast
  const boundary = actuals.length > 0 ? actuals[actuals.length - 1].date : null;

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
              {boundary && (
                <ReferenceLine
                  x={boundary}
                  stroke={theme.palette.text.disabled}
                  strokeDasharray="3 3"
                  label={{ value: 'Forecast start', position: 'top', fontSize: 10, fill: theme.palette.text.secondary }}
                />
              )}
              {boundary && (detail.auto_backtest || (detail.request.backtest_overlap != null && detail.request.backtest_overlap > 0)) && actuals.length > 0 && (
                <ReferenceArea
                  x1={actuals.slice(-(detail.backtest_overlap_n || detail.request.backtest_overlap || 0))[0]?.date ?? boundary}
                  x2={boundary}
                  fill={theme.palette.warning.light}
                  fillOpacity={0.08}
                  stroke="none"
                  label={{ value: detail.auto_backtest ? 'Auto backtest zone' : 'Backtest zone', position: 'insideTopLeft', fontSize: 10, fill: theme.palette.warning.main }}
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
          Black line: historical actuals · Blue line: forecast (through backtest zone) · Dashed grey line: baseline (no uplift) · Shaded area: 95% confidence interval.
        </Typography>
      </CardContent>
    </Card>
  );
}
