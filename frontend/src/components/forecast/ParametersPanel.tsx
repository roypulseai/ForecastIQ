import { useState } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Slider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Tooltip,
} from '@mui/material'
import { ExpandMore, Tune, Info } from '@mui/icons-material'

interface ModelParams {
  arima?: { p: number; d: number; q: number }
  sarimax?: { p: number; d: number; q: number; seasonal_p: number; seasonal_d: number; seasonal_q: number; seasonal_period: number }
  prophet?: { seasonality_mode: string; yearly_seasonality: boolean; weekly_seasonality: boolean; daily_seasonality: boolean; changepoint_prior_scale: number; seasonality_prior_scale: number; holidays_prior_scale: number }
  lightgbm?: { n_estimators: number; learning_rate: number; max_depth: number; num_leaves: number; min_child_samples: number }
  xgboost?: { n_estimators: number; learning_rate: number; max_depth: number; min_child_weight: number; subsample: number; colsample_bytree: number }
  wma?: { window: number }
  ets?: { trend: string; seasonal: string; seasonal_periods: number }
  theta?: { period: number; deseasonalize: boolean }
  stl?: { period: number; robust: boolean }
}

interface ParametersPanelProps {
  selectedModels: string[]
  parameters: ModelParams
  onChange: (params: ModelParams) => void
}

function ARIMAParams({ value, onChange }: { value: ModelParams['arima']; onChange: (v: ModelParams['arima']) => void }) {
  const params = value || { p: 1, d: 1, q: 1 }
  
  return (
    <Grid container spacing={2}>
      <Grid item xs={12} sm={4}>
        <Box sx={{ px: 1 }}>
          <Typography variant="caption" gutterBottom>
            AR (p): {params.p}
          </Typography>
          <Slider
            value={params.p}
            min={0}
            max={10}
            step={1}
            onChange={(_, v) => onChange({ ...params, p: v as number })}
            marks={[{ value: 0 }, { value: 5 }, { value: 10 }]}
          />
        </Box>
      </Grid>
      <Grid item xs={12} sm={4}>
        <Box sx={{ px: 1 }}>
          <Typography variant="caption" gutterBottom>
            Differencing (d): {params.d}
          </Typography>
          <Slider
            value={params.d}
            min={0}
            max={2}
            step={1}
            onChange={(_, v) => onChange({ ...params, d: v as number })}
            marks={[{ value: 0 }, { value: 1 }, { value: 2 }]}
          />
        </Box>
      </Grid>
      <Grid item xs={12} sm={4}>
        <Box sx={{ px: 1 }}>
          <Typography variant="caption" gutterBottom>
            MA (q): {params.q}
          </Typography>
          <Slider
            value={params.q}
            min={0}
            max={10}
            step={1}
            onChange={(_, v) => onChange({ ...params, q: v as number })}
            marks={[{ value: 0 }, { value: 5 }, { value: 10 }]}
          />
        </Box>
      </Grid>
    </Grid>
  )
}

function SARIMAXParams({ value, onChange }: { value: ModelParams['sarimax']; onChange: (v: ModelParams['sarimax']) => void }) {
  const params = value || { p: 1, d: 1, q: 1, seasonal_p: 1, seasonal_d: 1, seasonal_q: 1, seasonal_period: 7 }
  
  return (
    <Grid container spacing={2}>
      <Grid item xs={12} sm={6}>
        <Typography variant="subtitle2" sx={{ mb: 1 }}>Non-Seasonal</Typography>
        <Grid container spacing={1}>
          <Grid item xs={4}>
            <TextField
              size="small"
              label="p"
              type="number"
              value={params.p}
              onChange={(e) => onChange({ ...params, p: parseInt(e.target.value) || 1 })}
              inputProps={{ min: 0, max: 10 }}
              fullWidth
            />
          </Grid>
          <Grid item xs={4}>
            <TextField
              size="small"
              label="d"
              type="number"
              value={params.d}
              onChange={(e) => onChange({ ...params, d: parseInt(e.target.value) || 1 })}
              inputProps={{ min: 0, max: 2 }}
              fullWidth
            />
          </Grid>
          <Grid item xs={4}>
            <TextField
              size="small"
              label="q"
              type="number"
              value={params.q}
              onChange={(e) => onChange({ ...params, q: parseInt(e.target.value) || 1 })}
              inputProps={{ min: 0, max: 10 }}
              fullWidth
            />
          </Grid>
        </Grid>
      </Grid>
      <Grid item xs={12} sm={6}>
        <Typography variant="subtitle2" sx={{ mb: 1 }}>Seasonal</Typography>
        <Grid container spacing={1}>
          <Grid item xs={3}>
            <TextField
              size="small"
              label="P"
              type="number"
              value={params.seasonal_p}
              onChange={(e) => onChange({ ...params, seasonal_p: parseInt(e.target.value) || 1 })}
              inputProps={{ min: 0, max: 5 }}
              fullWidth
            />
          </Grid>
          <Grid item xs={3}>
            <TextField
              size="small"
              label="D"
              type="number"
              value={params.seasonal_d}
              onChange={(e) => onChange({ ...params, seasonal_d: parseInt(e.target.value) || 1 })}
              inputProps={{ min: 0, max: 2 }}
              fullWidth
            />
          </Grid>
          <Grid item xs={3}>
            <TextField
              size="small"
              label="Q"
              type="number"
              value={params.seasonal_q}
              onChange={(e) => onChange({ ...params, seasonal_q: parseInt(e.target.value) || 1 })}
              inputProps={{ min: 0, max: 5 }}
              fullWidth
            />
          </Grid>
          <Grid item xs={3}>
            <TextField
              size="small"
              label="Period"
              type="number"
              value={params.seasonal_period}
              onChange={(e) => onChange({ ...params, seasonal_period: parseInt(e.target.value) || 7 })}
              inputProps={{ min: 2, max: 365 }}
              fullWidth
            />
          </Grid>
        </Grid>
      </Grid>
    </Grid>
  )
}

function ProphetParams({ value, onChange }: { value: ModelParams['prophet']; onChange: (v: ModelParams['prophet']) => void }) {
  const params = value || {
    seasonality_mode: 'additive',
    yearly_seasonality: true,
    weekly_seasonality: true,
    daily_seasonality: false,
    changepoint_prior_scale: 0.05,
    seasonality_prior_scale: 10.0,
    holidays_prior_scale: 10.0,
  }
  
  return (
    <Grid container spacing={3}>
      <Grid item xs={12} sm={6}>
        <FormControl fullWidth size="small">
          <InputLabel>Seasonality Mode</InputLabel>
          <Select
            value={params.seasonality_mode}
            label="Seasonality Mode"
            onChange={(e) => onChange({ ...params, seasonality_mode: e.target.value })}
          >
            <MenuItem value="additive">Additive</MenuItem>
            <MenuItem value="multiplicative">Multiplicative</MenuItem>
          </Select>
        </FormControl>
      </Grid>
      <Grid item xs={12} sm={6}>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Chip
            label="Yearly"
            color={params.yearly_seasonality ? 'primary' : 'default'}
            onClick={() => onChange({ ...params, yearly_seasonality: !params.yearly_seasonality })}
            size="small"
          />
          <Chip
            label="Weekly"
            color={params.weekly_seasonality ? 'primary' : 'default'}
            onClick={() => onChange({ ...params, weekly_seasonality: !params.weekly_seasonality })}
            size="small"
          />
          <Chip
            label="Daily"
            color={params.daily_seasonality ? 'primary' : 'default'}
            onClick={() => onChange({ ...params, daily_seasonality: !params.daily_seasonality })}
            size="small"
          />
        </Box>
      </Grid>
      <Grid item xs={12}>
        <Typography variant="caption" gutterBottom>
          Changepoint Prior Scale (trend flexibility): {params.changepoint_prior_scale}
          <Tooltip title="Controls how flexible the trend is. Higher values allow more changes.">
            <Info sx={{ fontSize: 14, ml: 0.5, verticalAlign: 'middle' }} />
          </Tooltip>
        </Typography>
        <Slider
          value={params.changepoint_prior_scale}
          min={0.001}
          max={1}
          step={0.001}
          onChange={(_, v) => onChange({ ...params, changepoint_prior_scale: v as number })}
          marks={[{ value: 0.001, label: '0.001' }, { value: 0.5, label: '0.5' }, { value: 1, label: '1' }]}
        />
      </Grid>
      <Grid item xs={12}>
        <Typography variant="caption" gutterBottom>
          Seasonality Prior Scale: {params.seasonality_prior_scale}
          <Tooltip title="Controls how strong seasonality effects are.">
            <Info sx={{ fontSize: 14, ml: 0.5, verticalAlign: 'middle' }} />
          </Tooltip>
        </Typography>
        <Slider
          value={params.seasonality_prior_scale}
          min={0.01}
          max={100}
          step={0.01}
          onChange={(_, v) => onChange({ ...params, seasonality_prior_scale: v as number })}
          marks={[{ value: 0.01, label: '0.01' }, { value: 50, label: '50' }, { value: 100, label: '100' }]}
        />
      </Grid>
      <Grid item xs={12}>
        <Typography variant="caption" gutterBottom>
          Holidays Prior Scale: {params.holidays_prior_scale}
        </Typography>
        <Slider
          value={params.holidays_prior_scale}
          min={0.01}
          max={100}
          step={0.01}
          onChange={(_, v) => onChange({ ...params, holidays_prior_scale: v as number })}
          marks={[{ value: 0.01, label: '0.01' }, { value: 50, label: '50' }, { value: 100, label: '100' }]}
        />
      </Grid>
    </Grid>
  )
}

function LightGBMParams({ value, onChange }: { value: ModelParams['lightgbm']; onChange: (v: ModelParams['lightgbm']) => void }) {
  const params = value || { n_estimators: 100, learning_rate: 0.1, max_depth: 5, num_leaves: 31, min_child_samples: 20 }
  
  return (
    <Grid container spacing={2}>
      <Grid item xs={12} sm={6}>
        <TextField
          fullWidth
          size="small"
          label="Number of Estimators"
          type="number"
          value={params.n_estimators}
          onChange={(e) => onChange({ ...params, n_estimators: parseInt(e.target.value) || 100 })}
          inputProps={{ min: 10, max: 1000 }}
        />
      </Grid>
      <Grid item xs={12} sm={6}>
        <TextField
          fullWidth
          size="small"
          label="Learning Rate"
          type="number"
          value={params.learning_rate}
          onChange={(e) => onChange({ ...params, learning_rate: parseFloat(e.target.value) || 0.1 })}
          inputProps={{ min: 0.01, max: 1, step: 0.01 }}
        />
      </Grid>
      <Grid item xs={12} sm={6}>
        <Box sx={{ px: 1 }}>
          <Typography variant="caption" gutterBottom>
            Max Depth: {params.max_depth}
          </Typography>
          <Slider
            value={params.max_depth}
            min={1}
            max={20}
            step={1}
            onChange={(_, v) => onChange({ ...params, max_depth: v as number })}
            marks={[{ value: 1 }, { value: 10 }, { value: 20 }]}
          />
        </Box>
      </Grid>
      <Grid item xs={12} sm={6}>
        <Box sx={{ px: 1 }}>
          <Typography variant="caption" gutterBottom>
            Num Leaves: {params.num_leaves}
          </Typography>
          <Slider
            value={params.num_leaves}
            min={2}
            max={255}
            step={1}
            onChange={(_, v) => onChange({ ...params, num_leaves: v as number })}
            marks={[{ value: 2 }, { value: 128 }, { value: 255 }]}
          />
        </Box>
      </Grid>
      <Grid item xs={12} sm={6}>
        <TextField
          fullWidth
          size="small"
          label="Min Child Samples"
          type="number"
          value={params.min_child_samples}
          onChange={(e) => onChange({ ...params, min_child_samples: parseInt(e.target.value) || 20 })}
          inputProps={{ min: 1, max: 100 }}
        />
      </Grid>
    </Grid>
  )
}

function WMAParams({ value, onChange }: { value: ModelParams['wma']; onChange: (v: ModelParams['wma']) => void }) {
  const params = value || { window: 8 }

  return (
    <Box sx={{ px: 1, maxWidth: 300 }}>
      <Typography variant="caption" gutterBottom>
        Lookback Window: {params.window} days
      </Typography>
      <Slider
        value={params.window}
        min={2}
        max={365}
        step={1}
        onChange={(_, v) => onChange({ window: v as number })}
        marks={[{ value: 2 }, { value: 30 }, { value: 90 }, { value: 180 }, { value: 365 }]}
      />
    </Box>
  )
}

function XGBoostParams({ value, onChange }: { value: ModelParams['xgboost']; onChange: (v: ModelParams['xgboost']) => void }) {
  const params = value || { n_estimators: 100, learning_rate: 0.1, max_depth: 5, min_child_weight: 1, subsample: 1.0, colsample_bytree: 1.0 }

  return (
    <Grid container spacing={2}>
      <Grid item xs={12} sm={6}>
        <TextField
          fullWidth
          size="small"
          label="Number of Estimators"
          type="number"
          value={params.n_estimators}
          onChange={(e) => onChange({ ...params, n_estimators: parseInt(e.target.value) || 100 })}
          inputProps={{ min: 10, max: 1000 }}
        />
      </Grid>
      <Grid item xs={12} sm={6}>
        <TextField
          fullWidth
          size="small"
          label="Learning Rate"
          type="number"
          value={params.learning_rate}
          onChange={(e) => onChange({ ...params, learning_rate: parseFloat(e.target.value) || 0.1 })}
          inputProps={{ min: 0.01, max: 1, step: 0.01 }}
        />
      </Grid>
      <Grid item xs={12} sm={6}>
        <Box sx={{ px: 1 }}>
          <Typography variant="caption" gutterBottom>
            Max Depth: {params.max_depth}
          </Typography>
          <Slider
            value={params.max_depth}
            min={1}
            max={20}
            step={1}
            onChange={(_, v) => onChange({ ...params, max_depth: v as number })}
            marks={[{ value: 1 }, { value: 10 }, { value: 20 }]}
          />
        </Box>
      </Grid>
      <Grid item xs={12} sm={6}>
        <TextField
          fullWidth
          size="small"
          label="Min Child Weight"
          type="number"
          value={params.min_child_weight}
          onChange={(e) => onChange({ ...params, min_child_weight: parseInt(e.target.value) || 1 })}
          inputProps={{ min: 1, max: 100 }}
        />
      </Grid>
    </Grid>
  )
}

function ETSParams({ value, onChange }: { value: ModelParams['ets']; onChange: (v: ModelParams['ets']) => void }) {
  const params = value || { trend: 'add', seasonal: 'add', seasonal_periods: 7 }

  return (
    <Grid container spacing={2}>
      <Grid item xs={12} sm={4}>
        <FormControl fullWidth size="small">
          <InputLabel>Trend</InputLabel>
          <Select
            value={params.trend}
            label="Trend"
            onChange={(e) => onChange({ ...params, trend: e.target.value })}
          >
            <MenuItem value="add">Additive</MenuItem>
            <MenuItem value="mul">Multiplicative</MenuItem>
            <MenuItem value=None>None</MenuItem>
          </Select>
        </FormControl>
      </Grid>
      <Grid item xs={12} sm={4}>
        <FormControl fullWidth size="small">
          <InputLabel>Seasonal</InputLabel>
          <Select
            value={params.seasonal}
            label="Seasonal"
            onChange={(e) => onChange({ ...params, seasonal: e.target.value })}
          >
            <MenuItem value="add">Additive</MenuItem>
            <MenuItem value="mul">Multiplicative</MenuItem>
            <MenuItem value="None">None</MenuItem>
          </Select>
        </FormControl>
      </Grid>
      <Grid item xs={12} sm={4}>
        <TextField
          fullWidth
          size="small"
          label="Seasonal Period"
          type="number"
          value={params.seasonal_periods}
          onChange={(e) => onChange({ ...params, seasonal_periods: parseInt(e.target.value) || 7 })}
          inputProps={{ min: 2, max: 365 }}
        />
      </Grid>
    </Grid>
  )
}

function ThetaParams({ value, onChange }: { value: ModelParams['theta']; onChange: (v: ModelParams['theta']) => void }) {
  const params = value || { period: 7, deseasonalize: true }

  return (
    <Grid container spacing={2}>
      <Grid item xs={12} sm={6}>
        <TextField
          fullWidth
          size="small"
          label="Period"
          type="number"
          value={params.period}
          onChange={(e) => onChange({ ...params, period: parseInt(e.target.value) || 7 })}
          inputProps={{ min: 2, max: 365 }}
        />
      </Grid>
      <Grid item xs={12} sm={6}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <input
            type="checkbox"
            checked={params.deseasonalize}
            onChange={(e) => onChange({ ...params, deseasonalize: e.target.checked })}
          />
          <Typography>Deseasonalize</Typography>
        </Box>
      </Grid>
    </Grid>
  )
}

function STLParams({ value, onChange }: { value: ModelParams['stl']; onChange: (v: ModelParams['stl']) => void }) {
  const params = value || { period: 7, robust: true }

  return (
    <Grid container spacing={2}>
      <Grid item xs={12} sm={6}>
        <TextField
          fullWidth
          size="small"
          label="Seasonal Period"
          type="number"
          value={params.period}
          onChange={(e) => onChange({ ...params, period: parseInt(e.target.value) || 7 })}
          inputProps={{ min: 2, max: 365 }}
        />
      </Grid>
      <Grid item xs={12} sm={6}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <input
            type="checkbox"
            checked={params.robust}
            onChange={(e) => onChange({ ...params, robust: e.target.checked })}
          />
          <Typography>Robust Fitting</Typography>
        </Box>
      </Grid>
    </Grid>
  )
}

export function ParametersPanel({ selectedModels, parameters, onChange }: ParametersPanelProps) {
  const [expanded, setExpanded] = useState<string | null>('prophet')
  
  const handleChange = (model: string) => (event: React.SyntheticEvent, isExpanded: boolean) => {
    setExpanded(isExpanded ? model : null)
  }
  
  const updateParams = (model: string, newParams: any) => {
    onChange({ ...parameters, [model]: newParams })
  }
  
  const hasAnyParams = selectedModels.length > 0
  
  if (!hasAnyParams) {
    return null
  }
  
  return (
    <Card sx={{ mt: 3 }}>
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
          <Tune sx={{ color: 'primary.main' }} />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Model Parameters
          </Typography>
          <Chip label="Power User" size="small" color="secondary" sx={{ ml: 1 }} />
        </Box>
        
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Fine-tune model hyperparameters for each forecasting method. Leave default values for automatic selection.
        </Typography>
        
        {selectedModels.includes('arima') && (
          <Accordion expanded={expanded === 'arima'} onChange={handleChange('arima')}>
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Typography sx={{ fontWeight: 600 }}>ARIMA</Typography>
              <Typography variant="caption" color="text.secondary" sx={{ ml: 2 }}>
                (p, d, q) = ({parameters.arima?.p || 1}, {parameters.arima?.d || 1}, {parameters.arima?.q || 1})
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <ARIMAParams value={parameters.arima} onChange={(v) => updateParams('arima', v)} />
            </AccordionDetails>
          </Accordion>
        )}
        
        {selectedModels.includes('sarimax') && (
          <Accordion expanded={expanded === 'sarimax'} onChange={handleChange('sarimax')}>
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Typography sx={{ fontWeight: 600 }}>SARIMAX</Typography>
              <Typography variant="caption" color="text.secondary" sx={{ ml: 2 }}>
                Seasonal ARIMA with period {parameters.sarimax?.seasonal_period || 7}
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <SARIMAXParams value={parameters.sarimax} onChange={(v) => updateParams('sarimax', v)} />
            </AccordionDetails>
          </Accordion>
        )}
        
        {selectedModels.includes('prophet') && (
          <Accordion expanded={expanded === 'prophet'} onChange={handleChange('prophet')}>
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Typography sx={{ fontWeight: 600 }}>Prophet</Typography>
              <Typography variant="caption" color="text.secondary" sx={{ ml: 2 }}>
                {parameters.prophet?.seasonality_mode || 'additive'} mode
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <ProphetParams value={parameters.prophet} onChange={(v) => updateParams('prophet', v)} />
            </AccordionDetails>
          </Accordion>
        )}
        
        {selectedModels.includes('lightgbm') && (
          <Accordion expanded={expanded === 'lightgbm'} onChange={handleChange('lightgbm')}>
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Typography sx={{ fontWeight: 600 }}>LightGBM</Typography>
              <Typography variant="caption" color="text.secondary" sx={{ ml: 2 }}>
                {parameters.lightgbm?.n_estimators || 100} trees, lr={parameters.lightgbm?.learning_rate || 0.1}
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <LightGBMParams value={parameters.lightgbm} onChange={(v) => updateParams('lightgbm', v)} />
            </AccordionDetails>
          </Accordion>
        )}
        
        {selectedModels.includes('wma') && (
          <Accordion expanded={expanded === 'wma'} onChange={handleChange('wma')}>
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Typography sx={{ fontWeight: 600 }}>Weighted Moving Average</Typography>
              <Typography variant="caption" color="text.secondary" sx={{ ml: 2 }}>
                Window: {parameters.wma?.window || 8} days
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <WMAParams value={parameters.wma} onChange={(v) => updateParams('wma', v)} />
            </AccordionDetails>
          </Accordion>
        )}

        {selectedModels.includes('xgboost') && (
          <Accordion expanded={expanded === 'xgboost'} onChange={handleChange('xgboost')}>
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Typography sx={{ fontWeight: 600 }}>XGBoost</Typography>
              <Typography variant="caption" color="text.secondary" sx={{ ml: 2 }}>
                {parameters.xgboost?.n_estimators || 100} trees, lr={parameters.xgboost?.learning_rate || 0.1}
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <XGBoostParams value={parameters.xgboost} onChange={(v) => updateParams('xgboost', v)} />
            </AccordionDetails>
          </Accordion>
        )}

        {selectedModels.includes('ets') && (
          <Accordion expanded={expanded === 'ets'} onChange={handleChange('ets')}>
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Typography sx={{ fontWeight: 600 }}>ETS</Typography>
              <Typography variant="caption" color="text.secondary" sx={{ ml: 2 }}>
                {parameters.ets?.trend || 'add'} trend, {parameters.ets?.seasonal || 'add'} seasonal
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <ETSParams value={parameters.ets} onChange={(v) => updateParams('ets', v)} />
            </AccordionDetails>
          </Accordion>
        )}

        {selectedModels.includes('theta') && (
          <Accordion expanded={expanded === 'theta'} onChange={handleChange('theta')}>
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Typography sx={{ fontWeight: 600 }}>Theta</Typography>
              <Typography variant="caption" color="text.secondary" sx={{ ml: 2 }}>
                Period: {parameters.theta?.period || 7}, {parameters.theta?.deseasonalize ? 'deseasonalized' : 'not deseasonalized'}
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <ThetaParams value={parameters.theta} onChange={(v) => updateParams('theta', v)} />
            </AccordionDetails>
          </Accordion>
        )}

        {selectedModels.includes('stl') && (
          <Accordion expanded={expanded === 'stl'} onChange={handleChange('stl')}>
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Typography sx={{ fontWeight: 600 }}>STL</Typography>
              <Typography variant="caption" color="text.secondary" sx={{ ml: 2 }}>
                Period: {parameters.stl?.period || 7}, {parameters.stl?.robust ? 'robust' : 'standard'}
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <STLParams value={parameters.stl} onChange={(v) => updateParams('stl', v)} />
            </AccordionDetails>
          </Accordion>
        )}
      </CardContent>
    </Card>
  )
}
