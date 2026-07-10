import { ReactNode, useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Box, Typography, Card, CardContent, useTheme } from '@mui/material';

interface ModelComponentsChartProps {
  components: Record<string, unknown> | null | undefined;
  modelName?: string;
}

export function ModelComponentsChart({ components, modelName }: ModelComponentsChartProps): ReactNode {
  const theme = useTheme();

  const hasData = components && (
    Array.isArray(components.trend) ||
    Array.isArray(components.yearly) ||
    Array.isArray(components.weekly)
  );

  const data = useMemo(() => {
    if (!hasData) return [];
    const maxLen = Math.max(
      (components!.trend as unknown[])?.length ?? 0,
      (components!.yearly as unknown[])?.length ?? 0,
      (components!.weekly as unknown[])?.length ?? 0,
    );
    return Array.from({ length: maxLen }, (_, i) => ({
      index: i,
      trend: (components!.trend as number[])?.[i] ?? null,
      yearly: (components!.yearly as number[])?.[i] ?? null,
      weekly: (components!.weekly as number[])?.[i] ?? null,
    }));
  }, [components, hasData]);

  if (data.length === 0) return null;

  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
          Model components {modelName ? `(${modelName})` : ''}
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
          Decomposed trend, yearly, and weekly patterns from the forecast model
        </Typography>

        <Box sx={{ width: '100%', height: 200 }}>
          <ResponsiveContainer>
            <LineChart data={data} margin={{ left: 10, right: 10, top: 5, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="index" tick={{ fontSize: 10 }} label={{ value: 'Period', position: 'insideBottom', offset: -5 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend />
              {data.some((d) => d.trend != null) && (
                <Line type="monotone" dataKey="trend" stroke={theme.palette.primary.main} dot={false} strokeWidth={2} name="Trend" />
              )}
              {data.some((d) => d.yearly != null) && (
                <Line type="monotone" dataKey="yearly" stroke={theme.palette.success.main} dot={false} strokeWidth={1.5} name="Yearly" />
              )}
              {data.some((d) => d.weekly != null) && (
                <Line type="monotone" dataKey="weekly" stroke={theme.palette.warning.main} dot={false} strokeWidth={1.5} name="Weekly" />
              )}
            </LineChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
}
