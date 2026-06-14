#!/usr/bin/env python3
"""
AMOS Autoencoder Training Pipeline
Trains a deep autoencoder for anomaly detection on industrial sensor data.

Usage:
    python train_autoencoder.py --epochs 100 --input-size 16 --latent-dim 4
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score
from torch.utils.data import DataLoader, TensorDataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("amos-trainer")

# ─── Autoencoder Model ──────────────────────────────────────

class Autoencoder(nn.Module):
    """Deep autoencoder for anomaly detection on sensor time-series."""

    def __init__(self, input_size: int = 16, latent_dim: int = 4):
        super().__init__()
        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_size, input_size * 2),
            nn.ReLU(),
            nn.Linear(input_size * 2, latent_dim * 2),
            nn.ReLU(),
            nn.Linear(latent_dim * 2, latent_dim),
            nn.ReLU(),
        )
        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, latent_dim * 2),
            nn.ReLU(),
            nn.Linear(latent_dim * 2, input_size * 2),
            nn.ReLU(),
            nn.Linear(input_size * 2, input_size),
            nn.Sigmoid(),
        )

    def forward(self, x):
        z = self.encoder(x)
        recon = self.decoder(z)
        return recon

    def get_latent(self, x):
        """Extract latent representation."""
        return self.encoder(x)


# ─── Synthetic Data Generator ───────────────────────────────

def generate_normal_data(num_samples: int = 10000, input_size: int = 16, noise_level: float = 0.05):
    """Generate synthetic 'normal' industrial sensor data.

    Creates sinusoidal patterns with noise to simulate healthy machine operation.
    Each sample represents a time window of sensor readings.
    """
    t = np.linspace(0, 4 * np.pi, input_size)
    data = []
    for _ in range(num_samples):
        # Base sinusoidal signal with random phase shift
        phase = np.random.uniform(0, 2 * np.pi)
        amplitude = np.random.uniform(0.8, 1.2)
        base = amplitude * np.sin(t + phase)
        # Add harmonics
        harm = 0.3 * np.sin(2 * t + phase * 1.5)
        # Add low-frequency drift
        drift = 0.1 * np.random.randn()
        # Add Gaussian noise
        noise = noise_level * np.random.randn(input_size)
        sample = base + harm + drift + noise
        # Normalize to [0, 1]
        sample = (sample - sample.min()) / (sample.max() - sample.min() + 1e-8)
        data.append(sample)

    return np.array(data, dtype=np.float32)


def generate_anomaly_data(num_samples: int = 2000, input_size: int = 16):
    """Generate synthetic anomalous data.

    Anomalies include:
    - Spike anomalies: sudden sharp deviations
    - Drift anomalies: gradual offset from normal
    - Noise burst: high-frequency noise injection
    """
    t = np.linspace(0, 4 * np.pi, input_size)
    data = []
    labels = []

    for i in range(num_samples):
        base = 0.5 + 0.3 * np.sin(t + np.random.uniform(0, 2 * np.pi))

        anomaly_type = i % 3
        if anomaly_type == 0:
            # Spike anomaly
            spike_pos = np.random.randint(0, input_size)
            spike_mag = np.random.uniform(2.0, 5.0)
            base[spike_pos] += spike_mag
            label = 1
        elif anomaly_type == 1:
            # Drift anomaly
            drift = np.linspace(0, np.random.uniform(0.5, 1.5), input_size)
            base += drift
            label = 1
        else:
            # Noise burst
            burst = np.random.uniform(-0.5, 0.5, input_size) * 3
            base += burst
            label = 1

        # Normalize
        sample = (base - base.min()) / (base.max() - base.min() + 1e-8)
        data.append(sample)
        labels.append(label)

    return np.array(data, dtype=np.float32), np.array(labels)


# ─── Training Function ──────────────────────────────────────

def train_autoencoder(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    epochs: int = 100,
    lr: float = 1e-3,
    patience: int = 10,
    device: str = "cpu",
    checkpoint_dir: str = "checkpoints",
) -> dict:
    """Train autoencoder with early stopping and checkpointing."""
    device = torch.device(device)
    model = model.to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

    os.makedirs(checkpoint_dir, exist_ok=True)

    best_val_loss = float("inf")
    patience_counter = 0
    history = {"train_loss": [], "val_loss": []}

    for epoch in range(1, epochs + 1):
        # Training
        model.train()
        train_loss = 0.0
        for batch in train_loader:
            x = batch[0].to(device)
            recon = model(x)
            loss = criterion(recon, x)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * x.size(0)

        train_loss /= len(train_loader.dataset)

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for batch in val_loader:
                x = batch[0].to(device)
                recon = model(x)
                loss = criterion(recon, x)
                val_loss += loss.item() * x.size(0)

        val_loss /= len(val_loader.dataset)
        scheduler.step(val_loss)

        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)

        logger.info(
            f"Epoch {epoch:3d}/{epochs} | "
            f"Train Loss: {train_loss:.6f} | "
            f"Val Loss: {val_loss:.6f} | "
            f"LR: {optimizer.param_groups[0]['lr']:.2e}"
        )

        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            # Save best model
            checkpoint_path = os.path.join(checkpoint_dir, "best_model.pt")
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_loss": val_loss,
                "input_size": model.encoder[0].in_features,
                "latent_dim": model.encoder[4].out_features,
            }, checkpoint_path)
            logger.info(f"  -> New best model saved (val_loss={val_loss:.6f})")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info(f"Early stopping triggered at epoch {epoch}")
                break

    return history


# ─── Evaluation ──────────────────────────────────────────────

def evaluate_model(
    model: nn.Module,
    normal_data: np.ndarray,
    anomaly_data: np.ndarray,
    anomaly_labels: np.ndarray,
    device: str = "cpu",
):
    """Evaluate autoencoder performance using reconstruction error as anomaly score."""
    device = torch.device(device)
    model = model.to(device)
    model.eval()

    criterion = nn.MSELoss(reduction="none")
    all_scores = []
    all_labels = []

    with torch.no_grad():
        # Normal data (label=0)
        for i in range(0, len(normal_data), 64):
            batch = torch.tensor(normal_data[i:i+64]).to(device)
            recon = model(batch)
            mse = criterion(recon, batch).mean(dim=1).cpu().numpy()
            all_scores.extend(mse.tolist())
            all_labels.extend([0] * len(mse))

        # Anomaly data (label=1)
        for i in range(0, len(anomaly_data), 64):
            batch = torch.tensor(anomaly_data[i:i+64]).to(device)
            recon = model(batch)
            mse = criterion(recon, batch).mean(dim=1).cpu().numpy()
            all_scores.extend(mse.tolist())
            all_labels.extend(anomaly_labels[i:i+64].tolist())

    scores = np.array(all_scores)
    labels = np.array(all_labels)

    # Find optimal threshold using ROC curve
    roc_auc = roc_auc_score(labels, scores)

    # Determine threshold at 95% recall
    thresholds = np.linspace(scores.min(), scores.max(), 100)
    best_f1 = 0
    best_threshold = 0.05

    for threshold in thresholds:
        preds = (scores > threshold).astype(int)
        f1 = f1_score(labels, preds, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold

    preds = (scores > best_threshold).astype(int)
    precision = precision_score(labels, preds, zero_division=0)
    recall = recall_score(labels, preds, zero_division=0)

    logger.info("=" * 60)
    logger.info("Model Evaluation Results")
    logger.info(f"  ROC-AUC:          {roc_auc:.4f}")
    logger.info(f"  Optimal Threshold: {best_threshold:.6f}")
    logger.info(f"  F1 Score:          {best_f1:.4f}")
    logger.info(f"  Precision:         {precision:.4f}")
    logger.info(f"  Recall:            {recall:.4f}")
    logger.info("=" * 60)

    return {
        "roc_auc": float(roc_auc),
        "optimal_threshold": float(best_threshold),
        "f1_score": float(best_f1),
        "precision": float(precision),
        "recall": float(recall),
    }


# ─── Main ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AMOS Autoencoder Training")
    parser.add_argument("--epochs", type=int, default=100, help="Number of training epochs")
    parser.add_argument("--input-size", type=int, default=16, help="Input vector size")
    parser.add_argument("--latent-dim", type=int, default=4, help="Latent space dimension")
    parser.add_argument("--batch-size", type=int, default=64, help="Training batch size")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument("--device", type=str, default="cpu", help="Training device (cpu/cuda)")
    parser.add_argument("--checkpoint-dir", type=str, default="checkpoints", help="Checkpoint directory")
    parser.add_argument("--output-dir", type=str, default="../models", help="Output directory for trained model")
    args = parser.parse_args()

    model_dir = Path(args.output_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir = model_dir / "checkpoints"
    checkpoint_dir.mkdir(exist_ok=True)

    logger.info("Generating synthetic training data...")
    # Generate normal data
    normal_data = generate_normal_data(num_samples=10000, input_size=args.input_size)
    anomaly_data, anomaly_labels = generate_anomaly_data(num_samples=2000, input_size=args.input_size)

    # Split normal data for train/val
    split = int(0.8 * len(normal_data))
    train_data = normal_data[:split]
    val_data = normal_data[split:]

    train_dataset = TensorDataset(torch.tensor(train_data))
    val_dataset = TensorDataset(torch.tensor(val_data))
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size)

    logger.info(f"Train samples: {len(train_data)}, Val samples: {len(val_data)}")
    logger.info(f"Anomaly test samples: {len(anomaly_data)}")

    # Build model
    model = Autoencoder(input_size=args.input_size, latent_dim=args.latent_dim)
    logger.info(f"Model: {model}")
    logger.info(f"Parameters: {sum(p.numel() for p in model.parameters()):,}")

    # Train
    history = train_autoencoder(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        epochs=args.epochs,
        lr=args.lr,
        patience=10,
        device=args.device,
        checkpoint_dir=str(checkpoint_dir),
    )

    # Load best model for evaluation
    best_checkpoint = checkpoint_dir / "best_model.pt"
    if best_checkpoint.exists():
        checkpoint = torch.load(best_checkpoint, map_location=args.device)
        model.load_state_dict(checkpoint["model_state_dict"])
        logger.info(f"Loaded best model from epoch {checkpoint['epoch']}")

    # Evaluate
    eval_results = evaluate_model(
        model=model,
        normal_data=normal_data,
        anomaly_data=anomaly_data,
        anomaly_labels=anomaly_labels,
        device=args.device,
    )

    # Save final model
    final_path = model_dir / "autoencoder_model.pt"
    torch.save({
        "model_state_dict": model.state_dict(),
        "input_size": args.input_size,
        "latent_dim": args.latent_dim,
        "eval_results": eval_results,
    }, final_path)
    logger.info(f"Final model saved to {final_path}")

    # Export to ONNX
    try:
        export_onnx(model, args.input_size, str(model_dir / "anomaly.onnx"))
        logger.info(f"ONNX model saved to {model_dir / 'anomaly.onnx'}")
    except Exception as e:
        logger.warning(f"ONNX export failed: {e}")

    return eval_results


def export_onnx(model: nn.Module, input_size: int, output_path: str):
    """Export PyTorch model to ONNX format."""
    model.eval()
    dummy_input = torch.randn(1, input_size)
    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        export_params=True,
        opset_version=17,
        do_constant_folding=True,
        input_names=["sensor_input"],
        output_names=["reconstructed"],
        dynamic_axes={
            "sensor_input": {0: "batch_size"},
            "reconstructed": {0: "batch_size"},
        },
    )
    logger.info(f"Exported ONNX model to {output_path}")


if __name__ == "__main__":
    results = main()
    logger.info(f"Training complete. ROC-AUC: {results['roc_auc']:.4f}")