from __future__ import annotations

from dataclasses import asdict, dataclass, field

from discovery_engine.enums import SourceType


def _bounded_score(name: str, value: float) -> float:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0, got {value}.")
    return value


@dataclass(slots=True)
class SourceRecord:
    id: str
    title: str
    domain: str
    source_type: SourceType
    abstract: str = ""
    claims: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    mechanisms: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    bridge_tags: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    authority_score: float = 0.0
    bias_index: float = 0.0
    novelty_factor: float = 0.0
    citations: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.authority_score = _bounded_score("authority_score", self.authority_score)
        self.bias_index = _bounded_score("bias_index", self.bias_index)
        self.novelty_factor = _bounded_score("novelty_factor", self.novelty_factor)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "SourceRecord":
        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict):
            raise ValueError("metadata must be a dictionary")

        normalized_metadata = {str(key): str(value) for key, value in metadata.items()}
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            domain=str(data["domain"]),
            source_type=SourceType(str(data["source_type"])),
            abstract=str(data.get("abstract", "")),
            claims=[str(item) for item in data.get("claims", [])],
            methods=[str(item) for item in data.get("methods", [])],
            mechanisms=[str(item) for item in data.get("mechanisms", [])],
            open_questions=[str(item) for item in data.get("open_questions", [])],
            bridge_tags=[str(item) for item in data.get("bridge_tags", [])],
            limitations=[str(item) for item in data.get("limitations", [])],
            authority_score=float(data.get("authority_score", 0.0)),
            bias_index=float(data.get("bias_index", 0.0)),
            novelty_factor=float(data.get("novelty_factor", 0.0)),
            citations=[str(item) for item in data.get("citations", [])],
            metadata=normalized_metadata,
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
