import { useState, type ReactNode } from 'react';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Grid,
  MenuItem,
  Slider,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import TuneIcon from '@mui/icons-material/Tune';
import type { ModelParameters, ModelType } from '../../types';

interface ParametersPanelProps {
  models: ModelType[];
  value: ModelParameters;
  onChange: (next: ModelParameters) => void;
}

const NUMBER_FIELDS = [
  { key: 'p', label: 'p (autoregressive)', min: 0, max: 10, step: 1 },
  { key: 'd', label: 'd (differencing)', min: 0, max: 2, step: 1 },
  { key: 'q', label: 'q (moving average)', min: 0, max: 10, step: 1 },
] as const;

const SEASONAL_FIELDS = [
  { key: 'seasonal_p', label: 'Seasonal p', min: 0, max: 5, step: 1 },
  { key: 'seasonal_d', label: 'Seasonal d', min: 0, max: 2, step: 1 },
  { key: 'seasonal_q', label: 'Seasonal q', min: 0, max: 5, step: 1 },
  { key: 'seasonal_period', label: 'Seasonal period', min: 2, max: 365, step: 1 },
] as const;

export function ParametersPanel({ models, value, onChange }: ParametersPanelProps): ReactNode {
  const [openPanels, setOpenPanels] = useState<Record<string, boolean>>({});

  const toggle = (m: string) => setOpenPanels((p) => ({ ...p, [m]: !p[m] }));

  const updateArima = (k: 'p' | 'd' | 'q', v: number) =>
    onChange({ ...value, arima: { ...(value.arima ?? { p: 1, d: 1, q: 1 }), [k]: v } });

  const updateSarimax = (k: 'p' | 'd' | 'q' | 'seasonal_p' | 'seasonal_d' | 'seasonal_q' | 'seasonal_period', v: number) =>
    onChange({
      ...value,
      sarimax: {
        ...(value.sarimax ?? { p: 1, d: 1, q: 1, seasonal_p: 1, seasonal_d: 1, seasonal_q: 1, seasonal_period: 7 }),
        [k]: v,
      },
    });

  const updateProphet = (k: keyof NonNullable<ModelParameters['prophet']>, v: string | number | boolean) =>
    onChange({
      ...value,
      prophet: {
        ...(value.prophet ?? {
          seasonality_mode: 'additive' as const,
          yearly_seasonality: true,
          weekly_seasonality: true,
          daily_seasonality: false,
          changepoint_prior_scale: 0.05,
          seasonality_prior_scale: 10,
          holidays_prior_scale: 10,
        }),
        [k]: v,
      },
    });

  const updateLightgbm = (k: keyof NonNullable<ModelParameters['lightgbm']>, v: number) =>
    onChange({
      ...value,
      lightgbm: {
        ...(value.lightgbm ?? { n_estimators: 200, learning_rate: 0.05, max_depth: 5, num_leaves: 31, min_child_samples: 20 }),
        [k]: v,
      },
    });

  const updateXgboost = (k: keyof NonNullable<ModelParameters['xgboost']>, v: number) =>
    onChange({
      ...value,
      xgboost: {
        ...(value.xgboost ?? { n_estimators: 200, learning_rate: 0.05, max_depth: 5, min_child_weight: 1, subsample: 0.9, colsample_bytree: 0.9 }),
        [k]: v,
      },
    });

  const updateWma = (v: number) => onChange({ ...value, wma: { window: v } });
  const updateEts = (k: 'trend' | 'seasonal' | 'seasonal_periods', v: string | number) =>
    onChange({
      ...value,
      ets: {
        ...(value.ets ?? { trend: 'add' as const, seasonal: 'add' as const, seasonal_periods: 7 }),
        [k]: v,
      },
    });
  const updateTheta = (k: 'period' | 'deseasonalize', v: number | boolean) =>
    onChange({ ...value, theta: { ...(value.theta ?? { period: 7, deseasonalize: true }), [k]: v } });
  const updateStl = (k: 'period' | 'robust', v: number | boolean) =>
    onChange({ ...value, stl: { ...(value.stl ?? { period: 7, robust: true }), [k]: v } });

  const enabled = (m: ModelType) => models.includes(m);

  return (
    <Stack spacing={1.5}>
      <Stack direction="row" spacing={1} alignItems="center">
        <TuneIcon fontSize="small" color="action" />
        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
          Model parameters
        </Typography>
        <Typography variant="caption" color="text.secondary">
          (optional, leave at defaults for most cases)
        </Typography>
      </Stack>

      {enabled('arima') && (
        <Accordion expanded={Boolean(openPanels.arima)} onChange={() => toggle('arima')} disableGutters>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography sx={{ fontWeight: 500 }}>ARIMA</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              {NUMBER_FIELDS.map((f) => (
                <Grid key={f.key} item xs={12} sm={4}>
                  <Typography variant="caption" color="text.secondary">
                    {f.label}: {value.arima?.[f.key] ?? 1}
                  </Typography>
                  <Slider
                    value={value.arima?.[f.key] ?? 1}
                    min={f.min}
                    max={f.max}
                    step={f.step}
                    onChange={(_, v) => updateArima(f.key, Array.isArray(v) ? v[0] : v)}
                    valueLabelDisplay="auto"
                    aria-label={f.label}
                  />
                </Grid>
              ))}
            </Grid>
          </AccordionDetails>
        </Accordion>
      )}

      {enabled('sarimax') && (
        <Accordion expanded={Boolean(openPanels.sarimax)} onChange={() => toggle('sarimax')} disableGutters>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography sx={{ fontWeight: 500 }}>SARIMAX</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              {NUMBER_FIELDS.map((f) => (
                <Grid key={f.key} item xs={12} sm={4}>
                  <Typography variant="caption" color="text.secondary">
                    {f.label}: {value.sarimax?.[f.key] ?? 1}
                  </Typography>
                  <Slider
                    value={value.sarimax?.[f.key] ?? 1}
                    min={f.min}
                    max={f.max}
                    step={f.step}
                    onChange={(_, v) => updateSarimax(f.key, Array.isArray(v) ? v[0] : v)}
                    valueLabelDisplay="auto"
                    aria-label={f.label}
                  />
                </Grid>
              ))}
              {SEASONAL_FIELDS.map((f) => (
                <Grid key={f.key} item xs={12} sm={3}>
                  <Typography variant="caption" color="text.secondary">
                    {f.label}: {value.sarimax?.[f.key] ?? f.key === 'seasonal_period' ? 7 : 1}
                  </Typography>
                  <Slider
                    value={value.sarimax?.[f.key] ?? (f.key === 'seasonal_period' ? 7 : 1)}
                    min={f.min}
                    max={f.max}
                    step={f.step}
                    onChange={(_, v) => updateSarimax(f.key, Array.isArray(v) ? v[0] : v)}
                    valueLabelDisplay="auto"
                    aria-label={f.label}
                  />
                </Grid>
              ))}
            </Grid>
          </AccordionDetails>
        </Accordion>
      )}

      {enabled('prophet') && (
        <Accordion expanded={Boolean(openPanels.prophet)} onChange={() => toggle('prophet')} disableGutters>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography sx={{ fontWeight: 500 }}>Prophet</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={4}>
                <TextField
                  select
                  fullWidth
                  size="small"
                  label="Seasonality mode"
                  value={value.prophet?.seasonality_mode ?? 'additive'}
                  onChange={(e) => updateProphet('seasonality_mode', e.target.value)}
                >
                  <MenuItem value="additive">Additive</MenuItem>
                  <MenuItem value="multiplicative">Multiplicative</MenuItem>
                </TextField>
              </Grid>
              <Grid item xs={12} sm={8}>
                <Stack direction="row" spacing={3} alignItems="center" flexWrap="wrap" rowGap={1}>
                  <BoolField
                    label="Yearly"
                    checked={value.prophet?.yearly_seasonality ?? true}
                    onChange={(c) => updateProphet('yearly_seasonality', c)}
                  />
                  <BoolField
                    label="Weekly"
                    checked={value.prophet?.weekly_seasonality ?? true}
                    onChange={(c) => updateProphet('weekly_seasonality', c)}
                  />
                  <BoolField
                    label="Daily"
                    checked={value.prophet?.daily_seasonality ?? false}
                    onChange={(c) => updateProphet('daily_seasonality', c)}
                  />
                </Stack>
              </Grid>
              <Grid item xs={12} sm={4}>
                <NumberField
                  label="Changepoint prior"
                  value={value.prophet?.changepoint_prior_scale ?? 0.05}
                  min={0.001}
                  max={0.5}
                  step={0.005}
                  onChange={(v) => updateProphet('changepoint_prior_scale', v)}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <NumberField
                  label="Seasonality prior"
                  value={value.prophet?.seasonality_prior_scale ?? 10}
                  min={0.1}
                  max={50}
                  step={0.5}
                  onChange={(v) => updateProphet('seasonality_prior_scale', v)}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <NumberField
                  label="Holidays prior"
                  value={value.prophet?.holidays_prior_scale ?? 10}
                  min={0.1}
                  max={50}
                  step={0.5}
                  onChange={(v) => updateProphet('holidays_prior_scale', v)}
                />
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>
      )}

      {enabled('lightgbm') && (
        <Accordion expanded={Boolean(openPanels.lightgbm)} onChange={() => toggle('lightgbm')} disableGutters>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography sx={{ fontWeight: 500 }}>LightGBM</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={4}>
                <NumberField
                  label="Estimators"
                  value={value.lightgbm?.n_estimators ?? 200}
                  min={10}
                  max={2000}
                  step={10}
                  onChange={(v) => updateLightgbm('n_estimators', v)}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <NumberField
                  label="Learning rate"
                  value={value.lightgbm?.learning_rate ?? 0.05}
                  min={0.01}
                  max={1}
                  step={0.01}
                  onChange={(v) => updateLightgbm('learning_rate', v)}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <NumberField
                  label="Max depth"
                  value={value.lightgbm?.max_depth ?? 5}
                  min={1}
                  max={20}
                  step={1}
                  onChange={(v) => updateLightgbm('max_depth', v)}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <NumberField
                  label="Num leaves"
                  value={value.lightgbm?.num_leaves ?? 31}
                  min={2}
                  max={255}
                  step={1}
                  onChange={(v) => updateLightgbm('num_leaves', v)}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <NumberField
                  label="Min child samples"
                  value={value.lightgbm?.min_child_samples ?? 20}
                  min={1}
                  max={200}
                  step={1}
                  onChange={(v) => updateLightgbm('min_child_samples', v)}
                />
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>
      )}

      {enabled('xgboost') && (
        <Accordion expanded={Boolean(openPanels.xgboost)} onChange={() => toggle('xgboost')} disableGutters>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography sx={{ fontWeight: 500 }}>XGBoost</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={4}>
                <NumberField
                  label="Estimators"
                  value={value.xgboost?.n_estimators ?? 200}
                  min={10}
                  max={2000}
                  step={10}
                  onChange={(v) => updateXgboost('n_estimators', v)}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <NumberField
                  label="Learning rate"
                  value={value.xgboost?.learning_rate ?? 0.05}
                  min={0.01}
                  max={1}
                  step={0.01}
                  onChange={(v) => updateXgboost('learning_rate', v)}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <NumberField
                  label="Max depth"
                  value={value.xgboost?.max_depth ?? 5}
                  min={1}
                  max={20}
                  step={1}
                  onChange={(v) => updateXgboost('max_depth', v)}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <NumberField
                  label="Min child weight"
                  value={value.xgboost?.min_child_weight ?? 1}
                  min={1}
                  max={200}
                  step={1}
                  onChange={(v) => updateXgboost('min_child_weight', v)}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <NumberField
                  label="Subsample"
                  value={value.xgboost?.subsample ?? 0.9}
                  min={0.1}
                  max={1}
                  step={0.05}
                  onChange={(v) => updateXgboost('subsample', v)}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <NumberField
                  label="Colsample bytree"
                  value={value.xgboost?.colsample_bytree ?? 0.9}
                  min={0.1}
                  max={1}
                  step={0.05}
                  onChange={(v) => updateXgboost('colsample_bytree', v)}
                />
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>
      )}

      {enabled('wma') && (
        <Accordion expanded={Boolean(openPanels.wma)} onChange={() => toggle('wma')} disableGutters>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography sx={{ fontWeight: 500 }}>WMA</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <NumberField
              label="Window"
              value={value.wma?.window ?? 8}
              min={2}
              max={365}
              step={1}
              onChange={(v) => updateWma(v)}
            />
          </AccordionDetails>
        </Accordion>
      )}

      {enabled('ets') && (
        <Accordion expanded={Boolean(openPanels.ets)} onChange={() => toggle('ets')} disableGutters>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography sx={{ fontWeight: 500 }}>ETS</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={4}>
                <TextField
                  select
                  fullWidth
                  size="small"
                  label="Trend"
                  value={value.ets?.trend ?? 'add'}
                  onChange={(e) => updateEts('trend', e.target.value)}
                >
                  <MenuItem value="add">Additive</MenuItem>
                  <MenuItem value="mul">Multiplicative</MenuItem>
                  <MenuItem value="none">None</MenuItem>
                </TextField>
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  select
                  fullWidth
                  size="small"
                  label="Seasonal"
                  value={value.ets?.seasonal ?? 'add'}
                  onChange={(e) => updateEts('seasonal', e.target.value)}
                >
                  <MenuItem value="add">Additive</MenuItem>
                  <MenuItem value="mul">Multiplicative</MenuItem>
                  <MenuItem value="none">None</MenuItem>
                </TextField>
              </Grid>
              <Grid item xs={12} sm={4}>
                <NumberField
                  label="Seasonal periods"
                  value={value.ets?.seasonal_periods ?? 7}
                  min={2}
                  max={365}
                  step={1}
                  onChange={(v) => updateEts('seasonal_periods', v)}
                />
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>
      )}

      {enabled('theta') && (
        <Accordion expanded={Boolean(openPanels.theta)} onChange={() => toggle('theta')} disableGutters>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography sx={{ fontWeight: 500 }}>Theta</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Stack direction="row" spacing={3} alignItems="center" flexWrap="wrap" rowGap={1}>
              <Box sx={{ width: 200 }}>
                <NumberField
                  label="Period"
                  value={value.theta?.period ?? 7}
                  min={2}
                  max={365}
                  step={1}
                  onChange={(v) => updateTheta('period', v)}
                />
              </Box>
              <BoolField
                label="Deseasonalize"
                checked={value.theta?.deseasonalize ?? true}
                onChange={(c) => updateTheta('deseasonalize', c)}
              />
            </Stack>
          </AccordionDetails>
        </Accordion>
      )}

      {enabled('stl') && (
        <Accordion expanded={Boolean(openPanels.stl)} onChange={() => toggle('stl')} disableGutters>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography sx={{ fontWeight: 500 }}>STL</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Stack direction="row" spacing={3} alignItems="center" flexWrap="wrap" rowGap={1}>
              <Box sx={{ width: 200 }}>
                <NumberField
                  label="Period"
                  value={value.stl?.period ?? 7}
                  min={2}
                  max={365}
                  step={1}
                  onChange={(v) => updateStl('period', v)}
                />
              </Box>
              <BoolField
                label="Robust"
                checked={value.stl?.robust ?? true}
                onChange={(c) => updateStl('robust', c)}
              />
            </Stack>
          </AccordionDetails>
        </Accordion>
      )}
    </Stack>
  );
}

interface NumberFieldProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
}

function NumberField({ label, value, min, max, step, onChange }: NumberFieldProps): ReactNode {
  return (
    <TextField
      type="number"
      size="small"
      fullWidth
      label={label}
      value={Number.isFinite(value) ? value : ''}
      inputProps={{ min, max, step }}
      onChange={(e) => {
        const n = Number(e.target.value);
        if (Number.isFinite(n)) onChange(n);
      }}
    />
  );
}

interface BoolFieldProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}

function BoolField({ label, checked, onChange }: BoolFieldProps): ReactNode {
  return (
    <Stack direction="row" alignItems="center" spacing={1}>
      <Switch size="small" checked={checked} onChange={(_, c) => onChange(c)} />
      <Typography variant="body2">{label}</Typography>
    </Stack>
  );
}
