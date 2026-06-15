# AMOS Deployment Guide

This guide covers deploying AMOS from development to production.

---

## 1. Local Development

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 20+
- Rust 1.76+ (for edge agent development)

### Start the cloud stack

```bash
cd cloud-core

# Create required directories
mkdir -p models kafka-data influxdb-data grafana-data mlflow-data

# Start all services
docker-compose up -d

# Verify all services are healthy
docker-compose ps
```

Services available:
| Service | URL | Credentials |
|---------|-----|-------------|
| Dashboard | http://localhost:5173 | — |
| Alert API | http://localhost:8003 | — |
| TSDB API | http://localhost:8002 | — |
| Ingestion API | http://localhost:8001 | — |
| MLOps API | http://localhost:8004 | — |
| Grafana | http://localhost:3000 | admin / amos_admin_2024 |
| Kafka UI | http://localhost:8080 | — |
| MLflow | http://localhost:5000 | — |

### Start the dashboard

```bash
cd dashboard
npm install --legacy-peer-deps
npm run dev
# Dashboard → http://localhost:5173
```

### Build and run the edge agent

```bash
cd edge-agent

# Build the release binary
cargo build --release

# Run (point at local cloud stack)
./target/release/amos-edge-agent \
  --config config/edge-config.yaml
```

### Simulate sensor data (no real PLC needed)

The edge agent's OPC-UA collector works in simulation mode when no PLC is present. You can also use the included script to generate synthetic telemetry directly to the cloud:

```bash
# From cloud-core/ directory
python3 scripts/simulate_sensor_data.py --device edge-plant1-001 --duration 3600
```

---

## 2. Edge Device Setup

Recommended hardware: **Advantech UNO-2271G V3**
- Intel Atom x7211RE (2 cores, 2.0 GHz)
- 8GB RAM, 64GB SSD
- Dual GbE LAN (one for PLC network, one for plant network)
- Fanless, DIN-rail mountable

### Flashing the edge device

1. Flash Ubuntu Server 22.04 LTS to a USB stick
2. Connect to management network, install:
   ```bash
   curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
   apt-get install -y nodejs docker.io docker-compose
   usermod -aG docker amos
   ```

3. Copy the edge agent binary:
   ```bash
   # Copy from your build machine
   scp amos-edge-agent amos@edge-device:/usr/local/bin/
   ssh amos@edge-device "chmod +x /usr/local/bin/amos-edge-agent"

   # Copy config (never commit this to git)
   scp edge-config.yaml amos@edge-device:/etc/amos/edge-config.yaml
   ```

4. Set up as a systemd service:
   ```bash
   sudo tee /etc/systemd/system/amos-edge-agent.service <<'EOF'
   [Unit]
   Description=AMOS Edge Agent
   After=network.target docker.service

   [Service]
   Type=simple
   User=amos
   ExecStart=/usr/local/bin/amos-edge-agent --config /etc/amos/edge-config.yaml
   Restart=always
   RestartSec=10
   StandardOutput=journal
   StandardError=journal

   [Install]
   WantedBy=multi-user.target
   EOF

   sudo systemctl enable amos-edge-agent
   sudo systemctl start amos-edge-agent
   sudo systemctl status amos-edge-agent
   ```

5. Verify it's running:
   ```bash
   journalctl -u amos-edge-agent -f
   # Should see: "AMOS Edge Agent v0.1.0 starting up..."
   ```

### Network configuration

The edge device needs:
- Port 8883 (MQTT over TLS) outbound to cloud broker
- Port 443 (HTTPS) outbound for MLflow model downloads
- Port 4840 (OPC-UA) inbound from PLC network (if PLC is on same subnet)

```bash
# Verify MQTT connectivity
openssl s_client -connect broker.amos-platform.io:8883 -quiet
```

### Connecting to a real PLC (OPC-UA)

Edit `/etc/amos/edge-config.yaml`:

```yaml
opcua:
  endpoint: "opc.tcp://plc-plant-network:4840"  # Replace with your PLC IP
  application_name: "AMOS Edge Agent"
  security_policy: "Basic256Sha256"              # Match your PLC config
  auth_mode: "UsernamePassword"
  username: "amos_reader"                         # Create read-only PLC account
  password: "your-secure-password"
  monitored_nodes:
    - node_id: "ns=2;i=1001"
      name: "Spindle_Temperature"
      unit: "C"
    - node_id: "ns=2;i=1002"
      name: "Spindle_Vibration"
      unit: "mm/s"
```

---

## 3. Production Kubernetes Deployment

### Prerequisites
- Kubernetes 1.28+ (EKS, AKS, or on-prem)
- kubectl configured with cluster access
- Docker registry credentials (GHCR or private registry)
- Stateful storage (PVC support for InfluxDB, Kafka)

### Container images

Build and push all services:

```bash
# Log in to registry
docker login ghcr.io -u ik123a

# Build all services
for svc in ingestion-service tsdb-service alert-service mlops-service; do
  docker build -t ghcr.io/ik123a/AMOS-Autonomous-Manufacturing-OS/$svc:latest ./cloud-core/$svc
  docker push ghcr.io/ik123a/AMOS-Autonomous-Manufacturing-OS/$svc:latest
done
```

Or use the GitHub Actions pipeline (it handles this on push to `main`).

### Deploy the AMOS stack

```bash
# Create namespace
kubectl apply -f infrastructure/k8s/namespace.yaml

# Apply all manifests
kubectl apply -f infrastructure/k8s/

# Check pod status
kubectl get pods -n amos

# Watch rollout
kubectl rollout status deployment/ingestion-service -n amos --timeout=120s
kubectl rollout status deployment/tsdb-service -n amos --timeout=120s
```

### External access

The K8s services are ClusterIP by default. To expose externally:

**Option A — Ingress (recommended for production):**
```bash
kubectl apply -f infrastructure/k8s/ingress.yaml
# Requires: ingress-nginx controller, cert-manager, and a valid domain
```

**Option B — NodePort (staging only):**
```bash
# Change service type in each service manifest, or:
kubectl patch service ingestion-service -n amos -p '{"spec":{"type":"NodePort"}}'
```

### Persistent storage

InfluxDB and Kafka require persistent volumes. The manifests include `PersistentVolumeClaim` resources but you'll need a `StorageClass` in your cluster:

```bash
# AWS EKS
kubectl apply -f - <<'EOF'
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: amos-gp3
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  fiops: "6000"
  throughput: "250"
EOF

# Then patch the PVCs to use it:
kubectl patch pvc influxdb-pvc -n amos -p '{"spec":{"storageClassName":"amos-gp3"}}'
```

### Environment variables for production

Override the ConfigMap values for production:

```bash
kubectl create configmap amos-config -n amos \
  --from-literal=KAFKA_BOOTSTRAP_SERVERS="kafka Amos:9092" \
  --from-literal=INFLUXDB_URL="http://influxdb.amos.svc.cluster.local:8086" \
  --from-literal=ALERT_THRESHOLD_CRITICAL="0.8" \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Secrets management

Never commit secrets to the ConfigMap. Use Kubernetes Secrets or a vault:

```bash
# Create a TLS secret for the ingress
kubectl create secret tls amos-tls -n amos \
  --cert=path/to/cert.pem \
  --key=path/to/key.pem

# Or use cert-manager to auto-provision via Let's Encrypt
```

### Verifying the deployment

```bash
# Port-forward to test locally
kubectl port-forward -n amos svc/ingestion-service 8001:80
kubectl port-forward -n amos svc/tsdb-service 8002:80
kubectl port-forward -n amos svc/grafana 3000:80

# Check all deployments
kubectl get deploy -n amos
kubectl get svc -n amos
kubectl get pods -n amos

# Tail logs
kubectl logs -n amos deployment/ingestion-service -f
```

---

## 4. Upgrading

### Edge agent (rolling update)

```bash
# Build new binary, copy to device
scp amos-edge-agent-new amos@edge-device:/usr/local/bin/amos-edge-agent

# Restart service
ssh amos@edge-device "sudo systemctl restart amos-edge-agent"
```

### Cloud services (Kubernetes)

```bash
# Trigger rolling update (images auto-updated by GitHub Actions)
kubectl rollout restart deployment/ingestion-service -n amos
kubectl rollout restart deployment/tsdb-service -n amos

# Or force image pull:
kubectl patch deployment ingestion-service -n amos \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"ingestion-service","imagePullPolicy":"Always"}]}}}}'
```

---

## 5. Monitoring & Alerting

### Grafana dashboards

1. Open Grafana at http://localhost:3000
2. Login with admin / amos_admin_2024
3. Navigate to Dashboards → Browse
4. Import dashboards from `cloud-core/grafana/dashboards/`

Pre-built dashboards:
- **AMOS Fleet Overview** — All machines, health scores, active alerts
- **Anomaly Detection** — Per-machine anomaly scores over time
- **Edge Agent Health** — CPU, memory, MQTT connection status

### Alert routing

Alerts are sent via webhook to configured endpoints. Edit `cloud-core/alert-service/app/main.py` to add Slack, PagerDuty, or email:

```python
# Slack example
if alert.severity == "critical":
    slack_webhook.send(f":red_alert: {alert.device_id} — {alert.message}")
```

---

## 6. Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Edge agent fails to start | Config syntax error | Run `python3 -c "import yaml; yaml.safe_load(open('edge-config.yaml'))"` |
| No telemetry in dashboard | MQTT not connected | Check `edge-config.yaml` broker URL and firewall |
| Dashboard shows "no data" | InfluxDB not receiving | Check `docker-compose logs tsdb-service` |
| High memory usage | Kafka consumer lag | Scale tsdb-service to 2+ replicas |
| Model not loading on edge | Wrong ONNX path | Verify `inference.model_path` in edge-config.yaml |
| Kubernetes pod CrashLoopBackOff | Missing env vars | Check `kubectl logs <pod> -n amos` |