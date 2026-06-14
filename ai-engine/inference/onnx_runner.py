#!/usr/bin/env python3
"""
AMOS ONNX Runtime Inference Runner
Wraps ONNX Runtime session for autoencoder-based anomaly detection.

Usage:
    runner = AnomalyDetector("models/anomaly.onnx")
    result = runner.predict(sensor_vector)
    print(result["anomaly_score"], result["is_anomaly"])
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

import numpy as np

logger = logging.getLogger("amos-inference-runner")


class AnomalyDetector:
    """ONNX Runtime wrapper for autoencoder anomaly detection."""

    def __init__(
        self,
        model_path: str,
        threshold: float = 0.05,
        input_size: int = 16,
        provider: str = "CPUExecutionProvider",
    ):
        self.model_path = Path(model_path)
        self.threshold = threshold
        self.input_size = input_size
        self.provider = provider
        self.session = None
        self.input_name = None
        self.output_name = None

        # Validate model exists
        if not self.model_path.exists():
            raise FileNotFoundError(f"ONNX model not found: {model_path}")

        self._load_model()

    def _load_model(self):
        """Load the ONNX model and create inference session."""
        import onnxruntime as ort

        # Check for available providers
        available = ort.get_available_providers()
        logger.info(f"Available ONNX providers: {available}")

        if self.provider not in available:
            logger.warning(
                f"Provider '{self.provider}' not available, falling back to CPU"
            )
            self.provider = "CPUExecutionProvider"

        # Create session with optimizations
        sess_options = ort.SessionOptions()
        sess_options.enable_cpu_mem_arena = True
        sess_options.enable_mem_reuse = True
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        self.session = ort.InferenceSession(
            str(self.model_path),
            sess_options=sess_options,
            providers=[self.provider],
        )

        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        actual_input_size = self.session.get_inputs()[0].shape[1]

        if actual_input_size and actual_input_size != self.input_size:
            logger.warning(
                f"Model expects input size {actual_input_size}, "
                f"but configured for {self.input_size}. Using model's size."
            )
            self.input_size = actual_input_size

        logger.info(
            f"Model loaded: {self.model_path.name} | "
            f"Input: {self.input_name}({self.input_size}) | "
            f"Output: {self.output_name} | "
            f"Provider: {self.provider}"
        )

    def predict(self, input_vector: List[float]) -> Dict[str, Any]:
        """Run inference on a single sensor vector.

        Args:
            input_vector: List of sensor readings (length must match input_size)

        Returns:
            Dict with keys: anomaly_score, is_anomaly, reconstruction,
                           sensor_contributions
        """
        if self.session is None:
            raise RuntimeError("Model not loaded. Call _load_model() first.")

        # Validate input
        arr = np.array(input_vector, dtype=np.float32)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)

        if arr.shape[1] != self.input_size:
            raise ValueError(
                f"Expected input size {self.input_size}, got {arr.shape[1]}"
            )

        # Run inference
        outputs = self.session.run(
            [self.output_name], {self.input_name: arr}
        )
        reconstruction = outputs[0][0]

        # Calculate reconstruction error
        original = arr[0]
        errors = (original - reconstruction) ** 2
        mse = float(np.mean(errors))

        # Determine anomaly status
        is_anomaly = mse > self.threshold

        # Per-sensor contributions (for explainability)
        total_error = float(np.sum(errors))
        sensor_contributions = []
        for i in range(self.input_size):
            contribution_pct = (errors[i] / total_error * 100) if total_error > 0 else 0
            sensor_contributions.append({
                "sensor_index": i,
                "original_value": float(original[i]),
                "reconstructed_value": float(reconstruction[i]),
                "error": float(errors[i]),
                "contribution_pct": float(contribution_pct),
            })

        # Sort by contribution (most anomalous sensor first)
        sensor_contributions.sort(key=lambda x: x["error"], reverse=True)

        return {
            "anomaly_score": mse,
            "is_anomaly": is_anomaly,
            "threshold": self.threshold,
            "reconstruction": reconstruction.tolist(),
            "sensor_contributions": sensor_contributions,
            "top_sensor": sensor_contributions[0] if sensor_contributions else None,
        }

    def predict_batch(self, input_vectors: List[List[float]]) -> List[Dict[str, Any]]:
        """Run inference on a batch of sensor vectors.

        Args:
            input_vectors: List of sensor vectors

        Returns:
            List of prediction dicts
        """
        if not input_vectors:
            return []

        batch = np.array(input_vectors, dtype=np.float32)
        if batch.ndim == 1:
            batch = batch.reshape(1, -1)

        if batch.shape[1] != self.input_size:
            raise ValueError(
                f"Expected input size {self.input_size}, got {batch.shape[1]}"
            )

        outputs = self.session.run(
            [self.output_name], {self.input_name: batch}
        )
        reconstructions = outputs[0]

        results = []
        for i in range(len(input_vectors)):
            original = batch[i]
            reconstruction = reconstructions[i]
            errors = (original - reconstruction) ** 2
            mse = float(np.mean(errors))
            is_anomaly = mse > self.threshold

            results.append({
                "anomaly_score": mse,
                "is_anomaly": is_anomaly,
                "threshold": self.threshold,
                "reconstruction": reconstruction.tolist(),
            })

        return results

    def explain(self, input_vector: List[float]) -> Dict[str, Any]:
        """Get anomaly explanation with per-sensor contributions.

        Args:
            input_vector: Sensor readings vector

        Returns:
            Dict with explanation details including the top contributing sensors
        """
        result = self.predict(input_vector)
        return {
            "anomaly_score": result["anomaly_score"],
            "is_anomaly": result["is_anomaly"],
            "threshold": self.threshold,
            "top_contributors": result["sensor_contributions"][:5],
            "all_contributors": result["sensor_contributions"],
        }

    def update_threshold(self, new_threshold: float):
        """Update the anomaly detection threshold."""
        old = self.threshold
        self.threshold = new_threshold
        logger.info(f"Threshold updated: {old:.4f} -> {new_threshold:.4f}")


# ─── CLI Usage ───────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    parser = argparse.ArgumentParser(description="AMOS ONNX Inference Runner")
    parser.add_argument("--model", type=str, default="../models/anomaly.onnx",
                        help="Path to ONNX model")
    parser.add_argument("--input", type=str, nargs="+", required=True,
                        help="Sensor values (space-separated floats)")
    parser.add_argument("--threshold", type=float, default=0.05,
                        help="Anomaly threshold")
    parser.add_argument("--explain", action="store_true",
                        help="Show per-sensor explanation")

    args = parser.parse_args()

    detector = AnomalyDetector(
        model_path=args.model,
        threshold=args.threshold,
    )

    input_data = [float(x) for x in args.input]

    if args.explain:
        result = detector.explain(input_data)
    else:
        result = detector.predict(input_data)

    print(json.dumps(result, indent=2))