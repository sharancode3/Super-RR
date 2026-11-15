"""Regression and validation tests for Stage F03: Model Evidence Parity, Self-Contained Forecast Fields, and Dispatch."""

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(".").resolve()))

from rr_pressure.config import PipelineConfig
from rr_pressure.forecast import fit_player_forecast, Z_25
from rr_pressure.challengers import ChallengerD_WorkloadDistributional, ChallengerE_DirectQuantileBoosted

REVIEW_DIR = Path("artifacts_release_review")
RAW_DIR = Path("6af3166e7b922_data_pack")


def test_challenger_d_self_contained_forecast_fields():
    """Verify Challenger D produces model-implied mean and 80% CI without borrowing B0."""
    p_dim = pd.read_csv(REVIEW_DIR / "player_dimension.csv")
    bat_match_df = pd.read_csv(REVIEW_DIR / "match_player_batting_impact.csv")
    
    chal_d = ChallengerD_WorkloadDistributional().fit(
        bat_match_df[bat_match_df["fold"].isin(["TRAIN_2022_2024", "VAL_2025"])], p_dim, "batting"
    )
    pids = np.array([1001, 1002, 1003])
    workloads = np.full(3, 12.0)
    
    q25 = chal_d.predict_quantile(pids, workloads, quantile=0.25)
    mean = chal_d.predict_mean(pids)
    q10, q90 = chal_d.predict_ci_80(pids, workloads)
    
    # Monotonicity: q10 < q25 < mean < q90
    assert (q10 < q25).all()
    assert (q25 < mean).all()
    assert (mean < q90).all()


def test_challenger_e_self_contained_forecast_fields():
    """Verify Challenger E produces model-implied mean and 80% CI without borrowing B0."""
    p_dim = pd.read_csv(REVIEW_DIR / "player_dimension.csv")
    bat_match_df = pd.read_csv(REVIEW_DIR / "match_player_batting_impact.csv")
    bat_refit, _ = fit_player_forecast(bat_match_df, p_dim, "batting", seed=2027)
    
    chal_e = ChallengerE_DirectQuantileBoosted(seed=2027).fit(
        bat_match_df[bat_match_df["fold"].isin(["TRAIN_2022_2024", "VAL_2025"])], bat_refit, "batting"
    )
    sample = bat_refit.head(10).copy()
    
    q25 = chal_e.predict(sample, bat_refit)
    mean = chal_e.predict_mean(sample, bat_refit)
    q10, q90 = chal_e.predict_ci_80(sample, bat_refit)
    
    assert (q10 <= q25).all()
    assert (q10 <= q90).all()
    assert len(q25) == 10
    assert len(mean) == 10


def test_validation_cohort_and_metric_parity():
    """Verify all 6 candidates are evaluated on the exact identical set of opportunities in validation."""
    comp_path = REVIEW_DIR / "model_comparison.json"
    with open(comp_path, "r", encoding="utf-8") as f:
        comp = json.load(f)
        
    val_bat = comp["validation_2025_results"]["batting"]
    val_bowl = comp["validation_2025_results"]["bowling"]
    
    expected_opps_bat = 655
    expected_opps_bowl = 783
    
    models = [
        "candidate_A_baseline",
        "candidate_B_statistical",
        "candidate_C_boosted",
        "ablation_B0_no_pressure",
        "challenger_D_workload",
        "challenger_E_quantile_boosted",
    ]
    
    for m in models:
        assert val_bat[m]["opportunity_count"] == expected_opps_bat, f"{m} batting opp count mismatch!"
        assert val_bowl[m]["opportunity_count"] == expected_opps_bowl, f"{m} bowling opp count mismatch!"
        # Coverage must be valid nominal coverage
        assert 0.15 <= val_bat[m]["coverage_q25"] <= 0.35, f"{m} batting coverage outside [0.15, 0.35]"
        assert 0.15 <= val_bowl[m]["coverage_q25"] <= 0.35, f"{m} bowling coverage outside [0.15, 0.35]"


def test_excluded_fixture_13612_not_in_examples(tmp_path):
    """Verify excluded fixture 13612 is not used as a modeled example without mutating archived artifacts_release_review."""
    import shutil
    from rr_pressure.exports import generate_match_examples

    for fname in ("delivery_impact_ledger.csv", "model_diagnostics.json", "rr_shortlist.csv"):
        src = REVIEW_DIR / fname
        if src.exists():
            shutil.copyfile(src, tmp_path / fname)

    json_path = generate_match_examples(tmp_path)
    with open(json_path, "r", encoding="utf-8") as f:
        examples = json.load(f)

    # Check both freshly generated scratch examples and untouched frozen archive
    with open(REVIEW_DIR / "match_examples.json", "r", encoding="utf-8") as f:
        archived_examples = json.load(f)

    # Fixture 13612 was excluded due to revised overs; Sheldon Cottrell in fixture 13511 is the audited anchor
    for dataset in (examples, archived_examples):
        items = dataset["examples"]
        for ex in items:
            assert ex["match_id"] != 13612, "Excluded fixture 13612 found in match examples!"
        assert any(ex["match_id"] == 13511 for ex in items), "Audited fixture 13511 anchor missing from match examples!"
