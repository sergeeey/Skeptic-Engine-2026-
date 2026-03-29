from __future__ import annotations

import gzip
import json
from pathlib import Path


def _read_series_header(path: Path) -> list[str]:
    header_lines: list[str] = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("!series_matrix_table_begin"):
                break
            if stripped.startswith("!"):
                header_lines.append(stripped)
    return header_lines


def _parse_sample_lines(header_lines: list[str]) -> dict[str, list[list[str]]]:
    data: dict[str, list[list[str]]] = {}
    for line in header_lines:
        if not line.startswith("!Sample_"):
            continue
        parts = line.split("\t")
        key = parts[0].strip()
        values = [part.strip().strip('"') for part in parts[1:]]
        data.setdefault(key, []).append(values)
    return data


def _build_sample_table(parsed: dict[str, list[list[str]]]) -> list[dict[str, str]]:
    key_lists = next(iter(parsed.values()))
    total_samples = len(key_lists[0]) if key_lists else 0
    samples: list[dict[str, str]] = []

    for idx in range(total_samples):
        entry: dict[str, str] = {}
        for key, blocks in parsed.items():
            for block in blocks:
                if idx >= len(block):
                    continue
                value = block[idx]
                entry.setdefault(key, []).append(value)
        samples.append(entry)
    return samples


def _extract_characteristics(entry: dict[str, list[str]]) -> dict[str, str]:
    characteristics = {}
    for block in entry.get("!Sample_characteristics_ch1", []):
        if ":" not in block:
            continue
        key, value = block.split(":", 1)
        field = key.strip().lower().replace(" ", "_")
        characteristics[field] = value.strip()
    return characteristics


def main() -> None:
    series_path = Path("data/h4_audit/GSE164897_series_matrix.txt.gz")
    if not series_path.exists():
        raise FileNotFoundError(series_path)

    header_lines = _read_series_header(series_path)
    parsed_samples = _parse_sample_lines(header_lines)
    raw_samples = _build_sample_table(parsed_samples)

    sample_infos = []
    treatments = set()
    for sample in raw_samples:
        chars = _extract_characteristics(sample)
        treatment = chars.get("treatment", "unknown")
        treatments.add(treatment)
        sample_infos.append(
            {
                "geo_accession": sample.get("!Sample_geo_accession", ["unknown"])[0],
                "title": sample.get("!Sample_title", ["unknown"])[0],
                "treatment": treatment,
                "cell_line": chars.get("cell_line", "unknown"),
                "sample_group": sample.get("!Sample_title", ["unknown"])[0],
            }
        )

    spec_path = Path("data/benchmarks/h4_mvp_spec.json")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    default_route = next(
        (route for route in spec.get("dataset_routes", []) if route.get("default_route")),
        {},
    )

    report = {
        "dataset": "GSE164897",
        "route_status": default_route.get("route_status"),
        "samples": sample_infos,
        "unique_treatments": sorted(sorted(treatments)),
        "group_keys_expected": default_route.get("group_keys_for_split", []),
        "leakage_keys_expected": default_route.get("leakage_keys", []),
        "split_unit": default_route.get("split_unit"),
        "label_schema": default_route.get("label_schema", {}),
        "sample_count": len(sample_infos),
    }

    out_path = Path("data/h4_audit/GSE164897_metadata.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
