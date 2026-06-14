# AMOS — Autonomous Manufacturing OS

![Status](https://img.shields.io/badge/status-early%20release-blue)
![Rust](https://img.shields.io/badge/rust-1.76%2B-orange)
![Python](https://img.shields.io/badge/python-3.11%2B-green)
![Kubernetes](https://img.shields.io/badge/k8s-1.28%2B-blue)

**AMOS transforms reactive, siloed factory operations into a predictive and autonomous ecosystem.** It detects machine anomalies before failure occurs, using edge-side AI inference on existing PLC data — without requiring any "rip-and-replace" hardware changes.

Target: **40-50% reduction in unplanned downtime**, **18-25% maintenance cost savings**, sub-18-month ROI.

---

## What AMOS Does

```
Factory Floor                          Cloud                            Dashboard
─────────────                          ─────                            ─────────
  CNC-04 ──[OPC-UA/Modbus-TCP]──┐
                                    │
  Inject-02 ──[OPC-UA/Modbus-TCP]─┼── Edge Agent (Rust)
                                    │      │
  Convey-01 ──[OPC-UA/Modbus-TCP]─┘      │ ONNX Autoencoder Inference
                                          │ (anomaly score > 0.05 = ALERT)
                                          │
                                          ├─ MQTT → Kafka → InfluxDB
                                          ├─ MQTT → Kafka → Alert Service
                                          └─ MQTT → Kafka → MLflow
                                                        │
                                              ┌─────────▼────────┐
                                              │  React Dashboard  │
                                              │  health scores   │
                                              │  anomaly alerts  │
                                              │  trend analytics │
                                              └──────────────────┘
```

**Core value flow:**
1. Edge agent reads raw sensor data from PLCs via OPC-UA or Modbus-TCP
2. ONNX autoencoder computes a real-time "anomaly score" — how unusual the current readings are
3. If the score exceeds the threshold, an alert is published to the cloud
4. The alert service evaluates rules and notifies the right people
5. The dashboard displays machine health, active alerts, and historical trends

---

## Architecture

| Layer | Technology | Location |
|-------|-----------|----------|
| Edge Agent | Rust + Tokio + ONNX Runtime | `edge-agent/` |
| Cloud Ingestion | Python 3.11 + FastAPI + Kafka | `cloud-core/ingestion-service/` |
| Time-Series DB | InfluxDB | `cloud-core/` (docker-compose) |
| Alert Engine | Python 3.11 + FastAPI | `cloud-core/alert-service/` |
| MLOps | Python 3.11 + MLflow | `cloud-core/mlops-service/` |
| AI Training | PyTorch + ONNX export | `ai-engine/` |
| Dashboard | React 18 + MUI + Recharts | `dashboard/` |
| Infrastructure | Docker Compose / Kubernetes | `cloud-core/`, `infrastructure/k8s/` |

---

## Quick Start

### 1. Clone and Explore

```bash
git clone https://github.com/ik123a/AMOS-Autonomous-Manufacturing-OS.git
cd AMOS-Autonomous-Manufacturing-OS

# See the full project structure
ls -la
# edge-agent/       Rust edge device agent
# cloud-core/       Python microservices + Docker Compose
# ai-engine/        PyTorch autoencoder training
# dashboard/        React 18 dashboard
# infrastructure/  Kubernetes manifests
# docs/             Architecture, API reference, deployment
```

### 2. Start the Cloud Stack (Docker Compose)

```bash
cd cloud-core
docker compose up -d

# Wait for all services to be healthy
docker compose ps

# You'll have:
#   ingestion-service  :8001   FastAPI — MQTT → Kafka
#   tsdb-service       :8002   FastAPI — Kafka → InfluxDB  ← use this
#   alert-service      :8003   FastAPI — alert evaluation
#   mlops-service      :8004   FastAPI — model registry
#   Kafka              :9092   Message broker
#   InfluxDB           :8086   Time-series database
#   MLflow             :5000   Experiment tracking UI
#   Grafana            :3000   Dashboards (admin/amos_admin_2024)
```

### 3. Build the Edge Agent

```bash
cd edge-agent

# Install Rust (if needed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env

# Build
cargo build --release
# Binary → target/release/amos-edge-agent
```

### 4. Train a Model (or use the example)

```bash
cd ai-engine
pip install -r requirements.txt

# See sample data format
head -3 data/sample_sensor_data.csv
# timestamp,Spindle_Temperature,Spindle_Vibration,Spindle_Torque,Coolant_Flow,Cutting_Speed,Feed_Rate
# 2024-04-01 00:00:00,58.2,0.12,45.3,8.2,1150,195
# 2024-04-01 00:00:01,58.3,0.11,45.1,8.2,1150,195

# Train an autoencoder on "normal" data → produces anomaly.onnx
python training/train_autoencoder.py \
  --data ./data/sample_sensor_data.csv \
  --epochs 100 \
  --output ./models/anomaly.onnx

# Verify: run inference with the trained model
python inference/onnx_runner.py --model ./models/anomaly.onnx
```

### 5. Run the Dashboard

```bash
cd dashboard
npm install
npm run dev
# → Open http://localhost:5173
```

### 6. Run the Edge Agent

```bash
cd edge-agent

# Point the edge agent at the local Docker MQTT broker
# Edit config/edge-config.yaml — set mqtt.host to your Docker host IP
# (On Linux: your LAN IP; On macOS/Windows: use docker.for.<host>.local)

./target/release/amos-edge-agent --config config/edge-config.yaml
```

You should see output like:
```
AMOS Edge Agent v0.1.0 starting up...
Device: edge-plant1-001 @ Building-A-Line-3
MQTT connected to 192.168.1.100:1883
Starting OPC-UA collector: opc.tcp://192.168.1.42:4840 (6 nodes)
Starting Modbus collector: 192.168.1.43:502 (8 registers)
Health: cpu=12.4% mem=38.7% status=healthy
Anomaly score: 0.012 [NORMAL]
Anomaly score: 0.031 [NORMAL]
Anomaly score: 0.073 [ANOMALY DETECTED] → published to MQTT
```

---

## Configuration

### Edge Agent (`edge-agent/config/edge-config.yaml`)

```yaml
device_id: "edge-plant1-001"
machine_name: "CNC-Machine-04"
location: "Building-A-Line-3"

# Change this to your MQTT broker address
mqtt:
  host: "192.168.1.100"
  port: 1883
  use_tls: false
  topic_prefix: "amos"

# OPC-UA: connect to your PLC's OPC-UA server
opcua:
  endpoint: "opc.tcp://192.168.1.42:4840"
  monitored_nodes:
    - "ns=2;i=1"   # Spindle_Temperature
    - "ns=2;i=2"   # Spindle_Vibration
    - "ns=2;i=3"   # Spindle_Torque
    - "ns=2;i=4"   # Coolant_Flow
    - "ns=2;i=5"   # Cutting_Speed
    - "ns=2;i=6"   # Feed_Rate

# Modbus-TCP: alternative to OPC-UA
modbus:
  host: "192.168.1.43"
  port: 502
  slave_id: 1
  registers:
    - name: "Spindle_Temperature"
      address: 0
      scale: 0.1
      unit: "C"

# ONNX inference
inference:
  enabled: true
  model_path: "/opt/amos/models/anomaly.onnx"
  anomaly_threshold: 0.05   # Alert triggers when MSE > this
  input_size: 6            # Number of sensor channels
  buffer_size: 12          # Sliding window size
```

### Cloud Services

Environment variables (in docker-compose.yml or K8s ConfigMap):

| Variable | Default | Description |
|----------|---------|-------------|
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | Kafka broker address |
| `INFLUXDB_URL` | `http://influxdb:8086` | InfluxDB endpoint |
| `MLFLOW_TRACKING_URI` | `http://mlflow:5000` | MLflow server |
| `ALERT_THRESHOLD_WARNING` | `0.05` | Warning alert threshold |
| `ALERT_THRESHOLD_CRITICAL` | `0.10` | Critical alert threshold |

---

## API Reference

The tsdb-service exposes a REST API on port 8002:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/machines` | GET | List all machines + health scores |
| `/api/machines/{id}` | GET | Single machine detail |
| `/api/machines/{id}/telemetry` | GET | Recent sensor readings |
| `/api/machines/{id}/health` | GET | Machine health history |
| `/api/alerts` | GET | All alerts (filter by severity, status) |
| `/api/alerts/{id}/acknowledge` | PUT | Acknowledge an alert |
| `/api/alerts/{id}/resolve` | PUT | Resolve an alert |
| `/api/analytics/{id}/anomaly-score` | GET | Anomaly score time series |
| `/api/analytics/{id}/feature-attribution` | GET | Which sensors triggered alert |
| `/api/models/train` | POST | Trigger model training |
| `/api/models/deploy` | POST | Deploy model to edge agent |

Full API docs: [docs/api-reference.md](docs/api-reference.md)

---

## The AI Model (Autoencoder)

AMOS uses a **deep autoencoder** trained exclusively on *normal* operational data. It learns to reconstruct normal patterns. When reconstruction error spikes, something abnormal is happening — even if that exact failure mode was never seen in training.

**Architecture:** 6-layer symmetric autoencoder
```
Input(6) → 64 → 32 → 16 → 8 → 16 → 32 → 64 → Output(6)
```

**Why autoencoders for predictive maintenance:**
- Only requires "normal" data to train (no labeled failure data needed)
- Detects novel failure modes, not just known patterns
- Achieves 98%+ accuracy on industrial benchmarks
- Explainable: SHAP values show *which* sensors triggered the alert

**Federated Learning (future):** Share only anonymized model gradient updates, never raw sensor data, to build fleet-wide models across customer deployments.

---

## Dashboard Screenshots / UI

The dashboard runs at `http://localhost:5173` (dev) and provides:

- **Overview** — Fleet health grid, active alert count, system status
- **Machines** — Per-machine health score (0-100), sensor sparklines, last seen
- **Alerts** — Feed of anomaly alerts with severity, timestamp, affected sensors, recommended action
- **Analytics** — Anomaly score chart, feature attribution bar chart, health trend
- **Settings** — Notification channels, alert rules, edge agent management

The UI uses an industrial dark theme (MUI with custom `--amos-bg` palette) designed for plant-floor displays and monitors.

---

## Deployment Options

| Environment | Command | Best For |
|-------------|---------|---------|
| Local dev | `cd cloud-core && docker compose up -d` | First-time exploration |
| Single-server staging | Docker Compose on a VM | Pilot customer deployment |
| Production | Kubernetes manifests in `infrastructure/k8s/` | Multi-customer SaaS |

See [docs/deployment.md](docs/deployment.md) for the full Kubernetes production guide including edge agent bare-metal and Docker installation.

---

## Project Structure

```
AMOS/
├── edge-agent/                    # Rust edge device agent
│   ├── src/
│   │   ├── main.rs               # Entry point, CLI, service orchestration
│   │   ├── config.rs             # YAML config deserialization + helpers
│   │   ├── mqtt.rs               # MQTT client (rumqttc) with TLS + reconnect
│   │   ├── inference.rs          # ONNX Runtime autoencoder inference engine
│   │   ├── health.rs             # System health monitor + MQTT publisher
│   │   └── collectors/
│   │       ├── opcua.rs          # OPC-UA collector (production-ready interface)
│   │       └── modbus.rs         # Modbus-TCP collector (same pattern)
│   ├── config/edge-config.yaml  # Sample configuration
│   ├── Cargo.toml                # Rust dependencies
│   └── Dockerfile               # Edge agent container image
│
├── cloud-core/                    # Python cloud microservices
│   ├── docker-compose.yml         # Full local stack (Kafka, InfluxDB, MLflow, etc.)
│   ├── ingestion-service/        # MQTT → Kafka bridge (FastAPI)
│   ├── tsdb-service/             # Kafka → InfluxDB + REST API (FastAPI)
│   ├── alert-service/            # Alert evaluation + routing (FastAPI)
│   ├── mlops-service/            # Model registry + training triggers (FastAPI)
│   └── grafana/                  # Grafana dashboards + datasources
│
├── ai-engine/                     # PyTorch ML pipeline
│   ├── training/
│   │   └── train_autoencoder.py  # Full training pipeline (data → model)
│   ├── inference/
│   │   ├── onnx_runner.py        # ONNX Runtime inference wrapper
│   │   └── stream_processor.py   # Real-time sliding window inference
│   ├── export_onnx.py            # PyTorch → ONNX export + validation
│   ├── requirements.txt
│   └── data/sample_sensor_data.csv
│
├── dashboard/                     # React 18 dashboard
│   ├── src/
│   │   ├── App.jsx               # Router + theme provider
│   │   ├── pages/                # Dashboard, Machines, Alerts, Analytics, Settings
│   │   └── components/           # HealthCard, AlertBadge, Sidebar, StatusDot
│   └── package.json
│
├── infrastructure/k8s/            # Kubernetes manifests
│   ├── namespace.yaml             # amos namespace
│   ├── configmap.yaml             # Shared env vars
│   ├── kafka.yaml                 # Kafka broker
│   ├── influxdb.yaml             # Time-series DB + PVC
│   ├── ingestion-service.yaml    # MQTT → Kafka
│   ├── tsdb-service.yaml        # Kafka → InfluxDB
│   ├── alert-service.yaml        # Alert evaluation
│   ├── mlops-deployment.yaml     # Model training
│   └── mlops-service-svc.yaml
│
├── docs/
│   ├── architecture.md            # System design, component inventory, data flow
│   ├── api-reference.md           # Full REST API documentation
│   └── deployment.md              # Local dev, K8s, edge agent installation
│
├── .gitignore
├── CONTRIBUTING.md                # Dev setup, code style, PR process
├── LICENSE                       # Proprietary license
├── README.md
└── push-to-github.sh             # Helper script for GitHub setup
```

---

## Performance Targets

| Metric | Target |
|--------|--------|
| Edge inference latency | < 10ms per reading window |
| End-to-end alert latency | < 2s (sensor → MQTT → Kafka → alert) |
| MQTT reconnect time | < 5s after broker restart |
| Anomaly detection accuracy | ROC-AUC > 0.90 |
| False positive rate | < 5% of alerts |
| Supported edge devices per cloud instance | 500+ |
| Data retention (InfluxDB) | 90 days hot, 2 years cold |

---

## Key Dependencies

**Edge Agent (Rust):**
- `tokio` — async runtime
- `rumqttc` — MQTT client
- `serde`, `serde_yaml` — config parsing
- `onnxruntime` — ML inference
- `tracing`, `tracing-subscriber` — structured logging
- `clap` — CLI argument parsing
- `sysinfo` — system health monitoring
- `ndarray` — array operations for ONNX tensor building

**Cloud (Python):**
- `fastapi` + `uvicorn` — HTTP server
- `aiokafka` — async Kafka client
- `influxdb-client` — InfluxDB write API
- `mlflow` — experiment tracking
- `httpx` — async HTTP client

**Dashboard:**
- `react` 18 + `react-router-dom` 6
- `@mui/material` — component library
- `recharts` — charting
- `axios` — API client

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style guides, testing, and the PR process.

---

## Roadmap

- [ ] **Month 6** — MVP pilot validation at partner site
- [ ] **Month 9** — Onboard 3-5 pilot customers; self-service onboarding
- [ ] **Month 12** — Formal product launch; $1M ARR target
- [ ] **Month 15** — Predictive Maintenance Scheduler (auto-generate work orders from RUL predictions)
- [ ] **Month 18** — Energy Optimization Module (10-15% energy savings)
- [ ] **Month 24** — Federated Learning engine; SOC 2 Type II
- [ ] **Month 30** — First international deployment (Germany)