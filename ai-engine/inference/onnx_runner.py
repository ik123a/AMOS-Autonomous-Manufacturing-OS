#!/usr/bin/env python3
"""
AMOS ONNX Runtime Inference Runner
Wraps ONNX Runtime session for autoencoder-based anomaly detection.

Usage:
    runner = AnomalyDetector("models/anomaly.onnx")
    result = runner.detect([52.3, 65.2, 42.1, 38.9, 55.6, 61.0])
    print(result)  # {'anomaly_score': 0.023, 'is_anomaly': False, ...}
"""

import argparse
import time
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import onnxruntime as ort


@dataclass
class AnomalyResult:
    anomaly_score: float
    is_anomaly: bool
    threshold: float
    feature_errors: List[float]
    model_name: str
    execution_time_ms: float


class AnomalyDetector:
    """
    Loads an ONNX autoencoder and runs anomaly detection on sensor windows.

    The autoencoder is trained on normal operational data. During inference,
    a high reconstruction error signals that the input pattern deviates from
    learned normal behavior — indicating a potential fault or anomaly.
    """

    def __init__(
        self,
        model_path: str,
        threshold: float = 0.05,
        model_name: str = "anomaly_detector",
        providers: Optional[List[str]] = None,
    ):
        self.model_name = model_name
        self.threshold = threshold

        if providers is None:
            providers = ["CPUExecutionProvider"]

        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        self.session = ort.InferenceSession(model_path, sess_options, providers=providers)

        # Verify input shape
        inputs = self.session.get_inputs()
        assert len(inputs) == 1, f"Expected 1 input, got {len(inputs)}"
        self.input_name = inputs[0].name
        self.input_dim = inputs[0].shape[-1]

        # Outputs: [0] = reconstruction, [1] = latent (optional)
        outputs = self.session.get_outputs()
        self.output_name = outputs[0].name

        print(f"[AnomalyDetector] Loaded: {model_path}")
        print(f"  Input: {self.input_name} — dim={self.input_dim}")
        print(f"  Output: {self.output_name}")
        print(f"  Threshold: {threshold}")

    def detect(self, values: List[float]) -> AnomalyResult:
        """
        Run anomaly detection on a single sensor window.

        Args:
            values: List of sensor readings (must match input_dim)

        Returns:
            AnomalyResult with score, flag, and per-feature reconstruction errors
        """
        if len(values) != self.input_dim:
            raise ValueError(f"Expected {self.input_dim} values, got {len(values)}")

        start = time.perf_counter()
        input_data = np.array(values, dtype=np.float32).reshape(1, -1)

        outputs = self.session.run(
            [self.output_name],
            {self.input_name: input_data}
        )
        reconstruction = outputs[0].flatten()

        exec_ms = (time.perf_counter() - start) * 1000

        # Per-feature reconstruction error
        inputs_arr = np.array(values, dtype=np.float32)
        feature_errors = np.abs(inputs_arr - reconstruction).tolist()

        # Overall score = mean reconstruction error
        anomaly_score = float(np.mean(feature_errors))
        is_anomaly = anomaly_score > self.threshold

        return AnomalyResult(
            anomaly_score=anomaly_score,
            is_anomaly=is_anomaly,
            threshold=self.threshold,
            feature_errors=feature_errors,
            model_name=self.model_name,
            execution_time_ms=exec_ms,
        )

    def detect_batch(self, batch: List[List[float]]) -> List[AnomalyResult]:
        """Run detection on multiple windows (batched inference)."""
        if not batch:
            return []
        n = len(batch)
        inputs = np.array(batch, dtype=np.float32)

        start = time.perf_counter()
        outputs = self.session.run(
            [self.output_name],
            {self.input_name: inputs}
        )
        reconstructions = outputs[0]  # shape: (batch, input_dim)
        exec_ms = (time.perf_counter() - start) * 1000

        results = []
        for i in range(n):
            inputs_i = inputs[i]
            recon_i = reconstructions[i]
            feature_errors = np.abs(inputs_i - recon_i).tolist()
            anomaly_score = float(np.mean(feature_errors))
            results.append(AnomalyResult(
                anomaly_score=anomaly_score,
                is_anomaly=anomaly_score > self.threshold,
                threshold=self.threshold,
                feature_errors=feature_errors,
                model_name=self.model_name,
                execution_time_ms=exec_ms / n,
            ))
        return results

    def top_contributors(self, result: AnomalyResult, n: int = 3) -> List[tuple]:
        """Return the top N sensors contributing to the anomaly score."""
        indexed = list(enumerate(result.feature_errors))
        indexed.sort(key=lambda x: x[1], reverse=True)
        return indexed[:n]

    def __repr__(self) -> str:
        return f"AnomalyDetector(model={self.model_name}, dim={self.input_dim}, threshold={self.threshold})"


SENSOR_LABELS = [
    "Spindle_Temperature",
    "Spindle_Vibration",
    "Spindle_Torque",
    "Coolant_Flow",
    "Cutting_Speed",
    "Feed_Rate",
]


def main():
    parser = argparse.ArgumentParser(description="AMOS ONNX Runtime inference runner")
    parser.add_argument("--model", required=True, help="Path to .onnx model file")
    parser.add_argument("--threshold", type=float, default=0.05, help="Anomaly threshold (MSE)")
    parser.add_argument(
        "--input",
        type=float,
        nargs="+",
        help="Space-separated sensor values for a single detection",
    )
    args = parser.parse_args()

    detector = AnomalyDetector(args.model, threshold=args.threshold)

    if args.input:
        result = detector.detect(args.input)
        print(f"\nInput: {args.input}")
        print(f"Anomaly Score: {result.anomaly_score:.4f} (threshold={result.threshold:.4f})")
        print(f"Is Anomaly: {result.is_anomaly}")
        print(f"Execution: {result.execution_time_ms:.2f}ms")
        print("\nPer-sensor reconstruction errors:")
        for label, error in zip(SENSOR_LABELS, result.feature_errors):
            bar = "█" * min(int(error * 50), 40)
            print(f"  {label:22s} {error:.4f}  {bar}")
    else:
        # Demo: run on synthetic normal and anomalous data
        print("\n=== Demo: Normal Data ===")
        normal = [62.0, 5.2, 35.0, 4.5, 150.0, 0.8]
        result = detector.detect(normal)
        print(f"  Score: {result.anomaly_score:.4f}, Anomaly: {result.is_anomaly}")

        print("\n=== Demo: Anomalous Data (high vibration + temp) ===")
        anomaly = [82.0, 12.3, 35.0, 4.5, 150.0, 0.8]
        result = detector.detect(anomaly)
        print(f"  Score: {result.anomaly_score:.4f}, Anomaly: {result.is_anomaly}")
        print("  Top contributors:")
        for label, error in detector.top_contributors(result, n=3):
            print(f"    {label}: {error:.4f}")


if __name__ == "__main__":
    main()