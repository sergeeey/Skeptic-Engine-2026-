"""H24+H21 Normalized Cross-Validation — Feature normalization to improve generalization.

Hypothesis: cross-dataset failure is caused by dataset-specific baseline shifts in
Benford/cell-level features. Subtracting per-dataset mean profile should remove
dataset identity while preserving fabrication signal.

Three normalization strategies:
  A) Z-score: (x - mean) / std per feature, computed on real data only
  B) Rank: replace values with rank percentiles (distribution-free)
  C) Delta-from-Benford: subtract theoretical Benford expected frequencies

Usage:
    python experiments/h24_benford_scrna/run_normalized_crossval.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, f1_score, roc_auc_score
from sklearn.preprocessing import QuantileTransformer, StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))

from digit_features import BENFORD_FIRST, BENFORD_SECOND, extract_features_per_sample
from fabrication import FABRICATION_METHODS
from isolation_forest import cell_level_features
from run_crossval import _load_kang2018, _load_pbmc3k

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def _extract_all(matrix: np.ndarray) -> np.ndarray:
    benford = extract_features_per_sample(matrix)
    cell = cell_level_features(matrix)
    return np.hstack([benford, cell])


def _evaluate(model, X: np.ndarray, y: np.ndarray) -> dict:
    y_prob = model.predict_proba(X)[:, 1]
    y_pred = model.predict(X)
    return {
        "auc": round(roc_auc_score(y, y_prob), 4),
        "ap": round(average_precision_score(y, y_prob), 4),
        "f1": round(f1_score(y, y_pred), 4),
    }


class DeltaBenfordTransformer:
    """Subtract theoretical Benford expected from digit frequency features.

    Features 0-8: first digit → subtract BENFORD_FIRST
    Features 9-18: second digit → subtract BENFORD_SECOND
    Features 19-20: chi2 stats → leave as-is
    Features 21+: cell-level → z-score normalize
    """

    def __init__(self) -> None:
        self._cell_scaler = StandardScaler()
        self._fitted = False

    def fit(self, X: np.ndarray) -> "DeltaBenfordTransformer":
        if X.shape[1] > 21:
            self._cell_scaler.fit(X[:, 21:])
        self._fitted = True
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        out = X.copy()
        # Delta from Benford expected
        out[:, :9] -= BENFORD_FIRST
        out[:, 9:19] -= BENFORD_SECOND
        # Cell-level features: z-score
        if X.shape[1] > 21:
            out[:, 21:] = self._cell_scaler.transform(X[:, 21:])
        return out

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        self.fit(X)
        return self.transform(X)


NORMALIZERS = {
    "raw": None,
    "zscore": lambda: StandardScaler(),
    "rank": lambda: QuantileTransformer(output_distribution="normal", random_state=42),
    "delta_benford": lambda: DeltaBenfordTransformer(),
}


def main() -> None:
    print("=" * 70)
    print("H24+H21 Normalized Cross-Validation")
    print("=" * 70)
    t0 = time.time()

    # Load
    print("\nLoading datasets...")
    pbmc3k = _load_pbmc3k()
    kang = _load_kang2018()

    rng = np.random.default_rng(2026)
    if kang.shape[0] > pbmc3k.shape[0] * 2:
        idx = rng.choice(kang.shape[0], size=pbmc3k.shape[0], replace=False)
        kang = kang[idx]

    min_genes = min(pbmc3k.shape[1], kang.shape[1])
    pbmc3k = pbmc3k[:, :min_genes]
    kang = kang[:, :min_genes]
    n_cells = pbmc3k.shape[0]
    print(f"PBMC3k: {pbmc3k.shape}, Kang: {kang.shape}")

    all_results = []

    for method_name in FABRICATION_METHODS:
        print(f"\n{'=' * 60}")
        print(f"Fabrication: {method_name}")
        print(f"{'=' * 60}")

        # Generate features
        fab_fn = FABRICATION_METHODS[method_name]
        pbmc_real_feat = _extract_all(pbmc3k)
        pbmc_fake_feat = _extract_all(fab_fn(pbmc3k, rng=np.random.default_rng(2026)))
        kang_real_feat = _extract_all(kang)
        kang_fake_feat = _extract_all(fab_fn(kang, rng=np.random.default_rng(2026)))

        X_pbmc = np.vstack([pbmc_real_feat, pbmc_fake_feat])
        y_pbmc = np.concatenate([np.zeros(n_cells), np.ones(n_cells)])
        X_kang = np.vstack([kang_real_feat, kang_fake_feat])
        y_kang = np.concatenate([np.zeros(n_cells), np.ones(n_cells)])

        method_results = {"method": method_name}

        for norm_name, norm_factory in NORMALIZERS.items():
            if norm_factory is None:
                X_p, X_k = X_pbmc, X_kang
            else:
                # Fit normalizer on REAL data of training dataset only
                scaler_p = norm_factory()
                scaler_p.fit(pbmc_real_feat)
                X_p = scaler_p.transform(X_pbmc)
                X_k = scaler_p.transform(X_kang)  # Apply PBMC3k scaler to Kang

                # Also fit on Kang real for reverse direction
                scaler_k = norm_factory()
                scaler_k.fit(kang_real_feat)
                X_k_rev = scaler_k.transform(X_kang)
                X_p_rev = scaler_k.transform(X_pbmc)

            # Train on PBMC3k → test on Kang
            rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
            rf.fit(X_p, y_pbmc)
            p_to_k = _evaluate(rf, X_k, y_kang)

            # Train on Kang → test on PBMC3k
            if norm_factory is not None:
                rf2 = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
                rf2.fit(X_k_rev, y_kang)
                k_to_p = _evaluate(rf2, X_p_rev, y_pbmc)
            else:
                rf2 = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
                rf2.fit(X_kang, y_kang)
                k_to_p = _evaluate(rf2, X_pbmc, y_pbmc)

            method_results[norm_name] = {
                "p_to_k": p_to_k,
                "k_to_p": k_to_p,
                "mean_cross": round((p_to_k["auc"] + k_to_p["auc"]) / 2, 4),
            }

            print(
                f"  {norm_name:16s} | P→K={p_to_k['auc']:.4f}  K→P={k_to_p['auc']:.4f}  "
                f"mean={method_results[norm_name]['mean_cross']:.4f}"
            )

        all_results.append(method_results)

    # Summary
    print(f"\n{'=' * 70}")
    print("NORMALIZATION IMPACT ON CROSS-DATASET AUC (mean of P→K and K→P)")
    print(f"{'=' * 70}")
    print(f"{'Method':<14} {'raw':>8} {'zscore':>8} {'rank':>8} {'delta_B':>8}")
    print("-" * 50)
    for r in all_results:
        print(
            f"{r['method']:<14} "
            f"{r['raw']['mean_cross']:>8.4f} "
            f"{r['zscore']['mean_cross']:>8.4f} "
            f"{r['rank']['mean_cross']:>8.4f} "
            f"{r['delta_benford']['mean_cross']:>8.4f}"
        )

    # Best normalization per method
    print(f"\nBest normalization per fabrication method:")
    for r in all_results:
        best_norm = max(
            ["raw", "zscore", "rank", "delta_benford"],
            key=lambda n: r[n]["mean_cross"],
        )
        print(f"  {r['method']:14s} → {best_norm} (mean AUC={r[best_norm]['mean_cross']:.4f})")

    elapsed = time.time() - t0
    print(f"\nTotal time: {elapsed:.1f}s")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "h24_normalized_crossval.json"
    out_path.write_text(
        json.dumps({"results": all_results, "elapsed_s": round(elapsed, 1)}, indent=2),
        encoding="utf-8",
    )
    print(f"Results saved: {out_path}")


if __name__ == "__main__":
    main()
