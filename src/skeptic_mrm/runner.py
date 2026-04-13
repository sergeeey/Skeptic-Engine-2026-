"""SE-MRM MRMRunner — end-to-end batch processing."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from skeptic_mrm.falsification import (
    FalsificationResult,
    RuleBasedAttackPolicy,
    run_falsification_suite,
)
from skeptic_mrm.generator_adapters import IGeneratorAdapter
from skeptic_mrm.ingest import load_candidates
from skeptic_mrm.normalize import normalize_candidates
from skeptic_mrm.reports import (
    BatchReport,
    CandidateReport,
    generate_batch_report,
    generate_candidate_report,
)
from skeptic_mrm.scoring import ScoreBundle, compute_scores, make_decision
from skeptic_mrm.schemas.failure_attack import FailureAttack
from skeptic_mrm.schemas.material_candidate import MaterialCandidate
from skeptic_mrm.schemas.reliability_decision import ReliabilityDecision
from skeptic_mrm.schemas.simulation_run import SimulationRun
from skeptic_mrm.simulation_backends import ISimulationBackend


@dataclass(frozen=True)
class MRMConfig:
    """Configuration for an MRM run."""

    domain: str = "inorganic_crystals"
    mode: str = "standard"  # "quick", "standard", "deep"
    simulation_backend: str = "mattersim"
    attack_policy: str = "rules_v1"
    max_attacks_per_candidate: int = 8
    enabled_attacks: list[str] | None = None
    kill_below: float = 0.35
    hold_below: float = 0.65
    promote_above: float = 0.65

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MRMConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass(frozen=True)
class MRMResult:
    """Complete result of an MRM batch run."""

    batch_id: str
    config: MRMConfig
    candidate_reports: list[CandidateReport]
    batch_report: BatchReport

    def top_survivors(self, n: int = 5) -> list[CandidateReport]:
        return self.batch_report.top_survivors(n)

    def summary(self) -> str:
        return self.batch_report.summary()

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "config": {
                "domain": self.config.domain,
                "mode": self.config.mode,
                "backend": self.config.simulation_backend,
            },
            "batch_report": self.batch_report.to_dict(),
        }

    def save(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(
            json.dumps(self.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )


class MRMRunner:
    """Main entry point for running the MRM pipeline on a batch of candidates."""

    def __init__(
        self,
        config: MRMConfig | None = None,
        backend: ISimulationBackend | None = None,
        generator: IGeneratorAdapter | None = None,
    ) -> None:
        from skeptic_mrm.simulation_backends import MatterSimBackendStub

        self.config = config or MRMConfig()
        self._backend = backend or MatterSimBackendStub()
        self._generator = generator

    def run_batch(self, input_path: str | Path) -> MRMResult:
        """Run the full MRM pipeline on a batch of candidates."""
        batch_id = f"batch_{uuid.uuid4().hex[:8]}"
        path = Path(input_path)

        # Stage 0: Ingest
        candidates = load_candidates(path)

        # Stage 1: Normalize + dedup
        kept, norm_report = normalize_candidates(candidates)

        # Stage 2-5: Process each candidate
        reports: list[CandidateReport] = []
        for candidate in kept:
            report = self._process_candidate(candidate)
            reports.append(report)

        # Stage 6: Batch report
        batch_report = generate_batch_report(batch_id, reports)

        return MRMResult(
            batch_id=batch_id,
            config=self.config,
            candidate_reports=reports,
            batch_report=batch_report,
        )

    def _process_candidate(
        self,
        candidate: MaterialCandidate,
    ) -> CandidateReport:
        """Run screening + falsification + scoring + decision for one candidate."""

        # Stage 3: Simulation screening (stub)
        sim_run = self._backend.relax(candidate)
        sim_runs = [sim_run]

        # Stage 4: Falsification attacks
        policy = RuleBasedAttackPolicy(
            enabled_attacks=self.config.enabled_attacks
        )
        falsification = run_falsification_suite(
            candidate,
            self._backend,
            policy,
            budget={"max_attacks_per_candidate": self.config.max_attacks_per_candidate},
        )

        # Stage 5: Scoring
        score_bundle = compute_scores(
            candidate,
            sim_runs,
            stress_resilience=falsification.stress_resilience_score,
            backend=self.config.simulation_backend,
            thresholds={
                "kill_below": self.config.kill_below,
                "hold_below": self.config.hold_below,
                "promote_above": self.config.promote_above,
            },
        )

        # Stage 5b: Decision
        decision = make_decision(
            score_bundle,
            thresholds={
                "kill_below": self.config.kill_below,
                "hold_below": self.config.hold_below,
                "promote_above": self.config.promote_above,
            },
        )

        # Stage 7: Report
        return generate_candidate_report(
            candidate=candidate,
            score_bundle=score_bundle,
            decision=decision,
            simulation_runs=sim_runs,
            failure_attacks=falsification.attacks,
        )
