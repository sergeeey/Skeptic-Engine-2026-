"""ReliabilityDecision schema."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class DecisionStatus(str, Enum):
    PROMOTE = "promote"
    HOLD = "hold"
    KILL = "kill"


@dataclass(frozen=True)
class ReliabilityDecision:
    """Final reliability decision for a candidate with scoring rationale."""

    decision_id: str
    candidate_id: str
    final_score: float
    status: DecisionStatus
    sub_scores: dict[str, float] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    review_required: bool = False

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "candidate_id": self.candidate_id,
            "final_score": self.final_score,
            "status": self.status.value,
            "sub_scores": dict(self.sub_scores),
            "reasons": list(self.reasons),
            "review_required": self.review_required,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReliabilityDecision":
        return cls(
            decision_id=data["decision_id"],
            candidate_id=data["candidate_id"],
            final_score=data["final_score"],
            status=DecisionStatus(data["status"]),
            sub_scores=data.get("sub_scores", {}),
            reasons=data.get("reasons", []),
            review_required=data.get("review_required", False),
        )
