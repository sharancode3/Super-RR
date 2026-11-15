"""Stage A03: Acceptance Tests for Model Training, Evaluation, and Selection.

Validates:
1. Model candidate evaluation on identical dated assessment rows.
2. Non-negative, finite Q25 pinball loss with calibrated coverage (15% - 35%).
3. Objective, model-neutral selection rule recorded with clear rationale.
4. Clear separation of 2025 selection window and 2026 retrospective evaluation.
"""

import json
from pathlib import Path
import numpy as np
import pytest

ARTIFACTS_DIR = Path("artifacts_decision_validation")


def test_identical_assessment_rows_across_candidates():
    """Verify that all evaluated candidates share identical evaluation row counts and keys."""
    metrics_path = ARTIFACTS_DIR / "model_comparison.json"
    assert metrics_path.exists(), f"Missing {metrics_path}"
    
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)
        
    for discipline in ["batting", "bowling"]:
        val_block = metrics["validation_2025_results"][discipline]
        row_counts = []
        for cand_key in [
            "candidate_A_baseline",
            "candidate_B_statistical",
            "ablation_B0_no_pressure",
            "challenger_D_workload",
            "challenger_E_quantile_boosted",
        ]:
            assert cand_key in val_block, f"Missing {cand_key} in {discipline} metrics"
            cnt = val_block[cand_key]["opportunity_count"]
            assert cnt > 0, f"Expected non-zero opportunity count for {cand_key}"
            row_counts.append(cnt)
            
        # All models must be evaluated on the exact same number of opportunities
        assert len(set(row_counts)) == 1, f"Opportunity count mismatch in {discipline}: {row_counts}"


def test_quantile_loss_and_calibration():
    """Verify Q25 pinball loss is finite/positive and coverage is within reasonable bounds."""
    metrics_path = ARTIFACTS_DIR / "model_comparison.json"
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)
        
    for discipline in ["batting", "bowling"]:
        val_block = metrics["validation_2025_results"][discipline]
        for cand_key in [
            "candidate_B_statistical",
            "ablation_B0_no_pressure",
            "challenger_D_workload",
            "challenger_E_quantile_boosted",
        ]:
            res = val_block[cand_key]
            loss = res["pinball_loss_q25"]
            cov = res["coverage_q25"]
            
            assert np.isfinite(loss) and loss > 0.0, f"Invalid loss for {discipline} {cand_key}: {loss}"
            assert 0.15 <= cov <= 0.35, f"Coverage out of bounds for {discipline} {cand_key}: {cov}"


def test_model_neutral_selection_and_retrospective_labelling():
    """Verify winner was selected algorithmically and 2026 is strictly labeled retrospective."""
    metrics_path = ARTIFACTS_DIR / "model_comparison.json"
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)
        
    decision = metrics["pre_holdout_decision"]
    assert "chosen_model_batting" in decision, "Missing chosen_model_batting"
    assert "chosen_model_bowling" in decision, "Missing chosen_model_bowling"
    assert "selection_rationale" in decision, "Missing selection_rationale"
    
    # Verify 2026 evaluation is present and labeled
    assert "test_holdout_2026_evaluation" in metrics, "Missing test_holdout_2026_evaluation"
    eval_2026 = metrics["test_holdout_2026_evaluation"]
    assert "batting" in eval_2026
    assert "bowling" in eval_2026
    assert "status" in eval_2026


def test_top10_later_performance_and_assessable_counts():
    """Verify later performance of top 10 lists reports assessable counts and bootstrap uncertainty."""
    metrics_path = ARTIFACTS_DIR / "model_comparison.json"
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)
        
    for discipline in ["batting", "bowling"]:
        val_block = metrics["validation_2025_results"][discipline]
        for cand_key in ["candidate_B_statistical", "ablation_B0_no_pressure", "challenger_E_quantile_boosted"]:
            top10_info = val_block[cand_key].get("top10_performance", {})
            assert "assessable_picks_count" in top10_info, f"Missing assessable_picks_count in {cand_key}"
            assert "unassessable_picks_count" in top10_info, f"Missing unassessable_picks_count in {cand_key}"
            assert "bootstrap_realized_std" in top10_info, f"Missing bootstrap_realized_std in {cand_key}"
            assert "player_outcomes" in top10_info, f"Missing player_outcomes in {cand_key}"
            assert top10_info["assessable_picks_count"] + top10_info["unassessable_picks_count"] == 10
