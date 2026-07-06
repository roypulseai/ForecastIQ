import { useMemo, type ReactNode } from 'react';
import { Box, Card, CardContent, Stack, Typography } from '@mui/material';
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
import { useTheme } from '@mui/material/styles';
import { formatNumber, formatShortDate } from '../../utils/format';

interface DecompositionChartProps {
  dates: string[];
  values: number[];
  period?: number;
  title?: string;
  height?: number;
}

interface DecompPoint {
  date: string;
  trend: number;
  seasonal: number;
  residual: number;
}

function movingAverage(values: number[], window: number): (number | null)[] {
  const half = Math.floor(window / 2);
  const result: (number | null)[] = new Array(values.length).fill(null);
  for (let i = half; i < values.length - half; i += 1) {
    let sum = 0;
    for (let j = i - half; j <= i + half; j += 1) sum += values[j];
    result[i] = sum / window;
  }
  return result;
}

function classicDecompose(values: number[], period: number): {
  trend: (number | null)[];
  seasonal: (number | null)[];
  residual: (number | null)[];
} {
  if (values.length < period * 2) {
    return { trend: values.map(() => null), seasonal: values.map(() => null), residual: values.map(() => null) };
  }
  const trend = movingAverage(values, period);
  const detrended: (number | null)[] = values.map((v, i) =>
    trend[i] !== null && trend[i] !== 0 ? v - (trend[i] as number) : null,
  );
  const seasonalIdx: number[] = new Array(period).fill(0);
  const seasonalCnt: number[] = new Array(period).fill(0);
  for (let i = 0; i < detrended.length; i += 1) {
    const d = detrended[i];
    if (d === null) continue;
    const idx = i % period;
    seasonalIdx[idx] += d;
    seasonalCnt[idx] += 1;
  }
  const seasonalAvg = seasonalIdx.map((s, i) =>
    seasonalCnt[i] > 0 ? s / seasonalCnt[i] : 0,
  );
  const meanSeasonal =
    seasonalAvg.reduce((a, b) => a + b, 0) / Math.max(1, seasonalAvg.length);
  const seasonalNorm = seasonalAvg.map((s) => s - meanSeasonal);
  const seasonal: (number | null)[] = values.map((_, i) => seasonalNorm[i % period]);
  const residual: (number | null)[] = values.map((v, i) => {
    const t = trend[i];
    const s = seasonal[i];
    if (t === null || s === null) return null;
    return v - t - s;
  });
  return { trend, seasonal, residual };
}

export function DecompositionChart({
  dates,
  values,
  period = 7,
  title = 'Trend / Seasonality / Residual',
  height = 360,
}: DecompositionChartProps): ReactNode {
  const theme = useTheme();

  const data: DecompPoint[] = useMemo(() => {
    const { trend, seasonal, residual } = classicDecompose(values, period);
    return dates.map((d, i) => ({
      date: d,
      trend: trend[i] ?? 0,
      seasonal: seasonal[i] ?? 0,
      residual: residual[i] ?? 0,
    }));
  }, [dates, values, period]);

  return (
    <Card>
      <CardContent>
        <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
          <Typography variant="h5">{title}</Typography>
          <Typography variant="caption" color="text.secondary">
            period = {period}
          </Typography>
        </Stack>
        <Box sx={{ width: '100%', height }}>
          <ResponsiveContainer>
            <ComposedChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis
                dataKey="date"
                tickFormatter={(d: string) => formatShortDate(d)}
                tick={{ fontSize: 10, fill: theme.palette.text.secondary }}
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
              <Line
                type="monotone"
                dataKey="trend"
                stroke={theme.palette.primary.main}
                strokeWidth={2.5}
                dot={false}
                name="Trend"
              />
              <Area
                type="monotone"
                dataKey="seasonal"
                stroke={theme.palette.secondary.main}
                fill={theme.palette.secondary.main}
                fillOpacity={0.2}
                strokeWidth={1.5}
                name="Seasonal"
              />
              <Line
                type="monotone"
                dataKey="residual"
                stroke={theme.palette.warning.main}
                strokeWidth={1}
                strokeDasharray="3 3"
                dot={false}
                name="Residual"
              />
            </ComposedChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
}
