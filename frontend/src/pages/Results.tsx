import { useEffect, useState } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
  Alert,
  Tabs,
  Tab,
  Button,
} from '@mui/material'
import { Download, Refresh } from '@mui/icons-material'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { Line } from 'react-chartjs-2'
import { forecastApi, ForecastResult } from '../services/api'
import { useStore } from '../store/appStore'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

const colors = ['#1976d2', '#dc004e', '#2e7d32', '#ed6c02', '#7b1fa2', '#00acc1']

export function Results() {
  const { currentForecast, forecasts } = useStore()
  const [forecastData, setForecastData] = useState<ForecastResult | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedModel, setSelectedModel] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState(0)

  useEffect(() => {
    const loadForecast = async () => {
      const forecastId = currentForecast || (forecasts.length > 0 ? forecasts[0].forecast_id : null)

      if (!forecastId) {
        setError('No forecast found. Please create a forecast first.')
        setIsLoading(false)
        return
      }

      try {
        const data = await forecastApi.getForecast(forecastId)
        setForecastData(data)
        const firstModel = Object.keys(data.results)[0]
        setSelectedModel(firstModel || null)
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load forecast')
      } finally {
        setIsLoading(false)
      }
    }

    loadForecast()
  }, [currentForecast, forecasts])

  const handleRefresh = async () => {
    setIsLoading(true)
    try {
      const forecastsList = await forecastApi.listForecasts()
      if (forecastsList.length > 0) {
        const data = await forecastApi.getForecast(forecastsList[0].forecast_id)
        setForecastData(data)
        const firstModel = Object.keys(data.results)[0]
        setSelectedModel(firstModel || null)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to refresh')
    } finally {
      setIsLoading(false)
    }
  }

  if (isLoading) {
    return (
      <Box sx={{ textAlign: 'center', py: 8 }}>
        <CircularProgress sx={{ mb: 2 }} />
        <Typography>Loading forecast results...</Typography>
      </Box>
    )
  }

  if (error || !forecastData) {
    return (
      <Box sx={{ textAlign: 'center', py: 8 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error || 'No forecast data available'}
        </Alert>
        <Button variant="contained" href="/forecast">
          Create New Forecast
        </Button>
      </Box>
    )
  }

  const selectedData = selectedModel && forecastData.results[selectedModel]
  const ensembleData = forecastData.ensemble

  const chartData = {
    labels: selectedData?.forecast_values.map((v) => v.date) || [],
    datasets: [
      {
        label: selectedModel?.toUpperCase() || '',
        data: selectedData?.forecast_values.map((v) => v.forecast) || [],
        borderColor: colors[0],
        backgroundColor: `${colors[0]}20`,
        fill: true,
        tension: 0.4,
      },
      ...(ensembleData
        ? [
            {
              label: 'ENSEMBLE',
              data: ensembleData.forecast_values.map((v) => v.forecast),
              borderColor: colors[1],
              backgroundColor: `${colors[1]}20`,
              fill: true,
              tension: 0.4,
            },
          ]
        : []),
    ],
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: false,
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
      },
    },
    interaction: {
      mode: 'nearest' as const,
      axis: 'x' as const,
      intersect: false,
    },
  }

  const allDates = new Set([
    ...(selectedData?.forecast_values.map((v) => v.date) || []),
    ...(ensembleData?.forecast_values.map((v) => v.date) || []),
  ])
  const sortedDates = Array.from(allDates).sort()

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
            {forecastData.name}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Created: {new Date(forecastData.created_at).toLocaleString()}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button variant="outlined" startIcon={<Refresh />} onClick={handleRefresh}>
            Refresh
          </Button>
          <Button variant="contained" startIcon={<Download />}>
            Export CSV
          </Button>
        </Box>
      </Box>

      <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)} sx={{ mb: 3 }}>
        <Tab label="Forecast Chart" />
        <Tab label="Model Comparison" />
        <Tab label="Detailed Results" />
      </Tabs>

      {activeTab === 0 && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Card>
              <CardContent sx={{ p: 3 }}>
                <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
                  {Object.keys(forecastData.results).map((model, idx) => (
                    <Chip
                      key={model}
                      label={model.toUpperCase()}
                      onClick={() => setSelectedModel(model)}
                      color={selectedModel === model ? 'primary' : 'default'}
                      sx={{ cursor: 'pointer' }}
                    />
                  ))}
                  {ensembleData && (
                    <Chip
                      label="ENSEMBLE"
                      onClick={() => setSelectedModel('ensemble')}
                      color="secondary"
                      sx={{ cursor: 'pointer' }}
                    />
                  )}
                </Box>
                <Box sx={{ height: 400 }}>
                  <Line data={chartData} options={chartOptions} />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {activeTab === 1 && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Card>
              <CardContent sx={{ p: 0 }}>
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Model</TableCell>
                        <TableCell align="right">MAE</TableCell>
                        <TableCell align="right">RMSE</TableCell>
                        <TableCell align="right">MAPE (%)</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {Object.entries(forecastData.results).map(([model, result]) => (
                        <TableRow
                          key={model}
                          hover
                          onClick={() => setSelectedModel(model)}
                          sx={{ cursor: 'pointer' }}
                        >
                          <TableCell>
                            <Chip label={model.toUpperCase()} size="small" />
                          </TableCell>
                          <TableCell align="right">
                            {result.metrics.mae?.toFixed(2) || 'N/A'}
                          </TableCell>
                          <TableCell align="right">
                            {result.metrics.rmse?.toFixed(2) || 'N/A'}
                          </TableCell>
                          <TableCell align="right">
                            {result.metrics.mape?.toFixed(2) || 'N/A'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {activeTab === 2 && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Card>
              <CardContent sx={{ p: 0 }}>
                <TableContainer sx={{ maxHeight: 600 }}>
                  <Table stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell>Date</TableCell>
                        {Object.keys(forecastData.results).map((m) => (
                          <TableCell key={m} align="right">
                            {m.toUpperCase()}
                          </TableCell>
                        ))}
                        {ensembleData && (
                          <TableCell align="right" sx={{ bgcolor: 'secondary.lighter' }}>
                            ENSEMBLE
                          </TableCell>
                        )}
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {sortedDates.map((date) => (
                        <TableRow key={date}>
                          <TableCell sx={{ fontWeight: 500 }}>{date}</TableCell>
                          {Object.entries(forecastData.results).map(([model, result]) => {
                            const value = result.forecast_values.find((v) => v.date === date)
                            return (
                              <TableCell key={model} align="right">
                                {value?.forecast.toFixed(2) || 'N/A'}
                              </TableCell>
                            )
                          })}
                          {ensembleData && (
                            <TableCell
                              align="right"
                              sx={{ fontWeight: 600, bgcolor: 'secondary.lighter' }}
                            >
                              {ensembleData.forecast_values.find((v) => v.date === date)?.forecast.toFixed(2) || 'N/A'}
                            </TableCell>
                          )}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Box>
  )
}
