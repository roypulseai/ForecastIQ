import { createTheme, alpha, type ThemeOptions } from '@mui/material/styles';

const palette = {
  primary: { main: '#2563eb', light: '#60a5fa', dark: '#1d4ed8', lighter: '#dbeafe' },
  secondary: { main: '#7c3aed', light: '#a78bfa', dark: '#5b21b6', lighter: '#ede9fe' },
  success: { main: '#10b981', light: '#34d399', dark: '#047857', lighter: '#d1fae5' },
  warning: { main: '#f59e0b', light: '#fbbf24', dark: '#b45309', lighter: '#fef3c7' },
  error: { main: '#ef4444', light: '#f87171', dark: '#b91c1c', lighter: '#fee2e2' },
  info: { main: '#0ea5e9', light: '#38bdf8', dark: '#0369a1', lighter: '#e0f2fe' },
};

declare module '@mui/material/styles' {
  interface PaletteColor {
    lighter?: string;
  }
  interface TypeBackground {
    subtle?: string;
  }
}

const themeOptions: ThemeOptions = {
  palette: {
    mode: 'light',
    primary: palette.primary,
    secondary: palette.secondary,
    success: palette.success,
    warning: palette.warning,
    error: palette.error,
    info: palette.info,
    background: {
      default: '#f9fafb',
      paper: '#ffffff',
      ...{ subtle: '#f3f4f6' },
    },
    text: {
      primary: '#111827',
      secondary: '#6b7280',
    },
    divider: '#e5e7eb',
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: { fontWeight: 700, fontSize: '2.25rem', lineHeight: 1.2 },
    h2: { fontWeight: 700, fontSize: '1.875rem', lineHeight: 1.25 },
    h3: { fontWeight: 600, fontSize: '1.5rem', lineHeight: 1.3 },
    h4: { fontWeight: 600, fontSize: '1.25rem', lineHeight: 1.35 },
    h5: { fontWeight: 600, fontSize: '1.125rem', lineHeight: 1.4 },
    h6: { fontWeight: 600, fontSize: '1rem', lineHeight: 1.4 },
    body1: { fontSize: '0.9375rem', lineHeight: 1.5 },
    body2: { fontSize: '0.875rem', lineHeight: 1.5 },
    button: { fontWeight: 600, textTransform: 'none' },
  },
  shape: { borderRadius: 10 },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: { backgroundColor: '#f9fafb' },
        '*::-webkit-scrollbar': { width: 8, height: 8 },
        '*::-webkit-scrollbar-track': { background: '#f1f5f9' },
        '*::-webkit-scrollbar-thumb': {
          background: '#cbd5e1',
          borderRadius: 4,
        },
        '*::-webkit-scrollbar-thumb:hover': { background: '#94a3b8' },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          padding: '8px 18px',
          transition: 'all 200ms ease',
        },
        contained: {
          boxShadow: 'none',
          '&:hover': { boxShadow: '0 4px 12px rgba(37, 99, 235, 0.25)' },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.06)',
          border: '1px solid #f3f4f6',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: { backgroundImage: 'none' },
        rounded: { borderRadius: 12 },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { borderRadius: 6, fontWeight: 500 },
      },
    },
    MuiTextField: {
      defaultProps: { size: 'small' },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: { borderRadius: 8 },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: { borderBottom: '1px solid #f3f4f6' },
        head: { fontWeight: 600, backgroundColor: '#f9fafb', color: '#374151' },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          backgroundColor: '#111827',
          fontSize: '0.75rem',
          padding: '6px 10px',
        },
      },
    },
  },
};

export const theme = createTheme(themeOptions);

export const brandColors = {
  primary: palette.primary,
  secondary: palette.secondary,
  success: palette.success,
  warning: palette.warning,
  error: palette.error,
};

export const alphaColor = (color: string, value: number) => alpha(color, value);
