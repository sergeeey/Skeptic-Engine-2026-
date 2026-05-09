"""Instinct Memory for Skeptic Engine.

This module implements a simple "instinct" system where the engine
remembers patterns from past analyses to guide future ones.
Based on the "Everything Claude Code" instinct model:
Trigger + Action + Confidence + Scope.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Instinct:
    """A learned pattern from past analysis."""

    trigger: str  # e.g., "scRNA-seq with >50K genes"
    action: str  # e.g., "Prioritize Benford check"
    confidence: float  # 0.0 to 1.0
    scope: str  # e.g., "scRNA-seq only"
    activation_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "trigger": self.trigger,
            "action": self.action,
            "confidence": self.confidence,
            "scope": self.scope,
            "activation_count": self.activation_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Instinct:
        return cls(**data)


class InstinctMemory:
    """Manages the collection of instincts."""

    def __init__(self, storage_path: Path | None = None):
        self.instincts: list[Instinct] = []
        self.storage_path = storage_path
        if storage_path and storage_path.exists():
            self.load(storage_path)

    def add_instinct(self, instinct: Instinct) -> None:
        """Add a new instinct or update existing one."""
        # Check for duplicate trigger+scope
        for existing in self.instincts:
            if existing.trigger == instinct.trigger and existing.scope == instinct.scope:
                # Update action if new confidence is higher
                if instinct.confidence > existing.confidence:
                    existing.action = instinct.action
                    existing.confidence = instinct.confidence

                existing.activation_count += 1
                return

        self.instincts.append(instinct)

    def get_relevant_instincts(self, context: dict[str, Any]) -> list[Instinct]:
        """Get instincts matching the current context."""
        relevant = []
        for inst in self.instincts:
            if self._matches_scope(inst.scope, context):
                relevant.append(inst)

        # Sort by confidence descending
        return sorted(relevant, key=lambda x: x.confidence, reverse=True)

    def _matches_scope(self, scope: str, context: dict[str, Any]) -> bool:
        """Check if scope matches context."""
        scope_lower = scope.lower()
        context_str = " ".join(str(v).lower() for v in context.values())
        return scope_lower in context_str or scope_lower == "global"

    def save(self, path: Path | None = None) -> None:
        """Save instincts to JSON."""
        p = path or self.storage_path
        if not p:
            return

        p.parent.mkdir(parents=True, exist_ok=True)
        data = [i.to_dict() for i in self.instincts]
        with p.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load(self, path: Path) -> None:
        """Load instincts from JSON."""
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        self.instincts = [Instinct.from_dict(d) for d in data]
