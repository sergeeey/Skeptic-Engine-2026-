# H4 Verification Note

## Candidate

`H4` — TDA signature of cancer drug resistance.

## Verification Date

2026-03-25

## Status

`partially_verified`

## Verified Findings

1. TDA is already established in oncology for prognosis, treatment-response-related analysis, and cancer subtype discovery.
2. A 2022 ISMB poster described `Transition Topological Data Analysis (T2DA)` on melanoma single-cell RNA-seq and explicitly reported identifying transition genes from drug-responsive to drug-resistant states.
3. A 2023 PLOS Computational Biology paper used TDA to predict relapse in pediatric acute lymphoblastic leukemia, showing that TDA can already support clinically relevant recurrence-risk prediction in cancer.
4. The ScPCA / OpenScPCA ecosystem is a real and accessible public single-cell pediatric cancer resource, but the retrieved documentation does not by itself establish that it contains the treatment-response or drug-resistance labels needed for a clean H4 benchmark.
5. A concrete open resistance-labeled melanoma single-cell benchmark does exist: `GSE164897` contains `26,979` cells from four explicit treatment conditions in the A375 melanoma model, including untreated/sensitive cells and single- or double-drug-resistant states.
6. A concrete public immunotherapy-response melanoma benchmark also exists: `GSE120575` contains `16,291` CD45+ single cells from `48` tumor biopsies of `32` melanoma patients treated with checkpoint inhibitors, with responder/non-responder labels reused by later studies.
7. A broad patient-derived discovery layer now also exists via `scCT-DB`, which reports `266` paired pre-/post-treatment single-cell datasets, `195` with primary response information, `22` with acquired resistance, and `41` longitudinal datasets with at least three timepoints.

## Practical Reading

### What this means

The broad claim "TDA for cancer drug resistance is untouched" is not defensible.

### What still appears open

A narrower candidate may still survive:

- TDA-based detection of early resistant-state transitions in well-labeled single-cell treatment datasets
- TDA features that add value beyond standard embeddings, pseudotime, or velocity baselines in resistance prediction

These remain inferences from the retrieved sources, not proven literature gaps.

## Novelty Reassessment

- Original seed framing: high novelty
- Revised assessment: medium novelty

Reason:

- Oncology already has meaningful TDA prior art.
- Drug-resistance-adjacent single-cell TDA prior art exists at least at poster level.
- Relapse prediction with TDA in cancer is already published.

## Recommended Reframe

Replace the old wording:

- "TDA signature of cancer drug resistance"

With a narrower wording:

- "TDA for early detection of resistant-state transitions in cancer single-cell data"

## Dataset Reassessment

### Confirmed

- The ScPCA Portal is a real public resource with downloadable processed single-cell data and metadata.
- `GSE164897` is a real open melanoma resistance scRNA-seq dataset and is directly suitable for a fast benchmark.
- `GSE120575` is a real open melanoma immunotherapy-response scRNA-seq dataset and is directly suitable for a patient-response benchmark.
- `scCT-DB` is a real searchable and downloadable resource for treatment-related patient-derived single-cell datasets with structured response metadata.

### Not yet confirmed

- Whether OpenScPCA alone provides suitable resistance-labeled cohorts for H4
- Whether the melanoma resistance data used in the 2022 T2DA report is the same reusable package as `GSE164897` or a separate benchmark route
- Which patient-derived dataset inside `scCT-DB` is the best first executable benchmark for H4

## Current Dataset Decision

The dataset question for `H4` is no longer "does any usable benchmark exist?" That is now verified.

The real decision is which benchmark tier to choose:

### Tier 1: Fast executable benchmark

- `GSE164897`
- melanoma targeted-therapy resistance
- explicit sensitive vs resistant states
- open and directly reusable

Main caveat:

- cell-line route, not patient-derived clinical resistance

### Tier 2: Patient-response benchmark

- `GSE120575`
- metastatic melanoma under checkpoint blockade
- responder / non-responder labels
- already reused by later prediction papers

Main caveat:

- response/resistance framing is clinically meaningful, but not a clean multi-timepoint transition benchmark

### Tier 3: Scalable patient-derived search space

- `scCT-DB`
- many paired and longitudinal datasets with structured treatment metadata

Main caveat:

- not a single benchmark by itself; still requires choosing one concrete dataset and ingestion route

## Next Verification Steps

1. Choose the first H4 benchmark route explicitly:
   - `GSE164897` for fast resistance-state benchmarking
   - or `GSE120575` / `scCT-DB` for patient-response benchmarking
2. Verify whether T2DA or equivalent methods have a full paper and public code/data beyond the IBM poster page.
3. Compare H4 against simpler baselines: PCA/UMAP + clustering, pseudotime, RNA velocity, or standard graph methods.
4. Keep `H4` in the top-5 queue only if the value-add over standard single-cell methods remains plausible after the dataset route is fixed.

## Sources

- IBM ISMB 2022 poster page: https://research.ibm.com/publications/uncovering-signals-of-cell-state-transition-using-topological-data-analysis-in-single-cell-data
- Applications of TDA in Oncology review: https://pmc.ncbi.nlm.nih.gov/articles/PMC8076640/
- PLOS Computational Biology relapse paper: https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1011329
- OpenScPCA data access docs: https://openscpca.readthedocs.io/en/stable/getting-started/accessing-resources/getting-access-to-data/
- ScPCA manuscript/data paper: https://alexslemonade.github.io/ScPCA-manuscript/
- Melanoma resistance trajectory paper with open dataset: https://pmc.ncbi.nlm.nih.gov/articles/PMC8763000/
- GEO accession summary for `GSE164897`: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE164897
- GEO accession summary for `GSE120575`: https://www.omicsdi.org/dataset/geo/GSE120575
- scCT-DB paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC12807622/
