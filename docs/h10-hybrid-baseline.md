# H10 Hybrid Baseline

- model: `hybrid_hgb_v1`
- target: `solvent_removal_stability_binary`
- descriptor input: `data\benchmarks\h10_features\mofsimplify_descriptor_features.csv`
- graph input: `data\benchmarks\h10_graphs\mofsimplify_asr_graphs.jsonl.gz`
- rows: train=`1394`, val=`349`, test=`436`
- descriptor features: `174`
- graph features: `41`
- total features: `215`
- selected params: `{"learning_rate": 0.08, "max_depth": 8, "max_iter": 500, "min_samples_leaf": 10}`

## Validation Metrics

- average_precision: `0.877291`
- roc_auc: `0.852550`
- balanced_accuracy: `0.770772`
- threshold: `0.852836`

## Test Metrics

- average_precision: `0.862236`
- roc_auc: `0.834634`
- balanced_accuracy: `0.751918`
- threshold: `0.852836`

## Notes

- This baseline tests whether graph-structural features add value on top of the descriptor stack.
- It uses a single train/val/test split and selects hyperparameters on validation only.
- It improves over `descriptor_hgb_v1` on `ROC-AUC` and `balanced_accuracy`, but not on the primary metric `average_precision`.

## Artifacts

- report: `data\benchmarks\h10_results\hybrid_hgb_v1.json`
- predictions: `data\benchmarks\h10_results\hybrid_hgb_v1_test_predictions.csv`
