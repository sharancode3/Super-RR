"""Verification tests for Step 2: Player Confidence, Calibration, and Stability Metrics."""
import json
from pathlib import Path
import pytest
import numpy as np

REPO_ROOT = Path("C:/SHARAN PROJECTS/rr")

def get_fresh_dir() -> Path:
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


def test_player_confidence_metrics_artifact_exists():
    path = get_fresh_dir() / "player_confidence_metrics.json"
    assert path.exists(), f"Missing {path}"
    assert path.stat().st_size > 0, f"Empty {path}"


def test_player_confidence_profiles_20_players():
    path = get_fresh_dir() / "player_confidence_metrics.json"
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    
    profiles = doc["official_picks_confidence_profiles"]
    assert len(profiles) == 20, f"Expected 20 profiles, got {len(profiles)}"
    
    bat_count = sum(1 for p in profiles if p["role_pool"] == "Batting")
    bowl_count = sum(1 for p in profiles if p["role_pool"] == "Bowling")
    assert bat_count == 10
    assert bowl_count == 10
    
    for p in profiles:
        pid = p["player_id"]
        name = p["player_name"]
        forecast = p["performance_forecast_12b"]
        mean = forecast["mean"]
        q25 = forecast["q25"]
        q10 = forecast["q10"]
        q90 = forecast["q90"]
        
        # Finite floats
        assert np.isfinite(mean)
        assert np.isfinite(q25)
        assert np.isfinite(q10)
        assert np.isfinite(q90)
        
        # Ordered quantiles
        assert q10 <= q25 <= q90, f"Quantile monotonicity failure for {name}: {q10} <= {q25} <= {q90}"
        
        # Lift decomposition
        decomp = p["pressure_lift_decomposition_12b"]
        if p["role_pool"] == "Bowling":
            assert decomp["modeled_pressure_lift"] == 0.0, f"B0 modeled lift must be 0.0, got {decomp['modeled_pressure_lift']}"
            assert decomp["pressure_lift_estimator"] == "ZERO_BY_CONSTRUCTION_B0"
            assert "observed_hp_minus_usual_lift" in decomp
        
        # Calibrated event probability
        calib_prob = p["calibrated_event_probability"]
        p_pos = calib_prob["p_positive_impact_in_pressure"]
        assert 0.0 <= p_pos <= 1.0, f"Probability out of range: {p_pos}"
        
        # Shortlist stability
        stab = p["shortlist_stability_100_replicates"]
        assert stab["total_draws"] == 100
        assert 0 <= stab["eligible_draws"] <= 100
        assert 0 <= stab["top10_draws"] <= 100
        assert stab["top10_draws"] <= stab["eligible_draws"] <= 100
        if stab["eligible_draws"] == 0:
            assert stab["central_rank_range"] == []
        else:
            assert isinstance(stab["central_rank_range"], list)
            
        # No arbitrary HIGH_CONFIDENCE string
        p_str = json.dumps(p)
        assert "HIGH_CONFIDENCE" not in p_str, f"Found arbitrary HIGH_CONFIDENCE in profile {name}"
        assert "BORDERLINE_SENSITIVE" not in p_str, f"Found arbitrary BORDERLINE_SENSITIVE in profile {name}"


def test_calibration_benchmarks_parity():
    path = get_fresh_dir() / "player_confidence_metrics.json"
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
        
    bench = doc["model_calibration_benchmarks_2025_ipl"]
    assert "batting_challenger_d" in bench
    assert "bowling_ablation_b0" in bench
    
    bat_d = bench["batting_challenger_d"]
    bat_slices = bat_d.get("raw_interval_slices", bat_d.get("slices", {}))
    bowl_slices = bench["bowling_ablation_b0"].get("interval_slices", bench["bowling_ablation_b0"].get("slices", {}))
    
    for s_dict in [bat_slices, bowl_slices]:
        assert "all_positive_workloads" in s_dict
        assert "slice_1_to_5_balls" in s_dict
        assert "slice_6_plus_balls" in s_dict
        
        for s_key in ["all_positive_workloads", "slice_1_to_5_balls", "slice_6_plus_balls"]:
            s = s_dict[s_key]
            assert s["sample_size"] > 0
            assert "q25_pinball_loss" in s
            assert "coverage_share_le_q25" in s
            assert "mae" in s
            assert "empirical_coverage_ci_80" in s
            assert "average_width_80" in s
            assert "lower_miss_rate" in s
            assert "upper_miss_rate" in s
            assert "interval_score_80" in s
            
    # Parity check
    bat_all_cov = bat_slices["all_positive_workloads"]["empirical_coverage_ci_80"]
    bat_short_cov = bat_slices["slice_1_to_5_balls"]["empirical_coverage_ci_80"]
    assert 0.60 <= bat_all_cov <= 0.75, f"Batting all cov {bat_all_cov} out of parity range (~63.8%)"
    assert 0.48 <= bat_short_cov <= 0.60, f"Batting short cov {bat_short_cov} out of parity range (~52.4%)"
    
    bowl_all_cov = bowl_slices["all_positive_workloads"]["empirical_coverage_ci_80"]
    bowl_short_cov = bowl_slices["slice_1_to_5_balls"]["empirical_coverage_ci_80"]
    assert 0.68 <= bowl_all_cov <= 0.80, f"Bowling all cov {bowl_all_cov} out of parity range (~72.0%)"
    assert 0.50 <= bowl_short_cov <= 0.65, f"Bowling short cov {bowl_short_cov} out of parity range (~55.4%)"
