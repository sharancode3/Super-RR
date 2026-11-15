import numpy as np
import pandas as pd

from rr_pressure.auction_lock import graded_profiles, select_recipe


def test_graded_pressure_preserves_legal_balls_and_runs_from_illegal_deliveries():
    deliveries = pd.DataFrame({
        "match_id": [1, 1, 1], "match_date": pd.to_datetime(["2026-04-01"] * 3),
        "comp_tier": "IPL", "match_phase": "DEATH", "venue_id": 1, "bowler_id": 15,
        "bowling_impact": [2, 3, -1], "is_legal_ball": [True, True, False],
        "is_high_pressure_15": [True, False, False], "is_high_pressure_20": [True, False, False],
        "is_high_pressure_25": [True, True, True],
    })
    row = graded_profiles(deliveries, "bowling").iloc[0]
    np.testing.assert_allclose(row[["hp_balls", "ordinary_balls", "hp_impact", "ordinary_impact"]].astype(float),
                               [4 / 3, 2 / 3, 8 / 3, 4 / 3])


def test_single_year_gain_cannot_mask_regression_or_leak_future_results():
    comparisons = pd.DataFrame([
        {"season": year, "lane": "forward", "recipe": recipe, "target_per_slot": impact,
         "pressure_per_slot": impact, "assessed_picks": 8, "mae": 3.}
        for year, name, value in [(2024, "challenger", -.2), (2025, "challenger", 1.), (2026, "challenger", 100.)]
        for recipe, impact in [("incumbent", 0.), (name, value)]
    ])
    assert select_recipe(comparisons) == "incumbent"
    comparisons.loc[comparisons["season"].eq(2024) & comparisons["recipe"].eq("challenger"), "target_per_slot"] = .2
    assert select_recipe(comparisons) == "challenger"
