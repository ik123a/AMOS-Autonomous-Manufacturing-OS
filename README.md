# AMOS — Autonomous Manufacturing OS

![CI/CD](https://github.com/ik123a/AMOS-Autonomous-Manufacturing-OS/actions/workflows/ci.yaml/badge.svg)
![Rust](https://img.shields.io/badge/Rust-1.76+-orange?logo=rust)
![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![TypeScript](https://img.shields.io/badge/TypeScript-5.3-blue?logo=typescript)
![Docker](https://img.shields.io/badge/Docker-K8s-blue?logo=docker)

---

**AMOS transforms reactive, siloed factory operations into a predictive and autonomous ecosystem.**

It monitors machines via edge agents (Rust), streams data through cloud microservices (Python/FastAPI), runs PyTorch autoencoder anomaly detection at the edge and in the cloud, and presents everything through a React dashboard.

> **Target outcome:** 40–50% reduction in unplanned downtime, 18–25% maintenance cost savings, ROI in under 18 months.

---

## What AMOS Does

```
Machine sensors (temperature, vibration, torque, pressure, etc.)
    │
    ▼
Edge Agent (Rust, Advantech UNO-2271G V3)
    ├── Reads PLC data via OPC-UA / Modbus-TCP
    ├── Runs ONNX autoencoder inference (anomaly score)
    ├── Publishes telemetry + alerts via MQTT (TLS)
    │
    ├─→ MQTT: amos/{device_id}/telemetry
    ├─→ MQTT: amos/{device_id}/alerts
    └─→ MQTT: amos/{device_id}/health
            │
            ▼
Cloud (Docker/K8s)
    ├── Kafka — message bus
    ├── InfluxDB — time-series storage
    ├── FastAPI services — ingestion, alerts, MLOps
    └── MLflow — experiment tracking
            │
            ▼
React Dashboard (http://localhost:5173)
    ├── Fleet overview (all machines, health scores)
    ├── Per-machine telemetry + anomaly history
    ├── Alert feed with severity + recommended actions
    └── Analytics (anomaly score charts, feature attribution)
```

---

## Key Features

| Feature | Implementation |
|---------|---------------|
| **OPC-UA / Modbus-TCP collector** | Rust async — non-blocking reads from any PLC |
| **ONNX edge inference** | PyTorch autoencoder → ONNX Runtime — detects anomalies in <10ms |
| **MQTT streaming** | TLS 1.3, certificate-authenticated, auto-reconnect |
| **Time-series DB** | InfluxDB with 1-second resolution, retention policies |
| **Alert routing** | FastAPI service evaluates rules, sends to Slack/PagerDuty/email |
| **MLOps** | MLflow experiment tracking, model registry, one-click promote to edge |
| **Explainable AI** | SHAP values show which sensor triggered each alert |
| **Federated Learning** | Architecture ready — share model updates, not raw data |
| **Zero rip-and-replace** | Works with existing PLCs and sensors via open standards |

---

## Quick Start

### 1. Start the cloud stack

```bash
cd cloud-core
docker-compose up -d

# Wait for services to be healthy
docker-compose ps

# Services available:
#   Dashboard   http://localhost:5173
#   Alert API  http://localhost:8003
#   TSDB API   http://localhost:8002
#   Ingestion  http://localhost:8001
#   MLOps API  http://localhost:8004
#   Grafana    http://localhost:3000  (admin / amos_admin_2024)
#   Kafka UI   http://localhost:8080
#   MLflow     http://localhost:5000
```

### 2. Build the dashboard

```bash
cd dashboard
npm install --legacy-peer-deps
npm run dev
# Open http://localhost:5173
```

### 3. Build the edge agent

```bash
cd edge-agent
cargo build --release
./target/release/amos-edge-agent --config config/edge-config.yaml

# Or with Docker:
docker build -t amos-edge-agent ./edge-agent
docker run --rm -v $(pwd)/config:/etc/amos amos-edge-agent
```

### 4. Simulate data (no PLC needed)

```bash
# Generate synthetic sensor data → MQTT → cloud
cd cloud-core
python3 scripts/simulate_sensor_data.py --device edge-plant1-001 --duration 3600
```

---

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for the full technical architecture.

### Edge Agent (Rust)
- `src/main.rs` — entry point, collector orchestration
- `src/config.rs` — YAML config deserialization + validation
- `src/mqtt.rs` — MQTT client (rumqttc), TLS, reconnect
- `src/inference.rs` — ONNX Runtime wrapper, anomaly scoring
- `src/health.rs` — system health monitor
- `src/collectors/opcua.rs` — OPC-UA data collector
- `src/collectors/modbus.rs` — Modbus-TCP data collector

### Cloud Microservices (Python/FastAPI)
| Service | Port | Responsibility |
|---------|------|----------------|
| `ingestion-service` | 8001 | MQTT → Kafka |
| `tsdb-service` | 8002 | Kafka → InfluxDB |
| `alert-service` | 8003 | Alert evaluation + routing |
| `mlops-service` | 8004 | Model training + registry |

### AI Engine
- `ai-engine/training/train_autoencoder.py` — train autoencoder on normal operational data
- `ai-engine/training/export_onnx.py` — export trained model to ONNX
- `ai-engine/inference/onnx_runner.py` — ONNX Runtime inference wrapper
- `ai-engine/inference/stream_processor.py` — sliding-window inference for streaming data

### React Dashboard (TypeScript/React 18)
- Dashboard page: fleet overview, health scores, active alerts
- Machines page: per-machine detail, sensor trends, anomaly timeline
- Alerts page: alert feed with severity, ack/resolve workflow
- Analytics page: anomaly score charts, SHAP feature attribution
- Settings page: system config, edge agent management

---

## Configuration

### Edge Agent (`edge-agent/config/edge-config.yaml`)

```yaml
device_id: "edge-plant1-001"
machine_name: "CNC-Machine-04"
location: "Building-A-Line-3"

mqtt:
  broker_host: "broker.amos-platform.io"
  broker_port: 8883
  use_tls: true

opcua:
  endpoint: "opc.tcp://plc-host:4840"
  monitored_nodes:
    - node_id: "ns=2;i=1001"
      name: "Spindle_Temperature"
      unit: "C"

inference:
  enabled: true
  model_path: "/opt/amos/models/anomaly.onnx"
  anomaly_threshold: 0.05
  input_size: 6
  buffer_size: 12
```

### Cloud Services

All service configuration is in `cloud-core/docker-compose.yml` via environment variables. For production, override in a `cloud-core/.env` file or Kubernetes ConfigMap.

---

## Deployment

See [`docs/deployment.md`](docs/deployment.md) for full production deployment instructions.

### Production (Kubernetes)

```bash
# Build + push all container images
docker build -t ghcr.io/ik123a/AMOS-Autonomous-Manufacturing-OS/ingestion-service:latest ./cloud-core/ingestion-service
docker push ghcr.io/ik123a/AMOS-Autonomous-Manufacturing-OS/ingestion-service:latest
# (repeat for tsdb-service, alert-service, mlops-service)

# Deploy to K8s
kubectl apply -f infrastructure/k8s/namespace.yaml
kubectl apply -f infrastructure/k8s/

# Check rollout status
kubectl rollout status deployment/ingestion-service -n amos
```

### Edge Agent on Hardware

```bash
# Copy binary to Advantech UNO-2271G V3
scp amos-edge-agent amos@edge-device:/usr/local/bin/

# Set up as systemd service
sudo tee /etc/systemd/system/amos-edge-agent.service <<'EOF'
[Unit]
Description=AMOS Edge Agent

[Service]
ExecStart=/usr/local/bin/amos-edge-agent --config /etc/amos/edge-config.yaml
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable amos-edge-agent
sudo systemctl start amos-edge-agent
```

---

## API Reference

See [`docs/api-reference.md`](docs/api-reference.md) for the full REST API documentation.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/machines` | List all machines + health scores |
| GET | `/api/machines/{id}` | Machine detail (sensors, anomaly history) |
| GET | `/api/machines/{id}/telemetry` | Raw sensor data for a machine |
| GET | `/api/alerts` | Alert feed (filter by severity, machine, time) |
| POST | `/api/alerts/{id}/acknowledge` | Acknowledge an alert |
| GET | `/api/analytics/{id}/anomaly-score` | Anomaly score time series |
| GET | `/api/models` | List model registry |
| POST | `/api/models/train` | Trigger model retraining |

---

## Project Structure

```
AMOS/
├── edge-agent/           # Rust edge device software
│   ├── src/
│   │   ├── main.rs       # Entry point
│   │   ├── config.rs     # YAML config + validation
│   │   ├── mqtt.rs       # MQTT client (rumqttc)
│   │   ├── inference.rs  # ONNX Runtime inference
│   │   ├── health.rs     # System health monitor
│   │   └── collectors/    # OPC-UA and Modbus collectors
│   ├── Cargo.toml
│   ├── Dockerfile
│   └── config/           # Default config files
│
├── cloud-core/           # Cloud microservices
│   ├── ingestion-service/  # MQTT → Kafka bridge (FastAPI, Port 8001)
│   ├── tsdb-service/      # Kafka → InfluxDB writer (FastAPI, Port 8002)
│   ├── alert-service/      # Alert evaluation + routing (FastAPI, Port 8003)
│   ├── mlops-service/     # MLflow + model registry (FastAPI, Port 8004)
│   ├── kafka-config/
│   ├── grafana/           # Dashboard provisioning
│   ├── docker-compose.yml
│   └── scripts/
│
├── ai-engine/           # ML training and inference
│   ├── training/         # PyTorch autoencoder training
│   ├── inference/       # ONNX runtime wrappers
│   └── models/          # Model store
│
├── dashboard/           # React 18 dashboard
│   ├── src/
│   │   ├── pages/       # Dashboard, Machines, Alerts, Analytics, Settings
│   │   └── components/  # HealthCard, Sidebar, StatusDot, AlertBadge
│   ├── package.json
│   └── vite.config.ts
│
├── infrastructure/      # K8s deployment manifests
│   └── k8s/
│
├── docs/                # Architecture, API, deployment guides
│   ├── architecture.md
│   ├── api-reference.md
│   └── deployment.md
│
├── .github/workflows/   # CI/CD (GitHub Actions)
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Edge Agent | Rust, tokio, rumqttc, ONNX Runtime, OPC-UA |
| Cloud Runtime | Docker, Kubernetes 1.28+, Helm |
| Message Bus | Apache Kafka |
| Time-Series DB | InfluxDB 2.7 |
| Cloud Services | Python 3.11, FastAPI, aiokafka, influxdb-client |
| ML Training | PyTorch 2.2, ONNX, MLflow |
| ML Inference | ONNX Runtime 2.0 |
| Dashboard | React 18, TypeScript 5.3, MUI 5, Recharts, React Router 6 |
| CI/CD | GitHub Actions, Docker Buildx |

---

## License

Proprietary — see [`LICENSE`](LICENSE). All rights reserved.

---

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for development setup, code style, and PR process.

---

**Built with the vision of making every factory floor predictive, not reactive.**