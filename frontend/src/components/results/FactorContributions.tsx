import { ReactNode, useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Box, Typography, Card, CardContent, Stack, Chip, useTheme } from '@mui/material';
import type { FactorContribution } from '../../types';

interface FactorContributionsProps {
  contributions: Record<string, FactorContribution> | null | undefined;
  totalUplift?: number | null;
}

const FACTOR_LABELS: Record<string, string> = {
  media_plan: 'Media Plan',
  promotions: 'Promotions',
  holidays: 'Holidays',
  events: 'Events',
  weather: 'Weather',
  competitor: 'Competitor',
  economic: 'Economic',
};

const FACTOR_COLORS: Record<string, string> = {
  media_plan: '#2196F3',
  promotions: '#4CAF50',
  holidays: '#FF9800',
  events: '#9C27B0',
  weather: '#00BCD4',
  competitor: '#F44336',
  economic: '#607D8B',
};

export function FactorContributions({ contributions, totalUplift }: FactorContributionsProps): ReactNode {
  const theme = useTheme();

  const chartData = useMemo(() => {
    if (!contributions) return [];
    return Object.entries(contributions)
      .map(([key, val]) => ({
        name: FACTOR_LABELS[key] ?? key,
        key,
        contribution: val.total_contribution,
        direction: val.direction,
      }))
      .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution));
  }, [contributions]);

  if (chartData.length === 0) return null;

  const totalContrib = chartData.reduce((s, d) => s + d.contribution, 0);

  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
          External factor contributions
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ mb: 1.5, display: 'block' }}>
          How much each external factor lifts the forecast
          {totalUplift != null && `  |  Total uplift: ${totalUplift > 0 ? '+' : ''}$${totalUplift.toFixed(2)}`}
        </Typography>

        <Stack direction="row" spacing={0.5} sx={{ mb: 1.5, flexWrap: 'wrap' }} useFlexGap>
          {chartData.map((d) => (
            <Chip
              key={d.key}
              label={`${d.name}: ${d.contribution > 0 ? '+' : ''}$${d.contribution.toFixed(0)}`}
              size="small"
              sx={{
                bgcolor: `${FACTOR_COLORS[d.key] ?? theme.palette.grey[500]}22`,
                color: FACTOR_COLORS[d.key] ?? theme.palette.text.primary,
                fontWeight: 500,
                fontSize: 11,
              }}
            />
          ))}
        </Stack>

        <Box sx={{ width: '100%', height: Math.max(120, chartData.length * 40) }}>
          <ResponsiveContainer>
            <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" tickFormatter={(v: number) => `$${v}`} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 12 }} width={110} />
              <Tooltip formatter={(v: number) => [`$${v.toFixed(2)}`, 'Contribution']} />
              <Bar dataKey="contribution" radius={[0, 3, 3, 0]}>
                {chartData.map((entry) => (
                  <Cell key={entry.key} fill={FACTOR_COLORS[entry.key] ?? theme.palette.primary.main} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Box>

        {Math.abs(totalContrib - (totalUplift ?? 0)) > 1 && (
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            Note: Individual factor contributions (sum: ${totalContrib.toFixed(2)}) may not exactly equal total uplift
            (${(totalUplift ?? 0).toFixed(2)}) due to factor interactions.
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}
