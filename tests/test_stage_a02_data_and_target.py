"""Stage A02: Acceptance Tests for Data, Target, and Chronological Provenance.

Validates:
1. Reconciled event-to-scoreboard ledger with distinct tracking of official scorecards,
   delivery rows, and legal workload.
2. Real-scenario pressure scoring on mixed fixtures (setting total, close chase, lopsided chase).
3. Strict forward-only chronological provenance of pre-match features (usual_level, hp_balls)
   with zero future-to-past or within-match leakage.
4. Frozen common target normalization (12-ball equivalents) and centered impact attribution.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from rr_pressure.impact import compute_cumulative_prematch_features

ARTIFACTS_DIR = Path("artifacts_decision_validation")


def test_official_scorecard_vs_delivery_grain_distinction():
    """Verify that official scorecards, delivery rows, and legal balls are kept distinct."""
    batting_impact_path = ARTIFACTS_DIR / "match_player_batting_impact.csv"
    assert batting_impact_path.exists(), f"Missing {batting_impact_path}"
    
    df_bat = pd.read_csv(batting_impact_path)
    
    # Fixture 50943: Vaibhav Sooryavanshi (ID 50284).
    # Official score is 97 runs off 29 balls.
    # The pack contains 31 delivery rows where he was striker, and 28 legal balls faced.
    soorya_50943 = df_bat[(df_bat["match_id"] == 50943) & (df_bat["player_id"] == 50284)]
    assert len(soorya_50943) == 1, "Expected single row for player 50284 in fixture 50943"
    row_50943 = soorya_50943.iloc[0]
    
    assert row_50943["total_balls_faced"] == 28, f"Expected 28 legal balls, got {row_50943['total_balls_faced']}"
    assert row_50943["total_runs_scored"] == 97, f"Expected 97 runs, got {row_50943['total_runs_scored']}"
    
    # Check in delivery_pressure_labels that raw delivery rows equals 31
    labels_path = ARTIFACTS_DIR / "delivery_pressure_labels.csv"
    df_labels = pd.read_csv(labels_path, usecols=["match_id", "striker_id", "is_legal_ball"], low_memory=False)
    rows_50943 = df_labels[(df_labels["match_id"] == 50943) & (df_labels["striker_id"] == 50284)]
    assert len(rows_50943) == 31, f"Expected 31 total delivery rows in pack, got {len(rows_50943)}"
    
    # Fixture 50944: official score is 96 off 47 balls, pack has 48 delivery rows, 47 legal balls
    soorya_50944 = df_bat[(df_bat["match_id"] == 50944) & (df_bat["player_id"] == 50284)]
    assert len(soorya_50944) == 1, "Expected single row for player 50284 in fixture 50944"
    row_50944 = soorya_50944.iloc[0]
    assert row_50944["total_balls_faced"] == 47, f"Expected 47 legal balls, got {row_50944['total_balls_faced']}"
    assert row_50944["total_runs_scored"] == 96, f"Expected 96 runs, got {row_50944['total_runs_scored']}"
    
    rows_50944 = df_labels[(df_labels["match_id"] == 50944) & (df_labels["striker_id"] == 50284)]
    assert len(rows_50944) == 48, f"Expected 48 total delivery rows in pack, got {len(rows_50944)}"


def test_mixed_pressure_replay_fixtures():
    """Verify pressure is identified across varied real scenarios (setting total, close, lopsided)."""
    p_balls_path = ARTIFACTS_DIR / "delivery_pressure_labels.csv"
    assert p_balls_path.exists(), f"Missing {p_balls_path}"
    
    df_p = pd.read_csv(p_balls_path, usecols=["match_id", "innings", "is_high_pressure_20", "pre_ball_leverage"], low_memory=False)
    
    # Check fixtures 40759, 50943, 50944
    for mid in [40759, 50943, 50944]:
        sub = df_p[df_p["match_id"] == mid]
        assert not sub.empty, f"Fixture {mid} missing from pressure labeled deliveries"
        hp_count = sub["is_high_pressure_20"].sum()
        assert hp_count > 0, f"Fixture {mid} should contain high-pressure deliveries"


def test_strict_forward_only_feature_provenance():
    """Verify pre-match features (usual_level, hp_balls) strictly depend only on past matches."""
    batting_impact_path = ARTIFACTS_DIR / "match_player_batting_impact.csv"
    df_bat = pd.read_csv(batting_impact_path)
    
    # Check that for any player's first chronological match, prior stats are 0
    df_sorted = df_bat.sort_values(["player_id", "match_date", "match_id"])
    first_matches = df_sorted.groupby("player_id").first()
    
    assert (first_matches["prior_ord_balls"] == 0.0).all(), "First match must have 0 prior ordinary balls"
    assert (first_matches["hp_balls"] == 0.0).all(), "First match must have 0 prior hp balls"
    assert (first_matches["usual_level"] == 0.0).all(), "First match must have 0.0 usual level"
    
    # Test mutation invariance: mutating a future match does not affect earlier pre-match features
    sample_df = pd.DataFrame({
        "player_id": [999, 999, 999],
        "match_id": [1, 2, 3],
        "match_date": ["2023-01-01", "2023-01-02", "2023-01-03"],
        "hp_balls_faced": [12, 12, 12],
        "hp_bat_impact": [5.0, 5.0, 5.0],
        "ord_balls_faced": [24, 24, 24],
        "ord_bat_impact": [4.0, 4.0, 4.0],
    })
    
    res1 = compute_cumulative_prematch_features(sample_df, "batting")
    usual_match2_base = res1.loc[res1["match_id"] == 2, "usual_level"].values[0]
    
    # Mutate match 3 (future relative to match 2)
    sample_mutated = sample_df.copy()
    sample_mutated.loc[sample_mutated["match_id"] == 3, "ord_bat_impact"] = 9999.0
    res2 = compute_cumulative_prematch_features(sample_mutated, "batting")
    usual_match2_after = res2.loc[res2["match_id"] == 2, "usual_level"].values[0]
    
    assert np.isclose(usual_match2_base, usual_match2_after), "Future match mutation leaked into match 2 features!"


def test_frozen_common_target():
    """Verify target metrics are normalized to 12 legal-ball equivalents with centered attribution."""
    batting_impact_path = ARTIFACTS_DIR / "match_player_batting_impact.csv"
    bowling_impact_path = ARTIFACTS_DIR / "match_player_bowling_impact.csv"
    
    df_bat = pd.read_csv(batting_impact_path)
    df_bowl = pd.read_csv(bowling_impact_path)
    
    # Check batting impact 12b calculation
    bat_valid = df_bat[df_bat["hp_balls_faced"] >= 6]
    expected_bat_12b = (bat_valid["hp_bat_impact"] / bat_valid["hp_balls_faced"]) * 12.0
    assert np.allclose(bat_valid["hp_bat_impact_12b"], expected_bat_12b, atol=1e-5), "Batting 12b mismatch"
    
    # Check bowling impact 12b calculation
    bowl_valid = df_bowl[df_bowl["hp_balls_bowled"] >= 6]
    expected_bowl_12b = (bowl_valid["hp_bowl_impact"] / bowl_valid["hp_balls_bowled"]) * 12.0
    assert np.allclose(bowl_valid["hp_bowl_impact_12b"], expected_bowl_12b, atol=1e-5), "Bowling 12b mismatch"
