# AMOS Alert Service - Alert management and notification dispatch

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
import uuid
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alert-service")

# ─── Models ─────────────────────────────────────────────────

class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertStatus(str, Enum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"

class AlertCreate(BaseModel):
    device_id: str
    sensor_name: str
    anomaly_score: float
    severity: AlertSeverity = AlertSeverity.MEDIUM
    message: str
    value: float = 0.0
    threshold: float = 0.05
    recommended_action: Optional[str] = None

class Alert(BaseModel):
    id: str
    device_id: str
    sensor_name: str
    anomaly_score: float
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.NEW
    message: str
    value: float
    threshold: float
    recommended_action: Optional[str] = None
    created_at: str
    acknowledged_at: Optional[str] = None
    resolved_at: Optional[str] = None
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None

class AlertAcknowledge(BaseModel):
    acknowledged_by: str = "operator"

class AlertResolve(BaseModel):
    resolved_by: str = "operator"
    resolution_notes: Optional[str] = None

class HealthResponse(BaseModel):
    service: str = "alert-service"
    status: str = "healthy"
    alert_count: int = 0

# ─── Webhook Dispatcher ──────────────────────────────────────

class WebhookDispatcher:
    def __init__(self):
        self.slack_url = os.getenv("SLACK_WEBHOOK_URL", "")

    async def dispatch(self, alert: dict):
        tasks = []
        if self.slack_url:
            tasks.append(self._send_slack(alert))
        if tasks:
            import asyncio
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    logger.error(f"Webhook delivery failed: {r}")

    async def _send_slack(self, alert: dict):
        import httpx
        severity_colors = {
            "low": "#808080",
            "medium": "#FFA500",
            "high": "#FF4500",
            "critical": "#FF0000",
        }
        payload = {
            "attachments": [{
                "color": severity_colors.get(alert.get("severity", "low"), "#808080"),
                "title": f"AMOS Alert: {alert.get('severity', 'UNKNOWN').upper()}",
                "fields": [
                    {"title": "Device", "value": alert.get("device_id", "N/A"), "short": True},
                    {"title": "Sensor", "value": alert.get("sensor_name", "N/A"), "short": True},
                    {"title": "Message", "value": alert.get("message", "N/A"), "short": False},
                    {"title": "Score", "value": f"{alert.get('anomaly_score', 0):.4f}", "short": True},
                    {"title": "Value", "value": f"{alert.get('value', 0):.2f}", "short": True},
                    {"title": "Action", "value": alert.get("recommended_action", "Inspect machine"), "short": False},
                ],
                "footer": "AMOS Predictive Maintenance",
            }]
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.slack_url, json=payload, timeout=10.0)
            response.raise_for_status()
            logger.info(f"Slack alert sent for {alert.get('device_id')}")

# ─── FastAPI App ─────────────────────────────────────────────

alerts_store: dict[str, Alert] = {}
webhook = WebhookDispatcher()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Alert service started")
    yield

app = FastAPI(title="AMOS Alert Service", version="0.1.0", lifespan=lifespan)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(alert_count=len(alerts_store))

@app.post("/api/v1/alerts")
async def create_alert(alert_data: AlertCreate):
    """Create a new alert from edge agent or ML engine."""
    now = datetime.now(timezone.utc).isoformat()
    alert = Alert(
        id=str(uuid.uuid4()),
        device_id=alert_data.device_id,
        sensor_name=alert_data.sensor_name,
        anomaly_score=alert_data.anomaly_score,
        severity=alert_data.severity,
        status=AlertStatus.NEW,
        message=alert_data.message,
        value=alert_data.value,
        threshold=alert_data.threshold,
        recommended_action=alert_data.recommended_action,
        created_at=now,
    )
    alerts_store[alert.id] = alert
    logger.warning(
        f"ALERT [{alert.severity.value.upper()}] {alert.id[:8]} - "
        f"{alert.message} on {alert.device_id} (score={alert.anomaly_score:.4f})"
    )
    # Fire webhook for critical alerts
    if alert.severity.value in ("high", "critical"):
        await webhook.dispatch(alert.model_dump())
    return alert

@app.get("/api/v1/alerts")
async def list_alerts(
    device_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(50),
):
    """List alerts with optional filters."""
    results = list(alerts_store.values())
    if device_id:
        results = [a for a in results if a.device_id == device_id]
    if status:
        results = [a for a in results if a.status.value == status]
    if severity:
        results = [a for a in results if a.severity.value == severity]
    results.sort(key=lambda a: a.created_at, reverse=True)
    return {"alerts": results[:limit], "total": len(results)}

@app.put("/api/v1/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, body: AlertAcknowledge):
    """Acknowledge an alert."""
    if alert_id not in alerts_store:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert = alerts_store[alert_id]
    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_at = datetime.now(timezone.utc).isoformat()
    alert.acknowledged_by = body.acknowledged_by
    logger.info(f"Alert {alert_id[:8]} acknowledged by {body.acknowledged_by}")
    return alert

@app.post("/api/v1/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, body: AlertResolve):
    """Resolve an alert after investigation."""
    if alert_id not in alerts_store:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert = alerts_store[alert_id]
    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = datetime.now(timezone.utc).isoformat()
    alert.resolved_by = body.resolved_by
    logger.info(f"Alert {alert_id[:8]} resolved by {body.resolved_by}")
    return alert

@app.get("/api/v1/alerts/{alert_id}")
async def get_alert(alert_id: str):
    """Get a single alert by ID."""
    if alert_id not in alerts_store:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alerts_store[alert_id]