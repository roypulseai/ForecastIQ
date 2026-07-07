import type { ReactNode } from 'react';
import {
  Autocomplete,
  Box,
  Card,
  CardContent,
  Collapse,
  FormControlLabel,
  Grid,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import { alpha, useTheme } from '@mui/material/styles';
import {
  COMMON_COUNTRIES,
  FILE_TYPE_LABELS,
  type FileType,
  type UploadedFile,
} from '../../types';

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
    auto_detect_events: boolean;
    auto_event_country: string | null;
    auto_event_regions: string[];
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

const COUNTRY_OPTIONS = COMMON_COUNTRIES.map((c) => ({
  code: c.code,
  label: `${c.flag ?? ''} ${c.name} (${c.code})`,
}));

export function ExternalFactors({ files, values, onChange }: ExternalFactorsProps): ReactNode {
  const theme = useTheme();

  const has = (t: FileType) => files.some((f) => f.type === t);

  return (
    <Grid container spacing={2}>
      {FACTOR_KEYS.map(({ key, type, description }) => {
        const available = has(type);
        const checked = values[key] as boolean;
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

      {/* Auto-detect events — always available, no file upload needed */}
      <Grid item xs={12} sm={6} md={4}>
        <Card
          elevation={0}
          sx={{
            border: '1px solid',
            borderColor: values.auto_detect_events ? 'secondary.main' : 'divider',
            backgroundColor: values.auto_detect_events
              ? alpha(theme.palette.secondary.main, 0.04)
              : 'background.paper',
          }}
        >
          <CardContent>
            <FormControlLabel
              control={
                <Switch
                  checked={values.auto_detect_events}
                  onChange={(_, c) => onChange({ ...values, auto_detect_events: c })}
                  inputProps={{ 'aria-label': 'Auto-detect regional events' }}
                  color="secondary"
                />
              }
              label={
                <Box>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    Auto-detect events
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Holidays, cultural feasts &amp; sports (no upload needed)
                  </Typography>
                </Box>
              }
            />

            <Collapse in={values.auto_detect_events}>
              <Box sx={{ mt: 1.5, display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                <Autocomplete
                  size="small"
                  options={COUNTRY_OPTIONS}
                  value={COUNTRY_OPTIONS.find((o) => o.code === values.auto_event_country) ?? undefined}
                  onChange={(_, v) => onChange({
                    ...values,
                    auto_event_country: v?.code ?? null,
                  })}
                  getOptionLabel={(o) => o.label}
                  renderInput={(params) => (
                    <TextField {...params} label="Country" placeholder="Select country" />
                  )}
                  disableClearable
                  fullWidth
                />
                <TextField
                  size="small"
                  label="Regions (optional)"
                  placeholder="e.g. West Bengal, Maharashtra"
                  value={values.auto_event_regions.join(', ')}
                  onChange={(e) => onChange({
                    ...values,
                    auto_event_regions: e.target.value
                      .split(',')
                      .map((s) => s.trim())
                      .filter(Boolean),
                  })}
                  helperText="Comma-separated. Leave empty to auto-detect from data."
                  fullWidth
                />
              </Box>
            </Collapse>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
}
