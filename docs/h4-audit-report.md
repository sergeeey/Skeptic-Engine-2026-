# H4 Audit Report — GSE164897

## Date

2026-03-26

## Purpose

Document the audit-ready metadata for the default H4 route (`GSE164897`) so that any raw ingestion starts from a validated contract.

## Key Facts

- accession: `GSE164897`
- status: `contract_locked_pending_audit`
- dataset type: single-cell expression profiling (10x Genomics v2)
- unit of analysis: `single_cell`, evaluation level `sample_group_primary_cell_level_secondary`
- split unit: `sample_group`; planned group keys: `sample_id`, `condition_label`, `replicate_id`
- leakage keys: `cell_barcode`, `sample_id`, `condition_label`, `replicate_id`, `dataset_accession`
- label schema: binary resistance-state classification (`drug_resistant_state` vs `non_resistant_state`)
- sample count from metadata: `4` primary samples, ~27k cells total
- sample-level treatments (parsed from `characteristics_ch1`):
  1. `treatment: vemurafenib`
  2. `treatment: untreated`
  3. `treatment: vemurafenib + cobimetinib`
  4. `treatment: vemurafenib + trametinib`
- planned first baseline contract: compare resistant-state detection vs non-resistance per sample group/condition

## Audit Artifacts

- raw metadata download: `data/h4_audit/GSE164897_series_matrix.txt.gz`
- metadata summary (auto-generated): `data/h4_audit/GSE164897_metadata.json`
- extractor script: `scripts/h4_gse164897_audit.py`
- script output confirms presence of the planned split/leakage keys and enumerates sample treatments; it also records the spec-derived contract.

## Outstanding Checks

1. Confirm that raw metadata files actually expose columns mapping to `sample_id`, `condition_label`, `replicate_id`.
2. Ensure sample-group splitting retains at least one independent group per treatment in train/val/test.
3. Decide whether to evaluate primarily at sample-group level with aggregated counts, or at cell level with careful leakage control.

## Next Work

Use the audit checklist in `h4-audit-plan` to:

1. Capture the raw manifest (files, sizes, checksums) and stash it under `data/h4_audit/`.
2. Map raw metadata fields explicitly to the contract keys and record the mapping in an audit report.
3. Only after those steps trigger the first data ingest that outputs the split metadata for baseline training.
