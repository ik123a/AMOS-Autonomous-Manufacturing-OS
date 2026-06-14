import { useLocation, useNavigate } from 'react-router-dom';
import {
  Drawer, List, ListItemButton, ListItemIcon, ListItemText,
  Typography, Box, Divider, Chip,
} from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import PrecisionManufacturingIcon from '@mui/icons-material/PrecisionManufacturing';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import TimelineIcon from '@mui/icons-material/Timeline';
import SettingsIcon from '@mui/icons-material/Settings';

const DRAWER_WIDTH = 240;

const navItems = [
  { path: '/', label: 'Dashboard', icon: <DashboardIcon /> },
  { path: '/machines', label: 'Machines', icon: <PrecisionManufacturingIcon /> },
  { path: '/alerts', label: 'Alerts', icon: <NotificationsActiveIcon /> },
  { path: '/analytics', label: 'Analytics', icon: <TimelineIcon /> },
  { path: '/settings', label: 'Settings', icon: <SettingsIcon /> },
];

export default function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: DRAWER_WIDTH,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: DRAWER_WIDTH,
          boxSizing: 'border-box',
          borderRight: '1px solid #2a3442',
          backgroundColor: '#0d1a2a',
        },
      }}
    >
      {/* Logo Header */}
      <Box sx={{ p: 2.5, display: 'flex', alignItems: 'center', gap: 1.5 }} onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
        <Box sx={{
          width: 38, height: 38, borderRadius: 2,
          background: 'linear-gradient(135deg, #00d4ff 0%, #0066ff 100%)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontWeight: 800, fontSize: '1rem', color: '#000', flexShrink: 0,
        }}>
          A
        </Box>
        <Box>
          <Typography variant="subtitle1" fontWeight={700} fontSize="1rem" color="primary.main" letterSpacing="0.05em">
            AMOS
          </Typography>
          <Typography variant="caption" color="text.secondary" fontSize="0.62rem">
            Autonomous Manufacturing OS
          </Typography>
        </Box>
      </Box>

      <Divider sx={{ borderColor: '#2a3442' }} />

      {/* Nav Items */}
      <List sx={{ px: 1.5, mt: 1.5 }}>
        {navItems.map((item) => {
          const active = location.pathname === item.path;
          return (
            <ListItemButton
              key={item.path}
              onClick={() => navigate(item.path)}
              sx={{
                borderRadius: 2, mb: 0.5, py: 1,
                backgroundColor: active ? 'rgba(0, 212, 255, 0.10)' : 'transparent',
                borderLeft: active ? '3px solid #00d4ff' : '3px solid transparent',
                '&:hover': {
                  backgroundColor: active ? 'rgba(0, 212, 255, 0.14)' : 'rgba(255, 255, 255, 0.04)',
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: 38, color: active ? '#00d4ff' : '#8896a6' }}>
                {item.icon}
              </ListItemIcon>
              <ListItemText
                primary={item.label}
                primaryTypographyProps={{
                  fontSize: '0.85rem',
                  fontWeight: active ? 600 : 400,
                  color: active ? '#e0e6ed' : '#8896a6',
                }}
              />
              {active && (
                <Chip label="LIVE" size="small" sx={{ height: 18, fontSize: '0.6rem', backgroundColor: 'rgba(0, 212, 255, 0.2)', color: '#00d4ff', fontWeight: 700 }} />
              )}
            </ListItemButton>
          );
        })}
      </List>

      {/* Footer */}
      <Box sx={{ mt: 'auto', p: 2, borderTop: '1px solid #2a3442' }}>
        <Typography variant="caption" color="text.secondary" fontSize="0.65rem">
          AMOS v0.1.0 · Edge-First AI Platform
        </Typography>
      </Box>
    </Drawer>
  );
}