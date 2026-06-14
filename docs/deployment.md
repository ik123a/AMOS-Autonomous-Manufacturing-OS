# AMOS Deployment Guide

This guide covers deploying AMOS from local development all the way through to production Kubernetes.

---

## Prerequisites

| Component | Version | Notes |
|-----------|---------|-------|
| Docker | 24+ | Required for local cloud stack |
| Docker Compose | 2.20+ | V2 syntax (docker compose, not docker-compose) |
| Python | 3.11+ | For cloud services |
| Node.js | 20+ | For dashboard |
| Rust | 1.76+ | For edge agent |
| kubectl | 1.28+ | For K8s deployments |
| Kubernetes | 1.28+ | For production |

---

## Local Development (Docker Compose)

Best for local testing of the full cloud stack.

```bash
cd cloud-core

# Start all services
docker compose up -d

# Watch logs
docker compose logs -f

# Verify all services are up
docker compose ps

# Services and their ports:
#   ingestion-service :8001
#   tsdb-service     :8002
#   alert-service    :8003
#   mlops-service    :8004
#   Kafka            :9092
#   InfluxDB         :8086
#   MLflow           :5000
#   Grafana          :3000 (admin/amos_admin_2024)

# Stop everything
docker compose down
```

### Dashboard (React)

```bash
cd dashboard
npm install
npm run dev      # → http://localhost:5173
```

### Edge Agent (Rust)

```bash
cd edge-agent

# Build
cargo build --release
# Binary → target/release/amos-edge-agent

# Run (pointing at local cloud stack)
./target/release/amos-edge-agent \
  --config config/edge-config.yaml
```

The edge agent expects:
- MQTT broker at `192.168.1.100:1883` (configurable in `config/edge-config.yaml`)
- An ONNX model at `/opt/amos/models/anomaly.onnx` (train one first with `ai-engine/`)

### Training a Model (Local)

```bash
cd ai-engine

# Install dependencies
pip install -r requirements.txt

# Train an autoencoder on sample data
python training/train_autoencoder.py \
  --data ./data/sample_sensor_data.csv \
  --epochs 100 \
  --output ./models/anomaly.onnx

# Verify the model
python inference/onnx_runner.py \
  --model ./models/anomaly.onnx
```

---

## Production Deployment (Kubernetes)

### Cluster Requirements

- Kubernetes 1.28+ with `kubectl` configured
- At least 3 worker nodes (4+ CPU, 16GB RAM each recommended)
- `kubectl` context set to the target cluster

### Step 1 — Apply Kubernetes Manifests

```bash
cd infrastructure/k8s

# Apply all manifests (order matters: namespace → config → storage → apps)
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f kafka.yaml            # Wait: kubectl rollout status deployment/kafka -n amos
kubectl apply -f influxdb.yaml         # Wait: kubectl rollout status deployment/influxdb -n amos
kubectl apply -f ingestion-service.yaml
kubectl apply -f tsdb-service.yaml
kubectl apply -f alert-service.yaml
kubectl apply -f mlops-deployment.yaml

# Verify all pods are running
kubectl get pods -n amos
```

Expected output:
```
NAME                    READY   STATUS    RESTARTS   AGE
kafka-xxxxx             1/1     Running   0          2m
influxdb-xxxxx          1/1     Running   0          2m
ingestion-service      2/2     Running   0          1m
tsdb-service           2/2     Running   0          1m
alert-service          2/2     Running   0          1m
mlops-service          1/1     Running   0          1m
```

### Step 2 — Expose Services

**Development (NodePort):**
```bash
# Not for production — use an ingress controller in production
kubectl expose deployment ingestion-service \
  --type=NodePort \
  --port=8000 \
  --target-port=8001 \
  --name=ingestion-svc \
  -n amos
```

**Production (Ingress + TLS):**
```yaml
# infrastructure/k8s/ingress.yaml (create this file)
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: amos-ingress
  namespace: amos
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
    - hosts:
        - api.amos-platform.io
        - grafana.amos-platform.io
      secretName: amos-tls-cert
  rules:
    - host: api.amos-platform.io
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: tsdb-service
                port:
                  number: 8000
```

### Step 3 — Configure MQTT (Cloud Broker)

Point your edge agents at the cloud MQTT broker. Update `config/edge-config.yaml`:

```yaml
mqtt:
  host: "mqtt.amos-platform.io"
  port: 8883        # TLS port
  use_tls: true
  # For production: provide CA cert
  ca_cert_path: "/etc/ssl/certs/MQTT-Broker-CA.crt"
```

### Step 4 — First-Time Setup (MLflow + Model Upload)

```bash
# Port-forward to MLflow locally
kubectl port-forward svc/mlflow -n amos 5000:5000

# Train and register a model
cd ai-engine
python training/train_autoencoder.py \
  --data ./data/sample_sensor_data.csv \
  --epochs 100 \
  --output ./models/anomaly.onnx \
  --mlflow_uri http://localhost:5000

# Register the model in MLflow UI (http://localhost:5000)
# Then mark it as "Production" stage
```

### Step 5 — Verify the System

```bash
# Get the dashboard service
kubectl get svc -n amos

# Port-forward dashboard locally
kubectl port-forward svc/grafana -n amos 3000:3000
# Open http://localhost:3000 → admin/amos_admin_2024

# Check logs
kubectl logs -l app=ingestion-service -n amos -f
```

---

## Edge Agent Installation (Physical Hardware)

Target hardware: **Advantech UNO-2271G V3** (Intel Atom x7211RE, 8GB RAM, 64GB SSD)

### Option A — Docker (Recommended for Fast Deployment)

```bash
# On the edge device
docker pull ghcr.io/ik123a/amos-edge-agent:latest

# Create config directory
sudo mkdir -p /etc/amos/models
sudo cp edge-config.yaml /etc/amos/edge-config.yaml

# Place ONNX model
sudo cp anomaly.onnx /etc/amos/models/anomaly.onnx

# Run
docker run -d \
  --name amos-edge-agent \
  --restart unless-stopped \
  --network host \
  -v /etc/amos:/etc/amos \
  ghcr.io/ik123a/amos-edge-agent:latest

# Verify
docker logs amos-edge-agent
journalctl -u amos-edge-agent -f
```

### Option B — Bare Metal (Production)

```bash
# On the edge device
sudo apt update && sudo apt install -y libssl-dev pkg-config

# Build from source
git clone https://github.com/ik123a/AMOS-Autonomous-Manufacturing-OS.git
cd AMOS-Autonomous-Manufacturing-OS/edge-agent
cargo build --release --features production

# Install binary
sudo cp target/release/amos-edge-agent /usr/local/bin/
sudo chown root:root /usr/local/bin/amos-edge-agent

# Create service
sudo tee /etc/systemd/system/amos-edge-agent.service <<EOF
[Unit]
Description=AMOS Edge Agent
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/amos-edge-agent --config /etc/amos/edge-config.yaml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable amos-edge-agent
sudo systemctl start amos-edge-agent
sudo journalctl -u amos-edge-agent -f
```

---

## Configuration Reference

### Edge Agent (`config/edge-config.yaml`)

| Section | Key | Description | Default |
|---------|-----|-------------|---------|
| `device_id` | — | Unique ID for this edge device | **Required** |
| `machine_name` | — | Human-readable machine name | — |
| `location` | — | Physical location | — |
| `logging.level` | — | Log level: trace, debug, info, warn, error | `info` |
| `mqtt.host` | — | MQTT broker hostname | **Required** |
| `mqtt.port` | — | MQTT port | `1883` |
| `mqtt.use_tls` | — | Enable TLS | `false` |
| `mqtt.topic_prefix` | — | MQTT topic root | `amos` |
| `collection_interval_ms` | — | Sensor polling interval | `100` |
| `heartbeat_interval_secs` | — | Health publish interval | `30` |
| `inference.enabled` | — | Enable ONNX inference | `true` |
| `inference.anomaly_threshold` | — | Alert threshold (MSE) | `0.05` |
| `inference.num_threads` | — | ONNX Runtime threads | `4` |

### Kubernetes ConfigMap (`configmap.yaml`)

| Key | Description |
|-----|-------------|
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka broker address |
| `INFLUXDB_URL` | InfluxDB HTTP endpoint |
| `MLFLOW_TRACKING_URI` | MLflow server URL |
| `ALERT_THRESHOLD_CRITICAL` | Score above which = critical alert |
| `ALERT_THRESHOLD_WARNING` | Score above which = warning alert |

---

## Production Checklist

- [ ] Change all default passwords (Kafka, InfluxDB, Grafana, MLflow)
- [ ] Enable TLS on all external-facing services
- [ ] Configure Kubernetes resource requests/limits on all Deployments
- [ ] Set up Prometheus + AlertManager for cluster monitoring
- [ ] Configure Kubernetes Horizontal Pod Autoscaler (HPA) for microservices
- [ ] Enable Kubernetes NetworkPolicy to restrict pod-to-pod communication
- [ ] Configure backup for InfluxDB (or use InfluxDB OSS with persistent volumes)
- [ ] Set up log aggregation (Loki / ELK) for production log analysis
- [ ] Obtain TLS certificates for all external hostnames
- [ ] Configure Kubernetes PodDisruptionBudgets for zero-downtime updates