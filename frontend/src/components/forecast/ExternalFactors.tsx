import type { ReactNode } from 'react';
import {
  Box,
  Card,
  CardContent,
  FormControlLabel,
  Grid,
  Switch,
  Typography,
} from '@mui/material';
import { alpha, useTheme } from '@mui/material/styles';
import { FILE_TYPE_LABELS, type FileType, type UploadedFile } from '../../types';

interface ExternalFactorsProps {
  files: UploadedFile[];
  values: {
    media_plan: boolean;
    promotions: boolean;
    holidays: boolean;
    events: boolean;
    weather: boolean;
    competitor: boolean;
    economic: boolean;
  };
  onChange: (next: ExternalFactorsProps['values']) => void;
}

const FACTOR_KEYS: Array<{ key: keyof ExternalFactorsProps['values']; type: FileType; description: string }> = [
  { key: 'media_plan', type: 'media_plan', description: 'Marketing spend & channel mix' },
  { key: 'promotions', type: 'promotions', description: 'Discounts and promotional events' },
  { key: 'holidays', type: 'holidays', description: 'Public holidays with impact factors' },
  { key: 'events', type: 'events', description: 'Sports, concerts, one-off events' },
  { key: 'weather', type: 'weather', description: 'Daily weather by region' },
  { key: 'competitor', type: 'competitor', description: 'Competitor pricing and activity' },
  { key: 'economic', type: 'economic', description: 'Macroeconomic indicators' },
];

export function ExternalFactors({ files, values, onChange }: ExternalFactorsProps): ReactNode {
  const theme = useTheme();

  const has = (t: FileType) => files.some((f) => f.type === t);

  return (
    <Grid container spacing={2}>
      {FACTOR_KEYS.map(({ key, type, description }) => {
        const available = has(type);
        const checked = values[key];
        return (
          <Grid key={key} item xs={12} sm={6} md={4}>
            <Card
              elevation={0}
              sx={{
                border: '1px solid',
                borderColor: checked && available ? 'primary.main' : 'divider',
                backgroundColor:
                  checked && available
                    ? alpha(theme.palette.primary.main, 0.04)
                    : 'background.paper',
                opacity: available ? 1 : 0.55,
              }}
            >
              <CardContent>
                <FormControlLabel
                  control={
                    <Switch
                      checked={checked && available}
                      disabled={!available}
                      onChange={(_, c) => onChange({ ...values, [key]: c })}
                      inputProps={{ 'aria-label': `Include ${FILE_TYPE_LABELS[type]}` }}
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {FILE_TYPE_LABELS[type]}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {description}
                      </Typography>
                    </Box>
                  }
                />
                {!available && (
                  <Typography variant="caption" color="warning.dark" sx={{ display: 'block', mt: 0.5 }}>
                    ⚠ Upload {FILE_TYPE_LABELS[type].toLowerCase()} data to enable
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>
        );
      })}
    </Grid>
  );
}
