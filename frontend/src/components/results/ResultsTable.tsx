import { useMemo, type ReactNode } from 'react';
import { Box, Card, CardContent, MenuItem, Stack, TextField, Typography } from '@mui/material';
import { DataGrid, type GridColDef } from '@mui/x-data-grid';
import type { ForecastValue } from '../../types';
import { formatNumber, formatShortDate } from '../../utils/format';

interface ResultsTableProps {
  values: ForecastValue[];
  modelName: string;
  modelOptions?: Array<{ value: string; label: string }>;
  selectedModel?: string;
  onModelChange?: (model: string) => void;
  height?: number;
  backtestValues?: ForecastValue[] | null;
  actuals?: Array<{ date: string; value: number }>;
}

export function ResultsTable({
  values, modelName, modelOptions, selectedModel, onModelChange, height = 520, backtestValues, actuals,
}: ResultsTableProps): ReactNode {
  const actualByDate = useMemo(() => {
    const m = new Map<string, number>();
    if (actuals) for (const a of actuals) m.set(a.date, a.value);
    return m;
  }, [actuals]);
  const knownFields = new Set(['date', 'forecast', 'lower_ci', 'upper_ci', 'baseline', 'uplift', 'category', 'shap', 'shap_base']);
  const sample = values[0];
  const extraFields = sample
    ? Object.keys(sample).filter((k) => !knownFields.has(k))
    : [];
  const hasCategory = extraFields.length > 0 || (values.length > 0 && values.some((v) => v.category));

  const rows = useMemo(() => {
    const forecastRows = values.map((v, idx) => ({
      ...v,
      id: `${modelName}-${idx}-${v.date}${v.category ? '-' + v.category : ''}`,
      model: modelName,
      baseline: v.baseline ?? null,
      uplift: v.uplift ?? null,
    }));
    const btRows = (backtestValues ?? []).map((v, idx) => ({
      ...v,
      id: `bt-${modelName}-${idx}-${v.date}`,
      model: `${modelName} (backtest)`,
      baseline: v.baseline ?? null,
      uplift: v.uplift ?? null,
      actual: actualByDate.get(v.date) ?? null,
      residual: actualByDate.has(v.date)
        ? (actualByDate.get(v.date) as number) - v.forecast
        : null,
    }));
    return [...btRows, ...forecastRows];
  }, [values, modelName, backtestValues, actualByDate]);

  const columns: GridColDef[] = useMemo(
    () => [
      // Dynamic columns for multi-category breakdown
      ...extraFields.map((f) => ({
        field: f as string,
        headerName: f.charAt(0).toUpperCase() + f.slice(1),  // capitalize
        width: 140,
      })),
      ...(hasCategory && extraFields.length === 0
        ? [{
            field: 'category' as const,
            headerName: 'Category',
            width: 140,
          }]
        : []),
      {
        field: 'model',
        headerName: 'Model',
        width: 140,
      },
      {
        field: 'date',
        headerName: 'Date',
        width: 130,
        valueFormatter: (params: { value: string }) => formatShortDate(params.value),
      },
      {
        field: 'forecast',
        headerName: 'Forecast',
        type: 'number',
        flex: 1,
        minWidth: 120,
        valueFormatter: (params: { value: number | null | undefined }) =>
          formatNumber(params.value, 2),
      },
      {
        field: 'actual',
        headerName: 'Actual',
        type: 'number',
        flex: 1,
        minWidth: 100,
        valueFormatter: (params: { value: number | null | undefined }) =>
          params.value === null || params.value === undefined ? '\u2014' : formatNumber(params.value, 2),
      },
      {
        field: 'residual',
        headerName: 'Error',
        type: 'number',
        flex: 1,
        minWidth: 100,
        valueFormatter: (params: { value: number | null | undefined }) =>
          params.value === null || params.value === undefined ? '\u2014' : formatNumber(params.value, 2),
      },
      {
        field: 'lower_ci',
        headerName: 'Lower CI',
        type: 'number',
        flex: 1,
        minWidth: 120,
        valueFormatter: (params: { value: number | null | undefined }) =>
          formatNumber(params.value, 2),
      },
      {
        field: 'upper_ci',
        headerName: 'Upper CI',
        type: 'number',
        flex: 1,
        minWidth: 120,
        valueFormatter: (params: { value: number | null | undefined }) =>
          formatNumber(params.value, 2),
      },
      {
        field: 'baseline',
        headerName: 'Baseline',
        type: 'number',
        flex: 1,
        minWidth: 120,
        valueFormatter: (params: { value: number | null | undefined }) =>
          params.value === null || params.value === undefined ? '\u2014' : formatNumber(params.value, 2),
      },
      {
        field: 'uplift',
        headerName: 'Uplift',
        type: 'number',
        flex: 1,
        minWidth: 120,
        valueFormatter: (params: { value: number | null | undefined }) =>
          params.value === null || params.value === undefined ? '\u2014' : formatNumber(params.value, 2),
      },
    ],
    [hasCategory, extraFields],
  );

  return (
    <Card>
      <CardContent>
        <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
          <Box>
            <Typography variant="h5">Detailed forecast values</Typography>
            <Typography variant="body2" color="text.secondary">
              {modelName} &middot; {rows.length} rows
            </Typography>
          </Box>
          {modelOptions && onModelChange && selectedModel && (
            <TextField
              select
              size="small"
              label="Model"
              value={selectedModel}
              onChange={(e) => onModelChange(e.target.value)}
              sx={{ minWidth: 200 }}
            >
              {modelOptions.map((o) => (
                <MenuItem key={o.value} value={o.value}>
                  {o.label}
                </MenuItem>
              ))}
            </TextField>
          )}
        </Stack>
        <Box sx={{ width: '100%' }}>
          <DataGrid
            rows={rows}
            columns={columns}
            density="compact"
            disableRowSelectionOnClick
            initialState={{
              pagination: { paginationModel: { pageSize: 25, page: 0 } },
              sorting: { sortModel: [{ field: 'date', sort: 'asc' }] },
            }}
            pageSizeOptions={[10, 25, 50, 100]}
            sx={{
              border: 0,
              '& .MuiDataGrid-columnHeaders': { backgroundColor: 'background.subtle' },
              minHeight: height,
            }}
          />
        </Box>
      </CardContent>
    </Card>
  );
}
