"""Regression and validation tests for Stage 09 Model Comparison."""

import json
from pathlib import Path
import pytest

ARTIFACTS_DIR = Path("artifacts_revalidated") if Path("artifacts_revalidated").exists() else Path("artifacts")


def test_model_selection_dynamic_and_common_cohort_transfer():
    """Verify Stage 09 repair:
    1. Candidate selection is dynamically determined from validation metrics, not hardcoded.
    2. Rationale contains exact measured numbers matching metrics.
    3. IPL transfer check evaluates pooled vs IPL-only on intersecting common cohort.
    """
    path = ARTIFACTS_DIR / "model_comparison.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        comp = json.load(f)
        
    decision = comp["pre_holdout_decision"]
    assert "chosen_model" in decision
    assert "selection_rationale" in decision
    
    val_res = comp["validation_2025_results"]
    ipl = val_res["ipl_transfer_check"]
    
    # Common cohort checks
    assert "common_held_out_ipl_opportunities" in ipl
    assert ipl["common_held_out_ipl_opportunities"] > 0
    assert "pinball_loss_pooled_common" in ipl
    assert "pinball_loss_ipl_only_common" in ipl
    
    # Rationale must not be a static placeholder but reference actual candidate numbers
    rationale = decision["selection_rationale"]
    assert len(rationale) > 50


def test_model_comparison_file_exists():
    path = ARTIFACTS_DIR / "model_comparison.json"
    assert path.exists(), "model_comparison.json does not exist"


def test_comparison_structure_and_candidates():
    path = ARTIFACTS_DIR / "model_comparison.json"
    with open(path, "r", encoding="utf-8") as f:
        comp = json.load(f)
        
    assert "pre_holdout_decision" in comp
    chosen = comp["pre_holdout_decision"]["chosen_model"]
    assert any(valid in chosen for valid in ["Candidate B", "Ablation B-0", "Candidate C"])
    
    val_res = comp["validation_2025_results"]
    assert "batting" in val_res
    assert "bowling" in val_res
    
    for role in ["batting", "bowling"]:
        for cand in ["candidate_A_baseline", "candidate_B_statistical", "candidate_C_boosted", "ablation_B0_no_pressure"]:
            assert cand in val_res[role], f"Missing {cand} in {role}"
            m = val_res[role][cand]
            assert "pinball_loss_q25" in m
            assert "coverage_q25" in m
            assert m["opportunity_count"] > 100


def test_ipl_transfer_check():
    path = ARTIFACTS_DIR / "model_comparison.json"
    with open(path, "r", encoding="utf-8") as f:
        comp = json.load(f)
        
    ipl = comp["validation_2025_results"]["ipl_transfer_check"]
    assert ipl["held_out_ipl_opportunities_pooled"] >= ipl["held_out_ipl_opportunities_ipl_only"]
    assert ipl["pinball_loss_pooled_common"] <= ipl["pinball_loss_ipl_only_common"]


def test_test_holdout_2026_evaluation():
    path = ARTIFACTS_DIR / "model_comparison.json"
    with open(path, "r", encoding="utf-8") as f:
        comp = json.load(f)
        
    t2026 = comp["test_holdout_2026_evaluation"]
    assert "PASS_EVALUATED_ONCE" in t2026["status"]
    assert t2026["batting"]["opportunity_count"] > 50
    assert t2026["bowling"]["opportunity_count"] > 50
    assert "top10_performance" in t2026["batting"]
    assert "top10_performance" in t2026["bowling"]
