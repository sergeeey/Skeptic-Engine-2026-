"""SE-MRM generator adapters — abstract interface + stubs."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IGeneratorAdapter(ABC):
    """Abstract interface for a material generator backend."""

    @abstractmethod
    def sample(self, constraints: dict[str, Any] | None = None, n: int = 1) -> list[dict[str, Any]]:
        """Generate n candidate structures. Returns list of raw dicts."""

    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        """Return backend metadata (version, supported elements, etc.)."""


class MatterGenAdapterStub(IGeneratorAdapter):
    """Stub for Microsoft MatterGen integration.

    This adapter does NOT execute generation.
    It returns synthetic candidate stubs for pipeline testing.

    Real integration requires:
    - pip install mattergen
    - model checkpoint access
    - GPU availability
    """

    def __init__(self) -> None:
        self._version = "mattergen-stub-0.1"

    def sample(self, constraints: dict[str, Any] | None = None, n: int = 1) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for i in range(n):
            results.append(
                {
                    "candidate_id": f"mg_{i:06d}",
                    "source": "mattergen",
                    "composition": "LiFePO4",
                    "structure_format": "json",
                    "structure_blob": '{"lattice": [[10,0,0],[0,10,0],[0,0,10]], "sites": []}',
                    "generator_version": self._version,
                    "generator_seed": 42 + i,
                    "target_properties": constraints or {},
                }
            )
        return results

    def metadata(self) -> dict[str, Any]:
        return {
            "name": "MatterGen",
            "version": self._version,
            "status": "stub",
            "note": "Real integration requires mattergen package + checkpoint",
        }
