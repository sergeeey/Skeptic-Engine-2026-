"""H25 MVP — Banking Fraud Autoencoder for Proteomics Data Integrity.

Transfer: LSTM/Dense autoencoder reconstruction error (from banking fraud detection)
applied to proteomics expression data to detect fabricated samples.

Uses Bradshaw 2021 CPTAC data (CNA + proteomics) with three fabrication methods:
  - Random: random values from fitted distributions
  - Imputation: fill missing with imputed values
  - Distribution: sample from per-gene distributions

Compares autoencoder reconstruction error vs Bradshaw's Benford+RF baseline.

Usage:
    python experiments/h25_banking_ae_lcms/run_h25.py
"""

from __future__ import annotations

import gzip
import io
import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, average_precision_score, f1_score, precision_recall_curve
from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.preprocessing import StandardScaler

DATA_DIR = Path(__file__).resolve().parent / "data"
RESULTS_DIR = Path(__file__).resolve().parent / "results"

BRADSHAW_BASE = "https://raw.githubusercontent.com/MSBradshaw/FakeData/master"


def _download_gz(url: str, dest: Path) -> None:
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  Downloading {dest.name}...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        with open(dest, "wb") as f:
            f.write(resp.read())


def _load_cct_gz(path: Path) -> pd.DataFrame:
    """Load Bradshaw .cct.gz format (tab-separated, genes as rows, samples as columns)."""
    with gzip.open(path, "rt") as f:
        df = pd.read_csv(f, sep="\t", index_col=0)
    return df.T  # Transpose to samples × genes


def _download_bradshaw_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Download CNA and proteomics data from Bradshaw GitHub."""
    cna_path = DATA_DIR / "bradshaw" / "CNA.cct.gz"
    prot_path = DATA_DIR / "bradshaw" / "proteomics.cct.gz"

    _download_gz(f"{BRADSHAW_BASE}/Data/Data-Original/CNA.cct.gz", cna_path)
    _download_gz(f"{BRADSHAW_BASE}/Data/Data-Original/proteomics.cct.gz", prot_path)

    cna = _load_cct_gz(cna_path)
    prot = _load_cct_gz(prot_path)
    return cna, prot


# ── Fabrication methods ──────────────────────────────────────────


def fabricate_random(real: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Per-feature random from fitted normal."""
    fake = np.zeros_like(real)
    for j in range(real.shape[1]):
        col = real[:, j]
        valid = col[~np.isnan(col)]
        if len(valid) > 1:
            fake[:, j] = rng.normal(valid.mean(), valid.std(), size=real.shape[0])
        else:
            fake[:, j] = rng.normal(0, 1, size=real.shape[0])
    return fake


def fabricate_shuffle(real: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Per-feature shuffle (like H24 resample)."""
    fake = real.copy()
    for j in range(fake.shape[1]):
        rng.shuffle(fake[:, j])
    return fake


def fabricate_noise(real: np.ndarray, rng: np.random.Generator, scale: float = 0.1) -> np.ndarray:
    """Additive Gaussian noise."""
    noise = rng.normal(0, scale * np.nanstd(real, axis=0, keepdims=True), size=real.shape)
    return real + noise


# ── Dense Autoencoder ────────────────────────────────────────────


class DenseAutoencoder(nn.Module):
    def __init__(self, input_dim: int, latent_dim: int = 64) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, latent_dim),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, input_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.encoder(x))


def train_autoencoder(
    X_real: np.ndarray,
    epochs: int = 100,
    lr: float = 1e-3,
    batch_size: int = 32,
    latent_dim: int = 64,
) -> DenseAutoencoder:
    """Train dense autoencoder on real data only."""
    model = DenseAutoencoder(X_real.shape[1], latent_dim)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    X_tensor = torch.tensor(X_real, dtype=torch.float32)
    dataset = torch.utils.data.TensorDataset(X_tensor, X_tensor)
    loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)

    model.train()
    for epoch in range(epochs):
        total_loss = 0.0
        for batch_x, _ in loader:
            optimizer.zero_grad()
            recon = model(batch_x)
            loss = criterion(recon, batch_x)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

    model.eval()
    return model


def reconstruction_error(model: DenseAutoencoder, X: np.ndarray) -> np.ndarray:
    """Compute per-sample MSE reconstruction error."""
    with torch.no_grad():
        X_tensor = torch.tensor(X, dtype=torch.float32)
        recon = model(X_tensor)
        mse = ((X_tensor - recon) ** 2).mean(dim=1).numpy()
    return mse


# ── Benford baseline (from H24) ─────────────────────────────────


def digit_features_continuous(X: np.ndarray) -> np.ndarray:
    """Extract first-digit frequencies from continuous data (take absolute value, ignore near-zero)."""
    n_samples = X.shape[0]
    features = np.zeros((n_samples, 9), dtype=np.float64)
    for i in range(n_samples):
        row = np.abs(X[i])
        valid = row[row > 0.001]  # Skip near-zero
        if len(valid) == 0:
            continue
        # Extract first significant digit
        digits = np.floor(valid / (10 ** np.floor(np.log10(valid)))).astype(int)
        digits = np.clip(digits, 1, 9)
        for d in range(1, 10):
            features[i, d - 1] = (digits == d).sum()
        total = features[i].sum()
        if total > 0:
            features[i] /= total
    return features


# ── Main experiment ──────────────────────────────────────────────


def _evaluate(y_true: np.ndarray, y_score: np.ndarray) -> dict:
    auc = roc_auc_score(y_true, y_score)
    ap = average_precision_score(y_true, y_score)
    # WHY: derive optimal threshold from precision-recall curve instead of using
    # np.median which guarantees ~50% positive rate and makes F1 incomparable.
    precision, recall, thresholds = precision_recall_curve(y_true, y_score)
    f1_scores = 2 * precision[:-1] * recall[:-1] / np.maximum(precision[:-1] + recall[:-1], 1e-10)
    best_threshold = thresholds[np.argmax(f1_scores)] if len(thresholds) > 0 else np.median(y_score)
    y_pred = (y_score >= best_threshold).astype(int)
    f1 = f1_score(y_true, y_pred)
    return {"auc": round(auc, 4), "ap": round(ap, 4), "f1": round(f1, 4)}


def main() -> None:
    print("=" * 70)
    print("H25 MVP — Banking Fraud Autoencoder for Proteomics Integrity")
    print("=" * 70)
    t0 = time.time()

    # Load data
    print("\n[1/5] Downloading Bradshaw CPTAC data...")
    cna, prot = _download_bradshaw_data()
    print(f"  CNA: {cna.shape[0]} samples × {cna.shape[1]} genes")
    print(f"  Proteomics: {prot.shape[0]} samples × {prot.shape[1]} proteins")

    # Use proteomics (the novel target — CNA was Bradshaw's original)
    # Fill NaN with 0 for simplicity (real proteomics has missing values)
    prot_matrix = prot.values.astype(np.float64)
    nan_frac = np.isnan(prot_matrix).mean()
    print(f"  Proteomics NaN fraction: {nan_frac:.4f}")
    prot_matrix = np.nan_to_num(prot_matrix, nan=0.0)

    # Also prepare CNA for comparison with Bradshaw baseline
    cna_matrix = cna.values.astype(np.float64)
    cna_matrix = np.nan_to_num(cna_matrix, nan=0.0)

    all_results = []

    for data_name, real_matrix in [("proteomics", prot_matrix), ("CNA", cna_matrix)]:
        print(f"\n{'=' * 60}")
        print(f"[2/5] Dataset: {data_name} ({real_matrix.shape})")
        print(f"{'=' * 60}")

        # Normalize
        scaler = StandardScaler()
        real_scaled = scaler.fit_transform(real_matrix)

        # Train autoencoder on real data
        print("  Training autoencoder on real data...")
        ae = train_autoencoder(real_scaled, epochs=150, latent_dim=32)
        real_recon_error = reconstruction_error(ae, real_scaled)
        print(
            f"  Real reconstruction error: mean={real_recon_error.mean():.4f} std={real_recon_error.std():.4f}"
        )

        # Percentile threshold (banking style: 98th percentile)
        threshold_98 = np.percentile(real_recon_error, 98)
        print(f"  98th percentile threshold: {threshold_98:.4f}")

        for fab_name, fab_fn in [
            ("random", fabricate_random),
            ("shuffle", fabricate_shuffle),
            ("noise_10pct", lambda r, rng: fabricate_noise(r, rng, 0.10)),
        ]:
            print(f"\n  --- {fab_name} ---")
            rng = np.random.default_rng(2026)
            fake_matrix = fab_fn(real_matrix, rng)
            fake_scaled = scaler.transform(fake_matrix)
            fake_recon_error = reconstruction_error(ae, fake_scaled)
            print(
                f"    Fake recon error: mean={fake_recon_error.mean():.4f} std={fake_recon_error.std():.4f}"
            )

            # Method 1: AE reconstruction error as score
            y_true = np.concatenate(
                [np.zeros(len(real_recon_error)), np.ones(len(fake_recon_error))]
            )
            ae_scores = np.concatenate([real_recon_error, fake_recon_error])
            ae_metrics = _evaluate(y_true, ae_scores)
            print(f"    AE recon error AUC: {ae_metrics['auc']:.4f}")

            # Method 2: Benford digits on raw data
            real_digits = digit_features_continuous(real_matrix)
            fake_digits = digit_features_continuous(fake_matrix)
            X_digits = np.vstack([real_digits, fake_digits])
            y = y_true.copy()

            splitter = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
            train_idx, test_idx = next(splitter.split(X_digits, y))
            rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
            rf.fit(X_digits[train_idx], y[train_idx])
            benford_proba = rf.predict_proba(X_digits[test_idx])[:, 1]
            benford_auc = roc_auc_score(y[test_idx], benford_proba)
            print(f"    Benford RF AUC:     {benford_auc:.4f}")

            # Method 3: Fusion (AE error + Benford digits)
            X_fusion = np.hstack([X_digits, ae_scores.reshape(-1, 1)])
            rf_fus = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
            rf_fus.fit(X_fusion[train_idx], y[train_idx])
            fusion_proba = rf_fus.predict_proba(X_fusion[test_idx])[:, 1]
            fusion_auc = roc_auc_score(y[test_idx], fusion_proba)
            print(f"    Fusion AUC:         {fusion_auc:.4f}")

            # Fraction above 98th percentile
            frac_flagged = (fake_recon_error > threshold_98).mean()
            print(f"    Fake above 98th pct: {frac_flagged:.4f}")

            all_results.append(
                {
                    "dataset": data_name,
                    "fabrication": fab_name,
                    "ae_metrics": ae_metrics,
                    "benford_rf_auc": round(benford_auc, 4),
                    "fusion_auc": round(fusion_auc, 4),
                    "real_recon_mean": round(float(real_recon_error.mean()), 4),
                    "fake_recon_mean": round(float(fake_recon_error.mean()), 4),
                    "threshold_98": round(float(threshold_98), 4),
                    "frac_above_threshold": round(float(frac_flagged), 4),
                }
            )

    # Summary
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    print(
        f"{'Dataset':<14} {'Fabrication':<14} {'AE-AUC':>8} {'Benford':>8} {'Fusion':>8} {'%Flag':>8}"
    )
    print("-" * 64)
    for r in all_results:
        print(
            f"{r['dataset']:<14} {r['fabrication']:<14} "
            f"{r['ae_metrics']['auc']:>8.4f} {r['benford_rf_auc']:>8.4f} "
            f"{r['fusion_auc']:>8.4f} {r['frac_above_threshold']:>7.1%}"
        )

    elapsed = time.time() - t0
    print(f"\nTotal time: {elapsed:.1f}s")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "h25_results.json"
    out_path.write_text(
        json.dumps({"results": all_results, "elapsed_s": round(elapsed, 1)}, indent=2),
        encoding="utf-8",
    )
    print(f"Results saved: {out_path}")


if __name__ == "__main__":
    main()
