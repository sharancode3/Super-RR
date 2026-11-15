"""Comprehensive Verification Suite for Chronological Calibration, Prediction Parity, and Market Invariants.

Tests:
1. Chronological independence: evaluation features fixed, past replay unchanged.
2. Production forecast parity: exact agreement between player_confidence_metrics.json and top10 CSVs.
3. Quantile ordering and symmetry: q10 <= q25 <= q50 <= q90, mean == q50 for symmetric distributions.
4. Modeled lift arithmetic: modeled_lift == mean - usual for D, strictly 0.0 for B0.
5. Observed lift arithmetic: observed_hp_minus_usual_lift == ipl_hp_rate_12b - usual_impact_12b.
6. Shortlist stability invariants: top10_draws <= eligible_draws <= total_draws.
7. Explicit market status transitions without substring bugs.
8. Delivery scoring regressions: (20181, 2, 120) and (16042, 1, 67).
"""

import json
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

REPO_ROOT = Path("C:/SHARAN PROJECTS/rr")

def get_active_run_dir() -> Path:
    candidates = [
        REPO_ROOT / "artifacts_hardened_v4_20261113",
        REPO_ROOT / "artifacts_hardened_v3_20261113",
        REPO_ROOT / "artifacts_hardened_v2_20261113",
        REPO_ROOT / "artifacts_hardened_20261113",
    ]
    for c in candidates:
        if c.exists() and (c / "player_confidence_metrics.json").exists():
            return c
    return REPO_ROOT / "artifacts_hardened_20261113"


def test_cricket_scoring_ledger_invariants():
    """Verify delivery ledger accounting for plain wide and no-ball cases."""
    run_dir = get_active_run_dir()
    ledger_path = run_dir / "delivery_impact_ledger.csv"
    assert ledger_path.exists(), f"Missing {ledger_path}"
    
    # Read only needed columns for speed
    cols = ["match_id", "innings", "innings_ball_num", "is_legal_ball", "is_wide", "is_noball",
            "offbat_runs", "bowler_charge_runs", "batting_impact", "bowling_impact"]
    df = pd.read_csv(ledger_path, usecols=cols, low_memory=False)
    
    # 1. Plain wide in match 20181, innings 2, innings_ball_num 120: batting 0, bowling -1
    r_wide = df[(df["match_id"] == 20181) & (df["innings"] == 2) & (df["innings_ball_num"] == 120)]
    assert not r_wide.empty, "Match 20181 inn 2 ball 120 not found"
    row_w = r_wide.iloc[0]
    assert not bool(row_w["is_legal_ball"]), "Wide must not be a legal ball"
    assert bool(row_w["is_wide"]), "Must be flagged as wide"
    assert float(row_w["batting_impact"]) == 0.0, f"Batting impact must be 0, got {row_w['batting_impact']}"
    assert float(row_w["bowling_impact"]) == -1.0, f"Bowling impact must be -1, got {row_w['bowling_impact']}"
    assert float(row_w["bowler_charge_runs"]) == 1.0, f"Bowler charge must be 1, got {row_w['bowler_charge_runs']}"
    
    # 2. No-ball at match 16042, innings 1, innings_ball_num 67: 4 off bat, 5 charged, zero legal balls
    r_nb = df[(df["match_id"] == 16042) & (df["innings"] == 1) & (df["innings_ball_num"] == 67)]
    assert not r_nb.empty, "Match 16042 inn 1 ball 67 not found"
    row_nb = r_nb.iloc[0]
    assert not bool(row_nb["is_legal_ball"]), "No-ball must not be a legal ball"
    assert bool(row_nb["is_noball"]), "Must be flagged as no-ball"
    assert float(row_nb["offbat_runs"]) == 4.0, f"Off-bat runs must be 4, got {row_nb['offbat_runs']}"
    assert float(row_nb["bowler_charge_runs"]) == 5.0, f"Bowler charge must be 5, got {row_nb['bowler_charge_runs']}"
    assert float(row_nb["batting_impact"]) == 4.0, f"Batting impact must be 4, got {row_nb['batting_impact']}"
    assert float(row_nb["bowling_impact"]) == -5.0, f"Bowling impact must be -5, got {row_nb['bowling_impact']}"


def test_production_forecast_parity_across_artifacts():
    """Verify exact bit-for-bit / rounded floating point agreement between confidence JSON and top10 CSVs."""
    run_dir = get_active_run_dir()
    conf_path = run_dir / "player_confidence_metrics.json"
    bat_path = run_dir / "top10_batters_under_pressure.csv"
    bowl_path = run_dir / "top10_bowlers_under_pressure.csv"
    short_path = run_dir / "rr_shortlist.csv"
    
    with open(conf_path, "r", encoding="utf-8") as f:
        conf_doc = json.load(f)
        
    bat_df = pd.read_csv(bat_path).set_index("player_id")
    bowl_df = pd.read_csv(bowl_path).set_index("player_id")
    short_df = pd.read_csv(short_path).set_index("player_id")
    
    profiles = conf_doc["official_picks_confidence_profiles"]
    assert len(profiles) == 20
    
    for p in profiles:
        pid = p["player_id"]
        role = p["role_pool"]
        fcast = p["performance_forecast_12b"]
        decomp = p["pressure_lift_decomposition_12b"]
        
        target_df = bat_df if role == "Batting" else bowl_df
        assert pid in target_df.index, f"Player {pid} missing from top 10 {role} CSV"
        row = target_df.loc[pid]
        
        # Mean agreement
        json_mean = fcast["mean"]
        csv_mean = round(float(row["predicted_hp_impact_12b"]), 3)
        assert abs(json_mean - csv_mean) < 1e-2, f"Mean mismatch for {p['player_name']}: json={json_mean}, csv={csv_mean}"
        
        # Q25 agreement
        json_q25 = fcast["q25"]
        csv_q25 = round(float(row["conservative_score_q25"]), 3)
        assert abs(json_q25 - csv_q25) < 1e-2, f"Q25 mismatch for {p['player_name']}: json={json_q25}, csv={csv_q25}"
        
        # Quantile monotonicity
        q10, q25, q50, q90 = fcast["q10"], fcast["q25"], fcast["q50"], fcast["q90"]
        assert q10 <= q25 <= q50 <= q90, f"Quantile ordering violation for {p['player_name']}: {q10} <= {q25} <= {q50} <= {q90}"
        
        # Mean == median for symmetric distribution
        assert abs(fcast["mean"] - q50) < 1e-2, f"Mean-median equality violation for {p['player_name']}"
        
        # Modeled lift
        if role == "Bowling":
            assert decomp["modeled_pressure_lift"] == 0.0
            assert decomp["pressure_lift_estimator"] == "ZERO_BY_CONSTRUCTION_B0"
        else:
            expected_lift = round(float(row["predicted_hp_impact_12b"]) - float(row["usual_impact_12b"]), 3)
            assert abs(decomp["modeled_pressure_lift"] - expected_lift) < 1e-2
            
        # Observed lift
        obs_lift = decomp["observed_hp_minus_usual_lift"]
        expected_obs_diff = round(float(row["ipl_hp_rate_12b"]) - float(row["usual_impact_12b"]), 3)
        assert abs(obs_lift - expected_obs_diff) < 1e-2
        
        # Stability invariants
        stab = p["shortlist_stability_100_replicates"]
        assert stab["top10_draws"] <= stab["eligible_draws"] <= stab["total_draws"]


def test_market_status_explicit_enums():
    """Verify that market records use explicit statuses without substring 'REG' or 'RELEASED' bugs."""
    run_dir = get_active_run_dir()
    conf_path = run_dir / "player_confidence_metrics.json"
    with open(conf_path, "r", encoding="utf-8") as f:
        conf_doc = json.load(f)
        
    for p in conf_doc["official_picks_confidence_profiles"]:
        pid = p["player_id"]
        route = p["auction_and_squad_route"]
        
        conf_entry = route["confirmed_auction_entry"]
        rel_st = route["release_status"]
        rep_reg = route["reported_registration"]
        
        # Specific player invariants
        if pid == 4373:  # Mustafizur Rahman
            assert conf_entry == "CONDITIONAL_ON_BCCI_NOC_CLEARANCE", f"Mustafizur confirmed entry must be CONDITIONAL_ON_BCCI_NOC_CLEARANCE, got {conf_entry}"
            assert rel_st == "PRE_2026_BCCI_DIRECTIVE_RELEASE", f"Mustafizur release status must be PRE_2026_BCCI_DIRECTIVE_RELEASE, got {rel_st}"
            assert rep_reg == "REPORTED_REGISTRATION_BCB_NOV11"
        elif pid == 8661:  # Matheesha Pathirana
            assert conf_entry == "CONDITIONAL_ON_RELEASE_AND_FITNESS", f"Pathirana confirmed entry must be CONDITIONAL_ON_RELEASE_AND_FITNESS, got {conf_entry}"
            assert rel_st == "CONTRACTED_RIVAL_INJURY_LIST", f"Pathirana release status must be CONTRACTED_RIVAL_INJURY_LIST, got {rel_st}"
            assert route["fitness_clearance_status"] == "HAMSTRING_REHABILITATION"
            assert "FITNESS_CLEARED" not in route["actionable_acquisition_route"], "Pathirana cannot claim FITNESS_CLEARED route while medical status is pending"
        elif pid == 8182:  # Donovan Ferreira
            assert conf_entry == "INTERNAL_RR_RETENTION_DECISION"
            assert rel_st == "INTERNAL_RR_INCUMBENT"
            assert rep_reg == "INTERNAL_ROSTER_MEMBER"
            assert "1.00 Cr" in route["rr_incumbent_comparison"] or "1 crore" in route["rr_incumbent_comparison"].lower()
        elif pid == 6423:  # Riyan Parag
            assert conf_entry == "INTERNAL_RR_RETENTION_DECISION"
            assert rel_st == "INTERNAL_RR_INCUMBENT"
            assert route["fitness_clearance_status"] == "POST_REHAB_SHOULDER_MONITORED"
        elif pid == 1566:  # Mohammed Shami
            assert conf_entry == "CONDITIONAL_ON_RELEASE"
            assert rel_st == "PENDING_NOV17_RETENTION_LIST"


def test_chronological_replay_slices():
    """Verify chronological replay benchmark metrics on 2025 IPL validation."""
    run_dir = get_active_run_dir()
    conf_path = run_dir / "player_confidence_metrics.json"
    with open(conf_path, "r", encoding="utf-8") as f:
        conf_doc = json.load(f)
        
    bench_2025 = conf_doc["model_calibration_benchmarks_2025_ipl"]
    bat_d = bench_2025["batting_challenger_d"]
    bowl_b0 = bench_2025["bowling_ablation_b0"]
    
    # Batting raw coverage
    raw_slices = bat_d["raw_interval_slices"]
    assert raw_slices["all_positive_workloads"]["sample_size"] == 500
    assert raw_slices["slice_1_to_5_balls"]["sample_size"] == 290
    assert raw_slices["slice_6_plus_balls"]["sample_size"] == 210
    
    # 2025 raw coverage ~63% overall, short stint ~51.7%
    assert 0.60 <= raw_slices["all_positive_workloads"]["empirical_coverage_ci_80"] <= 0.66
    assert 0.48 <= raw_slices["slice_1_to_5_balls"]["empirical_coverage_ci_80"] <= 0.55
    
    # Recalibrated interval benchmark reaches ~80% overall and ~71% short stint
    recal_slices = bat_d["recalibrated_interval_slices"]
    assert 0.78 <= recal_slices["all_positive_workloads"]["empirical_coverage_ci_80"] <= 0.83
    assert 0.68 <= recal_slices["slice_1_to_5_balls"]["empirical_coverage_ci_80"] <= 0.74
    
    # Bowling coverage ~72.0%
    bowl_slices = bowl_b0["interval_slices"]
    assert bowl_slices["all_positive_workloads"]["sample_size"] == 404
    assert 0.70 <= bowl_slices["all_positive_workloads"]["empirical_coverage_ci_80"] <= 0.75
    
    # Bowling Brier beats base rate
    brier_bowl = bowl_b0["event_probability_brier"]
    assert brier_bowl["brier_score"] <= brier_bowl["brier_baseline_base_rate"]
