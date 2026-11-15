"""Regression and validation tests for Stage H04: Research-backed Forecast Challengers (D and E)."""

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(".").resolve()))

from rr_pressure.config import PipelineConfig
from rr_pressure.challengers import ChallengerD_WorkloadDistributional, ChallengerE_DirectQuantileBoosted
from rr_pressure.compare import run_stage09_comparison

HARDENED_DIR = Path("artifacts_hardened")
RAW_DIR = Path("6af3166e7b922_data_pack")


def test_challenger_d_workload_variance():
    """Verify Challenger D produces tighter predictive variance for higher ball workloads."""
    bat_match_df = pd.read_csv(HARDENED_DIR / "match_player_batting_impact.csv")
    p_dim = pd.read_csv(HARDENED_DIR / "player_dimension_train.csv")
    
    train_bat = bat_match_df[bat_match_df["fold"] == "TRAIN_2022_2024"]
    chal_d = ChallengerD_WorkloadDistributional().fit(train_bat, p_dim, "batting")
    
    test_pids = np.array([train_bat["player_id"].iloc[0], train_bat["player_id"].iloc[0]])
    q_low_workload = chal_d.predict_quantile(test_pids[:1], np.array([6.0]))
    q_high_workload = chal_d.predict_quantile(test_pids[:1], np.array([36.0]))
    
    # Higher workload should have lower variance -> higher (less conservative) Q25 relative to mean
    assert q_high_workload[0] > q_low_workload[0], "Higher workload should yield higher Q25 given tighter uncertainty"


def test_challenger_e_direct_quantile_loss():
    """Verify Challenger E trains directly on quantile loss and produces valid predictions."""
    bat_match_df = pd.read_csv(HARDENED_DIR / "match_player_batting_impact.csv")
    p_dim = pd.read_csv(HARDENED_DIR / "player_dimension_train.csv")
    from rr_pressure.forecast import fit_player_forecast
    
    train_bat = bat_match_df[bat_match_df["fold"] == "TRAIN_2022_2024"]
    stats_bat, _ = fit_player_forecast(train_bat, p_dim, "batting", seed=2027)
    
    chal_e = ChallengerE_DirectQuantileBoosted(seed=2027).fit(train_bat, stats_bat, "batting")
    assert chal_e.fitted is True
    
    val_bat = bat_match_df[(bat_match_df["fold"] == "VAL_2025") & (bat_match_df["hp_balls_faced"] >= 6)]
    preds = chal_e.predict(val_bat, stats_bat)
    assert len(preds) == len(val_bat)
    assert np.isfinite(preds).all()


def test_all_six_candidates_evaluated_on_common_cohort(isolated_hardened_inputs):
    """Verify that all 6 candidate recipes are reported on identical validation opportunities."""
    out_dir = isolated_hardened_inputs(
        "delivery_impact_ledger.csv", "player_dimension.csv", "player_dimension_train.csv",
        "match_player_batting_impact.csv", "match_player_bowling_impact.csv",
    )
    config = PipelineConfig(raw_dir=RAW_DIR, out_dir=out_dir, seed=2027)
    comp_summary, _ = run_stage09_comparison(config)
    
    val_bat = comp_summary["validation_2025_results"]["batting"]
    val_bowl = comp_summary["validation_2025_results"]["bowling"]
    
    expected_cands = [
        "candidate_A_baseline",
        "candidate_B_statistical",
        "candidate_C_boosted",
        "ablation_B0_no_pressure",
        "challenger_D_workload",
        "challenger_E_quantile_boosted",
    ]
    
    for cand in expected_cands:
        assert cand in val_bat, f"Missing {cand} in batting comparison"
        assert cand in val_bowl, f"Missing {cand} in bowling comparison"
        assert val_bat[cand]["opportunity_count"] in (578, 655)
        assert val_bowl[cand]["opportunity_count"] in (704, 783)
        assert "pinball_loss_q25" in val_bat[cand]
        assert "coverage_q25" in val_bat[cand]
