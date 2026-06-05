"""
H25 Autoencoder — Credit Card Fraud Detection (Real Data)

Adapts H25 experiment from proteomics to credit card transactions.
Tests Autoencoder reconstruction error on REAL fraud labels.

Dataset: MLG-ULB Credit Card Fraud (284,807 transactions, 492 fraud)
Goal: Compare AUC on real fraud vs H25's synthetic fabrication (AUC 1.000).

Architecture:
    - Train AE on NORMAL transactions (Class=0)
    - Test reconstruction error on ALL transactions
    - High error → fraud prediction

Usage:
    python experiments/validation/golden_set/run_h25_creditcard.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# ── Autoencoder Architecture ──────────────────────────────────────


class SimpleAutoencoder(nn.Module):
    """
    Simple dense autoencoder for credit card transactions.

    Architecture: input → encoder → bottleneck → decoder → reconstruction
    """

    def __init__(self, input_dim: int, bottleneck_dim: int = 10):
        super().__init__()
        hidden_dim = max(input_dim // 2, bottleneck_dim * 2)

        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, bottleneck_dim),
            nn.ReLU(),
        )

        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(bottleneck_dim, hidden_dim), nn.ReLU(), nn.Linear(hidden_dim, input_dim)
        )

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded


def train_autoencoder(X_train: np.ndarray, epochs: int = 50, lr: float = 0.001):
    """
    Train autoencoder on normal transactions.

    Args:
        X_train: Normal transactions (Class=0 only)
        epochs: Training epochs
        lr: Learning rate

    Returns:
        model: Trained autoencoder
        scaler: StandardScaler for preprocessing
    """
    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train)

    # Convert to tensor
    X_tensor = torch.FloatTensor(X_scaled)

    # Initialize model
    input_dim = X_train.shape[1]
    model = SimpleAutoencoder(input_dim, bottleneck_dim=10)

    # Loss and optimizer
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    # Training loop
    model.train()
    print(f"[TRAINING] Autoencoder on {len(X_train):,} normal transactions...")

    for epoch in range(epochs):
        # Forward pass
        reconstructed = model(X_tensor)
        loss = criterion(reconstructed, X_tensor)

        # Backward pass
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if (epoch + 1) % 10 == 0:
            print(f"  Epoch {epoch+1}/{epochs}, Loss: {loss.item():.6f}")

    return model, scaler


def compute_reconstruction_errors(model, X: np.ndarray, scaler):
    """
    Compute reconstruction error for each transaction.

    Args:
        model: Trained autoencoder
        X: Transactions to test
        scaler: Fitted StandardScaler

    Returns:
        errors: Per-sample reconstruction error (MSE)
    """
    model.eval()

    # Standardize
    X_scaled = scaler.transform(X)
    X_tensor = torch.FloatTensor(X_scaled)

    # Reconstruct
    with torch.no_grad():
        reconstructed = model(X_tensor)

    # Compute MSE per sample
    errors = torch.mean((X_tensor - reconstructed) ** 2, dim=1).numpy()

    return errors


# ── Main Experiment ───────────────────────────────────────────────


def load_creditcard_data(csv_path: Path | None = None):
    """Load MLG-ULB credit card fraud dataset."""
    if csv_path is None:
        csv_path = Path(__file__).parent / "creditcard_fraud_dataset.csv"

    if not csv_path.exists():
        print(f"[ERROR] Dataset not found: {csv_path}")
        print("[ACTION] Run load_real_fraud_data.py first.")
        sys.exit(1)

    df = pd.read_csv(csv_path)
    print(f"[INFO] Loaded {len(df):,} transactions")
    print(f"[INFO] Fraud: {df['Class'].sum():,} ({df['Class'].mean()*100:.3f}%)")

    return df


def run_h25_creditcard_experiment():
    """
    Main experiment: H25 Autoencoder on real credit card fraud.

    Steps:
        1. Load MLG-ULB dataset
        2. Split: train on NORMAL only, test on ALL
        3. Train autoencoder on normal transactions
        4. Compute reconstruction errors for test set
        5. Evaluate: high error = fraud prediction
        6. Compare to H25 synthetic AUC (1.000)
    """
    print("=" * 60)
    print("H25 Autoencoder — Credit Card Fraud (Real Data)")
    print("=" * 60)

    # Load data
    df = load_creditcard_data()

    # Features: V1-V28 (PCA-transformed) + Amount
    # Note: Time is excluded (sequential, not useful for AE)
    feature_cols = [f"V{i}" for i in range(1, 29)] + ["Amount"]
    X = df[feature_cols].values
    y = df["Class"].values

    print(f"[INFO] Features: {X.shape[1]} columns")

    # Split data: 70% train, 30% test
    X_train_all, X_test, y_train_all, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    # Train set: ONLY normal transactions (Class=0)
    X_train_normal = X_train_all[y_train_all == 0]

    print(f"[INFO] Train (normal only): {len(X_train_normal):,}")
    print(f"[INFO] Test (all): {len(X_test):,} ({y_test.sum()} fraud)")

    # Train autoencoder
    model, scaler = train_autoencoder(X_train_normal, epochs=50, lr=0.001)

    # Compute reconstruction errors on test set
    print("\n[INFERENCE] Computing reconstruction errors on test set...")
    errors_test = compute_reconstruction_errors(model, X_test, scaler)

    # Fraud detection: high reconstruction error → fraud
    # (Normal transactions should have low error, fraud should have high)

    # Evaluate
    auc = roc_auc_score(y_test, errors_test)
    ap = average_precision_score(y_test, errors_test)

    print("\n[RESULTS] Autoencoder:")
    print(f"  AUC-ROC: {auc:.4f}")
    print(f"  AP: {ap:.4f}")

    # Compare to H25 synthetic
    print("\n" + "=" * 60)
    print("COMPARISON: Real Fraud vs H25 Synthetic Fabrication")
    print("=" * 60)
    print("H25 (proteomics synthetic fabrication): AUC 1.000")
    print(f"H25 (credit card REAL fraud):           AUC {auc:.3f}")
    print(f"\nDelta: {auc - 1.000:.3f}")

    # Verdict
    if auc < 0.65:
        verdict = "⚠️  [FAIL] AUC < 0.65 — Autoencoder ineffective on real fraud"
    elif auc < 0.80:
        verdict = "⚠️  [WEAK] AUC < 0.80 — Autoencoder works but not strong"
    else:
        verdict = "✅ [PASS] AUC ≥ 0.80 — Autoencoder effective on real fraud"

    print(f"\n{verdict}")

    # Save results
    results = {
        "Autoencoder": {
            "auc_roc": float(auc),
            "average_precision": float(ap),
        }
    }

    output_path = Path(__file__).parent / "h25_creditcard_real_fraud_results.json"
    output_path.write_text(json.dumps(results, indent=2))

    print(f"\n[SAVED] Results: {output_path}")

    return results


if __name__ == "__main__":
    run_h25_creditcard_experiment()
