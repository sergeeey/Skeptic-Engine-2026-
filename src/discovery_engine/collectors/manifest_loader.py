from __future__ import annotations

import json
from pathlib import Path

from discovery_engine.schemas import SourceRecord


def load_source_manifest(path: str | Path) -> list[SourceRecord]:
    manifest_path = Path(path)
    raw_items = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw_items, list):
        raise ValueError("Source manifest must contain a JSON array.")

    records: list[SourceRecord] = []
    for item in raw_items:
        if not isinstance(item, dict):
            raise ValueError("Each source manifest item must be a JSON object.")
        records.append(SourceRecord.from_dict(item))
    return records
