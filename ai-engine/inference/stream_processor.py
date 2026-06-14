#!/usr/bin/env python3
"""
AMOS Stream Processor
Real-time sliding-window inference for streaming sensor data.

Usage:
    processor = StreamProcessor(model_path="models/anomaly.onnx")
    processor.on_anomaly(lambda r: send_alert(r))  # callback
    processor.start(mqtt_broker="mqtt.amos.io", topic="plant1/#")
"""

import threading
import time
import json
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import paho.mqtt.client as mqtt
from numpy.typing import NDArray
import numpy as np


@dataclass
class AnomalyEvent:
    device_id: str
    sensor_name: str
    anomaly_score: float
    threshold: float
    is_anomaly: bool
    feature_errors: Dict[str, float]
    timestamp: str
    window: List[float]


class StreamProcessor:
    """
    Maintains a sliding window buffer per device and runs inference
    each time the buffer fills. Emits anomaly events via callback.
    """

    def __init__(
        self,
        model_path: str,
        window_size: int = 12,
        threshold: float = 0.05,
        cooldown_secs: float = 30.0,
        sensor_labels: Optional[List[str]] = None,
    ):
        from .onnx_runner import AnomalyDetector
        self.detector = AnomalyDetector(model_path, threshold=threshold)
        self.window_size = window_size
        self.cooldown_secs = cooldown_secs
        self.sensor_labels = sensor_labels or [
            "Spindle_Temperature", "Spindle_Vibration", "Spindle_Torque",
            "Coolant_Flow", "Cutting_Speed", "Feed_Rate",
        ]

        # Per-device sliding windows
        self.windows: Dict[str, deque] = {}
        # Per-device last alert time
        self.last_alert: Dict[str, float] = {}

        self.anomaly_callback: Optional[Callable[[AnomalyEvent], None]] = None
        self._lock = threading.Lock()
        self._running = False

    def on_anomaly(self, callback: Callable[[AnomalyEvent], None]) -> None:
        """Register a callback for anomaly events."""
        self.anomaly_callback = callback

    def ingest(self, device_id: str, sensor_values: List[float], timestamp: str) -> Optional[AnomalyEvent]:
        """
        Ingest a reading from a device. Returns AnomalyEvent if anomaly detected.
        Callers can use this directly without MQTT.
        """
        if len(sensor_values) != self.detector.input_dim:
            raise ValueError(
                f"Expected {self.detector.input_dim} sensor values, got {len(sensor_values)}"
            )

        with self._lock:
            # Init or reset window for this device
            if device_id not in self.windows:
                self.windows[device_id] = deque(maxlen=self.window_size)

            self.windows[device_id].append(sensor_values)

            # Only run inference when window is full
            if len(self.windows[device_id]) < self.window_size:
                return None

            # Run inference on the average of the window
            window_arr = np.array(self.windows[device_id])
            avg_values = window_arr.mean(axis=0).tolist()
            result = self.detector.detect(avg_values)

            # Cooldown check
            now = time.time()
            last = self.last_alert.get(device_id, 0)
            in_cooldown = (now - last) < self.cooldown_secs

            if result.is_anomaly and not in_cooldown:
                self.last_alert[device_id] = now

                # Build per-sensor errors dict
                errors_dict = dict(zip(self.sensor_labels, result.feature_errors))

                event = AnomalyEvent(
                    device_id=device_id,
                    sensor_name="",  # multi-sensor
                    anomaly_score=result.anomaly_score,
                    threshold=result.threshold,
                    is_anomaly=True,
                    feature_errors=errors_dict,
                    timestamp=timestamp,
                    window=avg_values,
                )

                if self.anomaly_callback:
                    try:
                        self.anomaly_callback(event)
                    except Exception as e:
                        print(f"[StreamProcessor] Callback error: {e}")

                return event

        return None

    def start_mqtt(
        self,
        broker: str,
        port: int = 8883,
        topic: str = "amos/+/telemetry",
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> mqtt.Client:
        """Start consuming telemetry from MQTT broker."""
        client = mqtt.Client()
        if username:
            client.username_pw_set(username, password)

        def on_connect(c, u, f, rc):
            if rc == 0:
                print(f"[StreamProcessor] Connected to MQTT {broker}:{port}")
                c.subscribe(topic, qos=1)
            else:
                print(f"[StreamProcessor] MQTT connection failed: rc={rc}")

        def on_message(c, userdata, msg):
            try:
                payload = json.loads(msg.payload.decode())
                device_id = payload.get("device_id", "unknown")
                timestamp = payload.get("timestamp", "")

                for reading in payload.get("readings", []):
                    # Accumulate into the device's multi-sensor window
                    self.ingest(
                        device_id=device_id,
                        sensor_values=[r["value"] for r in payload.get("readings", [])],
                        timestamp=timestamp,
                    )
                    break  # one ingestion per payload
            except Exception as e:
                print(f"[StreamProcessor] Parse error: {e}")

        client.on_connect = on_connect
        client.on_message = on_message
        client.tls_set()
        client.connect(broker, port, keepalive=60)
        self._running = True
        client.loop_start()
        return client

    def stop(self) -> None:
        self._running = False


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python stream_processor.py <model.onnx>")
        sys.exit(1)

    processor = StreamProcessor(sys.argv[1], window_size=6, cooldown_secs=60)

    def on_anomaly(event: AnomalyEvent):
        print(f"\n{'='*60}")
        print(f"  ANOMALY DETECTED — {event.device_id}")
        print(f"  Score: {event.anomaly_score:.4f} (threshold: {event.threshold:.4f})")
        print(f"  Time:  {event.timestamp}")
        print("  Top contributors:")
        sorted_errors = sorted(event.feature_errors.items(), key=lambda x: x[1], reverse=True)
        for label, error in sorted_errors[:3]:
            print(f"    {label}: {error:.4f}")

    processor.on_anomaly(on_anomaly)
    print("StreamProcessor ready — send test readings via processor.ingest()")
    print(f"  Window size: {processor.window_size}")
    print(f"  Threshold:   {processor.detector.threshold}")

    # Example: send a synthetic normal reading
    normal_reading = [62.0, 5.2, 35.0, 4.5, 150.0, 0.8]
    result = processor.ingest("test-device-01", normal_reading, time.strftime("%Y-%m-%dT%H:%M:%SZ"))
    print(f"\nNormal reading result: {result}")

    # Example: send a synthetic anomalous reading
    bad_reading = [85.0, 14.2, 35.0, 4.5, 150.0, 0.8]
    result = processor.ingest("test-device-01", bad_reading, time.strftime("%Y-%m-%dT%H:%M:%SZ"))
    print(f"Anomalous reading result: {result}")