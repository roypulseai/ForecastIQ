import { ReactNode, useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Box, Typography, Card, CardContent, useTheme } from '@mui/material';
import type { DecompositionResult } from '../../types';

interface DecompositionChartProps {
  decomposition: DecompositionResult | null | undefined;
}

export function DecompositionChart({ decomposition }: DecompositionChartProps): ReactNode {
  const theme = useTheme();

  const data = useMemo(() => {
    if (!decomposition?.dates) return [];
    return decomposition.dates.map((d, i) => ({
      date: d,
      trend: decomposition.trend?.[i] ?? null,
      seasonal: decomposition.seasonal?.[i] ?? null,
      residual: decomposition.residual?.[i] ?? null,
    }));
  }, [decomposition]);

  if (data.length === 0) return null;

  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
          Time series decomposition
        </Typography>
        {decomposition?.seasonal_strength != null && (
          <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
            Seasonal strength: {(decomposition.seasonal_strength * 100).toFixed(1)}%
            {decomposition?.period && `  |  Period: ${decomposition.period} days`}
          </Typography>
        )}

        <Box sx={{ width: '100%', height: 280 }}>
          <ResponsiveContainer>
            <LineChart data={data} margin={{ left: 10, right: 10, top: 5, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="trend"
                stroke={theme.palette.primary.main}
                dot={false}
                strokeWidth={2}
                name="Trend"
              />
              <Line
                type="monotone"
                dataKey="seasonal"
                stroke={theme.palette.success.main}
                dot={false}
                strokeWidth={1.5}
                name="Seasonal"
              />
              <Line
                type="monotone"
                dataKey="residual"
                stroke={theme.palette.warning.main}
                dot={false}
                strokeWidth={1}
                strokeDasharray="4 4"
                name="Residual"
              />
            </LineChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
}
