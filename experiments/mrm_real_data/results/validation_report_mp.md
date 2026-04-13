# SE-MRM Validation Report — Real Materials Project Data

## Date: 2026-04-06

---

## Executive Summary

**Calibration test on 130 real materials from Materials Project API.**

| Metric | Value |
|---|---|
| **Total candidates** | 130 (50 stable + 30 marginal + 50 unstable) |
| **Overall accuracy** | **63.8% (83/130)** |
| **Unstable detection** | **100% (50/50)** ✅ |
| **Stable detection** | 40% (20/50) |
| **Marginal detection** | 43% (13/30) |

---

## Data Sources

| Source | Count | Filter |
|---|---|---|
| Materials Project (stable) | 50 | eah < 0.02, fe < -0.5, no radioactive |
| Materials Project (marginal) | 30 | 0.1 < eah < 0.3, no radioactive |
| Materials Project (unstable) | 50 | eah > 0.5 |

**Radioactive elements excluded:** Ac, Tc, Pm, Po, At, Rn, Fr, Ra, Th, Pa, Np, Pu, Am, Cm, Bk, Cf, Es, Fm, Md, No, Lr

---

## Results Detail

### Stable Materials (expected: promote)

| Metric | Value |
|---|---|
| Avg score | 0.547 |
| Promoted | 20 (40%) |
| Held | 30 (60%) |
| Killed | 0 (0%) |

**Misclassified as hold:** Complex compounds like Ag(W₃Br₇)₂, Ag₂₅(BiO₆)₃ — these have moderate formation energies and complex structures that lower stability scores.

### Marginal Materials (expected: hold)

| Metric | Value |
|---|---|
| Avg score | 0.466 |
| Promoted | 0 (0%) |
| Held | 13 (43%) |
| Killed | 17 (57%) |

**Misclassified as kill:** Simple compounds like Ag₂O, Ag₂HgI₄ with higher eah values that push them into kill range.

### Unstable Materials (expected: kill)

| Metric | Value |
|---|---|
| Avg score | 0.163 |
| Promoted | 0 (0%) |
| Held | 0 (0%) |
| Killed | 50 (100%) ✅ |

**Perfect detection!** All unstable materials correctly identified.

---

## Score Distribution

```
Stable:    ████████████████████████████████████████ 0.547
Marginal:  ██████████████████████████████████ 0.466
Unstable:  ████████████ 0.163
```

Clear separation: **stable > marginal > unstable** ✅

---

## Comparison: Synthetic vs Real Data

| Test | Dataset | Accuracy |
|---|---|---|
| Synthetic (CalibratedStub) | 17 candidates | **100%** |
| Embedded Reference Set | 100 candidates | 63% |
| **Materials Project (real)** | **130 candidates** | **63.8%** |

---

## Conclusions

### What Works
- ✅ **Unstable detection: 100%** — the module perfectly identifies materials that will fail
- ✅ **Score separation: clear** — stable (0.547) > marginal (0.466) > unstable (0.163)
- ✅ **No false positives for unstable** — 0 unstable materials promoted
- ✅ **No false kills for stable** — 0 stable materials killed

### What Needs Improvement
- ⚠️ **Stable promote rate: 40%** — many stable materials get "held" instead of "promoted"
- ⚠️ **Marginal hold rate: 43%** — many marginal materials get "killed" instead of "held"
- ⚠️ **Threshold tuning needed** — the promote/hold boundary is too strict

### Next Steps
1. **Lower promote threshold** from 0.55 to ~0.50 to capture more stable materials
2. **Adjust hold lower bound** to reduce marginal→kill misclassifications
3. **Add more features** (bond valence, coordination analysis) to improve scoring
4. **Test on PhononBench dataset** for ground-truth dynamical stability labels
5. **Integrate real MatterSim backend** for actual physics-based simulation

---

## Files

- `data/mp_real_candidates.json` — 130 Materials Project candidates
- `results/real_calibration_results.json` — detailed calibration data
- `validation_report.md` — this report
