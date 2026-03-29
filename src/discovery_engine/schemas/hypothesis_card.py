from __future__ import annotations

from dataclasses import asdict, dataclass, field

from discovery_engine.enums import RiskTier


def _bounded_score(name: str, value: float) -> float:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0, got {value}.")
    return value


@dataclass(slots=True)
class HypothesisCard:
    id: str
    title: str
    fields_bridged: list[str]
    core_mechanism: str
    known_facts: list[str]
    inferred_bridge: str
    speculative_hypothesis: str
    evidence_source_ids: list[str]
    novelty_score: float
    feasibility_score: float
    falsifiability_score: float
    impact_score: float
    validation_cost: float
    evidence_quality_score: float
    confidence_score: float
    python_mvp: str
    open_data_route: str
    first_falsification_test: str
    objections: list[str] = field(default_factory=list)
    risk_tier: RiskTier = RiskTier.LOW_HANGING

    def __post_init__(self) -> None:
        self.novelty_score = _bounded_score("novelty_score", self.novelty_score)
        self.feasibility_score = _bounded_score("feasibility_score", self.feasibility_score)
        self.falsifiability_score = _bounded_score("falsifiability_score", self.falsifiability_score)
        self.impact_score = _bounded_score("impact_score", self.impact_score)
        self.validation_cost = _bounded_score("validation_cost", self.validation_cost)
        self.evidence_quality_score = _bounded_score("evidence_quality_score", self.evidence_quality_score)
        self.confidence_score = _bounded_score("confidence_score", self.confidence_score)

    @property
    def discovery_score(self) -> float:
        weighted_value = (
            self.novelty_score
            * self.feasibility_score
            * self.falsifiability_score
            * self.impact_score
            * self.evidence_quality_score
        )
        return round(weighted_value / max(self.validation_cost, 0.05), 4)

    def promotion_ready(self) -> bool:
        return all(
            [
                bool(self.evidence_source_ids),
                bool(self.python_mvp.strip()),
                bool(self.first_falsification_test.strip()),
                self.evidence_quality_score >= 0.5,
                self.feasibility_score >= 0.4,
                self.falsifiability_score >= 0.4,
            ]
        )

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["discovery_score"] = self.discovery_score
        data["promotion_ready"] = self.promotion_ready()
        return data
