import * as React from 'react'
import { Box, Card, CardContent, Typography, Grid, alpha } from '@mui/material'
import { 
  TrendingUp, TrendingDown, CalendarMonth, Warning, 
  CheckCircle, Speed, Insights 
} from '@mui/icons-material'
import type { SvgIconProps } from '@mui/material'

interface DataCharacteristics {
  length: number
  mean: number
  std: number
  cv: number
  trend: string
  seasonality: string
  stationarity: boolean
  outliers_pct: number
  missing_pct: number
}

interface ModelRecommendation {
  model: string
  score: number
  reason: string
}

interface DataAnalysisProps {
  characteristics: DataCharacteristics | null
  recommendations: ModelRecommendation[]
}

const StatCard = ({ 
  icon, 
  title, 
  value, 
  subtitle, 
  color 
}: { 
  icon: React.ReactElement<SvgIconProps>
  title: string
  value: string | number
  subtitle?: string
  color: string 
}) => (
  <Card sx={{ height: '100%' }}>
    <CardContent sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            {title}
          </Typography>
          <Typography variant="h4" sx={{ fontWeight: 700, color: 'text.primary' }}>
            {value}
          </Typography>
          {subtitle && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
              {subtitle}
            </Typography>
          )}
        </Box>
        <Box
          sx={{
            width: 48,
            height: 48,
            borderRadius: 2,
            bgcolor: alpha(color, 0.1),
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {icon}
        </Box>
      </Box>
    </CardContent>
  </Card>
)

export function DataAnalysis({ characteristics, recommendations }: DataAnalysisProps) {
  if (!characteristics) {
    return (
      <Card sx={{ height: '100%' }}>
        <CardContent sx={{ p: 4, textAlign: 'center' }}>
          <Insights sx={{ fontSize: 48, color: 'text.disabled', mb: 2 }} />
          <Typography color="text.secondary">
            Upload data to see analysis
          </Typography>
        </CardContent>
      </Card>
    )
  }

  const getTrendIcon = (color: string): React.ReactElement<SvgIconProps> => {
    if (characteristics.trend === 'increasing') return <TrendingUp sx={{ color, fontSize: 24 }} />
    if (characteristics.trend === 'decreasing') return <TrendingDown sx={{ color, fontSize: 24 }} />
    return <TrendingUp sx={{ color, fontSize: 24 }} />
  }

  return (
    <Box>
      <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
        Data Analysis
      </Typography>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            icon={<CalendarMonth sx={{ color: '#1976d2', fontSize: 24 }} />}
            title="Data Points"
            value={characteristics.length.toLocaleString()}
            subtitle={`${characteristics.missing_pct.toFixed(1)}% missing`}
            color="#1976d2"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            icon={getTrendIcon(characteristics.trend === 'increasing' ? '#2e7d32' : characteristics.trend === 'decreasing' ? '#d32f2f' : '#1976d2')}
            title="Trend"
            value={characteristics.trend.charAt(0).toUpperCase() + characteristics.trend.slice(1)}
            subtitle={`CV: ${characteristics.cv.toFixed(2)}`}
            color={characteristics.trend === 'increasing' ? '#2e7d32' : characteristics.trend === 'decreasing' ? '#d32f2f' : '#1976d2'}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            icon={characteristics.stationarity 
              ? <CheckCircle sx={{ color: '#2e7d32', fontSize: 24 }} />
              : <Warning sx={{ color: '#ed6c02', fontSize: 24 }} />
            }
            title="Stationarity"
            value={characteristics.stationarity ? 'Stationary' : 'Non-stationary'}
            subtitle={`Outliers: ${characteristics.outliers_pct.toFixed(1)}%`}
            color={characteristics.stationarity ? '#2e7d32' : '#ed6c02'}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            icon={<Speed sx={{ color: '#7b1fa2', fontSize: 24 }} />}
            title="Seasonality"
            value={characteristics.seasonality === 'none' ? 'Not Detected' : characteristics.seasonality}
            subtitle={`Mean: ${characteristics.mean.toFixed(2)}`}
            color="#7b1fa2"
          />
        </Grid>
      </Grid>

      <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
        Recommended Models
      </Typography>

      <Grid container spacing={2}>
        {recommendations.map((rec, index) => (
          <Grid item xs={12} md={6} key={rec.model}>
            <Card
              sx={{
                cursor: 'pointer',
                transition: 'all 0.2s',
                border: '2px solid',
                borderColor: index === 0 ? 'primary.main' : 'transparent',
                '&:hover': {
                  borderColor: 'primary.light',
                  transform: 'translateY(-2px)',
                },
              }}
            >
              <CardContent sx={{ p: 2.5 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Box
                      sx={{
                        width: 36,
                        height: 36,
                        borderRadius: '50%',
                        bgcolor: index === 0 ? 'primary.main' : 'grey.300',
                        color: 'white',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontWeight: 700,
                        fontSize: '0.875rem',
                      }}
                    >
                      {index + 1}
                    </Box>
                    <Box>
                      <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                        {rec.model.toUpperCase()}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {rec.reason}
                      </Typography>
                    </Box>
                  </Box>
                  <Box
                    sx={{
                      px: 1.5,
                      py: 0.5,
                      borderRadius: 1,
                      bgcolor: alpha('#2e7d32', 0.1),
                    }}
                  >
                    <Typography variant="caption" sx={{ color: 'success.main', fontWeight: 600 }}>
                      {(rec.score * 100).toFixed(0)}%
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  )
}
