"""Unit tests for Debate-driven verdict module."""

from __future__ import annotations

import numpy as np
import pytest


# ===========================================================================
# Fixtures
# ===========================================================================
@pytest.fixture
def debate_module():
    """Import debate module."""
    import sys
    from pathlib import Path

    src_dir = Path(__file__).resolve().parents[1] / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from skeptic_engine.utils.debate import (
        Argument,
        DebateVerdict,
        Defense,
        Judge,
        Prosecutor,
        run_debate,
    )

    return {
        "Argument": Argument,
        "DebateVerdict": DebateVerdict,
        "Defense": Defense,
        "Judge": Judge,
        "Prosecutor": Prosecutor,
        "run_debate": run_debate,
    }


# ===========================================================================
# 1. Argument
# ===========================================================================
class TestArgument:
    """Test Argument dataclass."""

    def test_to_dict(self, debate_module: dict) -> None:
        """Should convert to dict correctly."""
        arg = debate_module["Argument"](
            claim="Test Claim",
            evidence="Test Evidence",
            weight=0.8,
            category="test",
        )
        d = arg.to_dict()
        assert d["claim"] == "Test Claim"
        assert d["weight"] == 0.8
        assert d["category"] == "test"


# ===========================================================================
# 2. Prosecutor
# ===========================================================================
class TestProsecutor:
    """Test Prosecutor agent."""

    def test_benford_violation(self, debate_module: dict) -> None:
        """Should flag high Benford MACE."""
        features = {"benford_mace": 0.2}
        p = debate_module["Prosecutor"]()
        args = p.generate_arguments(features)
        
        benford_args = [a for a in args if a.category == "benford"]
        assert len(benford_args) == 1
        assert benford_args[0].weight == pytest.approx(0.2)

    def test_pvalue_clustering(self, debate_module: dict) -> None:
        """Should flag excessive p-value clustering."""
        features = {"pvalue_frac_below_05": 0.4}
        p = debate_module["Prosecutor"]()
        args = p.generate_arguments(features)
        
        pval_args = [a for a in args if a.category == "p_value"]
        assert len(pval_args) == 1
        assert pval_args[0].weight == pytest.approx(0.4)

    def test_no_false_positives_on_clean(self, debate_module: dict) -> None:
        """Should generate no arguments for clean data."""
        features = {
            "benford_mace": 0.01,
            "pvalue_frac_below_05": 0.02,
            "temporal_drift_slope": 0.0,
            "temporal_drift_p": 0.9,
            "cross_modal_corr": 0.8,
            "calibrated_score": 0.05,
        }
        p = debate_module["Prosecutor"]()
        args = p.generate_arguments(features)
        assert len(args) == 0


# ===========================================================================
# 3. Defense
# ===========================================================================
class TestDefense:
    """Test Defense agent."""

    def test_large_sample_size(self, debate_module: dict) -> None:
        """Should argue for large sample sizes."""
        features = {"n_samples": 5000}
        d = debate_module["Defense"]()
        args = d.generate_arguments(features)
        
        sample_args = [a for a in args if a.category == "sample_size"]
        assert len(sample_args) == 1

    def test_benford_compliance(self, debate_module: dict) -> None:
        """Should flag low Benford MACE as innocence."""
        features = {"benford_mace": 0.02}
        d = debate_module["Defense"]()
        args = d.generate_arguments(features)
        
        benford_args = [a for a in args if a.category == "benford"]
        assert len(benford_args) == 1
        assert benford_args[0].weight > 0.9

    def test_no_false_positives_on_anomalous(self, debate_module: dict) -> None:
        """Should generate no arguments for clearly anomalous data."""
        features = {
            "benford_mace": 0.5,
            "pvalue_entropy": 0.5,
            "temporal_drift_p": 0.001,
            "cross_modal_corr": 0.1,
            "calibrated_score": 0.9,
        }
        d = debate_module["Defense"]()
        args = d.generate_arguments(features)
        assert len(args) == 0


# ===========================================================================
# 4. Judge
# ===========================================================================
class TestJudge:
    """Test Judge agent."""

    def test_clear_prosecution_win(self, debate_module: dict) -> None:
        """Should rule ANOMALOUS if prosecution is much stronger."""
        j = debate_module["Judge"]()
        p_args = [
            debate_module["Argument"]("Claim 1", "Ev 1", 0.8, "cat1"),
            debate_module["Argument"]("Claim 2", "Ev 2", 0.9, "cat2"),
        ]
        d_args = [
            debate_module["Argument"]("Claim 3", "Ev 3", 0.1, "cat1"),
        ]
        
        verdict = j.render_verdict(p_args, d_args)
        assert verdict.status == "ANOMALOUS"
        assert verdict.confidence > 0.5

    def test_clear_defense_win(self, debate_module: dict) -> None:
        """Should rule CLEAN if defense is much stronger."""
        j = debate_module["Judge"]()
        p_args = [
            debate_module["Argument"]("Claim 1", "Ev 1", 0.1, "cat1"),
        ]
        d_args = [
            debate_module["Argument"]("Claim 3", "Ev 3", 0.8, "cat1"),
            debate_module["Argument"]("Claim 4", "Ev 4", 0.9, "cat2"),
        ]
        
        verdict = j.render_verdict(p_args, d_args)
        assert verdict.status == "CLEAN"

    def test_conflict_resolution(self, debate_module: dict) -> None:
        """Should mark category as unresolved if both sides argue it."""
        j = debate_module["Judge"]()
        p_args = [
            debate_module["Argument"]("Prosecution Benford", "Ev 1", 0.6, "benford"),
        ]
        d_args = [
            debate_module["Argument"]("Defense Benford", "Ev 3", 0.5, "benford"),
        ]
        
        verdict = j.render_verdict(p_args, d_args)
        assert any("benford" in point for point in verdict.unresolved_points)

    def test_empty_debate(self, debate_module: dict) -> None:
        """Should return UNKNOWN if no arguments."""
        j = debate_module["Judge"]()
        verdict = j.render_verdict([], [])
        assert verdict.status == "UNKNOWN"


# ===========================================================================
# 5. Integration
# ===========================================================================
class TestRunDebate:
    """Test run_debate integration function."""

    def test_suspicious_case(self, debate_module: dict) -> None:
        """Should return a valid verdict for mixed features."""
        features = {
            "benford_mace": 0.15,
            "pvalue_frac_below_05": 0.2,
            "temporal_drift_p": 0.05,
            "cross_modal_corr": 0.4,
            "calibrated_score": 0.6,
        }
        
        verdict = debate_module["run_debate"](features)
        
        assert verdict.status in ("CLEAN", "SUSPICIOUS", "ANOMALOUS")
        assert 0 <= verdict.confidence <= 1
        assert len(verdict.key_evidence) > 0
