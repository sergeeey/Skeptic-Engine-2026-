"""SE-MRM falsification module — attack library + orchestrator."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from skeptic_mrm.schemas.failure_attack import FailureAttack
from skeptic_mrm.schemas.material_candidate import MaterialCandidate
from skeptic_mrm.schemas.simulation_run import SimulationRun
from skeptic_mrm.simulation_backends import ISimulationBackend

# ── Failure mode taxonomy ──────────────────────────────────────────


FAILURE_MODES = [
    "thermodynamic_instability",
    "dynamic_instability",
    "structure_collapse_after_relaxation",
    "temperature_sensitivity",
    "pressure_sensitivity",
    "defect_sensitivity",
    "symmetry_collapse",
    "property_collapse_under_perturbation",
    "ood_uncertainty",
    "simulation_disagreement",
]


# ── Attack definitions ─────────────────────────────────────────────


@dataclass(frozen=True)
class AttackConfig:
    """Configuration for a single attack type."""

    name: str
    failure_mode: str
    default_params: dict[str, Any] = field(default_factory=dict)


ATTACK_LIBRARY: dict[str, AttackConfig] = {
    "lattice_perturbation": AttackConfig(
        name="lattice_perturbation",
        failure_mode="structure_collapse_after_relaxation",
        default_params={"displacement_std": 0.05},
    ),
    "atomic_displacement": AttackConfig(
        name="atomic_displacement",
        failure_mode="dynamic_instability",
        default_params={"max_displacement_A": 0.1},
    ),
    "temperature_ramp": AttackConfig(
        name="temperature_ramp",
        failure_mode="temperature_sensitivity",
        default_params={"t_start": 300, "t_end": 1200, "steps": 20},
    ),
    "pressure_ramp": AttackConfig(
        name="pressure_ramp",
        failure_mode="pressure_sensitivity",
        default_params={"p_start": 0, "p_end": 50, "steps": 15},
    ),
    "repeated_relaxation": AttackConfig(
        name="repeated_relaxation",
        failure_mode="thermodynamic_instability",
        default_params={"n_cycles": 5},
    ),
    "defect_injection": AttackConfig(
        name="defect_injection",
        failure_mode="defect_sensitivity",
        default_params={"vacancy_fraction": 0.02},
    ),
    "property_target_fragility": AttackConfig(
        name="property_target_fragility",
        failure_mode="property_collapse_under_perturbation",
        default_params={"property": "band_gap", "tolerance": 0.1},
    ),
    "symmetry_perturbation": AttackConfig(
        name="symmetry_perturbation",
        failure_mode="symmetry_collapse",
        default_params={"noise_fraction": 0.01},
    ),
}


# ── Attack policy ──────────────────────────────────────────────────


class IAttackPolicy:
    """Decides which attacks to run next for a candidate."""

    def propose(
        self,
        candidate: MaterialCandidate,
        history: list[FailureAttack],
        budget: dict[str, Any],
    ) -> list[str]:
        raise NotImplementedError


class RuleBasedAttackPolicy(IAttackPolicy):
    """Run a fixed set of attacks in predefined order."""

    def __init__(self, enabled_attacks: list[str] | None = None) -> None:
        self.enabled = enabled_attacks or list(ATTACK_LIBRARY.keys())

    def propose(
        self,
        candidate: MaterialCandidate,
        history: list[FailureAttack],
        budget: dict[str, Any],
    ) -> list[str]:
        already_run = {a.attack_type for a in history}
        remaining = [a for a in self.enabled if a not in already_run]
        max_attacks = budget.get("max_attacks_per_candidate", 8)
        return remaining[:max_attacks]


# ── Falsification orchestrator ─────────────────────────────────────


@dataclass(frozen=True)
class FalsificationResult:
    """Collection of attacks run on a candidate."""

    candidate_id: str
    attacks: list[FailureAttack] = field(default_factory=list)
    total_collapsed: int = 0
    avg_property_drop: float = 0.0
    stress_hotspots: int = 0

    @property
    def stress_resilience_score(self) -> float:
        """Score in [0, 1]. 1.0 = no collapses, no drops."""
        if not self.attacks:
            return 1.0
        collapse_rate = self.total_collapsed / len(self.attacks)
        drop_penalty = min(self.avg_property_drop, 1.0)
        return max(0.0, 1.0 - collapse_rate - 0.3 * drop_penalty)

    def to_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "n_attacks": len(self.attacks),
            "total_collapsed": self.total_collapsed,
            "avg_property_drop": self.avg_property_drop,
            "stress_hotspots": self.stress_hotspots,
            "stress_resilience_score": self.stress_resilience_score,
            "attacks": [a.to_dict() for a in self.attacks],
        }


def _run_single_attack(
    attack_name: str,
    candidate: MaterialCandidate,
    backend: ISimulationBackend,
    attack_config: AttackConfig | None = None,
) -> FailureAttack:
    """Execute a single attack using the simulation backend."""
    config = attack_config or ATTACK_LIBRARY[attack_name]
    attack_id = f"atk_{uuid.uuid4().hex[:8]}"

    # Stub execution: in v0.1, attacks are simulated via the backend
    # Real implementation would modify the structure and re-relax
    params = {**config.default_params}
    scenario = {"type": attack_name, "value": params.get("t_end", params.get("p_end", 1.0))}

    try:
        sim_result = backend.simulate(candidate, scenario)

        collapsed = sim_result.metrics.get("collapsed", 0.0) > 0.5
        prop_drop = float(sim_result.metrics.get("property_drop", 0.05))
        hotspots = bool(sim_result.metrics.get("stress_hotspots_detected", False))
    except Exception:
        # Simulation failure = conservative: treat as collapse
        collapsed = True
        prop_drop = 1.0
        hotspots = True

    return FailureAttack(
        attack_id=attack_id,
        candidate_id=candidate.candidate_id,
        attack_type=attack_name,
        params=params,
        collapsed=collapsed,
        property_drop=prop_drop,
        stress_hotspots_detected=hotspots,
        details={"failure_mode": config.failure_mode},
    )


def run_falsification_suite(
    candidate: MaterialCandidate,
    backend: ISimulationBackend,
    policy: IAttackPolicy,
    attack_history: list[FailureAttack] | None = None,
    budget: dict[str, Any] | None = None,
) -> FalsificationResult:
    """Run a falsification suite on a single candidate.

    Returns FalsificationResult with all attack outcomes.
    """
    history = attack_history or []
    attacks_to_run = policy.propose(candidate, history, budget or {})

    attacks: list[FailureAttack] = []
    for attack_name in attacks_to_run:
        if attack_name not in ATTACK_LIBRARY:
            continue
        attack = _run_single_attack(attack_name, candidate, backend)
        attacks.append(attack)

    total_collapsed = sum(1 for a in attacks if a.collapsed)
    avg_drop = (
        sum(a.property_drop for a in attacks) / len(attacks) if attacks else 0.0
    )
    hotspots = sum(1 for a in attacks if a.stress_hotspots_detected)

    return FalsificationResult(
        candidate_id=candidate.candidate_id,
        attacks=attacks,
        total_collapsed=total_collapsed,
        avg_property_drop=avg_drop,
        stress_hotspots=hotspots,
    )
