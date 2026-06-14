import { useState, useEffect, useCallback } from 'react';
import {
  Box, Typography, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Paper, Button, Stack, TextField, MenuItem,
  CircularProgress, Snackbar, Alert, Chip,
} from '@mui/material';
import { getAlerts, acknowledgeAlert, resolveAlert, Alert as AlertType } from '../services/api';
import AlertBadge from '../components/AlertBadge';
import StatusDot from '../components/StatusDot';

const DEMO_ALERTS: AlertType[] = [
  { id: 'a1', device_id: 'edge-plant1-003', sensor_name: 'Vibration', anomaly_score: 0.12, severity: 'high', status: 'new', message: 'Vibration on Motor-07 exceeded warning threshold (12.3mm/s)', value: 12.3, threshold: 0.05, created_at: new Date(Date.now() - 1800000).toISOString() },
  { id: 'a2', device_id: 'edge-plant1-005', sensor_name: 'Temperature', anomaly_score: 0.31, severity: 'critical', status: 'new', message: 'Spindle temperature critical: 87°C (limit: 85°C)', value: 87.0, threshold: 0.05, recommended_action: 'Immediate shutdown recommended', created_at: new Date(Date.now() - 600000).toISOString() },
  { id: 'a3', device_id: 'edge-plant1-001', sensor_name: 'Cycle_Time', anomaly_score: 0.07, severity: 'medium', status: 'acknowledged', message: 'Cycle time variance increased by 15% from baseline', value: 19.2, threshold: 0.05, created_at: new Date(Date.now() - 7200000).toISOString() },
  { id: 'a4', device_id: 'edge-plant1-002', sensor_name: 'Torque', anomaly_score: 0.04, severity: 'low', status: 'resolved', message: 'Minor torque fluctuation detected on Spindle-03', value: 46.5, threshold: 0.05, created_at: new Date(Date.now() - 14400000).toISOString() },
];

export default function Alerts() {
  const [alerts, setAlerts] = useState<AlertType[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState('');
  const [filterSeverity, setFilterSeverity] = useState('');
  const [snackbar, setSnackbar] = useState<{ open: boolean; msg: string; sev: 'success' | 'error' }>({ open: false, msg: '', sev: 'success' });

  const load = useCallback(async () => {
    try {
      const data = await getAlerts(undefined, filterStatus || undefined, filterSeverity || undefined);
      setAlerts(data.alerts.length ? data.alerts : DEMO_ALERTS);
    } catch {
      setAlerts(DEMO_ALERTS);
    } finally {
      setLoading(false);
    }
  }, [filterStatus, filterSeverity]);

  useEffect(() => { load(); }, [load]);

  const handleAck = async (id: string) => {
    try { await acknowledgeAlert(id); load(); setSnackbar({ open: true, msg: 'Alert acknowledged', sev: 'success' }); }
    catch { setSnackbar({ open: true, msg: 'Failed to acknowledge', sev: 'error' }); }
  };

  const handleResolve = async (id: string) => {
    try { await resolveAlert(id); load(); setSnackbar({ open: true, msg: 'Alert resolved', sev: 'success' }); }
    catch { setSnackbar({ open: true, msg: 'Failed to resolve', sev: 'error' }); }
  };

  const counts = {
    total: alerts.length,
    new: alerts.filter((a) => a.status === 'new').length,
    critical: alerts.filter((a) => a.severity === 'critical').length,
  };

  if (loading) return <Box display="flex" justifyContent="center" mt={8}><CircularProgress sx={{ color: 'primary.main' }} /></Box>;

  return (
    <Box>
      <Typography variant="h4" fontWeight={700} gutterBottom sx={{ letterSpacing: '-0.02em' }}>Alert Management</Typography>
      <Typography variant="body2" color="text.secondary" mb={3}>Monitor and respond to anomaly alerts from all edge devices</Typography>

      {/* Summary chips */}
      <Stack direction="row" spacing={1.5} mb={3}>
        <Chip label={`Total: ${counts.total}`} variant="outlined" size="small" />
        <Chip label={`New: ${counts.new}`} color={counts.new > 0 ? 'error' : undefined} variant={counts.new > 0 ? 'filled' : 'outlined'} size="small" />
        <Chip label={`Critical: ${counts.critical}`} color="error" variant="outlined" size="small" />
      </Stack>

      {/* Filters */}
      <Stack direction="row" spacing={2} mb={3} flexWrap="wrap">
        <TextField select label="Status" value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} size="small" sx={{ minWidth: 150 }}>
          <MenuItem value="">All Status</MenuItem>
          <MenuItem value="new">New</MenuItem>
          <MenuItem value="acknowledged">Acknowledged</MenuItem>
          <MenuItem value="resolved">Resolved</MenuItem>
        </TextField>
        <TextField select label="Severity" value={filterSeverity} onChange={(e) => setFilterSeverity(e.target.value)} size="small" sx={{ minWidth: 150 }}>
          <MenuItem value="">All Severity</MenuItem>
          <MenuItem value="critical">Critical</MenuItem>
          <MenuItem value="high">High</MenuItem>
          <MenuItem value="medium">Medium</MenuItem>
          <MenuItem value="low">Low</MenuItem>
        </TextField>
      </Stack>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Severity</TableCell>
              <TableCell>Device · Sensor</TableCell>
              <TableCell>Message</TableCell>
              <TableCell>Score</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Time</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {alerts.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 6 }}>
                  <Typography variant="body2" color="text.secondary">No alerts match the current filters</Typography>
                </TableCell>
              </TableRow>
            ) : (
              alerts.map((a) => (
                <TableRow key={a.id} hover sx={{ backgroundColor: a.severity === 'critical' ? 'rgba(255, 23, 68, 0.04)' : undefined }}>
                  <TableCell>
                    <Box display="flex" alignItems="center" gap={1}>
                      <StatusDot status={a.severity === 'critical' ? 'critical' : a.severity === 'high' ? 'critical' : 'degraded'} size={8} pulse={a.severity === 'critical'} />
                      <AlertBadge severity={a.severity} />
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography fontWeight={600} sx={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '0.78rem' }}>{a.device_id}</Typography>
                    <Typography variant="caption" color="text.secondary">{a.sensor_name}</Typography>
                  </TableCell>
                  <TableCell sx={{ maxWidth: 320 }}>
                    <Typography variant="body2" sx={{ fontSize: '0.82rem' }}>{a.message}</Typography>
                    {a.recommended_action && (
                      <Typography variant="caption" color="warning.main" display="block" mt={0.5}>
                        → {a.recommended_action}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Typography fontWeight={800} color={a.anomaly_score > 0.1 ? 'error.main' : a.anomaly_score > 0.05 ? 'warning.main' : 'text.secondary'} sx={{ fontFamily: '"JetBrains Mono", monospace' }}>
                      {(a.anomaly_score * 100).toFixed(1)}%
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip label={a.status} size="small" sx={{ fontSize: '0.68rem', textTransform: 'capitalize', backgroundColor: '#2a3442' }} />
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" color="text.secondary" sx={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '0.7rem' }}>
                      {new Date(a.created_at).toLocaleString()}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                      {a.status === 'new' && (
                        <Button size="small" variant="outlined" color="warning" onClick={() => handleAck(a.id)} sx={{ fontSize: '0.72rem', py: 0.3 }}>
                          Acknowledge
                        </Button>
                      )}
                      {a.status !== 'resolved' && (
                        <Button size="small" variant="contained" color="success" onClick={() => handleResolve(a.id)} sx={{ fontSize: '0.72rem', py: 0.3 }}>
                          Resolve
                        </Button>
                      )}
                    </Stack>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Snackbar open={snackbar.open} autoHideDuration={3000} onClose={() => setSnackbar({ ...snackbar, open: false })}>
        <Alert severity={snackbar.sev} onClose={() => setSnackbar({ ...snackbar, open: false })}>{snackbar.msg}</Alert>
      </Snackbar>
    </Box>
  );
}