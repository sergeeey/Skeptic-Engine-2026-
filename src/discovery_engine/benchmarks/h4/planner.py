from __future__ import annotations


def build_h4_execution_plan(spec: dict[str, object]) -> list[str]:
    dataset_routes = spec.get("dataset_routes", [])
    baselines = spec.get("baselines", [])
    track_status = str(spec.get("track_status", "active"))
    status_reason = str(spec.get("status_reason", ""))

    default_route = None
    phase2_routes: list[dict[str, object]] = []
    for route in dataset_routes:
        if not isinstance(route, dict):
            continue
        if route.get("default_route"):
            default_route = route
        else:
            phase2_routes.append(route)

    plan: list[str] = []

    if track_status != "active":
        plan.append(
            "H4 is closed after the kill criterion; do not continue benchmark execution without an explicit reopen decision."
        )
        if status_reason:
            plan.append(f"Closure reason: {status_reason}")
        if isinstance(default_route, dict):
            plan.append(
                "Archive default route context only: "
                f"{default_route.get('id')} ({default_route.get('label_type')})."
            )
        plan.append(
            "If H4 is ever reopened, start from a fresh benchmark hypothesis rather than resuming the old scaffold by default."
        )
        return plan

    plan.append(
        "Lock the first executable benchmark route before building any single-cell training pipeline."
    )

    if isinstance(default_route, dict):
        plan.append(
            "Default benchmark route: "
            f"{default_route.get('id')} ({default_route.get('label_type')})."
        )
        for question in default_route.get(
            "blocking_issues",
            default_route.get("blocking_questions", []),
        ):
            plan.append(f"Resolve blocking question: {question}")

    for route in phase2_routes:
        plan.append(f"Keep phase-2 route available: {route.get('id')} ({route.get('label_type')}).")

    for baseline in baselines:
        if isinstance(baseline, dict):
            plan.append(
                f"Prepare {baseline.get('id')} baseline in family {baseline.get('family')}."
            )

    plan.append(
        "Use a shared evaluation harness so TDA and standard single-cell baselines are compared on identical splits."
    )
    plan.append(
        "Do not claim TDA value unless it beats simpler trajectory or state-embedding baselines on a defensible label."
    )
    return plan
