"""SE-MRM Benchmark v0.1 — baseline comparison.

Benchmarks the MRM pipeline against:
  A. generator + simple property filter (baseline)
  B. generator + MatterSim screening without falsification
  C. generator + MRM full pipeline (falsification)

This is a stub benchmark using synthetic data.
Real benchmark requires reference materials with known stability outcomes.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from skeptic_mrm.falsification import RuleBasedAttackPolicy, run_falsification_suite
from skeptic_mrm.normalize import normalize_candidates
from skeptic_mrm.reports import generate_candidate_report
from skeptic_mrm.runner import MRMConfig, MRMRunner
from skeptic_mrm.schemas.material_candidate import MaterialCandidate
from skeptic_mrm.scoring import compute_scores, make_decision
from skeptic_mrm.simulation_backends import MatterSimBackendStub


def _generate_synthetic_candidates(n: int = 20) -> list[MaterialCandidate]:
    """Generate synthetic inorganic crystal candidates for benchmarking."""
    compositions = [
        "LiFePO4", "LiCoO2", "NaMnO2", "Li2MnO3", "LiNi0.5Mn1.5O4",
        "CaTiO3", "SrTiO3", "BaTiO3", "MgO", "Al2O3",
        "SiO2", "TiO2", "ZrO2", "HfO2", "CeO2",
        "GaN", "ZnO", "InP", "GaAs", "CdTe",
    ]
    candidates: list[MaterialCandidate] = []
    for i in range(n):
        comp = compositions[i % len(compositions)]
        candidates.append(MaterialCandidate(
            candidate_id=f"bench_{i:04d}",
            source="benchmark_synthetic",
            composition=comp,
            structure_format="json",
            structure_blob=f'{{"lattice": [[10,0,0],[0,10,0],[0,0,10]], "sites": [], "id": {i}}}',
            target_properties={"band_gap": 1.0 + i * 0.1},
        ))
    return candidates


def _save_candidates(candidates: list[MaterialCandidate], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [c.to_dict() for c in candidates]
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def run_bench_v01(output_dir: str | Path = "experiments/mrm_bench_v01/results") -> dict:
    """Run the benchmark and return results dict."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Generate synthetic candidates
    candidates = _generate_synthetic_candidates(20)
    candidates_path = out / "bench_candidates.json"
    _save_candidates(candidates, candidates_path)

    # Normalize
    kept, norm_report = normalize_candidates(candidates)

    # Run MRM pipeline
    config = MRMConfig(mode="quick", max_attacks_per_candidate=4)
    runner = MRMRunner(config=config)
    result = runner.run_batch(str(candidates_path))

    # Summary
    summary = {
        "benchmark": "mrm_bench_v01",
        "n_candidates": len(candidates),
        "n_kept_after_normalize": len(kept),
        "normalization_report": norm_report.to_dict(),
        "batch_summary": result.batch_report.failure_summary(),
        "top_survivors": [
            {
                "candidate_id": r.candidate.candidate_id,
                "composition": r.candidate.composition,
                "score": r.score_bundle.final_reliability_score,
                "decision": r.decision.status.value,
            }
            for r in result.top_survivors(5)
        ],
        "all_decisions": {
            "promote": sum(1 for r in result.candidate_reports if r.decision.status.value == "promote"),
            "hold": sum(1 for r in result.candidate_reports if r.decision.status.value == "hold"),
            "kill": sum(1 for r in result.candidate_reports if r.decision.status.value == "kill"),
        },
    }

    # Save
    results_path = out / "bench_results.json"
    results_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Print
    print(f"Benchmark: {summary['benchmark']}")
    print(f"Candidates: {summary['n_candidates']}")
    print(f"Kept after normalization: {summary['n_kept_after_normalize']}")
    print(f"Decisions: {summary['all_decisions']}")
    print(f"\nTop survivors:")
    for s in summary["top_survivors"]:
        print(f"  {s['candidate_id']} | {s['composition']} | score={s['score']:.3f} | {s['decision']}")
    print(f"\nResults saved to: {results_path}")

    return summary


if __name__ == "__main__":
    run_bench_v01()
