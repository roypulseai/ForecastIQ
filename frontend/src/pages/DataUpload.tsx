import { useState, useCallback } from 'react'
import { Box, Typography, Grid, Button, Alert, Snackbar, CircularProgress, Card, CardContent, Chip } from '@mui/material'
import { CloudUpload, Download, Description, Cloud } from '@mui/icons-material'
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
    required: true,
  },
  {
    type: 'media_plan',
    title: 'Media Plan',
    description: 'Marketing spend by channel (TV, digital, social)',
    acceptedTypes: '.csv, .xlsx, .xls',
    required: false,
  },
  {
    type: 'promotions',
    title: 'Promotions',
    description: 'Promotional campaigns and discounts',
    acceptedTypes: '.csv, .xlsx, .xls',
    required: false,
  },
  {
    type: 'holidays',
    title: 'Holidays',
    description: 'Holiday calendar with impact factors',
    acceptedTypes: '.csv, .xlsx, .xls',
    required: false,
  },
  {
    type: 'events',
    title: 'Events',
    description: 'Special events that affect demand',
    acceptedTypes: '.csv, .xlsx, .xls',
    required: false,
  },
  {
    type: 'weather',
    title: 'Weather',
    description: 'Weather conditions (temp, rain, snow)',
    acceptedTypes: '.csv, .xlsx, .xls',
    required: false,
  },
  {
    type: 'competitor',
    title: 'Competitor',
    description: 'Competitor pricing and market share',
    acceptedTypes: '.csv, .xlsx, .xls',
    required: false,
  },
  {
    type: 'economic',
    title: 'Economic',
    description: 'Economic indicators (GDP, inflation)',
    acceptedTypes: '.csv, .xlsx, .xls',
    required: false,
  },
]

const templates = [
  { name: 'Sales Template', file: 'templates/01_sales_template.csv', description: 'Required for forecasting' },
  { name: 'Media Plan', file: 'templates/02_media_plan_template.csv', description: 'Channel spend data' },
  { name: 'Promotions', file: 'templates/03_promotions_template.csv', description: 'Promo campaigns' },
  { name: 'Holidays', file: 'templates/04_holidays_template.csv', description: 'Holiday impact' },
  { name: 'Events', file: 'templates/05_events_template.csv', description: 'Special events' },
  { name: 'Weather', file: 'templates/06_weather_template.csv', description: 'Weather conditions' },
  { name: 'Competitor', file: 'templates/07_competitor_template.csv', description: 'Competitor data' },
  { name: 'Economic', file: 'templates/08_economic_template.csv', description: 'Economic indicators' },
]

export function DataUpload() {
  const { uploadedFiles, addUploadedFile, removeUploadedFile, setSalesFileId, setAnalysisData } = useStore()
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string }>({
    open: false,
    message: '',
  })

  const handleRemove = useCallback(
    async (fileId: string) => {
      try {
        await forecastApi.deleteFile(fileId)
        const file = uploadedFiles.find((f) => f.file_id === fileId)
        removeUploadedFile(fileId)
        if (file?.type === 'sales') {
          setSalesFileId(null)
          setAnalysisData(null)
        }
        setSnackbar({
          open: true,
          message: 'File removed successfully',
        })
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to remove file')
      }
    },
    [uploadedFiles, removeUploadedFile, setSalesFileId, setAnalysisData]
  )

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

  const handleDownloadTemplate = (templateFile: string) => {
    const link = document.createElement('a')
    link.href = `/${templateFile}`
    link.download = templateFile.split('/').pop() || 'template.csv'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const salesFile = uploadedFiles.find((f) => f.type === 'sales')
  const analysisData = useStore((state) => state.analysisData)

  const uploadedTypes = new Set(uploadedFiles.map(f => f.type))
  const allRequiredUploaded = uploadedTypes.has('sales')

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
          Data Upload
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Upload your data files for forecasting. Download templates below.
        </Typography>
      </Box>

      <Card sx={{ mb: 4, bgcolor: 'primary.lighter' }}>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
            <Download sx={{ color: 'primary.main', fontSize: 32 }} />
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Download CSV Templates
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Use these templates to format your external data correctly
              </Typography>
            </Box>
          </Box>
          <Grid container spacing={2}>
            {templates.map((template) => (
              <Grid item xs={12} sm={6} md={3} key={template.name}>
                <Box
                  sx={{
                    p: 2,
                    bgcolor: 'background.paper',
                    borderRadius: 2,
                    cursor: 'pointer',
                    '&:hover': { bgcolor: 'action.hover' },
                  }}
                  onClick={() => handleDownloadTemplate(template.file)}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                    <Description sx={{ fontSize: 18, color: 'primary.main' }} />
                    <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                      {template.name}
                    </Typography>
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    {template.description}
                  </Typography>
                </Box>
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Upload Files
            </Typography>
            <Chip
              label={allRequiredUploaded ? 'Ready' : 'Sales Required'}
              color={allRequiredUploaded ? 'success' : 'warning'}
              size="small"
            />
          </Box>

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
                  onRemove={handleRemove}
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
              characteristics={analysisData?.analysis?.data_characteristics || null}
              recommendations={analysisData?.analysis?.model_recommendations || []}
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
