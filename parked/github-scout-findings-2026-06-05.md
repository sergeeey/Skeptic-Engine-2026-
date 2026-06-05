# GitHub Scout Findings — Skeptic Engine (2026-06-05)

**Revival Trigger:** 2026-06-20 + GeoScan delivered  
**Цель:** Импорт golden-set harness + усиление методов

---

## 🔴 Priority 1 — Real Fraud Ground Truth (узкое место)

### 1. [Fraud-Detection-Handbook/fraud-detection-handbook](https://github.com/Fraud-Detection-Handbook/fraud-detection-handbook)
- **Push:** 2026-06-04
- **Что:** Reproducible ML для credit card fraud — real-world labeled dataset
- **Действие:** Загрузить датасет → протестировать H24/H25 → сравнить AUC (synthetic vs real)
- **Файл:** `fraud_detection_handbook/Chapter_3_GettingStarted/fraud_detection_handbook_datasets.ipynb`
- **Научная валидность:** 6/10 → 8/10 после интеграции

### 2. [danielmoreira/sciint](https://github.com/danielmoreira/sciint)
- **Push:** 2026-05-27
- **Что:** Scientific integrity verification (image forgery)
- **Действие:** Прочитать `experimental_results/` → взять их validation approach
- **Риск:** Medium (другая модальность: image vs tabular)

---

## 🟢 Priority 2 — Ensemble Усиление (сильные места)

### 1. [yzhao062/pyod](https://github.com/yzhao062/pyod) — 8.7k stars
- **Push:** 2026-06-04
- **Что:** 60+ anomaly detectors, benchmark-backed
- **Действие:** `pip install pyod` → wrapper для H24/H25/H29 → ensemble voting
- **Файл:** `src/skeptic_toolkit/ensemble/pyod_wrapper.py`
- **Эффект:** Single-method → ensemble AUC boost

### 2. [erdogant/benfordslaw](https://github.com/erdogant/benfordslaw) + [milcent/benford_py](https://github.com/milcent/benford_py)
- **Что:** Battle-tested Benford implementations
- **Действие:** A/B test vs твоя H24 → заменить если точнее
- **Файл:** `experiments/h24_benford_scrna/benford.py`

---

## 🟡 Priority 3 — Cross-Domain Expansion (неочевидные ходы)

### 1. [chartgerink/ddfab](https://github.com/chartgerink/ddfab) — R package
- **Что:** Statistical tools для data fabrication detection (psychology)
- **Действие:** Прочитать [arxiv.org/pdf/1311.5517](https://arxiv.org/pdf/1311.5517) → портировать в Python
- **Файл:** `experiments/h31_statistical_forensics/ddfab_port.py`
- **Peer-review:** [Tools of the data detective (2025)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12121900/)

### 2. [phillipecardenuto/upm](https://github.com/phillipecardenuto/upm)
- **Push:** 2025-04-25
- **Что:** Paper mill detection (text fraud)
- **Действие:** Ensemble data fraud (H24/H25) + text fraud (UPM)
- **Файл:** `experiments/h33_text_fraud/`

### 3. [numbersprotocol/awesome-data-integrity](https://github.com/numbersprotocol/awesome-data-integrity)
- **Что:** Data integrity methods (blockchain, IOTA)
- **Действие:** Cryptographic audit trail для научных данных
- **Long-term:** Blockchain-backed integrity claims

---

## 📊 Scoring Summary

| Репо | Score | Push | Domain | Risk |
|---|---|---|---|---|
| Fraud-Detection-Handbook | 9/10 | 2026-06-04 | Real fraud | Low |
| pyod | 10/10 | 2026-06-04 | Ensemble | Low |
| sciint | 8/10 | 2026-05-27 | Scientific integrity | Medium |
| ddfab | 9/10 | ? | Statistical forensics | Medium |
| upm | 9/10 | 2025-04-25 | Paper mills | Medium |
| benfordslaw | 8/10 | Recent | Benford | Low |
| DGFraud | 7/10 | 2026-05-29 | Graph-based | Medium |

---

## 💡 Execution Plan (post-2026-06-20)

### Phase 1 (8 hours) — Golden-Set Harness [REQUIRED]
1. Import [Fraud-Detection-Handbook](https://github.com/Fraud-Detection-Handbook/fraud-detection-handbook) dataset
2. Test H24/H25 on real fraud (not synthetic)
3. Update scientific validity: 6/10 → 8/10
4. Document in `experiments/validation/real_fraud_baseline.md`

### Phase 2 (6 hours) — Ensemble Boost [OPTIONAL]
1. Integrate [pyod](https://github.com/yzhao062/pyod)
2. Ensemble: Benford + AE + Syndrome + 5 PyOD detectors
3. Benchmark single vs ensemble AUC
4. File: `src/skeptic_toolkit/ensemble/pyod_wrapper.py`

### Phase 3 (12 hours) — Cross-Domain [OPTIONAL]
1. Port [ddfab](https://github.com/chartgerink/ddfab) methods (R → Python)
2. Integrate [upm](https://github.com/phillipecardenuto/upm) paper mill detection
3. New niche: text fraud + data fraud in one system
4. File: `experiments/h31_statistical_forensics/`, `experiments/h33_text_fraud/`

---

**Tracy Rule:** Phase 1 FIRST. Phases 2-3 only AFTER Phase 1 complete.  
**Zero-Based Thinking:** Skeptic без real fraud validation = proof-of-concept. Phase 1 ликвидирует это.

---

**Source Links (MUST include):**
- [Fraud Detection Handbook](https://github.com/Fraud-Detection-Handbook/fraud-detection-handbook)
- [PyOD Library](https://github.com/yzhao062/pyod)
- [Scientific Integrity System](https://github.com/danielmoreira/sciint)
- [Data Fabrication Detection (R)](https://github.com/chartgerink/ddfab)
- [Paper Mill Detection](https://github.com/phillipecardenuto/upm)
- [Benford's Law Python](https://github.com/erdogant/benfordslaw)
- [Awesome Data Integrity](https://github.com/numbersprotocol/awesome-data-integrity)
- [Statistical Detection Paper](https://arxiv.org/pdf/1311.5517)
- [Tools of the Data Detective (2025)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12121900/)
- [Golden Datasets Guide](https://focusinsite.com/golden-datasets-why-the-future-of-ai-depends-on-high-fidelity-ground-truth/)
