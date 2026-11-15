"""Regression and validation tests for Stage H03: Candidate Selection, Refit, and Reporting Parity."""

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(".").resolve()))

from rr_pressure.config import PipelineConfig
from rr_pressure.forecast import fit_player_forecast, Z_25
from rr_pressure.compare import compute_pinball_loss, run_stage09_comparison
from rr_pressure.challengers import ChallengerD_WorkloadDistributional
from rr_pressure.rankings import run_stage11_rankings

HARDENED_DIR = Path("artifacts_hardened")
RAW_DIR = Path("6af3166e7b922_data_pack")


def test_forecast_exports_both_b0_and_b1():
    """Verify fit_player_forecast generates coherent b0 and b1 predictions with matching uncertainty."""
    bat_match_df = pd.read_csv(HARDENED_DIR / "match_player_batting_impact.csv")
    p_dim = pd.read_csv(HARDENED_DIR / "player_dimension_train.csv")
    
    stats, _ = fit_player_forecast(bat_match_df, p_dim, "batting", seed=2027, folds=["TRAIN_2022_2024"])
    
    assert "b0_mean" in stats.columns
    assert "b0_q25" in stats.columns
    assert "b1_mean" in stats.columns
    assert "b1_q25" in stats.columns
    assert "predictive_sigma" in stats.columns
    
    # Exact relationship
    assert np.allclose(stats["b0_q25"], stats["b0_mean"] - Z_25 * stats["predictive_sigma"])
    assert np.allclose(stats["b1_q25"], stats["b1_mean"] - Z_25 * stats["predictive_sigma"])
    # B0 mean is usual level
    assert np.allclose(stats["b0_mean"], stats["usual_level"])
    # B1 mean is usual level + lift
    assert np.allclose(stats["b1_mean"], stats["usual_level"] + stats["pressure_lift"])


def test_candidate_shortlist_parity_and_common_cohort(isolated_hardened_inputs):
    """Verify that compare stage scores every candidate on common cohort and passes its OWN shortlist."""
    out_dir = isolated_hardened_inputs(
        "delivery_impact_ledger.csv", "player_dimension.csv", "player_dimension_train.csv",
        "match_player_batting_impact.csv", "match_player_bowling_impact.csv",
    )
    config = PipelineConfig(raw_dir=RAW_DIR, out_dir=out_dir, seed=2027)
    comp_summary, _ = run_stage09_comparison(config)
    
    val_res = comp_summary["validation_2025_results"]
    bat_res = val_res["batting"]
    bowl_res = val_res["bowling"]
    
    # All candidates must have the exact same opportunity count
    opp_count_bat = bat_res["candidate_B_statistical"]["opportunity_count"]
    assert bat_res["candidate_A_baseline"]["opportunity_count"] == opp_count_bat
    assert bat_res["candidate_C_boosted"]["opportunity_count"] == opp_count_bat
    assert bat_res["ablation_B0_no_pressure"]["opportunity_count"] == opp_count_bat
    
    opp_count_bowl = bowl_res["candidate_B_statistical"]["opportunity_count"]
    assert bowl_res["candidate_A_baseline"]["opportunity_count"] == opp_count_bowl
    assert bowl_res["candidate_C_boosted"]["opportunity_count"] == opp_count_bowl
    assert bowl_res["ablation_B0_no_pressure"]["opportunity_count"] == opp_count_bowl
    
    # B0 must have its own top10 performance recorded
    assert "top10_performance" in bat_res["ablation_B0_no_pressure"]
    assert "top10_performance" in bowl_res["ablation_B0_no_pressure"]

    retrospective = comp_summary["test_holdout_2026_evaluation"]
    for role, balls, impact in (
        ("batting", "hp_balls_faced", "hp_bat_impact_12b"),
        ("bowling", "hp_balls_bowled", "hp_bowl_impact_12b"),
    ):
        matches = pd.read_csv(out_dir / f"match_player_{role}_impact.csv")
        assess = matches[(matches["fold"] == "TEST_HOLDOUT_2026") & (matches[balls] >= 6)]
        assert retrospective[role]["opportunity_count"] == len(assess)
        if retrospective["chosen_model"].startswith("Batting: Challenger D") and role == "batting":
            historical = matches[matches["fold"].isin(["TRAIN_2022_2024", "VAL_2025"])]
            dimension = pd.read_csv(out_dir / "player_dimension_train.csv")
            challenger = ChallengerD_WorkloadDistributional().fit(historical, dimension, role)
            ids = assess["player_id"].to_numpy()
            q25 = challenger.predict_quantile(ids, np.full(len(ids), 12.0))
            assert retrospective[role]["pinball_loss_q25"] == pytest.approx(
                compute_pinball_loss(assess[impact].to_numpy(), q25)
            )
            assert retrospective[role]["mean_forecast_error"] == pytest.approx(
                (assess[impact].to_numpy() - challenger.predict_mean(ids)).mean()
            )


def test_rankings_export_parity(isolated_hardened_inputs):
    """Verify that shortlisted players have mean, Q25, and intervals from the exact selected candidate."""
    out_dir = isolated_hardened_inputs(
        "player_dimension.csv", "model_comparison.json",
        "match_player_batting_impact.csv", "match_player_bowling_impact.csv",
    )
    config = PipelineConfig(raw_dir=RAW_DIR, out_dir=out_dir, seed=2027)
    run_stage11_rankings(config)
    
    shortlist = pd.read_csv(out_dir / "rr_shortlist.csv")
    
    with open(out_dir / "model_comparison.json", "r", encoding="utf-8") as f:
        comp = json.load(f)
    decision = comp.get("pre_holdout_decision", {})
    chosen_bat = decision.get("chosen_model_batting", decision.get("chosen_model", ""))
    chosen_bowl = decision.get("chosen_model_bowling", decision.get("chosen_model", ""))
    
    # For Ablation B-0, predicted_hp_impact_12b MUST equal usual_impact_12b (not usual + lift)
    if "Ablation" in chosen_bat:
        bat_s = shortlist[shortlist["tactical_squad_role"].str.contains("Batter|Top|Order", case=False)]
        assert np.allclose(bat_s["predicted_hp_impact_12b"], bat_s["usual_impact_12b"], atol=1e-3)
    if "Ablation" in chosen_bowl:
        bowl_s = shortlist[shortlist["tactical_squad_role"].str.contains("Bowler", case=False)]
        assert np.allclose(bowl_s["predicted_hp_impact_12b"], bowl_s["usual_impact_12b"], atol=1e-3)
    if "Challenger D" in chosen_bat:
        batter = shortlist[shortlist["role_pool"] == "Batting"].iloc[0]
        matches = pd.read_csv(out_dir / "match_player_batting_impact.csv")
        fitted = matches[(matches["player_id"] == batter["player_id"]) & (matches["hp_balls_faced"] >= 6)]
        assert batter["model_fit_matches"] == len(fitted)
        assert batter["model_fit_hp_balls"] == fitted["hp_balls_faced"].sum()
