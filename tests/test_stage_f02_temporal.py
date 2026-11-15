"""Regression and validation tests for Stage F02: Temporal Boundaries, Workload Leakage Prevention, and State-Dependent Wicket Attribution."""

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(".").resolve()))

REVIEW_DIR = Path("artifacts_release_review")


@pytest.fixture(scope="module")
def review_data():
    ledger_path = REVIEW_DIR / "delivery_impact_ledger.csv"
    if not ledger_path.exists():
        pytest.skip("delivery_impact_ledger.csv not yet generated in artifacts_release_review")
    df = pd.read_csv(ledger_path, low_memory=False)
    bat = pd.read_csv(REVIEW_DIR / "match_player_batting_impact.csv")
    bowl = pd.read_csv(REVIEW_DIR / "match_player_bowling_impact.csv")
    with open(REVIEW_DIR / "attribution_audit.json", "r", encoding="utf-8") as f:
        audit = json.load(f)
    with open(REVIEW_DIR / "evaluation_split_manifest.json", "r", encoding="utf-8") as f:
        split = json.load(f)
    return df, bat, bowl, audit, split


def test_state_dependent_wicket_valuation(review_data):
    """Verify w(s) varies across game states: bounded in [1.0, 15.0] and PP > Death."""
    df, _, _, audit, _ = review_data
    
    assert "marginal_wicket_value_ws" in df.columns
    ws = df["marginal_wicket_value_ws"]
    assert (ws >= 1.0).all() and (ws <= 15.0).all()
    
    pp_high_wkt = df[(df["pre_balls_remaining"] >= 100) & (df["pre_wickets_in_hand"] >= 9)]["marginal_wicket_value_ws"].mean()
    death_mid_wkt = df[(df["pre_balls_remaining"] <= 24) & (df["pre_wickets_in_hand"].between(3, 5))]["marginal_wicket_value_ws"].mean()
    
    assert pp_high_wkt > death_mid_wkt, f"Expected PP ({pp_high_wkt:.2f}) > Death ({death_mid_wkt:.2f})"
    assert audit["state_dependent_wicket_used"] is True


def test_residual_centering_and_cross_fitting(review_data):
    """Verify peer residuals are centered and 5-fold cross-fitting was applied."""
    _, _, _, audit, _ = review_data
    
    assert audit.get("cross_fitting_folds") == 5
    assert abs(audit["peer_residual_mean_batting_runs"]) < 0.20
    assert abs(audit["peer_residual_mean_bowling_runs"]) < 0.20


def test_y12_target_definition(review_data):
    """Verify rate target is per-12 legal-ball rate, finite when hp_balls > 0."""
    _, bat, bowl, _, _ = review_data
    
    has_hp_bat = bat["hp_balls_faced"] > 0
    assert np.isfinite(bat.loc[has_hp_bat, "hp_bat_impact_12b"]).all()
    assert bat.loc[~has_hp_bat, "hp_bat_impact_12b"].isna().all()
    
    has_hp_bowl = bowl["hp_balls_bowled"] > 0
    assert np.isfinite(bowl.loc[has_hp_bowl, "hp_bowl_impact_12b"]).all()
    assert bowl.loc[~has_hp_bowl, "hp_bowl_impact_12b"].isna().all()


def test_no_realized_workload_in_challenger_e_features():
    """Verify that Challenger E's feature extractor uses standardized reference workload, not realized match balls."""
    from rr_pressure.challengers import ChallengerE_DirectQuantileBoosted
    model = ChallengerE_DirectQuantileBoosted()
    
    # Create dummy match opportunities with different realized match balls
    opp_1 = pd.DataFrame([{
        "player_id": 1001,
        "comp_tier": "IPL",
        "hp_balls_faced": 24, # 24 balls realized in match
    }])
    opp_2 = pd.DataFrame([{
        "player_id": 1001,
        "comp_tier": "IPL",
        "hp_balls_faced": 6,  # 6 balls realized in match
    }])
    p_stats = pd.DataFrame([{
        "player_id": 1001,
        "usual_level": 1.5,
        "hp_balls": 150,      # Historical training balls
    }])
    
    X1, _ = model._extract_features(opp_1, p_stats)
    X2, _ = model._extract_features(opp_2, p_stats)
    
    # Features must be identical despite different realized match workloads!
    np.testing.assert_array_equal(X1, X2, err_msg="Challenger E features varied with realized match balls!")
    assert X1[0, 3] == 12.0, "Expected standardized 12.0 ball reference workload."


def test_temporal_split_integrity(review_data):
    """Verify train, val, and test temporal windows are strictly disjoint."""
    _, _, _, _, split = review_data
    
    train_end = split["folds"]["TRAIN_2022_2024"]["date_range"][1]
    val_start = split["folds"]["VAL_2025"]["date_range"][0]
    val_end = split["folds"]["VAL_2025"]["date_range"][1]
    test_start = split["folds"]["TEST_HOLDOUT_2026"]["date_range"][0]
    
    assert train_end < val_start, f"Train {train_end} overlaps Val {val_start}"
    assert val_end < test_start, f"Val {val_end} overlaps Test {test_start}"
    assert split["assertions"]["no_match_overlap"] is True
    assert split["assertions"]["train_val_strict_order"] is True
    assert split["assertions"]["val_test_strict_order"] is True
