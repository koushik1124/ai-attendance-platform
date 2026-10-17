import { Box, CircularProgress, Typography } from '@mui/material';

export default function LoadingState({ label = 'Loading…', minHeight = 180 }) {
  return (
    <Box sx={{ minHeight, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1.5 }}>
      <CircularProgress size={24} />
      <Typography color="text.secondary">{label}</Typography>
    </Box>
  );
}
