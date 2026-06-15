# AMOS API Reference

Base URL (local): `http://localhost:8001`
Base URL (production): `https://api.amos-platform.io`

## Authentication

All API endpoints (except `/health`) require a Bearer token:

```
Authorization: Bearer <token>
```

Tokens are issued by the auth service and expire after 24 hours. Request one via:

```bash
curl -X POST https://api.amos-platform.io/auth/token \
  -H "Content-Type: application/json" \
  -d '{"client_id": "your-client-id", "client_secret": "your-secret"}'
```

---

## Alert Service — Port 8003

### `GET /health`

Health check (no auth required).

**Response `200`:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "uptime_seconds": 86400
}
```

---

### `GET /api/alerts`

Fetch all alerts, newest first.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | Max alerts to return |
| `offset` | int | 0 | Pagination offset |
| `severity` | string | all | `critical`, `warning`, `info`, or `all` |
| `machine_id` | string | all | Filter by device |
| `since` | ISO8601 | 7 days ago | Start of time window |

**Response `200`:**
```json
{
  "total": 142,
  "offset": 0,
  "alerts": [
    {
      "id": "alt_8f3a2b",
      "device_id": "edge-plant1-001",
      "timestamp": "2024-06-14T08:23:41Z",
      "severity": "critical",
      "sensor_channel": "Spindle_Vibration",
      "anomaly_score": 0.847,
      "threshold": 0.05,
      "recommended_action": "Inspect spindle bearing — possible wear detected",
      "acknowledged": false,
      "acknowledged_by": null,
      "acknowledged_at": null
    }
  ]
}
```

---

### `POST /api/alerts/{id}/acknowledge`

Acknowledge an alert (marks it as seen).

**Request body (optional):**
```json
{
  "comment": "Scheduled for maintenance next Tuesday"
}
```

**Response `200`:**
```json
{
  "id": "alt_8f3a2b",
  "acknowledged": true,
  "acknowledged_by": "operator@plant.com",
  "acknowledged_at": "2024-06-14T10:45:00Z"
}
```

---

### `GET /api/alerts/stats`

Aggregate alert statistics.

**Query parameters:** `since` (ISO8601, default 30 days ago)

**Response `200`:**
```json
{
  "total": 142,
  "by_severity": { "critical": 12, "warning": 89, "info": 41 },
  "by_machine": {
    "edge-plant1-001": 45,
    "edge-plant1-002": 38
  },
  "top_sensors": [
    { "sensor": "Spindle_Vibration", "count": 67 },
    { "sensor": "Spindle_Temperature", "count": 43 }
  ]
}
```

---

## TSDB Service — Port 8002

### `GET /health`

Health check (no auth required).

---

### `GET /api/machines`

List all registered machines and their latest health scores.

**Response `200`:**
```json
{
  "machines": [
    {
      "device_id": "edge-plant1-001",
      "machine_name": "CNC-Machine-04",
      "location": "Building-A-Line-3",
      "health_score": 87,
      "status": "healthy",
      "last_seen": "2024-06-14T08:23:00Z",
      "active_alerts": 2,
      "uptime_hours": 720.4
    }
  ]
}
```

---

### `GET /api/machines/{device_id}`

Detailed view for a single machine.

**Response `200`:**
```json
{
  "device_id": "edge-plant1-001",
  "machine_name": "CNC-Machine-04",
  "location": "Building-A-Line-3",
  "health_score": 87,
  "status": "healthy",
  "last_seen": "2024-06-14T08:23:00Z",
  "uptime_hours": 720.4,
  "active_alerts": 2,
  "sensors": [
    {
      "name": "Spindle_Vibration",
      "unit": "mm/s",
      "current_value": 2.34,
      "normal_range_min": 0.0,
      "normal_range_max": 4.50,
      "last_updated": "2024-06-14T08:22:58Z"
    }
  ],
  "anomaly_history": [
    {
      "timestamp": "2024-06-14T06:12:00Z",
      "score": 0.72,
      "sensor_triggered": "Spindle_Vibration"
    }
  ]
}
```

---

### `GET /api/machines/{device_id}/telemetry`

Fetch raw telemetry for a machine.

**Query parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sensors` | string | Yes | Comma-separated list, e.g. `Spindle_Temperature,Spindle_Vibration` |
| `start` | ISO8601 | Yes | Start of time window |
| `end` | ISO8601 | No | End (defaults to now) |
| `interval` | string | No | `raw`, `1m`, `5m`, `1h` (default `raw`) |
| `limit` | int | No | Max points (default 1000, max 10000) |

**Response `200`:**
```json
{
  "device_id": "edge-plant1-001",
  "start": "2024-06-13T00:00:00Z",
  "end": "2024-06-14T00:00:00Z",
  "interval": "1h",
  "sensors": ["Spindle_Temperature", "Spindle_Vibration"],
  "data": [
    {
      "timestamp": "2024-06-13T01:00:00Z",
      "Spindle_Temperature": 48.2,
      "Spindle_Vibration": 1.87
    }
  ]
}
```

---

### `GET /api/analytics/{device_id}/anomaly-score`

Anomaly score time series for a machine.

**Query parameters:** `start`, `end` (ISO8601), `interval` (default `1h`)

**Response `200`:**
```json
{
  "device_id": "edge-plant1-001",
  "start": "2024-06-07T00:00:00Z",
  "end": "2024-06-14T00:00:00Z",
  "threshold": 0.05,
  "series": [
    { "timestamp": "2024-06-07T01:00:00Z", "score": 0.012, "is_anomaly": false },
    { "timestamp": "2024-06-10T14:23:00Z", "score": 0.72, "is_anomaly": true }
  ]
}
```

---

## Ingestion Service — Port 8001

### `GET /health`

Health check (no auth required).

---

### `GET /api/status`

Ingestion pipeline status.

**Response `200`:**
```json
{
  "kafka_connected": true,
  "mqtt_connected": 12,
  "messages_per_second": 847.3,
  "queue_depth": 0
}
```

---

## MLOps Service — Port 8004

### `GET /health`

Health check (no auth required).

---

### `GET /api/models`

List registered models in the model registry.

**Response `200`:**
```json
{
  "models": [
    {
      "name": "anomaly_autoencoder_v2",
      "version": 3,
      "stage": "staging",
      "accuracy": 0.974,
      "trained_on_samples": 480000,
      "created_at": "2024-06-10T12:00:00Z",
      "created_by": "ml-pipeline"
    }
  ]
}
```

---

### `POST /api/models/train`

Trigger model retraining on new data.

**Request body:**
```json
{
  "model_name": "anomaly_autoencoder_v2",
  "training_window_days": 14,
  "validation_split": 0.2,
  "epochs": 100
}
```

**Response `202` (async):**
```json
{
  "run_id": "run_4a8f2c",
  "status": "pending",
  "mlflow_run_url": "https://mlflow.amos-platform.io/#/runs/run_4a8f2c"
}
```

---

### `POST /api/models/{name}/promote`

Promote a model from staging to production.

**Request body:**
```json
{
  "version": 3
}
```

**Response `200`:**
```json
{
  "name": "anomaly_autoencoder_v2",
  "version": 3,
  "stage": "production",
  "deployed_to_edge": ["edge-plant1-001", "edge-plant1-002"]
}
```

---

### `GET /api/models/{name}/explain/{timestamp`

Get feature attribution (SHAP values) for a specific anomaly detection event.

**Query parameters:** `timestamp` (ISO8601 of the anomaly event)

**Response `200`:**
```json
{
  "timestamp": "2024-06-14T06:12:00Z",
  "device_id": "edge-plant1-001",
  "anomaly_score": 0.72,
  "shap_values": {
    "Spindle_Temperature": 0.31,
    "Spindle_Vibration": 0.82,
    "Spindle_Torque": -0.05,
    "Coolant_Flow": 0.02
  },
  "top_contributors": [
    { "sensor": "Spindle_Vibration", "contribution": 0.82, "direction": "above_normal" }
  ]
}
```

---

## WebSocket — Real-time Updates

Connect to `wss://api.amos-platform.io/ws` for live updates (JWT required).

**Subscribe to machine updates:**
```json
{"type": "subscribe", "channel": "machines"}
```

**Subscribe to alerts:**
```json
{"type": "subscribe", "channel": "alerts"}
```

**Server events:**
```json
{"type": "alert", "data": {"id": "alt_8f3a2b", "severity": "critical", "device_id": "edge-plant1-001"}}
{"type": "health_score", "data": {"device_id": "edge-plant1-001", "score": 87}}
```

---

## Error Responses

All endpoints return errors in this format:

```json
{
  "error": "not_found",
  "message": "Machine edge-plant1-999 not found",
  "status_code": 404
}
```

| HTTP Code | Error | Meaning |
|-----------|-------|---------|
| 400 | `bad_request` | Invalid parameters |
| 401 | `unauthorized` | Missing or invalid token |
| 403 | `forbidden` | Insufficient permissions |
| 404 | `not_found` | Resource does not exist |
| 429 | `rate_limited` | Too many requests |
| 500 | `internal_error` | Server-side error |
| 503 | `service_unavailable` | Dependency down (Kafka, InfluxDB) |