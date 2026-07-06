import { useState } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Alert,
} from '@mui/material'
import { Tune, Layers } from '@mui/icons-material'

interface AggregationConfig {
  time_rollup: string
  product_level: string
  region_level: string
  agg_function: string
}

interface AggregationPanelProps {
  config: AggregationConfig
  onChange: (config: AggregationConfig) => void
  hasHierarchy: boolean
}

const timeOptions = [
  { value: 'D', label: 'Daily' },
  { value: 'W', label: 'Weekly' },
  { value: 'F', label: 'Fortnight (2 Weeks)' },
  { value: 'M', label: 'Monthly' },
  { value: 'Q', label: 'Quarterly' },
  { value: 'Y', label: 'Yearly' },
]

const productOptions = [
  { value: 'sku', label: 'SKU Level', description: 'Most granular - individual products' },
  { value: 'product', label: 'Product Level', description: 'Unique products' },
  { value: 'category', label: 'Category Level', description: 'Snacks, Dairy, Beverages, etc.' },
  { value: 'sub_category', label: 'Sub-Category Level', description: 'Nuts, Yogurt, Water, etc.' },
  { value: 'portfolio', label: 'Portfolio Level', description: 'Highest product grouping' },
]

const regionOptions = [
  { value: 'store', label: 'Store Level', description: 'Individual stores' },
  { value: 'region', label: 'Region Level', description: 'North, South, East, West' },
  { value: 'national', label: 'National', description: 'All stores combined' },
]

const aggFunctions = [
  { value: 'sum', label: 'Sum', description: 'Total across units' },
  { value: 'mean', label: 'Mean', description: 'Average across units' },
  { value: 'median', label: 'Median', description: 'Middle value' },
]

export function AggregationPanel({ config, onChange, hasHierarchy }: AggregationPanelProps) {
  const handleChange = (key: keyof AggregationConfig, value: string) => {
    onChange({ ...config, [key]: value })
  }

  return (
    <Card sx={{ mt: 3 }}>
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <Layers sx={{ color: 'primary.main' }} />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Aggregation Settings
          </Typography>
          <Chip label="Advanced" size="small" color="secondary" />
        </Box>

        {!hasHierarchy && (
          <Alert severity="info" sx={{ mb: 2 }}>
            Upload sales data with product hierarchy to enable SKU aggregation.
          </Alert>
        )}

        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Configure how your forecast results should be aggregated across time and product hierarchy.
        </Typography>

        <Grid container spacing={3}>
          <Grid item xs={12} sm={6} md={4}>
            <FormControl fullWidth size="small">
              <InputLabel>Time Granularity</InputLabel>
              <Select
                value={config.time_rollup}
                label="Time Granularity"
                onChange={(e) => handleChange('time_rollup', e.target.value)}
              >
                {timeOptions.map((opt) => (
                  <MenuItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
              Roll up daily forecasts to higher time periods
            </Typography>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <FormControl fullWidth size="small" disabled={!hasHierarchy}>
              <InputLabel>Product Level</InputLabel>
              <Select
                value={config.product_level}
                label="Product Level"
                onChange={(e) => handleChange('product_level', e.target.value)}
              >
                {productOptions.map((opt) => (
                  <MenuItem key={opt.value} value={opt.value}>
                    <Box>
                      <Typography variant="body2">{opt.label}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {opt.description}
                      </Typography>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
              Aggregate SKU data to product/category/portfolio
            </Typography>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <FormControl fullWidth size="small">
              <InputLabel>Region Level</InputLabel>
              <Select
                value={config.region_level}
                label="Region Level"
                onChange={(e) => handleChange('region_level', e.target.value)}
              >
                {regionOptions.map((opt) => (
                  <MenuItem key={opt.value} value={opt.value}>
                    <Box>
                      <Typography variant="body2">{opt.label}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {opt.description}
                      </Typography>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
              Aggregate store data to region/national
            </Typography>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <FormControl fullWidth size="small">
              <InputLabel>Aggregation Function</InputLabel>
              <Select
                value={config.agg_function}
                label="Aggregation Function"
                onChange={(e) => handleChange('agg_function', e.target.value)}
              >
                {aggFunctions.map((opt) => (
                  <MenuItem key={opt.value} value={opt.value}>
                    <Box>
                      <Typography variant="body2">{opt.label}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {opt.description}
                      </Typography>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
        </Grid>

        <Box sx={{ mt: 3, p: 2, bgcolor: 'background.default', borderRadius: 2 }}>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            Current Aggregation Summary:
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Chip
              label={`Time: ${timeOptions.find(t => t.value === config.time_rollup)?.label}`}
              size="small"
              variant="outlined"
            />
            <Chip
              label={`Product: ${productOptions.find(p => p.value === config.product_level)?.label}`}
              size="small"
              variant="outlined"
            />
            <Chip
              label={`Region: ${regionOptions.find(r => r.value === config.region_level)?.label}`}
              size="small"
              variant="outlined"
            />
            <Chip
              label={`Agg: ${aggFunctions.find(a => a.value === config.agg_function)?.label}`}
              size="small"
              variant="outlined"
            />
          </Box>
        </Box>
      </CardContent>
    </Card>
  )
}
