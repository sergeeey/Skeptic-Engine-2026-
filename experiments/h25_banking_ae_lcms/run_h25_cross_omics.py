"""H25 Cross-Omics — Train on CNA → Test on Proteomics (and vice versa).

Key question: does the autoencoder artifact signal transfer across omics types
without retraining? If yes, this defeats the "overfitting on HDSS" argument.

Usage:
    python experiments/h25_banking_ae_lcms/run_h25_cross_omics.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "h24_benford_scrna"))

from run_h25 import (
    _download_bradshaw_data,
    digit_features_continuous,
    fabricate_random,
    fabricate_shuffle,
    fabricate_noise,
    train_autoencoder,
    reconstruction_error,
)

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def _extract_all(matrix: np.ndarray, ae_model, scaler) -> np.ndarray:
    """Benford digits + AE reconstruction error."""
    digits = digit_features_continuous(matrix)
    scaled = scaler.transform(matrix)
    recon = reconstruction_error(ae_model, scaled).reshape(-1, 1)
    return np.hstack([digits, recon])


def main() -> None:
    print("=" * 70)
    print("H25 Cross-Omics — CNA ↔ Proteomics Transfer")
    print("=" * 70)
    t0 = time.time()

    # Load data
    print("\n[1/3] Loading Bradshaw CPTAC data...")
    cna_df, prot_df = _download_bradshaw_data()
    cna = np.nan_to_num(cna_df.values.astype(np.float64), nan=0.0)
    prot = np.nan_to_num(prot_df.values.astype(np.float64), nan=0.0)
    print(f"  CNA: {cna.shape}")
    print(f"  Proteomics: {prot.shape}")

    fabs = {
        "random": fabricate_random,
        "shuffle": fabricate_shuffle,
        "noise_10pct": lambda r, rng: fabricate_noise(r, rng, 0.10),
    }

    all_results = []

    for fab_name, fab_fn in fabs.items():
        print(f"\n{'=' * 50}")
        print(f"Fabrication: {fab_name}")
        print(f"{'=' * 50}")

        rng = np.random.default_rng(2026)

        # Train AE on CNA real
        scaler_cna = StandardScaler()
        cna_scaled = scaler_cna.fit_transform(cna)
        ae_cna = train_autoencoder(cna_scaled, epochs=150, latent_dim=32)

        # Train AE on Proteomics real
        scaler_prot = StandardScaler()
        prot_scaled = scaler_prot.fit_transform(prot)
        ae_prot = train_autoencoder(prot_scaled, epochs=150, latent_dim=32)

        # Generate fakes
        cna_fake = fab_fn(cna, np.random.default_rng(2026))
        prot_fake = fab_fn(prot, np.random.default_rng(2026))

        # ── Within CNA ──
        cna_real_feat = _extract_all(cna, ae_cna, scaler_cna)
        cna_fake_feat = _extract_all(cna_fake, ae_cna, scaler_cna)
        X_cna = np.vstack([cna_real_feat, cna_fake_feat])
        y_cna = np.concatenate([np.zeros(len(cna)), np.ones(len(cna))])

        # WHY: use held-out split for within-dataset eval to avoid train-AUC inflation
        splitter = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)

        rf_cna = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        train_idx, test_idx = next(splitter.split(X_cna, y_cna))
        rf_cna.fit(X_cna[train_idx], y_cna[train_idx])
        within_cna = roc_auc_score(y_cna[test_idx], rf_cna.predict_proba(X_cna[test_idx])[:, 1])
        print(f"  Within CNA:        AUC={within_cna:.4f}")

        # ── Within Proteomics ──
        prot_real_feat = _extract_all(prot, ae_prot, scaler_prot)
        prot_fake_feat = _extract_all(prot_fake, ae_prot, scaler_prot)
        X_prot = np.vstack([prot_real_feat, prot_fake_feat])
        y_prot = np.concatenate([np.zeros(len(prot)), np.ones(len(prot))])

        rf_prot = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        train_idx, test_idx = next(splitter.split(X_prot, y_prot))
        rf_prot.fit(X_prot[train_idx], y_prot[train_idx])
        within_prot = roc_auc_score(y_prot[test_idx], rf_prot.predict_proba(X_prot[test_idx])[:, 1])
        print(f"  Within Proteomics: AUC={within_prot:.4f}")

        # ── Cross-omics: CNA-trained → Proteomics test ──
        # Use CNA AE + CNA scaler on proteomics data (feature dimensions differ!)
        # Only Benford features (9) are comparable — AE features are not transferable
        cna_real_benford = digit_features_continuous(cna)
        cna_fake_benford = digit_features_continuous(cna_fake)
        prot_real_benford = digit_features_continuous(prot)
        prot_fake_benford = digit_features_continuous(prot_fake)

        X_cna_ben = np.vstack([cna_real_benford, cna_fake_benford])
        X_prot_ben = np.vstack([prot_real_benford, prot_fake_benford])

        rf_cna_ben = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        rf_cna_ben.fit(X_cna_ben, y_cna)
        cross_c2p = roc_auc_score(y_prot, rf_cna_ben.predict_proba(X_prot_ben)[:, 1])
        print(f"  CNA → Proteomics (Benford only): AUC={cross_c2p:.4f}  ← CROSS-OMICS")

        rf_prot_ben = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        rf_prot_ben.fit(X_prot_ben, y_prot)
        cross_p2c = roc_auc_score(y_cna, rf_prot_ben.predict_proba(X_cna_ben)[:, 1])
        print(f"  Proteomics → CNA (Benford only): AUC={cross_p2c:.4f}  ← CROSS-OMICS")

        all_results.append(
            {
                "method": fab_name,
                "within_cna": round(within_cna, 4),
                "within_prot": round(within_prot, 4),
                "cross_cna_to_prot": round(cross_c2p, 4),
                "cross_prot_to_cna": round(cross_p2c, 4),
            }
        )

    # Summary
    print(f"\n{'=' * 70}")
    print("CROSS-OMICS SUMMARY (RF AUC)")
    print(f"{'=' * 70}")
    print(f"{'Method':<14} {'W-CNA':>8} {'W-Prot':>8} {'C→P':>8} {'P→C':>8}")
    print("-" * 50)
    for r in all_results:
        print(
            f"{r['method']:<14} {r['within_cna']:>8.4f} {r['within_prot']:>8.4f} "
            f"{r['cross_cna_to_prot']:>8.4f} {r['cross_prot_to_cna']:>8.4f}"
        )

    cross_aucs = []
    for r in all_results:
        cross_aucs.extend([r["cross_cna_to_prot"], r["cross_prot_to_cna"]])

    min_cross = min(cross_aucs)
    mean_cross = np.mean(cross_aucs)

    if min_cross >= 0.80:
        verdict = (
            "CROSS-OMICS GENERALIZES — Benford artifact signal transfers between CNA and proteomics"
        )
    elif mean_cross >= 0.70:
        verdict = "PARTIAL — some artifact types transfer across omics"
    else:
        verdict = "NO CROSS-OMICS GENERALIZATION — Benford signal is omics-specific"

    print(f"\nMin cross-omics AUC: {min_cross:.4f}")
    print(f"Mean cross-omics AUC: {mean_cross:.4f}")
    print(f"VERDICT: {verdict}")

    elapsed = time.time() - t0
    print(f"\nTotal time: {elapsed:.1f}s")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "experiment": "H25_cross_omics",
        "results": all_results,
        "min_cross_auc": round(min_cross, 4),
        "mean_cross_auc": round(mean_cross, 4),
        "verdict": verdict,
        "elapsed_s": round(elapsed, 1),
    }
    (RESULTS_DIR / "h25_cross_omics.json").write_text(
        json.dumps(output, indent=2), encoding="utf-8"
    )
    print(f"Results saved: {RESULTS_DIR / 'h25_cross_omics.json'}")


if __name__ == "__main__":
    main()
