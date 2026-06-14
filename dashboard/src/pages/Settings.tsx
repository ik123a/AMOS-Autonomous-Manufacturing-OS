import { useState, useEffect } from 'react';
import {
  Box, Typography, Card, CardContent, Slider, Switch, FormControlLabel,
  TextField, Button, Divider, Stack, Chip, Alert, Grid,
} from '@mui/material';
import { getHealth } from '../services/api';
import StatusDot from '../components/StatusDot';

export default function Settings() {
  const [threshold, setThreshold] = useState(0.05);
  const [cooldown, setCooldown] = useState(30);
  const [autoResolve, setAutoResolve] = useState(true);
  const [edgeAlertEnabled, setEdgeAlertEnabled] = useState(true);
  const [apiStatus, setApiStatus] = useState('checking');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getHealth()
      .then(() => setApiStatus('connected'))
      .catch(() => setApiStatus('disconnected'));
  }, []);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <Box>
      <Typography variant="h4" fontWeight={700} gutterBottom sx={{ letterSpacing: '-0.02em' }}>Settings</Typography>
      <Typography variant="body2" color="text.secondary" mb={3}>System configuration, thresholds, and integration settings</Typography>

      {saved && <Alert severity="success" sx={{ mb: 2 }}>Settings saved successfully!</Alert>}

      <Stack spacing={3} maxWidth={700}>
        {/* System Status */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>System Status</Typography>
            <Grid container spacing={3}>
              {[
                { label: 'Ingestion Service', port: '8001', status: 'active' },
                { label: 'TSDB Service', port: '8002', status: 'active' },
                { label: 'Alert Service', port: '8003', status: 'active' },
                { label: 'MLOps Service', port: '8004', status: 'active' },
              ].map((svc) => (
                <Grid item xs={12} sm={6} key={svc.label}>
                  <Box display="flex" alignItems="center" justifyContent="space-between" p={1.5} bgcolor="#0d1a2a" borderRadius={2} border="1px solid #2a3442">
                    <Box>
                      <Typography variant="body2" fontWeight={500}>{svc.label}</Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ fontFamily: '"JetBrains Mono", monospace' }}>localhost:{svc.port}</Typography>
                    </Box>
                    <Chip
                      icon={<StatusDot status={svc.status} size={8} />}
                      label={svc.status}
                      size="small"
                      color="success"
                      variant="outlined"
                      sx={{ fontSize: '0.7rem' }}
                    />
                  </Box>
                </Grid>
              ))}
            </Grid>
            <Divider sx={{ my: 2 }} />
            <Stack direction="row" spacing={2} alignItems="center">
              <StatusDot status={apiStatus} size={12} />
              <Typography variant="body2">
                Backend: {apiStatus === 'connected' ? 'Connected' : apiStatus === 'disconnected' ? 'Disconnected' : 'Checking...'}
              </Typography>
              <Chip
                label={apiStatus === 'connected' ? 'Online' : 'Offline'}
                color={apiStatus === 'connected' ? 'success' : 'error'}
                size="small"
              />
            </Stack>
          </CardContent>
        </Card>

        {/* Anomaly Detection */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>Anomaly Detection</Typography>
            <Typography variant="body2" color="text.secondary" mb={1}>
              Reconstruction Error Threshold (MSE)
            </Typography>
            <Stack direction="row" alignItems="center" spacing={2} mb={0.5}>
              <Slider
                value={threshold}
                onChange={(_, v) => setThreshold(v as number)}
                min={0.005} max={0.2} step={0.005}
                sx={{ color: threshold < 0.03 ? 'error.main' : threshold < 0.08 ? 'warning.main' : 'success.main', flex: 1 }}
              />
              <Typography fontWeight={700} color="primary.main" sx={{ fontFamily: '"JetBrains Mono", monospace', minWidth: 60 }} textAlign="right">
                {(threshold * 100).toFixed(1)}%
              </Typography>
            </Stack>
            <Typography variant="caption" color="text.secondary">
              Lower = more sensitive alerts · Current: <strong>{threshold < 0.03 ? 'HIGH sensitivity' : threshold < 0.08 ? 'Normal' : 'Low sensitivity'}</strong>
            </Typography>
          </CardContent>
        </Card>

        {/* Alert Behavior */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>Alert Behavior</Typography>
            <Box mb={2}>
              <Typography variant="body2" color="text.secondary" mb={1}>
                Alert Cooldown: <strong>{cooldown}s</strong>
              </Typography>
              <Slider
                value={cooldown}
                onChange={(_, v) => setCooldown(v as number)}
                min={5} max={300} step={5}
                sx={{ color: 'warning.main' }}
              />
              <Typography variant="caption" color="text.secondary">
                Minimum time between alerts from the same device to prevent alert flooding.
              </Typography>
            </Box>
            <Divider sx={{ my: 1.5 }} />
            <FormControlLabel
              control={<Switch checked={autoResolve} onChange={(e) => setAutoResolve(e.target.checked)} color="success" />}
              label="Auto-resolve alerts when anomaly score returns below threshold"
            />
            <Box mt={1}>
              <FormControlLabel
                control={<Switch checked={edgeAlertEnabled} onChange={(e) => setEdgeAlertEnabled(e.target.checked)} color="primary" />}
                label="Enable edge-level local alerting (sub-100ms response)"
              />
            </Box>
          </CardContent>
        </Card>

        {/* Edge Configuration */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>Edge Configuration</Typography>
            {[
              { label: 'MQTT Broker', value: 'mqtt.amos-platform.io:8883' },
              { label: 'OPC-UA Endpoint', value: 'opc.tcp://192.168.1.100:4840' },
              { label: 'Collection Rate', value: '100ms (10Hz)' },
              { label: 'Model Path', value: '/opt/amos/models/anomaly.onnx' },
              { label: 'Data Retention', value: '90 days on-device, unlimited cloud' },
            ].map(({ label, value }) => (
              <Box key={label} display="flex" justifyContent="space-between" py={0.8} borderBottom="1px solid #2a3442">
                <Typography variant="body2" color="text.secondary">{label}</Typography>
                <Typography variant="body2" fontWeight={500} sx={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '0.78rem' }}>
                  {value}
                </Typography>
              </Box>
            ))}
          </CardContent>
        </Card>

        <Button variant="contained" size="large" onClick={handleSave} sx={{ alignSelf: 'flex-start', px: 4, py: 1.2 }}>
          Save Settings
        </Button>
      </Stack>
    </Box>
  );
}