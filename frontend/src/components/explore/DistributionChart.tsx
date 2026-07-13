import { useMemo, type ReactNode } from 'react';
import { Box, Card, CardContent, Stack, Typography } from '@mui/material';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useTheme } from '@mui/material/styles';
import { formatNumber } from '../../utils/format';

interface DistributionChartProps {
  values: number[];
  bins?: number;
  title?: string;
  height?: number;
  valueLabel?: string;
}

interface Bin {
  range: string;
  count: number;
  midpoint: number;
  mid: number;
}

function buildHistogram(values: number[], bins: number): Bin[] {
  if (!values.length) return [];
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) {
    return [{ range: formatNumber(min), count: values.length, midpoint: min, mid: min }];
  }
  const width = (max - min) / bins;
  const result: Bin[] = Array.from({ length: bins }, (_, i) => {
    const lo = min + i * width;
    const hi = lo + width;
    return {
      range: `${formatNumber(lo, 0)}–${formatNumber(hi, 0)}`,
      count: 0,
      midpoint: (lo + hi) / 2,
      mid: (lo + hi) / 2,
    };
  });
  for (const v of values) {
    let idx = Math.floor((v - min) / width);
    if (idx >= bins) idx = bins - 1;
    if (idx < 0) idx = 0;
    result[idx].count += 1;
  }
  return result;
}

export function DistributionChart({
  values,
  bins = 20,
  title = 'Distribution',
  height = 280,
  valueLabel = 'Value',
}: DistributionChartProps): ReactNode {
  const theme = useTheme();

  const data = useMemo(() => buildHistogram(values, bins), [values, bins]);
  const maxCount = useMemo(() => data.reduce((m, b) => Math.max(m, b.count), 0), [data]);

  if (values.length === 0) {
    return (
      <Card sx={{ height: '100%' }}>
        <CardContent sx={{ textAlign: 'center', py: 6 }}>
          <Typography variant="body2" color="text.secondary">No distribution data available</Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
          <Typography variant="h5">{title}</Typography>
          <Typography variant="caption" color="text.secondary">
            {values.length} observations · {bins} bins
          </Typography>
        </Stack>
        <Box sx={{ width: '100%', height }}>
          <ResponsiveContainer>
            <BarChart data={data} margin={{ top: 10, right: 10, bottom: 10, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} vertical={false} />
              <XAxis
                dataKey="midpoint"
                tick={{ fontSize: 10, fill: theme.palette.text.secondary }}
                tickFormatter={(v: number) => formatNumber(v, 0)}
                stroke={theme.palette.divider}
              />
              <YAxis
                tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                stroke={theme.palette.divider}
                allowDecimals={false}
              />
              <Tooltip
                contentStyle={{
                  borderRadius: 8,
                  border: `1px solid ${theme.palette.divider}`,
                  fontSize: 12,
                }}
                labelFormatter={(label: number) => `${valueLabel}: ${formatNumber(label, 2)}`}
                formatter={(value: number) => [value, 'Count']}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {data.map((b, i) => (
                  <Cell
                    key={`bin-${i}`}
                    fill={
                      b.count === maxCount
                        ? theme.palette.primary.dark
                        : theme.palette.primary.main
                    }
                    fillOpacity={0.4 + 0.6 * (b.count / Math.max(1, maxCount))}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
}
