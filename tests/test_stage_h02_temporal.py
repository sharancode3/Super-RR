"""Regression and validation tests for Stage H02: Chronological Reference, State-Dependent Wicket Valuation, and Out-of-Fold Peer Targets."""

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(".").resolve()))

HARDENED_DIR = Path("artifacts_hardened")


@pytest.fixture(scope="module")
def impact_data():
    ledger_path = HARDENED_DIR / "delivery_impact_ledger.csv"
    if not ledger_path.exists():
        pytest.skip("delivery_impact_ledger.csv not yet generated in artifacts_hardened")
    df = pd.read_csv(ledger_path, low_memory=False)
    bat = pd.read_csv(HARDENED_DIR / "match_player_batting_impact.csv")
    bowl = pd.read_csv(HARDENED_DIR / "match_player_bowling_impact.csv")
    with open(HARDENED_DIR / "attribution_audit.json", "r", encoding="utf-8") as f:
        audit = json.load(f)
    return df, bat, bowl, audit


def test_state_dependent_wicket_valuation(impact_data):
    """Verify w(s) varies across game states: higher early/when conserving wickets, bounded in [1.0, 15.0]."""
    df, _, _, audit = impact_data
    
    assert "marginal_wicket_value_ws" in df.columns
    ws = df["marginal_wicket_value_ws"]
    assert (ws >= 1.0).all() and (ws <= 15.0).all()
    
    # Check that Powerplay with 10 wickets in hand has higher wicket value than Death with 3-4 wickets in hand
    pp_high_wkt = df[(df["pre_balls_remaining"] >= 100) & (df["pre_wickets_in_hand"] >= 9)]["marginal_wicket_value_ws"].mean()
    death_mid_wkt = df[(df["pre_balls_remaining"] <= 24) & (df["pre_wickets_in_hand"].between(3, 5))]["marginal_wicket_value_ws"].mean()
    
    assert pp_high_wkt > death_mid_wkt, f"Expected PP wicket value ({pp_high_wkt:.2f}) > Death wicket value ({death_mid_wkt:.2f})"
    assert audit["state_dependent_wicket_used"] is True


def test_cross_fitting_and_residual_centering(impact_data):
    """Verify peer residuals are centered and cross-fitting fold count is recorded."""
    _, _, _, audit = impact_data
    
    assert audit.get("cross_fitting_folds") == 5
    assert abs(audit["peer_residual_mean_batting_runs"]) < 0.20
    assert abs(audit["peer_residual_mean_bowling_runs"]) < 0.20


def test_y12_target_definition(impact_data):
    """Verify y12 is defined as 12 * hp_impact / hp_balls, finite when hp_balls > 0, and NaN when hp_balls == 0."""
    _, bat, bowl, _ = impact_data
    
    # Batting
    has_hp_bat = bat["hp_balls_faced"] > 0
    assert np.isfinite(bat.loc[has_hp_bat, "hp_bat_impact_12b"]).all()
    assert bat.loc[~has_hp_bat, "hp_bat_impact_12b"].isna().all()
    
    # Bowling
    has_hp_bowl = bowl["hp_balls_bowled"] > 0
    assert np.isfinite(bowl.loc[has_hp_bowl, "hp_bowl_impact_12b"]).all()
    assert bowl.loc[~has_hp_bowl, "hp_bowl_impact_12b"].isna().all()


def test_no_future_role_leakage_in_training(impact_data):
    """Verify that player roles assigned in the training ledger match the pre-cutoff dimension."""
    df, _, _, _ = impact_data
    p_train = pd.read_csv(HARDENED_DIR / "player_dimension_train.csv")
    train_role_map = p_train.set_index("player_id")["inferred_role"].to_dict()
    
    train_deliveries = df[df["fold"] == "TRAIN_2022_2024"]
    for pid in train_deliveries["striker_id"].unique()[:50]:
        if pid in train_role_map:
            actual_role = train_deliveries[train_deliveries["striker_id"] == pid]["striker_role"].iloc[0]
            assert actual_role == train_role_map[pid], f"Role mismatch for player {pid}: {actual_role} vs {train_role_map[pid]}"
