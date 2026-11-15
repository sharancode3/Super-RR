"""Command Line Interface for rr_pressure."""

import argparse
import sys
from pathlib import Path
from typing import Optional

from rr_pressure.config import PipelineConfig, default_raw_dir
from rr_pressure.manifest import generate_input_manifest, compute_sha256
from rr_pressure.ingest import run_identity_audit
from rr_pressure.ledger import run_stage02_ledger
from rr_pressure.eda import run_eda_analysis
from rr_pressure.split import run_stage04_split
from rr_pressure.models import train_and_evaluate_models
from rr_pressure.pressure import run_stage06_pressure
from rr_pressure.impact import run_stage07_impact
from rr_pressure.forecast import run_stage08_forecast
from rr_pressure.compare import run_stage09_comparison
from rr_pressure.robustness import run_stage10_robustness
from rr_pressure.rankings import run_stage11_rankings
from rr_pressure.exports import run_stage12_exports
from rr_pressure.recovery import run_recovery_gate
from rr_pressure.progress import record_stage, get_default_progress_path


def cmd_recovery(args: argparse.Namespace) -> int:
    config = PipelineConfig(
        raw_dir=Path(args.raw_dir),
        out_dir=Path(args.out_dir),
        public_dir=Path(args.public_dir) if args.public_dir else None,
        seed=args.seed,
    )
    print(f"Running Recovery Gate on {config.raw_dir} -> {config.out_dir}...")
    evidence, output_fingerprints = run_recovery_gate(config)
    
    prog_path = get_default_progress_path(config.out_dir)
    record_stage(
        progress_path=prog_path,
        stage_id="recovery",
        status="PASS",
        command="python -m rr_pressure recovery --raw-dir " + str(config.raw_dir) + " --out-dir " + str(config.out_dir),
        next_prompt="round1_prompts/00_project_contract.md",
        resume_prompt=None,
        input_fingerprints={},
        output_fingerprints=output_fingerprints,
        output_paths=[str(config.out_dir / fname) for fname in output_fingerprints.keys()],
        evidence=evidence,
        open_issues=[],
        release_status="IN_PROGRESS",
    )
    print("Recovery gate completed. Checkpoint established in artifacts_revalidated.")
    return 0


def cmd_manifest(args: argparse.Namespace) -> int:
    config = PipelineConfig(
        raw_dir=Path(args.raw_dir),
        out_dir=Path(args.out_dir),
        public_dir=Path(args.public_dir) if args.public_dir else None,
        seed=args.seed,
    )
    print(f"Generating input manifest from {config.raw_dir} -> {config.out_dir}...")
    manifest = generate_input_manifest(config)
    manifest_path = config.out_dir / "input_manifest.json"
    print(f"Manifest written successfully: {manifest_path} ({len(manifest['files'])} files)")
    
    prog_path = get_default_progress_path(config.out_dir)
    record_stage(
        progress_path=prog_path,
        stage_id="00",
        status="PASS",
        command="python -m rr_pressure manifest --raw-dir " + str(config.raw_dir) + " --out-dir " + str(config.out_dir),
        next_prompt="round1_prompts/01_ingest_identity.md",
        resume_prompt=None,
        input_fingerprints={fname: meta["sha256"] for fname, meta in manifest["files"].items()},
        output_fingerprints={"input_manifest.json": compute_sha256(manifest_path)},
        output_paths=[str(manifest_path)],
        evidence={
            "files_verified": len(manifest["files"]),
            "python_version": manifest["environment"]["python_version"],
            "seed": config.seed,
            "manifest_path": str(manifest_path),
        },
        open_issues=[
            manifest["audit_notes"]["missing_public_archives"],
            manifest["audit_notes"]["unverified_dropdown_pool"],
        ],
        release_status="IN_PROGRESS",
    )
    print("Stage 00 contract established and recorded in round1_progress.json.")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    config = PipelineConfig(
        raw_dir=Path(args.raw_dir),
        out_dir=Path(args.out_dir),
        public_dir=Path(args.public_dir) if args.public_dir else None,
        seed=args.seed,
    )
    print(f"Running Stage 01 identity & grain audit on {config.raw_dir}...")
    audit_data, output_fingerprints = run_identity_audit(config)
    
    prog_path = get_default_progress_path(config.out_dir)
    record_stage(
        progress_path=prog_path,
        stage_id="01",
        status="PASS",
        command="python -m rr_pressure audit --raw-dir " + str(config.raw_dir) + " --out-dir " + str(config.out_dir),
        next_prompt="round1_prompts/02_scoreboard_ledgers.md",
        resume_prompt=None,
        input_fingerprints={},
        output_fingerprints=output_fingerprints,
        output_paths=[str(config.out_dir / fname) for fname in output_fingerprints.keys()],
        evidence={
            "total_deliveries": audit_data["delivery_audit"]["total_deliveries"],
            "delivery_key_duplicates": audit_data["delivery_audit"]["delivery_key_duplicates"],
            "total_fixtures": audit_data["fixture_audit"]["total_fixtures"],
            "fixtures_with_deliveries": audit_data["fixture_audit"]["fixtures_with_deliveries"],
            "fixtures_abandoned": audit_data["fixture_audit"]["abandoned_without_deliveries"],
            "xi_conflict_groups": audit_data["playing_eleven_audit"]["conflict_groups"],
            "xi_clean_rows": audit_data["playing_eleven_audit"]["clean_deduped_rows"],
            "total_unique_players": audit_data["player_dimension_audit"]["total_unique_players"],
        },
        open_issues=[],
        release_status="IN_PROGRESS",
    )
    print("Stage 01 audit completed and recorded in round1_progress.json.")
    return 0


def cmd_ledger(args: argparse.Namespace) -> int:
    config = PipelineConfig(
        raw_dir=Path(args.raw_dir),
        out_dir=Path(args.out_dir),
        public_dir=Path(args.public_dir) if args.public_dir else None,
        seed=args.seed,
    )
    print(f"Running Stage 02 Scoreboard Ledger builder on {config.raw_dir}...")
    coverage_report, output_fingerprints = run_stage02_ledger(config)
    
    prog_path = get_default_progress_path(config.out_dir)
    record_stage(
        progress_path=prog_path,
        stage_id="02",
        status="PASS",
        command="python -m rr_pressure ledger --raw-dir " + str(config.raw_dir) + " --out-dir " + str(config.out_dir),
        next_prompt="round1_prompts/03_exploratory_analysis.md",
        resume_prompt=None,
        input_fingerprints={},
        output_fingerprints=output_fingerprints,
        output_paths=[str(config.out_dir / fname) for fname in output_fingerprints.keys()],
        evidence={
            "total_deliveries": coverage_report["total_deliveries"],
            "cohort_eligible_deliveries": coverage_report["cohort_eligible_deliveries"],
            "total_fixtures": coverage_report["total_fixtures"],
            "excluded_fixtures_count": coverage_report["excluded_fixtures_count"],
            "eligible_fixtures_count": coverage_report["eligible_fixtures_count"],
            "quarantined_discrepancies_count": coverage_report["quarantined_discrepancies_count"],
            "route": coverage_report["notes"]["route_used"],
        },
        open_issues=[coverage_report["notes"]["reason_for_proxy"]],
        release_status="IN_PROGRESS",
    )
    print("Stage 02 ledger built and recorded in round1_progress.json.")
    return 0


def cmd_eda(args: argparse.Namespace) -> int:
    config = PipelineConfig(
        raw_dir=Path(args.raw_dir),
        out_dir=Path(args.out_dir),
        public_dir=Path(args.public_dir) if args.public_dir else None,
        seed=args.seed,
    )
    print(f"Running Stage 03 Exploratory Data Analysis on {config.out_dir}...")
    eda_summary, output_fingerprints = run_eda_analysis(config)
    
    prog_path = get_default_progress_path(config.out_dir)
    record_stage(
        progress_path=prog_path,
        stage_id="03",
        status="PASS",
        command="python -m rr_pressure eda --raw-dir " + str(config.raw_dir) + " --out-dir " + str(config.out_dir),
        next_prompt="round1_prompts/04_freeze_evaluation.md",
        resume_prompt=None,
        input_fingerprints={},
        output_fingerprints=output_fingerprints,
        output_paths=[str(config.out_dir / fname) for fname in output_fingerprints.keys()],
        evidence={
            "tier_phase_groups": len(eda_summary["tier_phase_statistics"]),
            "feasibility_combinations": len(eda_summary["feasibility_matrix"]),
            "eda_plot": eda_summary["plot_path"],
        },
        open_issues=[],
        release_status="IN_PROGRESS",
    )
    print("Stage 03 EDA completed and recorded in round1_progress.json.")
    return 0


def cmd_split(args: argparse.Namespace) -> int:
    config = PipelineConfig(
        raw_dir=Path(args.raw_dir),
        out_dir=Path(args.out_dir),
        public_dir=Path(args.public_dir) if args.public_dir else None,
        seed=args.seed,
    )
    print(f"Running Stage 04 Freeze Folds & Protocol on {config.out_dir}...")
    split_manifest, output_fingerprints = run_stage04_split(config)
    
    prog_path = get_default_progress_path(config.out_dir)
    record_stage(
        progress_path=prog_path,
        stage_id="04",
        status="PASS",
        command="python -m rr_pressure split --raw-dir " + str(config.raw_dir) + " --out-dir " + str(config.out_dir),
        next_prompt="round1_prompts/05_match_state_models.md",
        resume_prompt=None,
        input_fingerprints={},
        output_fingerprints=output_fingerprints,
        output_paths=[str(config.out_dir / fname) for fname in output_fingerprints.keys()],
        evidence={
            "total_matches": split_manifest["total_eligible_matches"],
            "train_matches": split_manifest["folds"]["TRAIN_2022_2024"]["match_count"],
            "val_matches": split_manifest["folds"]["VAL_2025"]["match_count"],
            "test_matches": split_manifest["folds"]["TEST_HOLDOUT_2026"]["match_count"],
        },
        open_issues=[],
        release_status="IN_PROGRESS",
    )
    print("Stage 04 evaluation folds frozen and recorded in round1_progress.json.")
    return 0


def cmd_models(args: argparse.Namespace) -> int:
    config = PipelineConfig(
        raw_dir=Path(args.raw_dir),
        out_dir=Path(args.out_dir),
        public_dir=Path(args.public_dir) if args.public_dir else None,
        seed=args.seed,
    )
    print(f"Running Stage 05 Match-State Models & Calibration on {config.out_dir}...")
    diagnostics, output_fingerprints = train_and_evaluate_models(config)
    
    prog_path = get_default_progress_path(config.out_dir)
    record_stage(
        progress_path=prog_path,
        stage_id="05",
        status="PASS",
        command="python -m rr_pressure models --raw-dir " + str(config.raw_dir) + " --out-dir " + str(config.out_dir),
        next_prompt="round1_prompts/06_pressure_definition.md",
        resume_prompt=None,
        input_fingerprints={},
        output_fingerprints=output_fingerprints,
        output_paths=[str(config.out_dir / fname) for fname in output_fingerprints.keys()],
        evidence={
            "inn1_logistic_brier": diagnostics["innings1_validation_2025"]["logistic_brier"],
            "inn2_logistic_brier": diagnostics["innings2_validation_2025"]["logistic_brier"],
            "remaining_runs_r2": diagnostics["remaining_runs_model"]["r2"],
            "marginal_wicket_value": diagnostics["remaining_runs_model"]["marginal_wicket_value_mid"],
            "monotonicity_verified": diagnostics["innings2_validation_2025"]["monotonicity_preserved"],
        },
        open_issues=[],
        release_status="IN_PROGRESS",
    )
    print("Stage 05 models fitted, calibrated and recorded in round1_progress.json.")
    return 0


def cmd_pressure(args: argparse.Namespace) -> int:
    config = PipelineConfig(
        raw_dir=Path(args.raw_dir),
        out_dir=Path(args.out_dir),
        public_dir=Path(args.public_dir) if args.public_dir else None,
        seed=args.seed,
    )
    print(f"Running Stage 06 Pre-Ball Pressure & Leverage on {config.out_dir}...")
    evidence, output_fingerprints = run_stage06_pressure(config)
    
    prog_path = get_default_progress_path(config.out_dir)
    record_stage(
        progress_path=prog_path,
        stage_id="06",
        status="PASS",
        command="python -m rr_pressure pressure --raw-dir " + str(config.raw_dir) + " --out-dir " + str(config.out_dir),
        next_prompt="round1_prompts/07_player_impact.md",
        resume_prompt=None,
        input_fingerprints={},
        output_fingerprints=output_fingerprints,
        output_paths=[str(config.out_dir / fname) for fname in output_fingerprints.keys()],
        evidence=evidence,
        open_issues=[],
        release_status="IN_PROGRESS",
    )
    print("Stage 06 pre-ball pressure labeled and recorded in round1_progress.json.")
    return 0


def cmd_impact(args: argparse.Namespace) -> int:
    config = PipelineConfig(
        raw_dir=Path(args.raw_dir),
        out_dir=Path(args.out_dir),
        public_dir=Path(args.public_dir) if args.public_dir else None,
        seed=args.seed,
    )
    print(f"Running Stage 07 Player Impact & Attribution on {config.out_dir}...")
    evidence, output_fingerprints = run_stage07_impact(config)
    
    prog_path = get_default_progress_path(config.out_dir)
    record_stage(
        progress_path=prog_path,
        stage_id="07",
        status="PASS",
        command="python -m rr_pressure impact --raw-dir " + str(config.raw_dir) + " --out-dir " + str(config.out_dir),
        next_prompt="round1_prompts/08_reliability_forecast.md",
        resume_prompt=None,
        input_fingerprints={},
        output_fingerprints=output_fingerprints,
        output_paths=[str(config.out_dir / fname) for fname in output_fingerprints.keys()],
        evidence=evidence,
        open_issues=[],
        release_status="IN_PROGRESS",
    )
    print("Stage 07 player impact converted and recorded in round1_progress.json.")
    return 0


def cmd_forecast(args: argparse.Namespace) -> int:
    config = PipelineConfig(
        raw_dir=Path(args.raw_dir),
        out_dir=Path(args.out_dir),
        public_dir=Path(args.public_dir) if args.public_dir else None,
        seed=args.seed,
    )
    print(f"Running Stage 08 Reliability Forecast on {config.out_dir}...")
    evidence, output_fingerprints = run_stage08_forecast(config)
    
    prog_path = get_default_progress_path(config.out_dir)
    record_stage(
        progress_path=prog_path,
        stage_id="08",
        status="PASS",
        command="python -m rr_pressure forecast --raw-dir " + str(config.raw_dir) + " --out-dir " + str(config.out_dir),
        next_prompt="round1_prompts/09_model_comparison.md",
        resume_prompt=None,
        input_fingerprints={},
        output_fingerprints=output_fingerprints,
        output_paths=[str(config.out_dir / fname) for fname in output_fingerprints.keys()],
        evidence=evidence,
        open_issues=[],
        release_status="IN_PROGRESS",
    )
    print("Stage 08 reliability forecasts fitted and recorded in round1_progress.json.")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    config = PipelineConfig(
        raw_dir=Path(args.raw_dir),
        out_dir=Path(args.out_dir),
        public_dir=Path(args.public_dir) if args.public_dir else None,
        seed=args.seed,
    )
    print(f"Running Stage 09 Model Comparison on {config.out_dir}...")
    evidence, output_fingerprints = run_stage09_comparison(config)
    
    prog_path = get_default_progress_path(config.out_dir)
    record_stage(
        progress_path=prog_path,
        stage_id="09",
        status="PASS",
        command="python -m rr_pressure compare --raw-dir " + str(config.raw_dir) + " --out-dir " + str(config.out_dir),
        next_prompt="round1_prompts/10_robustness_checks.md",
        resume_prompt=None,
        input_fingerprints={},
        output_fingerprints=output_fingerprints,
        output_paths=[str(config.out_dir / fname) for fname in output_fingerprints.keys()],
        evidence=evidence,
        open_issues=[],
        release_status="IN_PROGRESS",
    )
    print("Stage 09 model comparison completed and recorded in round1_progress.json.")
    return 0


def cmd_robustness(args: argparse.Namespace) -> int:
    config = PipelineConfig(
        raw_dir=Path(args.raw_dir),
        out_dir=Path(args.out_dir),
        public_dir=Path(args.public_dir) if args.public_dir else None,
        seed=args.seed,
    )
    print(f"Running Stage 10 Robustness Checks on {config.out_dir}...")
    evidence, output_fingerprints = run_stage10_robustness(config)
    
    prog_path = get_default_progress_path(config.out_dir)
    record_stage(
        progress_path=prog_path,
        stage_id="10",
        status="PASS",
        command="python -m rr_pressure robustness --raw-dir " + str(config.raw_dir) + " --out-dir " + str(config.out_dir),
        next_prompt="round1_prompts/11_rankings_and_eligibility.md",
        resume_prompt=None,
        input_fingerprints={},
        output_fingerprints=output_fingerprints,
        output_paths=[str(config.out_dir / fname) for fname in output_fingerprints.keys()],
        evidence=evidence,
        open_issues=[],
        release_status="IN_PROGRESS",
    )
    print("Stage 10 robustness checks completed and recorded in round1_progress.json.")
    return 0


def cmd_rank(args: argparse.Namespace) -> int:
    config = PipelineConfig(
        raw_dir=Path(args.raw_dir),
        out_dir=Path(args.out_dir),
        public_dir=Path(args.public_dir) if args.public_dir else None,
        seed=args.seed,
    )
    print(f"Running Stage 11 Rankings and RR Shortlist generator on {config.out_dir}...")
    evidence, output_fingerprints = run_stage11_rankings(config)
    
    prog_path = get_default_progress_path(config.out_dir)
    # Status is PASS on model rankings, with resume_prompt set to 11 for dropdown reconciliation
    record_stage(
        progress_path=prog_path,
        stage_id="11",
        status="PASS",
        command="python -m rr_pressure rank --raw-dir " + str(config.raw_dir) + " --out-dir " + str(config.out_dir),
        next_prompt="round1_prompts/12_terminal_exports.md",
        resume_prompt="round1_prompts/11_rankings_and_eligibility.md",
        input_fingerprints={},
        output_fingerprints=output_fingerprints,
        output_paths=[str(config.out_dir / fname) for fname in output_fingerprints.keys()],
        evidence=evidence,
        open_issues=["Live Unstop dropdown selection pool currently unverified on portal; PROVISIONAL names exported with Stage 11 resume point."],
        release_status="PROVISIONAL",
    )
    print("Stage 11 rankings generated and recorded in round1_progress.json.")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    config = PipelineConfig(
        raw_dir=Path(args.raw_dir),
        out_dir=Path(args.out_dir),
        public_dir=Path(args.public_dir) if args.public_dir else None,
        seed=args.seed,
    )
    print(f"Running Stage 12 Terminal Views and Official Exports on {config.out_dir}...")
    evidence, output_fingerprints = run_stage12_exports(config)
    
    prog_path = get_default_progress_path(config.out_dir)
    record_stage(
        progress_path=prog_path,
        stage_id="12",
        status="PASS",
        command="python -m rr_pressure export --raw-dir " + str(config.raw_dir) + " --out-dir " + str(config.out_dir),
        next_prompt="round1_prompts/13_release_verification.md",
        resume_prompt="round1_prompts/11_rankings_and_eligibility.md",
        input_fingerprints={},
        output_fingerprints=output_fingerprints,
        output_paths=[str(config.out_dir / fname) for fname in output_fingerprints.keys()],
        evidence=evidence,
        open_issues=["Live Unstop dropdown selection pool unverified on portal; PROVISIONAL snapshot exported with Stage 11 resume point."],
        release_status="PROVISIONAL",
    )
    print("Stage 12 exports produced and recorded in round1_progress.json.")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """End-to-end reproducible runner executing Stages 00 through 12 sequentially."""
    print("================================================================================")
    print("Executing SupeRR Selector Season 2 Full Pipeline End-to-End...")
    print("================================================================================")
    
    # 00. Manifest
    cmd_manifest(args)
    # 01. Audit
    cmd_audit(args)
    # 02. Ledger
    cmd_ledger(args)
    # 03. EDA
    cmd_eda(args)
    # 04. Split
    cmd_split(args)
    # 05. Models
    cmd_models(args)
    # 06. Pressure
    cmd_pressure(args)
    # 07. Impact
    cmd_impact(args)
    # 08. Forecast
    cmd_forecast(args)
    # 09. Compare
    cmd_compare(args)
    # 10. Robustness
    cmd_robustness(args)
    # 11. Rankings
    cmd_rank(args)
    # 12. Exports
    ret = cmd_export(args)
    return ret


def build_parser() -> argparse.ArgumentParser:
    raw_default = str(default_raw_dir())
    parser = argparse.ArgumentParser(
        prog="rr_pressure",
        description="SupeRR Selector Season 2 - Rajasthan Royals Pressure Analytics Pipeline",
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to execute")
    
    # recovery gate subcommand
    p_recovery = subparsers.add_parser("recovery", help="Revalidate existing run and isolate repair checkpoint")
    p_recovery.add_argument("--raw-dir", default=raw_default, help="Path to raw data directory")
    p_recovery.add_argument("--out-dir", default="artifacts_revalidated", help="Path to revalidated output directory")
    p_recovery.add_argument("--public-dir", default=None, help="Optional path to public cricsheet cache")
    p_recovery.add_argument("--seed", type=int, default=2027, help="Random seed")
    p_recovery.set_defaults(func=cmd_recovery)

    # manifest / stage 00 command
    p_manifest = subparsers.add_parser("manifest", help="Generate and verify immutable input manifest")
    p_manifest.add_argument("--raw-dir", default=raw_default, help="Path to raw data directory")
    p_manifest.add_argument("--out-dir", default="artifacts", help="Path to artifacts output directory")
    p_manifest.add_argument("--public-dir", default=None, help="Optional path to public cricsheet cache")
    p_manifest.add_argument("--seed", type=int, default=2027, help="Random seed")
    p_manifest.set_defaults(func=cmd_manifest)
    
    # audit subcommand (Stage 01)
    p_audit = subparsers.add_parser("audit", help="Ingest and audit dataset identity (Stage 01)")
    p_audit.add_argument("--raw-dir", default=raw_default, help="Path to raw data directory")
    p_audit.add_argument("--out-dir", default="artifacts", help="Path to artifacts output directory")
    p_audit.add_argument("--public-dir", default=None, help="Optional path to public cricsheet cache")
    p_audit.add_argument("--seed", type=int, default=2027, help="Random seed")
    p_audit.set_defaults(func=cmd_audit)

    # ledger subcommand (Stage 02)
    p_ledger = subparsers.add_parser("ledger", help="Build scoreboard state ledger (Stage 02)")
    p_ledger.add_argument("--raw-dir", default=raw_default, help="Path to raw data directory")
    p_ledger.add_argument("--out-dir", default="artifacts", help="Path to artifacts output directory")
    p_ledger.add_argument("--public-dir", default=None, help="Optional path to public cricsheet cache")
    p_ledger.add_argument("--seed", type=int, default=2027, help="Random seed")
    p_ledger.set_defaults(func=cmd_ledger)

    # eda subcommand (Stage 03)
    p_eda = subparsers.add_parser("eda", help="Run exploratory analysis and build feature dictionary (Stage 03)")
    p_eda.add_argument("--raw-dir", default=raw_default, help="Path to raw data directory")
    p_eda.add_argument("--out-dir", default="artifacts", help="Path to artifacts output directory")
    p_eda.add_argument("--public-dir", default=None, help="Optional path to public cricsheet cache")
    p_eda.add_argument("--seed", type=int, default=2027, help="Random seed")
    p_eda.set_defaults(func=cmd_eda)

    # split subcommand (Stage 04)
    p_split = subparsers.add_parser("split", help="Freeze evaluation folds and reference protocol (Stage 04)")
    p_split.add_argument("--raw-dir", default=raw_default, help="Path to raw data directory")
    p_split.add_argument("--out-dir", default="artifacts", help="Path to artifacts output directory")
    p_split.add_argument("--public-dir", default=None, help="Optional path to public cricsheet cache")
    p_split.add_argument("--seed", type=int, default=2027, help="Random seed")
    p_split.set_defaults(func=cmd_split)

    # models subcommand (Stage 05)
    p_models = subparsers.add_parser("models", help="Train and calibrate match-state models (Stage 05)")
    p_models.add_argument("--raw-dir", default=raw_default, help="Path to raw data directory")
    p_models.add_argument("--out-dir", default="artifacts", help="Path to artifacts output directory")
    p_models.add_argument("--public-dir", default=None, help="Optional path to public cricsheet cache")
    p_models.add_argument("--seed", type=int, default=2027, help="Random seed")
    p_models.set_defaults(func=cmd_models)

    # pressure subcommand (Stage 06)
    p_pressure = subparsers.add_parser("pressure", help="Identify pre-ball leverage and pressure (Stage 06)")
    p_pressure.add_argument("--raw-dir", default=raw_default, help="Path to raw data directory")
    p_pressure.add_argument("--out-dir", default="artifacts", help="Path to artifacts output directory")
    p_pressure.add_argument("--public-dir", default=None, help="Optional path to public cricsheet cache")
    p_pressure.add_argument("--seed", type=int, default=2027, help="Random seed")
    p_pressure.set_defaults(func=cmd_pressure)

    # impact subcommand (Stage 07)
    p_impact = subparsers.add_parser("impact", help="Convert runs and wickets into player impact (Stage 07)")
    p_impact.add_argument("--raw-dir", default=raw_default, help="Path to raw data directory")
    p_impact.add_argument("--out-dir", default="artifacts", help="Path to artifacts output directory")
    p_impact.add_argument("--public-dir", default=None, help="Optional path to public cricsheet cache")
    p_impact.add_argument("--seed", type=int, default=2027, help="Random seed")
    p_impact.set_defaults(func=cmd_impact)

    # forecast subcommand (Stage 08)
    p_forecast = subparsers.add_parser("forecast", help="Fit empirical Bayes reliability forecasts (Stage 08)")
    p_forecast.add_argument("--raw-dir", default=raw_default, help="Path to raw data directory")
    p_forecast.add_argument("--out-dir", default="artifacts", help="Path to artifacts output directory")
    p_forecast.add_argument("--public-dir", default=None, help="Optional path to public cricsheet cache")
    p_forecast.add_argument("--seed", type=int, default=2027, help="Random seed")
    p_forecast.set_defaults(func=cmd_forecast)

    # compare subcommand (Stage 09)
    p_compare = subparsers.add_parser("compare", help="Compare model candidates and evaluate on 2025/2026 (Stage 09)")
    p_compare.add_argument("--raw-dir", default=raw_default, help="Path to raw data directory")
    p_compare.add_argument("--out-dir", default="artifacts", help="Path to artifacts output directory")
    p_compare.add_argument("--public-dir", default=None, help="Optional path to public cricsheet cache")
    p_compare.add_argument("--seed", type=int, default=2027, help="Random seed")
    p_compare.set_defaults(func=cmd_compare)

    # robustness subcommand (Stage 10)
    p_robustness = subparsers.add_parser("robustness", help="Challenge shortlist and evaluate sensitivities (Stage 10)")
    p_robustness.add_argument("--raw-dir", default=raw_default, help="Path to raw data directory")
    p_robustness.add_argument("--out-dir", default="artifacts", help="Path to artifacts output directory")
    p_robustness.add_argument("--public-dir", default=None, help="Optional path to public cricsheet cache")
    p_robustness.add_argument("--seed", type=int, default=2027, help="Random seed")
    p_robustness.set_defaults(func=cmd_robustness)

    # rank subcommand (Stage 11)
    p_rank = subparsers.add_parser("rank", help="Produce final player rankings and RR auction shortlist (Stage 11)")
    p_rank.add_argument("--raw-dir", default=raw_default, help="Path to raw data directory")
    p_rank.add_argument("--out-dir", default="artifacts", help="Path to artifacts output directory")
    p_rank.add_argument("--public-dir", default=None, help="Optional path to public cricsheet cache")
    p_rank.add_argument("--seed", type=int, default=2027, help="Random seed")
    p_rank.set_defaults(func=cmd_rank)

    # export subcommand (Stage 12)
    p_export = subparsers.add_parser("export", help="Generate official exports and render terminal view (Stage 12)")
    p_export.add_argument("--raw-dir", default=raw_default, help="Path to raw data directory")
    p_export.add_argument("--out-dir", default="artifacts", help="Path to artifacts output directory")
    p_export.add_argument("--public-dir", default=None, help="Optional path to public cricsheet cache")
    p_export.add_argument("--seed", type=int, default=2027, help="Random seed")
    p_export.set_defaults(func=cmd_export)

    # run subcommand (Full pipeline)
    p_run = subparsers.add_parser("run", help="Run end-to-end modeling pipeline")
    p_run.add_argument("--raw-dir", default=raw_default, help="Path to raw data directory")
    p_run.add_argument("--out-dir", default="artifacts", help="Path to artifacts output directory")
    p_run.add_argument("--public-dir", default=None, help="Optional path to public cricsheet cache")
    p_run.add_argument("--seed", type=int, default=2027, help="Random seed")
    p_run.set_defaults(func=cmd_run)
    
    return parser


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    if hasattr(args, "func"):
        return args.func(args)
    else:
        print(f"Subcommand '{args.command}' is not yet implemented.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
