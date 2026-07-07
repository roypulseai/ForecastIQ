import type { ReactNode } from 'react';
import { Box } from '@mui/material';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AppNavbar } from './components/layout/AppNavbar';
import { ErrorBoundary } from './components/layout/ErrorBoundary';
import { Dashboard } from './pages/Dashboard';
import { DataUploadPage } from './pages/DataUpload';
import { DataExplorePage } from './pages/DataExplore';
import { ForecastPage } from './pages/Forecast';
import { ResultsPage } from './pages/Results';
import { ModelsPage } from './pages/Models';

function App(): ReactNode {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppNavbar />
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          backgroundColor: 'background.default',
        }}
      >
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/upload" element={<DataUploadPage />} />
            <Route path="/explore" element={<DataExplorePage />} />
            <Route path="/forecast" element={<ForecastPage />} />
            <Route path="/results" element={<ResultsPage />} />
            <Route path="/models" element={<ModelsPage />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </ErrorBoundary>
      </Box>
    </Box>
  );
}

export default App;
