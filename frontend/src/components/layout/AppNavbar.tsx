import { AppBar, Toolbar, Typography, Box, Button, Container, Chip } from '@mui/material'
import { Link as RouterLink, useLocation } from 'react-router-dom'
import { BarChart, CloudUpload, Build, Assessment } from '@mui/icons-material'

const navItems = [
  { label: 'Dashboard', path: '/dashboard', icon: BarChart },
  { label: 'Data Upload', path: '/upload', icon: CloudUpload },
  { label: 'Forecast', path: '/forecast', icon: Build },
  { label: 'Results', path: '/results', icon: Assessment },
]

export function AppNavbar() {
  const location = useLocation()

  return (
    <AppBar 
      position="sticky" 
      elevation={0}
      sx={{ 
        bgcolor: 'background.paper',
        borderBottom: '1px solid',
        borderColor: 'divider',
      }}
    >
      <Container maxWidth="xl">
        <Toolbar disableGutters sx={{ minHeight: 72 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mr: 4 }}>
            <Box
              sx={{
                width: 40,
                height: 40,
                borderRadius: 2,
                bgcolor: 'primary.main',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <BarChart sx={{ color: 'white', fontSize: 24 }} />
            </Box>
            <Box>
              <Typography 
                variant="h6" 
                sx={{ 
                  color: 'text.primary',
                  fontWeight: 700,
                  letterSpacing: '-0.5px',
                  lineHeight: 1.2,
                }}
              >
                ForecastIQ
              </Typography>
              <Typography 
                variant="caption" 
                sx={{ 
                  color: 'text.secondary',
                  fontSize: '0.7rem',
                  letterSpacing: '0.5px',
                }}
              >
                ADVANCED FORECASTING
              </Typography>
            </Box>
          </Box>

          <Box sx={{ display: 'flex', gap: 1, flex: 1 }}>
            {navItems.map((item) => {
              const isActive = location.pathname === item.path
              const Icon = item.icon
              return (
                <Button
                  key={item.path}
                  component={RouterLink}
                  to={item.path}
                  startIcon={<Icon sx={{ fontSize: 20 }} />}
                  sx={{
                    px: 2.5,
                    py: 1.5,
                    borderRadius: 2,
                    color: isActive ? 'primary.main' : 'text.secondary',
                    bgcolor: isActive ? 'primary.lighter' : 'transparent',
                    fontWeight: isActive ? 600 : 500,
                    '&:hover': {
                      bgcolor: isActive ? 'primary.lighter' : 'action.hover',
                    },
                  }}
                >
                  {item.label}
                </Button>
              )
            })}
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Chip 
              label="Pro" 
              size="small" 
              sx={{ 
                bgcolor: 'secondary.main', 
                color: 'white',
                fontWeight: 600,
                fontSize: '0.7rem',
              }} 
            />
            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
              v1.0.0
            </Typography>
          </Box>
        </Toolbar>
      </Container>
    </AppBar>
  )
}
