from __future__ import annotations

import json
from pathlib import Path

from discovery_engine.schemas import CandidateSeed


def load_candidate_seeds(path: str | Path) -> list[CandidateSeed]:
    candidate_path = Path(path)
    raw_items = json.loads(candidate_path.read_text(encoding="utf-8"))
    if not isinstance(raw_items, list):
        raise ValueError("Candidate seed file must contain a JSON array.")
    return [CandidateSeed.from_dict(item) for item in raw_items]
