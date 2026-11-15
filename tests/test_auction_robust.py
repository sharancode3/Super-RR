"""Regression tests for chronology, extras and shortlist constraints."""

import pandas as pd

from rr_pressure.auction_robust import candidate_order, make_match_profiles, player_features


def test_match_profiles_keep_illegal_delivery_impact_in_numerator():
    ledger = pd.DataFrame({
        "match_id": [1, 1, 1], "match_date": pd.to_datetime(["2025-04-02"] * 3),
        "comp_tier": ["IPL"] * 3, "match_phase": ["DEATH"] * 3, "venue_id": [7] * 3,
        "bowler_id": [9] * 3, "is_legal_ball": [True, False, True],
        "bowling_impact": [1., -4., 2.], "is_high_pressure_20": [True, True, False],
    })
    first = make_match_profiles(ledger, "bowling", 20).iloc[0]
    assert first[["hp_balls", "hp_impact", "ordinary_balls", "ordinary_impact"]].tolist() == [1, -3, 1, 2]


def test_features_use_strict_cutoff_and_resample_recent_evidence():
    rows = pd.DataFrame({
        "player_id": [1, 1], "match_id": [10, 11], "match_date": pd.to_datetime(["2025-04-02", "2025-04-03"]),
        "comp_tier": ["IPL", "IPL"], "match_phase": ["DEATH", "DEATH"],
        "hp_balls": [4, 7], "hp_impact": [2., 100.], "ordinary_balls": [12, 10],
        "ordinary_impact": [3., 100.],
    })
    cutoff = pd.Timestamp("2025-04-03")
    one = player_features(rows, cutoff).loc[1]
    two = player_features(rows, cutoff, fixture_weights={10: 2, 11: 10}).loc[1]
    assert one["recent_balls"] == 4
    assert two["recent_balls"] == 8
    assert one["recent_pressure_observed"] == two["recent_pressure_observed"] == 6


def test_role_coverage_and_order_do_not_use_franchise():
    scores = pd.Series(range(15, 0, -1), index=range(15))
    roles = pd.DataFrame({
        "deployment": ["POWERPLAY"] * 8 + ["DEATH"] * 3 + ["SPIN"] * 3 + ["MIDDLE"],
        "current_franchise": ["A"] * 7 + ["B"] * 8,
    })
    first = candidate_order(scores, roles, "bowling")
    second = candidate_order(scores, roles.assign(current_franchise="C"), "bowling")
    assert first == second == sorted(set(first))
    assert len(first) == 10
    assert roles.loc[first, "deployment"].value_counts().to_dict() == {"POWERPLAY": 5, "DEATH": 3, "SPIN": 2}
