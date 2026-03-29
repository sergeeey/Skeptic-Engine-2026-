from __future__ import annotations

import gzip
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer


@dataclass(slots=True)
class H10GraphMetricSet:
    average_precision: float
    roc_auc: float
    balanced_accuracy: float
    threshold: float


@dataclass(slots=True)
class H10GraphBaselineRun:
    model_id: str
    target_name: str
    input_artifact: str
    train_rows: int
    val_rows: int
    test_rows: int
    graph_feature_dim: int
    selected_params: dict[str, object]
    val_metrics: H10GraphMetricSet
    test_metrics: H10GraphMetricSet
    output_predictions_path: str
    output_report_path: str

    def to_dict(self) -> dict[str, object]:
        return {
            "model_id": self.model_id,
            "target_name": self.target_name,
            "input_artifact": self.input_artifact,
            "train_rows": self.train_rows,
            "val_rows": self.val_rows,
            "test_rows": self.test_rows,
            "graph_feature_dim": self.graph_feature_dim,
            "selected_params": self.selected_params,
            "val_metrics": asdict(self.val_metrics),
            "test_metrics": asdict(self.test_metrics),
            "output_predictions_path": self.output_predictions_path,
            "output_report_path": self.output_report_path,
        }


def _relative(project_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)


def _safe_auc(y_true: np.ndarray, scores: np.ndarray) -> float:
    positives = float(np.sum(y_true == 1))
    negatives = float(np.sum(y_true == 0))
    if positives == 0 or negatives == 0:
        return 0.5
    order = np.argsort(scores)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(scores) + 1, dtype=float)
    positive_ranks = ranks[y_true == 1].sum()
    auc = (positive_ranks - positives * (positives + 1) / 2.0) / (positives * negatives)
    return float(auc)


def _safe_average_precision(y_true: np.ndarray, scores: np.ndarray) -> float:
    positives = float(np.sum(y_true == 1))
    if positives == 0:
        return 0.0
    order = np.argsort(-scores)
    y_sorted = y_true[order]
    true_positives = np.cumsum(y_sorted == 1)
    precision = true_positives / np.arange(1, len(y_sorted) + 1, dtype=float)
    return float(np.sum(precision * (y_sorted == 1)) / positives)


def _balanced_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    positives = y_true == 1
    negatives = y_true == 0
    tpr = float(np.mean(y_pred[positives] == 1)) if positives.any() else 0.0
    tnr = float(np.mean(y_pred[negatives] == 0)) if negatives.any() else 0.0
    return (tpr + tnr) / 2.0


def _metric_set(y_true: np.ndarray, probabilities: np.ndarray, threshold: float) -> H10GraphMetricSet:
    predictions = (probabilities >= threshold).astype(int)
    return H10GraphMetricSet(
        average_precision=_safe_average_precision(y_true, probabilities),
        roc_auc=_safe_auc(y_true, probabilities),
        balanced_accuracy=_balanced_accuracy(y_true, predictions),
        threshold=float(threshold),
    )


def _candidate_thresholds(probabilities: np.ndarray) -> list[float]:
    values = sorted({round(float(value), 6) for value in probabilities.tolist()})
    if 0.5 not in values:
        values.append(0.5)
    return sorted(set(values))


def _best_threshold(y_true: np.ndarray, probabilities: np.ndarray) -> float:
    best_threshold = 0.5
    best_score = float("-inf")
    for threshold in _candidate_thresholds(probabilities):
        predictions = (probabilities >= threshold).astype(int)
        score = _balanced_accuracy(y_true, predictions)
        if score > best_score:
            best_score = score
            best_threshold = threshold
    return float(best_threshold)


def _element_fraction_features(atomic_numbers: list[int]) -> dict[str, float]:
    counts = np.bincount(np.array(atomic_numbers, dtype=int), minlength=95).astype(float)
    total = max(float(len(atomic_numbers)), 1.0)
    selected = [1, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 19, 20, 24, 25, 26, 27, 28, 29, 30, 31, 40, 56]
    return {f"atom_frac_{atomic_number}": counts[atomic_number] / total for atomic_number in selected}


def _degree_bin_features(degrees: np.ndarray) -> dict[str, float]:
    total = max(float(len(degrees)), 1.0)
    return {
        "deg_frac_0": float(np.sum(degrees == 0) / total),
        "deg_frac_1": float(np.sum(degrees == 1) / total),
        "deg_frac_2": float(np.sum(degrees == 2) / total),
        "deg_frac_3": float(np.sum(degrees == 3) / total),
        "deg_frac_4plus": float(np.sum(degrees >= 4) / total),
    }


def _graph_features(raw: dict[str, object]) -> dict[str, float | int | str]:
    num_nodes = int(raw["num_nodes"])
    num_edges = int(raw["num_edges"])
    atomic_numbers = [int(value) for value in raw["atomic_numbers"]]
    graph = nx.Graph()
    graph.add_nodes_from(range(num_nodes))
    graph.add_edges_from((int(a), int(b)) for a, b in raw["edges"])

    degrees = np.array([degree for _, degree in graph.degree()], dtype=float)
    components = [len(component) for component in nx.connected_components(graph)] if graph.number_of_nodes() else [0]
    largest_component = max(components) if components else 0
    density = float((2.0 * num_edges) / (num_nodes * max(num_nodes - 1, 1))) if num_nodes > 1 else 0.0
    avg_clustering = float(nx.average_clustering(graph)) if num_edges > 0 else 0.0

    features: dict[str, float | int | str] = {
        "structure_id": str(raw["structure_id"]),
        "core_mof_id": str(raw.get("core_mof_id", "")),
        "split": str(raw["split"]),
        "target_value": int(raw["target_value"]),
        "target_name": str(raw["target_name"]),
        "num_nodes": num_nodes,
        "num_edges": num_edges,
        "avg_degree": float(degrees.mean()) if len(degrees) else 0.0,
        "std_degree": float(degrees.std()) if len(degrees) else 0.0,
        "max_degree": float(degrees.max()) if len(degrees) else 0.0,
        "density": density,
        "avg_clustering": avg_clustering,
        "component_count": len(components),
        "largest_component_ratio": float(largest_component / max(num_nodes, 1)),
        "avg_atomic_number": float(np.mean(atomic_numbers)),
        "std_atomic_number": float(np.std(atomic_numbers)),
        "unique_atom_types": float(len(set(atomic_numbers))),
    }
    features.update(_degree_bin_features(degrees))
    features.update(_element_fraction_features(atomic_numbers))
    return features


def _load_graph_feature_frame(path: Path) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            rows.append(_graph_features(json.loads(line)))
    if not rows:
        raise ValueError("Graph artifact is empty; run h10-build-graph-artifact first.")
    return pd.DataFrame(rows)


def _build_markdown(run: H10GraphBaselineRun) -> str:
    return "\n".join(
        [
            "# H10 Graph Baseline",
            "",
            f"- model: `{run.model_id}`",
            f"- target: `{run.target_name}`",
            f"- input artifact: `{run.input_artifact}`",
            f"- rows: train=`{run.train_rows}`, val=`{run.val_rows}`, test=`{run.test_rows}`",
            f"- graph feature dim: `{run.graph_feature_dim}`",
            f"- selected params: `{json.dumps(run.selected_params, ensure_ascii=True)}`",
            "",
            "## Validation Metrics",
            "",
            f"- average_precision: `{run.val_metrics.average_precision:.6f}`",
            f"- roc_auc: `{run.val_metrics.roc_auc:.6f}`",
            f"- balanced_accuracy: `{run.val_metrics.balanced_accuracy:.6f}`",
            f"- threshold: `{run.val_metrics.threshold:.6f}`",
            "",
            "## Test Metrics",
            "",
            f"- average_precision: `{run.test_metrics.average_precision:.6f}`",
            f"- roc_auc: `{run.test_metrics.roc_auc:.6f}`",
            f"- balanced_accuracy: `{run.test_metrics.balanced_accuracy:.6f}`",
            f"- threshold: `{run.test_metrics.threshold:.6f}`",
            "",
            "## Notes",
            "",
            "- This baseline uses graph-derived structural features extracted directly from the graph artifact.",
            "- It is the first trainable graph-path baseline, even though it is not yet a message-passing neural network.",
            "- Hyperparameter selection is performed on validation only.",
            "",
            "## Artifacts",
            "",
            f"- report: `{run.output_report_path}`",
            f"- predictions: `{run.output_predictions_path}`",
        ]
    ) + "\n"


def run_h10_graph_baseline(
    *,
    project_root: Path,
    graph_artifact_path: Path,
    report_output_path: Path,
    predictions_output_path: Path,
    markdown_output_path: Path,
) -> H10GraphBaselineRun:
    df = _load_graph_feature_frame(graph_artifact_path)
    target_names = sorted(set(df["target_name"].astype(str)))
    if len(target_names) != 1:
        raise ValueError(f"Graph artifact must contain one target name, got {target_names}.")

    id_columns = {"structure_id", "core_mof_id", "split", "target_value", "target_name"}
    feature_columns = [column for column in df.columns if column not in id_columns]
    if not feature_columns:
        raise ValueError("Graph feature frame contains no feature columns.")

    train_df = df[df["split"] == "train"].copy()
    val_df = df[df["split"] == "val"].copy()
    test_df = df[df["split"] == "test"].copy()
    if train_df.empty or val_df.empty or test_df.empty:
        raise ValueError("Graph feature frame must contain train, val, and test rows.")

    x_train = train_df[feature_columns]
    y_train = train_df["target_value"].astype(int).to_numpy()
    x_val = val_df[feature_columns]
    y_val = val_df["target_value"].astype(int).to_numpy()
    x_test = test_df[feature_columns]
    y_test = test_df["target_value"].astype(int).to_numpy()

    imputer = SimpleImputer(strategy="median")
    x_train_imp = imputer.fit_transform(x_train)
    x_val_imp = imputer.transform(x_val)
    x_test_imp = imputer.transform(x_test)

    search_space = [
        {"learning_rate": 0.05, "max_depth": 4, "max_iter": 250, "min_samples_leaf": 20},
        {"learning_rate": 0.05, "max_depth": 6, "max_iter": 350, "min_samples_leaf": 15},
        {"learning_rate": 0.1, "max_depth": 6, "max_iter": 350, "min_samples_leaf": 12},
        {"learning_rate": 0.1, "max_depth": 8, "max_iter": 450, "min_samples_leaf": 10},
    ]

    best_model: HistGradientBoostingClassifier | None = None
    best_params: dict[str, object] | None = None
    best_val_probabilities: np.ndarray | None = None
    best_score = float("-inf")

    for params in search_space:
        model = HistGradientBoostingClassifier(
            learning_rate=float(params["learning_rate"]),
            max_depth=int(params["max_depth"]),
            max_iter=int(params["max_iter"]),
            min_samples_leaf=int(params["min_samples_leaf"]),
            random_state=42,
        )
        model.fit(x_train_imp, y_train)
        val_probabilities = model.predict_proba(x_val_imp)[:, 1]
        score = _safe_average_precision(y_val, val_probabilities)
        if score > best_score:
            best_score = score
            best_model = model
            best_params = dict(params)
            best_val_probabilities = val_probabilities

    if best_model is None or best_params is None or best_val_probabilities is None:
        raise RuntimeError("Graph baseline search failed to produce a model.")

    threshold = _best_threshold(y_val, best_val_probabilities)
    val_metrics = _metric_set(y_val, best_val_probabilities, threshold)
    test_probabilities = best_model.predict_proba(x_test_imp)[:, 1]
    test_metrics = _metric_set(y_test, test_probabilities, threshold)

    predictions = test_df[["structure_id", "core_mof_id", "split", "target_value"]].copy()
    predictions["predicted_probability"] = test_probabilities
    predictions["predicted_label"] = (test_probabilities >= threshold).astype(int)

    predictions_output_path.parent.mkdir(parents=True, exist_ok=True)
    report_output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_path.parent.mkdir(parents=True, exist_ok=True)

    predictions.to_csv(predictions_output_path, index=False)

    run = H10GraphBaselineRun(
        model_id="graph_structural_hgb_v1",
        target_name=target_names[0],
        input_artifact=_relative(project_root, graph_artifact_path),
        train_rows=len(train_df),
        val_rows=len(val_df),
        test_rows=len(test_df),
        graph_feature_dim=len(feature_columns),
        selected_params=best_params,
        val_metrics=val_metrics,
        test_metrics=test_metrics,
        output_predictions_path=_relative(project_root, predictions_output_path),
        output_report_path=_relative(project_root, report_output_path),
    )

    report_output_path.write_text(json.dumps(run.to_dict(), indent=2), encoding="utf-8")
    markdown_output_path.write_text(_build_markdown(run), encoding="utf-8")
    return run
