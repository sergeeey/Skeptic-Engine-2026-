from __future__ import annotations

import csv
import gzip
import json
import math
import os
import random
from dataclasses import asdict, dataclass
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import torch
from torch import nn
import numpy as np

try:
    from pymatgen.core.periodic_table import Element
except ImportError:
    Element = None


_ATOM_FEATURE_CACHE: dict[int, list[float]] = {}


@dataclass(slots=True)
class H10GraphMPNNMetricSet:
    average_precision: float
    roc_auc: float
    balanced_accuracy: float
    threshold: float


@dataclass(slots=True)
class H10GraphMPNNRun:
    model_id: str
    target_name: str
    input_artifact: str
    train_rows: int
    val_rows: int
    test_rows: int
    hidden_dim: int
    selected_params: dict[str, object]
    val_metrics: H10GraphMPNNMetricSet
    test_metrics: H10GraphMPNNMetricSet
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
            "hidden_dim": self.hidden_dim,
            "selected_params": self.selected_params,
            "val_metrics": asdict(self.val_metrics),
            "test_metrics": asdict(self.test_metrics),
            "output_predictions_path": self.output_predictions_path,
            "output_report_path": self.output_report_path,
        }


@dataclass(slots=True)
class GraphSample:
    structure_id: str
    core_mof_id: str
    split: str
    target_value: int
    target_name: str
    atomic_numbers: list[int]
    edge_index: list[tuple[int, int]]
    num_nodes: int
    num_edges: int
    frac_coords: list[list[float]]
    lattice_matrix: list[list[float]]
    edge_distances: list[float]
    node_scalar_features: list[list[float]]
    graph_features: list[float]


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
    return float((positive_ranks - positives * (positives + 1) / 2.0) / (positives * negatives))


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


def _metric_set(y_true: np.ndarray, probabilities: np.ndarray, threshold: float) -> H10GraphMPNNMetricSet:
    predictions = (probabilities >= threshold).astype(int)
    return H10GraphMPNNMetricSet(
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


def _atom_property_features(atomic_number: int) -> list[float]:
    cached = _ATOM_FEATURE_CACHE.get(atomic_number)
    if cached is not None:
        return cached

    if Element is None:
        features = [
            float(atomic_number) / 100.0,
            math.sqrt(float(atomic_number)) / 10.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        ]
    else:
        element = Element.from_Z(atomic_number)
        row = float(element.row or 0.0) / 10.0
        group = float(element.group or 0.0) / 18.0
        electronegativity = float(element.X or 0.0) / 4.0
        atomic_radius = float(element.atomic_radius or 0.0) / 3.0
        atomic_mass = float(element.atomic_mass or 0.0) / 250.0
        is_metal = 1.0 if bool(element.is_metal) else 0.0
        features = [
            float(atomic_number) / 100.0,
            math.sqrt(float(atomic_number)) / 10.0,
            row,
            group,
            electronegativity,
            atomic_radius,
            atomic_mass,
            is_metal,
        ]

    _ATOM_FEATURE_CACHE[atomic_number] = features
    return features


def _read_graph_samples(path: Path) -> list[GraphSample]:
    samples: list[GraphSample] = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            raw = json.loads(line)
            undirected_edges = [tuple(int(value) for value in edge) for edge in raw.get("edges", [])]
            directed_edges: list[tuple[int, int]] = []
            directed_edge_distances: list[float] = []
            frac_coords = [[float(value) for value in coords] for coords in raw.get("frac_coords", [])]
            lattice_matrix = [
                [float(value) for value in row] for row in raw.get("lattice_matrix", [])
            ]
            degree_counts = [0] * int(raw["num_nodes"])
            for source, target in undirected_edges:
                directed_edges.append((source, target))
                directed_edge_distances.append(
                    _minimum_image_distance(
                        frac_coords[source],
                        frac_coords[target],
                        lattice_matrix,
                    )
                )
                directed_edges.append((target, source))
                directed_edge_distances.append(
                    _minimum_image_distance(
                        frac_coords[target],
                        frac_coords[source],
                        lattice_matrix,
                    )
                )
                degree_counts[source] += 1
                degree_counts[target] += 1
            atomic_numbers = [int(value) for value in raw["atomic_numbers"]]
            node_scalar_features = [
                _atom_property_features(atomic_number) + [math.log1p(float(degree))]
                for atomic_number, degree in zip(atomic_numbers, degree_counts, strict=True)
            ]
            samples.append(
                GraphSample(
                    structure_id=str(raw["structure_id"]),
                    core_mof_id=str(raw.get("core_mof_id", "")),
                    split=str(raw["split"]),
                    target_value=int(raw["target_value"]),
                    target_name=str(raw["target_name"]),
                    atomic_numbers=atomic_numbers,
                    edge_index=directed_edges,
                    num_nodes=int(raw["num_nodes"]),
                    num_edges=int(raw["num_edges"]),
                    frac_coords=frac_coords,
                    lattice_matrix=lattice_matrix,
                    edge_distances=directed_edge_distances,
                    node_scalar_features=node_scalar_features,
                    graph_features=_graph_level_features(
                        atomic_numbers=atomic_numbers,
                        lattice_matrix=lattice_matrix,
                        num_nodes=int(raw["num_nodes"]),
                        num_edges=int(raw["num_edges"]),
                        directed_edge_lengths=directed_edge_distances,
                    ),
                )
            )
    return samples


def _split_samples(samples: list[GraphSample]) -> tuple[list[GraphSample], list[GraphSample], list[GraphSample]]:
    grouped = {"train": [], "val": [], "test": []}
    for sample in samples:
        if sample.split not in grouped:
            raise ValueError(f"Unexpected split {sample.split!r} in graph artifact.")
        grouped[sample.split].append(sample)
    if not all(grouped.values()):
        raise ValueError("Graph artifact must contain non-empty train, val, and test splits.")
    return grouped["train"], grouped["val"], grouped["test"]


def _mean_pool(node_embeddings: torch.Tensor, graph_index: torch.Tensor, num_graphs: int) -> torch.Tensor:
    pooled = torch.zeros((num_graphs, node_embeddings.shape[1]), device=node_embeddings.device)
    pooled.index_add_(0, graph_index, node_embeddings)
    counts = torch.zeros(num_graphs, device=node_embeddings.device)
    counts.index_add_(0, graph_index, torch.ones_like(graph_index, dtype=torch.float32))
    return pooled / counts.clamp_min(1.0).unsqueeze(1)


def _max_pool(node_embeddings: torch.Tensor, graph_index: torch.Tensor, num_graphs: int) -> torch.Tensor:
    pooled_rows: list[torch.Tensor] = []
    for graph_id in range(num_graphs):
        mask = graph_index == graph_id
        if torch.any(mask):
            pooled_rows.append(node_embeddings[mask].max(dim=0).values)
        else:
            pooled_rows.append(torch.zeros(node_embeddings.shape[1], device=node_embeddings.device))
    return torch.stack(pooled_rows, dim=0)


def _gated_pool(node_embeddings: torch.Tensor, graph_index: torch.Tensor, num_graphs: int) -> torch.Tensor:
    gates = torch.sigmoid(node_embeddings.mean(dim=1, keepdim=True))
    pooled = torch.zeros((num_graphs, node_embeddings.shape[1]), device=node_embeddings.device)
    pooled.index_add_(0, graph_index, node_embeddings * gates)
    gate_sums = torch.zeros((num_graphs, 1), device=node_embeddings.device)
    gate_sums.index_add_(0, graph_index, gates)
    return pooled / gate_sums.clamp_min(1.0)


def _minimum_image_distance(
    frac_source: list[float],
    frac_target: list[float],
    lattice_matrix: list[list[float]],
) -> float:
    delta = np.array(frac_target, dtype=np.float64) - np.array(frac_source, dtype=np.float64)
    delta -= np.round(delta)
    cart_delta = delta @ np.array(lattice_matrix, dtype=np.float64)
    return float(np.linalg.norm(cart_delta))


def _graph_level_features(
    *,
    atomic_numbers: list[int],
    lattice_matrix: list[list[float]],
    num_nodes: int,
    num_edges: int,
    directed_edge_lengths: list[float],
) -> list[float]:
    atomic_numbers_array = np.array(atomic_numbers, dtype=np.float64)
    atom_feature_array = np.array(
        [_atom_property_features(atomic_number) for atomic_number in atomic_numbers],
        dtype=np.float64,
    )
    lattice = np.array(lattice_matrix, dtype=np.float64)
    volume = float(abs(np.linalg.det(lattice))) if lattice.size else 0.0
    edge_lengths = np.array(directed_edge_lengths, dtype=np.float64) if directed_edge_lengths else np.zeros(1)
    return [
        math.log1p(num_nodes),
        math.log1p(num_edges),
        float(np.mean(atomic_numbers_array) / 100.0),
        float(np.std(atomic_numbers_array) / 50.0),
        float(len(set(atomic_numbers)) / 20.0),
        float(num_edges / max(num_nodes, 1)),
        math.log1p(max(volume, 0.0)),
        math.log1p((num_nodes / max(volume, 1e-6)) * 1000.0),
        float(np.mean(edge_lengths) / 5.0),
        float(np.std(edge_lengths) / 3.0),
        float(np.mean(atom_feature_array[:, 4])),
        float(np.mean(atom_feature_array[:, 7])),
    ]


def _collate(samples: list[GraphSample], device: torch.device) -> dict[str, object]:
    atomic_numbers: list[int] = []
    edge_rows: list[int] = []
    edge_cols: list[int] = []
    edge_distances: list[float] = []
    graph_index: list[int] = []
    targets: list[float] = []
    graph_features: list[list[float]] = []
    node_scalar_features: list[list[float]] = []
    structure_ids: list[str] = []
    core_mof_ids: list[str] = []
    offset = 0

    for graph_id, sample in enumerate(samples):
        atomic_numbers.extend(sample.atomic_numbers)
        graph_index.extend([graph_id] * len(sample.atomic_numbers))
        for source, target in sample.edge_index:
            edge_rows.append(source + offset)
            edge_cols.append(target + offset)
        edge_distances.extend(sample.edge_distances)
        node_scalar_features.extend(sample.node_scalar_features)
        offset += sample.num_nodes
        targets.append(float(sample.target_value))
        graph_features.append(sample.graph_features)
        structure_ids.append(sample.structure_id)
        core_mof_ids.append(sample.core_mof_id)

    return {
        "atomic_numbers": torch.tensor(atomic_numbers, dtype=torch.long, device=device),
        "edge_index": torch.tensor([edge_rows, edge_cols], dtype=torch.long, device=device),
        "edge_distances": torch.tensor(edge_distances, dtype=torch.float32, device=device),
        "graph_index": torch.tensor(graph_index, dtype=torch.long, device=device),
        "targets": torch.tensor(targets, dtype=torch.float32, device=device),
        "graph_features": torch.tensor(graph_features, dtype=torch.float32, device=device),
        "node_scalar_features": torch.tensor(node_scalar_features, dtype=torch.float32, device=device),
        "num_graphs": len(samples),
        "structure_ids": structure_ids,
        "core_mof_ids": core_mof_ids,
    }


class EdgeMessagePassingLayer(nn.Module):
    def __init__(self, hidden_dim: int, edge_rbf_dim: int) -> None:
        super().__init__()
        self.message_mlp = nn.Sequential(
            nn.Linear(hidden_dim * 2 + edge_rbf_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
        )
        self.update_mlp = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
        )
        self.norm = nn.LayerNorm(hidden_dim)

    def forward(
        self,
        node_embeddings: torch.Tensor,
        edge_index: torch.Tensor,
        edge_rbf: torch.Tensor,
    ) -> torch.Tensor:
        source, target = edge_index
        messages = self.message_mlp(
            torch.cat([node_embeddings[source], node_embeddings[target], edge_rbf], dim=1)
        )
        neighbor_sum = torch.zeros_like(node_embeddings)
        neighbor_sum.index_add_(0, target, messages)
        counts = torch.zeros(node_embeddings.shape[0], dtype=torch.float32, device=node_embeddings.device)
        counts.index_add_(0, target, torch.ones_like(target, dtype=torch.float32))
        neighbor_mean = neighbor_sum / counts.clamp_min(1.0).unsqueeze(1)
        updated = self.update_mlp(torch.cat([node_embeddings, neighbor_mean], dim=1))
        return self.norm(node_embeddings + updated)


class H10GraphMPNN(nn.Module):
    def __init__(self, hidden_dim: int, num_layers: int, dropout: float) -> None:
        super().__init__()
        self.atom_embedding = nn.Embedding(119, hidden_dim)
        self.node_scalar_proj = nn.Linear(9, hidden_dim)
        self.edge_centers = nn.Parameter(torch.linspace(0.8, 4.5, steps=12), requires_grad=False)
        self.layers = nn.ModuleList(
            [EdgeMessagePassingLayer(hidden_dim=hidden_dim, edge_rbf_dim=12) for _ in range(num_layers)]
        )
        self.dropout = nn.Dropout(dropout)
        self.graph_feature_proj = nn.Sequential(
            nn.Linear(12, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim * 4, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, batch: dict[str, object]) -> torch.Tensor:
        atomic_numbers = batch["atomic_numbers"]
        edge_index = batch["edge_index"]
        edge_distances = batch["edge_distances"]
        graph_index = batch["graph_index"]
        node_scalar_features = batch["node_scalar_features"]
        num_graphs = int(batch["num_graphs"])

        edge_rbf = torch.exp(-1.5 * (edge_distances.unsqueeze(1) - self.edge_centers.unsqueeze(0)) ** 2)
        node_embeddings = self.atom_embedding(atomic_numbers) + self.node_scalar_proj(node_scalar_features)

        for layer in self.layers:
            node_embeddings = self.dropout(layer(node_embeddings, edge_index, edge_rbf))

        pooled_mean = _mean_pool(node_embeddings, graph_index, num_graphs)
        pooled_max = _max_pool(node_embeddings, graph_index, num_graphs)
        pooled_gate = _gated_pool(node_embeddings, graph_index, num_graphs)
        graph_side = self.graph_feature_proj(batch["graph_features"])
        graph_repr = torch.cat([pooled_mean, pooled_max, pooled_gate, graph_side], dim=1)
        return self.classifier(graph_repr).squeeze(1)


def _iterate_batches(
    samples: list[GraphSample],
    *,
    batch_size: int,
    device: torch.device,
    shuffle: bool,
) -> list[dict[str, object]]:
    indices = list(range(len(samples)))
    if shuffle:
        random.shuffle(indices)
    batches: list[dict[str, object]] = []
    for start in range(0, len(indices), batch_size):
        batch_samples = [samples[index] for index in indices[start : start + batch_size]]
        batches.append(_collate(batch_samples, device))
    return batches


@torch.no_grad()
def _predict(
    model: H10GraphMPNN,
    samples: list[GraphSample],
    *,
    batch_size: int,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray, list[str], list[str]]:
    model.eval()
    targets: list[int] = []
    probabilities: list[float] = []
    structure_ids: list[str] = []
    core_mof_ids: list[str] = []
    for batch in _iterate_batches(samples, batch_size=batch_size, device=device, shuffle=False):
        logits = model(batch)
        probs = torch.sigmoid(logits).detach().cpu().numpy()
        probabilities.extend(float(value) for value in probs)
        targets.extend(int(value) for value in batch["targets"].detach().cpu().numpy())
        structure_ids.extend(batch["structure_ids"])
        core_mof_ids.extend(batch["core_mof_ids"])
    return (
        np.array(targets, dtype=int),
        np.array(probabilities, dtype=np.float64),
        structure_ids,
        core_mof_ids,
    )


def _build_markdown(run: H10GraphMPNNRun) -> str:
    return "\n".join(
        [
            "# H10 Graph MPNN Baseline",
            "",
            f"- model: `{run.model_id}`",
            f"- target: `{run.target_name}`",
            f"- input artifact: `{run.input_artifact}`",
            f"- rows: train=`{run.train_rows}`, val=`{run.val_rows}`, test=`{run.test_rows}`",
            f"- hidden dim: `{run.hidden_dim}`",
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
            "- This is the current true message-passing graph baseline for H10.",
            "- It uses pure torch message passing with edge-distance RBF features and does not depend on torch_geometric.",
            "- The project sets `KMP_DUPLICATE_LIB_OK=TRUE` before torch import because this environment has an OpenMP runtime conflict.",
            "",
            "## Artifacts",
            "",
            f"- report: `{run.output_report_path}`",
            f"- predictions: `{run.output_predictions_path}`",
        ]
    ) + "\n"


def run_h10_graph_mpnn_baseline(
    *,
    project_root: Path,
    graph_artifact_path: Path,
    report_output_path: Path,
    predictions_output_path: Path,
    markdown_output_path: Path,
) -> H10GraphMPNNRun:
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    torch.set_num_threads(1)
    device = torch.device("cpu")

    samples = _read_graph_samples(graph_artifact_path)
    if not samples:
        raise ValueError("Graph artifact is empty; run h10-build-graph-artifact first.")
    target_names = sorted({sample.target_name for sample in samples})
    if len(target_names) != 1:
        raise ValueError(f"Graph artifact must contain one target name, got {target_names}.")

    train_samples, val_samples, test_samples = _split_samples(samples)
    positive_count = sum(sample.target_value for sample in train_samples)
    negative_count = len(train_samples) - positive_count
    pos_weight = float(negative_count / max(positive_count, 1))

    search_space = [
        {"hidden_dim": 48, "num_layers": 2, "dropout": 0.10, "lr": 0.0010, "batch_size": 8},
        {"hidden_dim": 64, "num_layers": 3, "dropout": 0.10, "lr": 0.0007, "batch_size": 6},
        {"hidden_dim": 64, "num_layers": 2, "dropout": 0.15, "lr": 0.0008, "batch_size": 8},
    ]

    best_state: dict[str, torch.Tensor] | None = None
    best_params: dict[str, object] | None = None
    best_val_probabilities: np.ndarray | None = None
    best_val_targets: np.ndarray | None = None
    best_score = float("-inf")

    for params in search_space:
        model = H10GraphMPNN(
            hidden_dim=int(params["hidden_dim"]),
            num_layers=int(params["num_layers"]),
            dropout=float(params["dropout"]),
        ).to(device)
        optimizer = torch.optim.AdamW(model.parameters(), lr=float(params["lr"]), weight_decay=1e-4)
        criterion = nn.BCEWithLogitsLoss()

        best_local_score = float("-inf")
        best_local_state: dict[str, torch.Tensor] | None = None
        patience = 0
        for _epoch in range(32):
            model.train()
            for batch in _iterate_batches(
                train_samples,
                batch_size=int(params["batch_size"]),
                device=device,
                shuffle=True,
            ):
                optimizer.zero_grad(set_to_none=True)
                logits = model(batch)
                loss = criterion(logits, batch["targets"])
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=3.0)
                optimizer.step()

            val_targets, val_probabilities, _, _ = _predict(
                model,
                val_samples,
                batch_size=int(params["batch_size"]),
                device=device,
            )
            score = _safe_average_precision(val_targets, val_probabilities)
            if score > best_local_score:
                best_local_score = score
                best_local_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
                patience = 0
            else:
                patience += 1
                if patience >= 6:
                    break

        if best_local_state is None:
            raise RuntimeError("MPNN baseline failed to produce a trained state.")

        model.load_state_dict(best_local_state)
        val_targets, val_probabilities, _, _ = _predict(
            model,
            val_samples,
            batch_size=int(params["batch_size"]),
            device=device,
        )
        score = _safe_average_precision(val_targets, val_probabilities)
        if score > best_score:
            best_score = score
            best_state = best_local_state
            best_params = dict(params)
            best_val_probabilities = val_probabilities
            best_val_targets = val_targets

    if best_state is None or best_params is None or best_val_probabilities is None or best_val_targets is None:
        raise RuntimeError("MPNN baseline search failed to produce a model.")

    model = H10GraphMPNN(
        hidden_dim=int(best_params["hidden_dim"]),
        num_layers=int(best_params["num_layers"]),
        dropout=float(best_params["dropout"]),
    ).to(device)
    model.load_state_dict(best_state)

    threshold = _best_threshold(best_val_targets, best_val_probabilities)
    val_metrics = _metric_set(best_val_targets, best_val_probabilities, threshold)
    test_targets, test_probabilities, structure_ids, core_mof_ids = _predict(
        model,
        test_samples,
        batch_size=int(best_params["batch_size"]),
        device=device,
    )
    test_metrics = _metric_set(test_targets, test_probabilities, threshold)

    predictions_output_path.parent.mkdir(parents=True, exist_ok=True)
    report_output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_path.parent.mkdir(parents=True, exist_ok=True)

    with predictions_output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "structure_id",
                "core_mof_id",
                "split",
                "target_value",
                "predicted_probability",
                "predicted_label",
            ]
        )
        for structure_id, core_mof_id, target_value, probability in zip(
            structure_ids,
            core_mof_ids,
            test_targets.tolist(),
            test_probabilities.tolist(),
            strict=True,
        ):
            writer.writerow(
                [
                    structure_id,
                    core_mof_id,
                    "test",
                    int(target_value),
                    float(probability),
                    int(probability >= threshold),
                ]
            )

    run = H10GraphMPNNRun(
        model_id="graph_mpnn_v3",
        target_name=target_names[0],
        input_artifact=_relative(project_root, graph_artifact_path),
        train_rows=len(train_samples),
        val_rows=len(val_samples),
        test_rows=len(test_samples),
        hidden_dim=int(best_params["hidden_dim"]),
        selected_params=best_params,
        val_metrics=val_metrics,
        test_metrics=test_metrics,
        output_predictions_path=_relative(project_root, predictions_output_path),
        output_report_path=_relative(project_root, report_output_path),
    )

    report_output_path.write_text(json.dumps(run.to_dict(), indent=2), encoding="utf-8")
    markdown_output_path.write_text(_build_markdown(run), encoding="utf-8")
    return run
