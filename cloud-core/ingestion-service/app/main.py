# AMOS Ingestion Service
# Receives sensor data from edge agents, publishes to Kafka, writes to InfluxDB

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingestion-service")

# ─── Models ─────────────────────────────────────────────────

class SensorReading(BaseModel):
    timestamp: str
    device_id: str
    sensor_name: str
    value: float
    unit: Optional[str] = None
    quality: str = "good"

class TelemetryBatch(BaseModel):
    timestamp: str
    device_id: str
    readings: List[SensorReading]

class HealthHeartbeat(BaseModel):
    timestamp: str
    device_id: str
    status: str = "running"
    cpu_usage_percent: Optional[float] = None
    memory_usage_percent: Optional[float] = None
    uptime_seconds: Optional[int] = None

class HealthResponse(BaseModel):
    service: str = "ingestion-service"
    status: str = "healthy"
    version: str = "0.1.0"

# ─── Kafka Producer ─────────────────────────────────────────

class KafkaProducerClient:
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.producer = None

    async def start(self):
        from aiokafka import AIOKafkaProducer
        import json
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all",
            retry_backoff_ms=500,
        )
        await self.producer.start()
        logger.info(f"Kafka producer connected to {self.bootstrap_servers}")

    async def produce(self, topic: str, message: dict):
        import json
        if not self.producer:
            logger.warning("Kafka producer not started, message dropped")
            return
        try:
            await self.producer.send_and_wait(topic, message)
            logger.debug(f"Published to {topic}: {message.get('device_id')}")
        except Exception as e:
            logger.error(f"Failed to publish to {topic}: {e}")

    async def stop(self):
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")

# ─── InfluxDB Client ────────────────────────────────────────

class InfluxClient:
    def __init__(self, url=None, token=None, org=None, bucket=None):
        from influxdb_client import InfluxDBClient, Point
        from influxdb_client.client.write_api import SYNCHRONOUS
        self.url = url or os.getenv("INFLUXDB_URL", "http://localhost:8086")
        self.token = token or os.getenv("INFLUXDB_TOKEN", "amos-token")
        self.org = org or os.getenv("INFLUXDB_ORG", "amos")
        self.bucket = bucket or os.getenv("INFLUXDB_BUCKET", "amos_telemetry")
        self.client = None
        self._Point = Point
        self._SYNCHRONOUS = SYNCHRONOUS

    def connect(self):
        from influxdb_client import InfluxDBClient
        self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
        logger.info(f"Connected to InfluxDB at {self.url}")

    def write_telemetry(self, device_id, sensor_name, value, unit="", quality="good"):
        if not self.client:
            logger.warning("InfluxDB not connected")
            return
        try:
            point = (
                self._Point("sensor_reading")
                .tag("device_id", device_id)
                .tag("sensor_name", sensor_name)
                .tag("unit", unit)
                .tag("quality", quality)
                .field("value", value)
            )
            write_api = self.client.write_api(write_options=self._SYNCHRONOUS)
            write_api.write(bucket=self.bucket, record=point)
        except Exception as e:
            logger.error(f"Failed to write telemetry: {e}")

    def write_health(self, device_id, status, cpu=0.0, memory=0.0, uptime=0):
        if not self.client:
            return
        try:
            point = (
                self._Point("device_health")
                .tag("device_id", device_id)
                .tag("status", status)
                .field("cpu_usage_percent", cpu)
                .field("memory_usage_percent", memory)
                .field("uptime_seconds", uptime)
            )
            write_api = self.client.write_api(write_options=self._SYNCHRONOUS)
            write_api.write(bucket=self.bucket, record=point)
        except Exception as e:
            logger.error(f"Failed to write health: {e}")

    def close(self):
        if self.client:
            self.client.close()

# ─── FastAPI App ─────────────────────────────────────────────

kafka_producer = KafkaProducerClient(
    bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
)
influx = InfluxClient()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await kafka_producer.start()
    influx.connect()
    logger.info("Ingestion service started")
    yield
    await kafka_producer.stop()
    influx.close()
    logger.info("Ingestion service stopped")

app = FastAPI(title="AMOS Ingestion Service", version="0.1.0", lifespan=lifespan)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse()

@app.post("/api/v1/telemetry")
async def ingest_telemetry(batch: TelemetryBatch):
    """Receive sensor data from edge agents."""
    try:
        await kafka_producer.produce("amos-telemetry", batch.model_dump())
        for reading in batch.readings:
            influx.write_telemetry(
                device_id=batch.device_id,
                sensor_name=reading.sensor_name,
                value=reading.value,
                unit=reading.unit or "",
                quality=reading.quality,
            )
        logger.info(f"Ingested {len(batch.readings)} readings from {batch.device_id}")
        return {"status": "ok", "readings_count": len(batch.readings)}
    except Exception as e:
        logger.error(f"Failed to ingest telemetry: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/health")
async def ingest_health(heartbeat: HealthHeartbeat):
    """Receive health heartbeats from edge agents."""
    try:
        await kafka_producer.produce("amos-device-health", heartbeat.model_dump())
        influx.write_health(
            device_id=heartbeat.device_id,
            status=heartbeat.status,
            cpu=heartbeat.cpu_usage_percent or 0.0,
            memory=heartbeat.memory_usage_percent or 0.0,
            uptime=heartbeat.uptime_seconds or 0,
        )
        logger.info(f"Health heartbeat from {heartbeat.device_id}: {heartbeat.status}")
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Failed to ingest health: {e}")
        raise HTTPException(status_code=500, detail=str(e))