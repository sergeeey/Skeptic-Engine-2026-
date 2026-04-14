# H38 — Causal Refutation via DoWhy Integration

## Hypothesis
Causal claims in scientific papers can be invalidated by refutation tests, and these tests are strengthened by Skeptic Engine's data integrity scores.

## Method
1. **Data:** Synthetic dataset simulating "Method X improves Accuracy Y", confounded by "Data Size".
2. **Model:** DoWhy `CausalModel` with Backdoor criterion.
3. **Refutation:**
   - **Placebo Treatment:** Replaces treatment with random noise. Effect should drop to zero.
   - **Add Unobserved Common Cause:** Adds a hidden confounder. Effect should change if the claim is sensitive.
4. **Integration:** Skeptic Engine's Syndrome Score acts as a baseline penalty. `Causal Fragility = max(Refutation_Score, Syndrome_Score)`.

## Results (Simulation Mode)
- **Original Effect:** 0.500
- **Placebo Effect:** 0.030 (Claim passes — effect is not random noise).
- **Effect w/ Hidden Confounder:** 0.278 (Claim is sensitive — effect drops by ~45%).
- **Causal Fragility:** 0.250 (Moderate).

## Verdict
The causal claim is partially robust. While it passes the Placebo test, it is sensitive to hidden confounders, consistent with the known confounding structure of the data. Skeptic Engine's syndrome score (0.196) adds an extra layer of skepticism based on data anomalies.

## Files
- `run_h38.py`: Main experiment script (uses DoWhy if available, else simulation).
- `results/h38_results.json`: Experiment output.
