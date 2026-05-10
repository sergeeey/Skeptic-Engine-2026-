"""Eval runner for benchmarking LLM models on Skeptic Engine tasks.

Usage:
    python eval/runner.py --model claude-sonnet-4.5 --tasks eval/tasks/*.yaml
    python eval/runner.py --model gpt-4 --task eval/tasks/01_bugfix_hash_lowercase.yaml
    python eval/runner.py --baseline  # Run without LLM (manual human baseline)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml


def load_task(task_path: Path) -> dict[str, Any]:
    """Load task definition from YAML file."""
    with open(task_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_worktree(task_id: str) -> Path:
    """Create isolated git worktree for task execution."""
    worktree_path = Path(tempfile.mkdtemp(prefix=f"eval_{task_id}_"))

    # Create worktree from current branch
    subprocess.run(
        ["git", "worktree", "add", str(worktree_path), "HEAD"],
        check=True,
        capture_output=True,
    )

    return worktree_path


def cleanup_worktree(worktree_path: Path) -> None:
    """Remove git worktree after task execution."""
    subprocess.run(
        ["git", "worktree", "remove", str(worktree_path), "--force"],
        check=False,  # Don't fail if already removed
        capture_output=True,
    )


def run_tests(worktree_path: Path, timeout: int = 300) -> dict[str, Any]:
    """Run pytest in worktree and return results."""
    result = subprocess.run(
        ["pytest", "tests/", "-v", "--tb=short"],
        cwd=worktree_path,
        capture_output=True,
        timeout=timeout,
        text=True,
    )

    return {
        "passed": result.returncode == 0,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def run_lint(worktree_path: Path, timeout: int = 60) -> dict[str, Any]:
    """Run ruff linter and return results."""
    result = subprocess.run(
        ["ruff", "check", "src/", "tests/"],
        cwd=worktree_path,
        capture_output=True,
        timeout=timeout,
        text=True,
    )

    return {
        "passed": result.returncode == 0,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def get_diff(worktree_path: Path) -> str:
    """Get git diff of changes made in worktree."""
    result = subprocess.run(
        ["git", "diff", "HEAD"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
    )
    return result.stdout


def score_task(task: dict, test_result: dict, lint_result: dict, diff: str) -> dict[str, Any]:
    """Compute score for task based on acceptance criteria."""
    scores = {}
    total = 0
    max_total = 100

    # Test pass score
    if test_result["passed"]:
        scores["pass_tests"] = task["scoring"]["pass_tests"]
        total += scores["pass_tests"]
    else:
        scores["pass_tests"] = 0

    # Lint clean score
    if lint_result["passed"]:
        scores["lint_clean"] = task["scoring"]["lint_clean"]
        total += scores["lint_clean"]
    else:
        scores["lint_clean"] = 0

    # Minimal diff score (heuristic: penalize large diffs)
    lines_changed = len(diff.split("\n"))
    if "minimal_diff" in task["scoring"]:
        if lines_changed <= 20:
            scores["minimal_diff"] = task["scoring"]["minimal_diff"]
        elif lines_changed <= 50:
            scores["minimal_diff"] = task["scoring"]["minimal_diff"] // 2
        else:
            scores["minimal_diff"] = 0
        total += scores["minimal_diff"]

    # No regression score (if all tests pass)
    if "no_regression" in task["scoring"]:
        if test_result["passed"]:
            scores["no_regression"] = task["scoring"]["no_regression"]
            total += scores["no_regression"]
        else:
            scores["no_regression"] = 0

    return {
        "total": total,
        "max": max_total,
        "percentage": (total / max_total) * 100,
        "breakdown": scores,
    }


def run_task(task_path: Path, model: str | None = None, auto: bool = False) -> dict[str, Any]:
    """Execute single task and return results."""
    task = load_task(task_path)
    print(f"\n{'='*60}")
    print(f"Task: {task['id']}")
    print(f"Type: {task['type']} | Difficulty: {task['difficulty']}")
    print(f"{'='*60}")

    # Create isolated worktree
    worktree_path = create_worktree(task["id"])
    print(f"Worktree: {worktree_path}")

    try:
        # TODO: Call LLM API to solve task (placeholder for now)
        if model:
            print(f"\n[LLM] Model: {model}")
            print(f"[LLM] Prompt: {task['prompt'][:100]}...")
            print("[LLM] Response: (not implemented — manual mode)")

            # Check if auto mode (skip manual intervention)
            if not auto:
                print("\n⚠️  Manual mode: Apply changes manually in worktree, then press Enter")
                try:
                    input("Press Enter when ready to evaluate...")
                except EOFError:
                    print(
                        "\n⚠️  EOF detected: running in non-interactive mode, skipping manual step"
                    )
            else:
                print("\n⚠️  Auto mode: skipping manual changes, evaluating as-is")

        # Run tests
        print("\n[EVAL] Running tests...")
        test_result = run_tests(worktree_path)
        print(f"  Tests: {'✅ PASS' if test_result['passed'] else '❌ FAIL'}")

        # Run lint
        print("[EVAL] Running lint...")
        lint_result = run_lint(worktree_path)
        print(f"  Lint: {'✅ PASS' if lint_result['passed'] else '❌ FAIL'}")

        # Get diff
        diff = get_diff(worktree_path)
        print(f"[EVAL] Diff: {len(diff.split(chr(10)))} lines changed")

        # Score task
        score = score_task(task, test_result, lint_result, diff)
        print(f"\n[SCORE] {score['total']}/{score['max']} ({score['percentage']:.1f}%)")
        print(f"  Breakdown: {score['breakdown']}")

        return {
            "task_id": task["id"],
            "model": model,
            "score": score,
            "test_result": test_result,
            "lint_result": lint_result,
            "diff": diff,
        }

    finally:
        # Cleanup worktree
        cleanup_worktree(worktree_path)
        print(f"\n[CLEANUP] Removed worktree: {worktree_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Eval runner for Skeptic Engine LLM benchmark")
    parser.add_argument(
        "--model",
        help="Model to evaluate (e.g., claude-sonnet-4.5, gpt-4)",
    )
    parser.add_argument(
        "--task",
        type=Path,
        help="Single task file to run",
    )
    parser.add_argument(
        "--tasks",
        type=str,
        help="Glob pattern for multiple tasks (e.g., eval/tasks/*.yaml)",
    )
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Run baseline (manual human evaluation)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("eval/results/latest.json"),
        help="Output file for results",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Auto mode: skip manual intervention, evaluate code as-is",
    )

    args = parser.parse_args()

    if args.baseline:
        model = "human-baseline"
    elif args.model:
        model = args.model
    else:
        parser.error("Provide --model or --baseline")

    # Collect tasks
    if args.task:
        task_files = [args.task]
    elif args.tasks:
        import glob

        task_files = [Path(p) for p in glob.glob(args.tasks)]
    else:
        task_files = list(Path("eval/tasks").glob("*.yaml"))

    print(f"Running {len(task_files)} tasks with model: {model}")

    # Run all tasks
    results = []
    for task_file in task_files:
        try:
            result = run_task(task_file, model, auto=args.auto)
            results.append(result)
        except Exception as e:
            print(f"❌ Task {task_file} failed: {e}")
            results.append(
                {
                    "task_id": task_file.stem,
                    "model": model,
                    "error": str(e),
                }
            )

    # Save results
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Results saved: {args.output}")
    print(f"{'='*60}")

    # Summary
    total_score = sum(r.get("score", {}).get("total", 0) for r in results)
    max_score = len(results) * 100
    print(f"\nOverall: {total_score}/{max_score} ({(total_score/max_score)*100:.1f}%)")


if __name__ == "__main__":
    main()
