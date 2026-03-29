"""Generate publication-quality figures for H24+H21 experiments.

Four figures:
  1. Within-dataset AUC comparison (4 methods × 3 fabrication types)
  2. Feature group importance by fabrication type
  3. Cross-dataset generalization heatmap
  4. Benford digit distribution: real vs fabricated (violin/bar)

Usage:
    python experiments/h24_benford_scrna/generate_figures.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

sys.path.insert(0, str(Path(__file__).resolve().parent))

RESULTS_DIR = Path(__file__).resolve().parent / "results"
FIGURES_DIR = Path(__file__).resolve().parent / "figures"


def _load_json(name: str) -> dict:
    return json.loads((RESULTS_DIR / name).read_text(encoding="utf-8"))


def figure1_within_dataset() -> None:
    """Bar chart: AUC by method × fabrication type."""
    data = _load_json("h24_h21_combined.json")

    methods = ["resample", "noise", "random_nb"]
    approaches = ["benford", "cell_features", "isolation_forest", "fusion"]
    labels = ["Benford (21)", "Cell-Level (8)", "IF-Only (1)", "Fusion (30)"]
    colors = ["#5C6BC0", "#26A69A", "#FFA726", "#EC407A"]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = np.arange(len(methods))
    width = 0.19

    for i, (approach, label, color) in enumerate(zip(approaches, labels, colors)):
        aucs = []
        for r in data["results"]:
            aucs.append(r[approach]["RF"]["auc"])
        bars = ax.bar(
            x + i * width, aucs, width, label=label, color=color, edgecolor="white", linewidth=0.5
        )
        for bar, auc in zip(bars, aucs):
            if auc < 0.99:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.01,
                    f"{auc:.2f}",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )

    ax.set_ylabel("AUC-ROC", fontsize=12)
    ax.set_title(
        "Within-Dataset Fabrication Detection (PBMC3k, RF)", fontsize=13, fontweight="bold"
    )
    ax.set_xticks(x + 1.5 * width)
    ax.set_xticklabels(
        [
            "Resample\n(correlation-destroying)",
            "Noise*\n(sparsity-changing)",
            "Random NB\n(distribution-generating)",
        ],
        fontsize=10,
    )
    ax.set_ylim(0.5, 1.08)
    ax.axhline(y=0.80, color="#E53935", linestyle="--", alpha=0.6, linewidth=1)
    ax.text(2.8, 0.81, "Kill threshold", color="#E53935", fontsize=8, alpha=0.7)
    ax.legend(loc="lower right", fontsize=9, framealpha=0.9)
    ax.annotate(
        "*Noise AUC=1.00 reflects trivial\nsparsity shift (2.6%→21.4%),\nnot meaningful detection",
        xy=(1, 1.0),
        fontsize=7,
        color="gray",
        ha="center",
        va="bottom",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8),
    )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    path = FIGURES_DIR / "fig1_within_dataset_auc.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.savefig(path.with_suffix(".pdf"), bbox_inches="tight")
    print(f"Figure 1 saved: {path}")
    plt.close()


def figure2_feature_importance() -> None:
    """Horizontal bar chart: feature group importance per fabrication type."""
    data = _load_json("h24_feature_importance.json")

    group_order = [
        "cell_level",
        "benford_chi2",
        "benford_first_digit",
        "benford_second_digit",
        "if_score",
    ]
    group_labels = [
        "Cell-Level (8)",
        "Benford χ² (2)",
        "Benford 1st Digit (9)",
        "Benford 2nd Digit (10)",
        "IF Score (1)",
    ]
    colors = ["#26A69A", "#7E57C2", "#5C6BC0", "#42A5F5", "#FFA726"]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)
    fab_labels = ["Resample", "Noise*", "Random NB"]

    for idx, result in enumerate(data["results"]):
        ax = axes[idx]
        groups = result["group_importance"]
        values = [groups.get(g, 0) for g in group_order]

        bars = ax.barh(group_labels, values, color=colors, edgecolor="white", linewidth=0.5)
        ax.set_xlabel("Permutation Importance (ΔAUC)", fontsize=10)
        ax.set_title(fab_labels[idx], fontsize=12, fontweight="bold")
        ax.invert_yaxis()

        for bar, val in zip(bars, values):
            if val > 0.001:
                ax.text(
                    bar.get_width() + 0.001,
                    bar.get_y() + bar.get_height() / 2,
                    f"{val:.3f}",
                    va="center",
                    fontsize=8,
                )

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    if all(v == 0 for v in [data["results"][1]["group_importance"].get(g, 0) for g in group_order]):
        axes[1].text(
            0.5,
            0.5,
            "All importances = 0\n(model already perfect;\nremoving any feature\ndoes not degrade AUC)",
            transform=axes[1].transAxes,
            ha="center",
            va="center",
            fontsize=9,
            color="gray",
            style="italic",
        )

    plt.suptitle("Feature Group Importance by Fabrication Type", fontsize=14, fontweight="bold")
    plt.tight_layout()
    path = FIGURES_DIR / "fig2_feature_importance.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.savefig(path.with_suffix(".pdf"), bbox_inches="tight")
    print(f"Figure 2 saved: {path}")
    plt.close()


def figure3_cross_dataset() -> None:
    """Heatmap: cross-dataset AUC."""
    data = _load_json("h24_h21_crossval.json")

    methods = [r["method"] for r in data["results"]]
    scenarios = ["Within\nPBMC3k", "Within\nKang2018", "PBMC3k\n→Kang", "Kang\n→PBMC3k"]

    matrix = np.zeros((len(methods), 4))
    for i, r in enumerate(data["results"]):
        matrix[i, 0] = r["within_pbmc3k"]["auc"]
        matrix[i, 1] = r["within_kang2018"]["auc"]
        matrix[i, 2] = r["cross_pbmc_to_kang"]["auc"]
        matrix[i, 3] = r["cross_kang_to_pbmc"]["auc"]

    fig, ax = plt.subplots(figsize=(8, 4))
    im = ax.imshow(matrix, cmap="RdYlGn", vmin=0.0, vmax=1.0, aspect="auto")

    ax.set_xticks(range(4))
    ax.set_xticklabels(scenarios, fontsize=10)
    ax.set_yticks(range(len(methods)))
    ax.set_yticklabels(["Resample", "Noise*", "Random NB"], fontsize=11)

    for i in range(len(methods)):
        for j in range(4):
            val = matrix[i, j]
            color = "white" if val < 0.5 or val > 0.9 else "black"
            ax.text(
                j,
                i,
                f"{val:.3f}",
                ha="center",
                va="center",
                fontsize=11,
                fontweight="bold",
                color=color,
            )

    # Vertical line separating within vs cross
    ax.axvline(x=1.5, color="white", linewidth=3)
    ax.text(
        0.5, -0.7, "Within-Dataset", ha="center", fontsize=10, fontweight="bold", color="#2E7D32"
    )
    ax.text(
        2.5, -0.7, "Cross-Dataset", ha="center", fontsize=10, fontweight="bold", color="#C62828"
    )

    cbar = plt.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("AUC-ROC", fontsize=10)

    ax.set_title("Cross-Dataset Generalization: PBMC3k ↔ Kang2018", fontsize=13, fontweight="bold")
    plt.tight_layout()
    path = FIGURES_DIR / "fig3_cross_dataset_heatmap.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.savefig(path.with_suffix(".pdf"), bbox_inches="tight")
    print(f"Figure 3 saved: {path}")
    plt.close()


def figure4_digit_distributions() -> None:
    """Bar chart: real vs fabricated first-digit distributions."""
    from scipy.io import mmread
    from digit_features import extract_features_per_sample, BENFORD_FIRST
    from fabrication import fabricate_resample, fabricate_random_nb

    sparse = mmread(
        str(
            Path(__file__).resolve().parent
            / "data"
            / "filtered_gene_bc_matrices"
            / "hg19"
            / "matrix.mtx"
        )
    )
    real = sparse.toarray().T.astype(np.int64)

    fake_resample = fabricate_resample(real, rng=np.random.default_rng(2026))
    fake_nb = fabricate_random_nb(real, rng=np.random.default_rng(2026))

    feat_real = extract_features_per_sample(real)
    feat_resample = extract_features_per_sample(fake_resample)
    feat_nb = extract_features_per_sample(fake_nb)

    digits = np.arange(1, 10)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)

    # Panel A: Mean first-digit freq
    ax = axes[0]
    w = 0.25
    ax.bar(
        digits - w,
        feat_real[:, :9].mean(axis=0),
        w,
        label="Real",
        color="#26A69A",
        edgecolor="white",
    )
    ax.bar(
        digits,
        feat_resample[:, :9].mean(axis=0),
        w,
        label="Resample",
        color="#5C6BC0",
        edgecolor="white",
    )
    ax.bar(
        digits + w,
        feat_nb[:, :9].mean(axis=0),
        w,
        label="Random NB",
        color="#EC407A",
        edgecolor="white",
    )
    ax.plot(digits, BENFORD_FIRST, "k--", alpha=0.5, label="Benford expected", linewidth=1.5)
    ax.set_xlabel("First Digit", fontsize=11)
    ax.set_ylabel("Mean Frequency", fontsize=11)
    ax.set_title("A. Mean First-Digit Distribution", fontsize=12, fontweight="bold")
    ax.legend(fontsize=8)
    ax.set_xticks(digits)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Panel B: Variance of first-digit freq across cells
    ax = axes[1]
    ax.bar(
        digits - w / 2,
        feat_real[:, :9].var(axis=0),
        w,
        label="Real",
        color="#26A69A",
        edgecolor="white",
    )
    ax.bar(
        digits + w / 2,
        feat_resample[:, :9].var(axis=0),
        w,
        label="Resample",
        color="#5C6BC0",
        edgecolor="white",
    )
    ax.set_xlabel("First Digit", fontsize=11)
    ax.set_ylabel("Variance Across Cells", fontsize=11)
    ax.set_title(
        "B. Digit Variance Collapse\n(Resample Homogenizes Cells)", fontsize=12, fontweight="bold"
    )
    ax.legend(fontsize=8)
    ax.set_xticks(digits)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Panel C: Chi² distribution
    ax = axes[2]
    bins = np.linspace(0, 2.5, 40)
    ax.hist(feat_real[:, 19], bins=bins, alpha=0.7, label="Real", color="#26A69A", density=True)
    ax.hist(
        feat_resample[:, 19], bins=bins, alpha=0.7, label="Resample", color="#5C6BC0", density=True
    )
    ax.hist(feat_nb[:, 19], bins=bins, alpha=0.7, label="Random NB", color="#EC407A", density=True)
    ax.set_xlabel("χ² vs Benford (first digit)", fontsize=11)
    ax.set_ylabel("Density", fontsize=11)
    ax.set_title("C. Chi-Squared Divergence\nfrom Benford Expected", fontsize=12, fontweight="bold")
    ax.legend(fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.suptitle(
        "Benford Digit Signatures: Real vs Fabricated scRNA-seq",
        fontsize=14,
        fontweight="bold",
        y=1.02,
    )
    plt.tight_layout()
    path = FIGURES_DIR / "fig4_digit_distributions.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.savefig(path.with_suffix(".pdf"), bbox_inches="tight")
    print(f"Figure 4 saved: {path}")
    plt.close()


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    print("Generating publication-quality figures...\n")

    figure1_within_dataset()
    figure2_feature_importance()
    figure3_cross_dataset()
    figure4_digit_distributions()

    print(f"\nAll figures saved to: {FIGURES_DIR}")


if __name__ == "__main__":
    main()
