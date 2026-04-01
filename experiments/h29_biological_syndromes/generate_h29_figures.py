"""H29 Figure Generation -- syndrome heatmap + module histogram.

Generates publication-quality figures for H29 results.

Usage:
    python experiments/h29_biological_syndromes/generate_h29_figures.py
"""
import json, sys, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results"


def plot_syndrome_comparison(results_path: Path, out_path: Path) -> None:
    """Bar chart comparing syndrome scores across fabrication methods."""
    data = json.loads(results_path.read_text())
    labels = [r["label"] for r in data["results"]]
    pw = [r["pairwise_violation_score"] for r in data["results"]]
    # Handle both old format (without module) and new
    mod = [r.get("module_violation_score", 0) for r in data["results"]]
    res = [r.get("residual_violation_score", 0) for r in data["results"]]

    x = np.arange(len(labels))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - width, pw, width, label="Pairwise", color="#2196F3")
    ax.bar(x, mod, width, label="Module", color="#FF9800")
    ax.bar(x + width, res, width, label="Residual", color="#4CAF50")

    ax.set_ylabel("Violation Score")
    ax.set_title("H29 Syndrome Decomposition by Fabrication Method")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15)
    ax.legend()
    ax.set_ylim(0, max(max(pw), max(mod), max(res), 0.1) * 1.2)

    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {out_path}")


def plot_module_violation_histogram(results_path: Path, out_path: Path) -> None:
    """Histogram of module violation counts from module-breaking test."""
    data = json.loads(results_path.read_text())

    fig, axes = plt.subplots(1, len(data["results"]), figsize=(4 * len(data["results"]), 4),
                              squeeze=False)

    for i, r in enumerate(data["results"]):
        ax = axes[0][i]
        test_name = r["test"]
        syndrome = r.get("syndrome", 0)
        mod_viol = r.get("module_violation", 0)

        ax.bar([0, 1], [syndrome, mod_viol], color=["#2196F3", "#FF9800"])
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Syndrome", "Module viol."])
        ax.set_title(test_name, fontsize=9)
        ax.set_ylim(0, max(0.7, syndrome * 1.2, mod_viol * 1.2))

    plt.suptitle("H29 Module-Breaking Test Results", fontsize=12)
    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {out_path}")


def plot_portability_comparison(results_path: Path, out_path: Path) -> None:
    """Comparison of syndrome scores: proteomics vs scRNA-seq."""
    data = json.loads(results_path.read_text())
    labels = [r["label"] for r in data["results"]]
    scores = [r["syndrome_score"] for r in data["results"]]
    classes = [r.get("violation_class", "unknown") for r in data["results"]]

    colors = {"clean": "#4CAF50", "technical_noise": "#FFC107",
              "local_break": "#FF9800", "structural_anomaly": "#F44336", "unknown": "#9E9E9E"}

    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(labels, scores, color=[colors.get(c, "#9E9E9E") for c in classes])
    ax.set_ylabel("Syndrome Score")
    ax.set_title("H29 Portability: Syndrome on scRNA-seq (PBMC3k)")
    ax.set_xticklabels(labels, rotation=15)

    # Legend for violation classes
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=colors[c], label=c)
                       for c in ["clean", "technical_noise", "structural_anomaly"]
                       if c in classes]
    ax.legend(handles=legend_elements, loc="upper left")

    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {out_path}")


def main():
    print("Generating H29 figures...")

    # 1. Syndrome comparison (from h29_results.json)
    r1 = RESULTS / "h29_results.json"
    if r1.exists():
        plot_syndrome_comparison(r1, RESULTS / "h29_syndrome_comparison.png")

    # 2. Module-breaking histogram
    r2 = RESULTS / "h29_module_breaking.json"
    if r2.exists():
        plot_module_violation_histogram(r2, RESULTS / "h29_module_histogram.png")

    # 3. Portability comparison
    r3 = RESULTS / "h29_h24_portability.json"
    if r3.exists():
        plot_portability_comparison(r3, RESULTS / "h29_portability.png")

    print("Done.")


if __name__ == "__main__":
    main()
