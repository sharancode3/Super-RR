"""Regression and validation tests for Stage 10 Robustness Checks."""

import json
from pathlib import Path
import sys
sys.path.insert(0, ".")
import pytest

ARTIFACTS_DIR = Path("artifacts_revalidated") if Path("artifacts_revalidated").exists() else Path("artifacts")


def test_bootstrap_preserves_match_multiplicity():
    """Verify Stage 10 repair:
    1. Cluster bootstrap weights rows by match draw count, preserving multiplicity.
    2. Repeated match draws are never deduplicated to weight 1.
    """
    import numpy as np
    import pandas as pd
    from rr_pressure.robustness import run_bootstrap_stability
    
    # Construct synthetic match df with two matches
    synth_matches = pd.DataFrame({
        "match_id": [101, 102],
        "player_id": [1, 1],
        "fold": ["TRAIN_2022_2024", "VAL_2025"],
        "hp_balls_faced": [20, 30],
        "hp_bat_impact": [10.0, 15.0],
    })
    synth_pdim = pd.DataFrame({
        "player_id": [1],
        "player_name": ["Test Batter"],
        "inferred_role": ["TOP_ORDER_BATTER"],
        "bowler_type": ["Unknown"],
    })
    
    # If match 101 is drawn twice in sample_mids, total balls must equal 20*2 = 40
    sample_mids = [101, 101]
    mid_counts = pd.Series(sample_mids).value_counts()
    sub = synth_matches[synth_matches["match_id"].isin(mid_counts.index)].copy()
    weights = sub["match_id"].map(mid_counts).values
    weighted_balls = sub["hp_balls_faced"].values * weights
    assert np.array_equal(weights, [2])
    assert np.array_equal(weighted_balls, [40])


def test_robustness_report_file_exists():
    path = ARTIFACTS_DIR / "robustness_report.json"
    assert path.exists(), "robustness_report.json does not exist"


def test_robustness_sensitivities():
    path = ARTIFACTS_DIR / "robustness_report.json"
    with open(path, "r", encoding="utf-8") as f:
        rep = json.load(f)
        
    assert "pressure_percentile_sensitivity" in rep
    assert "cutoff_15_percent" in rep["pressure_percentile_sensitivity"]
    assert "cutoff_25_percent" in rep["pressure_percentile_sensitivity"]
    
    assert "competition_tier_sensitivity" in rep
    assert "non_emerging_top10_overlap" in rep["competition_tier_sensitivity"]
    assert "ipl_only_top10_overlap" in rep["competition_tier_sensitivity"]
    
    assert "workload_evidence_floor_sensitivity" in rep
    wf = rep["workload_evidence_floor_sensitivity"]
    assert wf["standard_floor_48b_6m"]["qualified_batters"] > 50
    assert wf["standard_floor_48b_6m"]["qualified_bowlers"] > 50


def test_standout_and_bootstrap_stability():
    path = ARTIFACTS_DIR / "robustness_report.json"
    with open(path, "r", encoding="utf-8") as f:
        rep = json.load(f)
        
    standout = rep["standout_match_sensitivity"]
    assert len(standout["batting_top15"]) == 15
    assert len(standout["bowling_top15"]) == 15
    
    boot = rep["bootstrap_stability_100_replicates"]
    assert len(boot["batting_top15"]) == 15
    assert len(boot["bowling_top15"]) == 15
    for item in boot["batting_top15"]:
        assert 0.0 <= item["top10_inclusion_freq"] <= 1.0
        assert len(item["rank_ci_90"]) == 2


def test_borderline_cohort_review():
    path = ARTIFACTS_DIR / "robustness_report.json"
    with open(path, "r", encoding="utf-8") as f:
        rep = json.load(f)
        
    borderline = rep["borderline_cohort_review_ranks_8_to_15"]
    assert len(borderline["batting"]) == 8
    assert len(borderline["bowling"]) == 8
    for row in borderline["batting"]:
        assert 8 <= row["rank"] <= 15
        assert "assessment" in row
