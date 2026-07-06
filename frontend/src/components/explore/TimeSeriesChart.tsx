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
import { formatShortDate, formatNumber } from '../../utils/format';

export interface TimeSeriesPoint {
  date: string;
  value: number;
}

interface TimeSeriesChartProps {
  data: TimeSeriesPoint[];
  title?: string;
  height?: number;
  yLabel?: string;
  highlightOutliers?: boolean;
}

interface ChartPoint extends TimeSeriesPoint {
  trend: number | null;
  isOutlier: boolean;
}

function detectOutliers(values: number[]): boolean[] {
  if (values.length < 4) return values.map(() => false);
  const sorted = [...values].sort((a, b) => a - b);
  const q1 = sorted[Math.floor(sorted.length * 0.25)];
  const q3 = sorted[Math.floor(sorted.length * 0.75)];
  const iqr = q3 - q1;
  const lower = q1 - 1.5 * iqr;
  const upper = q3 + 1.5 * iqr;
  return values.map((v) => v < lower || v > upper);
}

function linearTrend(values: number[]): (number | null)[] {
  if (values.length < 2) return values.map(() => null);
  const n = values.length;
  const xs = values.map((_, i) => i);
  const meanX = xs.reduce((a, b) => a + b, 0) / n;
  const meanY = values.reduce((a, b) => a + b, 0) / n;
  let num = 0;
  let den = 0;
  for (let i = 0; i < n; i += 1) {
    num += (xs[i] - meanX) * (values[i] - meanY);
    den += (xs[i] - meanX) ** 2;
  }
  const slope = den === 0 ? 0 : num / den;
  const intercept = meanY - slope * meanX;
  return xs.map((x) => intercept + slope * x);
}

export function TimeSeriesChart({
  data,
  title,
  height = 360,
  yLabel,
  highlightOutliers = true,
}: TimeSeriesChartProps): ReactNode {
  const theme = useTheme();

  const chartData: ChartPoint[] = useMemo(() => {
    if (!data.length) return [];
    const values = data.map((d) => d.value);
    const isOutlier = detectOutliers(values);
    const trend = linearTrend(values);
    return data.map((d, i) => ({
      ...d,
      trend: trend[i],
      isOutlier: isOutlier[i],
    }));
  }, [data]);

  return (
    <Card>
      <CardContent>
        {title && (
          <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
            <Typography variant="h5">{title}</Typography>
            <Stack direction="row" spacing={2}>
              <LegendDot color={theme.palette.primary.main} label="Value" />
              <LegendDot color={theme.palette.secondary.main} label="Linear trend" />
              {highlightOutliers && (
                <LegendDot color={theme.palette.error.main} label="Outlier" />
              )}
            </Stack>
          </Stack>
        )}
        <Box sx={{ width: '100%', height }}>
          <ResponsiveContainer>
            <ComposedChart data={chartData} margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
              <defs>
                <linearGradient id="tsArea" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={theme.palette.primary.main} stopOpacity={0.18} />
                  <stop offset="100%" stopColor={theme.palette.primary.main} stopOpacity={0} />
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
                label={
                  yLabel
                    ? { value: yLabel, angle: -90, position: 'insideLeft', fill: theme.palette.text.secondary, fontSize: 12 }
                    : undefined
                }
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
                formatter={(value: number, name: string) => [
                  formatNumber(value, 2),
                  name === 'value' ? 'Value' : 'Trend',
                ]}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke={theme.palette.primary.main}
                strokeWidth={2}
                fill="url(#tsArea)"
                dot={(p: { payload?: ChartPoint; cx?: number; cy?: number }) => {
                  const point = p.payload;
                  if (!point) return <g />;
                  if (highlightOutliers && point.isOutlier) {
                    return (
                      <circle
                        key={`outlier-${point.date}`}
                        cx={p.cx ?? 0}
                        cy={p.cy ?? 0}
                        r={4}
                        fill={theme.palette.error.main}
                        stroke={theme.palette.error.dark}
                      />
                    );
                  }
                  return <g />;
                }}
                activeDot={{ r: 4 }}
              />
              <Line
                type="linear"
                dataKey="trend"
                stroke={theme.palette.secondary.main}
                strokeWidth={1.5}
                strokeDasharray="5 4"
                dot={false}
                connectNulls
              />
              <Legend
                content={() => (
                  <Stack direction="row" spacing={3} justifyContent="center" sx={{ pt: 1 }}>
                    <LegendDot color={theme.palette.primary.main} label="Value" />
                    <LegendDot color={theme.palette.secondary.main} label="Linear trend" />
                    {highlightOutliers && (
                      <LegendDot color={theme.palette.error.main} label="Outlier" />
                    )}
                  </Stack>
                )}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
}

function LegendDot({ color, label }: { color: string; label: string }): ReactNode {
  return (
    <Stack direction="row" spacing={0.75} alignItems="center">
      <Box sx={{ width: 10, height: 10, borderRadius: '5px', backgroundColor: color }} />
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
    </Stack>
  );
}
