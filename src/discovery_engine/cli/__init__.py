"""Discovery Engine CLI — modern command-line interface built with Click.

This module replaces the legacy main.py if/else command router with
a proper Click-based CLI featuring:
- Auto-generated --help for all commands
- Subcommand grouping (pipeline, h4, h10, fetch)
- Type hints and validation
- Consistent error handling
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

# Add project root to path for legacy module imports
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _run_legacy(command: str) -> None:
    """Run legacy main() with a specific command via sys.argv patch.

    Parameters
    ----------
    command : str
        Command string to pass to legacy main.
    """
    from discovery_engine.main import main as legacy_main

    old_argv = sys.argv
    sys.argv = ["discovery-engine", command]
    try:
        legacy_main()
    finally:
        sys.argv = old_argv


# ============================================================
# Root CLI Group
# ============================================================
@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version="0.2.0", prog_name="discovery-engine")
def cli() -> None:
    """Discovery Engine — Interdisciplinary Hypothesis Search CLI.

   \b
    Command Groups:
      pipeline  Core discovery pipeline stages
      h4        H4: TDA cancer resistance benchmark
      h10       H10: MOF stability benchmark
      fetch     Data collection from external sources
    """
    pass


# ============================================================
# Pipeline Commands
# ============================================================
@cli.group(short_help="Core discovery pipeline commands.")
def pipeline() -> None:
    """Core discovery pipeline stages."""
    pass


@pipeline.command("run")
@click.option("--sources", is_flag=True, help="Include source collection stage.")
@click.option("--semantic", is_flag=True, help="Include semantic profiling stage.")
@click.option("--candidates", is_flag=True, help="Include candidate generation stage.")
def pipeline_run(sources: bool, semantic: bool, candidates: bool) -> None:
    """Run the full discovery pipeline or selected stages."""

    # Build command string for legacy main
    command_parts = ["pipeline"]
    if sources:
        command_parts.append("sources")
    if semantic:
        command_parts.append("semantic")
    if candidates:
        command_parts.append("candidates")

    click.echo(f"Running pipeline: {' → '.join(command_parts)}")
    _run_legacy(" ".join(command_parts))


@pipeline.command("sources")
def pipeline_sources() -> None:
    """Fetch and normalize sources from biorxiv, PubMed, Zenodo."""

    click.echo("Fetching and normalizing sources...")
    _run_legacy("sources")


@pipeline.command("semantic")
def pipeline_semantic() -> None:
    """Build semantic profiles and find cross-domain links."""

    click.echo("Building semantic profiles...")
    _run_legacy("semantic")


@pipeline.command("candidates")
def pipeline_candidates() -> None:
    """Generate candidate hypotheses from cross-domain links."""

    click.echo("Generating candidates...")
    _run_legacy("candidates")


# ============================================================
# Skeptic Commands
# ============================================================
@cli.group(short_help="Skeptic review and prior art commands.")
def skeptic() -> None:
    """Skeptic review and prior art validation."""
    pass


@skeptic.command("review")
def skeptic_review() -> None:
    """Run skeptic challenge on candidate hypotheses."""

    click.echo("Running skeptic review...")
    _run_legacy("skeptic-run")


@skeptic.command("top5")
def skeptic_top5() -> None:
    """Review top 5 candidates with enhanced prior art."""

    click.echo("Running top 5 skeptic review...")
    _run_legacy("skeptic-top5")


@skeptic.command("report-seeds")
def skeptic_report_seeds() -> None:
    """Generate report for seeded candidates."""

    click.echo("Generating seed report...")
    _run_legacy("report-seeds")


# ============================================================
# H4 Commands (TDA Cancer Resistance)
# ============================================================
@cli.group(short_help="H4 benchmark: TDA cancer resistance.")
def h4() -> None:
    """H4: Topological Data Analysis for cancer resistance detection.

    \b
    Status: CLOSED after kill criterion (AUC=0.500)
    Commands below are for archival reference only.
    """
    pass


@h4.command("plan")
def h4_plan() -> None:
    """Show H4 execution plan (closed track)."""

    _run_legacy("h4-plan")


@h4.command("dataset-card")
def h4_dataset_card() -> None:
    """Generate H4 dataset card."""

    _run_legacy("h4-dataset-card")


@h4.command("validate-spec")
def h4_validate_spec() -> None:
    """Validate H4 MVP specification."""

    _run_legacy("h4-validate-spec")


@h4.command("audit-plan")
def h4_audit_plan() -> None:
    """Generate H4 audit plan (archival context)."""

    _run_legacy("h4-audit-plan")


@h4.command("top5-board")
def h4_top5_board() -> None:
    """Display H4 top 5 board."""

    _run_legacy("top5-board")


# ============================================================
# H10 Commands (MOF Stability Benchmark)
# ============================================================
@cli.group(short_help="H10 benchmark: MOF stability.")
def h10() -> None:
    """H10: Metal-Organic Framework stability benchmark."""
    pass


@h10.command("plan")
def h10_plan() -> None:
    """Show H10 execution plan."""

    _run_legacy("h10-plan")


@h10.command("routes")
def h10_routes() -> None:
    """List available H10 routes."""

    _run_legacy("h10-routes")


@h10.command("dataset-card")
def h10_dataset_card() -> None:
    """Generate H10 dataset card."""

    _run_legacy("h10-dataset-card")


@h10.command("map")
@click.option("--route", default=None, help="Route ID to use for mapping.")
def h10_map(route: str | None) -> None:
    """Map H10 dataset to benchmark format."""

    cmd = "h10-map"
    if route:
        cmd += f":{route}"
    _run_legacy(cmd)


@h10.command("readiness")
def h10_readiness() -> None:
    """Check H10 readiness report."""

    _run_legacy("h10-readiness")


@h10.command("baseline-scaffold")
def h10_baseline_scaffold() -> None:
    """Generate H10 baseline scaffold."""

    _run_legacy("h10-baseline-scaffold")


@h10.command("init-route")
@click.argument("route_id")
def h10_init_route(route_id: str) -> None:
    """Initialize a new H10 route."""

    _run_legacy(f"h10-init-route:{route_id}")


# ============================================================
# Fetch Commands (Data Collection)
# ============================================================
@cli.group(short_help="Fetch data from external sources.")
def fetch() -> None:
    """Fetch data from external APIs."""
    pass


@fetch.command("scholar")
@click.argument("query")
@click.option("--limit", default=50, help="Maximum number of results.")
def fetch_scholar(query: str, limit: int) -> None:
    """Fetch papers from Semantic Scholar."""

    click.echo(f"Fetching from Semantic Scholar: {query}")
    _run_legacy(f"fetch-scholar:{query}:limit={limit}")


@fetch.command("biorxiv")
@click.option("--limit", default=100, help="Maximum number of results.")
def fetch_biorxiv(limit: int) -> None:
    """Fetch recent preprints from biorxiv."""

    click.echo(f"Fetching from biorxiv (limit={limit})...")
    _run_legacy(f"fetch-biorxiv:limit={limit}")


@fetch.command("zenodo")
@click.option("--query", default="", help="Search query.")
@click.option("--limit", default=50, help="Maximum number of results.")
def fetch_zenodo(query: str, limit: int) -> None:
    """Fetch records from Zenodo."""

    cmd = "fetch-zenodo"
    if query:
        cmd += f":{query}"
    cmd += f":limit={limit}"
    click.echo(f"Fetching from Zenodo: {query or 'all'}")
    _run_legacy(cmd)


@fetch.command("all")
def fetch_all() -> None:
    """Fetch from all sources (scholar + biorxiv + zenodo)."""

    click.echo("Fetching from all sources...")
    _run_legacy("fetch-all")


# ============================================================
# Entry Point
# ============================================================
def main(args: list[str] | None = None) -> None:
    """CLI entry point.

    Parameters
    ----------
    args : list[str] | None
        Command line arguments (defaults to sys.argv[1:]).
    """
    try:
        cli(args=args, standalone_mode=False)
    except click.exceptions.Exit as e:
        sys.exit(e.exit_code)
    except KeyboardInterrupt:
        click.echo("\nAborted.", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
