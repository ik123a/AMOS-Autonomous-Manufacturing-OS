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

## What is AMOS?

AMOS (Autonomous Manufacturing OS) is an end-to-end industrial IoT and predictive maintenance platform. It solves the problem of unplanned machinery downtime by:
1. **Low-Latency Edge Collection**: Collecting high-frequency sensor telemetry directly from factory floor PLCs via standard protocols (OPC-UA and Modbus-TCP).
2. **Edge Machine Learning**: Performing real-time anomaly detection (using a deep autoencoder model) directly on the edge device to flag deviations in under 10ms.
3. **Robust Cloud Ingestion**: Streaming telemetry and alerts through an enterprise message broker (Apache Kafka) into a time-series database (InfluxDB).
4. **Actionable Operations Dashboard**: Presenting real-time fleet health, active alarms, and explainable AI feature attributions to factory operators.

---

## System Architecture

The following diagram outlines the telemetry flow and service architecture of the AMOS platform:

```mermaid
graph TD
    subgraph Edge Layer (Factory Floor)
        PLC["Factory PLCs & Sensors"] -- "OPC-UA / Modbus-TCP" --> EA["AMOS Edge Agent (Rust)"]
        EA -- "Local Inference (<10ms)" --> OR["ONNX Runtime (anomaly.onnx)"]
    end

    subgraph Transport
        EA -- "MQTT over TLS 1.3" --> MQTT["MQTT Broker (mqtt.amos-platform.io)"]
    end

    subgraph Cloud Layer (Kubernetes - 'amos' Namespace)
        MQTT -- "MQTT Bridge" --> Ingestion["Ingestion Service (FastAPI)"]
        Ingestion -- "Publish Telemetry" --> Kafka["Apache Kafka (Message Broker)"]
        ZK["Zookeeper"] <--> Kafka
        
        Kafka -- "Consume Telemetry" --> TSDB_Svc["TSDB Service (FastAPI)"]
        TSDB_Svc -- "Write Data" --> Influx["InfluxDB 2.7 (Time-Series)"]
        
        Kafka -- "Consume Alerts" --> Alert_Svc["Alert Service (FastAPI)"]
        Alert_Svc -- "Slack Webhooks" --> Slack["Slack / PagerDuty Alerting"]
        
        MLOps["MLOps Service (FastAPI)"] -- "Model Registry" --> MLflow["MLflow Server"]
        MLOps -- "Deploy Models" --> EA
    end

    subgraph Client Layer (Operator Interface)
        React["React 18 Dashboard"] -- "Query Telemetry" --> TSDB_Svc
        React -- "Manage Alarms" --> Alert_Svc
    end
    
    style Edge Layer fill:#2d3748,stroke:#ed8936,stroke-width:2px
    style Cloud Layer fill:#1a202c,stroke:#4299e1,stroke-width:2px
    style Client Layer fill:#2d3748,stroke:#48bb78,stroke-width:2px
```

---

## Key Features

| Feature | Implementation |
|---------|---------------|
| **OPC-UA / Modbus-TCP collector** | Rust async (tokio) — non-blocking reads from any industrial PLC |
| **ONNX edge inference** | PyTorch autoencoder → ONNX Runtime — detects anomalies in <10ms |
| **MQTT streaming** | TLS 1.3, certificate-authenticated, auto-reconnect |
| **Time-series DB** | InfluxDB with 1-second resolution, automated retention policies |
| **Alert routing** | FastAPI service evaluates rules, sends to Slack/PagerDuty/email |
| **MLOps** | MLflow experiment tracking, model registry, one-click promote to edge |
| **Explainable AI** | SHAP values show which sensor triggered each alert |
| **Zero rip-and-replace** | Works with existing PLCs and sensors via open standards |

---

## Quick Start

### 1. Start the Cloud Stack

Ensure Docker and Docker Compose are installed, then spin up the microservice ecosystem:

```bash
cd cloud-core
docker-compose up -d

# Wait for services to be healthy
docker-compose ps

# Services available:
#   Dashboard   http://localhost:5173
#   Alert API   http://localhost:8003
#   TSDB API    http://localhost:8002
#   Ingestion   http://localhost:8001
#   MLOps API   http://localhost:8004
#   Grafana     http://localhost:3000  (admin / amos_admin_2024)
#   Kafka UI    http://localhost:8080
#   MLflow      http://localhost:5000
```

### 2. Build and Run the Dashboard

The dashboard is built on React 18, Vite, and TypeScript.

```bash
cd dashboard
npm install --legacy-peer-deps
npm run dev
# Open http://localhost:5173
```

### 3. Build and Run the Edge Agent

The edge agent compiles into a native Rust binary.

```bash
cd edge-agent
cargo build --release
./target/release/amos-edge-agent --config config/edge-config.yaml

# Or build and run as a Docker container:
docker build -t amos-edge-agent ./edge-agent
docker run --rm -v $(pwd)/config:/etc/amos amos-edge-agent
```

### 4. Simulate Factory Floor Data (No PLC Needed)

If you don't have a physical PLC running OPC-UA or Modbus, run the simulation script to publish synthetic telemetry:

```bash
# Generate synthetic sensor data → MQTT → cloud stack
cd cloud-core
python3 scripts/simulate_sensor_data.py --device edge-plant1-001 --duration 3600
```

---

## Directory & Architecture Map

### Edge Agent (Rust)
*   [main.rs](file:///c:/Users/SKV/Desktop/Projects/AMOS/edge-agent/src/main.rs) — Entry point, orchestrates data collectors and connections.
*   [config.rs](file:///c:/Users/SKV/Desktop/Projects/AMOS/edge-agent/src/config.rs) — Decodes YAML configuration and validates inputs.
*   [mqtt.rs](file:///c:/Users/SKV/Desktop/Projects/AMOS/edge-agent/src/mqtt.rs) — Robust MQTT client with auto-reconnection and TLS support.
*   [inference.rs](file:///c:/Users/SKV/Desktop/Projects/AMOS/edge-agent/src/inference.rs) — ONNX Runtime integration for running local anomaly models.
*   [health.rs](file:///c:/Users/SKV/Desktop/Projects/AMOS/edge-agent/src/health.rs) — Collects CPU, memory, network, and disk metrics.
*   [collectors/opcua.rs](file:///c:/Users/SKV/Desktop/Projects/AMOS/edge-agent/src/collectors/opcua.rs) — OPC-UA industrial protocol client.
*   [collectors/modbus.rs](file:///c:/Users/SKV/Desktop/Projects/AMOS/edge-agent/src/collectors/modbus.rs) — Modbus-TCP industrial protocol client.

### Cloud Microservices (Python/FastAPI)
| Service | Port | Directory | Responsibility |
|---------|------|-----------|----------------|
| `ingestion-service` | 8001 | `cloud-core/ingestion-service` | Receives MQTT telemetry, routes to Kafka. |
| `tsdb-service` | 8002 | `cloud-core/tsdb-service` | Consumes from Kafka, writes to InfluxDB. |
| `alert-service` | 8003 | `cloud-core/alert-service` | Processes anomalies, triggers alert rules and Slack webhooks. |
| `mlops-service` | 8004 | `cloud-core/mlops-service` | Manages model training pipelines and registry. |

---

## Production Deployment

### 1. Kubernetes Deployment

To deploy the cloud services to a production Kubernetes cluster:

```bash
# 1. Build and push container images (replace with your repository path in lowercase)
# Note: GHCR requires lowercase repository tags
REPO_LOWER="ik123a/amos-autonomous-manufacturing-os"

for svc in ingestion-service tsdb-service alert-service mlops-service; do
  docker build -t ghcr.io/${REPO_LOWER}/$svc:latest ./cloud-core/$svc
  docker push ghcr.io/${REPO_LOWER}/$svc:latest
done

# 2. Apply Kubernetes Manifests
kubectl apply -f infrastructure/k8s/namespace.yaml
kubectl apply -f infrastructure/k8s/

# 3. Check Rollout Status
kubectl rollout status deployment/ingestion-service -n amos
```

### 2. Edge Agent on Hardware (Advantech UNO)

Configure the edge agent as a systemd service on factory gateway hardware:

```bash
# Copy binary to hardware
scp amos-edge-agent amos@edge-device:/usr/local/bin/

# Set up as a systemd service
sudo tee /etc/systemd/system/amos-edge-agent.service <<'EOF'
[Unit]
Description=AMOS Edge Agent
After=network.target

[Service]
ExecStart=/usr/local/bin/amos-edge-agent --config /etc/amos/edge-config.yaml
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable amos-edge-agent
sudo systemctl start amos-edge-agent
```

---

## API Reference

See `docs/api-reference.md` for full parameter schemas.

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

## Tech Stack

*   **Edge Layer**: Rust, tokio async, rumqttc, ONNX Runtime, OPC-UA, Modbus-TCP.
*   **Message Broker**: Apache Kafka & Zookeeper.
*   **Databases**: InfluxDB 2.7 (Telemetry) & PostgreSQL (Metadata/Alerts).
*   **Cloud Services**: Python 3.11, FastAPI, aiokafka, influxdb-client.
*   **Machine Learning**: PyTorch 2.2, ONNX, MLflow.
*   **Dashboard**: React 18, TypeScript 5.3, Vite, MUI 5, Recharts.
*   **CI/CD**: GitHub Actions, Docker Buildx.

---

## License

Proprietary — see [LICENSE](file:///c:/Users/SKV/Desktop/Projects/AMOS/LICENSE). All rights reserved.

---

**Built with the vision of making every factory floor predictive, not reactive.**