"""Debate-driven verdict for anomaly detection.

This module implements an adversarial debate pattern to improve verdict quality
under uncertainty. Instead of a single score, three agents argue:
- Prosecutor: Evidence for fabrication/anomaly
- Defense: Evidence for natural variation/innocence
- Judge: Synthesis and final verdict with confidence

Based on the "TradingAgents" pattern where debate improves decision quality.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Argument:
    """A single argument in the debate."""

    claim: str
    evidence: str
    weight: float  # 0.0 to 1.0
    category: str  # e.g., "benford", "p_value", "temporal", "cross_modal"

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim,
            "evidence": self.evidence,
            "weight": self.weight,
            "category": self.category,
        }


@dataclass
class DebateVerdict:
    """The final verdict from the debate."""

    status: str  # "CLEAN", "SUSPICIOUS", "ANOMALOUS", "UNKNOWN"
    confidence: float  # 0.0 to 1.0
    prosecution_score: float
    defense_score: float
    key_evidence: list[Argument] = field(default_factory=list)
    unresolved_points: list[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "confidence": self.confidence,
            "prosecution_score": self.prosecution_score,
            "defense_score": self.defense_score,
            "key_evidence": [a.to_dict() for a in self.key_evidence],
            "unresolved_points": self.unresolved_points,
            "explanation": self.explanation,
        }


class Prosecutor:
    """Argues that the data is fabricated/anomalous."""

    def generate_arguments(self, features: dict[str, Any]) -> list[Argument]:
        """Generate prosecution arguments based on features."""
        args = []

        # Benford Analysis
        if "benford_mace" in features:
            mace = features["benford_mace"]
            if mace > 0.1:
                args.append(
                    Argument(
                        claim="Significant deviation from Benford's Law",
                        evidence=f"MACE={mace:.3f} > 0.1 threshold",
                        weight=min(mace, 1.0),
                        category="benford",
                    )
                )

        # P-Value Clustering
        if "pvalue_frac_below_05" in features:
            frac = features["pvalue_frac_below_05"]
            if frac > 0.3:
                args.append(
                    Argument(
                        claim="Excessive clustering of p-values near significance",
                        evidence=f"{frac:.1%} of p-values in [0.04, 0.05)",
                        weight=frac,
                        category="p_value",
                    )
                )

        # Temporal Drift
        if "temporal_drift_slope" in features:
            slope = features["temporal_drift_slope"]
            p_val = features.get("temporal_drift_p", 1.0)
            if abs(slope) > 0.01 and p_val < 0.01:
                args.append(
                    Argument(
                        claim="Significant temporal drift in reporting patterns",
                        evidence=f"Slope={slope:.4f}, p={p_val:.4f}",
                        weight=1.0 - p_val,
                        category="temporal",
                    )
                )

        # Cross-Modal Inconsistency
        if "cross_modal_corr" in features:
            corr = features["cross_modal_corr"]
            if corr < 0.2:
                args.append(
                    Argument(
                        claim="Low consistency across data modalities",
                        evidence=f"Correlation={corr:.3f} < 0.2",
                        weight=1.0 - corr,
                        category="cross_modal",
                    )
                )

        # Calibrated Score
        if "calibrated_score" in features:
            score = features["calibrated_score"]
            if score > 0.8:
                args.append(
                    Argument(
                        claim="High calibrated anomaly probability",
                        evidence=f"Calibrated Score={score:.3f}",
                        weight=score,
                        category="calibration",
                    )
                )

        return args


class Defense:
    """Argues that the data is natural/valid."""

    def generate_arguments(self, features: dict[str, Any]) -> list[Argument]:
        """Generate defense arguments based on features."""
        args = []

        # Sample Size
        n_samples = features.get("n_samples", 0)
        if n_samples > 1000:
            args.append(
                Argument(
                    claim="Large sample size reduces false positive risk",
                    evidence=f"n={n_samples} observations",
                    weight=0.6,
                    category="sample_size",
                )
            )

        # Benford Compliance
        if "benford_mace" in features:
            mace = features["benford_mace"]
            if mace < 0.05:
                args.append(
                    Argument(
                        claim="Digit distribution is consistent with expectations",
                        evidence=f"MACE={mace:.3f} < 0.05",
                        weight=1.0 - mace,
                        category="benford",
                    )
                )

        # P-Value Diversity
        if "pvalue_entropy" in features:
            entropy = features["pvalue_entropy"]
            if entropy > 2.0:
                args.append(
                    Argument(
                        claim="Diverse p-value distribution suggests honest reporting",
                        evidence=f"Entropy={entropy:.2f}",
                        weight=min(entropy / 3.0, 1.0),
                        category="p_value",
                    )
                )

        # No Temporal Drift
        if "temporal_drift_p" in features:
            p_val = features["temporal_drift_p"]
            if p_val > 0.1:
                args.append(
                    Argument(
                        claim="No significant trend over time",
                        evidence=f"p={p_val:.3f} > 0.1",
                        weight=0.7,
                        category="temporal",
                    )
                )

        # High Cross-Modal Correlation
        if "cross_modal_corr" in features:
            corr = features["cross_modal_corr"]
            if corr > 0.5:
                args.append(
                    Argument(
                        claim="Strong consistency across modalities",
                        evidence=f"Correlation={corr:.3f} > 0.5",
                        weight=corr,
                        category="cross_modal",
                    )
                )

        # Calibrated Score
        if "calibrated_score" in features:
            score = features["calibrated_score"]
            if score < 0.2:
                args.append(
                    Argument(
                        claim="Low calibrated anomaly probability",
                        evidence=f"Calibrated Score={score:.3f}",
                        weight=1.0 - score,
                        category="calibration",
                    )
                )

        return args


class Judge:
    """Synthesizes arguments and renders a verdict."""

    def render_verdict(
        self,
        prosecution: list[Argument],
        defense: list[Argument],
    ) -> DebateVerdict:
        """Calculate final verdict."""
        if not prosecution and not defense:
            return DebateVerdict(
                status="UNKNOWN",
                confidence=0.0,
                prosecution_score=0.0,
                defense_score=0.0,
                explanation="No evidence presented by either side.",
            )

        # Calculate weighted scores
        p_score = sum(a.weight for a in prosecution)
        d_score = sum(a.weight for a in defense)

        # Normalize to 0-1 range relative to each other
        total = p_score + d_score
        if total == 0:
            norm_p = 0.5
            norm_d = 0.5
        else:
            norm_p = p_score / total
            norm_d = d_score / total

        # Determine status
        diff = norm_p - norm_d
        if diff > 0.2:
            status = "ANOMALOUS"
            confidence = min(diff + 0.5, 1.0)
        elif diff > 0.05:
            status = "SUSPICIOUS"
            confidence = 0.5 + diff * 2
        elif diff > -0.05:
            status = "CLEAN"
            confidence = 0.5 + abs(diff) * 2
        else:
            status = "CLEAN"
            confidence = 0.6

        # Key evidence: top arguments from the winning side
        winner = prosecution if norm_p > norm_d else defense
        key_evidence = sorted(winner, key=lambda x: x.weight, reverse=True)[:3]

        # Unresolved points: conflicting categories
        p_cats = {a.category for a in prosecution}
        d_cats = {a.category for a in defense}
        conflicts = p_cats & d_cats
        unresolved = [f"Conflicting evidence on {c}" for c in conflicts]

        # Explanation
        explanation = (
            f"Prosecution scored {p_score:.2f} vs Defense {d_score:.2f}. "
            f"Verdict: {status} (confidence {confidence:.2f})."
        )

        return DebateVerdict(
            status=status,
            confidence=confidence,
            prosecution_score=norm_p,
            defense_score=norm_d,
            key_evidence=key_evidence,
            unresolved_points=unresolved,
            explanation=explanation,
        )


def run_debate(features: dict[str, Any]) -> DebateVerdict:
    """Run the full debate cycle."""
    prosecutor = Prosecutor()
    defense = Defense()
    judge = Judge()

    p_args = prosecutor.generate_arguments(features)
    d_args = defense.generate_arguments(features)

    return judge.render_verdict(p_args, d_args)
