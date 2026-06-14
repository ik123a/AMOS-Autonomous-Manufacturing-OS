import axios from 'axios';

const client = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

export interface Machine {
  device_id: string;
  status: string;
  last_seen: string;
  sensor_count?: number;
  avg_health_score?: number;
}

export interface SensorReading {
  timestamp: string;
  value: number;
}

export interface TimeseriesResponse {
  device_id: string;
  sensor_name: string;
  points: SensorReading[];
}

export interface Alert {
  id: string;
  device_id: string;
  sensor_name: string;
  anomaly_score: number;
  severity: string;
  status: string;
  message: string;
  value: number;
  threshold: number;
  recommended_action?: string;
  created_at: string;
  acknowledged_at?: string;
  resolved_at?: string;
}

export interface MachineSummary {
  device_id: string;
  sensor_count: number;
  avg_value: number;
  period: string;
}

// ─── API Functions ───────────────────────────────────────

export async function getHealth(): Promise<{ service: string; status: string }> {
  const res = await client.get('/health');
  return res.data;
}

export async function getMachines(): Promise<Machine[]> {
  const res = await client.get('/machines');
  return res.data.machines || [];
}

export async function getMachineSummary(deviceId: string): Promise<MachineSummary> {
  const res = await client.get(`/summary/${deviceId}`);
  return res.data;
}

export async function getTimeseries(
  deviceId: string,
  sensorName?: string,
  start = '-7d',
  stop = 'now()'
): Promise<TimeseriesResponse> {
  const res = await client.get('/timeseries', {
    params: { device_id: deviceId, sensor_name: sensorName, start, stop },
  });
  return res.data;
}

export async function getAlerts(
  deviceId?: string,
  status?: string,
  severity?: string
): Promise<{ alerts: Alert[]; total: number }> {
  const res = await client.get('/alerts', {
    params: { device_id: deviceId, status, severity },
  });
  return res.data;
}

export async function acknowledgeAlert(alertId: string): Promise<Alert> {
  const res = await client.put(`/alerts/${alertId}/acknowledge`, {
    acknowledged_by: 'dashboard-operator',
  });
  return res.data;
}

export async function resolveAlert(alertId: string): Promise<Alert> {
  const res = await client.post(`/alerts/${alertId}/resolve`, {
    resolved_by: 'dashboard-operator',
    resolution_notes: 'Resolved from AMOS dashboard',
  });
  return res.data;
}

export default client;