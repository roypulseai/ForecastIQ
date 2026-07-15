import { useState, useEffect, useCallback, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import LoginIcon from '@mui/icons-material/Login';
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import { api } from '../services/api';

export function LoginPage(): ReactNode {
  const navigate = useNavigate();
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [checkingBackend, setCheckingBackend] = useState(true);
  const [backendDown, setBackendDown] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      navigate('/dashboard', { replace: true });
      return;
    }
    api.get('/auth/status')
      .then(() => setBackendDown(false))
      .catch(() => setBackendDown(true))
      .finally(() => setCheckingBackend(false));
  }, [navigate]);

  const doLogin = useCallback(async (user: string, pass: string) => {
    setError(null);
    setLoading(true);
    try {
      const res = await api.post('/auth/login', { username: user, password: pass });
      localStorage.setItem('token', res.data.access_token);
      navigate('/dashboard', { replace: true });
      window.location.reload();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || 'Login failed. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  const handleQuickLogin = () => doLogin('admin', 'admin');

  const handleDemoLogin = async () => {
    setError(null);
    setLoading(true);
    try {
      const res = await api.post('/auth/demo');
      localStorage.setItem('token', res.data.access_token);
      navigate('/dashboard', { replace: true });
      window.location.reload();
    } catch {
      setError('Demo login failed. Is the backend running?');
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    doLogin(username, password);
  };

  if (checkingBackend) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
        <Typography color="text.secondary">Connecting to backend...</Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        backgroundColor: 'background.default',
      }}
    >
      <Card sx={{ maxWidth: 400, width: '100%', mx: 2 }}>
        <CardContent sx={{ p: 4 }}>
          <Stack spacing={3} alignItems="center">
            <Box
              sx={{
                width: 56,
                height: 56,
                borderRadius: 2,
                background: (t) => `linear-gradient(135deg, ${t.palette.primary.main} 0%, ${t.palette.secondary.main} 100%)`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'common.white',
              }}
            >
              <ShowChartIcon sx={{ fontSize: 32 }} />
            </Box>

            <Box textAlign="center">
              <Typography variant="h5" fontWeight={700}>ForecastIQ</Typography>
              <Typography variant="body2" color="text.secondary">Sign in to your account</Typography>
            </Box>

            {backendDown && (
              <Alert severity="error" sx={{ width: '100%' }}>
                Cannot reach the backend. Make sure it is running on port 8000.
              </Alert>
            )}

            {error && <Alert severity="error" sx={{ width: '100%' }}>{error}</Alert>}

            <Button
              variant="contained"
              size="large"
              fullWidth
              startIcon={<LoginIcon />}
              disabled={loading || backendDown}
              onClick={handleQuickLogin}
              sx={{ py: 1.5 }}
            >
              Login as Admin
            </Button>

            <Button
              variant="outlined"
              size="small"
              fullWidth
              startIcon={<RocketLaunchIcon />}
              disabled={loading}
              onClick={handleDemoLogin}
              color="secondary"
              sx={{ textTransform: 'none' }}
            >
              Skip login (demo mode)
            </Button>

            <Box sx={{ width: '100%' }}>
              <Divider>
                <Chip label="or sign in with credentials" size="small" variant="outlined" />
              </Divider>
            </Box>

            <Box component="form" onSubmit={handleSubmit} sx={{ width: '100%' }}>
              <Stack spacing={2}>
                <TextField
                  label="Username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  autoFocus
                  fullWidth
                  required
                  size="small"
                />
                <TextField
                  label="Password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  fullWidth
                  required
                  size="small"
                />
                <Button
                  type="submit"
                  variant="outlined"
                  fullWidth
                  disabled={loading || backendDown}
                >
                  {loading ? 'Signing in...' : 'Sign in'}
                </Button>
              </Stack>
            </Box>

            <Typography variant="caption" color="text.secondary" textAlign="center">
              Default credentials: admin / admin<br />
              Change this password after first login.
            </Typography>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
