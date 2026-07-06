import { useState } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  FormControlLabel,
  Button,
  Chip,
  Alert,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tabs,
  Tab,
  Slider,
} from '@mui/material'
import { PlayArrow, Info, Download, ExpandMore, Compare } from '@mui/icons-material'
import { forecastApi, ForecastRequest, ModelParameters } from '../services/api'
import { useStore } from '../store/appStore'
import { ParametersPanel } from '../components/forecast/ParametersPanel'
import { WhatIfSimulator } from '../components/forecast/WhatIfSimulator'
import { AggregationPanel } from '../components/forecast/AggregationPanel'

const modelOptions = [
  { value: 'arima', label: 'ARIMA', description: 'AutoRegressive Integrated Moving Average' },
  { value: 'sarimax', label: 'SARIMAX', description: 'Seasonal ARIMAX with exogenous variables' },
  { value: 'prophet', label: 'Prophet', description: 'Facebook\'s time series forecasting' },
  { value: 'lightgbm', label: 'LightGBM', description: 'Gradient boosting for time series' },
  { value: 'xgboost', label: 'XGBoost', description: 'Extreme gradient boosting' },
  { value: 'wma', label: 'WMA', description: 'Weighted Moving Average' },
  { value: 'ets', label: 'ETS', description: 'Error-Trend-Seasonal' },
  { value: 'theta', label: 'Theta', description: 'Theta method (M3 winner)' },
  { value: 'stl', label: 'STL', description: 'Seasonal-Trend decomposition' },
]

const frequencyOptions = [
  { value: 'D', label: 'Daily' },
  { value: 'W', label: 'Weekly' },
  { value: 'M', label: 'Monthly' },
]

export function Forecast() {
  const { uploadedFiles, analysisData, setCurrentForecast, setForecasts, currentForecast } = useStore()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedModels, setSelectedModels] = useState<string[]>(['prophet'])
  const [useEnsemble, setUseEnsemble] = useState(false)
  const [ensembleModels, setEnsembleModels] = useState<string[]>(['prophet', 'lightgbm'])
  const [parameters, setParameters] = useState<ModelParameters>({})
  const [showWhatIf, setShowWhatIf] = useState(false)
  const [forecastResult, setForecastResult] = useState<any>(null)
  const [aggConfig, setAggConfig] = useState({
    time_rollup: 'D',
    product_level: 'sku',
    region_level: 'store',
    agg_function: 'sum',
  })

  const [formData, setFormData] = useState({
    name: '',
    targetColumn: analysisData?.validation?.value_column || '',
    dateColumn: analysisData?.validation?.date_column || '',
    frequency: 'D' as 'D' | 'W' | 'M',
    horizon: 30,
    country: '',
    includeMediaPlan: false,
    includePromotions: false,
    includeHolidays: false,
    includeEvents: false,
    includeWeather: false,
    includeCompetitor: false,
    includeEconomic: false,
  })

  const handleModelToggle = (modelValue: string) => {
    setSelectedModels((prev) => {
      if (prev.includes(modelValue)) {
        return prev.filter((m) => m !== modelValue)
      }
      return [...prev, modelValue]
    })
  }

  const handleEnsembleModelToggle = (modelValue: string) => {
    setEnsembleModels((prev) => {
      if (prev.includes(modelValue)) {
        return prev.filter((m) => m !== modelValue)
      }
      return [...prev, modelValue]
    })
  }

  const handleParametersChange = (newParams: ModelParameters) => {
    setParameters(newParams)
  }

  const handleSubmit = async () => {
    if (!formData.name) {
      setError('Please enter a forecast name')
      return
    }

    if (selectedModels.length === 0) {
      setError('Please select at least one model')
      return
    }

    if (useEnsemble && ensembleModels.length < 2) {
      setError('Please select at least 2 models for ensemble')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const request: ForecastRequest = {
        name: formData.name,
        target_column: formData.targetColumn,
        date_column: formData.dateColumn,
        frequency: formData.frequency,
        horizon: formData.horizon,
        models: selectedModels,
        parameters: parameters,
        ensemble_models: useEnsemble ? ensembleModels : undefined,
        ensemble_weights: useEnsemble ? ensembleModels.map(() => 1 / ensembleModels.length) : undefined,
        include_media_plan: formData.includeMediaPlan,
        include_promotions: formData.includePromotions,
        include_holidays: formData.includeHolidays,
        include_events: formData.includeEvents,
        include_weather: formData.includeWeather,
        include_competitor: formData.includeCompetitor,
        include_economic: formData.includeEconomic,
        country: formData.country || undefined,
        aggregation: aggConfig,
      }

      const response = await forecastApi.createForecast(request)
      setCurrentForecast(response.id)

      const forecasts = await forecastApi.listForecasts()
      setForecasts(forecasts)

      const result = await forecastApi.getForecast(response.id)
      setForecastResult(result)
      setShowWhatIf(true)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Forecast failed')
    } finally {
      setIsLoading(false)
    }
  }

  const salesFile = uploadedFiles.find((f) => f.type === 'sales')

  if (!salesFile) {
    return (
      <Box sx={{ textAlign: 'center', py: 8 }}>
        <Typography variant="h5" sx={{ mb: 2 }}>
          No Sales Data Uploaded
        </Typography>
        <Typography color="text.secondary" sx={{ mb: 4 }}>
          Please upload your sales data first before creating a forecast.
        </Typography>
        <Button variant="contained" href="/upload">
          Go to Data Upload
        </Button>
      </Box>
    )
  }

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
          Create Forecast
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Configure and run your forecasting model with external factors
        </Typography>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card sx={{ mb: 3 }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
                Forecast Configuration
              </Typography>

              <Grid container spacing={3}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Forecast Name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g., Q1 2024 Sales Forecast"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth>
                    <InputLabel>Frequency</InputLabel>
                    <Select
                      value={formData.frequency}
                      label="Frequency"
                      onChange={(e) =>
                        setFormData({ ...formData, frequency: e.target.value as 'D' | 'W' | 'M' })
                      }
                    >
                      {frequencyOptions.map((opt) => (
                        <MenuItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Forecast Horizon"
                    value={formData.horizon}
                    onChange={(e) =>
                      setFormData({ ...formData, horizon: parseInt(e.target.value) || 30 })
                    }
                    inputProps={{ min: 1, max: 365 }}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Country (for holidays)"
                    value={formData.country}
                    onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                    placeholder="e.g., US, UK, IN"
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          <Card sx={{ mb: 3 }}>
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  Select Models
                </Typography>
                <Info sx={{ fontSize: 18, color: 'text.secondary' }} />
              </Box>

              <Grid container spacing={2}>
                {modelOptions.map((model) => (
                  <Grid item xs={12} sm={6} key={model.value}>
                    <Card
                      variant="outlined"
                      sx={{
                        cursor: 'pointer',
                        borderColor: selectedModels.includes(model.value)
                          ? 'primary.main'
                          : 'divider',
                        bgcolor: selectedModels.includes(model.value)
                          ? 'primary.lighter'
                          : 'transparent',
                        '&:hover': {
                          borderColor: 'primary.main',
                        },
                      }}
                      onClick={() => handleModelToggle(model.value)}
                    >
                      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                          <Box
                            sx={{
                              width: 20,
                              height: 20,
                              borderRadius: 1,
                              border: '2px solid',
                              borderColor: selectedModels.includes(model.value)
                                ? 'primary.main'
                                : 'divider',
                              bgcolor: selectedModels.includes(model.value)
                                ? 'primary.main'
                                : 'transparent',
                            }}
                          />
                          <Box>
                            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                              {model.label}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {model.description}
                            </Typography>
                          </Box>
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>

              <Box sx={{ mt: 3 }}>
                <FormControlControlLabel
                  control={
                    <Checkbox
                      checked={useEnsemble}
                      onChange={(e) => setUseEnsemble(e.target.checked)}
                    />
                  }
                  label="Create Ensemble (Average of Multiple Models)"
                />

                {useEnsemble && (
                  <Box sx={{ mt: 2, ml: 4 }}>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      Select models for ensemble:
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                      {modelOptions.map((model) => (
                        <Chip
                          key={model.value}
                          label={model.label}
                          onClick={() => handleEnsembleModelToggle(model.value)}
                          color={ensembleModels.includes(model.value) ? 'primary' : 'default'}
                          variant={ensembleModels.includes(model.value) ? 'filled' : 'outlined'}
                        />
                      ))}
                    </Box>
                  </Box>
                )}
              </Box>
            </CardContent>
          </Card>

          <Card sx={{ mb: 3 }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                External Factors
              </Typography>

              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={formData.includeMediaPlan}
                        onChange={(e) =>
                          setFormData({ ...formData, includeMediaPlan: e.target.checked })
                        }
                      />
                    }
                    label="Include Media Plan"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={formData.includePromotions}
                        onChange={(e) =>
                          setFormData({ ...formData, includePromotions: e.target.checked })
                        }
                      />
                    }
                    label="Include Promotions"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={formData.includeHolidays}
                        onChange={(e) =>
                          setFormData({ ...formData, includeHolidays: e.target.checked })
                        }
                      />
                    }
                    label="Include Holidays"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={formData.includeEvents}
                        onChange={(e) =>
                          setFormData({ ...formData, includeEvents: e.target.checked })
                        }
                      />
                    }
                    label="Include Events"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={formData.includeWeather}
                        onChange={(e) =>
                          setFormData({ ...formData, includeWeather: e.target.checked })
                        }
                      />
                    }
                    label="Include Weather"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={formData.includeCompetitor}
                        onChange={(e) =>
                          setFormData({ ...formData, includeCompetitor: e.target.checked })
                        }
                      />
                    }
                    label="Include Competitor Data"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={formData.includeEconomic}
                        onChange={(e) =>
                          setFormData({ ...formData, includeEconomic: e.target.checked })
                        }
                      />
                    }
                    label="Include Economic Indicators"
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          <ParametersPanel
            selectedModels={selectedModels}
            parameters={parameters}
            onChange={handleParametersChange}
          />

          <AggregationPanel
            config={aggConfig}
            onChange={setAggConfig}
            hasHierarchy={!!analysisData?.hierarchy}
          />
        </Grid>

        <Grid item xs={12} md={4}>
          <Card sx={{ position: 'sticky', top: 16 }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                Summary
              </Typography>

              <Box sx={{ mb: 3 }}>
                <Typography variant="body2" color="text.secondary">
                  Selected Models
                </Typography>
                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 1 }}>
                  {selectedModels.map((m) => (
                    <Chip key={m} label={m.toUpperCase()} size="small" />
                  ))}
                </Box>
              </Box>

              {useEnsemble && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="body2" color="text.secondary">
                    Ensemble Models
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 1 }}>
                    {ensembleModels.map((m) => (
                      <Chip key={m} label={m.toUpperCase()} size="small" color="secondary" />
                    ))}
                  </Box>
                </Box>
              )}

              <Box sx={{ mb: 3 }}>
                <Typography variant="body2" color="text.secondary">
                  External Factors
                </Typography>
                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 1 }}>
                  {formData.includeMediaPlan && <Chip label="Media" size="small" variant="outlined" />}
                  {formData.includePromotions && <Chip label="Promo" size="small" variant="outlined" />}
                  {formData.includeHolidays && <Chip label="Holidays" size="small" variant="outlined" />}
                  {formData.includeEvents && <Chip label="Events" size="small" variant="outlined" />}
                  {formData.includeWeather && <Chip label="Weather" size="small" variant="outlined" />}
                  {formData.includeCompetitor && <Chip label="Competitor" size="small" variant="outlined" />}
                  {formData.includeEconomic && <Chip label="Economic" size="small" variant="outlined" />}
                </Box>
              </Box>

              <Box sx={{ mb: 3 }}>
                <Typography variant="body2" color="text.secondary">
                  Data Files
                </Typography>
                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 1 }}>
                  {uploadedFiles.map((f) => (
                    <Chip key={f.file_id} label={f.type} size="small" variant="outlined" />
                  ))}
                </Box>
              </Box>

              {error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {error}
                </Alert>
              )}

              <Button
                fullWidth
                variant="contained"
                size="large"
                startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : <PlayArrow />}
                onClick={handleSubmit}
                disabled={isLoading}
              >
                {isLoading ? 'Running Forecast...' : 'Run Forecast'}
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {showWhatIf && forecastResult && (
        <WhatIfSimulator
          open={showWhatIf}
          onClose={() => setShowWhatIf(false)}
          forecastResult={forecastResult}
        />
      )}
    </Box>
  )
}

function FormControlControlLabel({ control, label }: { control: any; label: string }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center' }}>
      {control}
      <Typography sx={{ ml: 1 }}>{label}</Typography>
    </Box>
  )
}

function Checkbox({ checked, onChange }: { checked: boolean; onChange: (e: any) => void }) {
  return (
    <input
      type="checkbox"
      checked={checked}
      onChange={onChange}
      style={{ width: 18, height: 18, cursor: 'pointer' }}
    />
  )
}
