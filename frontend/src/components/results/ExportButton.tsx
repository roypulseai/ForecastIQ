import type { ReactNode } from 'react';
import { Button, Menu, MenuItem, ListItemIcon, ListItemText, Divider } from '@mui/material';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import TableViewIcon from '@mui/icons-material/TableView';
import DataObjectIcon from '@mui/icons-material/DataObject';
import { useState } from 'react';
import { downloadBlob, downloadJson, toCsv } from '../../utils/csv';
import type { ForecastDetail, ForecastValue } from '../../types';

interface ExportButtonProps {
  detail: ForecastDetail;
  values: ForecastValue[];
  modelName: string;
  backtestValues?: ForecastValue[] | null;
  actuals?: Array<{ date: string; value: number }>;
}

export function ExportButton({ detail, values, modelName, backtestValues, actuals }: ExportButtonProps): ReactNode {
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);

  const actualByDate = new Map<string, number>();
  if (actuals) for (const a of actuals) actualByDate.set(a.date, a.value);

  const open = (e: React.MouseEvent<HTMLElement>) => setAnchor(e.currentTarget);
  const close = () => setAnchor(null);

  const exportCsv = () => {
    const cols = ['date', 'type', 'forecast', 'actual', 'error', 'lower_ci', 'upper_ci', 'baseline', 'uplift'];
    const rows: Array<Record<string, string | number>> = [];
    if (backtestValues) {
      for (const v of backtestValues) {
        const actual = actualByDate.get(v.date);
        rows.push({
          date: v.date,
          type: 'backtest',
          forecast: v.forecast,
          actual: actual ?? '',
          error: actual !== undefined ? +(actual - v.forecast).toFixed(4) : '',
          lower_ci: v.lower_ci,
          upper_ci: v.upper_ci,
          baseline: v.baseline ?? '',
          uplift: v.uplift ?? '',
        });
      }
    }
    for (const v of values) {
      rows.push({
        date: v.date,
        type: 'forecast',
        forecast: v.forecast,
        actual: '',
        error: '',
        lower_ci: v.lower_ci,
        upper_ci: v.upper_ci,
        baseline: v.baseline ?? '',
        uplift: v.uplift ?? '',
      });
    }
    const csv = toCsv(rows, cols);
    const safeName = modelName.replace(/[^a-z0-9_-]/gi, '_');
    downloadBlob(csv, `${detail.name.replace(/\s+/g, '_')}_${safeName}.csv`);
    close();
  };

  const exportJson = () => {
    const payload = {
      forecast_id: detail.forecast_id,
      name: detail.name,
      model: modelName,
      created_at: detail.created_at,
      values,
      backtest_values: backtestValues ?? [],
    };
    const safeName = detail.name.replace(/\s+/g, '_');
    downloadJson(payload, `${safeName}_${modelName}.json`);
    close();
  };

  return (
    <>
      <Button variant="outlined" startIcon={<FileDownloadIcon />} onClick={open} aria-haspopup="menu">
        Export
      </Button>
      <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={close}>
        <MenuItem onClick={exportCsv}>
          <ListItemIcon>
            <TableViewIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText primary="Download CSV" secondary={`${values.length} rows`} />
        </MenuItem>
        <Divider />
        <MenuItem onClick={exportJson}>
          <ListItemIcon>
            <DataObjectIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText primary="Download JSON" secondary="Full payload" />
        </MenuItem>
      </Menu>
    </>
  );
}
