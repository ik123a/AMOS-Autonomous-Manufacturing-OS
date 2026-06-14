import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#00d4ff',
      light: '#33ddff',
      dark: '#0099cc',
      contrastText: '#000000',
    },
    secondary: {
      main: '#0066ff',
      light: '#3388ff',
      dark: '#0044cc',
    },
    success: { main: '#00e676', light: '#69f0ae', dark: '#00c853' },
    error: { main: '#ff1744', light: '#ff616f', dark: '#c4001d' },
    warning: { main: '#ff9100', light: '#ffb74d', dark: '#ff6d00' },
    background: { default: '#0a1628', paper: '#1a2332' },
    text: { primary: '#e0e6ed', secondary: '#8896a6', disabled: '#4a5568' },
    divider: '#2a3442',
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", sans-serif',
    h4: { fontWeight: 600, letterSpacing: '-0.02em' },
    h5: { fontWeight: 600, letterSpacing: '-0.01em' },
    h6: { fontWeight: 600 },
    body2: { color: '#8896a6' },
    caption: { fontFamily: '"JetBrains Mono", "Consolas", monospace', fontSize: '0.75rem' },
  },
  shape: { borderRadius: 12 },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          border: '1px solid #2a3442',
          '&:hover': { borderColor: '#3a4a5a' },
        },
      },
    },
    MuiPaper: { styleOverrides: { root: { backgroundImage: 'none' } } },
    MuiChip: { styleOverrides: { root: { fontWeight: 500 } } },
    MuiTableHead: {
      styleOverrides: {
        root: {
          '& .MuiTableCell-head': {
            fontWeight: 600,
            color: '#8896a6',
            textTransform: 'uppercase',
            fontSize: '0.72rem',
            letterSpacing: '0.05em',
            backgroundColor: '#0d1a2a',
          },
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: '#0d1a2a',
          borderRight: '1px solid #2a3442',
        },
      },
    },
  },
});

export default theme;