import { useCallback, type ReactNode } from 'react';
import { useDropzone } from 'react-dropzone';
import { Box, CircularProgress, Stack, Typography } from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import { alpha, useTheme } from '@mui/material/styles';

interface FileUploaderProps {
  fileType: string;
  label: string;
  description?: string;
  isLoading?: boolean;
  disabled?: boolean;
  onFileSelected: (file: File) => void;
}

export function FileUploader({
  fileType,
  label,
  description,
  isLoading = false,
  disabled = false,
  onFileSelected,
}: FileUploaderProps): ReactNode {
  const theme = useTheme();

  const onDrop = useCallback(
    (accepted: File[]) => {
      if (accepted.length > 0) onFileSelected(accepted[0]);
    },
    [onFileSelected],
  );

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    multiple: false,
    disabled: disabled || isLoading,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    },
  });

  const primary = theme.palette.primary.main;
  const borderColor = isDragActive
    ? primary
    : isDragReject
      ? theme.palette.error.main
      : 'divider';
  const bg = isDragActive
    ? alpha(primary, 0.06)
    : isDragReject
      ? alpha(theme.palette.error.main, 0.06)
      : 'background.paper';

  return (
    <Box
      {...getRootProps()}
      role="button"
      tabIndex={0}
      aria-label={`Upload ${label}. ${description ?? ''}`}
      sx={{
        border: '2px dashed',
        borderColor,
        borderRadius: 2,
        p: 3,
        backgroundColor: bg,
        cursor: disabled || isLoading ? 'not-allowed' : 'pointer',
        textAlign: 'center',
        transition: 'all 200ms ease',
        outline: 'none',
        '&:focus-visible': {
          boxShadow: `0 0 0 3px ${alpha(primary, 0.2)}`,
        },
        opacity: disabled && !isLoading ? 0.5 : 1,
      }}
    >
      <input {...getInputProps()} aria-label={`File input for ${fileType}`} />
      <Stack spacing={1.5} alignItems="center">
        <Box
          sx={{
            width: 48,
            height: 48,
            borderRadius: '50%',
            backgroundColor: alpha(primary, 0.1),
            color: primary,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {isLoading ? (
            <CircularProgress size={24} />
          ) : isDragActive ? (
            <InsertDriveFileIcon />
          ) : (
            <CloudUploadIcon />
          )}
        </Box>
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            {isLoading ? 'Uploading…' : label}
          </Typography>
          {description && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {description}
            </Typography>
          )}
        </Box>
        <Typography variant="caption" color="text.secondary">
          Drag a file here or click to browse. CSV, XLS, XLSX (max 100 MB).
        </Typography>
      </Stack>
    </Box>
  );
}
