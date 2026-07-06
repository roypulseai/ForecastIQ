import type { ReactNode } from 'react';
import { Box, Stack, Typography } from '@mui/material';
import SwapHorizIcon from '@mui/icons-material/SwapHoriz';
import { alpha, useTheme } from '@mui/material/styles';

interface ColumnMapperProps {
  expected: string;
  detected: string;
}

export function ColumnMapper({ expected, detected }: ColumnMapperProps): ReactNode {
  const theme = useTheme();
  return (
    <Box
      sx={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 1,
        p: 1,
        borderRadius: 1.5,
        backgroundColor: 'background.subtle',
      }}
    >
      <Stack alignItems="flex-end" spacing={0}>
        <Typography variant="caption" color="text.secondary">
          expected
        </Typography>
        <Typography variant="body2" sx={{ fontWeight: 600 }}>
          {expected}
        </Typography>
      </Stack>
      <Box
        sx={{
          color: theme.palette.primary.main,
          backgroundColor: alpha(theme.palette.primary.main, 0.1),
          borderRadius: 1,
          p: 0.5,
          display: 'flex',
        }}
        aria-hidden
      >
        <SwapHorizIcon fontSize="small" />
      </Box>
      <Stack alignItems="flex-start" spacing={0}>
        <Typography variant="caption" color="text.secondary">
          detected
        </Typography>
        <Typography variant="body2" sx={{ fontWeight: 600 }}>
          {detected}
        </Typography>
      </Stack>
    </Box>
  );
}
