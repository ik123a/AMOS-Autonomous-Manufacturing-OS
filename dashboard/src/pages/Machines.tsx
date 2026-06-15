import { useState, useEffect } from 'react';
import {
  Box, Typography, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Paper, Collapse, Card, CardContent,
  CircularProgress, Chip, IconButton, Tooltip,
} from '@mui/material';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import { getMachines, getMachineSummary, Machine, MachineSummary } from '../services/api';
import StatusDot from '../components/StatusDot';

const DEMO_MACHINES: Machine[] = [
  { device_id: 'edge-plant1-001', status: 'healthy',    last_seen: new Date().toISOString(),                        sensor_count: 8, avg_health_score: 97 },
  { device_id: 'edge-plant1-002', status: 'healthy',    last_seen: new Date(Date.now() - 15000).toISOString(),      sensor_count: 6, avg_health_score: 94 },
  { device_id: 'edge-plant1-003', status: 'degraded',    last_seen: new Date(Date.now() - 120000).toISOString(),     sensor_count: 8, avg_health_score: 71 },
  { device_id: 'edge-plant1-004', status: 'healthy',     last_seen: new Date(Date.now() - 5000).toISOString(),       sensor_count: 10, avg_health_score: 98 },
  { device_id: 'edge-plant1-005', status: 'critical',    last_seen: new Date(Date.now() - 30000).toISOString(),      sensor_count: 8, avg_health_score: 34 },
  { device_id: 'edge-plant1-006', status: 'healthy',     last_seen: new Date().toISOString(),                         sensor_count: 6, avg_health_score: 91 },
  { device_id: 'edge-plant1-007', status: 'offline',     last_seen: new Date(Date.now() - 3600000).toISOString(),    sensor_count: 8, avg_health_score: 0  },
  { device_id: 'edge-plant1-008', status: 'healthy',    last_seen: new Date(Date.now() - 20000).toISOString(),      sensor_count: 6, avg_health_score: 95 },
];

const statusConfig: Record<string, { label: string; color: string }> = {
  healthy:  { label: 'Healthy',  color: '#00e676' },
  online:   { label: 'Online',   color: '#00e676' },
  running:  { label: 'Running',  color: '#00e676' },
  degraded: { label: 'Degraded', color: '#ff9100' },
  warning:  { label: 'Warning',  color: '#ff9100' },
  critical: { label: 'Critical', color: '#ff1744' },
  error:    { label: 'Error',    color: '#ff1744' },
  offline:  { label: 'Offline',  color: '#4a5568' },
  unknown:  { label: 'Unknown',  color: '#8896a6' },
};

function RowDetail({ machineId }: { machineId: string }) {
  const [summary, setSummary] = useState<MachineSummary | null>(null);
  useEffect(() => {
    getMachineSummary(machineId)
      .then(setSummary)
      .catch(() => setSummary({ device_id: machineId, sensor_count: 8, avg_value: 52.3, period: '7d' }));
  }, [machineId]);
  return (
    <Box sx={{ px: 3, py: 2.5, backgroundColor: '#0d1a2a' }}>
      <Card variant="outlined" sx={{ borderColor: '#2a3442' }}>
        <CardContent sx={{ pb: '16px !important' }}>
          <Typography variant="subtitle2" fontWeight={600} color="primary.main" mb={2}>
            Machine Details — {machineId}
          </Typography>
          <Box display="grid" gridTemplateColumns="repeat(auto-fill, minmax(160px, 1fr))" gap={2}>
            {[
              { label: 'Sensors', value: summary?.sensor_count ?? '—' },
              { label: 'Avg Value (7d)', value: summary?.avg_value != null ? summary.avg_value.toFixed(2) : '—' },
              { label: 'Period', value: summary?.period ?? '—' },
              { label: 'Data Retention', value: '90 days' },
              { label: 'Last Model Update', value: '2h ago' },
              { label: 'Anomaly Threshold', value: '0.05' },
            ].map(({ label, value }) => (
              <Box key={label}>
                <Typography variant="caption" color="text.secondary" display="block">{label}</Typography>
                <Typography variant="body2" fontWeight={600} sx={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '0.8rem' }}>
                  {value}
                </Typography>
              </Box>
            ))}
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}

export default function Machines() {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMachines()
      .then((m) => setMachines(m.length ? m : DEMO_MACHINES))
      .catch(() => setMachines(DEMO_MACHINES))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh"><CircularProgress sx={{ color: 'primary.main' }} /></Box>;
  }

  return (
    <Box>
      <Typography variant="h4" fontWeight={700} gutterBottom sx={{ letterSpacing: '-0.02em' }}>
        Machine Management
      </Typography>
      <Typography variant="body2" color="text.secondary" mb={3}>
        {machines.length} connected edge devices · Click any row to expand details
      </Typography>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell width={40} />
              <TableCell>Device ID</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Health Score</TableCell>
              <TableCell>Sensors</TableCell>
              <TableCell>Last Seen</TableCell>
              <TableCell>Uptime</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {machines.map((machine) => {
              const cfg = statusConfig[machine.status] ?? statusConfig.unknown;
              const healthScore = machine.avg_health_score ?? 0;
              const healthColor = healthScore >= 90 ? '#00e676' : healthScore >= 70 ? '#ff9100' : '#ff1744';

              return (
                <>
                  <TableRow
                    key={machine.device_id}
                    hover
                    onClick={() => setExpanded(expanded === machine.device_id ? null : machine.device_id)}
                    sx={{ cursor: 'pointer', '& > *': { borderBottom: expanded === machine.device_id ? 'none' : undefined } }}
                  >
                    <TableCell>
                      <IconButton size="small">
                        {expanded === machine.device_id ? <KeyboardArrowUpIcon fontSize="small" /> : <KeyboardArrowDownIcon fontSize="small" />}
                      </IconButton>
                    </TableCell>
                    <TableCell>
                      <Box display="flex" alignItems="center" gap={1.5}>
                        <StatusDot status={machine.status} size={10} />
                        <Typography fontWeight={600} sx={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '0.82rem' }}>
                          {machine.device_id}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={cfg.label}
                        size="small"
                        sx={{ backgroundColor: `${cfg.color}18`, color: cfg.color, fontWeight: 600, fontSize: '0.72rem' }}
                      />
                    </TableCell>
                    <TableCell>
                      <Box display="flex" alignItems="center" gap={1}>
                        <Box sx={{ width: 60, height: 6, borderRadius: 3, backgroundColor: '#2a3442', overflow: 'hidden' }}>
                          <Box sx={{ width: `${healthScore}%`, height: '100%', backgroundColor: healthColor, borderRadius: 3, transition: 'width 0.5s ease' }} />
                        </Box>
                        <Typography fontWeight={700} color={healthColor} sx={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '0.8rem' }}>
                          {healthScore}%
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontFamily: '"JetBrains Mono", monospace' }}>
                        {machine.sensor_count ?? '—'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary" sx={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '0.75rem' }}>
                        {machine.last_seen ? new Date(machine.last_seen).toLocaleTimeString() : 'Unknown'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {Math.floor((Date.now() - new Date(machine.last_seen).getTime()) / 60000)}m
                      </Typography>
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell colSpan={7} sx={{ p: 0 }}>
                      <Collapse in={expanded === machine.device_id} timeout="auto" unmountOnExit>
                        <RowDetail machineId={machine.device_id} />
                      </Collapse>
                    </TableCell>
                  </TableRow>
                </>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}