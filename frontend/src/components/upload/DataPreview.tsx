import type { ReactNode } from 'react';
import {
  Box,
  Chip,
  IconButton,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from '@mui/material';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import DownloadIcon from '@mui/icons-material/Download';
import StorageIcon from '@mui/icons-material/Storage';
import { formatBytes, formatNumber } from '../../utils/format';
import { FILE_TYPE_LABELS, type UploadedFile } from '../../types';

interface DataPreviewProps {
  file: UploadedFile;
  onDelete?: (fileId: string) => void;
  showDelete?: boolean;
  showDownloadTemplate?: boolean;
  onDownloadTemplate?: () => void;
}

export function DataPreview({
  file,
  onDelete,
  showDelete = true,
  showDownloadTemplate = false,
  onDownloadTemplate,
}: DataPreviewProps): ReactNode {
  return (
    <Paper sx={{ overflow: 'hidden' }}>
      <Box
        sx={{
          p: 2,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid',
          borderBottomColor: 'divider',
          backgroundColor: 'background.subtle',
        }}
      >
        <Stack direction="row" spacing={1.5} alignItems="center" sx={{ minWidth: 0 }}>
          <Box
            sx={{
              width: 36,
              height: 36,
              borderRadius: 1.5,
              backgroundColor: 'primary.lighter',
              color: 'primary.main',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <StorageIcon fontSize="small" />
          </Box>
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="subtitle2" noWrap title={file.filename}>
              {file.filename}
            </Typography>
            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" rowGap={0.5}>
              <Chip
                label={FILE_TYPE_LABELS[file.type as keyof typeof FILE_TYPE_LABELS] ?? file.type}
                size="small"
                color="primary"
                variant="outlined"
              />
              <Typography variant="caption" color="text.secondary">
                {formatNumber(file.row_count)} rows · {file.columns.length} cols ·{' '}
                {formatBytes(file.size)}
              </Typography>
            </Stack>
          </Box>
        </Stack>
        <Stack direction="row" spacing={0.5}>
          {showDownloadTemplate && onDownloadTemplate && (
            <Tooltip title="Download template">
              <IconButton size="small" onClick={onDownloadTemplate} aria-label="Download template">
                <DownloadIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
          {showDelete && onDelete && (
            <Tooltip title="Delete file">
              <IconButton
                size="small"
                onClick={() => onDelete(file.file_id)}
                aria-label={`Delete ${file.filename}`}
                color="error"
              >
                <DeleteOutlineIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
        </Stack>
      </Box>
      {file.warnings && file.warnings.length > 0 && (
        <Box sx={{ p: 2, backgroundColor: 'warning.lighter' }}>
          {file.warnings.map((w, idx) => (
            <Typography key={`${file.file_id}-warn-${idx}`} variant="body2" color="warning.dark">
              ⚠ {w}
            </Typography>
          ))}
        </Box>
      )}
      {file.column_mapping && Object.keys(file.column_mapping).length > 0 && (
        <Box sx={{ px: 2, py: 1.5, borderBottom: '1px solid', borderBottomColor: 'divider' }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
            Column mapping detected
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" rowGap={0.5} sx={{ mt: 0.5 }}>
            {Object.entries(file.column_mapping).map(([k, v]) => (
              <Chip
                key={`${file.file_id}-map-${k}`}
                label={`${k} ← ${v}`}
                size="small"
                variant="outlined"
              />
            ))}
          </Stack>
        </Box>
      )}
      <TableContainer sx={{ maxHeight: 360 }}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              {file.columns.map((col) => (
                <TableCell key={`${file.file_id}-col-${col}`}>{col}</TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            <TableRow>
              {file.columns.map((col) => (
                <TableCell key={`${file.file_id}-type-${col}`} sx={{ color: 'text.secondary' }}>
                  <em>Preview shown after upload</em>
                </TableCell>
              ))}
            </TableRow>
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
}
