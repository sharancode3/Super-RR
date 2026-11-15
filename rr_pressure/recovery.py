"""Recovery Gate: Revalidate existing run and isolate repair checkpoint."""

import json
from pathlib import Path
from typing import Any, Dict, Tuple

from rr_pressure.config import PipelineConfig
from rr_pressure.manifest import compute_sha256, generate_input_manifest
from rr_pressure.progress import record_stage, get_default_progress_path


KNOWN_AUDIT_DEFECTS = [
    {
        "defect_id": "STAGE_01_AS_OF_ROLES",
        "description": "Historical role and scoring can see later matches; player dimension derived from full 2022-2026 pack.",
        "owning_stages": ["01", "04"],
        "failing_check": "test_as_of_role_leakage",
        "status": "OPEN_PENDING_REPAIR",
    },
    {
        "defect_id": "STAGE_02_PROXY_SCORE_SEPARATION",
        "description": "Ledger computes 1 run per wide/no-ball and labels chronology as exact; official scores diverge on extras/penalties.",
        "owning_stages": ["02", "03"],
        "failing_check": "test_exact_proxy_separation",
        "status": "OPEN_PENDING_REPAIR",
    },
    {
        "defect_id": "STAGE_05_FLOAT_BRIER_BASELINE",
        "description": "np.full_like inherits integer target dtype and truncates constant win probability to 0.",
        "owning_stages": ["05"],
        "failing_check": "test_float_brier_baseline",
        "status": "OPEN_PENDING_REPAIR",
    },
    {
        "defect_id": "STAGE_06_DYNAMIC_PRESSURE_TRANSITIONS",
        "description": "Pressure pre-ball leverage used hard-coded next-ball outcome vectors rather than learned empirical frequencies.",
        "owning_stages": ["06"],
        "failing_check": "test_dynamic_pressure_transition_frequencies",
        "status": "OPEN_PENDING_REPAIR",
    },
    {
        "defect_id": "STAGE_07_FITTED_WICKET_VALUE_AND_LEGAL_DENOMINATOR",
        "description": "Impact used fixed 7.0 wicket price instead of fitted marginal value; legal ball denominator counted all event rows.",
        "owning_stages": ["07"],
        "failing_check": "test_impact_fitted_wicket_value_and_legal_ball_denominator",
        "status": "OPEN_PENDING_REPAIR",
    },
    {
        "defect_id": "STAGE_08_ROLE_PRIORS_EXCLUDE_ZERO_EXPOSURE",
        "description": "Role priors included missing-exposure zeroes; empirical Bayes shrinkage was heuristic.",
        "owning_stages": ["08"],
        "failing_check": "test_role_priors_exclude_zero_exposure",
        "status": "OPEN_PENDING_REPAIR",
    },
    {
        "defect_id": "STAGE_09_DYNAMIC_MODEL_SELECTION_AND_COMMON_COHORT",
        "description": "Candidate B was hardcoded string; ablation had lower pinball loss; common cohort was mismatched in IPL transfer check.",
        "owning_stages": ["09"],
        "failing_check": "test_model_selection_dynamic_and_common_cohort_transfer",
        "status": "OPEN_PENDING_REPAIR",
    },
    {
        "defect_id": "STAGE_10_BOOTSTRAP_PRESERVES_MATCH_MULTIPLICITY",
        "description": "Bootstrap used .isin() filtering which discarded duplicate resampled match draws.",
        "owning_stages": ["10"],
        "failing_check": "test_bootstrap_preserves_match_multiplicity",
        "status": "OPEN_PENDING_REPAIR",
    },
    {
        "defect_id": "STAGE_11_REFIT_DISPATCHES_SELECTED_MODEL",
        "description": "Final refit always called Candidate B; dropdown fields were populated with proxy names instead of remaining blank.",
        "owning_stages": ["11"],
        "failing_check": "test_refit_dispatches_selected_model_and_dropdown_labels_blank",
        "status": "OPEN_PENDING_REPAIR",
    },
    {
        "defect_id": "STAGE_12_REPLAY_BALLS_RECONCILIATION_AND_DYNAMIC_SCOUTING",
        "description": "Klaasen replay stated 58 balls remaining instead of 65; scouting profiles were hardcoded dictionaries.",
        "owning_stages": ["12", "13"],
        "failing_check": "test_replays_match_ledger_and_profiles_dynamic",
        "status": "OPEN_PENDING_REPAIR",
    },
]


def run_recovery_gate(config: PipelineConfig) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """Execute recovery gate: verify raw inputs, isolate artifacts_revalidated, and initialize ledger."""
    out = config.out_dir
    out.mkdir(parents=True, exist_ok=True)
    
    # 1. Generate and verify raw input manifest
    manifest_data = generate_input_manifest(config)
    manifest_path = out / "input_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
        
    # Check against legacy manifest if present
    legacy_manifest_path = Path("artifacts/input_manifest.json")
    if legacy_manifest_path.exists():
        with open(legacy_manifest_path, "r", encoding="utf-8") as f:
            legacy_manifest = json.load(f)
        for fname, meta in legacy_manifest["files"].items():
            assert manifest_data["files"][fname]["sha256"] == meta["sha256"], f"Raw hash mismatch on {fname}"
            assert manifest_data["files"][fname]["size_bytes"] == meta["size_bytes"], f"Size mismatch on {fname}"
            
    # 2. Write recovery audit ledger
    recovery_ledger = {
        "gate": "recovery_gate",
        "legacy_snapshot_preserved": "artifacts",
        "revalidated_output_directory": str(out),
        "raw_files_verified": len(manifest_data["files"]),
        "known_audit_defects": KNOWN_AUDIT_DEFECTS,
        "recovery_status": "PASS",
        "next_prompt": "round1_prompts/00_project_contract.md",
    }
    ledger_path = out / "recovery_audit_ledger.json"
    with open(ledger_path, "w", encoding="utf-8") as f:
        json.dump(recovery_ledger, f, indent=2)
        
    output_files = {
        "input_manifest.json": manifest_path,
        "recovery_audit_ledger.json": ledger_path,
    }
    output_fingerprints = {fname: compute_sha256(fpath) for fname, fpath in output_files.items()}
    return recovery_ledger, output_fingerprints
