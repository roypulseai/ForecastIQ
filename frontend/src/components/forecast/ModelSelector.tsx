import type { ReactNode } from 'react';
import { Box, Card, CardActionArea, CardContent, Chip, Stack, Typography } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { alpha, useTheme } from '@mui/material/styles';
import { MODEL_DESCRIPTIONS, MODEL_LABELS, type ModelType } from '../../types';

interface ModelSelectorProps {
  models: ModelType[];
  selected: ModelType[];
  onChange: (models: ModelType[]) => void;
  recommended?: string[];
  disabled?: boolean;
}

const ALL_MODELS: ModelType[] = [
  'arima',
  'sarimax',
  'prophet',
  'lightgbm',
  'xgboost',
  'wma',
  'ets',
  'theta',
  'stl',
];

export function ModelSelector({
  models,
  selected,
  onChange,
  recommended = [],
  disabled = false,
}: ModelSelectorProps): ReactNode {
  const theme = useTheme();
  const list = models.length ? models : ALL_MODELS;

  const toggle = (m: ModelType) => {
    if (disabled) return;
    if (selected.includes(m)) onChange(selected.filter((x) => x !== m));
    else onChange([...selected, m]);
  };

  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(3, 1fr)' },
        gap: 2,
      }}
    >
      {list.map((m) => {
        const isSelected = selected.includes(m);
        const isRecommended = recommended.includes(m);
        return (
          <Card
            key={m}
            elevation={0}
            sx={{
              border: '2px solid',
              borderColor: isSelected ? 'primary.main' : 'divider',
              transition: 'all 200ms ease',
              opacity: disabled ? 0.5 : 1,
              backgroundColor: isSelected
                ? alpha(theme.palette.primary.main, 0.04)
                : 'background.paper',
            }}
          >
            <CardActionArea
              onClick={() => toggle(m)}
              disabled={disabled}
              aria-pressed={isSelected}
              aria-label={`${MODEL_LABELS[m]} model${isSelected ? ', selected' : ''}`}
              sx={{ height: '100%' }}
            >
              <CardContent>
                <Stack spacing={1.25}>
                  <Stack direction="row" alignItems="center" justifyContent="space-between">
                    <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                      {MODEL_LABELS[m]}
                    </Typography>
                    {isSelected && (
                      <CheckCircleIcon color="primary" fontSize="small" />
                    )}
                  </Stack>
                  <Typography variant="body2" color="text.secondary" sx={{ minHeight: 40 }}>
                    {MODEL_DESCRIPTIONS[m]}
                  </Typography>
                  <Stack direction="row" spacing={0.5} flexWrap="wrap" rowGap={0.5}>
                    {isRecommended && (
                      <Chip label="Recommended" size="small" color="primary" />
                    )}
                    {m === 'sarimax' && (
                      <Chip label="External factors" size="small" variant="outlined" />
                    )}
                    {m === 'prophet' && (
                      <Chip label="Holidays" size="small" variant="outlined" />
                    )}
                  </Stack>
                </Stack>
              </CardContent>
            </CardActionArea>
          </Card>
        );
      })}
    </Box>
  );
}
