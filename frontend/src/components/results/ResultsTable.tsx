import { useMemo, type ReactNode } from 'react';
import { Box, Card, CardContent, Stack, Typography } from '@mui/material';
import { DataGrid, type GridColDef } from '@mui/x-data-grid';
import type { ForecastValue } from '../../types';
import { formatNumber, formatShortDate } from '../../utils/format';

interface ResultsTableProps {
  values: ForecastValue[];
  modelName: string;
  height?: number;
}

export function ResultsTable({ values, modelName, height = 520 }: ResultsTableProps): ReactNode {
  const rows = useMemo(
    () =>
      values.map((v, idx) => ({
        id: `${modelName}-${idx}-${v.date}`,
        date: v.date,
        forecast: v.forecast,
        lower_ci: v.lower_ci,
        upper_ci: v.upper_ci,
        baseline: v.baseline ?? null,
        uplift: v.uplift ?? null,
      })),
    [values, modelName],
  );

  const columns: GridColDef[] = useMemo(
    () => [
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
          params.value === null || params.value === undefined ? '—' : formatNumber(params.value, 2),
      },
      {
        field: 'uplift',
        headerName: 'Uplift',
        type: 'number',
        flex: 1,
        minWidth: 120,
        valueFormatter: (params: { value: number | null | undefined }) =>
          params.value === null || params.value === undefined ? '—' : formatNumber(params.value, 2),
      },
    ],
    [],
  );

  return (
    <Card>
      <CardContent>
        <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
          <Box>
            <Typography variant="h5">Detailed forecast values</Typography>
            <Typography variant="body2" color="text.secondary">
              {modelName} · {rows.length} rows
            </Typography>
          </Box>
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
