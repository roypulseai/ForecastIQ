import { useState, useCallback } from 'react'
import { Box, Typography, Grid, Button, Alert, Snackbar, CircularProgress } from '@mui/material'
import { CloudUpload } from '@mui/icons-material'
import { FileUploader } from '../components/upload/FileUploader'
import { DataAnalysis } from '../components/forecast/DataAnalysis'
import { forecastApi, UploadResponse } from '../services/api'
import { useStore } from '../store/appStore'

const fileTypes = [
  {
    type: 'sales',
    title: 'Sales Data',
    description: 'Historical sales data with dates and values',
    acceptedTypes: '.csv, .xlsx, .xls',
  },
  {
    type: 'media_plan',
    title: 'Media Plan',
    description: 'Marketing spend and channel data',
    acceptedTypes: '.csv, .xlsx, .xls',
  },
  {
    type: 'promotions',
    title: 'Promotions',
    description: 'Promotional campaigns and discounts',
    acceptedTypes: '.csv, .xlsx, .xls',
  },
  {
    type: 'holidays',
    title: 'Holidays',
    description: 'Holiday calendar with impact factors',
    acceptedTypes: '.csv, .xlsx, .xls',
  },
  {
    type: 'events',
    title: 'Events',
    description: 'Special events that may affect demand',
    acceptedTypes: '.csv, .xlsx, .xls',
  },
]

export function DataUpload() {
  const { uploadedFiles, addUploadedFile, setSalesFileId, setAnalysisData } = useStore()
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string }>({
    open: false,
    message: '',
  })

  const handleUpload = useCallback(
    async (fileType: string, file: File) => {
      try {
        const response = await forecastApi.uploadFile(fileType, file)
        const uploadResponse: UploadResponse = response

        addUploadedFile({
          ...uploadResponse,
          file_id: uploadResponse.file_id,
        })

        if (fileType === 'sales') {
          setSalesFileId(uploadResponse.file_id)
          setIsAnalyzing(true)

          try {
            const analysis = await forecastApi.analyzeData(uploadResponse.file_id)
            setAnalysisData(analysis)
          } catch (err) {
            console.error('Analysis error:', err)
          } finally {
            setIsAnalyzing(false)
          }
        }

        setSnackbar({
          open: true,
          message: `${file.name} uploaded successfully`,
        })
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Upload failed')
      }
    },
    [addUploadedFile, setSalesFileId, setAnalysisData]
  )

  const salesFile = uploadedFiles.find((f) => f.type === 'sales')
  const analysisData = useStore((state) => state.analysisData)

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
          Data Upload
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Upload your data files for forecasting analysis
        </Typography>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
            Upload Files
          </Typography>

          <Grid container spacing={3}>
            {fileTypes.map((fileType) => (
              <Grid item xs={12} sm={6} md={4} key={fileType.type}>
                <FileUploader
                  fileType={fileType.type}
                  title={fileType.title}
                  description={fileType.description}
                  acceptedTypes={fileType.acceptedTypes}
                  uploadedFile={uploadedFiles.find((f) => f.type === fileType.type) || null}
                  onUpload={(file) => handleUpload(fileType.type, file)}
                />
              </Grid>
            ))}
          </Grid>
        </Grid>

        <Grid item xs={12} md={4}>
          {isAnalyzing ? (
            <Box
              sx={{
                p: 4,
                textAlign: 'center',
                bgcolor: 'background.paper',
                borderRadius: 2,
              }}
            >
              <CircularProgress sx={{ mb: 2 }} />
              <Typography>Analyzing data...</Typography>
            </Box>
          ) : (
            <DataAnalysis
              characteristics={analysisData?.data_characteristics || null}
              recommendations={analysisData?.model_recommendations || []}
            />
          )}
        </Grid>
      </Grid>

      {salesFile && (
        <Box sx={{ mt: 4 }}>
          <Button
            variant="contained"
            size="large"
            endIcon={<CloudUpload />}
            onClick={() => window.location.href = '/forecast'}
          >
            Proceed to Forecast
          </Button>
        </Box>
      )}

      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        message={snackbar.message}
      />

      <Snackbar
        open={!!error}
        autoHideDuration={6000}
        onClose={() => setError(null)}
      >
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      </Snackbar>
    </Box>
  )
}
