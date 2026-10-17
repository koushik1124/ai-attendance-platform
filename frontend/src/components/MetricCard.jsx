import { Card, CardContent, Stack, Typography } from '@mui/material';

export default function MetricCard({ label, value, helper, icon, color = 'primary.main' }) {
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={2}>
          <Stack spacing={0.5}>
            <Typography variant="body2" color="text.secondary" fontWeight={700}>{label}</Typography>
            <Typography variant="h4" sx={{ color }}>{value}</Typography>
            {helper && <Typography variant="caption" color="text.secondary">{helper}</Typography>}
          </Stack>
          {icon && <Stack sx={{ color, bgcolor: 'action.hover', p: 1.25, borderRadius: 3 }}>{icon}</Stack>}
        </Stack>
      </CardContent>
    </Card>
  );
}
