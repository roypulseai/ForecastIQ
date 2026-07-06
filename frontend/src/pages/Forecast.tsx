import { useState } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Checkbox,
  FormControlLabel,
  Chip,
  Alert,
  CircularProgress,
} from '@mui/material'
import { PlayArrow, Info } from '@mui/icons-material'
import { forecastApi, ForecastRequest } from '../services/api'
import { useStore } from '../store/appStore'

const modelOptions = [
  { value: 'arima', label: 'ARIMA', description: 'AutoRegressive Integrated Moving Average' },
  { value: 'sarimax', label: 'SARIMAX', description: 'Seasonal ARIMAX with exogenous variables' },
  { value: 'prophet', label: 'Prophet', description: 'Facebook\'s time series forecasting' },
  { value: 'lightgbm', label: 'LightGBM', description: 'Gradient boosting for time series' },
  { value: 'wma', label: 'WMA', description: 'Weighted Moving Average' },
]

const frequencyOptions = [
  { value: 'D', label: 'Daily' },
  { value: 'W', label: 'Weekly' },
  { value: 'M', label: 'Monthly' },
]

export function Forecast() {
  const { uploadedFiles, analysisData, setCurrentForecast, setForecasts } = useStore()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedModels, setSelectedModels] = useState<string[]>(['prophet'])
  const [useEnsemble, setUseEnsemble] = useState(false)
  const [ensembleModels, setEnsembleModels] = useState<string[]>(['prophet', 'lightgbm'])

  const [formData, setFormData] = useState({
    name: '',
    targetColumn: analysisData?.validation?.value_column || '',
    dateColumn: analysisData?.validation?.date_column || '',
    frequency: 'D' as 'D' | 'W' | 'M',
    horizon: 30,
    seasonalityMode: 'additive' as 'additive' | 'multiplicative',
    country: '',
    includeMediaPlan: false,
    includePromotions: false,
    includeHolidays: false,
    includeEvents: false,
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
        ensemble_models: useEnsemble ? ensembleModels : undefined,
        ensemble_weights: useEnsemble ? ensembleModels.map(() => 1 / ensembleModels.length) : undefined,
        include_media_plan: formData.includeMediaPlan,
        include_promotions: formData.includePromotions,
        include_holidays: formData.includeHolidays,
        include_events: formData.includeEvents,
        seasonality_mode: formData.seasonalityMode,
        country: formData.country || undefined,
      }

      const response = await forecastApi.createForecast(request)
      setCurrentForecast(response.id)

      const forecasts = await forecastApi.listForecasts()
      setForecasts(forecasts)

      window.location.href = '/results'
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
          Configure and run your forecasting model
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
                  <FormControl fullWidth>
                    <InputLabel>Seasonality Mode</InputLabel>
                    <Select
                      value={formData.seasonalityMode}
                      label="Seasonality Mode"
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          seasonalityMode: e.target.value as 'additive' | 'multiplicative',
                        })
                      }
                    >
                      <MenuItem value="additive">Additive</MenuItem>
                      <MenuItem value="multiplicative">Multiplicative</MenuItem>
                    </Select>
                  </FormControl>
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
                          <Checkbox
                            checked={selectedModels.includes(model.value)}
                            sx={{ p: 0 }}
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
                <FormControlLabel
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

          <Card>
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
              </Grid>
            </CardContent>
          </Card>
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
    </Box>
  )
}
