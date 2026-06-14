# AMOS Architecture

## Overview

AMOS (Autonomous Manufacturing OS) is a layered edge-first platform that transforms reactive, siloed factory operations into a predictive autonomous ecosystem. The system spans from physical machine level (edge devices) to plant level (cloud microservices) to fleet level (global ML models).

```
┌─────────────────────────────────────────────────────────┐
│                    FACTORY FLOOR                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │  CNC-04  │  │INJECT-02 │  │CONVEY-01 │               │
│  │ ┌──────┐ │  │ ┌──────┐ │  │ ┌──────┐ │               │
│  │ │ Edge │ │  │ │ Edge │ │  │ │ Edge │ │  Advantech    │
│  │ │Agent │ │  │ │Agent │ │  │ │Agent │ │  UNO-2271G    │
│  │ └──────┘ │  │ └──────┘ │  │ └──────┘ │               │
│  └────┼─────┘  └────┼─────┘  └────┼─────┘               │
│       │MQTT/TLS     │MQTT/TLS     │MQTT/TLS             │
│       └─────────────┴──────┬──────┘                     │
│                           │                             │
│                    Plant Network (OPC-UA/Modbus)        │
└───────────────────────────┼─────────────────────────────┘
                            │ HTTPS/MQTT
┌───────────────────────────┼─────────────────────────────┐
│                    CLOUD CORE                            │
│                           │                             │
│  ┌────────────────────────▼──────────────────────────┐  │
│  │              Kafka (Message Bus)                  │  │
│  │         ingestion → alert → mlops                 │  │
│  └──────┬─────────────────┬─────────────────┬────────┘  │
│         │                 │                 │            │
│  ┌──────▼────┐    ┌───────▼────┐    ┌──────▼────┐      │
│  │ InfluxDB │    │ Alert Svc   │    │  MLflow    │      │
│  │  (TSDB)  │    │ (FastAPI)   │    │(Experiment│      │
│  │           │    │             │    │ Tracker)  │      │
│  └──────┬────┘    └─────────────┘    └───────────┘      │
│         │                                             │
│  ┌──────▼─────────────────────────────────────────┐   │
│  │              Grafana Dashboards                  │   │
│  │         Real-time health, alerts, trends         │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                            │
                   Fleet-wide ML Training
                   (Federated Learning — future)
```

## Component Inventory

### Edge Agent (Rust)

Located at: `edge-agent/`

The digital ear at each machine. Responsible for secure data ingestion, local processing, and low-latency alerting.

| File | Purpose |
|------|---------|
| `src/main.rs` | Entry point; spawns collectors, MQTT, health publisher |
| `src/config.rs` | Full configuration struct + YAML deserialization |
| `src/mqtt.rs` | MQTT client via rumqttc, TLS, reconnect logic |
| `src/inference.rs` | ONNX Runtime autoencoder inference engine |
| `src/health.rs` | System health monitor (CPU, mem, disk, network) |
| `src/collectors/opcua.rs` | OPC-UA data collector (simulated, production-ready interface) |
| `src/collectors/modbus.rs` | Modbus-TCP data collector (same pattern) |

**Data flow at edge:**
```
PLC (OPC-UA/Modbus)
    → Collector (reads raw registers)
    → Inference Engine (ONNX autoencoder)
    → MQTT Client (publishes telemetry + alerts)
    → Cloud Broker
```

**MQTT Topics:**
| Topic | Payload |
|-------|---------|
| `amos/{device_id}/telemetry` | `TelemetryBatch` — raw sensor readings |
| `amos/{device_id}/alerts` | `AnomalyResult` — when score exceeds threshold |
| `amos/{device_id}/health` | `HealthStatus` — edge device health |

### Cloud Core (Python/FastAPI)

Located at: `cloud-core/`

The intelligence hub: Kafka ingestion, time-series storage, alerting, and MLOps.

| Service | Port | Purpose |
|---------|------|---------|
| `ingestion-service` | 8001 | Consumes MQTT → publishes to Kafka |
| `tsdb-service` | 8002 | Reads from Kafka → writes to InfluxDB |
| `alert-service` | 8003 | Consumes anomaly alerts → evaluates rules → notifies |
| `mlops-service` | 8004 | Model registry, training triggers, ONNX export |
| Kafka | 9092 | Message broker (KAFKA) |
| InfluxDB | 8086 | Time-series database |
| MLflow | 5000 | Experiment tracking |
| Grafana | 3000 | Dashboards (admin/amos_admin) |

**Kafka Topics:**
| Topic | Producer | Consumer |
|-------|----------|----------|
| `amos.telemetry` | ingestion-service | tsdb-service |
| `amos.alerts` | tsdb-service | alert-service |
| `amos.models` | mlops-service | (downstream edge agents) |

### AI Engine (Python/PyTorch)

Located at: `ai-engine/`

Autoencoder-based anomaly detection. Trains on "normal" operational data, then flags deviations.

**Training pipeline** (`training/train_autoencoder.py`):
1. Load historical sensor data from InfluxDB (or CSV)
2. Normalize features (StandardScaler)
3. Train deep autoencoder (6-layer: 64→32→16→8→16→32→64)
4. Compute reconstruction error threshold on validation set
5. Export to ONNX via `export_onnx.py`
6. Upload to MLflow model registry

**Inference modes:**
- **Edge inference** (real-time): `inference/onnx_runner.py` + `stream_processor.py`
- **Cloud inference** (batch/backfill): Same ONNX model via `tsdb-service`

**Sensor channels** (configured in edge-config.yaml):
| Index | Channel | Unit |
|-------|---------|------|
| 0 | Spindle_Temperature | C |
| 1 | Spindle_Vibration | mm/s |
| 2 | Spindle_Torque | Nm |
| 3 | Coolant_Flow | L/min |
| 4 | Cutting_Speed | m/min |
| 5 | Feed_Rate | mm/min |

### React Dashboard

Located at: `dashboard/`

Industrial dark-theme SPA for plant-floor operators and maintenance managers.

| Page | Route | Purpose |
|------|-------|---------|
| Dashboard | `/` | Overview: fleet health, active alerts, recent events |
| Machines | `/machines` | Per-machine detail: health score, sensor trends, history |
| Alerts | `/alerts` | Alert feed with severity, timestamp, recommended actions |
| Analytics | `/analytics` | Charts: anomaly score over time, feature attribution |
| Settings | `/settings` | System config, notification rules, edge agent management |

**Key UI components:**
| Component | Purpose |
|-----------|---------|
| `HealthCard` | Machine health score (0-100) with color coding |
| `AlertBadge` | Severity indicator (normal/warning/critical) |
| `StatusDot` | Live connection status for MQTT |
| `Sidebar` | Navigation + collapse |

### Infrastructure

Located at: `infrastructure/k8s/`

Production Kubernetes manifests. All resources in the `amos` namespace.

| File | Resource | Purpose |
|------|----------|---------|
| `namespace.yaml` | Namespace | Isolates all AMOS resources |
| `configmap.yaml` | ConfigMap | Shared env vars (Kafka, InfluxDB endpoints) |
| `kafka.yaml` | Deployment + SVC | Message broker |
| `influxdb.yaml` | Deployment + SVC + PVC | Time-series database |
| `ingestion-service.yaml` | Deployment + SVC | MQTT→Kafka bridge |
| `tsdb-service.yaml` | Deployment + SVC | Kafka→InfluxDB writer |
| `alert-service.yaml` | Deployment + SVC | Alert evaluation + routing |
| `mlops-deployment.yaml` | Deployment + SVC | Model training + registry |
| `grafana.yaml` | Deployment + SVC | Dashboards |
| `mlops-service-svc.yaml` | Service | Exposes mlops API |

## Data Flow Summary

```
Machine sensors (temperature, vibration, torque, etc.)
    │
    ▼
Edge Agent (Rust, on Advantech UNO-2271G V3)
    ├── OPC-UA / Modbus-TCP collector
    ├── ONNX autoencoder inference (anomaly score)
    ├── Threshold check (anomaly_score > 0.05 → ALERT)
    │
    ├─→ MQTT: amos/{device_id}/telemetry  (all readings)
    ├─→ MQTT: amos/{device_id}/alerts     (anomaly events only)
    └─→ MQTT: amos/{device_id}/health     (device health, 30s interval)

    ▼
Cloud MQTT Broker (Kafka)
    │
    ├──→ tsdb-service → InfluxDB  (write telemetry)
    ├──→ alert-service → evaluate rules → Slack/email/PagerDuty
    └──→ mlops-service → MLflow (log anomaly events)

    ▼
React Dashboard (port 5173)
    ├── GET /api/machines          → list all machines + health scores
    ├── GET /api/machines/{id}     → machine detail
    ├── GET /api/alerts            → alert feed
    └── GET /api/analytics/{id}   → time-series chart data
```

## Security Model

| Layer | Mechanism |
|-------|-----------|
| Edge→Cloud | MQTT over TLS 1.3; certificate pinning |
| Cloud API | Bearer token authentication (JWT) |
| Data at rest | InfluxDB auth; Kafka SASL/SCRAM |
| Edge device | TPM-backed certificate storage (production) |
| ML models | Signed ONNX artifacts; model provenance via MLflow |

## Deployment Options

1. **Development** — docker-compose on a single VM (see cloud-core/docker-compose.yml)
2. **Staging/Production** — Kubernetes (see infrastructure/k8s/); uses persistent volumes for state
3. **Hybrid** — Edge agents on-premise; cloud microservices on AWS EKS / Azure AKS