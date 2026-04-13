"""FailureAttack schema."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FailureAttack:
    """Records a failure-mode attack on a material candidate."""

    attack_id: str
    candidate_id: str
    attack_type: str  # "temperature_ramp", "pressure_ramp", "lattice_perturbation", etc.
    params: dict[str, object] = field(default_factory=dict)
    collapsed: bool = False
    property_drop: float = 0.0
    stress_hotspots_detected: bool = False
    details: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "attack_id": self.attack_id,
            "candidate_id": self.candidate_id,
            "attack_type": self.attack_type,
            "params": dict(self.params),
            "collapsed": self.collapsed,
            "property_drop": self.property_drop,
            "stress_hotspots_detected": self.stress_hotspots_detected,
            "details": dict(self.details),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FailureAttack":
        return cls(
            attack_id=data["attack_id"],
            candidate_id=data["candidate_id"],
            attack_type=data["attack_type"],
            params=data.get("params", {}),
            collapsed=data.get("collapsed", False),
            property_drop=data.get("property_drop", 0.0),
            stress_hotspots_detected=data.get("stress_hotspots_detected", False),
            details=data.get("details", {}),
        )
