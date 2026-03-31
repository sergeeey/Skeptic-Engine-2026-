"""VerifiedResult — immutable, auditable wrapper for experiment outputs.

Inspired by VeriFind's VerifiedFact: every numerical claim is tied to the code
that produced it, the data it ran on, and the exact moment of execution.

WHY: When a paper says "AUC = 0.978", reviewers ask "how do I know this is real?"
VerifiedResult answers: here is the code hash, the data hash, the package version,
the timestamp, and the random seed. You can reproduce this number exactly.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skeptic_toolkit import __version__


@dataclass(frozen=True)
class VerifiedResult:
    """Immutable, auditable experiment result.

    All fields are set at creation and cannot be modified.
    The result_hash is computed from metrics + code_hash + data_hash,
    providing a tamper-evident fingerprint.
    """

    experiment_id: str
    metrics: dict[str, Any]
    verdict: str

    # Reproducibility provenance
    code_hash: str  # SHA-256 of the script that produced this result
    data_hash: str  # SHA-256 of input data (or manifest describing it)
    random_seed: int | None = None
    package_version: str = field(default_factory=lambda: __version__)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Computed integrity fingerprint
    result_hash: str = field(default="", init=False)

    def __post_init__(self) -> None:
        # WHY: frozen=True prevents assignment, so we use object.__setattr__
        payload = json.dumps(
            {"metrics": self.metrics, "code_hash": self.code_hash, "data_hash": self.data_hash},
            sort_keys=True,
        )
        h = hashlib.sha256(payload.encode()).hexdigest()[:16]
        object.__setattr__(self, "result_hash", h)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for JSON storage."""
        return asdict(self)

    def save(self, path: Path) -> None:
        """Write result to JSON with integrity metadata."""
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @staticmethod
    def hash_file(path: Path) -> str:
        """Compute SHA-256 hex digest of a file (first 16 chars)."""
        h = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        return h
