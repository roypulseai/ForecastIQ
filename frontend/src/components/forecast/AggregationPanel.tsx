import type { ReactNode } from 'react';
import { Grid, MenuItem, TextField, Typography } from '@mui/material';
import type { AggregationConfig, ProductLevel, RegionLevel, TimeGranularity } from '../../types';

interface AggregationPanelProps {
  value: AggregationConfig;
  onChange: (next: AggregationConfig) => void;
}

const TIME_OPTIONS: Array<{ value: TimeGranularity; label: string }> = [
  { value: 'D', label: 'Daily' },
  { value: 'W', label: 'Weekly' },
  { value: 'M', label: 'Monthly' },
  { value: 'Q', label: 'Quarterly' },
  { value: 'Y', label: 'Yearly' },
];

const PRODUCT_OPTIONS: Array<{ value: ProductLevel; label: string }> = [
  { value: 'sku', label: 'SKU' },
  { value: 'product', label: 'Product' },
  { value: 'sub_category', label: 'Sub-category' },
  { value: 'category', label: 'Category' },
  { value: 'portfolio', label: 'Portfolio' },
  { value: 'store', label: 'Store' },
  { value: 'region', label: 'Region' },
];

const REGION_OPTIONS: Array<{ value: RegionLevel; label: string }> = [
  { value: 'store', label: 'Store' },
  { value: 'region', label: 'Region' },
  { value: 'national', label: 'National' },
];

const AGG_OPTIONS = [
  { value: 'sum', label: 'Sum' },
  { value: 'mean', label: 'Mean' },
  { value: 'median', label: 'Median' },
];

export function AggregationPanel({ value, onChange }: AggregationPanelProps): ReactNode {
  const set = <K extends keyof AggregationConfig>(k: K, v: AggregationConfig[K]) =>
    onChange({ ...value, [k]: v });

  return (
    <Grid container spacing={2}>
      <Grid item xs={12} sm={6} md={3}>
        <TextField
          select
          fullWidth
          size="small"
          label="Time rollup"
          value={value.time_rollup}
          onChange={(e) => set('time_rollup', e.target.value as TimeGranularity)}
        >
          {TIME_OPTIONS.map((o) => (
            <MenuItem key={o.value} value={o.value}>
              {o.label}
            </MenuItem>
          ))}
        </TextField>
        <Typography variant="caption" color="text.secondary">
          Aggregate history to this cadence
        </Typography>
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <TextField
          select
          fullWidth
          size="small"
          label="Product level"
          value={value.product_level}
          onChange={(e) => set('product_level', e.target.value as ProductLevel)}
        >
          {PRODUCT_OPTIONS.map((o) => (
            <MenuItem key={o.value} value={o.value}>
              {o.label}
            </MenuItem>
          ))}
        </TextField>
        <Typography variant="caption" color="text.secondary">
          Group by this dimension
        </Typography>
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <TextField
          select
          fullWidth
          size="small"
          label="Region level"
          value={value.region_level}
          onChange={(e) => set('region_level', e.target.value as RegionLevel)}
        >
          {REGION_OPTIONS.map((o) => (
            <MenuItem key={o.value} value={o.value}>
              {o.label}
            </MenuItem>
          ))}
        </TextField>
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <TextField
          select
          fullWidth
          size="small"
          label="Aggregation function"
          value={value.agg_function}
          onChange={(e) => set('agg_function', e.target.value as 'sum' | 'mean' | 'median')}
        >
          {AGG_OPTIONS.map((o) => (
            <MenuItem key={o.value} value={o.value}>
              {o.label}
            </MenuItem>
          ))}
        </TextField>
      </Grid>
    </Grid>
  );
}
