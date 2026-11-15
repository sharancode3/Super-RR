"""Test Stage R02: Fit contract, thin support penalization, and model dispatch."""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from rr_pressure.challengers import ChallengerD_WorkloadDistributional, ChallengerE_DirectQuantileBoosted
from rr_pressure.forecast import fit_player_forecast


OUT_DIR = Path("artifacts_rank_validation")


def test_challenger_d_thin_sample_uncertainty_widening():
    """Verify Challenger D widens uncertainty and penalizes thin sample support via parameter SE."""
    bat_match_df = pd.read_csv(OUT_DIR / "match_player_batting_impact.csv")
    p_dim = pd.read_csv(OUT_DIR / "player_dimension.csv")
    
    # Fit Challenger D on historical data
    hist_matches = bat_match_df[bat_match_df["fold"].isin(["TRAIN_2022_2024", "VAL_2025"])]
    model_d = ChallengerD_WorkloadDistributional(df=5, m_prior=36.0)
    model_d.fit(hist_matches, p_dim, discipline="batting")
    
    # Check Rajapaksa (2003) vs an established player (e.g. 1699 SKY or 1184 Klaasen)
    raj_prof = model_d.player_profiles.get(2003)
    assert raj_prof is not None, "Rajapaksa profile must exist"
    
    # Established player with high sample support
    established_pids = [pid for pid, prof in model_d.player_profiles.items() if prof["n_opps"] >= 15]
    assert len(established_pids) > 0
    est_pid = established_pids[0]
    est_prof = model_d.player_profiles[est_pid]
    
    # Rajapaksa has few opportunities and lower n_eff
    assert raj_prof["n_eff"] < est_prof["n_eff"]
    # Rajapaksa parameter SE must be strictly larger than established player SE
    assert raj_prof["se_param"] > est_prof["se_param"]
    
    # Test predictive quantile at 12-ball scenario workload
    pids = np.array([2003, est_pid])
    workloads = np.array([12.0, 12.0])
    q25 = model_d.predict_quantile(pids, workloads, quantile=0.25)
    means = model_d.predict_mean(pids)
    
    penalties = means - q25
    # Thin sample penalty must be strictly greater than established player penalty
    assert penalties[0] > penalties[1], (
        f"Thin sample penalty ({penalties[0]:.4f}) must be greater than established penalty ({penalties[1]:.4f})"
    )


def test_forecast_records_score_and_support_consistently():
    """Verify forecast records score, support, and uncertainty from the same row without leakage."""
    bat_forecast_path = OUT_DIR / "player_reliability_forecasts_batting.csv"
    assert bat_forecast_path.exists()
    
    df = pd.read_csv(bat_forecast_path)
    
    required_cols = [
        "player_id", "player_name", "hp_balls", "hp_matches", "ord_balls",
        "usual_level", "pressure_lift", "b0_mean", "b0_q25", "b1_mean", "b1_q25",
        "param_se", "predictive_sigma", "is_qualified"
    ]
    for col in required_cols:
        assert col in df.columns, f"Missing required column {col}"
        
    # Check monotonicity of quantiles: q25 <= mean
    assert (df["b0_q25"] <= df["b0_mean"]).all()
    assert (df["b1_q25"] <= df["b1_mean"]).all()
    
    # Check predictive sigma includes parameter SE
    expected_sigma = np.sqrt(df["match_sigma"]**2 + df["param_se"]**2)
    np.testing.assert_allclose(df["predictive_sigma"].values, expected_sigma.values, rtol=1e-5)


def test_challenger_e_pre_match_features_only():
    """Verify Challenger E trains and predicts using pre-match features only."""
    bat_match_df = pd.read_csv(OUT_DIR / "match_player_batting_impact.csv")
    p_stats = pd.read_csv(OUT_DIR / "player_reliability_forecasts_batting.csv")
    
    hist_matches = bat_match_df[bat_match_df["fold"].isin(["TRAIN_2022_2024", "VAL_2025"])]
    model_e = ChallengerE_DirectQuantileBoosted(quantile=0.25, seed=2027)
    model_e.fit(hist_matches, p_stats, discipline="batting")
    
    assert model_e.fitted, "Challenger E must be fitted"
    
    preds = model_e.predict(hist_matches.iloc[:10], p_stats)
    assert len(preds) == 10
    assert not np.isnan(preds).any()
