"""SE-MRM Calibration Test — проверит что модуль различает хороших и плохих кандидатов.

Тест создаёт 3 группы синтетических кандидатов:
  A. Stable (известно стабильные материалы) — должны получить promote
  B. Marginal (пограничные) — должны получить hold
  C. Unstable (известно нестабильные) — должны получить kill

Это НЕ smoke test. Это проверка того, что scoring + decision логика
даёт осмысленную селекцию, а не отправляет всё в hold.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from skeptic_mrm.falsification import RuleBasedAttackPolicy, run_falsification_suite
from skeptic_mrm.normalize import normalize_candidates
from skeptic_mrm.reports import generate_candidate_report
from skeptic_mrm.runner import MRMConfig, MRMRunner
from skeptic_mrm.schemas.material_candidate import MaterialCandidate
from skeptic_mrm.schemas.simulation_run import SimulationRun
from skeptic_mrm.simulation_backends import ISimulationBackend, MatterSimBackendStub
from skeptic_mrm.scoring import compute_scores, make_decision


# ── Calibrated backend с разными профилями ─────────────────────────


class CalibratedStubBackend(ISimulationBackend):
    """Stub backend, который возвращает РАЗНЫЕ метрики для разных типов кандидатов.

    Это ключевой тест: если модуль не может различить stable vs unstable
    даже при явном сигнале в метриках — проблема в scoring/decision логике.
    """

    def __init__(self) -> None:
        self._run_counter = 0
        # Профили метрик для разных типов
        self._profiles: dict[str, dict] = {
            "stable": {
                "relaxation_converged": True,
                "energy_proxy": -4.5,        # глубокая энергия → стабильность
                "dynamic_stability_proxy": 0.92,  # высокая динамическая стабильность
                "temperature_resilience": 0.88,
                "pressure_resilience": 0.85,
                "property_drop": 0.02,
                "collapsed": 0.0,
                "stress_hotspots_detected": False,
            },
            "marginal": {
                "relaxation_converged": True,
                "energy_proxy": -2.0,
                "dynamic_stability_proxy": 0.55,
                "temperature_resilience": 0.45,
                "pressure_resilience": 0.40,
                "property_drop": 0.15,
                "collapsed": 0.0,
                "stress_hotspots_detected": True,
            },
            "unstable": {
                "relaxation_converged": False,
                "energy_proxy": -0.5,        # мелкая энергия → нестабильность
                "dynamic_stability_proxy": 0.15,  # низкая динамическая стабильность
                "temperature_resilience": 0.10,
                "pressure_resilience": 0.08,
                "property_drop": 0.60,
                "collapsed": 1.0,
                "stress_hotspots_detected": True,
            },
        }

    def relax(self, candidate: MaterialCandidate, config: dict | None = None) -> SimulationRun:
        self._run_counter += 1
        profile = self._get_profile(candidate)
        return SimulationRun(
            run_id=f"cal_{self._run_counter:06d}",
            candidate_id=candidate.candidate_id,
            backend="calibrated_stub",
            tier=1,
            config_version="calibrated-0.1",
            status="completed" if profile["relaxation_converged"] else "diverged",
            metrics={
                "energy_proxy": profile["energy_proxy"],
                "dynamic_stability_proxy": profile["dynamic_stability_proxy"],
                "temperature_resilience": profile["temperature_resilience"],
                "pressure_resilience": profile["pressure_resilience"],
            },
            artifacts={},
        )

    def simulate(self, candidate: MaterialCandidate, scenario: dict) -> SimulationRun:
        self._run_counter += 1
        profile = self._get_profile(candidate)
        return SimulationRun(
            run_id=f"cal_{self._run_counter:06d}",
            candidate_id=candidate.candidate_id,
            backend="calibrated_stub",
            tier=1,
            config_version="calibrated-0.1",
            status="completed",
            metrics={
                "property_drop": profile["property_drop"],
                "collapsed": profile["collapsed"],
                "stress_hotspots_detected": profile["stress_hotspots_detected"],
            },
            artifacts={},
        )

    def supports(self) -> dict:
        return {"name": "CalibratedStub", "status": "calibration_test"}

    def _get_profile(self, candidate: MaterialCandidate) -> dict:
        # Определяем тип из target_properties или composition
        target = candidate.target_properties or {}
        ptype = target.get("_profile_type", "marginal")
        return self._profiles.get(ptype, self._profiles["marginal"])


# ── Генерация тестовых кандидатов ──────────────────────────────────

# Известно стабильные материалы (литий-ионные катоды, перовскиты)
STABLE_MATERIALS = [
    ("LiFePO4", "olivetine_cathode"),
    ("LiCoO2", "layered_cathode"),
    ("CaTiO3", "perovskite"),
    ("MgO", "rock_salt"),
    ("Al2O3", "corundum"),
    ("SiO2", "quartz"),
    ("TiO2", "rutile"),
    ("NaCl", "halite"),
]

# Пограничные (гипотетические, с дефектами, high-energy phases)
MARGINAL_MATERIALS = [
    ("Li2MnO3", "layered_with_disorder"),
    ("LiNi0.5Mn1.5O4", "high_voltage_spinell"),
    ("SrTiO3", "doped_perovskite"),
    ("ZnO", "wurtzite_defective"),
    ("GaN", "wurtzite_strained"),
]

# Известно нестабильные (high-symmetry гипотетические, metastable)
UNSTABLE_MATERIALS = [
    ("CsAuCl3", "hypothetical_perovskite"),
    ("LiMn2O4_highT", "high_temp_phase"),
    ("FeO_rocksalt", "nonstoichiometric"),
    ("CaC2_polymorph", "hypothetical_polymorph"),
]


def _create_test_candidates() -> list[MaterialCandidate]:
    candidates: list[MaterialCandidate] = []
    idx = 0

    for comp, desc in STABLE_MATERIALS:
        candidates.append(MaterialCandidate(
            candidate_id=f"stable_{idx:03d}",
            source="calibration_test",
            composition=comp,
            structure_format="json",
            structure_blob=f'{{"material": "{comp}", "desc": "{desc}"}}',
            target_properties={"_profile_type": "stable", "band_gap": 2.0},
        ))
        idx += 1

    for comp, desc in MARGINAL_MATERIALS:
        candidates.append(MaterialCandidate(
            candidate_id=f"marginal_{idx:03d}",
            source="calibration_test",
            composition=comp,
            structure_format="json",
            structure_blob=f'{{"material": "{comp}", "desc": "{desc}"}}',
            target_properties={"_profile_type": "marginal", "band_gap": 1.5},
        ))
        idx += 1

    for comp, desc in UNSTABLE_MATERIALS:
        candidates.append(MaterialCandidate(
            candidate_id=f"unstable_{idx:03d}",
            source="calibration_test",
            composition=comp,
            structure_format="json",
            structure_blob=f'{{"material": "{comp}", "desc": "{desc}"}}',
            target_properties={"_profile_type": "unstable", "band_gap": 0.5},
        ))
        idx += 1

    return candidates


# ── Запуск теста ───────────────────────────────────────────────────


@dataclass(frozen=True)
class CalibrationResult:
    expected: str  # "stable", "marginal", "unstable"
    total: int
    promoted: int
    held: int
    killed: int
    avg_score: float
    misclassified: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "expected": self.expected,
            "total": self.total,
            "promoted": self.promoted,
            "held": self.held,
            "killed": self.killed,
            "avg_score": round(self.avg_score, 3),
            "misclassified": self.misclassified,
            "accuracy": round(1 - len(self.misclassified) / max(self.total, 1), 3),
        }


def run_calibration_test(output_dir: str | Path = "experiments/mrm_bench_v01/results") -> dict:
    """Run calibration test and return results."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    candidates = _create_test_candidates()
    backend = CalibratedStubBackend()
    config = MRMConfig(
        mode="quick",
        simulation_backend="calibrated_stub",
        max_attacks_per_candidate=4,
    )
    # Запускаем вручную для точного контроля
    all_reports = []
    for c in candidates:
        sim = backend.relax(c)
        falsif = run_falsification_suite(c, backend, RuleBasedAttackPolicy(), budget={"max_attacks_per_candidate": 4})
        scores = compute_scores(c, [sim], stress_resilience=falsif.stress_resilience_score, backend="calibrated_stub")
        decision = make_decision(scores)
        report = generate_candidate_report(c, scores, decision, [sim], falsif.attacks)
        all_reports.append(report)

    # Анализ по группам
    groups = {"stable": [], "marginal": [], "unstable": []}
    for r in all_reports:
        profile = r.candidate.target_properties.get("_profile_type", "marginal")
        groups[profile].append(r)

    expected_decisions = {"stable": "promote", "marginal": "hold", "unstable": "kill"}
    results: dict[str, dict] = {}
    total_correct = 0
    total_count = 0

    for group_name, reports in groups.items():
        expected = expected_decisions[group_name]
        promoted = sum(1 for r in reports if r.decision.status.value == "promote")
        held = sum(1 for r in reports if r.decision.status.value == "hold")
        killed = sum(1 for r in reports if r.decision.status.value == "kill")
        avg_score = sum(r.score_bundle.final_reliability_score for r in reports) / len(reports) if reports else 0

        misclassified = []
        for r in reports:
            if r.decision.status.value != expected:
                misclassified.append({
                    "candidate_id": r.candidate.candidate_id,
                    "composition": r.candidate.composition,
                    "score": round(r.score_bundle.final_reliability_score, 3),
                    "got": r.decision.status.value,
                    "expected": expected,
                })

        correct = sum(1 for r in reports if r.decision.status.value == expected)
        total_correct += correct
        total_count += len(reports)

        results[group_name] = {
            "total": len(reports),
            "promoted": promoted,
            "held": held,
            "killed": killed,
            "avg_score": round(avg_score, 3),
            "correct": correct,
            "accuracy": round(correct / max(len(reports), 1), 3),
            "misclassified": misclassified,
        }

    overall_accuracy = round(total_correct / max(total_count, 1), 3)
    results["overall"] = {
        "total": total_count,
        "total_correct": total_correct,
        "accuracy": overall_accuracy,
    }

    # Сохраняем
    results_path = out / "calibration_results.json"
    results_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")

    # Печатаем
    print("=" * 60)
    print("SE-MRM CALIBRATION TEST")
    print("=" * 60)

    for group in ["stable", "marginal", "unstable"]:
        r = results[group]
        expected = expected_decisions[group]
        print(f"\n--- {group.upper()} (expected: {expected}) ---")
        print(f"  Total: {r['total']} | Promoted: {r['promoted']} | Held: {r['held']} | Killed: {r['killed']}")
        print(f"  Avg score: {r['avg_score']}")
        print(f"  Accuracy: {r['accuracy']} ({r['correct']}/{r['total']})")
        if r["misclassified"]:
            print(f"  Misclassified:")
            for m in r["misclassified"]:
                print(f"    {m['candidate_id']} ({m['composition']}) score={m['score']} got={m['got']} expected={m['expected']}")

    print(f"\n{'=' * 60}")
    print(f"OVERALL ACCURACY: {overall_accuracy} ({total_correct}/{total_count})")
    print(f"{'=' * 60}")

    if overall_accuracy >= 0.7:
        print("STATUS: PASSED — модуль различает типы кандидатов")
    elif overall_accuracy >= 0.5:
        print("STATUS: PARTIAL — есть разделение, но нужна калибровка thresholds")
    else:
        print("STATUS: FAILED — scoring/decision логика не разделяет кандидатов")

    print(f"\nResults saved to: {results_path}")
    return results


if __name__ == "__main__":
    run_calibration_test()
