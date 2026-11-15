import numpy as np
import pandas as pd

from rr_pressure.challengers import ChallengerE_DirectQuantileBoosted
from rr_pressure.compare import _select_ipl_model, evaluate_top10_performance
from rr_pressure.impact import compute_cumulative_prematch_features


def test_same_day_fixtures_do_not_supply_history_to_each_other():
    matches = pd.DataFrame({
        "player_id": [1, 1, 1],
        "match_id": [10, 20, 30],
        "match_date": ["2025-01-01", "2025-01-01", "2025-01-02"],
        "hp_balls_faced": [8, 10, 6],
        "hp_bat_impact": [2.0, 1.0, 0.0],
        "ord_balls_faced": [12, 12, 6],
        "ord_bat_impact": [3.0, 3.0, 0.0],
        "prior_ord_balls": [900, 900, 900],
    })
    result = compute_cumulative_prematch_features(matches, "batting")
    assert result["hp_balls"].tolist() == [0, 0, 18]
    assert result["prior_ord_balls"].tolist() == [0, 0, 24]
    assert result["usual_level"].tolist() == [0.0, 0.0, 1.0]


def test_booster_cutoff_profile_uses_training_definition():
    booster = ChallengerE_DirectQuantileBoosted()
    profiles = pd.DataFrame({
        "player_id": [1], "ord_impact": [6.0], "ord_balls": [24],
        "usual_level": [99.0], "hp_balls": [18],
    })
    context = pd.DataFrame({"player_id": [1], "comp_tier": ["IPL"]})
    expected = np.array([[1.0, 18.0, 1.0, 12.0]])
    np.testing.assert_array_equal(booster._extract_features(context, profiles)[0], expected)
    np.testing.assert_array_equal(booster._extract_features(profiles, profiles)[0], expected)


def test_ipl_selection_checks_shortlist_performance_as_well_as_loss():
    def result(loss, interval, coverage, impact):
        return {
            "pinball_loss_q25": loss,
            "paired_pinball_difference_vs_b0_ci_90": interval,
            "top10_performance": {
                "assessable_picks_count": coverage,
                "realized_avg_impact_12b_player_weighted": impact,
            },
        }

    candidates = {
        "ablation_B0_no_pressure": result(3.0, [0, 0], 7, 1.0),
        "candidate_B_statistical": result(2.0, [-2.0, -0.5], 7, -1.0),
        "challenger_D_workload": result(2.5, [-1.0, -0.1], 8, 1.5),
        "challenger_E_quantile_boosted": result(2.4, [-1.0, 0.1], 8, 1.5),
    }
    assert _select_ipl_model(candidates) == "challenger_D_workload"


def test_unassessable_shortlist_has_no_bootstrap_interval():
    matches = pd.DataFrame({
        "match_id": [1], "player_id": [1], "hp_balls_faced": [1], "hp_bat_impact": [3.0],
    })
    report = evaluate_top10_performance([1], matches, "batting")
    assert report["assessable_picks_count"] == 0
    assert report["bootstrap_ci_90"] == [None, None]
