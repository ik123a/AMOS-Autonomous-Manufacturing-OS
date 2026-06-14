# AMOS — Autonomous Manufacturing OS

**AMOS** is an intelligent, unified nervous system for the factory floor. It transforms manufacturing from a reactive, siloed operation into a predictive and autonomous ecosystem.

## Core Value Proposition

- **10x improvement** in operational efficiency
- **40-50% reduction** in unplanned downtime
- **18-25% reduction** in maintenance costs
- **ROI in under 18 months** for a 50-machine plant

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    AMOS Cloud Core (K8s)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │Ingestion │ │  TSDB    │ │  Alert   │ │   MLOps       │  │
│  │ Service  │ │(InfluxDB)│ │ Service  │ │ (Kubeflow)    │  │
│  └────┬─────┘ └──────────┘ └────┬─────┘ └───────┬───────┘  │
│       │                         │                │          │
│  ┌────▼─────────────────────────▼────────────────▼───────┐  │
│  │                   Apache Kafka                        │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────┬───────────────────────────────────────┘
                      │ MQTT/TLS
┌─────────────────────▼───────────────────────────────────────┐
│              Edge Agent (Advantech UNO-2271G)               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ OPC-UA   │ │ Modbus   │ │ ONNX     │ │Local Alerting │  │
│  │ Client   │ │ Client   │ │ Runtime  │ │               │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └───────────────┘  │
│       │            │            │                           │
│  ┌────▼────────────▼────────────▼───────────────────────┐  │
│  │              PLCs & Sensors on Factory Floor          │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Edge Runtime** | Rust, open62541, NodeOPCUA |
| **ML Inference** | ONNX Runtime, PyTorch |
| **Message Bus** | Apache Kafka, MQTT |
| **Time-Series DB** | InfluxDB / TimescaleDB |
| **Orchestration** | Kubernetes, Docker |
| **MLOps** | Kubeflow, MLflow, KServe |
| **Dashboard** | React, TypeScript, Grafana |
| **Digital Twin** | Eclipse BaSyx |
| **Data Lakehouse** | Apache Iceberg, Spark, Trino |

## Project Structure

```
AMOS/
├── edge-agent/          # Edge device software (Rust)
├── cloud-core/          # Cloud microservices
├── ai-engine/           # ML models & training pipelines
├── dashboard/           # React-based web dashboard
├── infrastructure/      # Docker, K8s, CI/CD configs
├── docs/                # Architecture & design docs
└── scripts/             # Utility scripts
```

## Quick Start

```bash
# Clone the repository
git clone https://github.com/your-org/AMOS.git
cd AMOS

# Start the cloud stack locally
docker-compose -f infrastructure/docker/docker-compose.yml up -d

# Deploy edge agent (requires OPC-UA compatible PLC)
cd edge-agent && cargo run -- --config config/edge-config.yaml

# Launch dashboard
cd dashboard && npm install && npm start
```

## License

Proprietary — see LICENSE for details.