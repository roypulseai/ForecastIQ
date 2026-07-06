import * as React from 'react'
import { useState, useEffect } from 'react'
import { Box, Typography, Card, CardContent, Grid, Button, alpha, CircularProgress } from '@mui/material'
import { Link as RouterLink } from 'react-router-dom'
import { BarChart, TrendingUp, Speed, AutoAwesome, ArrowForward } from '@mui/icons-material'
import { DataAnalysis } from '../components/forecast/DataAnalysis'
import { useStore } from '../store/appStore'

const features = [
  {
    icon: TrendingUp,
    title: 'Multiple Models',
    description: 'ARIMA, SARIMAX, Prophet, LightGBM, and WMA with auto-selection',
    color: '#1976d2',
  },
  {
    icon: Speed,
    title: 'Auto Model Selection',
    description: 'AI-powered model recommendations based on your data patterns',
    color: '#7b1fa2',
  },
  {
    icon: AutoAwesome,
    title: 'Ensemble Methods',
    description: 'Combine 2-3 models with weighted averaging for better accuracy',
    color: '#2e7d32',
  },
]

export function Dashboard() {
  const { uploadedFiles, forecasts } = useStore()
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const timer = setTimeout(() => setIsLoading(false), 500)
    return () => clearTimeout(timer)
  }, [])

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
          Welcome to ForecastIQ
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Advanced time series forecasting with ML-powered model selection and ensemble methods
        </Typography>
      </Box>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%', bgcolor: alpha('#1976d2', 0.05), border: 'none' }}>
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                <Box
                  sx={{
                    width: 48,
                    height: 48,
                    borderRadius: 2,
                    bgcolor: alpha('#1976d2', 0.1),
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <BarChart sx={{ color: '#1976d2' }} />
                </Box>
                <Box>
                  <Typography variant="h3" sx={{ fontWeight: 700 }}>
                    {isLoading ? <CircularProgress size={24} /> : uploadedFiles.length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Data Files Uploaded
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%', bgcolor: alpha('#2e7d32', 0.05), border: 'none' }}>
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                <Box
                  sx={{
                    width: 48,
                    height: 48,
                    borderRadius: 2,
                    bgcolor: alpha('#2e7d32', 0.1),
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <TrendingUp sx={{ color: '#2e7d32' }} />
                </Box>
                <Box>
                  <Typography variant="h3" sx={{ fontWeight: 700 }}>
                    {isLoading ? <CircularProgress size={24} /> : forecasts.length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Forecasts Generated
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%', bgcolor: alpha('#7b1fa2', 0.05), border: 'none' }}>
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                <Box
                  sx={{
                    width: 48,
                    height: 48,
                    borderRadius: 2,
                    bgcolor: alpha('#7b1fa2', 0.1),
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <AutoAwesome sx={{ color: '#7b1fa2' }} />
                </Box>
                <Box>
                  <Typography variant="h3" sx={{ fontWeight: 700 }}>
                    5+
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    ML Models Available
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
        Key Features
      </Typography>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        {features.map((feature) => {
          const Icon = feature.icon
          return (
            <Grid item xs={12} md={4} key={feature.title}>
              <Card sx={{ height: '100%' }}>
                <CardContent sx={{ p: 3 }}>
                  <Box
                    sx={{
                      width: 48,
                      height: 48,
                      borderRadius: 2,
                      bgcolor: alpha(feature.color, 0.1),
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      mb: 2,
                    }}
                  >
                    {React.createElement(Icon, { sx: { color: feature.color, fontSize: 24 } })}
                  </Box>
                  <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
                    {feature.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {feature.description}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          )
        })}
      </Grid>

      <Box sx={{ display: 'flex', gap: 2 }}>
        <Button
          variant="contained"
          component={RouterLink}
          to="/upload"
          endIcon={<ArrowForward />}
          size="large"
        >
          Upload Your Data
        </Button>
        <Button
          variant="outlined"
          component={RouterLink}
          to="/forecast"
          size="large"
        >
          Create Forecast
        </Button>
      </Box>
    </Box>
  )
}
