from __future__ import annotations

import json
from pathlib import Path


def load_top5_board(path: str | Path) -> list[dict[str, object]]:
    board_path = Path(path)
    raw_items = json.loads(board_path.read_text(encoding="utf-8"))
    if not isinstance(raw_items, list):
        raise ValueError("Top-5 board file must contain a JSON array.")
    return raw_items
