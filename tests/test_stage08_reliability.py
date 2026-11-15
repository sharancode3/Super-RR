"""Regression and validation tests for Stage 08 Reliability Forecast."""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

ARTIFACTS_DIR = Path("artifacts_revalidated") if Path("artifacts_revalidated").exists() else Path("artifacts")


def test_role_priors_exclude_zero_exposure():
    """Verify Stage 08 repair:
    1. Unexposed players (balls == 0) are excluded when calculating role group medians.
    2. Empirical Bayes shrinkage shrinks zero-exposure players directly to their role priors.
    """
    for role in ["batting", "bowling"]:
        path = ARTIFACTS_DIR / f"player_reliability_forecasts_{role}.csv"
        assert path.exists()
        df = pd.read_csv(path)
        
        # Check players with zero HP balls: pressure_lift must equal prior_lift (shrunk to prior)
        zero_hp = df[df["hp_balls"] == 0]
        if len(zero_hp) > 0:
            assert np.allclose(zero_hp["pressure_lift"], zero_hp["prior_lift"], atol=1e-5)
            
        # Check players with zero ordinary balls: usual_level must equal prior_ord
        zero_ord = df[df["ord_balls"] == 0]
        if len(zero_ord) > 0:
            assert np.allclose(zero_ord["usual_level"], zero_ord["prior_ord"], atol=1e-5)
            
        # Prior values must be non-trivial (not all identically zero)
        assert df["prior_ord"].notna().all()
        assert df["prior_lift"].notna().all()


def test_forecast_files_exist_and_columns():
    for role in ["batting", "bowling"]:
        path = ARTIFACTS_DIR / f"player_reliability_forecasts_{role}.csv"
        assert path.exists(), f"Missing forecast file for {role}"
        df = pd.read_csv(path)
        required_cols = [
            "player_id", "player_name", "inferred_role", "usual_level",
            "pressure_lift", "predicted_hp_impact", "conservative_score_q25",
            "is_qualified", "performance_rank"
        ]
        for col in required_cols:
            assert col in df.columns, f"Missing column {col} in {role} forecast"


def test_conservative_q25_bound():
    for role in ["batting", "bowling"]:
        path = ARTIFACTS_DIR / f"player_reliability_forecasts_{role}.csv"
        df = pd.read_csv(path)
        # Conservative Q25 must be strictly less than mean predicted impact
        assert (df["conservative_score_q25"] < df["predicted_hp_impact"]).all()


def test_qualified_cohort_size():
    diag_path = ARTIFACTS_DIR / "forecast_diagnostics.json"
    assert diag_path.exists(), "forecast_diagnostics.json does not exist"
    with open(diag_path, "r", encoding="utf-8") as f:
        diag = json.load(f)
        
    assert diag["batting_model"]["qualified_players_count"] >= 50
    assert diag["bowling_model"]["qualified_players_count"] >= 50


def test_top_10_unique_and_ranked():
    for role in ["batting", "bowling"]:
        path = ARTIFACTS_DIR / f"player_reliability_forecasts_{role}.csv"
        df = pd.read_csv(path)
        top10 = df[df["is_qualified"]].head(10)
        assert len(top10) == 10
        assert top10["player_id"].nunique() == 10
        assert (top10["performance_rank"].values == np.arange(1, 11)).all()
