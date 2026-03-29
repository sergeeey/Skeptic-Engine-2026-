from __future__ import annotations

import gzip
from pathlib import Path


def main() -> None:
    path = Path("data/h4_audit/GSE164897_series_matrix.txt.gz")
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            if line.startswith("!"):
                print(line.strip())
            elif line.startswith("#"):
                continue
            else:
                break


if __name__ == "__main__":
    main()
