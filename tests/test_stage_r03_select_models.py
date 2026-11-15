"""Test Stage R03: Model selection by role, calibration, and backtest integrity."""

import json
from pathlib import Path
import pytest


OUT_DIR = Path("artifacts_rank_validation")


def test_model_selection_decisions_by_role():
    """Verify independent selection by role based on chronological validation."""
    comp_path = OUT_DIR / "model_comparison.json"
    assert comp_path.exists(), "model_comparison.json must exist"
    
    with open(comp_path, "r", encoding="utf-8") as f:
        comp = json.load(f)
        
    dec = comp["pre_holdout_decision"]
    assert "batting" in dec["chosen_model_batting"].lower() or "challenger e" in dec["chosen_model_batting"].lower()
    assert "ablation b-0" in dec["chosen_model_bowling"].lower() or "b0" in dec["chosen_model_bowling"].lower()
    
    # Check coverage calibration on 2025 validation
    val_bat = comp["validation_2025_results"]["batting"]["challenger_E_quantile_boosted"]
    val_bowl = comp["validation_2025_results"]["bowling"]["ablation_B0_no_pressure"]
    
    assert 0.15 <= val_bat["coverage_q25"] <= 0.35, f"Batting coverage {val_bat['coverage_q25']} out of bounds"
    assert 0.15 <= val_bowl["coverage_q25"] <= 0.35, f"Bowling coverage {val_bowl['coverage_q25']} out of bounds"
    
    # Verify Challenger E had lower pinball loss than B0 in batting
    b0_bat_loss = comp["validation_2025_results"]["batting"]["ablation_B0_no_pressure"]["pinball_loss_q25"]
    assert val_bat["pinball_loss_q25"] < b0_bat_loss
    
    # Verify B0 had lower pinball loss than B1 and A in bowling
    b1_bowl_loss = comp["validation_2025_results"]["bowling"]["candidate_B_statistical"]["pinball_loss_q25"]
    a_bowl_loss = comp["validation_2025_results"]["bowling"]["candidate_A_baseline"]["pinball_loss_q25"]
    assert val_bowl["pinball_loss_q25"] < b1_bowl_loss
    assert val_bowl["pinball_loss_q25"] < a_bowl_loss
