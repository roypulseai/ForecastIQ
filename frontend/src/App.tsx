import type { ReactNode } from 'react';
import { Box } from '@mui/material';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AppNavbar } from './components/layout/AppNavbar';
import { ErrorBoundary } from './components/layout/ErrorBoundary';
import { ToastProvider } from './components/common/ToastProvider';
import { Dashboard } from './pages/Dashboard';
import { DataUploadPage } from './pages/DataUpload';
import { DataExplorePage } from './pages/DataExplore';
import { ForecastPage } from './pages/Forecast';
import { ResultsPage } from './pages/Results';
import { ModelsPage } from './pages/Models';
import { ApiKeysPage } from './pages/ApiKeys';
import { LoginPage } from './pages/Login';

function AuthGate({ children }: { children: ReactNode }): ReactNode {
  const token = localStorage.getItem('token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

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
          <ToastProvider>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/" element={<AuthGate><Navigate to="/dashboard" replace /></AuthGate>} />
              <Route path="/dashboard" element={<AuthGate><Dashboard /></AuthGate>} />
              <Route path="/upload" element={<AuthGate><DataUploadPage /></AuthGate>} />
              <Route path="/explore" element={<AuthGate><DataExplorePage /></AuthGate>} />
              <Route path="/forecast" element={<AuthGate><ForecastPage /></AuthGate>} />
              <Route path="/results" element={<AuthGate><ResultsPage /></AuthGate>} />
              <Route path="/models" element={<AuthGate><ModelsPage /></AuthGate>} />
              <Route path="/api-keys" element={<AuthGate><ApiKeysPage /></AuthGate>} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </ToastProvider>
        </ErrorBoundary>
      </Box>
    </Box>
  );
}

export default App;
