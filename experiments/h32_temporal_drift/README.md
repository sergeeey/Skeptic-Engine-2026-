# H32 — Temporal P-Hacking Detection

## Hypothesis
Authors/labs engaged in p-hacking exhibit **temporal drift** in their p-value
distributions: an increasing concentration of p-values just below 0.05 over time,
coupled with declining effect sizes and rising "significance fatigue."

## Signals

| Signal | Description |
|---|---|
| `frac_just_below_05` | Fraction of p-values in [0.04, 0.05) per time window |
| `mean_p_drift` | Slope of mean p-value over time |
| `success_rate_drift` | Slope of fraction significant over time |
| `effect_size_decline` | Decline in reported effect sizes over time |
| `pvalue_clustering` | Increase in p-value clustering near 0.05 |

## Method

1. Extract p-value time series from author/lab publication history
2. Bin by publication year (or submission date)
3. Compute behavioral features per bin (from H23 feature set)
4. Fit linear trend to each feature over time
5. Flag authors with significant temporal drift (p < 0.01 for any trend)

## Data Sources

- **PubMed**: Extract p-values from abstracts via regex
- **ClinicalTrials.gov**: Structured p-values from results
- **Reproducibility Project**: Known p-hacking cases as positive controls

## Validation

- **Positive control:** Authors from known p-hacking scandals
- **Negative control:** Preregistered studies (should show no drift)
- **Target:** AUC > 0.75 on known cases

## Files

- `run_h32.py` — main experiment script
- `temporal_features.py` — feature extraction from time series
- `drift_detector.py` — trend analysis and flagging
- `results/h32_results.json` — experiment results
