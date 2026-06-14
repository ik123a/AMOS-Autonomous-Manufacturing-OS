import { useState, useEffect } from 'react';
import {
  Box, Grid, Typography, Card, CardContent, List, ListItem,
  ListItemText, CircularProgress, Alert as MuiAlert,
} from '@mui/material';
import { getMachines, getAlerts, Machine, Alert } from '../services/api';
import HealthCard from '../components/HealthCard';
import AlertBadge from '../components/AlertBadge';
import StatusDot from '../components/StatusDot';
import { useNavigate } from 'react-router-dom';

const DEMO_MACHINES: Machine[] = [
  { device_id: 'edge-plant1-001', status: 'healthy', last_seen: new Date().toISOString(), sensor_count: 8, avg_health_score: 97 },
  { device_id: 'edge-plant1-002', status: 'healthy', last_seen: new Date(Date.now() - 15000).toISOString(), sensor_count: 6, avg_health_score: 94 },
  { device_id: 'edge-plant1-003', status: 'degraded', last_seen: new Date(Date.now() - 120000).toISOString(), sensor_count: 8, avg_health_score: 71 },
  { device_id: 'edge-plant1-004', status: 'healthy', last_seen: new Date(Date.now() - 5000).toISOString(), sensor_count: 10, avg_health_score: 98 },
  { device_id: 'edge-plant1-005', status: 'critical', last_seen: new Date(Date.now() - 30000).toISOString(), sensor_count: 8, avg_health_score: 34 },
  { device_id: 'edge-plant1-006', status: 'healthy', last_seen: new Date().toISOString(), sensor_count: 6, avg_health_score: 91 },
];

export default function Dashboard() {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([getMachines(), getAlerts(undefined, 'new').catch(() => ({ alerts: [] as Alert[], total: 0 }))])
      .then(([m, a]) => {
        setMachines(m.length ? m : DEMO_MACHINES);
        setAlerts(a.alerts.slice(0, 8));
      })
      .catch(() => {
        setError('Backend unavailable — showing demo data');
        setMachines(DEMO_MACHINES);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress sx={{ color: 'primary.main' }} />
      </Box>
    );
  }

  const onlineCount = machines.filter((m) => ['healthy', 'online', 'running'].includes(m.status)).length;
  const criticalCount = machines.filter((m) => ['critical', 'error'].includes(m.status)).length;
  const avgHealth = machines.length
    ? Math.round(machines.reduce((s, m) => s + (m.avg_health_score ?? 0), 0) / machines.length)
    : 0;

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={3}>
        <Box>
          <Typography variant="h4" fontWeight={700} gutterBottom sx={{ letterSpacing: '-0.02em' }}>
            Factory Overview
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Real-time health monitoring · {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </Typography>
        </Box>
        {error && (
          <MuiAlert severity="info" sx={{ maxWidth: 320 }} onClose={() => setError(null)}>
            {error}
          </MuiAlert>
        )}
      </Box>

      {/* Stats Bar */}
      <Grid container spacing={2} mb={3}>
        {[
          { label: 'Total Devices', value: machines.length, color: 'primary.main', icon: null },
          { label: 'Online', value: onlineCount, color: 'success.main', icon: null },
          { label: 'Avg Health', value: `${avgHealth}%`, color: avgHealth >= 85 ? 'success.main' : avgHealth >= 65 ? 'warning.main' : 'error.main', icon: null },
          { label: 'Active Alerts', value: alerts.length, color: alerts.length > 0 ? 'error.main' : 'success.main', icon: null },
        ].map((stat, i) => (
          <Grid item xs={6} sm={3} key={i}>
            <Card>
              <CardContent sx={{ textAlign: 'center', py: 2.5, '&:last-child': { pb: 2.5 } }}>
                <Typography variant="h3" fontWeight={800} color={stat.color} sx={{ fontFamily: '"JetBrains Mono", monospace', lineHeight: 1 }}>
                  {stat.value}
                </Typography>
                <Typography variant="body2" color="text.secondary" mt={0.5}>
                  {stat.label}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Machine Health Grid */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6" fontWeight={600}>Machine Health</Typography>
        <Typography
          variant="body2" color="primary.main" sx={{ cursor: 'pointer', '&:hover': { textDecoration: 'underline' } }}
          onClick={() => navigate('/machines')}
        >
          View all →
        </Typography>
      </Box>
      <Grid container spacing={2} mb={4}>
        {machines.map((machine) => (
          <Grid item xs={12} sm={6} lg={4} xl={3} key={machine.device_id}>
            <HealthCard
              deviceId={machine.device_id}
              status={machine.status}
              lastSeen={machine.last_seen}
              sensorCount={machine.sensor_count}
              healthScore={machine.avg_health_score}
              onClick={() => navigate('/machines')}
            />
          </Grid>
        ))}
      </Grid>

      {/* Recent Alerts */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6" fontWeight={600}>Recent Alerts</Typography>
        <Typography
          variant="body2" color="primary.main" sx={{ cursor: 'pointer', '&:hover': { textDecoration: 'underline' } }}
          onClick={() => navigate('/alerts')}
        >
          View all →
        </Typography>
      </Box>
      <Card>
        <List disablePadding>
          {alerts.length === 0 ? (
            <ListItem>
              <Box display="flex" alignItems="center" gap={1.5} py={1}>
                <StatusDot status="healthy" size={10} />
                <ListItemText primary="No active alerts" secondary="All systems operating within normal parameters" primaryTypographyProps={{ color: 'success.main', fontWeight: 500 }} />
              </Box>
            </ListItem>
          ) : (
            alerts.map((alert, i) => (
              <ListItem key={alert.id} divider={i < alerts.length - 1} sx={{ py: 1.5 }}>
                <Box display="flex" alignItems="center" gap={1.5} width="100%">
                  <StatusDot status={alert.severity === 'critical' ? 'critical' : alert.severity === 'high' ? 'critical' : 'degraded'} size={8} pulse={alert.severity === 'critical'} />
                  <Box flex={1} minWidth={0}>
                    <Typography variant="body2" fontWeight={500} noWrap>
                      {alert.message}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ fontFamily: '"JetBrains Mono", monospace' }}>
                      {alert.device_id} · {alert.sensor_name} · {new Date(alert.created_at).toLocaleTimeString()}
                    </Typography>
                  </Box>
                  <AlertBadge severity={alert.severity} />
                </Box>
              </ListItem>
            ))
          )}
        </List>
      </Card>
    </Box>
  );
}