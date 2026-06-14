#!/usr/bin/env python3
"""
AMOS Stream Processor
Real-time sliding window inference for streaming sensor data.

Usage:
    processor = StreamProcessor(model_path="models/anomaly.onnx")
    processor.process({"sensor_0": 12.5, "sensor_1": 45.2, ...})
"""

import logging
import threading
from collections import deque
from typing import Callable, Optional, List, Dict, Any
from dataclasses import dataclass, field

import numpy as np

from onnx_runner import AnomalyDetector

logger = logging.getLogger("amos-stream-processor")


@dataclass
class AnomalyEvent:
    """Event emitted when an anomaly is detected."""
    timestamp: float
    anomaly_score: float
    threshold: float
    sensor_contributions: List[Dict]
    buffer_snapshot: List[float]
    device_id: str = "unknown"


class SlidingWindowBuffer:
    """Maintains a sliding window of sensor values for inference."""

    def __init__(self, buffer_size: int = 100, input_size: int = 16):
        self.buffer_size = buffer_size
        self.input_size = input_size
        self.buffer: deque = deque(maxlen=buffer_size)
        self.running_mean: Optional[float] = None
        self.running_std: Optional[float] = None

    def add(self, value: float):
        """Add a single sensor value to the buffer."""
        self.buffer.append(value)
        # Update running stats
        if len(self.buffer) >= 2:
            arr = np.array(self.buffer)
            self.running_mean = float(np.mean(arr))
            self.running_std = float(np.std(arr)) + 1e-8

    def is_ready(self) -> bool:
        """Check if buffer has enough data for inference."""
        return len(self.buffer) >= self.input_size

    def get_normalized(self) -> np.ndarray:
        """Get the most recent input_size values, z-score normalized."""
        if len(self.buffer) < self.input_size:
            return None

        recent = list(self.buffer)[-self.input_size:]
        arr = np.array(recent, dtype=np.float32)

        if self.running_mean is not None and self.running_std is not None:
            arr = (arr - self.running_mean) / self.running_std

        return arr

    def get_raw(self) -> List[float]:
        """Get the most recent input_size raw values."""
        if len(self.buffer) < self.input_size:
            return []
        return list(self.buffer)[-self.input_size:]

    def reset(self):
        """Clear the buffer."""
        self.buffer.clear()
        self.running_mean = None
        self.running_std = None


class StreamProcessor:
    """Processes streaming sensor data with sliding window inference."""

    def __init__(
        self,
        model_path: str,
        threshold: float = 0.05,
        input_size: int = 16,
        buffer_size: int = 100,
        device_id: str = "unknown",
        anomaly_callback: Optional[Callable[[AnomalyEvent], None]] = None,
        cooldown_seconds: float = 30.0,
    ):
        self.detector = AnomalyDetector(
            model_path=model_path,
            threshold=threshold,
            input_size=input_size,
        )
        self.buffer = SlidingWindowBuffer(
            buffer_size=buffer_size,
            input_size=input_size,
        )
        self.device_id = device_id
        self.anomaly_callback = anomaly_callback
        self.cooldown_seconds = cooldown_seconds
        self._last_alert_time = 0.0
        self._sensor_names: List[str] = []
        self._lock = threading.Lock()
        self._total_processed = 0
        self._anomaly_count = 0

        logger.info(
            f"StreamProcessor initialized | device={device_id} | "
            f"model={model_path} | threshold={threshold} | "
            f"input_size={input_size}"
        )

    def set_sensor_names(self, names: List[str]):
        """Set the names of monitored sensors (for explainability)."""
        self._sensor_names = names

    def process(self, sensor_readings: Dict[str, float]) -> Optional[AnomalyEvent]:
        """Process a dictionary of sensor readings.

        Args:
            sensor_readings: Dict mapping sensor_name -> value
                            (e.g., {"vibration": 12.5, "temperature": 65.2, ...})

        Returns:
            AnomalyEvent if anomaly detected, None otherwise
        """
        import time

        # Flatten to single vector (sorted by sensor name for consistency)
        if not self._sensor_names:
            self._sensor_names = sorted(sensor_readings.keys())

        values = [sensor_readings.get(name, 0.0) for name in self._sensor_names]

        # Add each value to its own buffer (multi-sensor support)
        # For simplicity, flatten all sensor values into one buffer
        # In production: one buffer per sensor
        with self._lock:
            for v in values:
                self.buffer.add(v)
            self._total_processed += 1

        # Check if ready for inference
        if not self.buffer.is_ready():
            return None

        # Get normalized input
        input_vector = self.buffer.get_normalized()
        if input_vector is None:
            return None

        # Run inference
        result = self.detector.predict(input_vector.tolist())

        # Check anomaly
        if not result["is_anomaly"]:
            return None

        # Rate limiting
        now = time.time()
        if now - self._last_alert_time < self.cooldown_seconds:
            logger.debug(f"Anomaly detected but in cooldown ({now - self._last_alert_time:.0f}s)")
            return None

        self._last_alert_time = now
        self._anomaly_count += 1

        # Create event
        event = AnomalyEvent(
            timestamp=now,
            anomaly_score=result["anomaly_score"],
            threshold=result["threshold"],
            sensor_contributions=result["sensor_contributions"],
            buffer_snapshot=self.buffer.get_raw(),
            device_id=self.device_id,
        )

        logger.warning(
            f"ANOMALY DETECTED | device={self.device_id} | "
            f"score={event.anomaly_score:.4f} | "
            f"threshold={event.threshold} | "
            f"total_anomalies={self._anomaly_count}"
        )

        # Fire callback
        if self.anomaly_callback:
            try:
                self.anomaly_callback(event)
            except Exception as e:
                logger.error(f"Anomaly callback failed: {e}")

        return event

    def process_raw(self, values: List[float]) -> Optional[AnomalyEvent]:
        """Process a raw list of sensor values.

        Args:
            values: Flat list of sensor readings

        Returns:
            AnomalyEvent if anomaly detected, None otherwise
        """
        with self._lock:
            for v in values:
                self.buffer.add(v)
            self._total_processed += 1

        if not self.buffer.is_ready():
            return None

        input_vector = self.buffer.get_normalized()
        if input_vector is None:
            return None

        result = self.detector.predict(input_vector.tolist())

        if not result["is_anomaly"]:
            return None

        import time
        now = time.time()
        if now - self._last_alert_time < self.cooldown_seconds:
            return None

        self._last_alert_time = now
        self._anomaly_count += 1

        event = AnomalyEvent(
            timestamp=now,
            anomaly_score=result["anomaly_score"],
            threshold=result["threshold"],
            sensor_contributions=result["sensor_contributions"],
            buffer_snapshot=self.buffer.get_raw(),
            device_id=self.device_id,
        )

        if self.anomaly_callback:
            try:
                self.anomaly_callback(event)
            except Exception as e:
                logger.error(f"Anomaly callback failed: {e}")

        return event

    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        with self._lock:
            return {
                "device_id": self.device_id,
                "total_processed": self._total_processed,
                "anomaly_count": self._anomaly_count,
                "buffer_size": len(self.buffer.buffer),
                "buffer_ready": self.buffer.is_ready(),
                "threshold": self.detector.threshold,
            }

    def reset(self):
        """Reset processor state."""
        with self._lock:
            self.buffer.reset()
            self._total_processed = 0
            self._anomaly_count = 0
            self._last_alert_time = 0.0
        logger.info("StreamProcessor reset")


# ─── CLI Demo ────────────────────────────────────────────────

if __name__ == "__main__":
    import time
    import json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    def on_anomaly(event: AnomalyEvent):
        print("=" * 60)
        print(f"ANOMALY EVENT")
        print(f"  Device:    {event.device_id}")
        print(f"  Score:     {event.anomaly_score:.4f}")
        print(f"  Threshold: {event.threshold}")
        print(f"  Top sensor contribution: {event.sensor_contributions[0] if event.sensor_contributions else 'N/A'}")
        print("=" * 60)

    # Create processor
    processor = StreamProcessor(
        model_path="../models/anomaly.onnx",
        threshold=0.05,
        device_id="demo-edge-001",
        anomaly_callback=on_anomaly,
        cooldown_seconds=5.0,
    )

    # Simulate streaming data
    print("Starting streaming demo...")
    sensor_names = ["vibration", "temperature", "torque", "pressure"]

    for i in range(200):
        # Normal data
        readings = {
            name: 50 + 10 * np.sin(i * 0.1 + j) + np.random.randn() * 2
            for j, name in enumerate(sensor_names)
        }

        # Inject anomaly every 50 samples
        if i % 50 == 0 and i > 0:
            readings["vibration"] += 100  # Spike!

        event = processor.process(readings)
        if event:
            print(f"Step {i}: ** ANOMALY ** score={event.anomaly_score:.4f}")

        time.sleep(0.05)

    print(f"\nStats: {json.dumps(processor.get_stats(), indent=2)}")