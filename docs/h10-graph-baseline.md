# H10 Graph Baseline

- model: `graph_structural_hgb_v1`
- target: `solvent_removal_stability_binary`
- input artifact: `data\benchmarks\h10_graphs\mofsimplify_asr_graphs.jsonl.gz`
- rows: train=`1394`, val=`349`, test=`436`
- graph feature dim: `41`
- selected params: `{"learning_rate": 0.1, "max_depth": 6, "max_iter": 350, "min_samples_leaf": 12}`

## Validation Metrics

- average_precision: `0.855295`
- roc_auc: `0.829698`
- balanced_accuracy: `0.765503`
- threshold: `0.508632`

## Test Metrics

- average_precision: `0.834278`
- roc_auc: `0.797952`
- balanced_accuracy: `0.725214`
- threshold: `0.508632`

## Notes

- This baseline uses graph-derived structural features extracted directly from the graph artifact.
- It is the first trainable graph-path baseline, even though it is not yet a message-passing neural network.
- Hyperparameter selection is performed on validation only.

## Artifacts

- report: `data\benchmarks\h10_results\graph_structural_hgb_v1.json`
- predictions: `data\benchmarks\h10_results\graph_structural_hgb_v1_test_predictions.csv`
