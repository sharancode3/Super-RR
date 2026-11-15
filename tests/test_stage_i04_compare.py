"""Validation tests for Stage I04: Train, Compare, and Role-Based Candidate Selection."""

import json
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(".").resolve()))

REVIEW_DIR = Path("artifacts_release_review")


@pytest.fixture(scope="module")
def comp_data():
    comp_path = REVIEW_DIR / "model_comparison.json"
    if not comp_path.exists():
        pytest.skip("model_comparison.json not yet generated in artifacts_release_review")
    with open(comp_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_independent_role_decision_presence(comp_data):
    """Verify that both batting and bowling have explicit, traceable chosen models."""
    decision = comp_data.get("pre_holdout_decision", {})
    assert "chosen_model" in decision
    assert "chosen_model_batting" in decision
    assert "chosen_model_bowling" in decision
    
    # Batting chose Challenger D (workload-aware)
    assert "Challenger D" in decision["chosen_model_batting"]
    # Bowling chose Ablation B-0 (parsimonious without noisy player pressure lift)
    assert "Ablation B-0" in decision["chosen_model_bowling"]


def test_validation_metrics_soundness(comp_data):
    """Verify pinball loss and coverage meet mathematical invariants on identical opportunities."""
    val = comp_data["validation_2025_results"]
    
    for discipline, exp_opps in [("batting", 655), ("bowling", 783)]:
        results = val[discipline]
        for name, metrics in results.items():
            assert metrics["opportunity_count"] == exp_opps, f"{discipline} {name} opp count mismatch!"
            assert 2.0 <= metrics["pinball_loss_q25"] <= 5.0, f"{discipline} {name} abnormal pinball loss!"
            assert 0.15 <= metrics["coverage_q25"] <= 0.35, f"{discipline} {name} coverage out of range!"


def test_improvement_threshold_justification(comp_data):
    """Verify chosen models meet the >= 0.02 pinball loss improvement threshold over Baseline."""
    val = comp_data["validation_2025_results"]
    
    # Batting
    base_bat = val["batting"]["candidate_A_baseline"]["pinball_loss_q25"]
    chal_d_bat = val["batting"]["challenger_D_workload"]["pinball_loss_q25"]
    assert base_bat - chal_d_bat >= 0.02, f"Batting improvement {base_bat - chal_d_bat:.4f} < 0.02!"
    
    # Bowling
    base_bowl = val["bowling"]["candidate_A_baseline"]["pinball_loss_q25"]
    b0_bowl = val["bowling"]["ablation_B0_no_pressure"]["pinball_loss_q25"]
    assert base_bowl - b0_bowl >= 0.02, f"Bowling improvement {base_bowl - b0_bowl:.4f} < 0.02!"
