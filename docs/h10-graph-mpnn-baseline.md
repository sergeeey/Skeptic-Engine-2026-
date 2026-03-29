# H10 Graph MPNN Baseline

- model: `graph_mpnn_v3`
- target: `solvent_removal_stability_binary`
- input artifact: `data\benchmarks\h10_graphs\mofsimplify_asr_graphs.jsonl.gz`
- rows: train=`1394`, val=`349`, test=`436`
- hidden dim: `64`
- selected params: `{"hidden_dim": 64, "num_layers": 2, "dropout": 0.15, "lr": 0.0008, "batch_size": 8}`

## Validation Metrics

- average_precision: `0.777547`
- roc_auc: `0.741644`
- balanced_accuracy: `0.700889`
- threshold: `0.396696`

## Test Metrics

- average_precision: `0.731329`
- roc_auc: `0.676191`
- balanced_accuracy: `0.608321`
- threshold: `0.396696`

## Notes

- This is the current true message-passing graph baseline for H10.
- It uses pure torch message passing with edge-distance RBF features and does not depend on torch_geometric.
- It adds chemistry-aware node features, but this `v3` attempt does not beat `graph_mpnn_v2` on the primary test metric `average_precision`.
- The project sets `KMP_DUPLICATE_LIB_OK=TRUE` before torch import because this environment has an OpenMP runtime conflict.

## Artifacts

- report: `data\benchmarks\h10_results\graph_mpnn_v3.json`
- predictions: `data\benchmarks\h10_results\graph_mpnn_v3_test_predictions.csv`
