#!/usr/bin/env python3
"""
AMOS ONNX Model Exporter
Exports a trained PyTorch autoencoder checkpoint to ONNX format.

Usage:
    python export_onnx.py --checkpoint ../models/checkpoints/best_model.pt --output ../models/anomaly.onnx
"""

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("amos-onnx-exporter")


class Autoencoder(nn.Module):
    """Must match the training architecture."""

    def __init__(self, input_size: int, latent_dim: int):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_size, input_size * 2),
            nn.ReLU(),
            nn.Linear(input_size * 2, latent_dim * 2),
            nn.ReLU(),
            nn.Linear(latent_dim * 2, latent_dim),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, latent_dim * 2),
            nn.ReLU(),
            nn.Linear(latent_dim * 2, input_size * 2),
            nn.ReLU(),
            nn.Linear(input_size * 2, input_size),
            nn.Sigmoid(),
        )

    def forward(self, x):
        return self.decoder(self.encoder(x))


def load_checkpoint(checkpoint_path: str, device: str = "cpu") -> dict:
    """Load a training checkpoint."""
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
    logger.info(f"Checkpoint loaded from {checkpoint_path}")
    logger.info(f"  Epoch: {checkpoint.get('epoch', 'N/A')}")
    logger.info(f"  Val Loss: {checkpoint.get('val_loss', 'N/A'):.6f}")
    logger.info(f"  Input Size: {checkpoint.get('input_size', 'N/A')}")
    logger.info(f"  Latent Dim: {checkpoint.get('latent_dim', 'N/A')}")
    return checkpoint


def export_to_onnx(
    model: nn.Module,
    input_size: int,
    output_path: str,
    opset_version: int = 17,
):
    """Export PyTorch model to ONNX format."""
    model.eval()
    dummy_input = torch.randn(1, input_size, requires_grad=False)

    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        export_params=True,
        opset_version=opset_version,
        do_constant_folding=True,
        input_names=["sensor_input"],
        output_names=["reconstructed"],
        dynamic_axes={
            "sensor_input": {0: "batch_size"},
            "reconstructed": {0: "batch_size"},
        },
    )
    logger.info(f"ONNX model exported to {output_path}")
    return output_path


def validate_onnx(onnx_path: str, input_size: int):
    """Validate ONNX model by running a sample inference."""
    try:
        import onnxruntime as ort
    except ImportError:
        logger.warning("onnxruntime not installed, skipping validation")
        return True

    # Create inference session
    session = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name

    # Run sample inference
    dummy = np.random.randn(1, input_size).astype(np.float32)
    outputs = session.run([output_name], {input_name: dummy})
    output = outputs[0]

    # Verify output shape
    assert output.shape == (1, input_size), (
        f"Expected shape (1, {input_size}), got {output.shape}"
    )
    logger.info(f"ONNX validation passed: output shape {output.shape}")
    logger.info(f"  Sample output range: [{output.min():.4f}, {output.max():.4f}]")

    # Also verify with batch size 4
    batch_dummy = np.random.randn(4, input_size).astype(np.float32)
    batch_outputs = session.run([output_name], {input_name: batch_dummy})
    assert batch_outputs[0].shape == (4, input_size), (
        f"Batch validation failed: expected (4, {input_size}), got {batch_outputs[0].shape}"
    )
    logger.info(f"Batch inference validated: shape {batch_outputs[0].shape}")

    return True


def main():
    parser = argparse.ArgumentParser(description="AMOS ONNX Model Exporter")
    parser.add_argument(
        "--checkpoint", type=str,
        default="../models/checkpoints/best_model.pt",
        help="Path to PyTorch checkpoint",
    )
    parser.add_argument(
        "--output", type=str,
        default="../models/anomaly.onnx",
        help="Output ONNX model path",
    )
    parser.add_argument(
        "--input-size", type=int, default=None,
        help="Override input size (default: from checkpoint)",
    )
    parser.add_argument(
        "--latent-dim", type=int, default=None,
        help="Override latent dim (default: from checkpoint)",
    )
    parser.add_argument("--validate", action="store_true", default=True,
                        help="Validate ONNX model after export")
    parser.add_argument("--device", type=str, default="cpu")

    args = parser.parse_args()

    # Resolve paths relative to script location
    script_dir = Path(__file__).parent
    checkpoint_path = Path(args.checkpoint)
    if not checkpoint_path.is_absolute():
        checkpoint_path = script_dir / checkpoint_path
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = script_dir / output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load checkpoint
    checkpoint = load_checkpoint(str(checkpoint_path), device=args.device)

    input_size = args.input_size or checkpoint.get("input_size", 16)
    latent_dim = args.latent_dim or checkpoint.get("latent_dim", 4)

    # Build model
    model = Autoencoder(input_size=input_size, latent_dim=latent_dim)
    model.load_state_dict(checkpoint["model_state_dict"])
    logger.info("Model architecture loaded from checkpoint")

    # Export
    export_to_onnx(model, input_size, str(output_path))

    # Validate
    if args.validate:
        validate_onnx(str(output_path), input_size)

    logger.info("Export complete! Ready for edge deployment.")
    return str(output_path)


if __name__ == "__main__":
    main()