# H31 — Unified Anomaly Score (UAS)

## Hypothesis
A unified anomaly score combining signals from multiple detection methods
(Benford, autoencoder, behavioral, syndrome, metadata) provides better
discrimination of anomalous scientific datasets than any single method alone.

## Signals

| Signal | Source | Description |
|---|---|---|
| `benford` | H24 | Benford digit deviation |
| `ae_reconstruction` | H25 | Autoencoder reconstruction error |
| `behavioral` | H23 | P-hacking behavioral features |
| `syndrome` | H29 | Constraint violation score |
| `pvalue_cluster` | H27 | P-value clustering anomaly |
| `metadata` | H28 | Metadata anomaly features |
| `cross_dataset` | H26 | Cross-dataset inconsistency |

## Method

1. Collect per-dataset scores from each experiment
2. Normalize each signal to [0,1] using min-max scaling
3. Compute weighted ensemble: `UAS = Σ(w_i × signal_i)`
4. Validate on H30 retracted data (ground truth "anomalous")

## Validation

- **Positive control:** H30 retracted GEO datasets (should score high)
- **Negative control:** Clean PBMC3k, GTEx healthy tissues (should score low)
- **Target:** AUC > 0.80 on retracted vs clean classification

## Files

- `run_h31.py` — main experiment script
- `signal_collector.py` — collects and normalizes signals
- `results/h31_results.json` — experiment results
