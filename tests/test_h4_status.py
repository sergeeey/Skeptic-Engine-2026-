from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from discovery_engine.benchmarks.h4 import (  # noqa: E402
    H4TaskCard,
    build_h4_audit_plan,
    build_h4_dataset_card,
    build_h4_execution_plan,
    validate_h4_spec,
)


H4_SPEC_PATH = PROJECT_ROOT / "data" / "benchmarks" / "h4_mvp_spec.json"


def _load_h4_spec() -> dict[str, object]:
    return json.loads(H4_SPEC_PATH.read_text(encoding="utf-8"))


def test_h4_spec_declares_closed_track_status() -> None:
    spec = _load_h4_spec()

    assert spec["track_status"] == "closed_after_kill_criterion"
    assert "TDA AUC=0.50" in spec["status_reason"]


def test_h4_task_card_exposes_track_closure() -> None:
    spec = _load_h4_spec()
    task_card = H4TaskCard.from_spec(spec)

    assert task_card.track_status == "closed_after_kill_criterion"
    assert task_card.default_route == "gse164897_melanoma_resistance"
    assert "kill criterion" in task_card.status_reason


def test_h4_closed_track_changes_execution_plan() -> None:
    spec = _load_h4_spec()

    plan = build_h4_execution_plan(spec)

    assert "H4 is closed after the kill criterion" in plan[0]
    assert any("fresh benchmark hypothesis" in item for item in plan)


def test_h4_dataset_card_carries_track_status() -> None:
    spec = _load_h4_spec()
    card = build_h4_dataset_card(spec)

    assert card.track_status == "closed_after_kill_criterion"
    assert card.current_route_id == "gse164897_melanoma_resistance"


def test_h4_audit_plan_is_archival_when_track_closed() -> None:
    spec = _load_h4_spec()
    plan = build_h4_audit_plan(spec)

    assert plan.track_status == "closed_after_kill_criterion"
    assert "archival context" in plan.audit_checks[0]


def test_h4_validator_accepts_closed_spec_and_warns() -> None:
    spec = _load_h4_spec()
    report = validate_h4_spec(spec)

    assert report.is_valid
    assert any("closed after kill criterion" in warning for warning in report.warnings)
