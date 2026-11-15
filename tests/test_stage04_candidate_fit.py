"""Stage 04 Verification Tests: Candidate Fit, Controls, Short-Stint Diagnostics, and Bowling Lift Audit."""
import json
from pathlib import Path
import pytest

REPO_ROOT = Path("C:/SHARAN PROJECTS/rr")
FRESH_DIR = REPO_ROOT / "artifacts_hardened_v4_20261113" if (REPO_ROOT / "artifacts_hardened_v4_20261113").exists() else (REPO_ROOT / "artifacts_hardened_v3_20261113" if (REPO_ROOT / "artifacts_hardened_v3_20261113").exists() else (REPO_ROOT / "artifacts_hardened_v2_20261113" if (REPO_ROOT / "artifacts_hardened_v2_20261113").exists() else (REPO_ROOT / "artifacts_hardened_20261113")))


def test_stage04_artifacts_exist():
    """Verify all required Stage 04 artifacts exist in the fresh run directory."""
    required = [
        "model_comparison.json",
        "stage04_replay_results.json",
        "stage04_candidate_inventory.json",
        "batting_short_stint_diagnostic.json",
        "bowling_pressure_lift_value_audit.json",
        "checkpoint.json",
    ]
    for fname in required:
        p = FRESH_DIR / fname
        assert p.exists(), f"Missing required Stage 04 artifact: {fname}"
        assert p.stat().st_size > 0, f"Artifact is empty: {fname}"


def test_stage04_candidate_inventory():
    """Verify candidate inventory covers controls, primary challengers, hazard, and quantile contenders."""
    inv_path = FRESH_DIR / "stage04_candidate_inventory.json"
    with open(inv_path, "r", encoding="utf-8") as f:
        inv = json.load(f)

    assert inv["stage"] == "04_fit_model_challengers"
    assert inv["candidate_count"] >= 16

    disciplines = {c["discipline"] for c in inv["candidates"]}
    assert disciplines == {"batting", "bowling"}

    bat_keys = {c["candidate_key"] for c in inv["candidates"] if c["discipline"] == "batting"}
    bowl_keys = {c["candidate_key"] for c in inv["candidates"] if c["discipline"] == "bowling"}

    # Refit controls
    assert "ablation_B0_no_pressure" in bat_keys
    assert "challenger_D_workload" in bat_keys
    assert "ablation_B0_no_pressure" in bowl_keys
    assert "challenger_D_workload" in bowl_keys

    # Challengers
    assert "challenger_RPP_role_phase_joint" in bat_keys
    assert "challenger_RPP_role_phase_joint" in bowl_keys
    assert "challenger_E_quantile_boosted" in bat_keys
    assert "challenger_E_quantile_boosted" in bowl_keys

    # Batting-specific two-part hazard
    assert "challenger_DHP_delivery_hazard" in bat_keys

    # Target unit
    for c in inv["candidates"]:
        assert c["target_unit"] == "adjusted runs per 12 legal balls"


def test_batting_short_stint_diagnostic():
    """Verify batting short-stint (1-5 balls) distribution and hazard diagnostics."""
    diag_path = FRESH_DIR / "batting_short_stint_diagnostic.json"
    with open(diag_path, "r", encoding="utf-8") as f:
        diag = json.load(f)

    breakdown = diag["short_stint_cause_breakdown"]
    overall = breakdown["overall"]
    assert overall["total_hp_stints"] > 4000
    assert overall["short_1_to_5b_stints"] > 2500
    # Over 50% are short stints
    assert overall["short_1_to_5b_stints"] / overall["total_hp_stints"] > 0.50

    # Dismissals have large negative impact due to lost legal ball opportunities
    d_impact = overall["by_cause"]["DISMISSED"]["mean_hp_impact_12b"]
    assert d_impact < -30.0

    # Check 2025 IPL slice
    ipl_2025 = breakdown["ipl_2025"]
    assert ipl_2025["total_hp_stints"] >= 400
    assert ipl_2025["short_1_to_5b_stints"] >= 200

    # Check model performance across slices
    perf = diag["model_performance_by_stint_slice"]
    assert "ge6_balls_standard_slice" in perf
    assert "short_1_to_5b_slice" in perf
    assert "all_positive_workload_gt0b_slice" in perf


def test_bowling_pressure_lift_value_audit():
    """Verify bowling audit comparing B0 (pressure-neutral usual level) vs individual lift models."""
    audit_path = FRESH_DIR / "bowling_pressure_lift_value_audit.json"
    with open(audit_path, "r", encoding="utf-8") as f:
        audit = json.load(f)

    ctrls = audit["controls_vs_challengers"]
    b0 = ctrls["Ablation_B0_no_pressure"]
    b1 = ctrls["Candidate_B1_statistical_lift"]

    # B0 pinball loss is lower or competitive vs B1
    assert b0["pinball_loss_q25"] <= b1["pinball_loss_q25"]
    # B0 top-10 realized player-weighted impact is superior in 2025 replay
    assert b0["top10_player_weighted_impact_2025"] > b1["top10_player_weighted_impact_2025"]
    assert b0["top10_player_weighted_impact_2025"] > 4.0


def test_stage04_checkpoint_status():
    """Verify checkpoint records Stage 04 completion or later progression."""
    cp_path = FRESH_DIR / "checkpoint.json"
    with open(cp_path, "r", encoding="utf-8") as f:
        cp = json.load(f)

    assert cp["stage"] in ["04_fit_model_challengers", "05_backtest_and_calibrate", "06_produce_rr_top_tens", "07_reproduce_and_handoff", "BACKEND_REVIEW"]
    assert cp["stage_status"] == "COMPLETED"
    assert cp.get("stage04_verified", True) is True
