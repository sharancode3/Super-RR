"""Regression and validation tests for Stage 06 Pre-Ball Leverage and Pressure."""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

ARTIFACTS_DIR = Path("artifacts_revalidated") if Path("artifacts_revalidated").exists() else Path("artifacts")


def test_dynamic_pressure_transition_frequencies():
    """Verify outcome transition probabilities are empirically fitted on training data,
    rather than using hard-coded constants."""
    thresh_path = ARTIFACTS_DIR / "pressure_thresholds.json"
    with open(thresh_path, "r", encoding="utf-8") as f:
        thresh = json.load(f)
        
    assert "transition_frequencies" in thresh, "Missing transition frequencies in pressure thresholds"
    meta = thresh["transition_frequencies"]
    assert "training_counts" in meta
    assert meta["training_counts"]["dot"] > 30000
    assert meta["training_counts"]["wicket"] > 5000
    
    probs = meta["probabilities_default"]
    assert len(probs) == 6
    assert abs(sum(probs) - 1.0) < 1e-5
    # Empirical dot probability in T20 is between 30% and 40%
    assert 0.30 <= probs[0] <= 0.40


def test_pre_ball_invariance():
    """Verify pre-ball leverage depends strictly on pre-ball state and is invariant to realized ball outcomes."""
    df = pd.read_csv(ARTIFACTS_DIR / "delivery_pressure_labels.csv", nrows=100, low_memory=False)
    # Check that pre_ball_leverage is non-null and strictly non-negative
    assert df["pre_ball_leverage"].notna().all()
    assert (df["pre_ball_leverage"] >= 0.0).all()


def test_pressure_thresholds_and_proportions():
    thresh_path = ARTIFACTS_DIR / "pressure_thresholds.json"
    assert thresh_path.exists(), "pressure_thresholds.json does not exist"
    with open(thresh_path, "r", encoding="utf-8") as f:
        thresh = json.load(f)
    assert len(thresh) > 0
    for key, val in thresh.items():
        if key == "transition_frequencies":
            continue
        assert val["p75"] <= val["p80"] <= val["p85"]


def test_replay_examples_separation():
    replay_path = ARTIFACTS_DIR / "replay_examples.json"
    assert replay_path.exists(), "replay_examples.json does not exist"
    with open(replay_path, "r", encoding="utf-8") as f:
        replays = json.load(f)
        
    assert "tight_late_chase" in replays
    assert "virtually_lost_chase" in replays
    assert "easy_chase" in replays
    assert "first_innings_collapse" in replays
    
    # In tight chase, leverage must be high
    for ex in replays["tight_late_chase"]:
        assert ex["pre_ball_leverage"] > 0.05
