import type { ReactNode } from 'react';
import { Box, Card, CardContent, Chip, Divider, Stack, Typography } from '@mui/material';
import { alpha, useTheme } from '@mui/material/styles';
import { MODEL_LABELS, type Frequency, type ModelType } from '../../types';
import { formatPercent } from '../../utils/format';

interface ForecastSummaryProps {
  name: string;
  horizon: number;
  frequency: Frequency;
  dateColumn: string;
  targetColumn: string;
  models: ModelType[];
  external: string[];
  ensemble: boolean;
  hasAggregation: boolean;
}

const FREQ_LABEL: Record<Frequency, string> = {
  D: 'Daily',
  W: 'Weekly',
  F: 'Fortnightly',
  M: 'Monthly',
  Q: 'Quarterly',
  Y: 'Yearly',
};

export function ForecastSummaryCard({
  name,
  horizon,
  frequency,
  dateColumn,
  targetColumn,
  models,
  external,
  ensemble,
  hasAggregation,
}: ForecastSummaryProps): ReactNode {
  const theme = useTheme();
  return (
    <Card sx={{ backgroundColor: alpha(theme.palette.primary.main, 0.04) }} elevation={0}>
      <CardContent>
        <Typography variant="overline" color="primary.main" sx={{ fontWeight: 700 }}>
          Run summary
        </Typography>
        <Typography variant="h4" sx={{ mt: 0.5, mb: 2 }}>
          {name || 'Untitled forecast'}
        </Typography>
        <Stack direction="row" divider={<Divider orientation="vertical" flexItem />} spacing={3} flexWrap="wrap" rowGap={2}>
          <Stat label="Horizon" value={`${horizon} ${FREQ_LABEL[frequency].toLowerCase()} periods`} />
          <Stat label="Date column" value={dateColumn} />
          <Stat label="Target column" value={targetColumn} />
          <Stat label="Models" value={`${models.length} selected${ensemble ? ' + ensemble' : ''}`} />
        </Stack>
        <Box sx={{ mt: 2 }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'block', mb: 0.5 }}>
            Models
          </Typography>
          <Stack direction="row" spacing={0.5} flexWrap="wrap" rowGap={0.5}>
            {models.map((m) => (
              <Chip key={m} label={MODEL_LABELS[m] ?? m} size="small" color="primary" />
            ))}
            {ensemble && <Chip label="Ensemble" size="small" color="secondary" />}
          </Stack>
        </Box>
        {external.length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'block', mb: 0.5 }}>
              External factors
            </Typography>
            <Stack direction="row" spacing={0.5} flexWrap="wrap" rowGap={0.5}>
              {external.map((e) => (
                <Chip key={e} label={e} size="small" variant="outlined" color="secondary" />
              ))}
            </Stack>
          </Box>
        )}
        {hasAggregation && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'block', mb: 0.5 }}>
              Aggregation
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Time, product, and region rollups enabled
            </Typography>
          </Box>
        )}
        <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
          Note: model accuracy typically falls within {formatPercent(0.05)}–{formatPercent(0.15)} MAPE for daily retail data.
        </Typography>
      </CardContent>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }): ReactNode {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', fontWeight: 600 }}>
        {label}
      </Typography>
      <Typography variant="body1" sx={{ fontWeight: 600 }}>
        {value}
      </Typography>
    </Box>
  );
}
