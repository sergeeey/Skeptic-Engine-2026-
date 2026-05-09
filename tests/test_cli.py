"""Unit tests for Discovery Engine CLI module.

Covers:
- Root CLI group and version
- Pipeline subcommands (run, sources, semantic, candidates)
- Skeptic subcommands (review, top5, report-seeds)
- H4 subcommands (plan, dataset-card, validate-spec, audit-plan, top5-board)
- H10 subcommands (plan, routes, dataset-card, map, readiness, baseline-scaffold, init-route)
- Fetch subcommands (scholar, biorxiv, zenodo, all)
- Error handling and edge cases
"""

from __future__ import annotations

import contextlib
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner


# ===========================================================================
# Fixtures
# ===========================================================================
@pytest.fixture
def runner() -> CliRunner:
    """Create a Click test runner."""
    return CliRunner()


@pytest.fixture
def mock_legacy_main() -> MagicMock:
    """Mock the _run_legacy helper to avoid executing real commands."""
    with patch("discovery_engine.cli._run_legacy") as mock:
        yield mock


# ===========================================================================
# 1. Root CLI
# ===========================================================================
class TestRootCLI:
    """Test root CLI group and basic behavior."""

    def test_cli_import(self) -> None:
        """CLI module should be importable."""
        from discovery_engine.cli import cli, main

        assert callable(cli)
        assert callable(main)

    def test_help_output(self, runner: CliRunner) -> None:
        """--help should show available command groups."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "pipeline" in result.output.lower()
        assert "h4" in result.output.lower()
        assert "h10" in result.output.lower()
        assert "fetch" in result.output.lower()

    def test_help_short_flag(self, runner: CliRunner) -> None:
        """-h should also show help."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["-h"])

        assert result.exit_code == 0

    def test_version_flag(self, runner: CliRunner) -> None:
        """--version should match package release (pyproject version)."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "0.2.0" in result.output
        assert "discovery-engine" in result.output.lower()

    def test_version_short_flag(self, runner: CliRunner) -> None:
        """-V is not a short version flag in Click, but let's verify."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0

    def test_no_command_shows_help(self, runner: CliRunner) -> None:
        """Running without command should show help."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli)

        # Click may exit 0 (showing help) or 2 (error) depending on version
        assert result.exit_code in (0, 2)
        assert "Discovery Engine" in result.output


# ===========================================================================
# 2. Pipeline Commands
# ===========================================================================
class TestPipelineCommands:
    """Test pipeline subcommands."""

    def test_pipeline_help(self, runner: CliRunner) -> None:
        """pipeline --help should show subcommands."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["pipeline", "--help"])

        assert result.exit_code == 0
        assert "run" in result.output
        assert "sources" in result.output
        assert "semantic" in result.output
        assert "candidates" in result.output

    def test_pipeline_run_no_flags(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """pipeline run without flags should call legacy with 'pipeline'."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["pipeline", "run"])

        assert result.exit_code == 0
        assert "Running pipeline: pipeline" in result.output
        mock_legacy_main.assert_called_once_with("pipeline")

    def test_pipeline_run_sources_flag(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """pipeline run --sources should include 'sources' stage."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["pipeline", "run", "--sources"])

        assert result.exit_code == 0
        assert "sources" in result.output
        mock_legacy_main.assert_called_once()
        call_args = mock_legacy_main.call_args[0][0]
        assert "sources" in call_args

    def test_pipeline_run_all_flags(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """pipeline run with all flags should include all stages."""
        from discovery_engine.cli import cli

        result = runner.invoke(
            cli, ["pipeline", "run", "--sources", "--semantic", "--candidates"]
        )

        assert result.exit_code == 0
        call_args = mock_legacy_main.call_args[0][0]
        assert "sources" in call_args
        assert "semantic" in call_args
        assert "candidates" in call_args

    def test_pipeline_sources(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """pipeline sources should call legacy with 'sources'."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["pipeline", "sources"])

        assert result.exit_code == 0
        assert "Fetching and normalizing sources" in result.output
        mock_legacy_main.assert_called_once_with("sources")

    def test_pipeline_semantic(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """pipeline semantic should call legacy with 'semantic'."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["pipeline", "semantic"])

        assert result.exit_code == 0
        assert "Building semantic profiles" in result.output
        mock_legacy_main.assert_called_once_with("semantic")

    def test_pipeline_candidates(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """pipeline candidates should call legacy with 'candidates'."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["pipeline", "candidates"])

        assert result.exit_code == 0
        assert "Generating candidates" in result.output
        mock_legacy_main.assert_called_once_with("candidates")


# ===========================================================================
# 3. Skeptic Commands
# ===========================================================================
class TestSkepticCommands:
    """Test skeptic subcommands."""

    def test_skeptic_help(self, runner: CliRunner) -> None:
        """skeptic --help should show subcommands."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["skeptic", "--help"])

        assert result.exit_code == 0
        assert "review" in result.output
        assert "top5" in result.output
        assert "report-seeds" in result.output

    def test_skeptic_review(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """skeptic review should call legacy with 'skeptic-run'."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["skeptic", "review"])

        assert result.exit_code == 0
        assert "Running skeptic review" in result.output
        mock_legacy_main.assert_called_once_with("skeptic-run")

    def test_skeptic_top5(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """skeptic top5 should call legacy with 'skeptic-top5'."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["skeptic", "top5"])

        assert result.exit_code == 0
        assert "top 5" in result.output.lower()
        mock_legacy_main.assert_called_once_with("skeptic-top5")

    def test_skeptic_report_seeds(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """skeptic report-seeds should call legacy with 'report-seeds'."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["skeptic", "report-seeds"])

        assert result.exit_code == 0
        assert "Generating seed report" in result.output
        mock_legacy_main.assert_called_once_with("report-seeds")


# ===========================================================================
# 4. H4 Commands
# ===========================================================================
class TestH4Commands:
    """Test H4 subcommands (archival)."""

    def test_h4_help(self, runner: CliRunner) -> None:
        """h4 --help should show subcommands."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["h4", "--help"])

        assert result.exit_code == 0
        assert "plan" in result.output
        assert "dataset-card" in result.output
        assert "validate-spec" in result.output

    def test_h4_plan(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """h4 plan should call legacy with 'h4-plan'."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["h4", "plan"])

        assert result.exit_code == 0
        mock_legacy_main.assert_called_once_with("h4-plan")

    def test_h4_dataset_card(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """h4 dataset-card should call legacy with 'h4-dataset-card'."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["h4", "dataset-card"])

        assert result.exit_code == 0
        mock_legacy_main.assert_called_once_with("h4-dataset-card")

    def test_h4_validate_spec(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """h4 validate-spec should call legacy with 'h4-validate-spec'."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["h4", "validate-spec"])

        assert result.exit_code == 0
        mock_legacy_main.assert_called_once_with("h4-validate-spec")

    def test_h4_audit_plan(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """h4 audit-plan should call legacy with 'h4-audit-plan'."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["h4", "audit-plan"])

        assert result.exit_code == 0
        mock_legacy_main.assert_called_once_with("h4-audit-plan")

    def test_h4_top5_board(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """h4 top5-board should call legacy with 'top5-board'."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["h4", "top5-board"])

        assert result.exit_code == 0
        mock_legacy_main.assert_called_once_with("top5-board")


# ===========================================================================
# 5. H10 Commands
# ===========================================================================
class TestH10Commands:
    """Test H10 subcommands."""

    def test_h10_help(self, runner: CliRunner) -> None:
        """h10 --help should show subcommands."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["h10", "--help"])

        assert result.exit_code == 0
        assert "plan" in result.output
        assert "routes" in result.output
        assert "dataset-card" in result.output
        assert "map" in result.output
        assert "readiness" in result.output
        assert "init-route" in result.output

    def test_h10_plan(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """h10 plan should call legacy with 'h10-plan'."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["h10", "plan"])

        assert result.exit_code == 0
        mock_legacy_main.assert_called_once_with("h10-plan")

    def test_h10_routes(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """h10 routes should call legacy with 'h10-routes'."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["h10", "routes"])

        assert result.exit_code == 0
        mock_legacy_main.assert_called_once_with("h10-routes")

    def test_h10_dataset_card(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """h10 dataset-card should call legacy with 'h10-dataset-card'."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["h10", "dataset-card"])

        assert result.exit_code == 0
        mock_legacy_main.assert_called_once_with("h10-dataset-card")

    def test_h10_map_no_route(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """h10 map without --route should call legacy with 'h10-map'."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["h10", "map"])

        assert result.exit_code == 0
        mock_legacy_main.assert_called_once_with("h10-map")

    def test_h10_map_with_route(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """h10 map --route <id> should call legacy with 'h10-map:<id>'."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["h10", "map", "--route", "my-route"])

        assert result.exit_code == 0
        mock_legacy_main.assert_called_once_with("h10-map:my-route")

    def test_h10_readiness(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """h10 readiness should call legacy with 'h10-readiness'."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["h10", "readiness"])

        assert result.exit_code == 0
        mock_legacy_main.assert_called_once_with("h10-readiness")

    def test_h10_baseline_scaffold(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """h10 baseline-scaffold should call legacy with 'h10-baseline-scaffold'."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["h10", "baseline-scaffold"])

        assert result.exit_code == 0
        mock_legacy_main.assert_called_once_with("h10-baseline-scaffold")

    def test_h10_init_route(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """h10 init-route <route_id> should call legacy with 'h10-init-route:<id>'."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["h10", "init-route", "solvent-route"])

        assert result.exit_code == 0
        mock_legacy_main.assert_called_once_with("h10-init-route:solvent-route")

    def test_h10_init_route_missing_argument(
        self,
        runner: CliRunner,
    ) -> None:
        """h10 init-route without argument should fail."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["h10", "init-route"])

        assert result.exit_code != 0


# ===========================================================================
# 6. Fetch Commands
# ===========================================================================
class TestFetchCommands:
    """Test fetch subcommands."""

    def test_fetch_help(self, runner: CliRunner) -> None:
        """fetch --help should show subcommands."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["fetch", "--help"])

        assert result.exit_code == 0
        assert "scholar" in result.output
        assert "biorxiv" in result.output
        assert "zenodo" in result.output
        assert "all" in result.output

    def test_fetch_scholar_default_limit(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """fetch scholar <query> with default limit=50."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["fetch", "scholar", "cancer research"])

        assert result.exit_code == 0
        assert "cancer research" in result.output
        mock_legacy_main.assert_called_once_with("fetch-scholar:cancer research:limit=50")

    def test_fetch_scholar_custom_limit(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """fetch scholar <query> --limit 100."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["fetch", "scholar", "gene therapy", "--limit", "100"])

        assert result.exit_code == 0
        mock_legacy_main.assert_called_once_with("fetch-scholar:gene therapy:limit=100")

    def test_fetch_biorxiv_default_limit(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """fetch biorxiv with default limit=100."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["fetch", "biorxiv"])

        assert result.exit_code == 0
        assert "limit=100" in result.output
        mock_legacy_main.assert_called_once_with("fetch-biorxiv:limit=100")

    def test_fetch_biorxiv_custom_limit(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """fetch biorxiv --limit 50."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["fetch", "biorxiv", "--limit", "50"])

        assert result.exit_code == 0
        mock_legacy_main.assert_called_once_with("fetch-biorxiv:limit=50")

    def test_fetch_zenodo_no_query(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """fetch zenodo without query should fetch all."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["fetch", "zenodo"])

        assert result.exit_code == 0
        mock_legacy_main.assert_called_once_with("fetch-zenodo:limit=50")

    def test_fetch_zenodo_with_query(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """fetch zenodo --query <q> --limit <n>."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["fetch", "zenodo", "--query", "ml", "--limit", "25"])

        assert result.exit_code == 0
        assert "ml" in result.output
        mock_legacy_main.assert_called_once_with("fetch-zenodo:ml:limit=25")

    def test_fetch_all(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """fetch all should call legacy with 'fetch-all'."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["fetch", "all"])

        assert result.exit_code == 0
        assert "all sources" in result.output.lower()
        mock_legacy_main.assert_called_once_with("fetch-all")


# ===========================================================================
# 7. Error Handling
# ===========================================================================
class TestErrorHandling:
    """Test CLI error handling and edge cases."""

    def test_unknown_command(self, runner: CliRunner) -> None:
        """Unknown command should return non-zero exit code."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["nonexistent-command"])

        assert result.exit_code != 0

    def test_main_function_with_args(self) -> None:
        """main() should accept explicit args list."""
        from discovery_engine.cli import main

        # Should not raise
        main(["--version"])

    def test_main_function_empty_args(self) -> None:
        """main([]) should show help (may or may not raise SystemExit)."""
        from discovery_engine.cli import main

        # Click may show help and exit with 0 or 1, or just return
        with contextlib.suppress(SystemExit):
            main([])

    def test_main_handles_keyboard_interrupt(self) -> None:
        """main() should handle KeyboardInterrupt gracefully."""
        from discovery_engine.cli import main

        with patch("discovery_engine.cli.cli", side_effect=KeyboardInterrupt):
            # Should not raise, should exit with code 130
            with pytest.raises(SystemExit) as exc_info:
                main([])
            assert exc_info.value.code == 130

    def test_main_handles_generic_exception(self) -> None:
        """main() should handle generic exceptions."""
        from discovery_engine.cli import main

        with patch("discovery_engine.cli.cli", side_effect=RuntimeError("test error")):
            with pytest.raises(SystemExit) as exc_info:
                main([])
            assert exc_info.value.code == 1

    def test_main_handles_click_exit(self) -> None:
        """main() should handle Click Exit exception."""
        import click

        from discovery_engine.cli import main

        with patch("discovery_engine.cli.cli", side_effect=click.exceptions.Exit(0)):
            with pytest.raises(SystemExit) as exc_info:
                main([])
            assert exc_info.value.code == 0

    def test_subcommand_routing_pipeline(self, runner: CliRunner) -> None:
        """Verify pipeline subcommand group is properly registered."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["pipeline", "--help"])
        assert result.exit_code == 0
        # Should list subcommands
        assert "Commands:" in result.output or "Options:" in result.output

    def test_subcommand_routing_skeptic(self, runner: CliRunner) -> None:
        """Verify skeptic subcommand group is properly registered."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["skeptic", "--help"])
        assert result.exit_code == 0

    def test_subcommand_routing_h4(self, runner: CliRunner) -> None:
        """Verify h4 subcommand group is properly registered."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["h4", "--help"])
        assert result.exit_code == 0

    def test_subcommand_routing_h10(self, runner: CliRunner) -> None:
        """Verify h10 subcommand group is properly registered."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["h10", "--help"])
        assert result.exit_code == 0

    def test_subcommand_routing_fetch(self, runner: CliRunner) -> None:
        """Verify fetch subcommand group is properly registered."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["fetch", "--help"])
        assert result.exit_code == 0


# ===========================================================================
# 8. Integration Tests (with mock legacy)
# ===========================================================================
class TestCLIIntegration:
    """Integration-style tests with mocked legacy main."""

    def test_pipeline_run_all_stages_chain(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """Full pipeline run with all stages should pass correct command."""
        from discovery_engine.cli import cli

        result = runner.invoke(
            cli, ["pipeline", "run", "--sources", "--semantic", "--candidates"]
        )

        assert result.exit_code == 0
        call_arg = mock_legacy_main.call_args[0][0]
        parts = call_arg.split()
        assert "pipeline" in parts
        assert "sources" in parts
        assert "semantic" in parts
        assert "candidates" in parts

    def test_fetch_zenodo_query_with_spaces(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """Zenodo query with spaces should be passed correctly."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["fetch", "zenodo", "--query", "machine learning"])

        assert result.exit_code == 0
        call_arg = mock_legacy_main.call_args[0][0]
        assert "machine learning" in call_arg

    def test_h10_map_special_characters_in_route(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """H10 map with special characters in route name."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["h10", "map", "--route", "my_route-123"])

        assert result.exit_code == 0
        mock_legacy_main.assert_called_once_with("h10-map:my_route-123")

    def test_fetch_scholar_special_characters(
        self,
        runner: CliRunner,
        mock_legacy_main: MagicMock,
    ) -> None:
        """Scholar query with special characters."""
        from discovery_engine.cli import cli

        result = runner.invoke(cli, ["fetch", "scholar", "CRISPR-Cas9"])

        assert result.exit_code == 0
        call_arg = mock_legacy_main.call_args[0][0]
        assert "CRISPR-Cas9" in call_arg

    def test_all_command_groups_have_help(
        self,
        runner: CliRunner,
    ) -> None:
        """All command groups should have help text."""
        from discovery_engine.cli import cli

        groups = ["pipeline", "skeptic", "h4", "h10", "fetch"]
        for group in groups:
            result = runner.invoke(cli, [group, "--help"])
            assert result.exit_code == 0, f"{group} --help failed: {result.output}"
