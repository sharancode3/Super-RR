import numpy as np
import pandas as pd

from rr_pressure.auction_challenger import (
    RECIPES, decision_scenarios, empirical_band, joint_shrinkage, model_choice, rule_pressure,
)


def test_joint_shrinkage_pools_ordinary_play_when_pressure_is_sparse():
    frame = pd.DataFrame({
        "ordinary_balls": [0, 48, 48], "hp_balls": [0, 0, 48],
        "ordinary_impact": [0, 24, 24], "hp_impact": [0, 0, 24],
    })
    expected = [0, 3, 102 / 23]
    np.testing.assert_allclose(joint_shrinkage(frame, frame.index), expected)


def test_pressure_uses_pre_delivery_resources():
    frame = pd.DataFrame({
        "pre_balls_remaining": [12, 12, 12, 120],
        "pre_target_reconciled_gap": [20, 70, np.nan, np.nan],
        "pre_wickets_in_hand": [7, 8, 5, 10],
        "innings": [2, 2, 1, 1], "match_phase": ["DEATH", "DEATH", "DEATH", "POWERPLAY"],
    })
    assert rule_pressure(frame).tolist() == [True, False, True, False]


def test_2026_cannot_change_model_selection():
    records = []
    for name in RECIPES:
        for year in (2024, 2025, 2026):
            advantage = .5 if name == "huber" and year < 2026 else 0
            records.append({
                "season": year, "lane": "forward", "recipe": name, "mae": 3,
                "target_per_slot": advantage, "pressure_per_slot": advantage, "assessed_picks": 9,
            })
    data = pd.DataFrame(records)
    assert model_choice(data) == "huber"
    data.loc[data["season"].eq(2026) & data["recipe"].eq("boost"), "target_per_slot"] = 100
    assert model_choice(data) == "huber"


def test_empirical_band_with_limited_calibration():
    assert np.isnan(empirical_band([1, 2, 3]))
    assert empirical_band(np.arange(1, 21)) == 20


def test_scenarios_do_not_change_skill_scores_or_relax_clearance():
    pool = pd.DataFrame({
        "player_name": ["Death option", "New-ball option", "Alternative", "Rival core", "Clearance pending"],
        "deployment": ["DEATH", "POWERPLAY", "DEATH", "SPIN", "SPIN"],
    }, index=pd.Index([4641, 29888, 600001, 600002, 600003], name="player_id"))
    scores = pd.Series([5., 4., 3., 2., 9.], index=pool.index)
    registry = pd.DataFrame({
        "player_id": pool.index,
        "availability_status": ["PENDING", "PENDING", "PENDING", "CONTRACTED_RIVAL_CORE", "FITNESS_CLEARANCE"],
    })
    runs = decision_scenarios(pool, scores, registry, "bowling")
    by_case = runs.groupby("scenario")["player_id"].apply(list)
    assert by_case["base_case"] == [4641, 29888, 600001]
    assert by_case["fitness_contingency"] == [600001]
    assert by_case["wider_release_case"] == [4641, 29888, 600001, 600002]
    assert runs["player_id"].map(scores).equals(runs["priority"])
