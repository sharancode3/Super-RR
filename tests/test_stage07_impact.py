"""Regression and validation tests for Stage 07 Player Impact."""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

ARTIFACTS_DIR = Path("artifacts_revalidated") if Path("artifacts_revalidated").exists() else Path("artifacts")


def test_impact_fitted_wicket_value_and_legal_ball_denominator():
    """Verify Stage 07 repair:
    1. Fitted marginal wicket value from Stage 05 projected score model is used (not hardcoded 7.0).
    2. Denominators for balls faced & bowled strictly count legal balls, so wides do not inflate ball counts.
    """
    # 1. Wicket price check
    audit_path = ARTIFACTS_DIR / "attribution_audit.json"
    score_model_path = ARTIFACTS_DIR / "projected_score_model.json"
    assert audit_path.exists()
    assert score_model_path.exists()
    
    with open(audit_path, "r", encoding="utf-8") as f:
        audit = json.load(f)
    with open(score_model_path, "r", encoding="utf-8") as f:
        score_model = json.load(f)
        
    fitted_w_price = float(score_model.get("marginal_wicket_value_mid_innings", score_model.get("marginal_wicket_value", 7.0)))
    assert audit["wicket_price_used"] == pytest.approx(fitted_w_price, abs=1e-5)
    # Ensure it's not the uncalibrated hardcoded 7.0 default
    assert audit["wicket_price_used"] != 7.0
    
    # 2. Denominator check
    bat_df = pd.read_csv(ARTIFACTS_DIR / "match_player_batting_impact.csv")
    bowl_df = pd.read_csv(ARTIFACTS_DIR / "match_player_bowling_impact.csv")
    
    # Total balls must equal hp_balls + ord_balls
    assert (bat_df["total_balls_faced"] == bat_df["hp_balls_faced"] + bat_df["ord_balls_faced"]).all()
    assert (bowl_df["total_balls_bowled"] == bowl_df["hp_balls_bowled"] + bowl_df["ord_balls_bowled"]).all()
    
    # Check on delivery level: wide deliveries must have is_legal_ball == False
    df = pd.read_csv(ARTIFACTS_DIR / "delivery_impact_ledger.csv", low_memory=False)
    wides = df[df["extras_type"] == "wide"]
    assert len(wides) > 0
    assert (~wides["is_legal_ball"]).all()
    assert (wides["hp_balls_faced"] == 0).all()
    assert (wides["ord_balls_faced"] == 0).all()
    assert (wides["hp_balls_bowled"] == 0).all()
    assert (wides["ord_balls_bowled"] == 0).all()


def test_impact_ledger_attribution():
    df = pd.read_csv(ARTIFACTS_DIR / "delivery_impact_ledger.csv", low_memory=False)
    
    # 1. Non-striker run-out: bowler must NOT be credited with wicket
    ns_runouts = df[df["is_non_striker_dismissed"] & (df["dismissal_type"] == "RunOut")]
    assert len(ns_runouts) > 0
    assert (~ns_runouts["is_bowler_wicket"]).all()
    assert (~ns_runouts["is_striker_dismissed"]).all()
    
    # 2. Six off the bat must produce positive batting impact
    sixes = df[df["runs"] == 6]
    assert (sixes["batting_impact"] > 0).all()
    
    # 3. Bowler-credited wicket must produce positive bowling impact
    bowler_wkts = df[df["is_bowler_wicket"] == True]
    assert (bowler_wkts["bowling_impact"] > 0).all()


def test_peer_residuals_centering():
    audit_path = ARTIFACTS_DIR / "attribution_audit.json"
    assert audit_path.exists(), "attribution_audit.json does not exist"
    with open(audit_path, "r", encoding="utf-8") as f:
        audit = json.load(f)
        
    # Residual means should be within [-0.15, 0.15] runs
    assert abs(audit["peer_residual_mean_batting_runs"]) < 0.15
    assert abs(audit["peer_residual_mean_bowling_runs"]) < 0.15


def test_match_level_impact_aggregation():
    bat_df = pd.read_csv(ARTIFACTS_DIR / "match_player_batting_impact.csv")
    bowl_df = pd.read_csv(ARTIFACTS_DIR / "match_player_bowling_impact.csv")
    
    assert len(bat_df) > 5000, "Batting match aggregation too small"
    assert len(bowl_df) > 5000, "Bowling match aggregation too small"
    
    # Standardized 12b impact should be finite when balls > 0
    valid_bat_12b = bat_df[bat_df["hp_balls_faced"] > 0]["hp_bat_impact_12b"]
    assert valid_bat_12b.notna().all()
    assert np.isfinite(valid_bat_12b).all()
