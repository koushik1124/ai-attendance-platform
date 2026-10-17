import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { AssessmentIcon, DashboardIcon, MenuIcon, MessageIcon, PeopleIcon, LogoutIcon } from './Icons';
import {
  AppBar,
  Avatar,
  Box,
  Chip,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Stack,
  Toolbar,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import { useAuth } from '../auth/AuthContext';

const drawerWidth = 250;

function Navigation({ items, onNavigate }) {
  return (
    <List sx={{ px: 1.5, py: 2 }}>
      {items.map((item) => (
        <ListItemButton
          key={item.to}
          component={NavLink}
          to={item.to}
          onClick={onNavigate}
          sx={{ borderRadius: 2.5, mb: 0.75, '&.active': { bgcolor: 'primary.main', color: 'white', '& .MuiListItemIcon-root': { color: 'white' } } }}
        >
          <ListItemIcon sx={{ minWidth: 38, color: 'text.secondary' }}>{item.icon}</ListItemIcon>
          <ListItemText primary={item.label} />
        </ListItemButton>
      ))}
    </List>
  );
}

export default function AppShell() {
  const theme = useTheme();
  const mobile = useMediaQuery(theme.breakpoints.down('md'));
  const [open, setOpen] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const items = [
    { label: user?.role === 'admin' ? 'Admin dashboard' : 'My dashboard', to: '/dashboard', icon: user?.role === 'admin' ? <PeopleIcon /> : <DashboardIcon /> },
    { label: 'Reports', to: '/reports', icon: <AssessmentIcon /> },
    { label: 'Assistant', to: '/assistant', icon: <MessageIcon /> },
  ];

  const drawer = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Stack direction="row" alignItems="center" spacing={1.25} sx={{ px: 2.5, py: 2.5 }}>
        <Avatar sx={{ bgcolor: 'secondary.main', color: '#172b4d', fontWeight: 900 }}>A</Avatar>
        <Box>
          <Typography fontWeight={900} color="primary.dark">Attendly</Typography>
          <Typography variant="caption" color="text.secondary">Operations console</Typography>
        </Box>
      </Stack>
      <Divider />
      <Navigation items={items} onNavigate={() => mobile && setOpen(false)} />
      <Box sx={{ mt: 'auto', p: 2 }}>
        <Box sx={{ bgcolor: '#f3f7fa', p: 1.5, borderRadius: 3 }}>
          <Typography variant="caption" color="text.secondary">Signed in as</Typography>
          <Typography variant="body2" fontWeight={800} noWrap>{user?.full_name}</Typography>
          <Chip size="small" label={user?.role === 'admin' ? 'Administrator' : 'Employee'} sx={{ mt: 1 }} />
        </Box>
      </Box>
    </Box>
  );

  const signOut = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppBar position="fixed" color="inherit" elevation={0} sx={{ borderBottom: '1px solid #e5ebf2', bgcolor: 'rgba(255,255,255,0.92)', backdropFilter: 'blur(12px)' }}>
        <Toolbar sx={{ minHeight: { xs: 68, md: 76 }, pl: { md: `${drawerWidth + 28}px` }, pr: { xs: 2, md: 4 } }}>
          {mobile && <IconButton onClick={() => setOpen(true)} edge="start" sx={{ mr: 1 }}><MenuIcon /></IconButton>}
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="body2" color="text.secondary">Attendance management</Typography>
            <Typography variant="h6" color="primary.dark">{user?.role === 'admin' ? 'Admin workspace' : 'My workspace'}</Typography>
          </Box>
          <Tooltip title="Sign out"><IconButton onClick={signOut} color="primary"><LogoutIcon /></IconButton></Tooltip>
        </Toolbar>
      </AppBar>
      {!mobile && <Drawer variant="permanent" open sx={{ width: drawerWidth, flexShrink: 0, '& .MuiDrawer-paper': { width: drawerWidth, boxSizing: 'border-box', borderRight: '1px solid #e5ebf2' } }}>{drawer}</Drawer>}
      {mobile && <Drawer variant="temporary" open={open} onClose={() => setOpen(false)} ModalProps={{ keepMounted: true }} sx={{ '& .MuiDrawer-paper': { width: drawerWidth } }}>{drawer}</Drawer>}
      <Box component="main" sx={{ flexGrow: 1, width: { md: `calc(100% - ${drawerWidth}px)` }, pt: { xs: 10, md: 12 }, px: { xs: 2, sm: 3, lg: 5 }, pb: 5 }}>
        <Outlet />
      </Box>
    </Box>
  );
}
