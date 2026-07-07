import { useState, type ReactNode } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import {
  AppBar,
  Box,
  Button,
  Container,
  IconButton,
  Stack,
  Toolbar,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import InsightsIcon from '@mui/icons-material/Insights';
import TimelineIcon from '@mui/icons-material/Timeline';
import AssessmentIcon from '@mui/icons-material/Assessment';
import MenuIcon from '@mui/icons-material/Menu';
import CloseIcon from '@mui/icons-material/Close';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import StorageIcon from '@mui/icons-material/Storage';
import VpnKeyIcon from '@mui/icons-material/VpnKey';
import { alpha } from '@mui/material/styles';

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', icon: DashboardIcon },
  { to: '/upload', label: 'Data', icon: CloudUploadIcon },
  { to: '/explore', label: 'Explore', icon: InsightsIcon },
  { to: '/forecast', label: 'Forecast', icon: TimelineIcon },
  { to: '/results', label: 'Results', icon: AssessmentIcon },
  { to: '/models', label: 'Models', icon: StorageIcon },
  { to: '/api-keys', label: 'API', icon: VpnKeyIcon },
] as const;

export function AppNavbar(): ReactNode {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [drawerOpen, setDrawerOpen] = useState(false);
  const location = useLocation();

  const closeDrawer = () => setDrawerOpen(false);

  return (
    <>
      <AppBar
        position="sticky"
        elevation={0}
        sx={{
          backgroundColor: 'background.paper',
          color: 'text.primary',
          borderBottom: '1px solid',
          borderBottomColor: 'divider',
          backdropFilter: 'saturate(180%) blur(8px)',
        }}
      >
        <Container maxWidth="xl">
          <Toolbar disableGutters sx={{ minHeight: 64, gap: 2 }}>
            <Box
              component={Link}
              to="/dashboard"
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1.25,
                textDecoration: 'none',
                color: 'inherit',
                mr: 2,
              }}
            >
              <Box
                sx={{
                  width: 36,
                  height: 36,
                  borderRadius: 2,
                  background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'common.white',
                }}
              >
                <ShowChartIcon sx={{ fontSize: 20 }} />
              </Box>
              <Box>
                <Typography variant="h6" sx={{ lineHeight: 1, fontWeight: 700 }}>
                  ForecastIQ
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ lineHeight: 1 }}>
                  Time Series Forecasting
                </Typography>
              </Box>
            </Box>

            {!isMobile && (
              <Stack direction="row" spacing={0.5} sx={{ flexGrow: 1 }}>
                {NAV_ITEMS.map((item) => {
                  const Icon = item.icon;
                  const active =
                    location.pathname === item.to ||
                    (item.to !== '/dashboard' && location.pathname.startsWith(item.to));
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      style={{ textDecoration: 'none' }}
                      aria-label={item.label}
                    >
                      <Button
                        startIcon={<Icon />}
                        sx={{
                          color: active ? 'primary.main' : 'text.secondary',
                          fontWeight: active ? 600 : 500,
                          px: 2,
                          backgroundColor: active
                            ? alpha(theme.palette.primary.main, 0.08)
                            : 'transparent',
                          '&:hover': {
                            backgroundColor: alpha(theme.palette.primary.main, 0.06),
                          },
                        }}
                      >
                        {item.label}
                      </Button>
                    </NavLink>
                  );
                })}
              </Stack>
            )}

            <Box sx={{ flexGrow: isMobile ? 1 : 0, ml: isMobile ? 0 : 'auto' }} />

            <Tooltip title="API documentation">
              <Button
                variant="outlined"
                size="small"
                href="/docs"
                target="_blank"
                rel="noopener noreferrer"
              >
                API Docs
              </Button>
            </Tooltip>

            {isMobile && (
              <IconButton
                edge="end"
                aria-label="open navigation"
                onClick={() => setDrawerOpen((o) => !o)}
                sx={{ ml: 1 }}
              >
                {drawerOpen ? <CloseIcon /> : <MenuIcon />}
              </IconButton>
            )}
          </Toolbar>
        </Container>
      </AppBar>

      {isMobile && drawerOpen && (
        <Box
          role="presentation"
          sx={{
            position: 'fixed',
            inset: '64px 0 0 0',
            backgroundColor: 'background.paper',
            zIndex: theme.zIndex.appBar - 1,
            borderTop: '1px solid',
            borderTopColor: 'divider',
            p: 2,
          }}
        >
          <Stack spacing={1}>
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const active =
                location.pathname === item.to ||
                (item.to !== '/dashboard' && location.pathname.startsWith(item.to));
              return (
                <Button
                  key={item.to}
                  component={NavLink}
                  to={item.to}
                  onClick={closeDrawer}
                  startIcon={<Icon />}
                  fullWidth
                  sx={{
                    justifyContent: 'flex-start',
                    color: active ? 'primary.main' : 'text.primary',
                    backgroundColor: active
                      ? alpha(theme.palette.primary.main, 0.08)
                      : 'transparent',
                    py: 1.5,
                  }}
                >
                  {item.label}
                </Button>
              );
            })}
          </Stack>
        </Box>
      )}
    </>
  );
}
