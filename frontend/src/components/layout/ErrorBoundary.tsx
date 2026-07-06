import { Component, type ErrorInfo, type ReactNode } from 'react';
import { Box, Button, Container, Paper, Stack, Typography } from '@mui/material';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import RefreshIcon from '@mui/icons-material/Refresh';
import HomeIcon from '@mui/icons-material/Home';
import { Link } from 'react-router-dom';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  componentStack: string | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, componentStack: null };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('[ErrorBoundary] Caught error:', error, info.componentStack);
    this.setState({ componentStack: info.componentStack ?? null });
  }

  private handleReload = (): void => {
    window.location.reload();
  };

  private handleReset = (): void => {
    this.setState({ hasError: false, error: null, componentStack: null });
  };

  render(): ReactNode {
    if (!this.state.hasError) return this.props.children;

    return (
      <Container maxWidth="md" sx={{ py: 8 }}>
        <Paper sx={{ p: 5, textAlign: 'center' }} elevation={0}>
          <Stack spacing={3} alignItems="center">
            <Box
              sx={{
                width: 72,
                height: 72,
                borderRadius: '50%',
                backgroundColor: 'error.lighter',
                color: 'error.main',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <ErrorOutlineIcon sx={{ fontSize: 40 }} />
            </Box>
            <Box>
              <Typography variant="h4" gutterBottom>
                Something went wrong
              </Typography>
              <Typography variant="body1" color="text.secondary">
                An unexpected error occurred. The page could not be displayed.
              </Typography>
            </Box>
            {this.state.error && (
              <Paper
                variant="outlined"
                sx={{
                  p: 2,
                  width: '100%',
                  textAlign: 'left',
                  backgroundColor: 'background.subtle',
                  maxHeight: 200,
                  overflow: 'auto',
                }}
              >
                <Typography
                  variant="body2"
                  component="pre"
                  sx={{ fontFamily: 'monospace', whiteSpace: 'pre-wrap', m: 0 }}
                >
                  {this.state.error.message}
                </Typography>
              </Paper>
            )}
            <Stack direction="row" spacing={2}>
              <Button variant="outlined" startIcon={<RefreshIcon />} onClick={this.handleReload}>
                Reload page
              </Button>
              <Button
                variant="contained"
                startIcon={<HomeIcon />}
                component={Link}
                to="/dashboard"
                onClick={this.handleReset}
              >
                Go to dashboard
              </Button>
            </Stack>
          </Stack>
        </Paper>
      </Container>
    );
  }
}
