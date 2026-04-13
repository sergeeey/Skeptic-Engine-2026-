"""SE-MRM scoring module — composite reliability score."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from skeptic_mrm.schemas.material_candidate import MaterialCandidate
from skeptic_mrm.schemas.reliability_decision import DecisionStatus, ReliabilityDecision
from skeptic_mrm.schemas.simulation_run import SimulationRun


@dataclass(frozen=True)
class ScoreBundle:
    """All scores computed for a candidate."""

    candidate_id: str
    stability_score: float = 1.0
    dynamic_score: float = 1.0
    stress_resilience_score: float = 1.0
    uncertainty_penalty: float = 0.0
    novelty_score: float = 0.5
    sim_disagreement_penalty: float = 0.0
    compute_cost: float = 0.0
    evidence_completeness: float = 0.0
    final_reliability_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "stability_score": self.stability_score,
            "dynamic_score": self.dynamic_score,
            "stress_resilience_score": self.stress_resilience_score,
            "uncertainty_penalty": self.uncertainty_penalty,
            "novelty_score": self.novelty_score,
            "sim_disagreement_penalty": self.sim_disagreement_penalty,
            "compute_cost": self.compute_cost,
            "evidence_completeness": self.evidence_completeness,
            "final_reliability_score": self.final_reliability_score,
        }


# ── Default weights ────────────────────────────────────────────────

DEFAULT_WEIGHTS = {
    "w1_stability": 0.25,
    "w2_dynamic": 0.20,
    "w3_stress": 0.20,
    "w4_reproducibility": 0.10,
    "w5_novelty": 0.05,
    "w6_uncertainty_penalty": 0.10,
    "w7_sim_disagreement": 0.05,
    "w8_compute_risk": 0.05,
}

DEFAULT_THRESHOLDS = {
    "kill_below": 0.30,
    "hold_below": 0.50,
    "promote_above": 0.45,
    "min_stability": 0.20,
    "min_dynamic": 0.20,
    "max_uncertainty": 0.55,
}


def _compute_evidence_completeness(
    simulation_runs: list[SimulationRun],
    falsification_n_attacks: int,
) -> float:
    """Fraction of evidence sources that were completed."""
    total_expected = 2  # at least 1 sim run + falsification
    completed = 0
    if simulation_runs:
        completed += sum(1 for r in simulation_runs if r.status == "completed")
    if falsification_n_attacks > 0:
        completed += 1
    return min(1.0, completed / total_expected)


def _compute_uncertainty_penalty(
    simulation_runs: list[SimulationRun],
    backend: str | None = None,
) -> float:
    """Estimate uncertainty from backend disagreement or missing runs."""
    if not simulation_runs:
        return 1.0  # maximum uncertainty if no runs

    # Penalize missing tiers
    tiers_covered = {r.tier for r in simulation_runs}
    tier_penalty = max(0.0, 1.0 - len(tiers_covered) / 2.0)

    # Penalize failed runs
    failed_fraction = sum(1 for r in simulation_runs if r.status != "completed") / len(
        simulation_runs
    )

    return 0.6 * tier_penalty + 0.4 * failed_fraction


def compute_scores(
    candidate: MaterialCandidate,
    simulation_runs: list[SimulationRun],
    stress_resilience: float = 1.0,
    backend: str | None = None,
    weights: dict[str, float] | None = None,
    thresholds: dict[str, float] | None = None,
) -> ScoreBundle:
    """Compute composite reliability scores.

    Formula:
        final = w1*thermo + w2*dynamic + w3*stress + w4*reprod + w5*novelty
                - w6*uncertainty - w7*disagreement - w8*compute_risk
    """
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    t = {**DEFAULT_THRESHOLDS, **(thresholds or {})}

    # Extract from simulation runs
    stability = 1.0
    dynamic = 1.0
    for run in simulation_runs:
        metrics = run.metrics
        if "energy_proxy" in metrics:
            # Normalize: more negative energy = more stable
            # Typical formation energy range: -4.0 (very stable) to 0.0 (unstable)
            # Use sigmoid-like mapping for better separation
            energy = float(metrics["energy_proxy"])
            # Sigmoid-style: steep transition around -1.0 eV/atom
            # fe = -3.0 → ~0.95, fe = -2.0 → ~0.73, fe = -1.0 → ~0.38, fe = -0.3 → ~0.14
            stability = min(1.0, max(0.0, 1.0 / (1.0 + math.exp(energy + 1.5))))
        if "dynamic_stability_proxy" in metrics:
            dynamic = float(metrics["dynamic_stability_proxy"])

    uncertainty = _compute_uncertainty_penalty(simulation_runs, backend)
    evidence = _compute_evidence_completeness(
        simulation_runs, falsification_n_attacks=0  # set from falsification result
    )

    final = (
        w["w1_stability"] * stability
        + w["w2_dynamic"] * dynamic
        + w["w3_stress"] * stress_resilience
        + w["w4_reproducibility"] * evidence
        + w["w5_novelty"] * 0.5
        - w["w6_uncertainty_penalty"] * uncertainty
        - w["w7_sim_disagreement"] * 0.0  # single backend in v0.1
        - w["w8_compute_risk"] * 0.0  # no cost tracking in v0.1 stubs
    )
    final = max(0.0, min(1.0, final))

    return ScoreBundle(
        candidate_id=candidate.candidate_id,
        stability_score=stability,
        dynamic_score=dynamic,
        stress_resilience_score=stress_resilience,
        uncertainty_penalty=uncertainty,
        novelty_score=0.5,
        sim_disagreement_penalty=0.0,
        compute_cost=0.0,
        evidence_completeness=evidence,
        final_reliability_score=final,
    )


def make_decision(
    scores: ScoreBundle,
    thresholds: dict[str, float] | None = None,
) -> ReliabilityDecision:
    """Apply kill/hold/promote criteria to a score bundle."""
    t = {**DEFAULT_THRESHOLDS, **(thresholds or {})}

    reasons: list[str] = []
    review_required = False

    # Auto-kill criteria
    if scores.stability_score < t["min_stability"]:
        return ReliabilityDecision(
            decision_id=f"dec_{scores.candidate_id}",
            candidate_id=scores.candidate_id,
            final_score=scores.final_reliability_score,
            status=DecisionStatus.KILL,
            sub_scores=scores.to_dict(),
            reasons=["stability_below_min_threshold"],
            review_required=False,
        )

    if scores.dynamic_score < t["min_dynamic"]:
        return ReliabilityDecision(
            decision_id=f"dec_{scores.candidate_id}",
            candidate_id=scores.candidate_id,
            final_score=scores.final_reliability_score,
            status=DecisionStatus.KILL,
            sub_scores=scores.to_dict(),
            reasons=["dynamic_stability_below_min_threshold"],
            review_required=False,
        )

    if scores.uncertainty_penalty > t["max_uncertainty"]:
        review_required = True
        reasons.append("high_uncertainty_penalty")

    # Kill/hold/promote by final score
    final = scores.final_reliability_score
    if final < t["kill_below"]:
        status = DecisionStatus.KILL
        reasons.append("final_score_below_kill_threshold")
    elif final < t["hold_below"]:
        status = DecisionStatus.HOLD
        reasons.append("final_score_in_hold_range")
    else:
        status = DecisionStatus.PROMOTE
        reasons.append("final_score_above_promote_threshold")

    if review_required and status == DecisionStatus.PROMOTE:
        status = DecisionStatus.HOLD
        review_required = True

    return ReliabilityDecision(
        decision_id=f"dec_{scores.candidate_id}",
        candidate_id=scores.candidate_id,
        final_score=scores.final_reliability_score,
        status=status,
        sub_scores=scores.to_dict(),
        reasons=reasons,
        review_required=review_required,
    )
