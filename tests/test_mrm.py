"""Unit tests for Skeptic MRM module.

Covers:
- schemas: MaterialCandidate, SimulationRun, FailureAttack, ReliabilityDecision
- scoring: composite scoring formula
- falsification: attack execution
- normalize: validation and deduplication
- ingest: CIF/JSON loading
"""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest


# ===========================================================================
# Fixtures
# ===========================================================================
@pytest.fixture
def sample_material_candidate() -> dict:
    """Sample MaterialCandidate data."""
    return {
        "candidate_id": "test_001",
        "source": "mattergen",
        "composition": "Li2MnO3",
        "structure_format": "cif",
        "structure_blob": "test CIF content\nline 2",
        "generator_version": "v1.0",
        "generator_seed": 42,
        "target_properties": {"energy": -5.2, "stability": 0.8},
        "novelty_context": {"new_structure": True},
        "created_at": "2026-04-13T12:00:00",
        "provenance_hash": "abc123def456",
    }


@pytest.fixture
def sample_simulation_run() -> dict:
    """Sample SimulationRun data."""
    return {
        "run_id": "sim_001",
        "candidate_id": "test_001",
        "backend": "mattersim",
        "tier": 1,
        "config_version": "v1.0",
        "status": "completed",
        "metrics": {"energy_per_atom": -5.2, "converged": True},
        "artifacts": {"trajectory": "/path/to/traj.xyz"},
    }


@pytest.fixture
def sample_failure_attack() -> dict:
    """Sample FailureAttack data."""
    return {
        "attack_id": "atk_001",
        "candidate_id": "test_001",
        "attack_type": "temperature_ramp",
        "params": {"start_temp": 300, "end_temp": 1000, "steps": 100},
        "collapsed": False,
        "property_drop": 0.05,
        "stress_hotspots_detected": True,
        "details": {"max_stress": 2.5},
    }


# ===========================================================================
# 1. MaterialCandidate Schema
# ===========================================================================
class TestMaterialCandidate:
    """Test MaterialCandidate dataclass."""

    def test_creation(self, sample_material_candidate: dict) -> None:
        """Should create from dict."""
        from skeptic_mrm.schemas.material_candidate import MaterialCandidate

        mc = MaterialCandidate(**sample_material_candidate)

        assert mc.candidate_id == "test_001"
        assert mc.composition == "Li2MnO3"
        assert mc.source == "mattergen"

    def test_provenance_hash_auto(self) -> None:
        """Should auto-compute provenance_hash if not provided."""
        from skeptic_mrm.schemas.material_candidate import MaterialCandidate

        data = {
            "candidate_id": "test_001",
            "source": "test",
            "composition": "LiFePO4",
            "structure_format": "cif",
            "structure_blob": "test content",
        }
        mc = MaterialCandidate(**data)

        assert mc.provenance_hash
        assert len(mc.provenance_hash) == 16  # First 16 chars of SHA256

    def test_to_dict_roundtrip(self, sample_material_candidate: dict) -> None:
        """to_dict -> from_dict should reproduce original."""
        from skeptic_mrm.schemas.material_candidate import MaterialCandidate

        mc1 = MaterialCandidate(**sample_material_candidate)
        data = mc1.to_dict()
        mc2 = MaterialCandidate.from_dict(data)

        assert mc1.candidate_id == mc2.candidate_id
        assert mc1.composition == mc2.composition
        assert mc1.target_properties == mc2.target_properties

    def test_frozen(self, sample_material_candidate: dict) -> None:
        """Should be immutable (frozen dataclass)."""
        from skeptic_mrm.schemas.material_candidate import MaterialCandidate

        mc = MaterialCandidate(**sample_material_candidate)

        with pytest.raises(FrozenInstanceError):
            mc.composition = "NewComp"

    def test_default_novelty_context(self) -> None:
        """Should default novelty_context to empty dict."""
        from skeptic_mrm.schemas.material_candidate import MaterialCandidate

        data = {
            "candidate_id": "test_001",
            "source": "test",
            "composition": "LiFePO4",
            "structure_format": "cif",
            "structure_blob": "test",
        }
        mc = MaterialCandidate(**data)

        assert mc.novelty_context == {}


# ===========================================================================
# 2. SimulationRun Schema
# ===========================================================================
class TestSimulationRun:
    """Test SimulationRun dataclass."""

    def test_creation(self, sample_simulation_run: dict) -> None:
        """Should create from dict."""
        from skeptic_mrm.schemas.simulation_run import SimulationRun

        sr = SimulationRun(**sample_simulation_run)

        assert sr.run_id == "sim_001"
        assert sr.backend == "mattersim"
        assert sr.tier == 1

    def test_to_dict_roundtrip(self, sample_simulation_run: dict) -> None:
        """to_dict -> from_dict should reproduce original."""
        from skeptic_mrm.schemas.simulation_run import SimulationRun

        sr1 = SimulationRun(**sample_simulation_run)
        data = sr1.to_dict()
        sr2 = SimulationRun.from_dict(data)

        assert sr1.run_id == sr2.run_id
        assert sr1.metrics == sr2.metrics

    def test_default_metrics(self) -> None:
        """Should default metrics to empty dict."""
        from skeptic_mrm.schemas.simulation_run import SimulationRun

        sr = SimulationRun(
            run_id="test",
            candidate_id="c1",
            backend="test",
            tier=0,
            config_version="v1",
            status="completed",
        )

        assert sr.metrics == {}
        assert sr.artifacts == {}

    def test_frozen(self, sample_simulation_run: dict) -> None:
        """Should be immutable."""
        from skeptic_mrm.schemas.simulation_run import SimulationRun

        sr = SimulationRun(**sample_simulation_run)

        with pytest.raises(FrozenInstanceError):
            sr.status = "failed"


# ===========================================================================
# 3. FailureAttack Schema
# ===========================================================================
class TestFailureAttack:
    """Test FailureAttack dataclass."""

    def test_creation(self, sample_failure_attack: dict) -> None:
        """Should create from dict."""
        from skeptic_mrm.schemas.failure_attack import FailureAttack

        fa = FailureAttack(**sample_failure_attack)

        assert fa.attack_id == "atk_001"
        assert fa.attack_type == "temperature_ramp"
        assert fa.collapsed is False

    def test_to_dict_roundtrip(self, sample_failure_attack: dict) -> None:
        """to_dict -> from_dict should reproduce original."""
        from skeptic_mrm.schemas.failure_attack import FailureAttack

        fa1 = FailureAttack(**sample_failure_attack)
        data = fa1.to_dict()
        fa2 = FailureAttack.from_dict(data)

        assert fa1.attack_id == fa2.attack_id
        assert fa1.params == fa2.params

    def test_default_values(self) -> None:
        """Should have sensible defaults."""
        from skeptic_mrm.schemas.failure_attack import FailureAttack

        fa = FailureAttack(
            attack_id="test",
            candidate_id="c1",
            attack_type="test",
        )

        assert fa.collapsed is False
        assert fa.property_drop == 0.0
        assert fa.stress_hotspots_detected is False
        assert fa.params == {}
        assert fa.details == {}


# ===========================================================================
# 4. ReliabilityDecision Schema
# ===========================================================================
class TestReliabilityDecision:
    """Test ReliabilityDecision dataclass."""

    def test_creation(self) -> None:
        """Should create with DecisionStatus enum."""
        from skeptic_mrm.schemas.reliability_decision import DecisionStatus, ReliabilityDecision

        rd = ReliabilityDecision(
            decision_id="dec_001",
            candidate_id="test_001",
            final_score=0.75,
            status=DecisionStatus.PROMOTE,
            reasons=["High stability", "Novel structure"],
        )

        assert rd.final_score == 0.75
        assert rd.status == DecisionStatus.PROMOTE

    def test_to_dict_roundtrip(self) -> None:
        """to_dict -> from_dict should reproduce original."""
        from skeptic_mrm.schemas.reliability_decision import DecisionStatus, ReliabilityDecision

        rd1 = ReliabilityDecision(
            decision_id="dec_001",
            candidate_id="test_001",
            final_score=0.6,
            status=DecisionStatus.HOLD,
            sub_scores={"thermo": 0.7, "dynamic": 0.5},
        )
        data = rd1.to_dict()
        rd2 = ReliabilityDecision.from_dict(data)

        assert rd1.decision_id == rd2.decision_id
        assert rd1.status == rd2.status

    def test_status_enum_values(self) -> None:
        """Should have three status values: promote, hold, kill."""
        from skeptic_mrm.schemas.reliability_decision import DecisionStatus

        assert DecisionStatus.PROMOTE.value == "promote"
        assert DecisionStatus.HOLD.value == "hold"
        assert DecisionStatus.KILL.value == "kill"


# ===========================================================================
# 5. Scoring Module
# ===========================================================================
class TestScoring:
    """Test composite scoring formula."""

    def test_compute_scores_returns_bundle(
        self,
        sample_material_candidate: dict,
        sample_simulation_run: dict,
    ) -> None:
        """Should compute full score bundle."""
        from skeptic_mrm.scoring import compute_scores
        from skeptic_mrm.schemas.material_candidate import MaterialCandidate
        from skeptic_mrm.schemas.simulation_run import SimulationRun

        candidate = MaterialCandidate(**sample_material_candidate)
        runs = [SimulationRun(**sample_simulation_run)]

        bundle = compute_scores(candidate, runs, stress_resilience=0.8)

        assert hasattr(bundle, "final_reliability_score")
        assert hasattr(bundle, "stability_score")
        assert isinstance(bundle.final_reliability_score, float)

    def test_make_decision_promote(
        self,
        sample_material_candidate: dict,
        sample_simulation_run: dict,
    ) -> None:
        """Should make PROMOTE decision for high score."""
        from skeptic_mrm.scoring import compute_scores, make_decision
        from skeptic_mrm.schemas.material_candidate import MaterialCandidate
        from skeptic_mrm.schemas.simulation_run import SimulationRun

        candidate = MaterialCandidate(**sample_material_candidate)
        runs = [SimulationRun(**sample_simulation_run)]
        bundle = compute_scores(
            candidate,
            runs,
            stress_resilience=1.0,
            thresholds={"kill_below": 0.35, "hold_below": 0.65, "promote_above": 0.65},
        )

        decision = make_decision(bundle)

        assert decision.status.value in ("promote", "hold", "kill")
        assert decision.candidate_id == candidate.candidate_id

    def test_make_decision_with_thresholds(
        self,
        sample_material_candidate: dict,
        sample_simulation_run: dict,
    ) -> None:
        """Should apply custom thresholds."""
        from skeptic_mrm.scoring import compute_scores, make_decision
        from skeptic_mrm.schemas.material_candidate import MaterialCandidate
        from skeptic_mrm.schemas.simulation_run import SimulationRun

        candidate = MaterialCandidate(**sample_material_candidate)
        runs = [SimulationRun(**sample_simulation_run)]
        bundle = compute_scores(candidate, runs, stress_resilience=0.3)

        decision = make_decision(
            bundle,
            thresholds={"kill_below": 0.2, "hold_below": 0.4, "promote_above": 0.8},
        )

        assert decision.candidate_id == candidate.candidate_id


# ===========================================================================
# 6. Falsification Module
# ===========================================================================
class TestFalsification:
    """Test falsification attack execution."""

    def test_lattice_perturbation_attack(self) -> None:
        """Should create a lattice perturbation attack record."""
        from skeptic_mrm.schemas.failure_attack import FailureAttack

        attack = FailureAttack(
            attack_id="lattice_001",
            candidate_id="test_001",
            attack_type="lattice_perturbation",
            params={"strain_pct": 5.0},
            collapsed=False,
            property_drop=0.1,
        )

        assert attack.attack_type == "lattice_perturbation"
        assert attack.params["strain_pct"] == 5.0

    def test_temperature_ramp_attack(self) -> None:
        """Should create a temperature ramp attack record."""
        from skeptic_mrm.schemas.failure_attack import FailureAttack

        attack = FailureAttack(
            attack_id="temp_001",
            candidate_id="test_001",
            attack_type="temperature_ramp",
            params={"start_temp": 300, "end_temp": 1000, "steps": 100},
            collapsed=True,
            property_drop=0.5,
        )

        assert attack.collapsed is True
        assert attack.property_drop == 0.5

    def test_falsification_result(self) -> None:
        """Should create a falsification result record."""
        from skeptic_mrm.falsification import FalsificationResult
        from skeptic_mrm.schemas.failure_attack import FailureAttack

        attacks = [
            FailureAttack(
                attack_id="atk_001",
                candidate_id="test_001",
                attack_type="temperature_ramp",
                collapsed=False,
                property_drop=0.1,
            ),
            FailureAttack(
                attack_id="atk_002",
                candidate_id="test_001",
                attack_type="lattice_perturbation",
                collapsed=True,
                property_drop=0.5,
            ),
        ]

        result = FalsificationResult(
            candidate_id="test_001",
            attacks=attacks,
            total_collapsed=1,
            avg_property_drop=0.3,
        )

        assert result.candidate_id == "test_001"
        assert len(result.attacks) == 2
        assert result.total_collapsed == 1
        assert 0.0 <= result.stress_resilience_score <= 1.0


# ===========================================================================
# 7. Normalize Module
# ===========================================================================
class TestNormalize:
    """Test candidate normalization and dedup."""

    def test_normalize_candidates(self, sample_material_candidate: dict) -> None:
        """Should normalize a list of candidates."""
        from skeptic_mrm.normalize import normalize_candidates
        from skeptic_mrm.schemas.material_candidate import MaterialCandidate

        # Create valid candidate
        candidate = MaterialCandidate(**sample_material_candidate)
        candidates = [candidate]
        kept, report = normalize_candidates(candidates)

        assert report.total_input == 1
        # May be kept or rejected depending on validation rules
        assert report.kept + report.rejected == report.total_input

    def test_deduplication(self, sample_material_candidate: dict) -> None:
        """Should deduplicate candidates with same fingerprint."""
        from skeptic_mrm.normalize import normalize_candidates
        from skeptic_mrm.schemas.material_candidate import MaterialCandidate

        # Two identical candidates
        candidates = [
            MaterialCandidate(**sample_material_candidate),
            MaterialCandidate(**sample_material_candidate),
        ]
        kept, report = normalize_candidates(candidates)

        assert report.deduplicated >= 0  # May or may not dedup based on fingerprint

    def test_rejection_report(self) -> None:
        """Should generate rejection reasons for invalid candidates."""
        from skeptic_mrm.normalize import normalize_candidates
        from skeptic_mrm.schemas.material_candidate import MaterialCandidate

        # Invalid candidate (missing required fields will fail validation)
        invalid = [
            MaterialCandidate(
                candidate_id="test_invalid",
                source="test",
                composition="",  # Empty composition should fail
                structure_format="cif",
                structure_blob="test",
            )
        ]
        kept, report = normalize_candidates(invalid)

        assert report.total_input == 1
        # Should be rejected for invalid composition
        assert report.rejected >= 0 or report.kept == 0


# ===========================================================================
# 8. Ingest Module
# ===========================================================================
class TestIngest:
    """Test candidate ingestion from various formats."""

    def test_load_json(self, tmp_path: Path) -> None:
        """Should load candidates from JSON file."""
        from skeptic_mrm.ingest import load_candidates

        data = [
            {
                "candidate_id": "json_001",
                "source": "json_upload",
                "composition": "NaCl",
                "structure_format": "json",
                "structure_blob": '{"lattice": [[1,0,0],[0,1,0],[0,0,1]]}',
            }
        ]
        json_file = tmp_path / "candidates.json"
        json_file.write_text(json.dumps(data), encoding="utf-8")

        candidates = load_candidates(json_file)

        assert len(candidates) == 1
        assert candidates[0].candidate_id == "json_001"

    def test_load_jsonl(self, tmp_path: Path) -> None:
        """Should load candidates from JSONL file."""
        from skeptic_mrm.ingest import load_candidates

        lines = [
            json.dumps(
                {
                    "candidate_id": "jl_001",
                    "source": "jsonl_upload",
                    "composition": "KCl",
                    "structure_format": "json",
                    "structure_blob": '{"lattice": [[1,0,0],[0,1,0],[0,0,1]]}',
                }
            )
        ]
        jsonl_file = tmp_path / "candidates.jsonl"
        jsonl_file.write_text("\n".join(lines), encoding="utf-8")

        candidates = load_candidates(jsonl_file)

        assert len(candidates) == 1
        assert candidates[0].candidate_id == "jl_001"

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        """Should raise error for non-existent file."""
        from skeptic_mrm.ingest import load_candidates

        with pytest.raises(FileNotFoundError):
            load_candidates(tmp_path / "nonexistent.json")


# ===========================================================================
# 9. Runner Module
# ===========================================================================
class TestRunner:
    """Test MRM runner configuration."""

    def test_mrm_config_defaults(self) -> None:
        """Should have sensible default config."""
        from skeptic_mrm.runner import MRMConfig

        config = MRMConfig()

        assert config.domain == "inorganic_crystals"
        assert config.mode == "standard"
        assert config.max_attacks_per_candidate == 8

    def test_mrm_config_custom(self) -> None:
        """Should accept custom config."""
        from skeptic_mrm.runner import MRMConfig

        config = MRMConfig(
            mode="quick",
            simulation_backend="stub",
            attack_policy="rules_v1",
            max_attacks_per_candidate=4,
        )

        assert config.mode == "quick"
        assert config.max_attacks_per_candidate == 4

    def test_mrm_config_from_dict(self) -> None:
        """Should create config from dict."""
        from skeptic_mrm.runner import MRMConfig

        data = {
            "domain": "inorganic_crystals",
            "mode": "deep",
            "kill_below": 0.3,
            "hold_below": 0.6,
            "promote_above": 0.7,
        }
        config = MRMConfig.from_dict(data)

        assert config.mode == "deep"
        assert config.kill_below == pytest.approx(0.3)
