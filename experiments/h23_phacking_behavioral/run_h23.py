"""H23 MVP — Behavioral Sequence Anomaly Detection for P-Hacking Patterns.

Transfer: Fraud transaction sequence anomaly detection → p-value choice pattern analysis.

Approach:
  1. Simulate clean research (real statistical power → p-value sequences)
  2. Simulate p-hacked research (12 Stefan 2023 strategies → distorted sequences)
  3. Extract behavioral features from p-value sequences
  4. Train anomaly detector (IF + RF)
  5. Compare to p-curve baseline

Usage:
    python experiments/h23_phacking_behavioral/run_h23.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from scipy import stats
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import roc_auc_score, average_precision_score, f1_score
from sklearn.model_selection import StratifiedShuffleSplit

RESULTS_DIR = Path(__file__).resolve().parent / "results"


# ── P-value simulation ──────────────────────────────────────────


def simulate_clean_study(
    n_tests: int = 20,
    true_effect: float = 0.3,
    sample_size: int = 50,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Simulate a clean study: t-tests with real effect size → p-value sequence."""
    rng = rng or np.random.default_rng()
    p_values = []
    for _ in range(n_tests):
        group_a = rng.normal(0, 1, size=sample_size)
        group_b = rng.normal(true_effect, 1, size=sample_size)
        _, p = stats.ttest_ind(group_a, group_b)
        p_values.append(p)
    return np.array(p_values)


def simulate_null_study(
    n_tests: int = 20,
    sample_size: int = 50,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Simulate null study: no real effect → uniform p-values."""
    rng = rng or np.random.default_rng()
    p_values = []
    for _ in range(n_tests):
        group_a = rng.normal(0, 1, size=sample_size)
        group_b = rng.normal(0, 1, size=sample_size)
        _, p = stats.ttest_ind(group_a, group_b)
        p_values.append(p)
    return np.array(p_values)


def phack_optional_stopping(
    sample_size_start: int = 20,
    sample_size_max: int = 100,
    step: int = 5,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """P-hack strategy 1: optional stopping — keep adding subjects until p < 0.05."""
    rng = rng or np.random.default_rng()
    p_values = []
    group_a = rng.normal(0, 1, size=sample_size_max)
    group_b = rng.normal(0, 1, size=sample_size_max)

    for n in range(sample_size_start, sample_size_max + 1, step):
        _, p = stats.ttest_ind(group_a[:n], group_b[:n])
        p_values.append(p)
        if p < 0.05:
            break
    return np.array(p_values)


def phack_outcome_switching(
    n_outcomes: int = 5,
    sample_size: int = 50,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """P-hack strategy 2: test multiple outcomes, report the best."""
    rng = rng or np.random.default_rng()
    p_values = []
    group_a = rng.normal(0, 1, size=(sample_size, n_outcomes))
    group_b = rng.normal(0, 1, size=(sample_size, n_outcomes))

    for j in range(n_outcomes):
        _, p = stats.ttest_ind(group_a[:, j], group_b[:, j])
        p_values.append(p)
    return np.array(p_values)


def phack_outlier_exclusion(
    sample_size: int = 50,
    n_attempts: int = 10,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """P-hack strategy 3: exclude outliers until significant."""
    rng = rng or np.random.default_rng()
    group_a = rng.normal(0, 1, size=sample_size)
    group_b = rng.normal(0, 1, size=sample_size)

    p_values = []
    _, p_full = stats.ttest_ind(group_a, group_b)
    p_values.append(p_full)

    for _ in range(n_attempts):
        # Remove the most extreme point from whichever group
        if np.abs(group_a).max() > np.abs(group_b).max():
            idx = np.argmax(np.abs(group_a))
            group_a = np.delete(group_a, idx)
        else:
            idx = np.argmax(np.abs(group_b))
            group_b = np.delete(group_b, idx)

        if len(group_a) < 10 or len(group_b) < 10:
            break
        _, p = stats.ttest_ind(group_a, group_b)
        p_values.append(p)
        if p < 0.05:
            break
    return np.array(p_values)


def phack_covariate_fishing(
    n_covariates: int = 5,
    sample_size: int = 50,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """P-hack strategy 4: add covariates until significant."""
    rng = rng or np.random.default_rng()
    y = rng.normal(0, 1, size=sample_size)
    X = rng.normal(0, 1, size=(sample_size, n_covariates + 1))
    X[:, 0] = rng.choice([0, 1], size=sample_size)  # Treatment

    p_values = []
    for n_cov in range(n_covariates + 1):
        X_subset = X[:, : n_cov + 1]
        try:
            # OLS: p-value for treatment coefficient
            XtX_inv = np.linalg.pinv(X_subset.T @ X_subset)
            beta = XtX_inv @ X_subset.T @ y
            residuals = y - X_subset @ beta
            mse = (residuals**2).sum() / max(len(y) - X_subset.shape[1], 1)
            se = np.sqrt(mse * np.diag(XtX_inv))
            t_stat = beta[0] / max(se[0], 1e-10)
            p = 2 * stats.t.sf(np.abs(t_stat), df=max(len(y) - X_subset.shape[1], 1))
            p_values.append(p)
        except Exception:
            p_values.append(1.0)
    return np.array(p_values)


PHACK_STRATEGIES = {
    "optional_stopping": phack_optional_stopping,
    "outcome_switching": phack_outcome_switching,
    "outlier_exclusion": phack_outlier_exclusion,
    "covariate_fishing": phack_covariate_fishing,
}


# ── Behavioral feature extraction (fraud-style) ─────────────────


def extract_behavioral_features(p_sequence: np.ndarray) -> np.ndarray:
    """Extract fraud-style behavioral features from a p-value sequence.

    Returns 18 features capturing the "behavioral fingerprint" of the research process.
    """
    n = len(p_sequence)
    if n == 0:
        return np.zeros(18)

    p = np.clip(p_sequence, 1e-15, 1.0)

    features = []

    # 1-3: Basic p-value statistics
    features.append(np.mean(p))  # mean p-value
    features.append(np.std(p) if n > 1 else 0)  # std of p-values
    features.append(np.min(p))  # minimum p-value

    # 4-6: Distribution shape
    features.append((p < 0.05).sum() / n)  # fraction significant
    features.append(
        (p < 0.10).sum() / n - (p < 0.05).sum() / n
    )  # fraction in "gray zone" 0.05-0.10
    features.append(((p > 0.04) & (p < 0.05)).sum() / max(n, 1))  # fraction just below 0.05

    # 7-9: Sequence dynamics (fraud-style: velocity, direction changes)
    if n > 1:
        diffs = np.diff(p)
        features.append(np.mean(diffs))  # mean delta (trend)
        features.append(np.std(diffs))  # volatility of deltas
        features.append((diffs < 0).sum() / len(diffs))  # fraction of decreasing steps
    else:
        features.extend([0, 0, 0])

    # 10-12: Terminal behavior (fraud: what happens at the end?)
    features.append(p[-1])  # final p-value
    features.append(1.0 if p[-1] < 0.05 else 0.0)  # did they "succeed"?
    features.append(p[-1] - p[0] if n > 1 else 0)  # total drift

    # 13-15: Entropy and regularity
    hist, _ = np.histogram(p, bins=10, range=(0, 1))
    hist_norm = hist / max(hist.sum(), 1)
    entropy = -np.sum(hist_norm[hist_norm > 0] * np.log2(hist_norm[hist_norm > 0]))
    features.append(entropy)  # Shannon entropy of p-distribution
    features.append(n)  # sequence length
    features.append(np.log1p(n))  # log sequence length

    # 16-18: Suspicious patterns
    features.append(
        np.sum(np.abs(np.diff(np.sign(np.diff(p)))) > 0) / max(n - 2, 1) if n > 2 else 0
    )  # direction change rate
    features.append(np.max(np.abs(np.diff(p))) if n > 1 else 0)  # max single-step jump
    features.append(np.corrcoef(np.arange(n), p)[0, 1] if n > 2 else 0)  # trend correlation

    return np.array(features[:18])


FEATURE_NAMES = [
    "mean_p",
    "std_p",
    "min_p",
    "frac_sig",
    "frac_gray_zone",
    "frac_just_below_05",
    "mean_delta",
    "volatility",
    "frac_decreasing",
    "final_p",
    "success_flag",
    "total_drift",
    "entropy",
    "seq_length",
    "log_seq_length",
    "direction_change_rate",
    "max_jump",
    "trend_corr",
]


# ── P-curve baseline ────────────────────────────────────────────


def pcurve_test_stat(p_sequence: np.ndarray) -> float:
    """Simple p-curve right-skew test: fraction of significant p-values < 0.025.

    Under real effect: most sig p-values cluster near 0.
    Under p-hacking: p-values cluster just below 0.05.
    """
    sig = p_sequence[p_sequence < 0.05]
    if len(sig) == 0:
        return 0.5
    return (sig < 0.025).mean()


# ── Main experiment ──────────────────────────────────────────────


def main() -> None:
    print("=" * 70)
    print("H23 MVP — Behavioral Sequence Anomaly for P-Hacking Detection")
    print("=" * 70)
    t0 = time.time()

    n_studies = 500  # per class
    rng = np.random.default_rng(2026)

    # Generate clean studies
    print(f"\n[1/4] Generating {n_studies} clean study sequences...")
    clean_sequences = []
    for _ in range(n_studies):
        effect = rng.choice([0.0, 0.2, 0.3, 0.5])  # mix of null and real effects
        if effect == 0:
            seq = simulate_null_study(n_tests=rng.integers(5, 30), rng=rng)
        else:
            seq = simulate_clean_study(n_tests=rng.integers(5, 30), true_effect=effect, rng=rng)
        clean_sequences.append(seq)

    # Generate p-hacked studies
    print(f"[2/4] Generating {n_studies} p-hacked study sequences...")
    hacked_sequences = []
    strategy_names = list(PHACK_STRATEGIES.keys())
    for _ in range(n_studies):
        strategy = rng.choice(strategy_names)
        seq = PHACK_STRATEGIES[strategy](rng=rng)
        hacked_sequences.append(seq)

    # Extract features
    print("[3/4] Extracting behavioral features...")
    X_clean = np.array([extract_behavioral_features(s) for s in clean_sequences])
    X_hacked = np.array([extract_behavioral_features(s) for s in hacked_sequences])

    X = np.vstack([X_clean, X_hacked])
    y = np.concatenate([np.zeros(n_studies), np.ones(n_studies)])

    # Handle NaN/Inf
    X = np.nan_to_num(X, nan=0.0, posinf=10.0, neginf=-10.0)

    print(f"  Features shape: {X.shape}")
    print(f"  Clean mean features: {np.round(X_clean.mean(axis=0)[:6], 3)}")
    print(f"  Hacked mean features: {np.round(X_hacked.mean(axis=0)[:6], 3)}")

    # ── Method 1: RF on behavioral features ──────────────────────
    print("\n[4/4] Training classifiers...")
    splitter = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(splitter.split(X, y))

    rf = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    rf.fit(X[train_idx], y[train_idx])
    rf_proba = rf.predict_proba(X[test_idx])[:, 1]
    rf_auc = roc_auc_score(y[test_idx], rf_proba)
    rf_ap = average_precision_score(y[test_idx], rf_proba)

    # ── Method 2: Isolation Forest (one-class on clean) ──────────
    iso = IsolationForest(n_estimators=200, contamination=0.1, random_state=42)
    iso.fit(X_clean)
    iso_scores = -iso.decision_function(X)  # negate: higher = more anomalous
    iso_auc = roc_auc_score(y, iso_scores)

    # ── Method 3: P-curve baseline ───────────────────────────────
    pcurve_clean = np.array([pcurve_test_stat(s) for s in clean_sequences])
    pcurve_hacked = np.array([pcurve_test_stat(s) for s in hacked_sequences])
    pcurve_scores = np.concatenate([pcurve_clean, pcurve_hacked])
    # For p-hacking: p-curve score is LOWER (p-values cluster near 0.05, not 0)
    pcurve_auc = roc_auc_score(y, -pcurve_scores)  # negate: lower right-skew = more suspicious

    # ── Feature importance ───────────────────────────────────────
    from sklearn.inspection import permutation_importance

    perm = permutation_importance(
        rf, X[test_idx], y[test_idx], n_repeats=10, random_state=42, scoring="roc_auc", n_jobs=-1
    )
    sorted_idx = np.argsort(perm.importances_mean)[::-1]

    print(f"\n{'=' * 70}")
    print("RESULTS")
    print(f"{'=' * 70}")
    print(f"  RF Behavioral AUC:    {rf_auc:.4f}  AP: {rf_ap:.4f}")
    print(f"  IF Anomaly AUC:       {iso_auc:.4f}")
    print(f"  P-curve Baseline AUC: {pcurve_auc:.4f}")

    print(f"\n  RF improvement over p-curve: {rf_auc - pcurve_auc:+.4f}")

    print(f"\nTop 10 behavioral features:")
    feature_ranking = []
    for rank, idx in enumerate(sorted_idx[:10], 1):
        name = FEATURE_NAMES[idx]
        imp = perm.importances_mean[idx]
        print(f"  {rank:2d}. {name:25s} | importance={imp:.4f}")
        feature_ranking.append({"rank": rank, "feature": name, "importance": round(float(imp), 4)})

    # Verdict
    if rf_auc > pcurve_auc + 0.05:
        verdict = f"POSITIVE — behavioral features beat p-curve by {rf_auc - pcurve_auc:.4f} AUC"
    elif rf_auc > pcurve_auc:
        verdict = f"MARGINAL — behavioral features slightly better ({rf_auc - pcurve_auc:+.4f})"
    else:
        verdict = f"NEGATIVE — p-curve baseline is sufficient; behavioral transfer adds no value"

    print(f"\nVERDICT: {verdict}")

    elapsed = time.time() - t0
    print(f"Total time: {elapsed:.1f}s")

    # Save
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "experiment": "H23_phacking_behavioral",
        "n_studies_per_class": n_studies,
        "phack_strategies": strategy_names,
        "rf_behavioral_auc": round(rf_auc, 4),
        "rf_behavioral_ap": round(rf_ap, 4),
        "if_anomaly_auc": round(iso_auc, 4),
        "pcurve_baseline_auc": round(pcurve_auc, 4),
        "rf_vs_pcurve_delta": round(rf_auc - pcurve_auc, 4),
        "verdict": verdict,
        "feature_ranking": feature_ranking,
        "elapsed_s": round(elapsed, 1),
    }
    out_path = RESULTS_DIR / "h23_results.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Results saved: {out_path}")


if __name__ == "__main__":
    main()
