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
import { Download, Refresh, TrendingUp, ShowChart } from '@mui/icons-material'
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
  const [showBaseline, setShowBaseline] = useState(true)

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

  const selectedData = selectedModel ? forecastData.results[selectedModel] : null
  const ensembleData = forecastData.ensemble

  const chartDatasets = []

  if (selectedData) {
    chartDatasets.push({
      label: `${selectedModel?.toUpperCase()} Forecast`,
      data: selectedData.forecast_values.map((v) => v.forecast),
      borderColor: colors[0],
      backgroundColor: `${colors[0]}20`,
      fill: true,
      tension: 0.4,
    })

    if (showBaseline && selectedData.baseline_values) {
      chartDatasets.push({
        label: 'Baseline (Trend)',
        data: selectedData.baseline_values.map((v) => v.forecast),
        borderColor: colors[1],
        backgroundColor: `${colors[1]}10`,
        borderDash: [5, 5],
        fill: false,
        tension: 0.4,
      })
    }

    if (showBaseline && selectedData.forecast_values.some(v => v.uplift !== undefined)) {
      const upliftData = selectedData.forecast_values.map((v) => v.uplift || 0)
      chartDatasets.push({
        label: 'Uplift %',
        data: upliftData,
        borderColor: colors[2],
        backgroundColor: `${colors[2]}20`,
        yAxisID: 'y1',
        fill: true,
        tension: 0.4,
      })
    }
  }

  if (ensembleData) {
    chartDatasets.push({
      label: 'ENSEMBLE Forecast',
      data: ensembleData.forecast_values.map((v) => v.forecast),
      borderColor: colors[3],
      backgroundColor: `${colors[3]}20`,
      fill: true,
      tension: 0.4,
    })

    if (showBaseline && ensembleData.baseline_values) {
      chartDatasets.push({
        label: 'ENSEMBLE Baseline',
        data: ensembleData.baseline_values.map((v) => v.forecast),
        borderColor: colors[4],
        backgroundColor: `${colors[4]}10`,
        borderDash: [5, 5],
        fill: false,
        tension: 0.4,
      })
    }
  }

  const chartData = {
    labels: selectedData?.forecast_values.map((v) => v.date) || [],
    datasets: chartDatasets,
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
        type: 'linear' as const,
        display: true,
        position: 'left' as const,
        beginAtZero: true,
        title: {
          display: true,
          text: 'Forecast Value',
        },
      },
      y1: {
        type: 'linear' as const,
        display: showBaseline && selectedData?.forecast_values.some(v => v.uplift !== undefined),
        position: 'right' as const,
        beginAtZero: true,
        title: {
          display: true,
          text: 'Uplift %',
        },
        grid: {
          drawOnChartArea: false,
        },
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
        <Tab label="Baseline vs Forecast" />
        <Tab label="Model Comparison" />
        <Tab label="Detailed Results" />
      </Tabs>

      {activeTab === 0 && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Card>
              <CardContent sx={{ p: 3 }}>
                <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap', alignItems: 'center' }}>
                  <Box sx={{ display: 'flex', gap: 1 }}>
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
                  <Box sx={{ flex: 1 }} />
                  <Chip
                    icon={<ShowChart />}
                    label={showBaseline ? 'Hide Baseline' : 'Show Baseline'}
                    onClick={() => setShowBaseline(!showBaseline)}
                    color={showBaseline ? 'primary' : 'default'}
                    variant={showBaseline ? 'filled' : 'outlined'}
                  />
                </Box>
                <Box sx={{ height: 450 }}>
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
              <CardContent sx={{ p: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                  <TrendingUp sx={{ color: 'primary.main' }} />
                  <Box>
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      Baseline vs Forecast Analysis
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Compare baseline trend (without external factors) vs. full forecast (with promotions, media, etc.)
                    </Typography>
                  </Box>
                </Box>
                <TableContainer sx={{ maxHeight: 500 }}>
                  <Table stickyHeader size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 600 }}>Date</TableCell>
                        {Object.keys(forecastData.results).map((model) => (
                          <TableCell key={model} align="center" colSpan={3}>
                            <Chip label={model.toUpperCase()} size="small" />
                          </TableCell>
                        ))}
                      </TableRow>
                      <TableRow>
                        <TableCell />
                        {Object.keys(forecastData.results).map(() => (
                          <>
                            <TableCell key={`${Math.random()}-baseline`} align="right" sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
                              Baseline
                            </TableCell>
                            <TableCell key={`${Math.random()}-forecast`} align="right" sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
                              Forecast
                            </TableCell>
                            <TableCell key={`${Math.random()}-uplift`} align="right" sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
                              Uplift %
                            </TableCell>
                          </>
                        ))}
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {sortedDates.slice(0, 30).map((date) => (
                        <TableRow key={date}>
                          <TableCell sx={{ fontWeight: 500 }}>{date}</TableCell>
                          {Object.entries(forecastData.results).map(([model, result]) => {
                            const forecast = result.forecast_values.find((v) => v.date === date)
                            const baseline = result.baseline_values?.find((v) => v.date === date)
                            return (
                              <>
                                <TableCell key={`${model}-baseline`} align="right">
                                  {baseline?.forecast.toFixed(2) || '-'}
                                </TableCell>
                                <TableCell key={`${model}-forecast`} align="right" sx={{ fontWeight: 600 }}>
                                  {forecast?.forecast.toFixed(2) || '-'}
                                </TableCell>
                                <TableCell
                                  key={`${model}-uplift`}
                                  align="right"
                                  sx={{
                                    color: (forecast?.uplift || 0) > 0 ? 'success.main' : (forecast?.uplift || 0) < 0 ? 'error.main' : 'text.secondary',
                                    fontWeight: 600,
                                  }}
                                >
                                  {forecast?.uplift ? `${forecast.uplift > 0 ? '+' : ''}${forecast.uplift.toFixed(1)}%` : '-'}
                                </TableCell>
                              </>
                            )
                          })}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
                {sortedDates.length > 30 && (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 2, textAlign: 'center' }}>
                    Showing first 30 rows of {sortedDates.length} total forecasts
                  </Typography>
                )}
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

      {activeTab === 3 && (
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
