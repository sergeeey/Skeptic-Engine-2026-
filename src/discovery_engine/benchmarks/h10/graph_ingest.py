from __future__ import annotations

import csv
import gzip
import json
import tarfile
from dataclasses import asdict, dataclass, field
from importlib import resources
from pathlib import Path

try:
    import CoRE_MOF
    import CoRE_MOF.data as core_mof_data
    from pymatgen.core import Structure
    from pymatgen.core.graphs import StructureGraph
    from pymatgen.core.local_env import MinimumDistanceNN

    _HAS_GRAPH_DEPS = True
except ImportError:
    _HAS_GRAPH_DEPS = False


@dataclass(slots=True)
class H10GraphIngestReport:
    dataset: str
    rows_requested: int
    rows_built: int
    failures: int
    graph_artifact_path: str
    summary_path: str
    avg_nodes: float
    avg_edges: float
    max_nodes: int
    max_edges: int
    failure_examples: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _relative(project_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)


def _load_mapped_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {str(key): str(value or "").strip() for key, value in row.items()} for row in reader
        ]


def _structure_from_tar(
    archive: tarfile.TarFile,
    members_by_name: dict[str, tarfile.TarInfo],
    structure_id: str,
) -> "Structure":
    member = members_by_name.get(f"{structure_id}.cif")
    if member is None:
        raise KeyError(f"missing CIF for {structure_id}")
    handle = archive.extractfile(member)
    if handle is None:
        raise KeyError(f"cannot extract CIF for {structure_id}")
    return Structure.from_str(handle.read().decode("utf-8"), fmt="cif")


def _graph_record(
    mapped_row: dict[str, str],
    archive: tarfile.TarFile,
    members_by_name: dict[str, tarfile.TarInfo],
) -> dict[str, object]:
    structure_id = mapped_row["structure_id"]
    structure = _structure_from_tar(archive, members_by_name, structure_id)
    graph = StructureGraph.from_local_env_strategy(structure, MinimumDistanceNN())

    edges: set[tuple[int, int]] = set()
    for source, target in graph.graph.edges():
        a = int(source)
        b = int(target)
        if a == b:
            continue
        edges.add((a, b) if a < b else (b, a))

    return {
        "structure_id": structure_id,
        "core_mof_id": mapped_row.get("core_mof_id", ""),
        "split": mapped_row.get("split", ""),
        "target_value": mapped_row.get("target_value", ""),
        "target_name": mapped_row.get("target_name", ""),
        "formula": structure.composition.formula,
        "num_nodes": len(structure),
        "num_edges": len(edges),
        "lattice_matrix": [
            [float(value) for value in row] for row in structure.lattice.matrix.tolist()
        ],
        "atomic_numbers": [int(site.specie.Z) for site in structure],
        "frac_coords": [
            [float(value) for value in coords] for coords in structure.frac_coords.tolist()
        ],
        "edges": [[int(a), int(b)] for a, b in sorted(edges)],
    }


def build_h10_graph_artifact(
    *,
    project_root: Path,
    mapped_dataset_path: Path,
    graph_output_path: Path,
    summary_output_path: Path,
) -> H10GraphIngestReport:
    if not _HAS_GRAPH_DEPS:
        raise ImportError(
            "Graph ingestion requires CoRE_MOF and pymatgen. "
            "Install them with: pip install CoRE-MOF pymatgen"
        )
    mapped_rows = _load_mapped_rows(mapped_dataset_path)
    if not mapped_rows:
        raise ValueError("Mapped H10 dataset is empty; run h10-map first.")

    graph_output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_output_path.parent.mkdir(parents=True, exist_ok=True)

    built = 0
    failures = 0
    total_nodes = 0
    total_edges = 0
    max_nodes = 0
    max_edges = 0
    failure_examples: list[str] = []

    tar_path = resources.files(core_mof_data) / "2019-ASR.tar.xz"
    with tarfile.open(tar_path, "r:xz") as archive:
        members_by_name = {
            member.name.split("/")[-1]: member
            for member in archive.getmembers()
            if member.isfile() and member.size > 0 and member.name.lower().endswith(".cif")
        }

        with gzip.open(graph_output_path, "wt", encoding="utf-8") as handle:
            for row in mapped_rows:
                structure_id = row["structure_id"]
                try:
                    record = _graph_record(row, archive, members_by_name)
                except Exception as exc:
                    failures += 1
                    if len(failure_examples) < 10:
                        failure_examples.append(f"{structure_id}: {type(exc).__name__}: {exc}")
                    continue

                built += 1
                total_nodes += int(record["num_nodes"])
                total_edges += int(record["num_edges"])
                max_nodes = max(max_nodes, int(record["num_nodes"]))
                max_edges = max(max_edges, int(record["num_edges"]))
                handle.write(json.dumps(record, ensure_ascii=True) + "\n")

    report = H10GraphIngestReport(
        dataset="2019-ASR",
        rows_requested=len(mapped_rows),
        rows_built=built,
        failures=failures,
        graph_artifact_path=_relative(project_root, graph_output_path),
        summary_path=_relative(project_root, summary_output_path),
        avg_nodes=(total_nodes / built) if built else 0.0,
        avg_edges=(total_edges / built) if built else 0.0,
        max_nodes=max_nodes,
        max_edges=max_edges,
        failure_examples=failure_examples,
    )
    summary_output_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return report
