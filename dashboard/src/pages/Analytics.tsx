import { useState, useEffect } from 'react';
import {
  Box, Typography, Grid, Card, CardContent, TextField, MenuItem,
  CircularProgress, Stack,
} from '@mui/material';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, Legend,
} from 'recharts';
import { getMachines, getTimeseries, Machine } from '../services/api';

const SENSORS = ['Temperature', 'Vibration', 'Torque', 'Pressure', 'Current_Draw'];
const DEMO_MACHINES: Machine[] = [
  { device_id: 'edge-plant1-001', status: 'healthy', last_seen: new Date().toISOString() },
  { device_id: 'edge-plant1-002', status: 'healthy', last_seen: new Date().toISOString() },
  { device_id: 'edge-plant1-003', status: 'degraded', last_seen: new Date().toISOString() },
];

function genDemoData(sensor: string, days = 7) {
  const bases: Record<string, number> = { Temperature: 62, Vibration: 7.2, Torque: 35, Pressure: 4.5, Current_Draw: 28 };
  const base = bases[sensor] ?? 50;
  const pts: { time: string; value: number }[] = [];
  const count = days * 24;
  for (let i = 0; i < count; i++) {
    const d = new Date(Date.now() - (count - i) * 3600000);
    const trend = i / count * 3;
    const noise = Math.sin(i * 0.4) * (base * 0.1) + (Math.random() - 0.5) * (base * 0.05);
    const spike = i > count * 0.85 && i < count * 0.87 ? base * 0.4 : 0;
    pts.push({ time: d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit' }), value: Math.round((base + trend + noise + spike) * 100) / 100 });
  }
  return pts;
}

function genAnomalyScore() {
  const pts: { time: string; score: number }[] = [];
  const count = 168;
  for (let i = 0; i < count; i++) {
    const d = new Date(Date.now() - (count - i) * 3600000);
    const base = 0.01 + Math.random() * 0.02;
    const spike = i > count * 0.85 ? 0.35 + Math.random() * 0.2 : 0;
    pts.push({ time: d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit' }), score: Math.min(base + spike, 1) });
  }
  return pts;
}

export default function Analytics() {
  const [machines, setMachines] = useState<Machine[]>(DEMO_MACHINES);
  const [selected, setSelected] = useState('edge-plant1-001');
  const [sensor, setSensor] = useState('Temperature');
  const [data, setData] = useState<{ time: string; value: number }[]>([]);
  const [anomalyData, setAnomalyData] = useState<{ time: string; score: number }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMachines()
      .then((m) => m.length && setMachines(m))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const ts = await getTimeseries(selected, sensor, '-7d', 'now()');
        setData(ts.points.length ? ts.points.map((p: { timestamp: string; value: number }) => ({ time: new Date(p.timestamp).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit' }), value: p.value })) : genDemoData(sensor));
      } catch {
        setData(genDemoData(sensor));
      }
      setAnomalyData(genAnomalyScore());
      setLoading(false);
    };
    load();
  }, [selected, sensor]);

  const stats = data.length > 1 ? {
    current: data[data.length - 1]?.value,
    avg: (data.reduce((s, d) => s + d.value, 0) / data.length).toFixed(2),
    max: Math.max(...data.map((d) => d.value)).toFixed(2),
    min: Math.min(...data.map((d) => d.value)).toFixed(2),
    std: Math.sqrt(data.reduce((s, d) => s + Math.pow(d.value - Number((data.reduce((s2, d2) => s2 + d2.value, 0) / data.length).toFixed(2)), 2), 0) / data.length).toFixed(2),
  } : { current: 0, avg: '0', max: '0', min: '0', std: '0' };

  return (
    <Box>
      <Typography variant="h4" fontWeight={700} gutterBottom sx={{ letterSpacing: '-0.02em' }}>Analytics</Typography>
      <Typography variant="body2" color="text.secondary" mb={3}>Sensor trends and anomaly scoring over time</Typography>

      <Stack direction="row" spacing={2} mb={3} flexWrap="wrap">
        <TextField select label="Machine" value={selected} onChange={(e) => setSelected(e.target.value)} size="small" sx={{ minWidth: 210 }}>
          {machines.map((m) => <MenuItem key={m.device_id} value={m.device_id}>{m.device_id}</MenuItem>)}
        </TextField>
        <TextField select label="Sensor" value={sensor} onChange={(e) => setSensor(e.target.value)} size="small" sx={{ minWidth: 170 }}>
          {SENSORS.map((s) => <MenuItem key={s} value={s}>{s}</MenuItem>)}
        </TextField>
      </Stack>

      {loading ? (
        <Box display="flex" justifyContent="center" py={8}><CircularProgress sx={{ color: 'primary.main' }} /></Box>
      ) : (
        <>
          {/* Stats */}
          <Grid container spacing={2} mb={3}>
            {[
              { label: 'Current', value: stats.current, unit: sensor === 'Temperature' ? '°C' : sensor === 'Pressure' ? 'bar' : sensor === 'Current_Draw' ? 'A' : sensor === 'Vibration' ? 'mm/s' : 'Nm', color: 'primary.main' },
              { label: 'Average', value: stats.avg, unit: '', color: 'text.primary' },
              { label: 'Maximum', value: stats.max, unit: '', color: 'error.main' },
              { label: 'Minimum', value: stats.min, unit: '', color: 'success.main' },
            ].map((s) => (
              <Grid item xs={6} sm={3} key={s.label}>
                <Card><CardContent sx={{ textAlign: 'center', py: 2, '&:last-child': { pb: 2 } }}>
                  <Typography variant="caption" color="text.secondary">{s.label}</Typography>
                  <Typography variant="h5" fontWeight={800} color={s.color} sx={{ fontFamily: '"JetBrains Mono", monospace' }}>
                    {typeof s.value === 'number' ? s.value.toFixed(2) : s.value}{s.unit}
                  </Typography>
                </CardContent></Card>
              </Grid>
            ))}
          </Grid>

          {/* Sensor Trend Chart */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>{sensor} Trend — {selected}</Typography>
              <ResponsiveContainer width="100%" height={340}>
                <AreaChart data={data}>
                  <defs>
                    <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#00d4ff" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#00d4ff" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a3442" />
                  <XAxis dataKey="time" tick={{ fill: '#8896a6', fontSize: 10 }} tickLine={false} axisLine={{ stroke: '#2a3442' }} interval={Math.floor(data.length / 8)} />
                  <YAxis tick={{ fill: '#8896a6', fontSize: 10 }} tickLine={false} axisLine={{ stroke: '#2a3442' }} />
                  <Tooltip contentStyle={{ backgroundColor: '#1a2332', border: '1px solid #2a3442', borderRadius: 8, color: '#e0e6ed' }} />
                  <Area type="monotone" dataKey="value" stroke="#00d4ff" fill="url(#g)" strokeWidth={2} name={sensor} />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Anomaly Score Timeline */}
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Anomaly Score — {selected}</Typography>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={anomalyData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a3442" />
                  <XAxis dataKey="time" tick={{ fill: '#8896a6', fontSize: 9 }} tickLine={false} interval={Math.floor(anomalyData.length / 6)} />
                  <YAxis tick={{ fill: '#8896a6', fontSize: 10 }} tickLine={false} domain={[0, 1]} />
                  <Tooltip contentStyle={{ backgroundColor: '#1a2332', border: '1px solid #2a3442', borderRadius: 8, color: '#e0e6ed' }} />
                  <Legend />
                  <Line type="monotone" dataKey="score" stroke="#ff9100" strokeWidth={1.5} dot={false} name="Anomaly Score" />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </>
      )}
    </Box>
  );
}