from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class CsvAssetSummary:
    path: str
    exists: bool
    row_count: int = 0
    columns: list[str] = field(default_factory=list)


@dataclass(slots=True)
class H10DatasetCard:
    route_id: str
    title: str
    assets: list[CsvAssetSummary]

    @property
    def total_rows(self) -> int:
        return sum(asset.row_count for asset in self.assets)

    @property
    def ready_for_mapping(self) -> bool:
        relevant = [asset for asset in self.assets if asset.path.endswith(".csv")]
        return all(asset.exists for asset in relevant) and any(asset.row_count > 0 for asset in relevant)


def _read_csv_summary(path: Path) -> CsvAssetSummary:
    if not path.exists():
        return CsvAssetSummary(path=str(path), exists=False)

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        rows = list(reader)

    if not rows:
        return CsvAssetSummary(path=str(path), exists=True, row_count=0, columns=[])

    header = [str(item) for item in rows[0]]
    row_count = max(0, len(rows) - 1)
    return CsvAssetSummary(path=str(path), exists=True, row_count=row_count, columns=header)


def build_h10_dataset_card(route: dict[str, object], project_root: Path) -> H10DatasetCard:
    assets: list[CsvAssetSummary] = []
    for item in route.get("expected_files", []):
        if not isinstance(item, dict):
            continue
        rel_path = str(item.get("path", ""))
        if not rel_path:
            continue
        abs_path = project_root / rel_path
        if abs_path.suffix.lower() == ".csv":
            assets.append(_read_csv_summary(abs_path))
        else:
            assets.append(CsvAssetSummary(path=str(abs_path), exists=abs_path.exists()))

    return H10DatasetCard(
        route_id=str(route.get("route_id", "unknown")),
        title=str(route.get("title", "")),
        assets=assets,
    )
