"""Regression and validation tests for Stage 03 Exploratory Data Analysis."""

import json
from pathlib import Path
import pytest

ARTIFACTS_DIR = Path("artifacts_revalidated") if Path("artifacts_revalidated").exists() else Path("artifacts")


def test_eda_summary_contents():
    summary_path = ARTIFACTS_DIR / "eda_summary.json"
    assert summary_path.exists(), "eda_summary.json does not exist"
    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "tier_phase_statistics" in data
    assert "impact_era_statistics" in data
    assert "feasibility_matrix" in data
    assert len(data["tier_phase_statistics"]) > 0


def test_feature_dictionary_leakage_controls():
    feat_path = ARTIFACTS_DIR / "feature_dictionary.json"
    assert feat_path.exists(), "feature_dictionary.json does not exist"
    with open(feat_path, "r", encoding="utf-8") as f:
        feats = json.load(f)
    
    types = {f["name"]: f["type"] for f in feats}
    assert types.get("bowl_speed") == "FORBIDDEN_FUTURE_LEAKAGE"
    assert types.get("stroke") == "FORBIDDEN_FUTURE_LEAKAGE"
    assert types.get("pre_balls_remaining") == "PRE_BALL_PREDICTOR"
    assert types.get("pre_wickets_in_hand") == "PRE_BALL_PREDICTOR"


def test_source_coverage_decision():
    cov_path = ARTIFACTS_DIR / "source_coverage_decision.json"
    assert cov_path.exists(), "source_coverage_decision.json does not exist"
    with open(cov_path, "r", encoding="utf-8") as f:
        cov = json.load(f)
    assert "selected_route" in cov
    assert "recommended_evidence_floor" in cov


def test_eda_plot_generated():
    plot_path = ARTIFACTS_DIR / "eda_distributions.png"
    assert plot_path.exists(), "eda_distributions.png was not generated"
    assert plot_path.stat().st_size > 1000, "Plot file size is too small"
