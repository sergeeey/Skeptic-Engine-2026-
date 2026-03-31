from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from scipy.io import mmread
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

EXPERIMENT_DIR = Path(__file__).resolve().parents[2] / "experiments" / "h24_benford_scrna"
sys.path.insert(0, str(EXPERIMENT_DIR))

SCORE_CLIP = (-2.0, 4.0)


def load_count_matrix(path: Path) -> np.ndarray:
    """Load a count matrix from text (.csv/.tsv) or 10x Market Matrix (.mtx)."""
    suffix = path.suffix.lower()
    if suffix == ".mtx":
        matrix = mmread(str(path))
        return matrix.toarray().T.astype(np.int64)

    delimiter = "\t" if suffix in {".tsv", ".txt"} else ","
    data = np.loadtxt(path, delimiter=delimiter, skiprows=0)
    if data.ndim == 1:
        raise ValueError("Count matrix must have at least one row and column.")
    return data.astype(np.int64)


def _scaled_mean_score(features: np.ndarray, *, clip: tuple[float, float] = SCORE_CLIP) -> float:
    if features.size == 0:
        return clip[0]
    scaled = StandardScaler().fit_transform(features)
    return float(np.clip(scaled.mean(), clip[0], clip[1]))


def _normalize_score(score: float, *, clip: tuple[float, float] = SCORE_CLIP) -> float:
    min_v, max_v = clip
    if max_v == min_v:
        return 0.0
    return float(np.clip((score - min_v) / (max_v - min_v), 0.0, 1.0))


def _load_reference_matrix(reference: Path | None) -> tuple[np.ndarray, str]:
    """Return the reference matrix used for scoring plus a descriptive source."""
    from run_h24 import _download_pbmc3k, _load_count_matrix

    if reference:
        if not reference.exists():
            raise FileNotFoundError(f"Reference file not found: {reference}")
        matrix = load_count_matrix(reference)
        return matrix, str(reference)

    mtx_dir = _download_pbmc3k()
    matrix = _load_count_matrix(mtx_dir)
    return matrix, str(mtx_dir)


def _fusion_probability(
    real_features: np.ndarray, candidate_features: np.ndarray
) -> tuple[float, np.ndarray]:
    """Train logistic regression on the fused features and return mean fake probability."""
    if len(candidate_features) == 0:
        return 0.0, np.array([])
    X = np.vstack([real_features, candidate_features])
    y = np.concatenate([np.zeros(len(real_features)), np.ones(len(candidate_features))])

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    candidate_scaled = scaler.transform(candidate_features)
    model = LogisticRegression(max_iter=2000, random_state=42)
    model.fit(X_scaled, y)
    probs = model.predict_proba(candidate_scaled)[:, 1]
    return float(np.mean(probs)), probs


def compute_scores(
    candidate_matrix: np.ndarray, reference_matrix: np.ndarray
) -> dict[str, float | np.ndarray]:
    from digit_features import extract_features_per_sample
    from isolation_forest import cell_level_features, score_anomalies, train_isolation_forest

    candidate_benford = extract_features_per_sample(candidate_matrix)
    reference_benford = extract_features_per_sample(reference_matrix)
    candidate_cell = cell_level_features(candidate_matrix)
    reference_cell = cell_level_features(reference_matrix)

    candidate_chi2 = candidate_benford[:, 19:]
    benford_score = _scaled_mean_score(candidate_chi2)
    cell_score = _scaled_mean_score(candidate_cell)

    if_model = train_isolation_forest(reference_cell)
    reference_if_scores = score_anomalies(if_model, reference_cell)
    candidate_if_scores = score_anomalies(if_model, candidate_cell)
    if_score = float(np.clip(-candidate_if_scores.mean(), SCORE_CLIP[0], SCORE_CLIP[1]))

    reference_fusion = np.hstack(
        [np.hstack([reference_benford, reference_cell]), reference_if_scores.reshape(-1, 1)]
    )
    candidate_fusion = np.hstack(
        [np.hstack([candidate_benford, candidate_cell]), candidate_if_scores.reshape(-1, 1)]
    )

    fusion_prob, candidate_probs = _fusion_probability(reference_fusion, candidate_fusion)
    norm_benford = _normalize_score(benford_score)
    norm_cell = _normalize_score(cell_score)
    norm_if = _normalize_score(if_score)

    # WHY: fusion_prob already integrates all features via LogReg.
    # Averaging with raw component scores dilutes the signal (caused false negatives on NB fabrication).
    final_score = float(fusion_prob)

    return {
        "benford_score": benford_score,
        "cell_score": cell_score,
        "if_score": if_score,
        "fusion_probability": fusion_prob,
        "fusion_probs": candidate_probs,
        "normalized_benford": norm_benford,
        "normalized_cell": norm_cell,
        "normalized_if": norm_if,
        "final_score": final_score,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Skeptic Toolkit MVP — H24-inspired fusion risk scanner for scRNA-seq matrices."
    )
    parser.add_argument(
        "matrix", type=Path, help="Path to candidate count matrix (.mtx/.csv/.tsv)."
    )
    parser.add_argument(
        "--reference",
        type=Path,
        help="Optional real count matrix to compare against (default: PBMC3k download).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.55,
        help="Final fabrication risk threshold (0-1) above which risk is flagged.",
    )
    args = parser.parse_args()

    if not args.matrix.exists():
        parser.error(f"File not found: {args.matrix}")

    candidate_matrix = load_count_matrix(args.matrix)
    reference_matrix, reference_source = _load_reference_matrix(args.reference)

    scores = compute_scores(candidate_matrix, reference_matrix)
    fusion_probs = (
        scores["fusion_probs"] if isinstance(scores["fusion_probs"], np.ndarray) else np.array([])
    )

    print(f"Candidate matrix: {args.matrix}")
    print(f"Reference source: {reference_source}")
    print(f"Candidate shape: {candidate_matrix.shape[0]} cells × {candidate_matrix.shape[1]} genes")
    print(f"Reference shape: {reference_matrix.shape[0]} cells × {reference_matrix.shape[1]} genes")
    print("\nComponent scores (raw / normalized):")
    print(f"- Benford chi²: {scores['benford_score']:.3f} / {scores['normalized_benford']:.3f}")
    print(f"- Cell-level anomaly: {scores['cell_score']:.3f} / {scores['normalized_cell']:.3f}")
    print(f"- Isolation Forest: {scores['if_score']:.3f} / {scores['normalized_if']:.3f}")
    if fusion_probs.size:
        print(
            f"- Fusion logistic-reg probability (mean): {scores['fusion_probability']:.3f}"
            f" (range {fusion_probs.min():.3f}–{fusion_probs.max():.3f})"
        )
    else:
        print("- Fusion logistic-reg probability (no candidate cells)")

    from skeptic_toolkit.verdict import make_verdict

    verdict = make_verdict(scores["final_score"], threshold=args.threshold)
    print(f"\nFinal fabrication risk score: {scores['final_score']:.3f}")
    print(f"Verdict: {verdict}")


if __name__ == "__main__":
    main()
