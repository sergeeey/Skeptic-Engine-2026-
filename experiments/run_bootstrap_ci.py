"""Bootstrap confidence intervals for all key AUC claims.

Addresses reviewer concern: "your ±0.17 std crosses random interval."
Computes 1000-iteration bootstrap 95% CI for each experiment's key AUC.

Usage:
    python experiments/run_bootstrap_ci.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.io import mmread
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent / "h24_benford_scrna"))

RESULTS_DIR = Path(__file__).resolve().parent / "bootstrap_results"


def bootstrap_auc(
    X: np.ndarray,
    y: np.ndarray,
    model_factory,
    n_bootstrap: int = 1000,
    test_size: float = 0.2,
    random_state: int = 42,
) -> dict:
    """Bootstrap AUC with 95% confidence interval."""
    rng = np.random.default_rng(random_state)
    aucs = []

    for i in range(n_bootstrap):
        # Bootstrap resample
        idx = rng.choice(len(X), size=len(X), replace=True)
        X_boot, y_boot = X[idx], y[idx]

        # Need both classes
        if len(np.unique(y_boot)) < 2:
            continue

        # Train/test split
        splitter = StratifiedShuffleSplit(n_splits=1, test_size=test_size, random_state=i)
        try:
            train_idx, test_idx = next(splitter.split(X_boot, y_boot))
        except ValueError:
            continue

        model = model_factory()
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_boot[train_idx])
        X_test = scaler.transform(X_boot[test_idx])

        model.fit(X_train, y_boot[train_idx])
        try:
            y_prob = model.predict_proba(X_test)[:, 1]
            auc = roc_auc_score(y_boot[test_idx], y_prob)
            aucs.append(auc)
        except (ValueError, IndexError):
            continue

    aucs = np.array(aucs)
    return {
        "mean": round(float(np.mean(aucs)), 4),
        "std": round(float(np.std(aucs)), 4),
        "ci_lower": round(float(np.percentile(aucs, 2.5)), 4),
        "ci_upper": round(float(np.percentile(aucs, 97.5)), 4),
        "n_valid": len(aucs),
        "above_random": bool(np.percentile(aucs, 2.5) > 0.55),
    }


def main() -> None:
    print("=" * 70)
    print("Bootstrap 95% CI for All Key AUC Claims")
    print("=" * 70)
    t0 = time.time()

    all_results = {}

    # ── H24: Benford+Fusion on PBMC3k (resample — hardest case) ──
    print("\n[1/3] H24: Benford fusion on PBMC3k (resample)...")
    from digit_features import extract_features_per_sample
    from fabrication import fabricate_resample
    from isolation_forest import cell_level_features

    mtx_path = (
        Path(__file__).resolve().parent
        / "h24_benford_scrna"
        / "data"
        / "filtered_gene_bc_matrices"
        / "hg19"
        / "matrix.mtx"
    )
    real = mmread(str(mtx_path)).toarray().T.astype(np.int64)
    fake = fabricate_resample(real, rng=np.random.default_rng(2026))

    benford_real = extract_features_per_sample(real)
    benford_fake = extract_features_per_sample(fake)
    cell_real = cell_level_features(real)
    cell_fake = cell_level_features(fake)
    X = np.vstack([np.hstack([benford_real, cell_real]), np.hstack([benford_fake, cell_fake])])
    y = np.concatenate([np.zeros(len(real)), np.ones(len(fake))])

    ci = bootstrap_auc(
        X, y, lambda: RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    )
    print(
        f"  H24 resample fusion: AUC={ci['mean']:.4f} 95%CI=[{ci['ci_lower']:.4f}, {ci['ci_upper']:.4f}] above_random={ci['above_random']}"
    )
    all_results["H24_resample_fusion"] = ci

    # ── H23: RPP real data (LR) ──────────────────────────────────
    print("\n[2/3] H23: RPP real data (LR)...")
    import csv

    rpp_path = Path(__file__).resolve().parent / "h23_phacking_behavioral" / "data" / "rpp_data.csv"
    studies = []
    with open(rpp_path, "r", encoding="latin-1") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                p_orig = float(row.get("T_pval_USE..O.", "").strip().replace(",", "."))
                replicated = row.get("Replicate (R)", "").strip().lower()
                if replicated not in ("yes", "no") or not (0 < p_orig <= 1):
                    continue
                power = float(row.get("Actual Power (O)", "0.5").strip() or "0.5")
                features = [
                    p_orig,
                    np.log10(max(p_orig, 1e-15)),
                    1.0 if 0.04 < p_orig < 0.05 else 0.0,
                    1.0 if p_orig < 0.001 else 0.0,
                    1.0 if 0.01 < p_orig < 0.05 else 0.0,
                    power,
                    0.80 - power,
                    1.0 if abs(p_orig - 0.05) < 0.005 else 0.0,
                    1.0 if abs(p_orig - 0.01) < 0.005 else 0.0,
                    1.0 if 0.04 <= p_orig < 0.05 else 0.0,
                ]
                label = 0 if replicated == "yes" else 1
                studies.append((features, label))
            except (ValueError, TypeError):
                continue

    X_rpp = np.array([s[0] for s in studies])
    y_rpp = np.array([s[1] for s in studies])
    X_rpp = np.nan_to_num(X_rpp, nan=0.0)

    ci_rpp = bootstrap_auc(
        X_rpp, y_rpp, lambda: LogisticRegression(max_iter=2000, random_state=42), n_bootstrap=1000
    )
    print(
        f"  H23 RPP LR: AUC={ci_rpp['mean']:.4f} 95%CI=[{ci_rpp['ci_lower']:.4f}, {ci_rpp['ci_upper']:.4f}] above_random={ci_rpp['above_random']}"
    )
    all_results["H23_RPP_LR"] = ci_rpp

    # ── H23: Statcheck real (LR) ────────────────────────────────
    print("\n[3/3] H23: Statcheck real data (LR)...")
    from collections import defaultdict

    sc_path = (
        Path(__file__).resolve().parent
        / "h23_phacking_behavioral"
        / "data"
        / "statcheckDataMetaAnalyses_Anonymized.txt"
    )

    articles: dict[str, list[dict]] = defaultdict(list)
    with open(sc_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=" ", quotechar='"')
        for row in reader:
            source = row.get("Source", "").strip()
            if not source:
                continue
            try:
                rp = float(row.get("Reported.P.Value", "nan"))
                err = row.get("Error", "FALSE") == "TRUE"
                if np.isnan(rp) or not (0 < rp <= 1):
                    continue
                articles[source].append({"reported_p": rp, "error": err})
            except (ValueError, TypeError):
                continue

    X_sc_list, y_sc_list = [], []
    for source, tests in articles.items():
        if len(tests) < 2:
            continue
        rps = np.array([t["reported_p"] for t in tests])
        has_error = any(t["error"] for t in tests)
        feats = [
            np.mean(rps),
            np.std(rps),
            np.min(rps),
            (rps < 0.05).mean(),
            ((rps > 0.04) & (rps < 0.05)).mean(),
            len(tests),
            np.log1p(len(tests)),
        ]
        if len(rps) > 1:
            feats.extend([np.std(np.diff(rps)), (np.diff(rps) < 0).mean()])
        else:
            feats.extend([0, 0])
        X_sc_list.append(feats)
        y_sc_list.append(1 if has_error else 0)

    X_sc = np.nan_to_num(np.array(X_sc_list), nan=0.0)
    y_sc = np.array(y_sc_list)

    ci_sc = bootstrap_auc(
        X_sc, y_sc, lambda: LogisticRegression(max_iter=2000, random_state=42), n_bootstrap=1000
    )
    print(
        f"  H23 Statcheck LR: AUC={ci_sc['mean']:.4f} 95%CI=[{ci_sc['ci_lower']:.4f}, {ci_sc['ci_upper']:.4f}] above_random={ci_sc['above_random']}"
    )
    all_results["H23_Statcheck_LR"] = ci_sc

    # ── Summary ──────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("BOOTSTRAP CI SUMMARY")
    print(f"{'=' * 70}")
    print(f"{'Experiment':<25} {'AUC':>6} {'95% CI':>20} {'> 0.55?':>8}")
    print("-" * 62)
    for name, ci in all_results.items():
        status = "YES" if ci["above_random"] else "NO"
        print(
            f"{name:<25} {ci['mean']:>6.4f} [{ci['ci_lower']:.4f}, {ci['ci_upper']:.4f}] {status:>8}"
        )

    elapsed = time.time() - t0
    print(f"\nTotal time: {elapsed:.1f}s")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "bootstrap_ci.json"
    out_path.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    print(f"Results saved: {out_path}")


if __name__ == "__main__":
    main()
