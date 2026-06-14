# AMOS TSDB Service - Time-series data query API
# Reads from InfluxDB and provides REST endpoints for the dashboard

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from contextlib import asynccontextmanager
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tsdb-service")

# ─── Models ─────────────────────────────────────────────────

class TimeSeriesQuery(BaseModel):
    device_id: str
    sensor_name: Optional[str] = None
    start: str = "-7d"
    stop: str = "now()"
    aggregation: Optional[str] = None

class DataPoint(BaseModel):
    timestamp: str
    value: float

class TimeSeriesResponse(BaseModel):
    device_id: str
    sensor_name: str
    points: List[DataPoint]

class MachineSummary(BaseModel):
    device_id: str
    status: str = "unknown"
    last_seen: str
    sensor_count: int = 0
    avg_health_score: float = 0.0

class AnomalySummary(BaseModel):
    event_id: str
    device_id: str
    sensor_name: str
    timestamp: str
    anomaly_score: float
    severity: str

class HealthResponse(BaseModel):
    service: str = "tsdb-service"
    status: str = "healthy"

# ─── InfluxDB Query Client ───────────────────────────────────

class InfluxQueryClient:
    def __init__(self):
        self.url = os.getenv("INFLUXDB_URL", "http://localhost:8086")
        self.token = os.getenv("INFLUXDB_TOKEN", "amos-token")
        self.org = os.getenv("INFLUXDB_ORG", "amos")
        self.bucket = os.getenv("INFLUXDB_BUCKET", "amos_telemetry")
        self.client = None

    def connect(self):
        from influxdb_client import InfluxDBClient
        self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
        logger.info(f"TSDB query client connected to {self.url}")

    def query_sensor_data(self, device_id, sensor_name="", start="-7d", stop="now()"):
        if not self.client:
            logger.warning("InfluxDB not connected")
            return []

        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: {start}, stop: {stop})
            |> filter(fn: (r) => r._measurement == "sensor_reading")
            |> filter(fn: (r) => r.device_id == "{device_id}")
        '''
        if sensor_name:
            query += f'|> filter(fn: (r) => r.sensor_name == "{sensor_name}")\n'
        query += '|> yield(name: "results")'

        try:
            tables = self.client.query_api().query(query, org=self.org)
            points = []
            for table in tables:
                for record in table.records:
                    points.append({
                        "timestamp": record.get_time().isoformat(),
                        "value": record.get_value(),
                    })
            return points
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []

    def get_machines(self):
        if not self.client:
            return []
        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: -30d)
            |> filter(fn: (r) => r._measurement == "device_health")
            |> last()
            |> group(columns: ["device_id"])
        '''
        try:
            tables = self.client.query_api().query(query, org=self.org)
            machines = {}
            for table in tables:
                for record in table.records:
                    did = record.values.get("device_id", "unknown")
                    machines[did] = {
                        "device_id": did,
                        "last_seen": record.get_time().isoformat() if record.get_time() else "",
                        "status": record.values.get("status", "unknown"),
                    }
            return list(machines.values())
        except Exception as e:
            logger.error(f"Machines query failed: {e}")
            return []

    def get_summary(self, device_id, sensor_name=None):
        if not self.client:
            return {}
        sensor_filter = f'r.sensor_name == "{sensor_name}"' if sensor_name else 'r.sensor_name != ""'
        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: -7d)
            |> filter(fn: (r) => r._measurement == "sensor_reading")
            |> filter(fn: (r) => r.device_id == "{device_id}")
            |> filter(fn: (r) => {sensor_filter})
            |> mean()
        '''
        try:
            tables = self.client.query_api().query(query, org=self.org)
            values = [t.records[0].get_value() for t in tables if t.records]
            return {
                "device_id": device_id,
                "sensor_count": len(values),
                "avg_value": sum(values) / len(values) if values else 0,
                "period": "7d",
            }
        except Exception as e:
            logger.error(f"Summary query failed: {e}")
            return {"device_id": device_id, "error": str(e)}

    def close(self):
        if self.client:
            self.client.close()

# ─── FastAPI App ─────────────────────────────────────────────

influx = InfluxQueryClient()

@asynccontextmanager
async def lifespan(app: FastAPI):
    influx.connect()
    logger.info("TSDB service started")
    yield
    influx.close()

app = FastAPI(title="AMOS TSDB Service", version="0.1.0", lifespan=lifespan)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse()

@app.get("/api/v1/timeseries")
async def query_timeseries(
    device_id: str = Query(...),
    sensor_name: str = Query(None),
    start: str = Query("-7d"),
    stop: str = Query("now()"),
):
    """Query time-series sensor data."""
    try:
        points = influx.query_sensor_data(device_id, sensor_name or "", start, stop)
        return TimeSeriesResponse(
            device_id=device_id,
            sensor_name=sensor_name or "all",
            points=points,
        )
    except Exception as e:
        logger.error(f"Timeseries query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/machines")
async def list_machines():
    """List all machines with latest status."""
    try:
        machines = influx.get_machines()
        return {"machines": machines}
    except Exception as e:
        logger.error(f"Machine list failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/summary/{device_id}")
async def machine_summary(device_id: str):
    """Get summary statistics for a machine."""
    try:
        summary = influx.get_summary(device_id)
        return summary
    except Exception as e:
        logger.error(f"Summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/anomalies")
async def list_anomalies(
    device_id: str = Query(None),
    severity: str = Query(None),
    limit: int = Query(50),
):
    """List detected anomalies. (Stub - would query InfluxDB)"""
    return {"anomalies": [], "count": 0}