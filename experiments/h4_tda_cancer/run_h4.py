"""H4 Clean Run — TDA for Cancer Drug Resistance State Detection.

One clean benchmark: does persistent homology (TDA) add value over standard
embedding baselines for distinguishing sensitive vs resistant melanoma cells?

Dataset: GSE164897 (Schmidt et al. 2021)
- 4 samples: 1 sensitive (untreated), 3 resistant (vemurafenib ± combos)
- ~27,000 cells, scRNA-seq 10x Genomics v2
- Binary label: sensitive (0) vs resistant (1)

Three baselines:
  1. PCA embedding + RF (standard)
  2. Variance/dispersion features + RF
  3. TDA: persistent homology on PCA point cloud → Betti features + RF

Kill criterion: if TDA AUC < 0.75 OR TDA adds < 2pp over PCA baseline → close H4.

Usage:
    python experiments/h4_tda_cancer/run_h4.py
"""

from __future__ import annotations

import gzip
import json
import time
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, average_precision_score, balanced_accuracy_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

DATA_DIR = Path(__file__).resolve().parent / "data"
RESULTS_DIR = Path(__file__).resolve().parent / "results"

SAMPLES = {
    "GSM5022595_raw_counts_probe3.txt.gz": {
        "probe": "Probe3_A375R",
        "label": 1,
        "condition": "vemurafenib_resistant",
    },
    "GSM5022596_raw_counts_probe4.txt.gz": {
        "probe": "Probe4_A375S",
        "label": 0,
        "condition": "sensitive_untreated",
    },
    "GSM5022597_raw_counts_probe5.txt.gz": {
        "probe": "Probe5_A375RR",
        "label": 1,
        "condition": "vem_cobimetinib_resistant",
    },
    "GSM5022598_raw_counts_probe6.txt.gz": {
        "probe": "Probe6_A375RR",
        "label": 1,
        "condition": "vem_trametinib_resistant",
    },
}


def load_count_matrix(path: Path) -> tuple[np.ndarray, list[str], list[str]]:
    """Load space-separated gene×cell matrix. Returns (matrix, gene_ids, cell_barcodes)."""
    with gzip.open(path, "rt") as f:
        header = f.readline().strip()
        barcodes = [b.strip('"') for b in header.split()]

        genes = []
        rows = []
        for line in f:
            parts = line.strip().split()
            gene_id = parts[0].strip('"')
            values = [int(x) for x in parts[1:]]
            genes.append(gene_id)
            rows.append(values)

    matrix = np.array(rows, dtype=np.int64)  # genes × cells
    return matrix.T, genes, barcodes  # transpose to cells × genes


def load_all_samples() -> tuple[np.ndarray, np.ndarray, list[str], list[str]]:
    """Load and combine all 4 samples into one matrix with labels."""
    sample_data: list[tuple[np.ndarray, list[str], dict]] = []

    for filename, meta in SAMPLES.items():
        path = DATA_DIR / filename
        print(f"  Loading {meta['probe']} ({meta['condition']})...")
        matrix, genes, barcodes = load_count_matrix(path)
        print(f"    {matrix.shape[0]} cells × {matrix.shape[1]} genes")
        sample_data.append((matrix, genes, meta))

    # Find shared genes across all samples
    gene_sets = [set(genes) for _, genes, _ in sample_data]
    shared_genes = sorted(set.intersection(*gene_sets))
    print(f"  Shared genes across all samples: {len(shared_genes)}")

    all_cells = []
    all_labels = []
    all_conditions = []

    for matrix, genes, meta in sample_data:
        gene_to_idx = {g: i for i, g in enumerate(genes)}
        shared_idx = [gene_to_idx[g] for g in shared_genes]
        aligned = matrix[:, shared_idx]
        all_cells.append(aligned)
        all_labels.extend([meta["label"]] * aligned.shape[0])
        all_conditions.extend([meta["condition"]] * aligned.shape[0])

    X = np.vstack(all_cells)
    y = np.array(all_labels)
    return X, y, all_conditions, shared_genes


def preprocess(X: np.ndarray, n_top_genes: int = 2000) -> np.ndarray:
    """Basic preprocessing: filter to top variable genes, log-normalize."""
    # Library size normalization
    lib_sizes = X.sum(axis=1, keepdims=True)
    lib_sizes = np.maximum(lib_sizes, 1)
    X_norm = X / lib_sizes * 10000  # CPM-like

    # Log1p
    X_log = np.log1p(X_norm)

    # Select top variable genes
    gene_var = X_log.var(axis=0)
    top_idx = np.argsort(gene_var)[-n_top_genes:]
    X_hvg = X_log[:, top_idx]

    return X_hvg


# ── Baseline 1: PCA embedding features ──────────────────────────


def pca_features(X: np.ndarray, n_components: int = 50) -> np.ndarray:
    """PCA embedding of normalized expression."""
    pca = PCA(n_components=min(n_components, X.shape[1], X.shape[0]))
    return pca.fit_transform(X)


# ── Baseline 2: Dispersion/variance features ────────────────────


def dispersion_features(X_raw: np.ndarray) -> np.ndarray:
    """Per-cell summary statistics (no embedding needed)."""
    n_cells = X_raw.shape[0]
    features = np.zeros((n_cells, 10), dtype=np.float64)

    for i in range(n_cells):
        row = X_raw[i].astype(np.float64)
        nonzero = row[row > 0]
        features[i, 0] = row.sum()  # library size
        features[i, 1] = len(nonzero)  # genes detected
        features[i, 2] = 1.0 - len(nonzero) / max(len(row), 1)  # zero fraction
        features[i, 3] = nonzero.mean() if len(nonzero) > 0 else 0  # mean nonzero
        features[i, 4] = nonzero.var() if len(nonzero) > 1 else 0  # var nonzero
        features[i, 5] = (
            nonzero.std() / nonzero.mean() if len(nonzero) > 0 and nonzero.mean() > 0 else 0
        )  # CV
        features[i, 6] = row.max()  # max count
        features[i, 7] = np.log1p(row.sum())  # log library size
        features[i, 8] = np.median(nonzero) if len(nonzero) > 0 else 0  # median nonzero
        features[i, 9] = (
            (nonzero > 5).sum() / max(len(nonzero), 1) if len(nonzero) > 0 else 0
        )  # frac high-expr

    return features


# ── Baseline 3: TDA features (persistent homology) ──────────────


def tda_features(X_pca: np.ndarray, n_neighbors: int = 50, n_landmarks: int = 500) -> np.ndarray:
    """Compute TDA features via persistent homology on PCA point cloud.

    For each cell: compute local persistent homology around its neighborhood.
    Features: Betti numbers, persistence statistics, topological complexity.
    """
    from ripser import ripser

    n_cells = X_pca.shape[0]
    features = np.zeros((n_cells, 12), dtype=np.float64)

    # Precompute k-NN for efficiency
    from sklearn.neighbors import NearestNeighbors

    nn = NearestNeighbors(n_neighbors=min(n_neighbors, n_cells - 1), algorithm="ball_tree")
    nn.fit(X_pca)

    print(f"    Computing TDA features for {n_cells} cells (local PH on {n_neighbors}-NN)...")
    t0 = time.time()
    failed_count = 0

    for i in range(n_cells):
        # Get local neighborhood
        distances, indices = nn.kneighbors(X_pca[i : i + 1])
        local_cloud = X_pca[indices[0]]

        # Compute persistent homology (H0 and H1)
        try:
            result = ripser(local_cloud, maxdim=1, thresh=2.0)
            dgms = result["dgms"]

            # H0 features (connected components)
            h0 = dgms[0]
            h0_finite = h0[np.isfinite(h0[:, 1])]
            if len(h0_finite) > 0:
                lifetimes_h0 = h0_finite[:, 1] - h0_finite[:, 0]
                features[i, 0] = len(h0_finite)  # number of H0 features
                features[i, 1] = lifetimes_h0.mean()  # mean H0 lifetime
                features[i, 2] = lifetimes_h0.max()  # max H0 lifetime
                features[i, 3] = lifetimes_h0.sum()  # total H0 persistence

            # H1 features (loops)
            if len(dgms) > 1:
                h1 = dgms[1]
                if len(h1) > 0:
                    lifetimes_h1 = h1[:, 1] - h1[:, 0]
                    features[i, 4] = len(h1)  # number of H1 features (loops)
                    features[i, 5] = lifetimes_h1.mean()  # mean H1 lifetime
                    features[i, 6] = lifetimes_h1.max()  # max H1 lifetime
                    features[i, 7] = lifetimes_h1.sum()  # total H1 persistence

            # Combined features
            total_features = len(h0_finite) + (len(dgms[1]) if len(dgms) > 1 else 0)
            features[i, 8] = total_features  # topological complexity
            features[i, 9] = features[i, 3] + features[i, 7]  # total persistence (H0+H1)

            # Persistence entropy
            all_lifetimes = []
            if len(h0_finite) > 0:
                all_lifetimes.extend(h0_finite[:, 1] - h0_finite[:, 0])
            if len(dgms) > 1 and len(dgms[1]) > 0:
                all_lifetimes.extend(dgms[1][:, 1] - dgms[1][:, 0])
            if all_lifetimes:
                lt = np.array(all_lifetimes)
                lt_sum = lt.sum()
                if lt_sum > 0:
                    lt_norm = lt / lt_sum
                    features[i, 10] = -np.sum(lt_norm * np.log2(lt_norm + 1e-15))
                features[i, 11] = lt.std()

        except Exception:
            failed_count += 1

        if (i + 1) % 5000 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (n_cells - i - 1) / rate
            print(f"      {i + 1}/{n_cells} ({rate:.0f} cells/s, ETA {eta:.0f}s)")

    print(f"    TDA complete: {time.time() - t0:.1f}s ({failed_count} cells failed)")
    return features


# ── Evaluation ───────────────────────────────────────────────────


def evaluate_cv(X: np.ndarray, y: np.ndarray, name: str, n_splits: int = 5) -> dict:
    """Stratified k-fold CV with RF."""
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    scaler = StandardScaler()

    fold_aucs = []
    fold_aps = []
    fold_bas = []

    for train_idx, test_idx in cv.split(X, y):
        X_train = scaler.fit_transform(X[train_idx])
        X_test = scaler.transform(X[test_idx])

        rf = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42, n_jobs=-1)
        rf.fit(X_train, y[train_idx])
        y_prob = rf.predict_proba(X_test)[:, 1]
        y_pred = rf.predict(X_test)

        fold_aucs.append(roc_auc_score(y[test_idx], y_prob))
        fold_aps.append(average_precision_score(y[test_idx], y_prob))
        fold_bas.append(balanced_accuracy_score(y[test_idx], y_pred))

    result = {
        "name": name,
        "auc_mean": round(np.mean(fold_aucs), 4),
        "auc_std": round(np.std(fold_aucs), 4),
        "ap_mean": round(np.mean(fold_aps), 4),
        "ba_mean": round(np.mean(fold_bas), 4),
    }
    print(
        f"  {name:30s} AUC={result['auc_mean']:.4f}±{result['auc_std']:.4f}  AP={result['ap_mean']:.4f}  BA={result['ba_mean']:.4f}"
    )
    return result


def main() -> None:
    print("=" * 70)
    print("H4 Clean Run — TDA for Cancer Drug Resistance Detection")
    print("=" * 70)
    t0 = time.time()

    # Load data
    print("\n[1/5] Loading GSE164897 raw count matrices...")
    X_raw, y, conditions, gene_ids = load_all_samples()
    print(f"\n  Combined: {X_raw.shape[0]} cells × {X_raw.shape[1]} genes")
    print(f"  Labels: sensitive={np.sum(y == 0)}, resistant={np.sum(y == 1)}")
    print(f"  Class balance: {np.mean(y):.3f} (resistant fraction)")

    # Preprocess
    print("\n[2/5] Preprocessing (normalize + top 2000 HVG)...")
    X_hvg = preprocess(X_raw, n_top_genes=2000)
    print(f"  Preprocessed: {X_hvg.shape}")

    # Baseline 1: PCA
    print("\n[3/5] Computing PCA embedding (50 components)...")
    X_pca = pca_features(X_hvg, n_components=50)
    print(f"  PCA: {X_pca.shape}")

    # Baseline 2: Dispersion
    print("\n[4/5] Computing dispersion features...")
    X_disp = dispersion_features(X_raw)
    print(f"  Dispersion: {X_disp.shape}")

    # Baseline 3: TDA
    print("\n[5/5] Computing TDA features (persistent homology on PCA cloud)...")
    X_tda = tda_features(X_pca, n_neighbors=30)
    print(f"  TDA: {X_tda.shape}")

    # ── Evaluate all baselines ───────────────────────────────────
    print(f"\n{'=' * 70}")
    print("5-fold Stratified CV Results")
    print(f"{'=' * 70}")

    all_results = []

    res_pca = evaluate_cv(X_pca, y, "PCA (50 components)")
    all_results.append(res_pca)

    res_disp = evaluate_cv(X_disp, y, "Dispersion (10 features)")
    all_results.append(res_disp)

    res_tda = evaluate_cv(X_tda, y, "TDA (12 PH features)")
    all_results.append(res_tda)

    # Fusion: PCA + TDA
    X_pca_tda = np.hstack([X_pca, X_tda])
    res_fusion = evaluate_cv(X_pca_tda, y, "PCA + TDA fusion")
    all_results.append(res_fusion)

    # Fusion: all
    X_all = np.hstack([X_pca, X_disp, X_tda])
    res_all = evaluate_cv(X_all, y, "PCA + Disp + TDA fusion")
    all_results.append(res_all)

    # ── Kill criterion ───────────────────────────────────────────
    tda_auc = res_tda["auc_mean"]
    pca_auc = res_pca["auc_mean"]
    tda_lift = tda_auc - pca_auc
    fusion_lift = res_fusion["auc_mean"] - pca_auc

    print(f"\n{'=' * 70}")
    print("KILL CRITERION CHECK")
    print(f"{'=' * 70}")
    print(f"  TDA standalone AUC:     {tda_auc:.4f}")
    print(f"  PCA baseline AUC:       {pca_auc:.4f}")
    print(f"  TDA lift over PCA:      {tda_lift:+.4f}")
    print(f"  PCA+TDA fusion lift:    {fusion_lift:+.4f}")

    if tda_auc < 0.75:
        verdict = f"KILL — TDA AUC ({tda_auc:.4f}) < 0.75 threshold. Close H4 track."
    elif tda_lift < 0.02 and fusion_lift < 0.02:
        verdict = f"KILL — TDA adds < 2pp over PCA ({tda_lift:+.4f}). No value from topology."
    elif fusion_lift >= 0.02:
        verdict = f"KEEP — PCA+TDA fusion adds {fusion_lift:+.4f} over PCA. TDA contributes."
    else:
        verdict = f"MARGINAL — TDA lift is {tda_lift:+.4f}. Consider closing unless justified."

    print(f"\n  VERDICT: {verdict}")

    # ── Caveat ───────────────────────────────────────────────────
    print(
        f"\n  CAVEAT: This is a cell-level classification. Only 4 samples (1 sensitive, 3 resistant)."
    )
    print(
        f"  CAVEAT: Cell-level splitting may leak sample identity. True generalization untestable with 4 samples."
    )
    print(
        f"  CAVEAT: High AUC may reflect trivial batch differences, not biological resistance signature."
    )

    elapsed = time.time() - t0
    print(f"\n  Total time: {elapsed:.1f}s")

    # Save
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "experiment": "H4_tda_cancer_resistance",
        "dataset": "GSE164897",
        "n_cells": int(X_raw.shape[0]),
        "n_genes": int(X_raw.shape[1]),
        "n_hvg": int(X_hvg.shape[1]),
        "class_balance": round(float(np.mean(y)), 4),
        "results": all_results,
        "tda_standalone_auc": round(tda_auc, 4),
        "pca_baseline_auc": round(pca_auc, 4),
        "tda_lift": round(tda_lift, 4),
        "fusion_lift": round(fusion_lift, 4),
        "verdict": verdict,
        "elapsed_s": round(elapsed, 1),
    }
    out_path = RESULTS_DIR / "h4_results.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"  Results saved: {out_path}")


if __name__ == "__main__":
    main()
