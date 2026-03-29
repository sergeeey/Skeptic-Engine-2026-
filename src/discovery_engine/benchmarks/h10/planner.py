from __future__ import annotations


def build_h10_execution_plan(spec: dict[str, object]) -> list[str]:
    dataset_routes = spec.get("dataset_routes", [])
    baselines = spec.get("baselines", [])

    default_route = None
    for route in dataset_routes:
        if isinstance(route, dict) and route.get("default_route"):
            default_route = route
            break

    plan: list[str] = []
    plan.append("Select and validate the default label route before writing training code.")

    if isinstance(default_route, dict):
        plan.append(
            "Default label route: "
            f"{default_route.get('id')} ({default_route.get('label_type')})."
        )
        for question in default_route.get("blocking_questions", []):
            plan.append(f"Resolve blocking question: {question}")

    for baseline in baselines:
        if isinstance(baseline, dict):
            plan.append(
                f"Prepare {baseline.get('id')} baseline in family {baseline.get('family')}."
            )

    plan.append(
        "Use a shared evaluation harness so descriptor, token, and graph baselines are compared on identical splits."
    )
    plan.append(
        "Do not claim graph advantage unless the graph baseline beats simpler baselines on a defensible target."
    )
    return plan
