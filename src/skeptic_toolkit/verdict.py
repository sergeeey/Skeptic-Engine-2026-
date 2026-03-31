"""Three-level verdict system inspired by VeriFind's fail-closed principle.

Instead of binary "flagged / not flagged", we produce:
  CLEAN      — signals within expected bounds, no action needed
  UNCERTAIN  — borderline scores, expert review recommended
  FLAGGED    — elevated anomaly signal, escalate for investigation

WHY: A scientific integrity tool must never produce false confidence.
"I don't know" (UNCERTAIN) is more honest than a wrong CLEAN or wrong FLAGGED.
The uncertainty band is configurable to match domain-specific risk tolerance.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class VerdictLevel(str, Enum):
    """Three-level verdict for integrity screening."""

    CLEAN = "CLEAN"
    UNCERTAIN = "UNCERTAIN"
    FLAGGED = "FLAGGED"


@dataclass(frozen=True)
class Verdict:
    """Immutable screening verdict with explanation."""

    level: VerdictLevel
    score: float
    threshold_low: float
    threshold_high: float
    explanation: str

    def __str__(self) -> str:
        return (
            f"{self.level.value} (score={self.score:.3f}, "
            f"band=[{self.threshold_low:.2f}, {self.threshold_high:.2f}]): "
            f"{self.explanation}"
        )


def make_verdict(
    score: float,
    *,
    threshold: float = 0.55,
    uncertainty_band: float = 0.10,
) -> Verdict:
    """Produce a three-level verdict from a fabrication risk score.

    Args:
        score: Fabrication risk score in [0, 1].
        threshold: Center of the decision boundary.
        uncertainty_band: Width of the UNCERTAIN zone around the threshold.
            The zone spans [threshold - band/2, threshold + band/2].

    Returns:
        Verdict with level, score, thresholds, and human-readable explanation.
    """
    low = threshold - uncertainty_band / 2
    high = threshold + uncertainty_band / 2

    if score >= high:
        return Verdict(
            level=VerdictLevel.FLAGGED,
            score=score,
            threshold_low=low,
            threshold_high=high,
            explanation="Elevated anomaly signal detected. Escalate for expert review.",
        )
    elif score <= low:
        return Verdict(
            level=VerdictLevel.CLEAN,
            score=score,
            threshold_low=low,
            threshold_high=high,
            explanation="Signals within expected statistical bounds.",
        )
    else:
        return Verdict(
            level=VerdictLevel.UNCERTAIN,
            score=score,
            threshold_low=low,
            threshold_high=high,
            explanation=(
                "Score falls in the uncertainty band. "
                "Cannot confidently classify as clean or anomalous. "
                "Expert review recommended."
            ),
        )
