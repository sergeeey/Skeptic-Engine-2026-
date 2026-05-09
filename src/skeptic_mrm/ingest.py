"""SE-MRM ingest module — loads candidates from various formats."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Iterable

from skeptic_mrm.schemas.material_candidate import MaterialCandidate


def _parse_cif_block(text: str) -> str:
    """Return raw CIF text as-is (full parser deferred to tier-1+)."""
    return text.strip()


def _parse_poscar_block(text: str) -> str:
    """Return raw POSCAR text as-is (full parser deferred to tier-1+)."""
    return text.strip()


def _load_json_candidates(path: Path) -> list[dict[str, Any]]:
    """Load candidates from JSON/JSONL file."""
    content = path.read_text(encoding="utf-8")
    if content.strip().startswith("["):
        return json.loads(content)  # type: ignore[no-any-return]
    # JSONL
    return [json.loads(line) for line in content.splitlines() if line.strip()]


def load_cif(
    path: Path, candidate_id: str | None = None, source: str = "cif_upload"
) -> MaterialCandidate:
    """Load a single CIF file as a MaterialCandidate."""
    text = path.read_text(encoding="utf-8")
    blob = _parse_cif_block(text)
    # Extract composition from CIF _chemical_formula_sum if present
    composition = "unknown"
    for line in text.splitlines():
        if line.strip().startswith("_chemical_formula_sum"):
            composition = line.split(None, 1)[1].strip().strip("\"'")
            break
    cid = candidate_id or f"mrm_{uuid.uuid4().hex[:8]}"
    return MaterialCandidate(
        candidate_id=cid,
        source=source,
        composition=composition,
        structure_format="cif",
        structure_blob=blob,
    )


def load_poscar(
    path: Path, candidate_id: str | None = None, source: str = "poscar_upload"
) -> MaterialCandidate:
    """Load a single POSCAR file as a MaterialCandidate."""
    text = path.read_text(encoding="utf-8")
    blob = _parse_poscar_block(text)
    composition = text.splitlines()[0].strip() if text.splitlines() else "unknown"
    cid = candidate_id or f"mrm_{uuid.uuid4().hex[:8]}"
    return MaterialCandidate(
        candidate_id=cid,
        source=source,
        composition=composition,
        structure_format="poscar",
        structure_blob=blob,
    )


def load_json_batch(path: Path, source: str = "json_batch") -> list[MaterialCandidate]:
    """Load a batch of candidates from JSON/JSONL."""
    raw_items = _load_json_candidates(path)
    candidates: list[MaterialCandidate] = []
    for item in raw_items:
        # Ensure required fields
        if "candidate_id" not in item:
            item["candidate_id"] = f"mrm_{uuid.uuid4().hex[:8]}"
        if "structure_blob" not in item:
            item["structure_blob"] = ""
        if "structure_format" not in item:
            item["structure_format"] = "json"
        candidates.append(
            MaterialCandidate.from_dict({**item, "source": item.get("source", source)})
        )
    return candidates


def load_mp_id(mp_id: str, candidate_id: str | None = None) -> MaterialCandidate:
    """Create a MaterialCandidate placeholder for a Materials Project ID.

    Actual data fetching via mp-api is deferred to the simulation backend.
    """
    cid = candidate_id or f"mrm_{uuid.uuid4().hex[:8]}"
    return MaterialCandidate(
        candidate_id=cid,
        source="materials_project",
        composition="pending_fetch",
        structure_format="mp_id",
        structure_blob=mp_id,
    )


def load_candidates(input_path: Path) -> list[MaterialCandidate]:
    """Auto-detect format and load candidates."""
    suffix = input_path.suffix.lower()
    if suffix == ".cif":
        return [load_cif(input_path)]
    if suffix in (".vasp", ".poscar"):
        return [load_poscar(input_path)]
    if suffix in (".json", ".jsonl"):
        return load_json_batch(input_path)
    raise ValueError(f"Unsupported file format: {suffix}. Supported: .cif, .poscar, .json, .jsonl")
