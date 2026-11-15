"""Stage 05 Verification Tests: Backtest, Calibration, and Frozen Model Decisions."""
import json
from pathlib import Path
import pytest

REPO_ROOT = Path("C:/SHARAN PROJECTS/rr")
FRESH_DIR = REPO_ROOT / "artifacts_hardened_v4_20261113" if (REPO_ROOT / "artifacts_hardened_v4_20261113").exists() else (REPO_ROOT / "artifacts_hardened_v3_20261113" if (REPO_ROOT / "artifacts_hardened_v3_20261113").exists() else (REPO_ROOT / "artifacts_hardened_v2_20261113" if (REPO_ROOT / "artifacts_hardened_v2_20261113").exists() else (REPO_ROOT / "artifacts_hardened_20261113")))


def test_stage05_artifacts_exist():
    """Verify all required Stage 05 artifacts exist and are non-empty."""
    required = [
        "model_validation.json",
        "robustness_report.json",
        "robustness_checks.json",
        "stage05_model_decision.json",
        "stage05_backtest_report.json",
        "checkpoint.json",
    ]
    for fname in required:
        p = FRESH_DIR / fname
        assert p.exists(), f"Missing Stage 05 artifact: {fname}"
        assert p.stat().st_size > 0, f"Artifact is empty: {fname}"


def test_frozen_model_decisions():
    """Verify model decisions and selection criteria for both batting and bowling."""
    dec_path = FRESH_DIR / "stage05_model_decision.json"
    with open(dec_path, "r", encoding="utf-8") as f:
        dec = json.load(f)

    frozen = dec["frozen_decision"]
    assert "Challenger D" in frozen["batting"]["selected_model"]
    assert "Case B" in frozen["batting"]["selection_rule"]

    assert "Ablation B-0" in frozen["bowling"]["selected_model"]
    assert "Fallback B0" in frozen["bowling"]["selection_rule"]

    # Batting metrics: Challenger D beats B0 by >= +1.0 PW impact within +0.05 loss
    bat_d = frozen["batting"]["metrics_2025_ipl"]
    bat_vs_b0 = frozen["batting"]["comparison_vs_b0"]
    assert bat_vs_b0["delta_top10_pw_impact"] >= 1.0
    assert bat_d["pinball_loss_q25"] <= bat_vs_b0["b0_pinball_loss"] + 0.05
    assert bat_d["assessable_picks"] >= 7

    # Bowling metrics: B0 achieves lowest loss and highest realized impact
    bowl_b0 = frozen["bowling"]["metrics_2025_ipl"]
    assert bowl_b0["top10_player_weighted_impact"] > 4.0
    assert bowl_b0["pinball_loss_q25"] < 3.41


def test_robustness_and_bootstrap():
    """Verify robustness sweeps and 100-replicate cluster bootstrap."""
    rob_path = FRESH_DIR / "robustness_report.json"
    with open(rob_path, "r", encoding="utf-8") as f:
        rob = json.load(f)

    assert "cutoff_15_percent" in rob["pressure_percentile_sensitivity"]
    assert "cutoff_25_percent" in rob["pressure_percentile_sensitivity"]

    assert "non_emerging_top10_overlap" in rob["competition_tier_sensitivity"]
    assert "ipl_only_top10_overlap" in rob["competition_tier_sensitivity"]

    assert "standard_floor_48b_6m" in rob["workload_evidence_floor_sensitivity"]
    assert "narrow_floor_36b_4m" in rob["workload_evidence_floor_sensitivity"]
    assert "strict_floor_72b_8m" in rob["workload_evidence_floor_sensitivity"]

    boot = rob["bootstrap_stability_100_replicates"]
    assert len(boot["batting_top15"]) == 15
    assert len(boot["bowling_top15"]) == 15


def test_stage05_checkpoint():
    """Verify Stage 05 checkpoint status or later progression."""
    cp_path = FRESH_DIR / "checkpoint.json"
    with open(cp_path, "r", encoding="utf-8") as f:
        cp = json.load(f)

    assert cp["stage"] in ["05_backtest_and_calibrate", "06_produce_rr_top_tens", "07_reproduce_and_handoff", "BACKEND_REVIEW"]
    assert cp["stage_status"] == "COMPLETED"
    assert cp.get("stage05_verified", True) is True
