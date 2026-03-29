from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class H4RouteCard:
    route_id: str
    title: str
    accession: str
    route_status: str
    disease: str
    unit_of_analysis: str
    evaluation_level: str
    label_type: str
    positive_label: str
    split_unit: str
    group_keys_for_split: list[str] = field(default_factory=list)
    leakage_keys: list[str] = field(default_factory=list)
    label_schema: dict[str, object] = field(default_factory=dict)
    sample_count: int | None = None
    cell_count: int | None = None
    notes: list[str] = field(default_factory=list)
    blocking_issues: list[str] = field(default_factory=list)
    is_default: bool = False


@dataclass(slots=True)
class H4DatasetCard:
    candidate_id: str
    title: str
    current_route_id: str
    current_route_title: str
    phase2_route_ids: list[str] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)
    route_cards: list[H4RouteCard] = field(default_factory=list)


def build_h4_dataset_card(spec: dict[str, object]) -> H4DatasetCard:
    dataset_routes = spec.get("dataset_routes", [])
    route_cards: list[H4RouteCard] = []
    default_route_id = "unknown"
    default_route_title = ""
    phase2_route_ids: list[str] = []

    for route in dataset_routes:
        if not isinstance(route, dict):
            continue
        card = H4RouteCard(
            route_id=str(route.get("id", "unknown")),
            title=str(route.get("title", "")),
            accession=str(route.get("accession", "")),
            route_status=str(route.get("route_status", "unknown")),
            disease=str(route.get("disease", "")),
            unit_of_analysis=str(route.get("unit_of_analysis", "")),
            evaluation_level=str(route.get("evaluation_level", "")),
            label_type=str(route.get("label_type", "")),
            positive_label=str(
                (
                    route.get("label_schema", {}).get("positive_label")
                    if isinstance(route.get("label_schema"), dict)
                    else route.get("positive_label", "")
                )
                or route.get("positive_label", "")
            ),
            split_unit=str(route.get("split_unit", "")),
            group_keys_for_split=[str(item) for item in route.get("group_keys_for_split", [])],
            leakage_keys=[str(item) for item in route.get("leakage_keys", [])],
            label_schema=(
                dict(route.get("label_schema", {}))
                if isinstance(route.get("label_schema"), dict)
                else {}
            ),
            sample_count=(
                int(route["sample_count"]) if isinstance(route.get("sample_count"), int) else None
            ),
            cell_count=(
                int(route["cell_count"]) if isinstance(route.get("cell_count"), int) else None
            ),
            notes=[str(item) for item in route.get("notes", [])],
            blocking_issues=[
                str(item)
                for item in route.get(
                    "blocking_issues",
                    route.get("blocking_questions", []),
                )
            ],
            is_default=bool(route.get("default_route")),
        )
        route_cards.append(card)
        if card.is_default:
            default_route_id = card.route_id
            default_route_title = card.title
        else:
            phase2_route_ids.append(card.route_id)

    return H4DatasetCard(
        candidate_id=str(spec.get("candidate_id", "H4")),
        title=str(spec.get("title", "")),
        current_route_id=default_route_id,
        current_route_title=default_route_title,
        phase2_route_ids=phase2_route_ids,
        metrics=[str(item) for item in spec.get("metrics", [])],
        route_cards=route_cards,
    )
