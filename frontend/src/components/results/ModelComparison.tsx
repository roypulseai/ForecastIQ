import { useMemo, type ReactNode } from 'react';
import { Box, Card, CardContent, Stack, Typography } from '@mui/material';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useTheme } from '@mui/material/styles';
import type { ModelRanking } from '../../types';
import { formatMetric, formatNumber } from '../../utils/format';

interface ModelComparisonProps {
  rankings: ModelRanking[];
  bestModel?: string | null;
}

const METRICS = ['mae', 'rmse', 'mape'] as const;
type Metric = (typeof METRICS)[number];

interface BarRow {
  model: string;
  mae: number;
  rmse: number;
  mape: number;
}

export function ModelComparison({ rankings, bestModel }: ModelComparisonProps): ReactNode {
  const theme = useTheme();

  const data: BarRow[] = useMemo(() => {
    return rankings
      .filter((r) => r.model !== 'ensemble')
      .map((r) => ({
        model: r.model.toUpperCase(),
        mae: r.mae ?? 0,
        rmse: r.rmse ?? 0,
        mape: (r.mape ?? 0) * 100,
      }));
  }, [rankings]);

  if (data.length === 0) {
    return (
      <Card>
        <CardContent>
          <Typography variant="body2" color="text.secondary">
            No model rankings available.
          </Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          alignItems={{ xs: 'flex-start', sm: 'center' }}
          justifyContent="space-between"
          sx={{ mb: 2 }}
        >
          <Box>
            <Typography variant="h5">Model comparison</Typography>
            <Typography variant="body2" color="text.secondary">
              Lower is better across all metrics
            </Typography>
          </Box>
          {bestModel && (
            <Typography variant="body2" color="success.main" sx={{ fontWeight: 600 }}>
              ★ Best: {bestModel.toUpperCase()}
            </Typography>
          )}
        </Stack>
        <Box sx={{ width: '100%', height: 360 }}>
          <ResponsiveContainer>
            <BarChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis
                dataKey="model"
                tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                stroke={theme.palette.divider}
              />
              <YAxis
                tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                stroke={theme.palette.divider}
                tickFormatter={(v: number) => formatMetric('mape', v)}
              />
              <Tooltip
                contentStyle={{
                  borderRadius: 8,
                  border: `1px solid ${theme.palette.divider}`,
                  fontSize: 12,
                }}
                formatter={(value: number, name: string) => {
                  const key = String(name).toLowerCase();
                  if (key === 'mape') return [`${value.toFixed(2)}%`, 'MAPE'];
                  return [formatMetric(key, value), String(name).toUpperCase()];
                }}
              />
              <Legend />
              {(['mae', 'rmse', 'mape'] as Metric[]).map((m) => (
                <Bar key={m} dataKey={m} radius={[6, 6, 0, 0]}>
                  {data.map((row) => (
                    <Cell
                      key={`${row.model}-${m}`}
                      fill={
                        m === 'mae'
                          ? theme.palette.primary.main
                          : m === 'rmse'
                            ? theme.palette.secondary.main
                            : theme.palette.info.main
                      }
                    />
                  ))}
                </Bar>
              ))}
            </BarChart>
          </ResponsiveContainer>
        </Box>
        <Box
          sx={{
            mt: 2,
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', sm: 'repeat(3, 1fr)' },
            gap: 1.5,
          }}
        >
          {data.map((row) => (
            <Box
              key={row.model}
              sx={{
                p: 1.5,
                borderRadius: 1.5,
                backgroundColor: 'background.subtle',
                border: '1px solid',
                borderColor: 'divider',
              }}
            >
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                {row.model}
              </Typography>
              <Stack direction="row" spacing={2} sx={{ mt: 0.5 }}>
                <Typography variant="body2">MAE {formatNumber(row.mae, 1)}</Typography>
                <Typography variant="body2">RMSE {formatNumber(row.rmse, 1)}</Typography>
                <Typography variant="body2">MAPE {row.mape.toFixed(1)}%</Typography>
              </Stack>
            </Box>
          ))}
        </Box>
      </CardContent>
    </Card>
  );
}
