import { ReactNode, useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Box, Typography, Card, CardContent, useTheme } from '@mui/material';

interface FeatureImportanceChartProps {
  featureImportance: Record<string, number> | null | undefined;
  modelName?: string;
}

export function FeatureImportanceChart({ featureImportance, modelName }: FeatureImportanceChartProps): ReactNode {
  const theme = useTheme();

  const data = useMemo(() => {
    if (!featureImportance) return [];
    const entries = Object.entries(featureImportance)
      .filter(([, v]) => v > 0)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 20);
    const maxVal = entries.length > 0 ? entries[0][1] : 1;
    return entries.map(([name, val]) => ({
      name,
      importance: val,
      pct: (val / maxVal) * 100,
    }));
  }, [featureImportance]);

  if (data.length === 0) return null;

  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
          Feature importance {modelName ? `(${modelName})` : ''}
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ mb: 1.5, display: 'block' }}>
          Which features drive the forecast most
        </Typography>
        <Box sx={{ width: '100%', height: Math.max(200, data.length * 24) }}>
          <ResponsiveContainer>
            <BarChart data={data} layout="vertical" margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" hide />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fontSize: 11 }}
                width={140}
                tickFormatter={(v: string) => v.replace(/_/g, ' ')}
              />
              <Tooltip
                formatter={(_: unknown, name: string) => [
                  name === 'importance' ? `Importance: ${Number(_).toFixed(1)}` : `${Number(_).toFixed(0)}%`,
                  '',
                ]}
              />
              <Bar dataKey="pct" fill={theme.palette.primary.main} radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
}
