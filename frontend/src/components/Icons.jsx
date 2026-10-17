import { SvgIcon } from '@mui/material';

const icon = (path) => function DashboardIcon(props) {
  return <SvgIcon {...props}><path d={path} /></SvgIcon>;
};

export const MenuIcon = icon('M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z');
export const DashboardIcon = icon('M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z');
export const AssessmentIcon = icon('M5 19h4V5H5v14zm5 0h4V3h-4v16zm5 0h4v-8h-4v8z');
export const MessageIcon = icon('M20 4H4c-1.1 0-2 .9-2 2v12l4-3h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2z');
export const PeopleIcon = icon('M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5s-3 1.34-3 3 1.34 3 3 3zM8 11c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5 5 6.34 5 8s1.34 3 3 3zm8 2c-2 0-6 1-6 3v3h12v-3c0-2-4-3-6-3zM8 13c-2.33 0-6 1.17-6 3v3h4v-3c0-1.1.75-2.14 2.03-2.75L8 13z');
export const LogoutIcon = icon('M10 17l5-5-5-5v3H2v4h8v3zm9-14H5c-1.1 0-2 .9-2 2v3h2V5h14v14H5v-3H3v3c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z');
export const LockIcon = icon('M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1S15.1 4.29 15.1 6v2z');
export const LoginIcon = icon('M11 7l-1.4 1.4 2.6 2.6H3v2h9.2l-2.6 2.6L11 17l5-5-5-5zm8-4H13v2h6v14h-6v2h6c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z');
export const ShieldIcon = icon('M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V6.3l7-3.11v8.8z');
export const AccessTimeIcon = icon('M11 7h2v5.17l4.25 2.52-1 1.65-5.25-3.17V7zm1-5a10 10 0 100 20 10 10 0 000-20zm0 18a8 8 0 110-16 8 8 0 010 16z');
export const GroupIcon = PeopleIcon;
export const HowToRegIcon = icon('M9 11c1.66 0 3-1.34 3-3S10.66 5 9 5 6 6.34 6 8s1.34 3 3 3zm0 2c-2 0-6 1-6 3v2h12v-2c0-2-4-3-6-3zm8-5V5h-2v3h-3v2h3v3h2v-3h3V8h-3z');
export const PercentIcon = icon('M7.5 4A2.5 2.5 0 105 6.5 2.5 2.5 0 007.5 4zM5 6.5a1 1 0 112 0 1 1 0 01-2 0zM16.5 15A2.5 2.5 0 1019 17.5a2.5 2.5 0 00-2.5-2.5zm0 3.5a1 1 0 111-1 1 1 0 01-1 1zM5.7 19L17.7 5l1.6 1.3-12 14L5.7 19z');
export const PersonAddIcon = icon('M15 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm-9-2V7H4v3H1v2h3v3h2v-3h3v-2H6zm9 4c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z');
export const RefreshIcon = icon('M17.65 6.35A7.95 7.95 0 0012 4c-4.42 0-7.99 3.58-7.99 8S7.58 20 12 20c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z');
export const TrendingUpIcon = icon('M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6z');
export const FilterIcon = icon('M10 18h4v-2h-4v2zM3 6v2h18V6H3zm3 7h12v-2H6v2z');
export const AutoAwesomeIcon = icon('M19 9l1.25-2.75L23 5l-2.75-1.25L19 1l-1.25 2.75L15 5l2.75 1.25L19 9zM19 15l-1.25 2.75L15 19l2.75 1.25L19 23l1.25-2.75L23 19l-2.75-1.25L19 15zM11.5 9.5L9 4 6.5 9.5 1 12l5.5 2.5L9 20l2.5-5.5L17 12l-5.5-2.5z');
