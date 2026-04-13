"""SE-MRM CLI — skeptic-mrm command-line interface."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from skeptic_mrm.ingest import load_candidates
from skeptic_mrm.normalize import normalize_candidates
from skeptic_mrm.runner import MRMConfig, MRMRunner


def _ensure_output_dir(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def cmd_ingest(args: list[str]) -> None:
    """skeptic-mrm ingest <input_path>"""
    if len(args) < 1:
        print("Usage: skeptic-mrm ingest <input_path>")
        return
    input_path = Path(args[0])
    candidates = load_candidates(input_path)
    kept, report = normalize_candidates(candidates)
    print(f"Input: {input_path}")
    print(f"Total: {report.total_input} | Kept: {report.kept} | Rejected: {report.rejected} | Deduped: {report.deduplicated}")
    if report.rejections:
        print("Rejections:")
        for r in report.rejections:
            print(f"  - {r['candidate_id']}: {r['reason']}")
    for c in kept[:10]:
        print(f"  - {c.candidate_id} | {c.composition} | format={c.structure_format}")


def cmd_run(args: list[str]) -> None:
    """skeptic-mrm run --input <path> [--backend mattersim] [--mode standard] [--out <dir>]"""
    import argparse

    parser = argparse.ArgumentParser(description="Run MRM pipeline")
    parser.add_argument("--input", required=True, help="Input candidates file")
    parser.add_argument("--backend", default="mattersim", help="Simulation backend")
    parser.add_argument("--mode", default="standard", choices=["quick", "standard", "deep"])
    parser.add_argument("--out", default="mrm_output", help="Output directory")
    parser.add_argument("--max-attacks", type=int, default=8)
    parser.add_argument("--kill-below", type=float, default=0.35)
    parser.add_argument("--hold-below", type=float, default=0.65)
    parser.add_argument("--promote-above", type=float, default=0.65)
    parsed = parser.parse_args(args)

    config = MRMConfig(
        mode=parsed.mode,
        simulation_backend=parsed.backend,
        max_attacks_per_candidate=parsed.max_attacks,
        kill_below=parsed.kill_below,
        hold_below=parsed.hold_below,
        promote_above=parsed.promote_above,
    )
    runner = MRMRunner(config=config)
    result = runner.run_batch(parsed.input)

    _ensure_output_dir(parsed.out)
    summary_path = Path(parsed.out) / "batch_summary.json"
    result.save(str(summary_path))

    print(result.summary())
    print(f"\nTop survivors:")
    for report in result.top_survivors(5):
        print(f"  {report.summary()}")
    print(f"\nResults saved to: {summary_path}")


def cmd_report(args: list[str]) -> None:
    """skeptic-mrm report <batch_summary.json> [--format json|html]"""
    if len(args) < 1:
        print("Usage: skeptic-mrm report <batch_summary.json>")
        return
    path = Path(args[0])
    data = json.loads(path.read_text(encoding="utf-8"))
    fmt = "json"
    if "--format" in sys.argv:
        idx = sys.argv.index("--format")
        if idx + 1 < len(sys.argv):
            fmt = sys.argv[idx + 1]

    if fmt == "json":
        print(json.dumps(data.get("batch_report", data), indent=2))
    elif fmt == "html":
        _print_html_report(data.get("batch_report", data))


def _print_html_report(data: dict[str, Any]) -> None:
    """Generate a simple HTML report."""
    summary = data.get("summary", {})
    candidates = data.get("candidate_reports", [])
    html = f"""<!DOCTYPE html>
<html>
<head><title>SE-MRM Batch Report</title>
<style>
body {{ font-family: monospace; margin: 2em; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ccc; padding: 4px 8px; text-align: left; }}
th {{ background: #eee; }}
.promote {{ color: green; }}
.hold {{ color: orange; }}
.kill {{ color: red; }}
</style>
</head>
<body>
<h1>SE-MRM Batch Report</h1>
<p>Batch: {data.get('batch_id', 'unknown')}</p>
<p>Generated: {data.get('generated_at', 'unknown')}</p>
<h2>Summary</h2>
<ul>
<li>Total: {summary.get('total', 0)}</li>
<li>Promoted: {summary.get('promoted', 0)}</li>
<li>Held: {summary.get('held', 0)}</li>
<li>Killed: {summary.get('killed', 0)}</li>
<li>Review needed: {summary.get('review_required', 0)}</li>
</ul>
<h2>Candidates</h2>
<table>
<tr><th>ID</th><th>Composition</th><th>Score</th><th>Decision</th></tr>
"""
    for c in candidates:
        status = c.get("decision", {}).get("status", "unknown")
        score = c.get("score_bundle", {}).get("final_reliability_score", 0)
        comp = c.get("candidate", {}).get("composition", "?")
        cid = c.get("candidate", {}).get("candidate_id", "?")
        html += f'<tr class="{status}"><td>{cid}</td><td>{comp}</td><td>{score:.3f}</td><td>{status}</td></tr>\n'
    html += "</table></body></html>"
    print(html)


def cmd_benchmark(args: list[str]) -> None:
    """skeptic-mrm benchmark <benchmark_name> [--out <dir>]"""
    print("Benchmark mode — placeholder for mrm_bench_v01")
    print("Run: python experiments/mrm_bench_v01/run_bench_v01.py")


def main() -> None:
    """CLI entry point for skeptic-mrm."""
    if len(sys.argv) < 2:
        print("Skeptic Engine: Materials Reliability Module (SE-MRM) v0.1.0")
        print("A falsification-first reliability layer for inorganic crystal candidates.")
        print()
        print("Usage: skeptic-mrm <command> [args...]")
        print()
        print("Commands:")
        print("  ingest <path>           Load and validate candidates from file")
        print("  run --input <path>      Run full MRM pipeline")
        print("  report <path>           Display batch report")
        print("  benchmark <name>        Run benchmark suite")
        return

    command = sys.argv[1]
    rest = sys.argv[2:]

    commands = {
        "ingest": cmd_ingest,
        "run": cmd_run,
        "report": cmd_report,
        "benchmark": cmd_benchmark,
    }

    handler = commands.get(command)
    if handler is None:
        print(f"Unknown command: {command}")
        print(f"Available: {', '.join(commands.keys())}")
        return

    handler(rest)


if __name__ == "__main__":
    main()
