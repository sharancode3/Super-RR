"""Regression and validation tests for Stage 05 Match-State Models."""

import json
from pathlib import Path
import pytest

ARTIFACTS_DIR = Path("artifacts_revalidated") if Path("artifacts_revalidated").exists() else Path("artifacts")


def test_float_brier_baseline():
    """Verify constant Brier baseline uses float dtype and correctly evaluates around ~0.251,
    rather than truncating to integer 0 (which produced artificial 0.476 / 0.523)."""
    diag_path = ARTIFACTS_DIR / "model_diagnostics.json"
    with open(diag_path, "r", encoding="utf-8") as f:
        diag = json.load(f)
    
    inn1_const = diag["innings1_validation_2025"]["constant_brier"]
    inn2_const = diag["innings2_validation_2025"]["constant_brier"]
    
    # Constant baseline for ~50% prevalence binary outcome is ~0.25, NOT >0.45
    assert 0.24 <= inn1_const <= 0.26, f"Corrupted constant Brier baseline for Inn 1: {inn1_const}"
    assert 0.24 <= inn2_const <= 0.26, f"Corrupted constant Brier baseline for Inn 2: {inn2_const}"
    
    # Verify logistic regression beats constant baseline
    assert diag["innings1_validation_2025"]["logistic_brier"] < inn1_const
    assert diag["innings2_validation_2025"]["logistic_brier"] < inn2_const


def test_model_diagnostics_brier_improvement():
    diag_path = ARTIFACTS_DIR / "model_diagnostics.json"
    assert diag_path.exists(), "model_diagnostics.json does not exist"
    with open(diag_path, "r", encoding="utf-8") as f:
        diag = json.load(f)
        
    # Innings 1 checks
    inn1 = diag["innings1_validation_2025"]
    assert inn1["logistic_brier"] < inn1["constant_brier"]
    assert inn1["logistic_brier"] < 0.25, f"Inn 1 Brier too high: {inn1['logistic_brier']}"
    
    # Innings 2 checks
    inn2 = diag["innings2_validation_2025"]
    assert inn2["logistic_brier"] < inn2["constant_brier"]
    assert inn2["logistic_brier"] < 0.15, f"Inn 2 Brier too high: {inn2['logistic_brier']}"
    assert inn2["monotonicity_preserved"] is True


def test_projected_remaining_runs_model():
    proj_path = ARTIFACTS_DIR / "projected_score_model.json"
    assert proj_path.exists(), "projected_score_model.json does not exist"
    with open(proj_path, "r", encoding="utf-8") as f:
        proj = json.load(f)
        
    assert proj["validation_r2"] > 0.70, f"Remaining runs R2 too low: {proj['validation_r2']}"
    # Marginal wicket cost must be positive and realistic (3 to 12 runs)
    w_mid = proj["marginal_wicket_value_mid_innings"]
    assert 3.0 <= w_mid <= 12.0, f"Unrealistic marginal wicket cost: {w_mid}"
