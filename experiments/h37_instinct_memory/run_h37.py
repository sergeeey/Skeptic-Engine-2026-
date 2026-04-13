"""H37 — Instinct Memory.

Demonstrates how the engine learns from past analyses to guide future ones.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
H37_DIR = Path(__file__).resolve().parent


def run_experiment() -> dict[str, Any]:
    """Run H37 instinct memory experiment."""
    print("=" * 60)
    print("H37: Instinct Memory — Learning from Experience")
    print("=" * 60)

    from skeptic_engine.utils.instinct_memory import Instinct, InstinctMemory

    # 1. Simulate Learning
    print("\n[1/3] Teaching the engine from past results...")
    
    # Create a temporary memory
    memory = InstinctMemory()

    # Teach it lessons from H24, H32, H33
    lessons = [
        {
            "trigger": "scRNA-seq UMI counts",
            "action": "Run Benford check first (fd_1 != 0.3)",
            "confidence": 0.95,
            "scope": "scRNA-seq",
        },
        {
            "trigger": "Proteomics correlation",
            "action": "Prioritize Cross-Modal Consistency",
            "confidence": 0.88,
            "scope": "proteomics",
        },
        {
            "trigger": "P-value sequences",
            "action": "Check temporal drift (frac_just_below_05)",
            "confidence": 0.92,
            "scope": "meta-analysis",
        },
        {
            "trigger": "Small sample size",
            "action": "Lower confidence thresholds",
            "confidence": 0.70,
            "scope": "global",
        },
    ]

    for lesson in lessons:
        memory.add_instinct(Instinct(**lesson))
        print(f"  Learned: {lesson['trigger']}")

    # 2. Test Retrieval
    print("\n[2/3] Testing retrieval with contexts...")
    
    test_contexts = {
        "new_scrna_study": {"data_type": "scRNA-seq", "genes": 30000},
        "new_proteomics": {"data_type": "proteomics", "samples": 50},
        "new_meta_analysis": {"data_type": "p-values"},
        "unknown_type": {"data_type": "weather_data"},
    }

    retrieval_results = {}
    for name, ctx in test_contexts.items():
        instincts = memory.get_relevant_instincts(ctx)
        retrieval_results[name] = [i.to_dict() for i in instincts]
        print(f"  {name}: {len(instincts)} instincts")
        if instincts:
            print(f"    Top: {instincts[0].action}")

    # 3. Persistence Test
    print("\n[3/3] Testing persistence (save/load)...")
    save_path = H37_DIR / "results" / "instincts.json"
    save_path.parent.mkdir(parents=True, exist_ok=True)
    memory.save(save_path)
    
    # Load into new memory
    memory2 = InstinctMemory(save_path)
    assert len(memory2.instincts) == len(memory.instincts)
    print(f"  Loaded {len(memory2.instincts)} instincts from disk.")

    return {
        "experiment": "H37",
        "description": "Instinct Memory",
        "lessons_learned": [i.to_dict() for i in memory.instincts],
        "retrieval_tests": retrieval_results,
        "persistence_check": "OK",
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    
    res = run_experiment()

    out_path = H37_DIR / "results" / "h37_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False, default=str)

    print(f"\nResults saved to: {out_path}")
