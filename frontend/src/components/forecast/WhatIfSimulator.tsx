import { useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  TextField,
  Slider,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  LinearProgress,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
} from '@mui/material'
import { Close, TrendingUp, ShowChart } from '@mui/icons-material'
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

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

interface WhatIfSimulatorProps {
  open: boolean
  onClose: () => void
  forecastResult: any
}

interface Scenario {
  name: string
  type: 'promo' | 'media' | 'price' | 'holiday'
  parameters: any
  results?: any[]
}

export function WhatIfSimulator({ open, onClose, forecastResult }: WhatIfSimulatorProps) {
  const [activeTab, setActiveTab] = useState(0)
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [promoParams, setPromoParams] = useState({ discount: 20, duration: 7, elasticity: -1.5 })
  const [mediaParams, setMediaParams] = useState({ channel: 'digital', spendIncrease: 50, duration: 30 })
  const [priceParams, setPriceParams] = useState({ changePct: -10, promoDepth: 15, duration: 14 })

  const getBaselineForecast = () => {
    if (!forecastResult?.results) return []
    
    const firstModel = Object.keys(forecastResult.results)[0]
    const modelResult = forecastResult.results[firstModel]
    return modelResult?.forecast_values || []
  }

  const simulatePromo = () => {
    const baseline = getBaselineForecast()
    const results = []
    
    for (let i = 0; i < baseline.length; i++) {
      const val = baseline[i]
      let uplift = 1.0
      
      if (i < promoParams.duration) {
        uplift = 1 + promoParams.elasticity * (promoParams.discount / 100)
        uplift = Math.max(0.5, Math.min(2.0, uplift))
      }
      
      results.push({
        date: val.date,
        baseline: val.baseline || val.forecast,
        forecast: val.forecast,
        simulated: val.forecast * uplift,
        upliftPct: (uplift - 1) * 100
      })
    }
    
    const newScenario: Scenario = {
      name: `Promo: ${promoParams.discount}% off`,
      type: 'promo',
      parameters: { ...promoParams },
      results
    }
    
    setScenarios([...scenarios.filter(s => s.type !== 'promo'), newScenario])
    setActiveTab(3)
  }

  const simulateMedia = () => {
    const baseline = getBaselineForecast()
    const results = []
    
    const channelRoi: Record<string, number> = {
      tv: 1.5, digital: 1.2, social: 0.8, print: 0.5, radio: 0.6
    }
    const roi = channelRoi[mediaParams.channel] || 1.0
    const spendMultiplier = 1 + (mediaParams.spendIncrease / 100) * roi
    
    for (let i = 0; i < baseline.length; i++) {
      const val = baseline[i]
      let effect = 1.0
      
      if (i < mediaParams.duration) {
        const decay = Math.exp(-i / 10)
        effect = 1 + ((spendMultiplier - 1) * decay)
      }
      
      results.push({
        date: val.date,
        baseline: val.baseline || val.forecast,
        forecast: val.forecast,
        simulated: val.forecast * effect,
        effectPct: (effect - 1) * 100
      })
    }
    
    const newScenario: Scenario = {
      name: `Media: ${mediaParams.channel} +${mediaParams.spendIncrease}%`,
      type: 'media',
      parameters: { ...mediaParams },
      results
    }
    
    setScenarios([...scenarios.filter(s => s.type !== 'media'), newScenario])
    setActiveTab(3)
  }

  const simulatePrice = () => {
    const baseline = getBaselineForecast()
    const results = []
    
    const elasticity = -1.5
    const priceEffect = 1 + (priceParams.changePct / 100) * elasticity
    const promoEffect = 1 + (priceParams.promoDepth / 100) * 0.5
    const totalEffect = priceEffect * promoEffect
    
    for (let i = 0; i < baseline.length; i++) {
      const val = baseline[i]
      let effect = 1.0
      
      if (i < priceParams.duration) {
        effect = totalEffect
      }
      
      results.push({
        date: val.date,
        baseline: val.baseline || val.forecast,
        forecast: val.forecast,
        simulated: val.forecast * effect,
        effectPct: (effect - 1) * 100
      })
    }
    
    const newScenario: Scenario = {
      name: `Price: ${priceParams.changePct}% + ${priceParams.promoDepth}% promo`,
      type: 'price',
      parameters: { ...priceParams },
      results
    }
    
    setScenarios([...scenarios.filter(s => s.type !== 'price'), newScenario])
    setActiveTab(3)
  }

  const chartData = {
    labels: getBaselineForecast().slice(0, 30).map((v: any) => v.date),
    datasets: [
      {
        label: 'Baseline',
        data: getBaselineForecast().slice(0, 30).map((v: any) => v.baseline || v.forecast),
        borderColor: '#94a3b8',
        backgroundColor: '#94a3b820',
        fill: false,
        tension: 0.4,
      },
      {
        label: 'Forecast',
        data: getBaselineForecast().slice(0, 30).map((v: any) => v.forecast),
        borderColor: '#1976d2',
        backgroundColor: '#1976d220',
        fill: true,
        tension: 0.4,
      },
      ...scenarios.map((s, idx) => ({
        label: s.name,
        data: (s.results || []).slice(0, 30).map((r: any) => r.simulated),
        borderColor: ['#dc004e', '#2e7d32', '#ed6c02', '#7b1fa2'][idx % 4],
        backgroundColor: 'transparent',
        borderDash: [5, 5],
        fill: false,
        tension: 0.4,
      }))
    ]
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top' as const },
    },
    scales: {
      y: { beginAtZero: true, title: { display: true, text: 'Forecast Value' } }
    }
  }

  const comparisonData = scenarios.map(s => {
    const totalBaseline = (s.results || []).reduce((sum: number, r: any) => sum + r.baseline, 0)
    const totalSimulated = (s.results || []).reduce((sum: number, r: any) => sum + r.simulated, 0)
    const totalImpact = totalSimulated - totalBaseline
    const avgImpact = (totalImpact / totalBaseline) * 100
    
    return {
      name: s.name,
      totalBaseline,
      totalSimulated,
      totalImpact,
      avgImpact,
      peakImpact: Math.max(...(s.results || []).map((r: any) => r.effectPct || r.upliftPct || 0))
    }
  })

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <ShowChart sx={{ color: 'primary.main' }} />
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              What-If Scenario Simulator
            </Typography>
          </Box>
          <Button onClick={onClose} startIcon={<Close />}>
            Close
          </Button>
        </Box>
      </DialogTitle>
      
      <DialogContent>
        <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)} sx={{ mb: 3 }}>
          <Tab label="Promotion" />
          <Tab label="Media Spend" />
          <Tab label="Price Change" />
          <Tab label="Results" />
        </Tabs>

        {activeTab === 0 && (
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 2 }}>
              Simulate Promotion Impact
            </Typography>
            <Grid container spacing={3}>
              <Grid item xs={12} sm={4}>
                <Box sx={{ px: 2 }}>
                  <Typography variant="caption" gutterBottom>
                    Discount: {promoParams.discount}%
                  </Typography>
                  <Slider
                    value={promoParams.discount}
                    min={0}
                    max={50}
                    step={5}
                    onChange={(_, v) => setPromoParams({ ...promoParams, discount: v as number })}
                  />
                </Box>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Box sx={{ px: 2 }}>
                  <Typography variant="caption" gutterBottom>
                    Duration: {promoParams.duration} days
                  </Typography>
                  <Slider
                    value={promoParams.duration}
                    min={1}
                    max={30}
                    step={1}
                    onChange={(_, v) => setPromoParams({ ...promoParams, duration: v as number })}
                  />
                </Box>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Box sx={{ px: 2 }}>
                  <Typography variant="caption" gutterBottom>
                    Elasticity: {promoParams.elasticity}
                  </Typography>
                  <Slider
                    value={promoParams.elasticity}
                    min={-3}
                    max={-0.5}
                    step={0.1}
                    onChange={(_, v) => setPromoParams({ ...promoParams, elasticity: v as number })}
                  />
                </Box>
              </Grid>
            </Grid>
            <Button variant="contained" onClick={simulatePromo} sx={{ mt: 2 }}>
              Run Simulation
            </Button>
          </Box>
        )}

        {activeTab === 1 && (
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 2 }}>
              Simulate Media Spend Impact
            </Typography>
            <Grid container spacing={3}>
              <Grid item xs={12} sm={4}>
                <TextField
                  fullWidth
                  select
                  label="Channel"
                  value={mediaParams.channel}
                  onChange={(e) => setMediaParams({ ...mediaParams, channel: e.target.value })}
                >
                  <MenuItem value="tv">TV</MenuItem>
                  <MenuItem value="digital">Digital</MenuItem>
                  <MenuItem value="social">Social</MenuItem>
                  <MenuItem value="print">Print</MenuItem>
                  <MenuItem value="radio">Radio</MenuItem>
                </TextField>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Box sx={{ px: 2 }}>
                  <Typography variant="caption" gutterBottom>
                    Spend Increase: +{mediaParams.spendIncrease}%
                  </Typography>
                  <Slider
                    value={mediaParams.spendIncrease}
                    min={0}
                    max={200}
                    step={10}
                    onChange={(_, v) => setMediaParams({ ...mediaParams, spendIncrease: v as number })}
                  />
                </Box>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Box sx={{ px: 2 }}>
                  <Typography variant="caption" gutterBottom>
                    Duration: {mediaParams.duration} days
                  </Typography>
                  <Slider
                    value={mediaParams.duration}
                    min={7}
                    max={90}
                    step={7}
                    onChange={(_, v) => setMediaParams({ ...mediaParams, duration: v as number })}
                  />
                </Box>
              </Grid>
            </Grid>
            <Button variant="contained" onClick={simulateMedia} sx={{ mt: 2 }}>
              Run Simulation
            </Button>
          </Box>
        )}

        {activeTab === 2 && (
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 2 }}>
              Simulate Price Change Impact
            </Typography>
            <Grid container spacing={3}>
              <Grid item xs={12} sm={4}>
                <Box sx={{ px: 2 }}>
                  <Typography variant="caption" gutterBottom>
                    Price Change: {priceParams.changePct}%
                  </Typography>
                  <Slider
                    value={priceParams.changePct}
                    min={-30}
                    max={30}
                    step={1}
                    onChange={(_, v) => setPriceParams({ ...priceParams, changePct: v as number })}
                  />
                </Box>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Box sx={{ px: 2 }}>
                  <Typography variant="caption" gutterBottom>
                    Promo Depth: {priceParams.promoDepth}%
                  </Typography>
                  <Slider
                    value={priceParams.promoDepth}
                    min={0}
                    max={50}
                    step={5}
                    onChange={(_, v) => setPriceParams({ ...priceParams, promoDepth: v as number })}
                  />
                </Box>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Box sx={{ px: 2 }}>
                  <Typography variant="caption" gutterBottom>
                    Duration: {priceParams.duration} days
                  </Typography>
                  <Slider
                    value={priceParams.duration}
                    min={1}
                    max={60}
                    step={1}
                    onChange={(_, v) => setPriceParams({ ...priceParams, duration: v as number })}
                  />
                </Box>
              </Grid>
            </Grid>
            <Button variant="contained" onClick={simulatePrice} sx={{ mt: 2 }}>
              Run Simulation
            </Button>
          </Box>
        )}

        {activeTab === 3 && (
          <Box>
            <Grid container spacing={3}>
              <Grid item xs={12} md={7}>
                <Card>
                  <CardContent sx={{ p: 2 }}>
                    <Typography variant="subtitle2" sx={{ mb: 2 }}>
                      Forecast Comparison
                    </Typography>
                    <Box sx={{ height: 400 }}>
                      <Line data={chartData} options={chartOptions} />
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} md={5}>
                <Card>
                  <CardContent sx={{ p: 2 }}>
                    <Typography variant="subtitle2" sx={{ mb: 2 }}>
                      Scenario Comparison
                    </Typography>
                    {comparisonData.length === 0 ? (
                      <Typography color="text.secondary">
                        Run simulations to see comparison
                      </Typography>
                    ) : (
                      <TableContainer>
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell>Scenario</TableCell>
                              <TableCell align="right">Impact</TableCell>
                              <TableCell align="right">Avg %</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {comparisonData.map((row) => (
                              <TableRow key={row.name}>
                                <TableCell>
                                  <Chip label={row.name} size="small" />
                                </TableCell>
                                <TableCell
                                  align="right"
                                  sx={{
                                    color: row.totalImpact > 0 ? 'success.main' : 'error.main',
                                    fontWeight: 600
                                  }}
                                >
                                  {row.totalImpact > 0 ? '+' : ''}{row.totalImpact.toFixed(0)}
                                </TableCell>
                                <TableCell
                                  align="right"
                                  sx={{
                                    color: row.avgImpact > 0 ? 'success.main' : 'error.main',
                                    fontWeight: 600
                                  }}
                                >
                                  {row.avgImpact > 0 ? '+' : ''}{row.avgImpact.toFixed(1)}%
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </Box>
        )}
      </DialogContent>
      
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  )
}
