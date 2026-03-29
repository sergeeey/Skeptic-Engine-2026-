# H10 Baseline Matrix

- route: `mofsimplify_stability`
- target: `solvent_removal_stability_binary`
- mapped dataset: `data\benchmarks\h10_mapped\mofsimplify_stability.csv`
- rows: `2179`

## Split Summary

| Split | Rows | Class Balance |
|---|---:|---|
| train | 1394 | 0=561, 1=833 |
| val | 349 | 0=149, 1=200 |
| test | 436 | 0=173, 1=263 |

## Baseline Matrix

| Baseline | Family | Status | Train Ready | Rows | Features | Artifact |
|---|---|---|---|---:|---:|---|
| descriptor_baseline | tabular | ready | yes | 2179 | 174 | data\benchmarks\h10_features\mofsimplify_descriptor_features.csv |
- descriptor_baseline: Uses RAC and geometric descriptors extracted from MOFSimplify full_SSD_data.csv.
- descriptor_baseline: Run descriptor baselines only on the fixed MOFSimplify train/val/test split.
| hybrid_baseline | tabular_plus_graph | ready | yes | 2179 | 215 | data\benchmarks\h10_features\mofsimplify_descriptor_features.csv + data\benchmarks\h10_graphs\mofsimplify_asr_graphs.jsonl.gz |
- hybrid_baseline: Merges the full descriptor stack with graph-structural features on the same split.
- hybrid_baseline: `hybrid_hgb_v1` improves over pure descriptor HGB on `ROC-AUC` and `balanced_accuracy`, but not on the primary metric `average_precision`.
| token_baseline | sequence_like | blocked | no | 0 | 0 | - |
- token_baseline: Preferred token route is formula or linker/metal tokenization from a structure-derived representation.
- token_baseline: Do not use CoRE refcodes as a proxy tokenization baseline; that would be identifier leakage, not chemistry.
- blocker for token_baseline: Mapped route does not yet provide reliable formula or linker token fields.
| graph_baseline | graph | ready | yes | 2179 | 41 | data\benchmarks\h10_graphs\mofsimplify_asr_graphs.jsonl.gz |
- graph_baseline: core_mof_id coverage is 2179/2179 and the graph artifact is trainable.
- graph_baseline: The first graph-path baseline is `graph_structural_hgb_v1`, built from graph-derived structural features extracted from the graph artifact.
- graph_baseline: True message-passing attempts `graph_mpnn_v2` and `graph_mpnn_v3` now exist.
- graph_baseline: Current test metrics are `AP=0.834278`, `ROC-AUC=0.797952`, `Balanced Accuracy=0.725214`, which do not beat `descriptor_hgb_v1`.
- graph_baseline: Best message-passing test result so far is `graph_mpnn_v2` with `AP=0.736903`, `ROC-AUC=0.672960`, `Balanced Accuracy=0.619431`, which improves on the first pure-torch attempt but still underperforms both `descriptor_hgb_v1` and `graph_structural_hgb_v1`.
- graph_baseline: The chemistry-aware follow-up `graph_mpnn_v3` reached `val AP=0.777547` and `test ROC-AUC=0.676191`, but its `test AP=0.731329` did not beat `graph_mpnn_v2` on the primary metric.

## Evaluation Protocol

- split policy: Use the fixed MOFSimplify train/val/test partition shipped with the source dataset.
- primary metric: `average_precision`
- metrics: roc_auc, average_precision, balanced_accuracy
- positive label: `1`
- falsification rule: Reject the H10 claim if graph models fail to outperform simpler baselines on a defensible proxy target or if the target labels cannot be justified scientifically.

## Warnings

- Token baseline remains blocked until chemistry-derived token fields are added.
- Do not compare graph models against descriptor baselines on different splits.
- The first graph-path baseline does not yet beat the strongest descriptor baseline, so the graph-advantage claim remains unproven.
- Multiple MPNN attempts are still materially weaker than the stronger non-neural baselines, so any continued graph push now needs a specific justification.
- The hybrid descriptor-plus-graph baseline does not beat `descriptor_hgb_v1` on the primary metric, so graph signal currently helps as a comparison layer, not as a winning route.

## Related Results

- `h10-descriptor-baseline.md` records the first linear descriptor baseline.
- `h10-descriptor-tree-baseline.md` records the nonlinear descriptor sanity baseline.
- `h10-graph-artifact.md` records the graph-ready CoRE-MOF artifact for the same split.
- `h10-graph-baseline.md` records the first trainable graph-path baseline result.
- `h10-graph-mpnn-baseline.md` records the first true message-passing graph baseline result.
- `h10-hybrid-baseline.md` records the descriptor-plus-graph comparison baseline result.
