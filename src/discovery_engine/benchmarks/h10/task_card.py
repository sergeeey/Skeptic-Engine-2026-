from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class H10TaskCard:
    candidate_id: str
    title: str
    label_route: str
    label_type: str
    metrics: list[str] = field(default_factory=list)
    baselines: list[str] = field(default_factory=list)
    falsification_rule: str = ""

    @classmethod
    def from_spec(cls, spec: dict[str, object]) -> "H10TaskCard":
        dataset_routes = spec.get("dataset_routes", [])
        default_route = next(
            (
                route
                for route in dataset_routes
                if isinstance(route, dict) and route.get("default_route")
            ),
            {},
        )
        baselines = [
            str(item.get("id"))
            for item in spec.get("baselines", [])
            if isinstance(item, dict)
        ]
        return cls(
            candidate_id=str(spec.get("candidate_id", "H10")),
            title=str(spec.get("title", "")),
            label_route=str(default_route.get("id", "unknown")),
            label_type=str(default_route.get("label_type", "unknown")),
            metrics=[str(item) for item in spec.get("metrics", [])],
            baselines=baselines,
            falsification_rule=str(spec.get("falsification_rule", "")),
        )
