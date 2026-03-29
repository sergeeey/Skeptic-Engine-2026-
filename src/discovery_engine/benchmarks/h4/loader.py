from __future__ import annotations

import json
from pathlib import Path


def load_h4_spec(path: str | Path) -> dict[str, object]:
    spec_path = Path(path)
    raw = json.loads(spec_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("H4 benchmark spec must be a JSON object.")
    return raw
