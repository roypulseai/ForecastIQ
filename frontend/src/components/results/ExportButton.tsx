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
}

export function ExportButton({ detail, values, modelName }: ExportButtonProps): ReactNode {
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);

  const open = (e: React.MouseEvent<HTMLElement>) => setAnchor(e.currentTarget);
  const close = () => setAnchor(null);

  const exportCsv = () => {
    const cols = ['date', 'forecast', 'lower_ci', 'upper_ci', 'baseline', 'uplift'];
    const rows = values.map((v) => ({
      date: v.date,
      forecast: v.forecast,
      lower_ci: v.lower_ci,
      upper_ci: v.upper_ci,
      baseline: v.baseline ?? '',
      uplift: v.uplift ?? '',
    }));
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
