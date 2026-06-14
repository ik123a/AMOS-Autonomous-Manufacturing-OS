# AMOS API Reference

Base URL: `http://localhost:8002` (local dev) | `https://api.amos-platform.io` (prod)

All endpoints return JSON. Authentication via `Authorization: Bearer <token>` header.

---

## Machine Management

### `GET /api/machines`

Returns all registered machines with their current health scores.

**Response `200`:**
```json
{
  "machines": [
    {
      "id": "edge-plant1-001",
      "name": "CNC-Machine-04",
      "location": "Building-A-Line-3",
      "status": "healthy",
      "health_score": 94,
      "last_seen": "2024-06-14T10:30:00Z",
      "ip_address": "192.168.1.42"
    }
  ],
  "total": 1
}
```

### `GET /api/machines/{machine_id}`

Returns detailed information for a single machine.

**Response `200`:**
```json
{
  "id": "edge-plant1-001",
  "name": "CNC-Machine-04",
  "location": "Building-A-Line-3",
  "status": "healthy",
  "health_score": 94,
  "last_seen": "2024-06-14T10:30:00Z",
  "uptime_seconds": 86400,
  "sensors": ["Spindle_Temperature", "Spindle_Vibration", "Spindle_Torque", "Coolant_Flow", "Cutting_Speed", "Feed_Rate"],
  "mqtt_connected": true,
  "opcua_connected": true,
  "model_loaded": true,
  "cpu_usage_percent": 12.4,
  "memory_usage_percent": 38.7,
  "disk_usage_percent": 22.1
}
```

**Response `404`:**
```json
{ "error": "Machine not found" }
```

---

## Telemetry & Health

### `GET /api/machines/{machine_id}/telemetry`

Returns recent telemetry readings for a machine.

| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `since` | ISO8601 | 1h ago | Start time |
| `limit` | int | 100 | Max readings (max 10000) |

**Response `200`:**
```json
{
  "machine_id": "edge-plant1-001",
  "readings": [
    {
      "timestamp": "2024-06-14T10:29:55Z",
      "Spindle_Temperature": 62.4,
      "Spindle_Vibration": 0.18,
      "Spindle_Torque": 48.2,
      "Coolant_Flow": 8.1,
      "Cutting_Speed": 1200,
      "Feed_Rate": 200
    }
  ],
  "count": 100,
  "period_start": "2024-06-14T09:30:00Z",
  "period_end": "2024-06-14T10:30:00Z"
}
```

### `GET /api/machines/{machine_id}/health`

Returns health history for a machine.

| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `since` | ISO8601 | 24h ago | Start time |

**Response `200`:**
```json
{
  "machine_id": "edge-plant1-001",
  "current": {
    "status": "healthy",
    "uptime_seconds": 86400,
    "cpu_usage_percent": 12.4,
    "memory_usage_percent": 38.7,
    "disk_usage_percent": 22.1,
    "opcua_connected": true,
    "mqtt_connected": true,
    "model_loaded": true
  },
  "history": [
    {
      "timestamp": "2024-06-14T09:30:00Z",
      "status": "healthy",
      "cpu_usage_percent": 11.8,
      "memory_usage_percent": 37.2
    }
  ]
}
```

---

## Alerts

### `GET /api/alerts`

Returns all alerts across all machines.

| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `severity` | string | all | Filter: `critical`, `warning`, `info` |
| `status` | string | all | Filter: `active`, `acknowledged`, `resolved` |
| `since` | ISO8601 | 24h ago | Start time |
| `limit` | int | 50 | Max results (max 200) |

**Response `200`:**
```json
{
  "alerts": [
    {
      "id": "uuid-1234",
      "machine_id": "edge-plant1-001",
      "machine_name": "CNC-Machine-04",
      "severity": "warning",
      "status": "active",
      "anomaly_score": 0.073,
      "threshold": 0.05,
      "triggered_at": "2024-06-14T08:15:00Z",
      "message": "Anomaly detected: vibration elevated",
      "affected_sensors": ["Spindle_Vibration"],
      "recommended_action": "Inspect spindle bearing; check lubrication system"
    }
  ],
  "total": 1,
  "critical_count": 0,
  "warning_count": 1,
  "info_count": 0
}
```

### `PUT /api/alerts/{alert_id}/acknowledge`

Acknowledge an alert (marks it as seen by an operator).

**Response `200`:**
```json
{ "id": "uuid-1234", "status": "acknowledged", "acknowledged_at": "2024-06-14T10:35:00Z" }
```

### `PUT /api/alerts/{alert_id}/resolve`

Resolve an alert manually.

**Request body:**
```json
{ "resolution": "Replaced spindle bearing; vibration returned to normal" }
```

**Response `200`:**
```json
{ "id": "uuid-1234", "status": "resolved", "resolved_at": "2024-06-14T11:00:00Z" }
```

---

## Analytics

### `GET /api/analytics/{machine_id}/anomaly-score`

Returns anomaly score time series for a machine.

| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `since` | ISO8601 | 7d ago | Start time |
| `interval` | string | `5m` | Aggregation interval: `1m`, `5m`, `1h`, `1d` |

**Response `200`:**
```json
{
  "machine_id": "edge-plant1-001",
  "threshold": 0.05,
  "series": [
    { "timestamp": "2024-06-14T00:00:00Z", "score": 0.012, "anomaly": false },
    { "timestamp": "2024-06-14T00:05:00Z", "score": 0.031, "anomaly": false },
    { "timestamp": "2024-06-14T00:10:00Z", "score": 0.073, "anomaly": true }
  ]
}
```

### `GET /api/analytics/{machine_id}/feature-attribution`

Returns which sensors contributed most to an anomaly alert.

**Query params:** `alert_id` (required)

**Response `200`:**
```json
{
  "alert_id": "uuid-1234",
  "machine_id": "edge-plant1-001",
  "attribution": [
    { "sensor": "Spindle_Vibration", "contribution": 0.52, "actual_value": 0.31, "normal_range": "0.05-0.18" },
    { "sensor": "Spindle_Torque", "contribution": 0.31, "actual_value": 61.4, "normal_range": "40-55" },
    { "sensor": "Spindle_Temperature", "contribution": 0.12, "actual_value": 68.2, "normal_range": "55-72" },
    { "sensor": "Coolant_Flow", "contribution": 0.05, "actual_value": 8.1, "normal_range": "7.5-9.0" }
  ],
  "shap_values_computed_at": "2024-06-14T08:15:05Z"
}
```

### `GET /api/analytics/{machine_id}/health-trend`

Returns the machine's overall health score over time.

| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `since` | ISO8601 | 30d ago | Start time |
| `interval` | string | `1d` | Aggregation interval |

**Response `200`:**
```json
{
  "machine_id": "edge-plant1-001",
  "trend": [
    { "date": "2024-06-10", "avg_health_score": 97.2, "alerts": 0 },
    { "date": "2024-06-11", "avg_health_score": 95.8, "alerts": 1 },
    { "date": "2024-06-12", "avg_health_score": 94.1, "alerts": 2 }
  ]
}
```

---

## MLOps (Model Management)

### `GET /api/models`

List all registered anomaly detection models.

**Response `200`:**
```json
{
  "models": [
    {
      "id": "model-uuid-001",
      "name": "anomaly_detector",
      "version": "v2.1.0",
      "uploaded_at": "2024-06-01T00:00:00Z",
      "accuracy_roc_auc": 0.94,
      "false_positive_rate": 0.03,
      "status": "production",
      "target_machine": "CNC-Machine-04"
    }
  ]
}
```

### `POST /api/models/train`

Trigger a new model training run.

**Request body:**
```json
{
  "machine_id": "edge-plant1-001",
  "training_data_start": "2024-04-01T00:00:00Z",
  "training_data_end": "2024-05-31T23:59:59Z",
  "validation_split": 0.2,
  "epochs": 100,
  "learning_rate": 0.001
}
```

**Response `202`:**
```json
{
  "run_id": "mlflow-run-uuid",
  "status": "started",
  "mlflow_ui_url": "http://mlflow:5000/#/experiments/0/runs/mlflow-run-uuid"
}
```

### `GET /api/models/{model_id}/export`

Export a trained model as an ONNX file for edge deployment.

**Response `200`:**
```json
{
  "model_id": "model-uuid-001",
  "onnx_download_url": "/api/models/model-uuid-001/download",
  "signature": {
    "inputs": [{ "name": "input", "shape": [6], "dtype": "float32" }],
    "outputs": [{ "name": "output", "shape": [6], "dtype": "float32" }]
  },
  "model_hash": "sha256:abc123..."
}
```

### `POST /api/models/deploy`

Deploy a model to a specific edge agent.

**Request body:**
```json
{
  "model_id": "model-uuid-001",
  "target_machine_id": "edge-plant1-001"
}
```

**Response `200`:**
```json
{
  "deployment_id": "deploy-uuid",
  "model_id": "model-uuid-001",
  "target_machine_id": "edge-plant1-001",
  "status": "deployed",
  "deployed_at": "2024-06-14T12:00:00Z"
}
```

---

## Webhooks

### `POST /api/webhooks`

Register a webhook to receive real-time alert notifications.

**Request body:**
```json
{
  "url": "https://your-system.com/amos-webhook",
  "events": ["alert.created", "alert.resolved", "machine.health_degraded"],
  "secret": "your-webhook-secret"
}
```

**Response `201`:**
```json
{
  "id": "webhook-uuid",
  "url": "https://your-system.com/amos-webhook",
  "events": ["alert.created", "alert.resolved", "machine.health_degraded"],
  "created_at": "2024-06-14T12:00:00Z"
}
```

Webhook payloads are signed with `X-Amos-Signature: sha256=<hmac>`.

---

## Error Responses

All errors follow this format:

```json
{
  "error": "Human-readable error message",
  "code": "MACHINE_NOT_FOUND",
  "details": {}
}
```

| HTTP Status | Code | Meaning |
|-------------|------|---------|
| 400 | `INVALID_REQUEST` | Malformed request body or params |
| 401 | `UNAUTHORIZED` | Missing or invalid auth token |
| 403 | `FORBIDDEN` | Valid token but insufficient permissions |
| 404 | `MACHINE_NOT_FOUND` | Machine ID does not exist |
| 404 | `ALERT_NOT_FOUND` | Alert ID does not exist |
| 422 | `VALIDATION_ERROR` | Request is valid but business logic rejects it |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Server-side error |