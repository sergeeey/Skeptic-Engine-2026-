"""SE-MRM reports module — candidate, batch, and benchmark reports."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from skeptic_mrm.schemas.failure_attack import FailureAttack
from skeptic_mrm.schemas.material_candidate import MaterialCandidate
from skeptic_mrm.schemas.reliability_decision import ReliabilityDecision
from skeptic_mrm.schemas.simulation_run import SimulationRun
from skeptic_mrm.scoring import ScoreBundle


@dataclass(frozen=True)
class CandidateReport:
    """Full report for a single candidate."""

    candidate: MaterialCandidate
    score_bundle: ScoreBundle
    decision: ReliabilityDecision
    simulation_runs: list[SimulationRun] = field(default_factory=list)
    failure_attacks: list[FailureAttack] = field(default_factory=list)
    generated_at: str = ""

    def __post_init__(self) -> None:
        if not self.generated_at:
            object.__setattr__(
                self, "generated_at", datetime.now(timezone.utc).isoformat()
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate": self.candidate.to_dict(),
            "score_bundle": self.score_bundle.to_dict(),
            "decision": self.decision.to_dict(),
            "simulation_runs": [r.to_dict() for r in self.simulation_runs],
            "failure_attacks": [a.to_dict() for a in self.failure_attacks],
            "generated_at": self.generated_at,
        }

    def summary(self) -> str:
        return (
            f"  candidate: {self.candidate.candidate_id} | "
            f"composition: {self.candidate.composition} | "
            f"score: {self.score_bundle.final_reliability_score:.3f} | "
            f"decision: {self.decision.status.value}"
        )


@dataclass(frozen=True)
class BatchReport:
    """Summary report for a batch of candidates."""

    batch_id: str
    candidate_reports: list[CandidateReport]
    generated_at: str = ""

    def __post_init__(self) -> None:
        if not self.generated_at:
            object.__setattr__(
                self, "generated_at", datetime.now(timezone.utc).isoformat()
            )

    def top_survivors(self, n: int = 5) -> list[CandidateReport]:
        """Return top-n promoted/hold candidates sorted by score."""
        survivors = [
            r
            for r in self.candidate_reports
            if r.decision.status.value in ("promote", "hold")
        ]
        survivors.sort(key=lambda r: r.score_bundle.final_reliability_score, reverse=True)
        return survivors[:n]

    def failure_summary(self) -> dict[str, Any]:
        killed = [
            r for r in self.candidate_reports if r.decision.status.value == "kill"
        ]
        return {
            "total": len(self.candidate_reports),
            "promoted": sum(
                1 for r in self.candidate_reports if r.decision.status.value == "promote"
            ),
            "held": sum(
                1 for r in self.candidate_reports if r.decision.status.value == "hold"
            ),
            "killed": len(killed),
            "review_required": sum(
                1 for r in self.candidate_reports if r.decision.review_required
            ),
            "kill_reasons": [
                r.decision.reasons for r in killed if r.decision.reasons
            ],
        }

    def summary(self) -> str:
        fs = self.failure_summary()
        return (
            f"Batch {self.batch_id}: "
            f"total={fs['total']} promoted={fs['promoted']} "
            f"held={fs['held']} killed={fs['killed']} "
            f"review_needed={fs['review_required']}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "candidate_reports": [r.to_dict() for r in self.candidate_reports],
            "generated_at": self.generated_at,
            "summary": self.failure_summary(),
        }


def generate_candidate_report(
    candidate: MaterialCandidate,
    score_bundle: ScoreBundle,
    decision: ReliabilityDecision,
    simulation_runs: list[SimulationRun],
    failure_attacks: list[FailureAttack],
) -> CandidateReport:
    return CandidateReport(
        candidate=candidate,
        score_bundle=score_bundle,
        decision=decision,
        simulation_runs=simulation_runs,
        failure_attacks=failure_attacks,
    )


def generate_batch_report(
    batch_id: str,
    candidate_reports: list[CandidateReport],
) -> BatchReport:
    return BatchReport(
        batch_id=batch_id,
        candidate_reports=candidate_reports,
    )


def save_report(report: CandidateReport | BatchReport, path: str) -> None:
    """Save a report as JSON."""
    import json
    from pathlib import Path

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(report.to_dict(), indent=2, default=str),
        encoding="utf-8",
    )
