"""Stage I05 Verification Tests: IPL Transfer, Shortlist Sensitivity, and Rank Stability."""

import json
from pathlib import Path
import pytest
import pandas as pd

REVIEW_DIR = Path("artifacts_release_review")


def test_ipl_transfer_matched_pairs():
    """Verify that IPL transfer is measured on exact common held-out IPL opportunities."""
    comp_file = REVIEW_DIR / "model_comparison.json"
    assert comp_file.exists()
    
    with open(comp_file, "r", encoding="utf-8") as f:
        comp_data = json.load(f)
        
    ipl_check = comp_data["validation_2025_results"]["ipl_transfer_check"]
    assert "common_held_out_ipl_opportunities" in ipl_check
    assert "common_held_out_ipl_opportunities_bowling" in ipl_check
    assert ipl_check["common_held_out_ipl_opportunities"] > 100
    assert ipl_check["common_held_out_ipl_opportunities_bowling"] > 100
    
    # Verify pinball loss on common opportunities is reported
    assert "pinball_loss_pooled_common" in ipl_check
    assert "pinball_loss_ipl_only_common" in ipl_check


def test_stage10_robustness_report_completeness():
    """Verify Stage 10 robustness report structure, bootstrap, and sensitivities in artifacts_release_review."""
    rob_file = REVIEW_DIR / "robustness_report.json"
    assert rob_file.exists()
    
    with open(rob_file, "r", encoding="utf-8") as f:
        report = json.load(f)
    
    assert "pressure_percentile_sensitivity" in report
    assert "competition_tier_sensitivity" in report
    assert "workload_evidence_floor_sensitivity" in report
    assert "standout_match_sensitivity" in report
    assert "bootstrap_stability_100_replicates" in report
    assert "borderline_cohort_review_ranks_8_to_15" in report
    
    # Check 15% and 25% sensitivities exist
    assert "cutoff_15_percent" in report["pressure_percentile_sensitivity"]
    assert "cutoff_25_percent" in report["pressure_percentile_sensitivity"]
    
    # Check standout match results for both roles
    standout = report["standout_match_sensitivity"]
    assert len(standout["batting_top15"]) == 15
    assert len(standout["bowling_top15"]) == 15
    
    # Check bootstrap results for both roles
    boot = report["bootstrap_stability_100_replicates"]
    assert len(boot["batting_top15"]) == 15
    assert len(boot["bowling_top15"]) == 15
    
    # Check borderline review
    borderline = report["borderline_cohort_review_ranks_8_to_15"]
    assert len(borderline["batting"]) == 8  # ranks 8 to 15
    assert len(borderline["bowling"]) == 8
