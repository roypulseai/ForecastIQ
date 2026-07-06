import { Routes, Route, Navigate } from 'react-router-dom'
import { Box, Container } from '@mui/material'
import { AppNavbar } from './components/layout/AppNavbar'
import { Dashboard } from './pages/Dashboard'
import { DataUpload } from './pages/DataUpload'
import { Forecast } from './pages/Forecast'
import { Results } from './pages/Results'

function App() {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppNavbar />
      <Box component="main" sx={{ flexGrow: 1, bgcolor: 'background.default', py: 3 }}>
        <Container maxWidth="xl">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/upload" element={<DataUpload />} />
            <Route path="/forecast" element={<Forecast />} />
            <Route path="/results" element={<Results />} />
          </Routes>
        </Container>
      </Box>
    </Box>
  )
}

export default App
