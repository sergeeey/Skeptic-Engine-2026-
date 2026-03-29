# Toolkit MVP — Statistical Artifact Screening Tool

## Purpose

Deliver a runnable CLI that takes a single-cell count matrix, runs the full H24 fusion pipeline (Benford digits + cell-level features + Isolation Forest), and produces an artifact risk score plus intermediate diagnostics. The tool screens for non-physical statistical patterns — it does not claim to detect deliberate fraud. Elevated scores indicate anomalous digit or structural distributions that warrant expert review.

## Usage

1. Install dependencies (or install the project in editable mode).
   ```
   python -m pip install -e .
   ```
2. Run via the console script:
   ```
   skeptic-toolkit <path/to/matrix> [--reference <real-matrix>] [--threshold 0.5]
   ```

Supported formats:

- `.mtx` (10x Genomics Market Matrix, transposed internally)
- `.csv`, `.tsv`, `.txt` (tab- or comma-delimited)

Optional flags:

- `--reference <path>` — override the default PBMC3k reference matrix with another real dataset (must follow the same format as the candidate).
- `--threshold <float>` — final fabrication risk threshold between 0 and 1 (default 0.5, tuned to H24 fusion).

## What it outputs

- sample/gene counts summary for both candidate and reference
- raw and normalized scores from Benford, cell-level, and isolation-forest features
- fusion logistic regression probability (mean + range) and final composite risk score
- verdict text (`fabrication risk appears elevated` vs `signals are within expected bounds`)

## Next steps

1. Smoke-test the toolkit using PBMC3k as both reference and candidate (see below) to ensure the fusion score is stable.
2. Wrap the script in a lightweight CLI distribution for collaborators.
3. Record each run’s component scores in the dashboard/report so the fusion pipeline is auditable.

## Smoke test (example)

```
skeptic-toolkit experiments/h24_benford_scrna/data/filtered_gene_bc_matrices/hg19/matrix.mtx
```

The command downloads (or reuses) PBMC3k as the reference, then scores the same matrix as if it were a suspect edge case. Adjust `--threshold` if you want to reflect tighter or looser risk tolerances.
