from __future__ import annotations

from discovery_engine.schemas import HypothesisCard


def rank_hypotheses(cards: list[HypothesisCard]) -> list[HypothesisCard]:
    return sorted(
        cards,
        key=lambda card: (
            card.promotion_ready(),
            card.discovery_score,
            card.evidence_quality_score,
            card.confidence_score,
        ),
        reverse=True,
    )
