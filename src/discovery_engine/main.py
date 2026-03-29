from __future__ import annotations

import json
import sys
from pathlib import Path

from discovery_engine.arbiter import rank_hypotheses
from discovery_engine.benchmarks.h4 import (
    build_h4_audit_plan,
    H4TaskCard,
    build_h4_dataset_card,
    build_h4_execution_plan,
    load_h4_spec,
    validate_h4_spec,
)
from discovery_engine.benchmarks.h10 import (
    build_h10_baseline_scaffold,
    build_h10_dataset_card,
    build_h10_execution_plan,
    build_h10_graph_artifact,
    build_h10_mapped_dataset,
    build_h10_readiness_report,
    run_h10_descriptor_baseline,
    run_h10_descriptor_tree_baseline,
    run_h10_graph_baseline,
    run_h10_graph_mpnn_baseline,
    run_h10_hybrid_baseline,
    import_mofsimplify_solvent_route,
    initialize_route_templates,
    load_h10_route,
    load_h10_spec,
    validate_h10_route,
)
from discovery_engine.benchmarks.h10.task_card import H10TaskCard
from discovery_engine.collectors import (
    fetch_biorxiv,
    fetch_semantic_scholar,
    fetch_zenodo,
    load_source_manifest,
)
from discovery_engine.dqops import normalize_sources
from discovery_engine.hypothesis_generation import generate_candidate_hypotheses
from discovery_engine.pipeline import PIPELINE_STAGES
from discovery_engine.report_ingest import load_candidate_seeds
from discovery_engine.semantic_core import build_semantic_profiles, find_cross_domain_links
from discovery_engine.skeptic import challenge_hypotheses
from discovery_engine.skeptic.prior_art import write_skeptic_outputs
from discovery_engine.skeptic.top5_prior_art import review_top5_candidates, write_top5_skeptic_outputs
from discovery_engine.schemas import SourceRecord
from discovery_engine.top5 import load_top5_board


def _save_manifest(records: list[SourceRecord], name: str) -> Path:
    """Persist SourceRecords as a JSON manifest for reproducibility."""
    path = Path(__file__).resolve().parents[2] / "data" / "manifests" / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([r.to_dict() for r in records], indent=2, default=str),
        encoding="utf-8",
    )
    return path


def _manifest_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "manifests" / "seed_sources.json"


def _manifest_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "manifests"


def _candidate_seed_path() -> Path:
    return (
        Path(__file__).resolve().parents[2] / "data" / "candidates" / "report_top10_candidates.json"
    )


def _top5_board_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "top5" / "curated_top5_board.json"


def _h10_spec_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "benchmarks" / "h10_mvp_spec.json"


def _h4_spec_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "benchmarks" / "h4_mvp_spec.json"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _h10_route_dir() -> Path:
    return _project_root() / "data" / "benchmarks" / "h10_routes"


def _h10_default_route_path() -> Path:
    return _h10_route_dir() / "mofsimplify_stability.json"


def _h10_default_archive_path() -> Path:
    return (
        _project_root()
        / "data"
        / "raw"
        / "h10"
        / "mofsimplify_stability"
        / "downloads"
        / "SciData.zip"
    )


def _h10_mapped_dataset_path() -> Path:
    return _project_root() / "data" / "benchmarks" / "h10_mapped" / "mofsimplify_stability.csv"


def _h10_descriptor_feature_path() -> Path:
    return (
        _project_root()
        / "data"
        / "benchmarks"
        / "h10_features"
        / "mofsimplify_descriptor_features.csv"
    )


def _h10_scaffold_output_path() -> Path:
    return (
        _project_root()
        / "data"
        / "benchmarks"
        / "h10_scaffold"
        / "mofsimplify_baseline_scaffold.json"
    )


def _h10_baseline_doc_path() -> Path:
    return _project_root() / "docs" / "h10-baseline-matrix.md"


def _h10_descriptor_report_path() -> Path:
    return _project_root() / "data" / "benchmarks" / "h10_results" / "descriptor_logreg_v1.json"


def _h10_descriptor_predictions_path() -> Path:
    return (
        _project_root()
        / "data"
        / "benchmarks"
        / "h10_results"
        / "descriptor_logreg_v1_test_predictions.csv"
    )


def _h10_descriptor_doc_path() -> Path:
    return _project_root() / "docs" / "h10-descriptor-baseline.md"


def _h10_descriptor_tree_report_path() -> Path:
    return _project_root() / "data" / "benchmarks" / "h10_results" / "descriptor_hgb_v1.json"


def _h10_descriptor_tree_predictions_path() -> Path:
    return (
        _project_root()
        / "data"
        / "benchmarks"
        / "h10_results"
        / "descriptor_hgb_v1_test_predictions.csv"
    )


def _h10_descriptor_tree_doc_path() -> Path:
    return _project_root() / "docs" / "h10-descriptor-tree-baseline.md"


def _h10_graph_artifact_path() -> Path:
    return (
        _project_root() / "data" / "benchmarks" / "h10_graphs" / "mofsimplify_asr_graphs.jsonl.gz"
    )


def _h10_graph_summary_path() -> Path:
    return (
        _project_root()
        / "data"
        / "benchmarks"
        / "h10_graphs"
        / "mofsimplify_asr_graph_summary.json"
    )


def _h10_graph_report_path() -> Path:
    return _project_root() / "data" / "benchmarks" / "h10_results" / "graph_structural_hgb_v1.json"


def _h10_graph_predictions_path() -> Path:
    return (
        _project_root()
        / "data"
        / "benchmarks"
        / "h10_results"
        / "graph_structural_hgb_v1_test_predictions.csv"
    )


def _h10_graph_doc_path() -> Path:
    return _project_root() / "docs" / "h10-graph-baseline.md"


def _h10_graph_mpnn_report_path() -> Path:
    return _project_root() / "data" / "benchmarks" / "h10_results" / "graph_mpnn_v3.json"


def _h10_graph_mpnn_predictions_path() -> Path:
    return (
        _project_root()
        / "data"
        / "benchmarks"
        / "h10_results"
        / "graph_mpnn_v3_test_predictions.csv"
    )


def _h10_graph_mpnn_doc_path() -> Path:
    return _project_root() / "docs" / "h10-graph-mpnn-baseline.md"


def _h10_hybrid_report_path() -> Path:
    return _project_root() / "data" / "benchmarks" / "h10_results" / "hybrid_hgb_v1.json"


def _h10_hybrid_predictions_path() -> Path:
    return (
        _project_root()
        / "data"
        / "benchmarks"
        / "h10_results"
        / "hybrid_hgb_v1_test_predictions.csv"
    )


def _h10_hybrid_doc_path() -> Path:
    return _project_root() / "docs" / "h10-hybrid-baseline.md"


def _skeptic_review_path() -> Path:
    return _project_root() / "data" / "candidates" / "skeptic_reviews.json"


def _skeptic_challenged_cards_path() -> Path:
    return _project_root() / "data" / "candidates" / "challenged_candidates.json"


def _skeptic_markdown_path() -> Path:
    return _project_root() / "docs" / "verification" / "skeptic-latest.md"


def _top5_skeptic_review_path() -> Path:
    return _project_root() / "data" / "candidates" / "top5_skeptic_reviews.json"


def _top5_skeptic_markdown_path() -> Path:
    return _project_root() / "docs" / "verification" / "top5-skeptic-latest.md"


def _skeptic_manifest_paths() -> list[Path]:
    manifest_dir = _manifest_dir()
    ordered_names = [
        "scholar_latest.json",
        "external_sources.json",
        "biorxiv_latest.json",
        "zenodo_latest.json",
    ]
    return [manifest_dir / name for name in ordered_names if (manifest_dir / name).exists()]


def _load_skeptic_prior_art_records() -> tuple[list[SourceRecord], list[str]]:
    records: list[SourceRecord] = []
    manifests_used: list[str] = []
    for path in _skeptic_manifest_paths():
        records.extend(load_source_manifest(path))
        manifests_used.append(path.name)
    normalized, _ = normalize_sources(records)
    return normalized, manifests_used


def main() -> None:
    command = sys.argv[1] if len(sys.argv) > 1 else "pipeline"

    if command == "pipeline":
        print("Interdisciplinary Discovery Engine")
        print("Pipeline:")
        for index, stage in enumerate(PIPELINE_STAGES, start=1):
            print(f"{index}. {stage.name}: {stage.purpose}")
        return

    if command == "sources":
        manifest = _manifest_path()
        records = load_source_manifest(manifest)
        normalized, report = normalize_sources(records)

        print(f"Manifest: {manifest}")
        print(f"Input records: {report.total_input}")
        print(f"Kept records: {report.kept}")
        print(f"Deduplicated: {report.deduplicated}")
        print("Warnings:")
        for warning in report.warnings or ["none"]:
            print(f"- {warning}")
        print("Records:")
        for record in normalized:
            print(
                f"- {record.id} | {record.domain} | {record.source_type.value} | "
                f"authority={record.authority_score:.2f} bias={record.bias_index:.2f}"
            )
        return

    if command == "semantic":
        manifest = _manifest_path()
        records = load_source_manifest(manifest)
        normalized, report = normalize_sources(records)
        source_index = {record.id: record for record in normalized}
        profiles = build_semantic_profiles(normalized)
        links = find_cross_domain_links(profiles, source_index)

        print(f"Manifest: {manifest}")
        print(f"Input records: {report.total_input}")
        print(f"Semantic profiles: {len(profiles)}")
        print(f"Cross-domain links: {len(links)}")
        print("Top links:")
        for link in links[:10]:
            print(
                f"- {link.source_a} <-> {link.source_b} | "
                f"tags={', '.join(link.shared_tags)} | score={link.link_score:.4f}"
            )
            print(f"  rationale: {link.rationale}")
        return

    if command == "candidates":
        manifest = _manifest_path()
        records = load_source_manifest(manifest)
        normalized, _ = normalize_sources(records)
        source_index = {record.id: record for record in normalized}
        profiles = build_semantic_profiles(normalized)
        links = find_cross_domain_links(profiles, source_index)
        ranked = rank_hypotheses(generate_candidate_hypotheses(links, source_index))

        print(f"Candidate hypotheses: {len(ranked)}")
        print("Top candidates:")
        for card in ranked[:10]:
            print(
                f"- {card.id} | {card.title} | score={card.discovery_score:.4f} | "
                f"promotion_ready={card.promotion_ready()} | tier={card.risk_tier.value}"
            )
            print(
                f"  confidence={card.confidence_score:.2f} evidence_quality={card.evidence_quality_score:.2f}"
            )
            print(f"  falsification: {card.first_falsification_test}")
        return

    if command == "skeptic-run":
        manifest = _manifest_path()
        max_live_results = int(sys.argv[2]) if len(sys.argv) > 2 else 2
        records = load_source_manifest(manifest)
        normalized, _ = normalize_sources(records)
        source_index = {record.id: record for record in normalized}
        profiles = build_semantic_profiles(normalized)
        links = find_cross_domain_links(profiles, source_index)
        cards = generate_candidate_hypotheses(links, source_index)
        prior_art_records, manifests_used = _load_skeptic_prior_art_records()
        skeptic_run = challenge_hypotheses(
            cards,
            source_index=source_index,
            prior_art_records=prior_art_records,
            manifests_used=manifests_used,
            max_live_results_per_source=max_live_results,
            use_live_fetch=max_live_results > 0,
        )
        ranked = rank_hypotheses(skeptic_run.challenged_cards)
        write_skeptic_outputs(
            skeptic_run,
            review_output_path=_skeptic_review_path(),
            challenged_cards_output_path=_skeptic_challenged_cards_path(),
            markdown_output_path=_skeptic_markdown_path(),
        )
        verdict_counts: dict[str, int] = {}
        review_by_id = {review.card_id: review for review in skeptic_run.reviews}
        for review in skeptic_run.reviews:
            verdict_counts[review.verdict] = verdict_counts.get(review.verdict, 0) + 1

        print(f"Seed manifest: {manifest}")
        print(f"Candidate cards reviewed: {len(skeptic_run.reviews)}")
        print(f"Prior-art records scanned: {skeptic_run.prior_art_count}")
        print(f"Manifests used: {', '.join(manifests_used) or 'none'}")
        print(f"Live targeted queries: {skeptic_run.live_fetch_queries}")
        print(f"Live records fetched: {skeptic_run.live_records_fetched}")
        print("Verdicts:")
        for verdict, count in sorted(verdict_counts.items()):
            print(f"- {verdict}: {count}")
        print("Top challenged cards:")
        for card in ranked[:10]:
            review = review_by_id.get(card.id)
            summary = review.challenge_summary if review else "no review"
            print(
                f"- {card.id} | novelty={card.novelty_score:.2f} "
                f"confidence={card.confidence_score:.2f} | {summary}"
            )
        print(f"Review JSON: {_skeptic_review_path()}")
        print(f"Challenged cards JSON: {_skeptic_challenged_cards_path()}")
        print(f"Skeptic note: {_skeptic_markdown_path()}")
        if skeptic_run.warnings:
            print("Warnings:")
            for warning in skeptic_run.warnings:
                print(f"- {warning}")
        return

    if command == "skeptic-top5":
        max_live_results = int(sys.argv[2]) if len(sys.argv) > 2 else 6
        seeds = sorted(load_candidate_seeds(_candidate_seed_path()), key=lambda item: item.priority_rank)
        run = review_top5_candidates(
            seeds[:5],
            max_live_results_per_source=max_live_results,
        )
        write_top5_skeptic_outputs(
            run,
            review_output_path=_top5_skeptic_review_path(),
            markdown_output_path=_top5_skeptic_markdown_path(),
        )
        print(f"Candidate seeds reviewed: {len(run.reviews)}")
        print(f"Live targeted queries: {run.live_fetch_queries}")
        print(f"Live records fetched: {run.live_records_fetched}")
        print("Top-5 skeptic verdicts:")
        for review in sorted(run.reviews, key=lambda item: item.revised_score, reverse=True):
            print(
                f"- {review.candidate_id} | verdict={review.verdict} | "
                f"score={review.original_score:.2f}->{review.revised_score:.2f}"
            )
            print(f"  summary: {review.challenge_summary}")
        print(f"Review JSON: {_top5_skeptic_review_path()}")
        print(f"Skeptic note: {_top5_skeptic_markdown_path()}")
        if run.warnings:
            print("Warnings:")
            for warning in run.warnings:
                print(f"- {warning}")
        return

    if command == "report-seeds":
        path = _candidate_seed_path()
        seeds = sorted(load_candidate_seeds(path), key=lambda item: item.priority_rank)
        print(f"Candidate seed file: {path}")
        print(f"Imported seeds: {len(seeds)}")
        print("Top-5 verification queue:")
        for seed in seeds[:5]:
            print(
                f"- {seed.id} | rank={seed.priority_rank} | claimed_ds={seed.claimed_discovery_score:.1f} | "
                f"status={seed.verification_status}"
            )
            print(f"  title: {seed.title}")
            print(f"  next: {seed.next_verification_step}")
        return

    if command == "h4-plan":
        path = _h4_spec_path()
        spec = load_h4_spec(path)
        task_card = H4TaskCard.from_spec(spec)
        plan = build_h4_execution_plan(spec)

        print(f"H4 spec: {path}")
        print(f"Candidate: {task_card.candidate_id} | {task_card.title}")
        print(f"Default route: {task_card.default_route} ({task_card.label_type})")
        print(f"Metrics: {', '.join(task_card.metrics)}")
        print(f"Baselines: {', '.join(task_card.baselines)}")
        print(f"Falsification rule: {task_card.falsification_rule}")
        print("Execution plan:")
        for step_number, step in enumerate(plan, start=1):
            print(f"{step_number}. {step}")
        return

    if command == "h4-dataset-card":
        path = _h4_spec_path()
        spec = load_h4_spec(path)
        card = build_h4_dataset_card(spec)
        print(f"Candidate: {card.candidate_id} | {card.title}")
        print(f"Current route: {card.current_route_id} | {card.current_route_title}")
        print(f"Phase-2 routes: {', '.join(card.phase2_route_ids) or 'none'}")
        print(f"Metrics: {', '.join(card.metrics)}")
        print("Routes:")
        for route in card.route_cards:
            print(
                f"- {route.route_id} | default={route.is_default} | accession={route.accession} | "
                f"status={route.route_status} | label_type={route.label_type}"
            )
            print(
                f"  disease={route.disease} unit={route.unit_of_analysis} "
                f"samples={route.sample_count or 'unknown'} cells={route.cell_count or 'unknown'}"
            )
            print(
                f"  evaluation={route.evaluation_level} split_unit={route.split_unit} "
                f"positive_label={route.positive_label}"
            )
            print(f"  group_keys={', '.join(route.group_keys_for_split) or 'none'}")
            print(f"  leakage_keys={', '.join(route.leakage_keys) or 'none'}")
            for note in route.notes:
                print(f"  note: {note}")
            for question in route.blocking_issues:
                print(f"  blocker: {question}")
        return

    if command == "h4-validate-spec":
        path = _h4_spec_path()
        spec = load_h4_spec(path)
        report = validate_h4_spec(spec)
        print(f"H4 spec: {path}")
        print(f"Candidate: {report.candidate_id}")
        print(
            f"Valid: {report.is_valid} | routes={report.route_count} | "
            f"default_routes={report.default_route_count}"
        )
        print("Routes:")
        for route in report.route_reports:
            print(
                f"- {route.route_id} | valid={route.is_valid} | "
                f"default={route.is_default} | status={route.route_status}"
            )
            for error in route.errors:
                print(f"  error: {error}")
            for warning in route.warnings:
                print(f"  warning: {warning}")
        print("Spec errors:")
        for item in report.errors or ["none"]:
            print(f"- {item}")
        print("Spec warnings:")
        for item in report.warnings or ["none"]:
            print(f"- {item}")
        return

    if command == "h4-audit-plan":
        path = _h4_spec_path()
        spec = load_h4_spec(path)
        route_id = sys.argv[2] if len(sys.argv) > 2 else None
        plan = build_h4_audit_plan(spec, route_id=route_id)
        print(f"H4 route: {plan.route_id} | accession={plan.accession}")
        print(
            f"Status: {plan.route_status} | unit={plan.unit_of_analysis} | "
            f"evaluation={plan.evaluation_level} | split_unit={plan.split_unit}"
        )
        print(f"Group keys: {', '.join(plan.group_keys_for_split) or 'none'}")
        print(f"Leakage keys: {', '.join(plan.leakage_keys) or 'none'}")
        print("Blocking issues:")
        for item in plan.blocking_issues or ["none"]:
            print(f"- {item}")
        print("Audit checks:")
        for item in plan.audit_checks:
            print(f"- {item}")
        print("Raw ingress steps:")
        for item in plan.raw_ingress_steps:
            print(f"- {item}")
        return

    if command == "top5-board":
        path = _top5_board_path()
        board = load_top5_board(path)
        print(f"Top-5 board: {path}")
        for item in board:
            print(f"- #{item['rank']} {item['id']} | {item['status']}")
            print(f"  title: {item['title']}")
            print(f"  rationale: {item['rationale']}")
            print(f"  next: {item['next_action']}")
        return

    if command == "h10-plan":
        path = _h10_spec_path()
        spec = load_h10_spec(path)
        task_card = H10TaskCard.from_spec(spec)
        plan = build_h10_execution_plan(spec)

        print(f"H10 spec: {path}")
        print(f"Candidate: {task_card.candidate_id} | {task_card.title}")
        print(f"Default label route: {task_card.label_route} ({task_card.label_type})")
        print(f"Metrics: {', '.join(task_card.metrics)}")
        print(f"Baselines: {', '.join(task_card.baselines)}")
        print(f"Falsification rule: {task_card.falsification_rule}")
        print("Execution plan:")
        for step_number, step in enumerate(plan, start=1):
            print(f"{step_number}. {step}")
        return

    if command == "h10-routes":
        route_dir = _h10_route_dir()
        route_files = sorted(route_dir.glob("*.json"))
        print(f"H10 routes: {route_dir}")
        for route_file in route_files:
            route = load_h10_route(route_file)
            report = validate_h10_route(route, _project_root())
            print(
                f"- {report.route_id} | required_found={report.found_required} "
                f"required_missing={report.missing_required} "
                f"optional_found={report.found_optional} optional_missing={report.missing_optional}"
            )
            print(f"  title: {report.title}")
            if report.missing_paths:
                print("  missing:")
                for missing in report.missing_paths:
                    print(f"    - {missing}")
        return

    if command == "h10-init-route":
        route_file = _h10_default_route_path()
        route = load_h10_route(route_file)
        created = initialize_route_templates(route, _project_root())
        print(f"Initialized route templates for: {route.get('route_id')}")
        if created:
            for path in created:
                print(f"- created: {path}")
        else:
            print("- no files created; all templates already existed")
        return

    if command == "h10-dataset-card":
        route_file = _h10_default_route_path()
        route = load_h10_route(route_file)
        card = build_h10_dataset_card(route, _project_root())
        print(f"Route: {card.route_id} | {card.title}")
        print(f"Ready for mapping: {card.ready_for_mapping}")
        print(f"Total rows across CSV assets: {card.total_rows}")
        print("Assets:")
        for asset in card.assets:
            print(f"- {asset.path} | exists={asset.exists} | rows={asset.row_count}")
            if asset.columns:
                print(f"  columns: {', '.join(asset.columns)}")
        return

    if command == "h10-map":
        route_file = _h10_default_route_path()
        route = load_h10_route(route_file)
        target_name = sys.argv[2] if len(sys.argv) > 2 else None
        mapping = build_h10_mapped_dataset(
            route,
            _project_root(),
            target_name=target_name,
            write_output=True,
        )
        print(f"Route: {mapping.route_id} | {mapping.title}")
        print(f"Target: {mapping.target_name or 'unresolved'}")
        print(f"Output: {mapping.output_path}")
        print(f"Rows: {mapping.row_count} | distinct_structures={mapping.distinct_structures}")
        print("Available targets:")
        for item in mapping.available_targets or ["none"]:
            print(f"- {item}")
        print("Target distribution:")
        for item in mapping.target_distribution or ["none"]:
            print(f"- {item}")
        print("Split distribution:")
        for item in mapping.split_distribution or ["none"]:
            print(f"- {item}")
        print("Warnings:")
        for item in mapping.warnings or ["none"]:
            print(f"- {item}")
        print("Blockers:")
        for item in mapping.blockers or ["none"]:
            print(f"- {item}")
        return

    if command == "h10-import-mofsimplify":
        route_file = _h10_default_route_path()
        route = load_h10_route(route_file)
        archive_path = Path(sys.argv[2]) if len(sys.argv) > 2 else _h10_default_archive_path()
        report = import_mofsimplify_solvent_route(archive_path, route, _project_root())
        print(f"Route: {report.route_id}")
        print(f"Archive: {report.archive_path}")
        print(f"Rows imported: {report.rows_written}")
        print(f"Structures CSV: {report.structures_path}")
        print(f"Labels CSV: {report.labels_path}")
        print(f"Join keys CSV: {report.join_keys_path}")
        print("Available targets:")
        for item in report.available_targets or ["none"]:
            print(f"- {item}")
        print("Class balance:")
        for item in report.class_balance or ["none"]:
            print(f"- {item}")
        return

    if command == "h10-readiness":
        route_file = _h10_default_route_path()
        route = load_h10_route(route_file)
        validation = validate_h10_route(route, _project_root())
        card = build_h10_dataset_card(route, _project_root())
        mapping = build_h10_mapped_dataset(route, _project_root(), write_output=False)
        readiness = build_h10_readiness_report(validation, card, mapping)
        print(f"Route: {readiness.route_id}")
        print(f"Ready: {readiness.is_ready}")
        print("Blockers:")
        for blocker in readiness.blockers or ["none"]:
            print(f"- {blocker}")
        return

    if command == "h10-baseline-scaffold":
        scaffold = build_h10_baseline_scaffold(
            project_root=_project_root(),
            spec=load_h10_spec(_h10_spec_path()),
            mapped_dataset_path=_h10_mapped_dataset_path(),
            archive_path=_h10_default_archive_path(),
            descriptor_output_path=_h10_descriptor_feature_path(),
            graph_artifact_path=_h10_graph_artifact_path(),
            scaffold_output_path=_h10_scaffold_output_path(),
            baseline_matrix_doc_path=_h10_baseline_doc_path(),
        )
        print(f"Route: {scaffold.route_id}")
        print(f"Target: {scaffold.target_name}")
        print(f"Mapped rows: {scaffold.total_rows}")
        print("Split summaries:")
        for split in scaffold.split_summaries:
            print(
                f"- {split.split} | rows={split.row_count} | class_balance={', '.join(split.class_balance)}"
            )
        print("Baselines:")
        for baseline in scaffold.baselines:
            print(
                f"- {baseline.baseline_id} | status={baseline.status} | "
                f"train_ready={baseline.ready_for_training} | rows={baseline.row_count} | features={baseline.feature_count}"
            )
            for blocker in baseline.blockers:
                print(f"  blocker: {blocker}")
        print("Project blockers:")
        for item in scaffold.blockers or ["none"]:
            print(f"- {item}")
        print(f"Scaffold JSON: {_h10_scaffold_output_path()}")
        print(f"Baseline doc: {_h10_baseline_doc_path()}")
        return

    if command == "h10-run-descriptor-baseline":
        run = run_h10_descriptor_baseline(
            project_root=_project_root(),
            descriptor_feature_path=_h10_descriptor_feature_path(),
            report_output_path=_h10_descriptor_report_path(),
            predictions_output_path=_h10_descriptor_predictions_path(),
            markdown_output_path=_h10_descriptor_doc_path(),
        )
        print(f"Model: {run.model_id}")
        print(f"Target: {run.target_name}")
        print(f"Rows: train={run.train_rows} val={run.val_rows} test={run.test_rows}")
        print(f"Features: {run.feature_count}")
        print(f"Selected params: {run.selected_params}")
        print(
            "Validation metrics: "
            f"ap={run.val_metrics.average_precision:.6f} "
            f"roc_auc={run.val_metrics.roc_auc:.6f} "
            f"balanced_accuracy={run.val_metrics.balanced_accuracy:.6f} "
            f"threshold={run.val_metrics.threshold:.6f}"
        )
        print(
            "Test metrics: "
            f"ap={run.test_metrics.average_precision:.6f} "
            f"roc_auc={run.test_metrics.roc_auc:.6f} "
            f"balanced_accuracy={run.test_metrics.balanced_accuracy:.6f} "
            f"threshold={run.test_metrics.threshold:.6f}"
        )
        print(f"Report JSON: {_h10_descriptor_report_path()}")
        print(f"Predictions CSV: {_h10_descriptor_predictions_path()}")
        print(f"Baseline doc: {_h10_descriptor_doc_path()}")
        return

    if command == "h10-run-descriptor-tree-baseline":
        run = run_h10_descriptor_tree_baseline(
            project_root=_project_root(),
            descriptor_feature_path=_h10_descriptor_feature_path(),
            report_output_path=_h10_descriptor_tree_report_path(),
            predictions_output_path=_h10_descriptor_tree_predictions_path(),
            markdown_output_path=_h10_descriptor_tree_doc_path(),
        )
        print(f"Model: {run.model_id}")
        print(f"Target: {run.target_name}")
        print(f"Rows: train={run.train_rows} val={run.val_rows} test={run.test_rows}")
        print(f"Features: {run.feature_count}")
        print(f"Selected params: {run.selected_params}")
        print(
            "Validation metrics: "
            f"ap={run.val_metrics.average_precision:.6f} "
            f"roc_auc={run.val_metrics.roc_auc:.6f} "
            f"balanced_accuracy={run.val_metrics.balanced_accuracy:.6f} "
            f"threshold={run.val_metrics.threshold:.6f}"
        )
        print(
            "Test metrics: "
            f"ap={run.test_metrics.average_precision:.6f} "
            f"roc_auc={run.test_metrics.roc_auc:.6f} "
            f"balanced_accuracy={run.test_metrics.balanced_accuracy:.6f} "
            f"threshold={run.test_metrics.threshold:.6f}"
        )
        print(f"Report JSON: {_h10_descriptor_tree_report_path()}")
        print(f"Predictions CSV: {_h10_descriptor_tree_predictions_path()}")
        print(f"Baseline doc: {_h10_descriptor_tree_doc_path()}")
        return

    if command == "h10-build-graph-artifact":
        report = build_h10_graph_artifact(
            project_root=_project_root(),
            mapped_dataset_path=_h10_mapped_dataset_path(),
            graph_output_path=_h10_graph_artifact_path(),
            summary_output_path=_h10_graph_summary_path(),
        )
        print(f"Dataset: {report.dataset}")
        print(f"Rows requested: {report.rows_requested}")
        print(f"Rows built: {report.rows_built}")
        print(f"Failures: {report.failures}")
        print(f"Average nodes: {report.avg_nodes:.2f}")
        print(f"Average edges: {report.avg_edges:.2f}")
        print(f"Max nodes: {report.max_nodes}")
        print(f"Max edges: {report.max_edges}")
        print(f"Graph artifact: {_h10_graph_artifact_path()}")
        print(f"Summary JSON: {_h10_graph_summary_path()}")
        if report.failure_examples:
            print("Failure examples:")
            for item in report.failure_examples:
                print(f"- {item}")
        return

    if command == "h10-run-graph-baseline":
        run = run_h10_graph_baseline(
            project_root=_project_root(),
            graph_artifact_path=_h10_graph_artifact_path(),
            report_output_path=_h10_graph_report_path(),
            predictions_output_path=_h10_graph_predictions_path(),
            markdown_output_path=_h10_graph_doc_path(),
        )
        print(f"Model: {run.model_id}")
        print(f"Target: {run.target_name}")
        print(f"Rows: train={run.train_rows} val={run.val_rows} test={run.test_rows}")
        print(f"Graph feature dim: {run.graph_feature_dim}")
        print(f"Selected params: {run.selected_params}")
        print(
            "Validation metrics: "
            f"ap={run.val_metrics.average_precision:.6f} "
            f"roc_auc={run.val_metrics.roc_auc:.6f} "
            f"balanced_accuracy={run.val_metrics.balanced_accuracy:.6f} "
            f"threshold={run.val_metrics.threshold:.6f}"
        )
        print(
            "Test metrics: "
            f"ap={run.test_metrics.average_precision:.6f} "
            f"roc_auc={run.test_metrics.roc_auc:.6f} "
            f"balanced_accuracy={run.test_metrics.balanced_accuracy:.6f} "
            f"threshold={run.test_metrics.threshold:.6f}"
        )
        print(f"Report JSON: {_h10_graph_report_path()}")
        print(f"Predictions CSV: {_h10_graph_predictions_path()}")
        print(f"Baseline doc: {_h10_graph_doc_path()}")
        return

    if command == "h10-run-graph-mpnn-baseline":
        run = run_h10_graph_mpnn_baseline(
            project_root=_project_root(),
            graph_artifact_path=_h10_graph_artifact_path(),
            report_output_path=_h10_graph_mpnn_report_path(),
            predictions_output_path=_h10_graph_mpnn_predictions_path(),
            markdown_output_path=_h10_graph_mpnn_doc_path(),
        )
        print(f"Model: {run.model_id}")
        print(f"Target: {run.target_name}")
        print(f"Rows: train={run.train_rows} val={run.val_rows} test={run.test_rows}")
        print(f"Hidden dim: {run.hidden_dim}")
        print(f"Selected params: {run.selected_params}")
        print(
            "Validation metrics: "
            f"ap={run.val_metrics.average_precision:.6f} "
            f"roc_auc={run.val_metrics.roc_auc:.6f} "
            f"balanced_accuracy={run.val_metrics.balanced_accuracy:.6f} "
            f"threshold={run.val_metrics.threshold:.6f}"
        )
        print(
            "Test metrics: "
            f"ap={run.test_metrics.average_precision:.6f} "
            f"roc_auc={run.test_metrics.roc_auc:.6f} "
            f"balanced_accuracy={run.test_metrics.balanced_accuracy:.6f} "
            f"threshold={run.test_metrics.threshold:.6f}"
        )
        print(f"Report JSON: {_h10_graph_mpnn_report_path()}")
        print(f"Predictions CSV: {_h10_graph_mpnn_predictions_path()}")
        print(f"Baseline doc: {_h10_graph_mpnn_doc_path()}")
        return

    if command == "h10-run-hybrid-baseline":
        run = run_h10_hybrid_baseline(
            project_root=_project_root(),
            descriptor_feature_path=_h10_descriptor_feature_path(),
            graph_artifact_path=_h10_graph_artifact_path(),
            report_output_path=_h10_hybrid_report_path(),
            predictions_output_path=_h10_hybrid_predictions_path(),
            markdown_output_path=_h10_hybrid_doc_path(),
        )
        print(f"Model: {run.model_id}")
        print(f"Target: {run.target_name}")
        print(f"Rows: train={run.train_rows} val={run.val_rows} test={run.test_rows}")
        print(
            "Feature counts: "
            f"descriptor={run.descriptor_feature_count} "
            f"graph={run.graph_feature_count} "
            f"total={run.total_feature_count}"
        )
        print(f"Selected params: {run.selected_params}")
        print(
            "Validation metrics: "
            f"ap={run.val_metrics.average_precision:.6f} "
            f"roc_auc={run.val_metrics.roc_auc:.6f} "
            f"balanced_accuracy={run.val_metrics.balanced_accuracy:.6f} "
            f"threshold={run.val_metrics.threshold:.6f}"
        )
        print(
            "Test metrics: "
            f"ap={run.test_metrics.average_precision:.6f} "
            f"roc_auc={run.test_metrics.roc_auc:.6f} "
            f"balanced_accuracy={run.test_metrics.balanced_accuracy:.6f} "
            f"threshold={run.test_metrics.threshold:.6f}"
        )
        print(f"Report JSON: {_h10_hybrid_report_path()}")
        print(f"Predictions CSV: {_h10_hybrid_predictions_path()}")
        print(f"Baseline doc: {_h10_hybrid_doc_path()}")
        return

    # ── External source collectors ───────────────────────────────────

    if command == "fetch-scholar":
        query = sys.argv[2] if len(sys.argv) > 2 else "interdisciplinary biology materials"
        max_results = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        records = fetch_semantic_scholar(query=query, max_results=max_results)
        normalized, report = normalize_sources(records)
        saved = _save_manifest(normalized, "scholar_latest")
        print(f"Semantic Scholar | query: {query}")
        print(
            f"Fetched: {report.total_input} | Kept: {report.kept} | Deduped: {report.deduplicated}"
        )
        print(f"Saved: {saved}")
        for record in normalized[:5]:
            print(
                f"- {record.id} | {record.domain} | authority={record.authority_score:.2f} "
                f"| tags={', '.join(record.bridge_tags[:4]) or 'none'}"
            )
            print(f"  {record.title[:100]}")
        if report.warnings:
            print(f"Warnings: {len(report.warnings)}")
        return

    if command == "fetch-biorxiv":
        interval = sys.argv[2] if len(sys.argv) > 2 else "2025-01-01/2026-03-26"
        max_results = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        records = fetch_biorxiv(interval=interval, max_results=max_results)
        normalized, report = normalize_sources(records)
        saved = _save_manifest(normalized, "biorxiv_latest")
        print(f"bioRxiv | interval: {interval}")
        print(
            f"Fetched: {report.total_input} | Kept: {report.kept} | Deduped: {report.deduplicated}"
        )
        print(f"Saved: {saved}")
        for record in normalized[:5]:
            print(
                f"- {record.id} | {record.domain} | authority={record.authority_score:.2f} "
                f"| tags={', '.join(record.bridge_tags[:4]) or 'none'}"
            )
            print(f"  {record.title[:100]}")
        return

    if command == "fetch-zenodo":
        query = sys.argv[2] if len(sys.argv) > 2 else "metal-organic framework dataset"
        max_results = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        records = fetch_zenodo(query=query, max_results=max_results)
        normalized, report = normalize_sources(records)
        saved = _save_manifest(normalized, "zenodo_latest")
        print(f"Zenodo | query: {query}")
        print(
            f"Fetched: {report.total_input} | Kept: {report.kept} | Deduped: {report.deduplicated}"
        )
        print(f"Saved: {saved}")
        for record in normalized[:5]:
            print(
                f"- {record.id} | {record.domain} | authority={record.authority_score:.2f} "
                f"| tags={', '.join(record.bridge_tags[:4]) or 'none'}"
            )
            print(f"  {record.title[:100]}")
        return

    if command == "fetch-all":
        query = (
            sys.argv[2] if len(sys.argv) > 2 else "interdisciplinary hypothesis biology materials"
        )
        max_per_source = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        all_records: list[SourceRecord] = []
        for name, fetcher in [
            ("scholar", lambda: fetch_semantic_scholar(query=query, max_results=max_per_source)),
            ("biorxiv", lambda: fetch_biorxiv(max_results=max_per_source)),
            ("zenodo", lambda: fetch_zenodo(query=query, max_results=max_per_source)),
        ]:
            try:
                batch = fetcher()
                all_records.extend(batch)
                print(f"  {name}: {len(batch)} records")
            except Exception as exc:
                print(f"  {name}: FAILED ({exc})")
        normalized, report = normalize_sources(all_records)
        saved = _save_manifest(normalized, "external_sources")
        print(
            f"Total fetched: {report.total_input} | Kept: {report.kept} | Deduped: {report.deduplicated}"
        )
        print(f"Saved: {saved}")
        # Domain breakdown
        domain_counts: dict[str, int] = {}
        for record in normalized:
            domain_counts[record.domain] = domain_counts.get(record.domain, 0) + 1
        print("Domains:")
        for domain, count in sorted(domain_counts.items(), key=lambda x: -x[1]):
            print(f"  {domain}: {count}")
        return

    raise SystemExit(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
