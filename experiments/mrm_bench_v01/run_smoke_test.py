"""SE-MRM smoke test — quick sanity check of the pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from skeptic_mrm.ingest import load_json_batch
from skeptic_mrm.normalize import normalize_candidates
from skeptic_mrm.runner import MRMConfig, MRMRunner
from skeptic_mrm.schemas.material_candidate import MaterialCandidate


def _create_smoke_test_data(path: Path) -> None:
    """Create minimal test data for smoke testing."""
    candidates = [
        MaterialCandidate(
            candidate_id="smoke_001",
            source="smoke_test",
            composition="LiFePO4",
            structure_format="json",
            structure_blob='{"lattice": [[10,0,0],[0,10,0],[0,0,10]], "sites": []}',
        ),
        MaterialCandidate(
            candidate_id="smoke_002",
            source="smoke_test",
            composition="NaCl",
            structure_format="json",
            structure_blob='{"lattice": [[5.6,0,0],[0,5.6,0],[0,0,5.6]], "sites": []}',
        ),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [c.to_dict() for c in candidates]
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def run_smoke_test() -> dict:
    """Run a minimal smoke test and return results."""
    data_path = Path(__file__).parent / "data" / "smoke_test.json"
    _create_smoke_test_data(data_path)

    config = MRMConfig(mode="quick", max_attacks_per_candidate=2)
    runner = MRMRunner(config=config)
    result = runner.run_batch(str(data_path))

    results = {
        "test": "smoke_test",
        "status": "passed",
        "n_candidates": len(result.candidate_reports),
        "decisions": {
            r.candidate.candidate_id: r.decision.status.value
            for r in result.candidate_reports
        },
    }
    print(f"Smoke test: {results['status']}")
    print(f"Candidates processed: {results['n_candidates']}")
    print(f"Decisions: {results['decisions']}")
    return results


if __name__ == "__main__":
    run_smoke_test()
