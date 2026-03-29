from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class CandidateSeed:
    id: str
    title: str
    fields_bridged: list[str]
    source_document: str
    claimed_discovery_score: float
    priority_rank: int
    verification_status: str
    why_promising: str
    claimed_datasets: list[str] = field(default_factory=list)
    claimed_tools: list[str] = field(default_factory=list)
    minimal_python_route: str = ""
    first_falsification_test: str = ""
    next_verification_step: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "CandidateSeed":
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            fields_bridged=[str(item) for item in data.get("fields_bridged", [])],
            source_document=str(data["source_document"]),
            claimed_discovery_score=float(data.get("claimed_discovery_score", 0.0)),
            priority_rank=int(data.get("priority_rank", 0)),
            verification_status=str(data.get("verification_status", "unknown")),
            why_promising=str(data.get("why_promising", "")),
            claimed_datasets=[str(item) for item in data.get("claimed_datasets", [])],
            claimed_tools=[str(item) for item in data.get("claimed_tools", [])],
            minimal_python_route=str(data.get("minimal_python_route", "")),
            first_falsification_test=str(data.get("first_falsification_test", "")),
            next_verification_step=str(data.get("next_verification_step", "")),
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
