import { createTheme } from '@mui/material/styles';

export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#146c94', dark: '#0b4058', light: '#3e9bc2' },
    secondary: { main: '#e6953c' },
    background: { default: '#f4f7fb', paper: '#ffffff' },
    text: { primary: '#172b4d', secondary: '#61738b' },
    success: { main: '#18866b' },
    warning: { main: '#c47716' },
    error: { main: '#c44747' },
  },
  typography: {
    fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    h4: { fontWeight: 800, letterSpacing: '-0.03em' },
    h5: { fontWeight: 750, letterSpacing: '-0.025em' },
    h6: { fontWeight: 750 },
    button: { textTransform: 'none', fontWeight: 700 },
  },
  shape: { borderRadius: 14 },
  components: {
    MuiCard: { styleOverrides: { root: { border: '1px solid #e5ebf2', boxShadow: '0 8px 24px rgba(31, 55, 78, 0.06)' } } },
    MuiButton: { defaultProps: { disableElevation: true } },
    MuiTableCell: { styleOverrides: { head: { fontWeight: 750, color: '#61738b', backgroundColor: '#f8fafc' } } },
  },
});
