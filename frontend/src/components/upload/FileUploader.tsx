import { useCallback, useState } from 'react'
import { Box, Typography, Card, CardContent, alpha, IconButton } from '@mui/material'
import { useDropzone } from 'react-dropzone'
import { CloudUpload, InsertDriveFile, CheckCircle, Delete } from '@mui/icons-material'

interface UploadedFile {
  file_id: string
  filename: string
  type: string
  size: number
  row_count: number
  columns: string[]
}

interface FileUploaderProps {
  fileType: string
  title: string
  description: string
  acceptedTypes: string
  uploadedFile: UploadedFile | null
  onUpload: (file: File) => void
  onRemove?: (fileId: string) => void
}

export function FileUploader({
  fileType,
  title,
  description,
  acceptedTypes,
  uploadedFile,
  onUpload,
  onRemove,
}: FileUploaderProps) {
  const [isUploading, setIsUploading] = useState(false)

  const handleDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0) {
        setIsUploading(true)
        onUpload(acceptedFiles[0])
        setTimeout(() => setIsUploading(false), 500)
      }
    },
    [onUpload]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
    maxFiles: 1,
    disabled: !!uploadedFile || isUploading,
    onDrop: handleDrop,
  } as any)

  if (uploadedFile) {
    return (
      <Card sx={{ height: '100%' }}>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
            <Box
              sx={{
                width: 48,
                height: 48,
                borderRadius: 2,
                bgcolor: alpha('#2e7d32', 0.1),
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <CheckCircle sx={{ color: 'success.main', fontSize: 24 }} />
            </Box>
            <Box sx={{ flex: 1 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                {uploadedFile.filename}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {uploadedFile.type.replace('_', ' ')} • {(uploadedFile.size / 1024).toFixed(1)} KB • {uploadedFile.row_count.toLocaleString()} rows
              </Typography>
            </Box>
            {onRemove && (
              <IconButton
                color="error"
                onClick={() => onRemove(uploadedFile.file_id)}
                size="small"
              >
                <Delete />
              </IconButton>
            )}
          </Box>
          <Box sx={{ mt: 2, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
              Columns:
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
              {uploadedFile.columns.map((col) => (
                <Box
                  key={col}
                  sx={{
                    px: 1,
                    py: 0.25,
                    bgcolor: 'primary.lighter',
                    borderRadius: 0.5,
                    fontSize: '0.75rem',
                  }}
                >
                  {col}
                </Box>
              ))}
            </Box>
          </Box>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card
      {...getRootProps()}
      sx={{
        height: '100%',
        cursor: 'pointer',
        transition: 'all 0.2s',
        border: '2px dashed',
        borderColor: isDragActive ? 'primary.main' : 'divider',
        bgcolor: isDragActive ? alpha('#1976d2', 0.04) : 'transparent',
        '&:hover': {
          borderColor: 'primary.light',
          bgcolor: alpha('#1976d2', 0.04),
        },
      }}
    >
      <input {...getInputProps()} />
      <CardContent sx={{ p: 4, textAlign: 'center' }}>
        <Box
          sx={{
            width: 64,
            height: 64,
            borderRadius: '50%',
            bgcolor: alpha('#1976d2', 0.1),
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            mx: 'auto',
            mb: 2,
          }}
        >
          {isUploading ? (
            <InsertDriveFile sx={{ color: 'primary.main', fontSize: 32 }} />
          ) : (
            <CloudUpload sx={{ color: 'primary.main', fontSize: 32 }} />
          )}
        </Box>
        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 0.5 }}>
          {title}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {description}
        </Typography>
        <Box
          sx={{
            display: 'inline-block',
            px: 2,
            py: 1,
            bgcolor: alpha('#1976d2', 0.1),
            borderRadius: 1,
          }}
        >
          <Typography variant="caption" color="primary" sx={{ fontWeight: 600 }}>
            {acceptedTypes}
          </Typography>
        </Box>
      </CardContent>
    </Card>
  )
}
