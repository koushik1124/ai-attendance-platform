import { useEffect, useState } from 'react';
import { AccessTimeIcon, GroupIcon, HowToRegIcon, LoginIcon, PercentIcon, PersonAddIcon, RefreshIcon, TrendingUpIcon } from '../components/Icons';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { ApiError } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import LoadingState from '../components/LoadingState';
import MetricCard from '../components/MetricCard';
import { currentMonth, displayError, formatDate, formatDateTime, monthLabel } from '../utils';

function PageHeading({ eyebrow, title, subtitle, action }) {
  return (
    <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ sm: 'center' }} gap={2} sx={{ mb: 3 }}>
      <Box>
        <Typography variant="overline" color="primary.main" fontWeight={800}>{eyebrow}</Typography>
        <Typography variant="h4" color="primary.dark">{title}</Typography>
        <Typography color="text.secondary" sx={{ mt: 0.75 }}>{subtitle}</Typography>
      </Box>
      {action}
    </Stack>
  );
}

function ChartCard({ points, title, subtitle }) {
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Typography variant="h6">{title}</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>{subtitle}</Typography>
        {points?.length ? (
          <Box sx={{ width: '100%', height: 270 }}>
            <ResponsiveContainer>
              <AreaChart data={points} margin={{ top: 8, right: 8, left: -24, bottom: 0 }}>
                <defs><linearGradient id="presentFill" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#146c94" stopOpacity={0.28} /><stop offset="95%" stopColor="#146c94" stopOpacity={0} /></linearGradient></defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e8eef4" />
                <XAxis dataKey="work_date" tickFormatter={(value) => value.slice(-2)} tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                <Tooltip labelFormatter={(value) => formatDate(value)} />
                <Area type="monotone" dataKey="present_count" name="Present" stroke="#146c94" fill="url(#presentFill)" strokeWidth={3} />
                <Area type="monotone" dataKey="absent_count" name="Absent" stroke="#e6953c" fill="none" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </Box>
        ) : <Typography color="text.secondary" sx={{ py: 10, textAlign: 'center' }}>No trend data is available.</Typography>}
      </CardContent>
    </Card>
  );
}

function AdminDashboard() {
  const { request, user } = useAuth();
  const [month] = useState(currentMonth);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({ email: '', full_name: '', password: '' });
  const [formError, setFormError] = useState('');
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setBusy(true);
    setError('');
    try {
      const [summary, trends, employees] = await Promise.all([
        request(`/api/v1/reports/attendance-summary?month=${month}`),
        request(`/api/v1/reports/monthly-trends?month=${month}`),
        request('/api/v1/admin/employees'),
      ]);
      setData({ summary, trends, employees });
    } catch (loadError) {
      setError(displayError(loadError, 'Unable to load the admin dashboard.'));
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => { load(); }, [month]);

  const createEmployee = async (event) => {
    event.preventDefault();
    setSaving(true);
    setFormError('');
    try {
      await request('/api/v1/admin/employees', { method: 'POST', body: form });
      setDialogOpen(false);
      setForm({ email: '', full_name: '', password: '' });
      await load();
    } catch (saveError) {
      setFormError(saveError instanceof ApiError ? saveError.message : 'Unable to create employee.');
    } finally {
      setSaving(false);
    }
  };

  const toggleEmployee = async (employee) => {
    try {
      await request(`/api/v1/admin/employees/${employee.id}/status`, { method: 'PATCH', body: { is_active: !employee.is_active } });
      await load();
    } catch (toggleError) {
      setError(displayError(toggleError));
    }
  };

  const deleteEmployee = async (employee) => {
    if (!window.confirm(`Delete ${employee.full_name}? This is only permitted when attendance history does not exist.`)) return;
    try {
      await request(`/api/v1/admin/employees/${employee.id}`, { method: 'DELETE' });
      await load();
    } catch (deleteError) {
      setError(displayError(deleteError));
    }
  };

  if (busy && !data) return <LoadingState label="Loading admin workspace…" />;
  const summary = data?.summary;
  return (
    <>
      <PageHeading
        eyebrow="ADMINISTRATION"
        title={`Good morning, ${user?.full_name?.split(' ')[0] || 'admin'}`}
        subtitle={`A verified view of workforce attendance for ${monthLabel(month)}.`}
        action={<Button variant="outlined" startIcon={<RefreshIcon />} onClick={load}>Refresh</Button>}
      />
      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}
      <Grid container spacing={2.5} sx={{ mb: 2.5 }}>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}><MetricCard label="Attendance rate" value={summary?.attendance_rate == null ? '—' : `${summary.attendance_rate}%`} helper={`${summary?.present_employee_days ?? 0} present employee-days`} icon={<PercentIcon />} /></Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}><MetricCard label="Present days" value={summary?.present_employee_days ?? '—'} helper={`of ${summary?.expected_employee_days ?? 0} expected`} icon={<HowToRegIcon />} color="success.main" /></Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}><MetricCard label="Incomplete" value={summary?.incomplete_employee_days ?? '—'} helper="Punch-out still needed" icon={<AccessTimeIcon />} color="warning.main" /></Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}><MetricCard label="Employees" value={data?.employees?.length ?? '—'} helper="Managed accounts" icon={<GroupIcon />} color="primary.dark" /></Grid>
      </Grid>
      <Grid container spacing={2.5} sx={{ mb: 2.5 }}>
        <Grid size={{ xs: 12, lg: 8 }}><ChartCard points={data?.trends?.points} title="Attendance trend" subtitle="Present and absent employee-days across the selected month." /></Grid>
        <Grid size={{ xs: 12, lg: 4 }}>
          <Card sx={{ height: '100%' }}><CardContent><Typography variant="h6">Operational pulse</Typography><Typography color="text.secondary" variant="body2" sx={{ mb: 2 }}>What needs attention today.</Typography>
            <Stack spacing={1.5}>
              <Box sx={{ p: 1.5, borderRadius: 3, bgcolor: '#eef8f4' }}><Typography variant="body2" color="success.dark" fontWeight={800}>Completed</Typography><Typography variant="h5">{summary?.completed_employee_days ?? 0}</Typography><Typography variant="caption" color="text.secondary">Completed employee-days this month</Typography></Box>
              <Box sx={{ p: 1.5, borderRadius: 3, bgcolor: '#fff7e9' }}><Typography variant="body2" color="warning.dark" fontWeight={800}>Absence</Typography><Typography variant="h5">{summary?.absent_employee_days ?? 0}</Typography><Typography variant="caption" color="text.secondary">Calendar-day absences in scope</Typography></Box>
            </Stack>
          </CardContent></Card>
        </Grid>
      </Grid>
      <Card><CardContent>
        <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ sm: 'center' }} gap={2} sx={{ mb: 2 }}>
          <Box><Typography variant="h6">Employee management</Typography><Typography variant="body2" color="text.secondary">Create, activate, deactivate, or safely remove employee accounts.</Typography></Box>
          <Button variant="contained" startIcon={<PersonAddIcon />} onClick={() => { setFormError(''); setDialogOpen(true); }}>Add employee</Button>
        </Stack>
        {!data?.employees?.length ? <Typography color="text.secondary" sx={{ py: 3 }}>No employee accounts exist yet.</Typography> : <TableContainer component={Paper} variant="outlined"><Table><TableHead><TableRow><TableCell>Employee</TableCell><TableCell>Email</TableCell><TableCell>Status</TableCell><TableCell align="right">Actions</TableCell></TableRow></TableHead><TableBody>{data.employees.map((employee) => <TableRow key={employee.id} hover><TableCell><Typography fontWeight={750}>{employee.full_name}</Typography><Typography variant="caption" color="text.secondary">ID #{employee.id}</Typography></TableCell><TableCell>{employee.email}</TableCell><TableCell><Chip size="small" label={employee.is_active ? 'Active' : 'Inactive'} color={employee.is_active ? 'success' : 'default'} /></TableCell><TableCell align="right"><Stack direction="row" justifyContent="flex-end" gap={1}><Button size="small" onClick={() => toggleEmployee(employee)}>{employee.is_active ? 'Deactivate' : 'Activate'}</Button><Button size="small" color="error" onClick={() => deleteEmployee(employee)}>Delete</Button></Stack></TableCell></TableRow>)}</TableBody></Table></TableContainer>}
      </CardContent></Card>
      <Dialog open={dialogOpen} onClose={() => !saving && setDialogOpen(false)} fullWidth maxWidth="sm"><Box component="form" onSubmit={createEmployee}><DialogTitle>Add employee account</DialogTitle><DialogContent><Stack spacing={2} sx={{ pt: 1 }}><TextField label="Full name" required value={form.full_name} onChange={(event) => setForm({ ...form, full_name: event.target.value })} /><TextField label="Work email" type="email" required value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /><TextField label="Temporary password" type="password" required helperText="At least 8 characters" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} />{formError && <Alert severity="error">{formError}</Alert>}</Stack></DialogContent><DialogActions><Button onClick={() => setDialogOpen(false)} disabled={saving}>Cancel</Button><Button type="submit" variant="contained" disabled={saving}>{saving ? 'Creating…' : 'Create employee'}</Button></DialogActions></Box></Dialog>
    </>
  );
}

function EmployeeDashboard() {
  const { request } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(true);
  const [actionBusy, setActionBusy] = useState(false);
  const month = currentMonth();

  const load = async () => {
    setBusy(true);
    setError('');
    try {
      const [current, summary, history] = await Promise.all([
        request('/api/v1/attendance/current'),
        request(`/api/v1/reports/attendance-summary?month=${month}`),
        request('/api/v1/attendance/history?limit=10'),
      ]);
      setData({ current, summary, history });
    } catch (loadError) {
      setError(displayError(loadError, 'Unable to load your attendance workspace.'));
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => { load(); }, []);

  const punch = async (actionType) => {
    if (actionBusy) return;
    setActionBusy(true);
    setError('');
    try {
      const endpoint = (actionType === 'out' || data?.current?.status === 'punched_in')
        ? '/api/v1/attendance/punch-out'
        : '/api/v1/attendance/punch-in';
      await request(endpoint, { method: 'POST' });
      await load();
    } catch (punchError) {
      setError(displayError(punchError));
    } finally {
      setActionBusy(false);
    }
  };

  if (busy && !data) return <LoadingState label="Loading your workspace…" />;
  const state = data?.current;
  const isNotStarted = !state?.status || state?.status === 'not_started';
  const isIn = state?.status === 'punched_in';
  const isDone = state?.status === 'punched_out';
  return (
    <>
      <PageHeading eyebrow="MY ATTENDANCE" title="Your workday, at a glance" subtitle="Punch actions and history are always scoped to your account." action={<Button variant="outlined" startIcon={<RefreshIcon />} onClick={load}>Refresh</Button>} />
      {error && <Alert severity="error" onClose={() => setError('')} sx={{ mb: 3 }}>{error}</Alert>}
      <Grid container spacing={2.5} sx={{ mb: 2.5 }}>
        <Grid size={{ xs: 12, md: 5 }}>
          <Card
            sx={{
              height: '100%',
              background: 'linear-gradient(145deg, #0b4058, #146c94)',
              color: 'white',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
            }}
          >
            <CardContent sx={{ p: 3 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                <Box>
                  <Typography variant="overline" sx={{ color: 'rgba(255,255,255,.7)', fontWeight: 800 }}>
                    TODAY
                  </Typography>
                  <Typography variant="h5" sx={{ mt: 0.5, fontWeight: 700 }}>
                    Attendance status
                  </Typography>
                  <Typography sx={{ color: 'rgba(255,255,255,.75)', mt: 0.5 }}>
                    {formatDate(state?.work_date)}
                  </Typography>
                </Box>
                <Chip
                  label={
                    isNotStarted ? 'Not started' : isIn ? 'Punched in' : isDone ? 'Day completed' : (state?.status?.replace('_', ' ') || 'Unavailable')
                  }
                  sx={{
                    color: isDone ? '#1b5e20' : isIn ? '#e65100' : 'white',
                    bgcolor: isDone ? '#c8e6c9' : isIn ? '#ffe0b2' : 'rgba(255,255,255,.16)',
                    fontWeight: 700,
                    textTransform: 'capitalize',
                  }}
                />
              </Stack>

              <Box sx={{ mt: 2.5, p: 2, borderRadius: 2, bgcolor: 'rgba(0,0,0,0.15)' }}>
                <Stack spacing={1}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.75)' }}>
                      Punch in:
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {state?.attendance?.punch_in_at
                        ? formatDateTime(state.attendance.punch_in_at)
                        : isNotStarted
                        ? 'Pending'
                        : '—'}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.75)' }}>
                      Punch out:
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {state?.attendance?.punch_out_at
                        ? formatDateTime(state.attendance.punch_out_at)
                        : isIn
                        ? 'In progress'
                        : 'Pending'}
                    </Typography>
                  </Box>
                  {state?.attendance?.working_hours != null && (
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.75)' }}>
                        Working hours:
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: 700, color: '#a5d6a7' }}>
                        {state.attendance.working_hours} hrs
                      </Typography>
                    </Box>
                  )}
                </Stack>
              </Box>

              <Box sx={{ mt: 2.5 }}>
                {isNotStarted && (
                  <Button
                    id="punch-in-button"
                    fullWidth
                    variant="contained"
                    color="secondary"
                    size="large"
                    startIcon={<LoginIcon />}
                    disabled={actionBusy}
                    onClick={() => punch('in')}
                    sx={{
                      py: 1.25,
                      fontWeight: 750,
                      color: 'primary.dark',
                      boxShadow: '0 4px 14px rgba(0,0,0,0.25)',
                    }}
                  >
                    {actionBusy ? 'Punching in…' : 'Punch in'}
                  </Button>
                )}

                {isIn && (
                  <Button
                    id="punch-out-button"
                    fullWidth
                    variant="contained"
                    size="large"
                    startIcon={<AccessTimeIcon />}
                    disabled={actionBusy}
                    onClick={() => punch('out')}
                    sx={{
                      py: 1.25,
                      fontWeight: 750,
                      bgcolor: '#ff9800',
                      color: '#1a202c',
                      '&:hover': { bgcolor: '#f57c00' },
                      boxShadow: '0 4px 14px rgba(0,0,0,0.25)',
                    }}
                  >
                    {actionBusy ? 'Punching out…' : 'Punch out'}
                  </Button>
                )}

                {isDone && (
                  <>
                    <Button
                      id="day-completed-button"
                      fullWidth
                      variant="contained"
                      size="large"
                      disabled
                      startIcon={<HowToRegIcon />}
                      sx={{
                        py: 1.25,
                        fontWeight: 750,
                        '&.Mui-disabled': {
                          bgcolor: 'rgba(255, 255, 255, 0.16)',
                          color: 'rgba(255, 255, 255, 0.9)',
                          border: '1px solid rgba(255, 255, 255, 0.25)',
                        },
                      }}
                    >
                      Day completed
                    </Button>
                    <Typography
                      variant="caption"
                      sx={{
                        display: 'block',
                        mt: 1,
                        color: 'rgba(255,255,255,0.75)',
                        textAlign: 'center',
                      }}
                    >
                      Both punches recorded for today. Shifts cannot be re-opened.
                    </Typography>
                  </>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 7 }}><Grid container spacing={2.5} sx={{ height: '100%' }}><Grid size={{ xs: 12, sm: 6 }}><MetricCard label="Attendance rate" value={data?.summary?.attendance_rate == null ? '—' : `${data.summary.attendance_rate}%`} helper={`${data?.summary?.present_employee_days ?? 0} present days this month`} icon={<TrendingUpIcon />} /></Grid><Grid size={{ xs: 12, sm: 6 }}><MetricCard label="Completed days" value={data?.summary?.completed_employee_days ?? '—'} helper="Both punches recorded" icon={<HowToRegIcon />} color="success.main" /></Grid><Grid size={{ xs: 12, sm: 6 }}><MetricCard label="Incomplete days" value={data?.summary?.incomplete_employee_days ?? '—'} helper="Punch-out still needed" icon={<AccessTimeIcon />} color="warning.main" /></Grid><Grid size={{ xs: 12, sm: 6 }}><MetricCard label="Absent days" value={data?.summary?.absent_employee_days ?? '—'} helper={data?.summary?.basis === 'scheduled_days' ? 'Scheduled-day basis' : 'Calendar-day basis'} icon={<PercentIcon />} color="error.main" /></Grid></Grid></Grid>
      </Grid>
      <Card><CardContent><Typography variant="h6">Recent attendance</Typography><Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>Your latest attendance records, newest first.</Typography>{!data?.history?.length ? <Typography color="text.secondary" sx={{ py: 3 }}>No attendance records yet. Use Punch in to start your workday.</Typography> : <TableContainer component={Paper} variant="outlined"><Table><TableHead><TableRow><TableCell>Work date</TableCell><TableCell>Punch in</TableCell><TableCell>Punch out</TableCell><TableCell>Duration</TableCell><TableCell>Status</TableCell></TableRow></TableHead><TableBody>{data.history.map((record) => <TableRow key={record.id}><TableCell>{formatDate(record.work_date)}</TableCell><TableCell>{formatDateTime(record.punch_in_at)}</TableCell><TableCell>{formatDateTime(record.punch_out_at)}</TableCell><TableCell>{record.working_hours != null ? `${record.working_hours} hrs` : '—'}</TableCell><TableCell><Chip size="small" label={record.punch_out_at ? 'Complete' : record.punch_in_at ? 'In progress' : 'Not started'} color={record.punch_out_at ? 'success' : record.punch_in_at ? 'warning' : 'default'} /></TableCell></TableRow>)}</TableBody></Table></TableContainer>}</CardContent></Card>
    </>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  return user?.role === 'admin' ? <AdminDashboard /> : <EmployeeDashboard />;
}
