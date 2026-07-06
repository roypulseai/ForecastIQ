import type { ReactNode } from 'react';
import { Box, Container, Stack, Typography } from '@mui/material';

interface PageContainerProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl';
  disableGutter?: boolean;
}

export function PageContainer({
  title,
  subtitle,
  actions,
  children,
  maxWidth = 'xl',
  disableGutter = false,
}: PageContainerProps): ReactNode {
  return (
    <Container maxWidth={maxWidth} disableGutters={disableGutter} sx={{ py: { xs: 3, md: 4 } }}>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        alignItems={{ xs: 'flex-start', sm: 'center' }}
        justifyContent="space-between"
        spacing={2}
        sx={{ mb: 3 }}
      >
        <Box>
          <Typography variant="h3" component="h1" gutterBottom={Boolean(subtitle)}>
            {title}
          </Typography>
          {subtitle && (
            <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 720 }}>
              {subtitle}
            </Typography>
          )}
        </Box>
        {actions && <Box sx={{ flexShrink: 0 }}>{actions}</Box>}
      </Stack>
      {children}
    </Container>
  );
}
