# H4 Data Contract

## Related Docs

- `h4-dataset-decision.md`
- `h4-benchmark-plan.md`
- `verification/H4-tda-cancer-resistance.md`

## Purpose

Define the minimum benchmark-valid contract for `H4` before raw ingestion or model training begins.

## Required Route Fields

Every `H4` dataset route must declare:

- `unit_of_analysis`
- `evaluation_level`
- `label_schema`
- `split_unit`
- `group_keys_for_split`
- `leakage_keys`
- `route_status`
- `blocking_issues`

## Route Status Meanings

- `scouting`: route is interesting but not yet contract-locked
- `contract_locked_pending_audit`: route has an explicit benchmark contract but still requires raw audit
- `ready`: route has passed audit and can move into ingestion or training

## Fail-Fast Rules

The spec should be treated as invalid if:

- there is not exactly one `default_route`
- any route is missing benchmark-contract fields
- `label_schema` is empty or lacks a clear positive label
- `split_unit` or `group_keys_for_split` are undefined
- `leakage_keys` are undefined
- a route is marked `ready` while `blocking_issues` are still present

## Current Default Route Contract

### Route

- `GSE164897`
- status: `contract_locked_pending_audit`

### Intended Benchmark Contract

- unit of analysis: `single_cell`
- primary evaluation level: `sample_group_primary_cell_level_secondary`
- label task: binary `drug_resistant_state` vs `non_resistant_state`
- split unit: `sample_group`
- provisional split keys:
  - `sample_id`
  - `condition_label`
  - `replicate_id`
- leakage keys:
  - `cell_barcode`
  - `sample_id`
  - `condition_label`
  - `replicate_id`
  - `dataset_accession`

## What Still Needs Audit

- whether those split keys actually exist in raw metadata
- whether sample-group splitting leaves enough independent groups for a meaningful benchmark
- whether the benchmark should be judged primarily at sample-group level or only at cell level
