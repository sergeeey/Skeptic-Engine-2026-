"""MaterialCandidate schema."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class MaterialCandidate:
    """Represents a single inorganic crystal candidate for reliability screening."""

    candidate_id: str
    source: str  # "mattergen", "materials_project", "cif_upload", etc.
    composition: str  # e.g. "Li2MnO3"
    structure_format: str  # "cif", "poscar", "json", "mp_id"
    structure_blob: str  # raw CIF/POSCAR content or MP-ID reference
    generator_version: str | None = None
    generator_seed: int | None = None
    target_properties: dict[str, float] = field(default_factory=dict)
    novelty_context: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    provenance_hash: str = ""

    def __post_init__(self) -> None:
        # Compute provenance hash if not provided
        if not self.provenance_hash:
            payload = json.dumps(
                {
                    "candidate_id": self.candidate_id,
                    "source": self.source,
                    "composition": self.composition,
                    "structure_format": self.structure_format,
                    "structure_blob_hash": hashlib.sha256(self.structure_blob.encode()).hexdigest(),
                },
                sort_keys=True,
            )
            object.__setattr__(
                self, "provenance_hash", hashlib.sha256(payload.encode()).hexdigest()[:16]
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "source": self.source,
            "composition": self.composition,
            "structure_format": self.structure_format,
            "structure_blob": self.structure_blob,
            "generator_version": self.generator_version,
            "generator_seed": self.generator_seed,
            "target_properties": self.target_properties,
            "novelty_context": dict(self.novelty_context),
            "created_at": self.created_at,
            "provenance_hash": self.provenance_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MaterialCandidate":
        return cls(
            candidate_id=data["candidate_id"],
            source=data["source"],
            composition=data["composition"],
            structure_format=data["structure_format"],
            structure_blob=data["structure_blob"],
            generator_version=data.get("generator_version"),
            generator_seed=data.get("generator_seed"),
            target_properties=data.get("target_properties", {}),
            novelty_context=data.get("novelty_context", {}),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            provenance_hash=data.get("provenance_hash", ""),
        )
