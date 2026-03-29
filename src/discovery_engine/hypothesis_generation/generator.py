from __future__ import annotations

from discovery_engine.enums import RiskTier
from discovery_engine.schemas import HypothesisCard, SourceRecord
from discovery_engine.semantic_core import CrossDomainLink


def _risk_tier(feasibility: float, impact: float, validation_cost: float) -> RiskTier:
    if feasibility >= 0.65 and validation_cost <= 0.45:
        return RiskTier.LOW_HANGING
    if impact >= 0.75 and feasibility >= 0.45:
        return RiskTier.MEDIUM_RISK
    return RiskTier.MOONSHOT


def _build_card(
    card_id: str,
    donor: SourceRecord,
    target: SourceRecord,
    link: CrossDomainLink,
    transferable_method: str,
) -> HypothesisCard:
    novelty = round(min(0.95, 0.45 + link.link_score), 2)
    feasibility = round(min(0.9, 0.35 + donor.authority_score + target.authority_score / 2), 2)
    falsifiability = 0.72
    impact = round(min(0.92, 0.45 + max(donor.novelty_factor, target.novelty_factor)), 2)
    validation_cost = round(max(0.2, 0.7 - target.novelty_factor / 2), 2)
    evidence_quality = round(max(0.2, (donor.authority_score + target.authority_score) / 2), 2)
    confidence = round(max(0.18, evidence_quality * 0.7), 2)
    tier = _risk_tier(feasibility, impact, validation_cost)

    target_question = target.open_questions[0] if target.open_questions else "an unresolved target problem"
    donor_mechanism = donor.mechanisms[0] if donor.mechanisms else "a transferable mechanism"

    return HypothesisCard(
        id=card_id,
        title=f"Transfer {transferable_method} from {donor.domain} into {target.domain}",
        fields_bridged=[donor.domain, target.domain],
        core_mechanism=(
            f"Use {transferable_method} to probe whether {donor_mechanism} helps explain or model "
            f"{target_question}."
        ),
        known_facts=[
            f"{donor.title} identifies {transferable_method} as relevant within {donor.domain}.",
            f"{target.title} identifies unresolved problems in {target.domain} that may admit a transfer approach.",
        ],
        inferred_bridge=(
            f"Shared bridge tags {', '.join(link.shared_tags)} suggest that {transferable_method} may connect "
            f"{donor.domain} methods to {target.domain} bottlenecks."
        ),
        speculative_hypothesis=(
            f"If {transferable_method} captures structure that current {target.domain} workflows miss, "
            f"then the target problem may become more predictable or more falsifiable."
        ),
        evidence_source_ids=[donor.id, target.id],
        novelty_score=novelty,
        feasibility_score=feasibility,
        falsifiability_score=falsifiability,
        impact_score=impact,
        validation_cost=validation_cost,
        evidence_quality_score=evidence_quality,
        confidence_score=confidence,
        python_mvp=(
            f"Build a narrow Python prototype applying {transferable_method} to a curated {target.domain} "
            f"dataset or surrogate simulation and compare against a simple baseline."
        ),
        open_data_route=(
            f"Start with manually curated {target.domain} seed data, then replace it with verified open datasets "
            f"once acquisition is upgraded."
        ),
        first_falsification_test=(
            f"Reject the hypothesis if {transferable_method} fails to beat or complement a simple baseline on a "
            f"well-scoped {target.domain} task."
        ),
        objections=[
            "Current evidence comes from internal seed notes rather than external verified literature.",
            "The transfer may be only analogical unless later source-level evidence supports a real mechanism.",
        ],
        risk_tier=tier,
    )


def generate_candidate_hypotheses(
    links: list[CrossDomainLink],
    source_index: dict[str, SourceRecord],
) -> list[HypothesisCard]:
    cards: list[HypothesisCard] = []

    for link in links:
        source_a = source_index[link.source_a]
        source_b = source_index[link.source_b]
        methods_a = list(source_a.methods[:2]) or list(link.transferable_methods[:1])
        methods_b = list(source_b.methods[:2]) or list(link.transferable_methods[:1])

        for idx, method in enumerate(methods_a, start=1):
            cards.append(
                _build_card(
                    card_id=f"{link.source_a}-to-{link.source_b}-{idx}",
                    donor=source_a,
                    target=source_b,
                    link=link,
                    transferable_method=method,
                )
            )

        for idx, method in enumerate(methods_b, start=1):
            cards.append(
                _build_card(
                    card_id=f"{link.source_b}-to-{link.source_a}-{idx}",
                    donor=source_b,
                    target=source_a,
                    link=link,
                    transferable_method=method,
                )
            )

    return cards
