"""Unit tests for Instinct Memory module."""

from __future__ import annotations

from pathlib import Path

import pytest


# ===========================================================================
# Fixtures
# ===========================================================================
@pytest.fixture
def instinct_module():
    """Import instinct memory module."""
    import sys

    src_dir = Path(__file__).resolve().parents[1] / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from skeptic_engine.utils.instinct_memory import Instinct, InstinctMemory

    return {"Instinct": Instinct, "InstinctMemory": InstinctMemory}


# ===========================================================================
# 1. Instinct
# ===========================================================================
class TestInstinct:
    """Test Instinct dataclass."""

    def test_to_dict(self, instinct_module: dict) -> None:
        """Should convert to dict correctly."""
        inst = instinct_module["Instinct"](
            trigger="Test Trigger",
            action="Test Action",
            confidence=0.9,
            scope="Test Scope",
        )
        d = inst.to_dict()
        assert d["trigger"] == "Test Trigger"
        assert d["confidence"] == 0.9

    def test_from_dict(self, instinct_module: dict) -> None:
        """Should create from dict."""
        data = {
            "trigger": "Test",
            "action": "Action",
            "confidence": 0.8,
            "scope": "Scope",
            "activation_count": 5,
        }
        inst = instinct_module["Instinct"].from_dict(data)
        assert inst.activation_count == 5


# ===========================================================================
# 2. InstinctMemory
# ===========================================================================
class TestInstinctMemory:
    """Test InstinctMemory class."""

    def test_add_and_retrieve(self, instinct_module: dict) -> None:
        """Should add and retrieve instincts."""
        mem = instinct_module["InstinctMemory"]()
        mem.add_instinct(
            instinct_module["Instinct"]("T", "A", 0.9, "scRNA-seq")
        )
        assert len(mem.instincts) == 1

    def test_update_existing(self, instinct_module: dict) -> None:
        """Should update existing instinct if trigger+scope match."""
        mem = instinct_module["InstinctMemory"]()
        mem.add_instinct(
            instinct_module["Instinct"]("T", "Action A", 0.5, "scRNA-seq")
        )
        mem.add_instinct(
            instinct_module["Instinct"]("T", "Action B", 0.9, "scRNA-seq")
        )

        # Should not add new one, but update existing
        assert len(mem.instincts) == 1
        assert mem.instincts[0].confidence == pytest.approx(0.9)
        assert mem.instincts[0].action == "Action B"

    def test_get_relevant(self, instinct_module: dict) -> None:
        """Should return instincts matching scope."""
        mem = instinct_module["InstinctMemory"]()
        mem.add_instinct(
            instinct_module["Instinct"]("T1", "A1", 0.9, "scRNA-seq")
        )
        mem.add_instinct(
            instinct_module["Instinct"]("T2", "A2", 0.8, "proteomics")
        )
        mem.add_instinct(
            instinct_module["Instinct"]("T3", "A3", 0.7, "global")
        )

        ctx = {"data_type": "scRNA-seq", "genes": 1000}
        relevant = mem.get_relevant_instincts(ctx)

        assert len(relevant) == 2  # scRNA-seq + global
        assert relevant[0].confidence >= relevant[1].confidence  # Sorted

    def test_save_and_load(self, instinct_module: dict, tmp_path: Path) -> None:
        """Should persist and load instincts."""
        mem = instinct_module["InstinctMemory"]()
        mem.add_instinct(
            instinct_module["Instinct"]("T", "A", 0.9, "scope")
        )

        save_path = tmp_path / "instincts.json"
        mem.save(save_path)

        mem2 = instinct_module["InstinctMemory"](save_path)
        assert len(mem2.instincts) == 1
        assert mem2.instincts[0].trigger == "T"

    def test_load_nonexistent(self, instinct_module: dict) -> None:
        """Should handle non-existent file gracefully."""
        mem = instinct_module["InstinctMemory"](Path("nonexistent.json"))
        assert len(mem.instincts) == 0
