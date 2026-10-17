import { useEffect, useState } from 'react';
import { AssessmentIcon, FilterIcon, RefreshIcon } from '../components/Icons';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useAuth } from '../auth/AuthContext';
import LoadingState from '../components/LoadingState';
import MetricCard from '../components/MetricCard';
import { currentMonth, displayError, formatDate, monthLabel } from '../utils';

export default function ReportsPage() {
  const { user, request } = useAuth();
  const [month, setMonth] = useState(currentMonth);
  const [employeeId, setEmployeeId] = useState('');
  const [employees, setEmployees] = useState([]);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user?.role !== 'admin') return undefined;
    request('/api/v1/admin/employees').then(setEmployees).catch((loadError) => setError(displayError(loadError, 'Unable to load employees.')));
    return undefined;
  }, [request, user?.role]);

  const loadReports = async () => {
    if (!month) return;
    setLoading(true);
    setError('');
    const query = new URLSearchParams({ month });
    if (user?.role === 'admin' && employeeId) query.set('employee_id', employeeId);
    const suffix = query.toString();
    try {
      const [trends, summary, absenteeism] = await Promise.all([
        request(`/api/v1/reports/monthly-trends?${suffix}`),
        request(`/api/v1/reports/attendance-summary?${suffix}`),
        request(`/api/v1/reports/absenteeism?${suffix}`),
      ]);
      setData({ trends, summary, absenteeism });
    } catch (loadError) {
      setError(displayError(loadError, 'Unable to load reports.'));
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadReports(); }, [month, employeeId]);

  const scopeLabel = data?.summary?.scope?.kind === 'all_employees' ? 'All employees' : (employees.find((employee) => employee.id === data?.summary?.scope?.employee_id)?.full_name || 'Employee scope');
  return (
    <>
      <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ sm: 'center' }} gap={2} sx={{ mb: 3 }}>
        <Box><Typography variant="overline" color="primary.main" fontWeight={800}>INSIGHTS</Typography><Typography variant="h4" color="primary.dark">Reports</Typography><Typography color="text.secondary" sx={{ mt: 0.75 }}>A decision-ready view of presence, completion, and absence.</Typography></Box>
        <Button variant="outlined" startIcon={<RefreshIcon />} onClick={loadReports}>Refresh</Button>
      </Stack>
      <Card sx={{ mb: 2.5 }}><CardContent><Stack direction={{ xs: 'column', md: 'row' }} alignItems={{ md: 'center' }} gap={2}><Stack direction="row" alignItems="center" spacing={1}><FilterIcon color="primary" /><Typography fontWeight={800}>Report filters</Typography></Stack><TextField label="Month" type="month" size="small" value={month} onChange={(event) => setMonth(event.target.value)} InputLabelProps={{ shrink: true }} sx={{ minWidth: 190 }} />{user?.role === 'admin' && <FormControl size="small" sx={{ minWidth: 240 }}><InputLabel>Employee scope</InputLabel><Select label="Employee scope" value={employeeId} onChange={(event) => setEmployeeId(event.target.value)}><MenuItem value="">All employees</MenuItem>{employees.map((employee) => <MenuItem key={employee.id} value={employee.id}>{employee.full_name}{employee.is_active ? '' : ' (inactive)'}</MenuItem>)}</Select></FormControl>}<Typography variant="body2" color="text.secondary" sx={{ ml: { md: 'auto' } }}>{data ? `${formatDate(data.summary.period_start)} – ${formatDate(data.summary.period_end)}` : 'Choose a month to begin'}</Typography></Stack></CardContent></Card>
      {error && <Alert severity="error" sx={{ mb: 2.5 }}>{error}</Alert>}
      {loading && !data ? <LoadingState label="Building report…" /> : data && <>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>Showing: <strong>{scopeLabel}</strong> · {monthLabel(data.summary.month)}</Typography>
        <Grid container spacing={2.5} sx={{ mb: 2.5 }}>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}><MetricCard label="Attendance rate" value={data.summary.attendance_rate == null ? '—' : `${data.summary.attendance_rate}%`} helper="Present employee-days" icon={<AssessmentIcon />} /></Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}><MetricCard label="Present days" value={data.summary.present_employee_days} helper={`of ${data.summary.expected_employee_days} expected`} /></Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}><MetricCard label="Incomplete" value={data.summary.incomplete_employee_days} helper="Punch-out missing" color="warning.main" /></Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}><MetricCard label="Absenteeism" value={data.absenteeism.absenteeism_rate == null ? '—' : `${data.absenteeism.absenteeism_rate}%`} helper="Calendar-day basis" color="error.main" /></Grid>
        </Grid>
        <Grid container spacing={2.5}>
          <Grid size={{ xs: 12, lg: 8 }}><Card><CardContent><Typography variant="h6">Daily presence trend</Typography><Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>Every effective day is included, even when there are no records.</Typography><Box sx={{ width: '100%', height: 330 }}><ResponsiveContainer><BarChart data={data.trends.points} margin={{ top: 8, right: 8, left: -24, bottom: 0 }}><CartesianGrid strokeDasharray="3 3" stroke="#e8eef4" /><XAxis dataKey="work_date" tickFormatter={(value) => value.slice(-2)} tick={{ fontSize: 12 }} /><YAxis allowDecimals={false} tick={{ fontSize: 12 }} /><Tooltip labelFormatter={(value) => formatDate(value)} /><Legend /><Bar dataKey="present_count" name="Present" fill="#146c94" radius={[4, 4, 0, 0]} /><Bar dataKey="absent_count" name="Absent" fill="#e6953c" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer></Box></CardContent></Card></Grid>
          <Grid size={{ xs: 12, lg: 4 }}><Card sx={{ height: '100%' }}><CardContent><Typography variant="h6">Report notes</Typography><Stack spacing={2} sx={{ mt: 2 }}><Box><Typography fontWeight={800}>Calendar-day basis</Typography><Typography variant="body2" color="text.secondary">Absence is calculated against every employee-calendar-day. Scheduled shifts, leave, and holidays are not yet modeled.</Typography></Box><Box><Typography fontWeight={800}>Data scope</Typography><Typography variant="body2" color="text.secondary">The backend applies role and employee scope before calculating every metric.</Typography></Box><Box><Typography fontWeight={800}>Completed vs incomplete</Typography><Typography variant="body2" color="text.secondary">Present means punch-in exists. Completed additionally requires punch-out.</Typography></Box></Stack></CardContent></Card></Grid>
        </Grid>
      </>}
    </>
  );
}
