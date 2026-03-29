from __future__ import annotations

import json
from pathlib import Path


def load_h10_route(path: str | Path) -> dict[str, object]:
    route_path = Path(path)
    raw = json.loads(route_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("H10 route file must be a JSON object.")
    return raw
