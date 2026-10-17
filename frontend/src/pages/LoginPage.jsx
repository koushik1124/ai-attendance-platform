import { useState } from 'react';
import { LockIcon, LoginIcon, ShieldIcon } from '../components/Icons';
import {
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Divider,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import { ApiError } from '../api/client';
import { useAuth } from '../auth/AuthContext';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setError('');
    setBusy(true);
    try {
      await login(form.email, form.password);
      navigate(location.state?.from || '/dashboard', { replace: true });
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : 'Unable to sign in.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center', p: 2, background: 'linear-gradient(135deg, #eff7fb 0%, #f7f9fc 55%, #fff7eb 100%)' }}>
      <Card sx={{ width: '100%', maxWidth: 1040, overflow: 'hidden' }}>
        <Stack direction={{ xs: 'column', md: 'row' }}>
          <Box sx={{ flex: 1, p: { xs: 3, md: 6 }, bgcolor: 'primary.dark', color: 'white', position: 'relative' }}>
            <Stack spacing={4} sx={{ position: 'relative', zIndex: 1 }}>
              <Stack direction="row" alignItems="center" spacing={1.5}>
                <Avatar sx={{ bgcolor: 'secondary.main', color: 'primary.dark', fontWeight: 900 }}>A</Avatar>
                <Typography variant="h6" fontWeight={900}>Attendly</Typography>
              </Stack>
              <Box>
                <Typography variant="h3" sx={{ fontWeight: 900, lineHeight: 1.05, mb: 2 }}>Make every workday count.</Typography>
                <Typography sx={{ color: 'rgba(255,255,255,.76)', maxWidth: 420 }}>A clear operational view of people, attendance, and the decisions that keep your team moving.</Typography>
              </Box>
              <Stack direction="row" spacing={1.5} alignItems="center">
                <ShieldIcon sx={{ color: 'secondary.light' }} />
                <Typography variant="body2" sx={{ color: 'rgba(255,255,255,.72)' }}>Secure server-side authentication</Typography>
              </Stack>
            </Stack>
          </Box>
          <Box sx={{ flex: 1, p: { xs: 3, md: 6 } }}>
            <Stack spacing={3} component="form" onSubmit={submit}>
              <Box>
                <Typography variant="h5" color="primary.dark">Welcome back</Typography>
                <Typography color="text.secondary" sx={{ mt: 0.75 }}>Sign in to your attendance workspace.</Typography>
              </Box>
              {error && <Alert severity="error">{error}</Alert>}
              <TextField label="Work email" type="email" autoComplete="email" required fullWidth value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
              <TextField label="Password" type="password" autoComplete="current-password" required fullWidth value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} />
              <Button type="submit" variant="contained" size="large" startIcon={busy ? <CircularProgress size={18} color="inherit" /> : <LoginIcon />} disabled={busy}>
                {busy ? 'Signing in…' : 'Sign in'}
              </Button>
              <Divider />
              <Stack direction="row" spacing={1} alignItems="center" color="text.secondary">
                <LockIcon fontSize="small" />
                <Typography variant="caption">Your role and access are verified by the backend.</Typography>
              </Stack>
            </Stack>
          </Box>
        </Stack>
      </Card>
    </Box>
  );
}
