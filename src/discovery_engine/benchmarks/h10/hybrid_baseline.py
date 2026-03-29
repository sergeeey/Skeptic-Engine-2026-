from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score, balanced_accuracy_score, roc_auc_score

from .graph_baseline import _load_graph_feature_frame


_JOIN_COLUMNS = ["structure_id", "core_mof_id", "split", "target_value"]
_DESCRIPTOR_ID_COLUMNS = {"structure_id", "core_mof_id", "split", "target_value"}
_GRAPH_ID_COLUMNS = {"structure_id", "core_mof_id", "split", "target_value", "target_name"}


@dataclass(slots=True)
class H10HybridMetricSet:
    average_precision: float
    roc_auc: float
    balanced_accuracy: float
    threshold: float


@dataclass(slots=True)
class H10HybridBaselineRun:
    model_id: str
    target_name: str
    descriptor_input_artifact: str
    graph_input_artifact: str
    train_rows: int
    val_rows: int
    test_rows: int
    descriptor_feature_count: int
    graph_feature_count: int
    total_feature_count: int
    selected_params: dict[str, object]
    val_metrics: H10HybridMetricSet
    test_metrics: H10HybridMetricSet
    output_predictions_path: str
    output_report_path: str

    def to_dict(self) -> dict[str, object]:
        return {
            "model_id": self.model_id,
            "target_name": self.target_name,
            "descriptor_input_artifact": self.descriptor_input_artifact,
            "graph_input_artifact": self.graph_input_artifact,
            "train_rows": self.train_rows,
            "val_rows": self.val_rows,
            "test_rows": self.test_rows,
            "descriptor_feature_count": self.descriptor_feature_count,
            "graph_feature_count": self.graph_feature_count,
            "total_feature_count": self.total_feature_count,
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


def _metric_set(y_true: pd.Series, probabilities: pd.Series, threshold: float) -> H10HybridMetricSet:
    predictions = (probabilities >= threshold).astype(int)
    return H10HybridMetricSet(
        average_precision=float(average_precision_score(y_true, probabilities)),
        roc_auc=float(roc_auc_score(y_true, probabilities)),
        balanced_accuracy=float(balanced_accuracy_score(y_true, predictions)),
        threshold=float(threshold),
    )


def _candidate_thresholds(probabilities: pd.Series) -> list[float]:
    values = sorted({round(float(value), 6) for value in probabilities.tolist()})
    if 0.5 not in values:
        values.append(0.5)
    return sorted(set(values))


def _best_threshold(y_true: pd.Series, probabilities: pd.Series) -> float:
    best_threshold = 0.5
    best_score = float("-inf")
    for threshold in _candidate_thresholds(probabilities):
        predictions = (probabilities >= threshold).astype(int)
        score = float(balanced_accuracy_score(y_true, predictions))
        if score > best_score:
            best_score = score
            best_threshold = threshold
    return best_threshold


def _build_hybrid_frame(descriptor_feature_path: Path, graph_artifact_path: Path) -> tuple[pd.DataFrame, str, int, int]:
    descriptor_df = pd.read_csv(descriptor_feature_path)
    if descriptor_df.empty:
        raise ValueError("Descriptor feature artifact is empty.")

    graph_df = _load_graph_feature_frame(graph_artifact_path)
    if graph_df.empty:
        raise ValueError("Graph feature artifact is empty.")

    target_names = sorted(set(graph_df["target_name"].astype(str)))
    if len(target_names) != 1:
        raise ValueError(f"Graph feature frame must contain one target name, got {target_names}.")

    descriptor_feature_columns = [
        column for column in descriptor_df.columns if column not in _DESCRIPTOR_ID_COLUMNS
    ]
    graph_feature_columns = [column for column in graph_df.columns if column not in _GRAPH_ID_COLUMNS]
    if not descriptor_feature_columns or not graph_feature_columns:
        raise ValueError("Hybrid baseline requires both descriptor and graph feature columns.")

    hybrid_df = descriptor_df.merge(
        graph_df[_JOIN_COLUMNS + graph_feature_columns],
        on=_JOIN_COLUMNS,
        how="inner",
        validate="one_to_one",
    )
    if len(hybrid_df) != len(descriptor_df):
        raise ValueError(
            f"Hybrid frame row mismatch after merge: descriptor_rows={len(descriptor_df)} "
            f"hybrid_rows={len(hybrid_df)}."
        )
    return hybrid_df, target_names[0], len(descriptor_feature_columns), len(graph_feature_columns)


def _build_markdown(run: H10HybridBaselineRun) -> str:
    return "\n".join(
        [
            "# H10 Hybrid Baseline",
            "",
            f"- model: `{run.model_id}`",
            f"- target: `{run.target_name}`",
            f"- descriptor input: `{run.descriptor_input_artifact}`",
            f"- graph input: `{run.graph_input_artifact}`",
            f"- rows: train=`{run.train_rows}`, val=`{run.val_rows}`, test=`{run.test_rows}`",
            f"- descriptor features: `{run.descriptor_feature_count}`",
            f"- graph features: `{run.graph_feature_count}`",
            f"- total features: `{run.total_feature_count}`",
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
            "- This baseline tests whether graph-structural features add value on top of the descriptor stack.",
            "- It uses a single train/val/test split and selects hyperparameters on validation only.",
            "",
            "## Artifacts",
            "",
            f"- report: `{run.output_report_path}`",
            f"- predictions: `{run.output_predictions_path}`",
        ]
    ) + "\n"


def run_h10_hybrid_baseline(
    *,
    project_root: Path,
    descriptor_feature_path: Path,
    graph_artifact_path: Path,
    report_output_path: Path,
    predictions_output_path: Path,
    markdown_output_path: Path,
) -> H10HybridBaselineRun:
    hybrid_df, target_name, descriptor_feature_count, graph_feature_count = _build_hybrid_frame(
        descriptor_feature_path,
        graph_artifact_path,
    )

    feature_columns = [column for column in hybrid_df.columns if column not in _JOIN_COLUMNS]
    train_df = hybrid_df[hybrid_df["split"] == "train"].copy()
    val_df = hybrid_df[hybrid_df["split"] == "val"].copy()
    test_df = hybrid_df[hybrid_df["split"] == "test"].copy()

    x_train = train_df[feature_columns]
    y_train = train_df["target_value"].astype(int)
    x_val = val_df[feature_columns]
    y_val = val_df["target_value"].astype(int)
    x_test = test_df[feature_columns]
    y_test = test_df["target_value"].astype(int)

    imputer = SimpleImputer(strategy="median")
    x_train_imp = imputer.fit_transform(x_train)
    x_val_imp = imputer.transform(x_val)
    x_test_imp = imputer.transform(x_test)

    search_space = [
        {"learning_rate": 0.03, "max_depth": 6, "max_iter": 350, "min_samples_leaf": 20},
        {"learning_rate": 0.05, "max_depth": 6, "max_iter": 450, "min_samples_leaf": 15},
        {"learning_rate": 0.05, "max_depth": 8, "max_iter": 500, "min_samples_leaf": 10},
        {"learning_rate": 0.08, "max_depth": 8, "max_iter": 500, "min_samples_leaf": 10},
    ]

    best_model: HistGradientBoostingClassifier | None = None
    best_params: dict[str, object] | None = None
    best_val_probabilities: pd.Series | None = None
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
        val_probabilities = pd.Series(model.predict_proba(x_val_imp)[:, 1], index=val_df.index)
        score = float(average_precision_score(y_val, val_probabilities))
        if score > best_score:
            best_score = score
            best_model = model
            best_params = dict(params)
            best_val_probabilities = val_probabilities

    if best_model is None or best_params is None or best_val_probabilities is None:
        raise RuntimeError("Hybrid baseline search failed to produce a model.")

    threshold = _best_threshold(y_val, best_val_probabilities)
    val_metrics = _metric_set(y_val, best_val_probabilities, threshold)
    test_probabilities = pd.Series(best_model.predict_proba(x_test_imp)[:, 1], index=test_df.index)
    test_metrics = _metric_set(y_test, test_probabilities, threshold)

    predictions = test_df[_JOIN_COLUMNS[:-1] + ["target_value"]].copy()
    predictions["predicted_probability"] = test_probabilities.to_numpy()
    predictions["predicted_label"] = (test_probabilities >= threshold).astype(int).to_numpy()

    predictions_output_path.parent.mkdir(parents=True, exist_ok=True)
    report_output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_path.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(predictions_output_path, index=False)

    run = H10HybridBaselineRun(
        model_id="hybrid_hgb_v1",
        target_name=target_name,
        descriptor_input_artifact=_relative(project_root, descriptor_feature_path),
        graph_input_artifact=_relative(project_root, graph_artifact_path),
        train_rows=len(train_df),
        val_rows=len(val_df),
        test_rows=len(test_df),
        descriptor_feature_count=descriptor_feature_count,
        graph_feature_count=graph_feature_count,
        total_feature_count=len(feature_columns),
        selected_params=best_params,
        val_metrics=val_metrics,
        test_metrics=test_metrics,
        output_predictions_path=_relative(project_root, predictions_output_path),
        output_report_path=_relative(project_root, report_output_path),
    )

    report_output_path.write_text(json.dumps(run.to_dict(), indent=2), encoding="utf-8")
    markdown_output_path.write_text(_build_markdown(run), encoding="utf-8")
    return run
