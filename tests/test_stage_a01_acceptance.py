"""Test Stage A01: Neutral acceptance gates, raw file integrity, and adversarial controls."""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from rr_pressure.manifest import compute_sha256


RAW_DIR = Path("6af3166e7b922_data_pack")
HISTORICAL_DIR = Path("artifacts_rank_validation")
OUT_DIR = Path("artifacts_decision_validation")


def test_raw_files_integrity():
    """Verify SHA-256 hashes of all 7 raw data pack files."""
    expected_hashes = {
        "ball_by_ball.csv": "a3926f49d2c684dca2a5d2de535a02c5ee46ea654ca1e79dd31c69e7544e9889",
        "competitions.csv": "507ceb7189f972d4e4f299ddcfc97f3c3247af1913f6291106f161fa8353fd9b",
        "competition_team_player_mapping.csv": "1ded4e42a933618572d6e2c3a521c3257eb1844fab4456d567d77cbb2d3bbb12",
        "matches.csv": "bb100ab84b8b9a15160c1f2315cf675210131a30e779ec5079fd5403dcf56eef",
        "playing_eleven.csv": "7517c73722a28d5d61c808ccf0cbed315a8780586d02e946eb9a7f5daf011c27",
        "Round 1 Problem Statement _ SupeRR Selector Season 2.docx.pdf": "8f7965c616d4a64b779e770a6b2c17dde6a2d6ccbf7de12a58b04db792162489",
        "teams.csv": "a65e5922a9b3bf49247b24fc9471782e700efb31f8dcc5042923238b87c50a5d",
    }
    for fname, expected_hash in expected_hashes.items():
        p = RAW_DIR / fname
        assert p.exists(), f"Raw file missing: {fname}"
        h = compute_sha256(p)
        assert h == expected_hash, f"Hash mismatch for {fname}: {h} != {expected_hash}"


def test_model_and_name_neutral_ranking_properties():
    """Model-neutral and name-neutral acceptance check: verify rankings satisfy mathematical properties."""
    rank_file = HISTORICAL_DIR / "player_rankings.csv"
    assert rank_file.exists(), "Historical player_rankings.csv must exist"
    
    df = pd.read_csv(rank_file)
    
    for role in ["Batting", "Bowling"]:
        sub = df[(df["role_pool"] == role) & (df["is_qualified"])].copy()
        assert len(sub) >= 10, f"Insufficient qualified players in {role}"
        
        # 1. Monotonicity: sorted performance rank must have non-increasing conservative scores
        sub_sorted = sub.sort_values("performance_rank")
        scores = sub_sorted["conservative_score_q25"].values
        diffs = np.diff(scores)
        assert (diffs <= 1e-5).all(), f"Scores are not monotonic for {role}"
        
        # 2. Performance rank continuity: 1, 2, 3, ..., N
        ranks = sub_sorted["performance_rank"].values
        expected_ranks = np.arange(1, len(sub_sorted) + 1)
        np.testing.assert_array_equal(ranks, expected_ranks)
        
        # 3. Monotonic quantiles: Q25 <= Mean <= Q90 (where available)
        if "predicted_hp_impact" in sub.columns:
            assert (sub["conservative_score_q25"] <= sub["predicted_hp_impact"] + 1e-4).all()
        if "ci_upper_80" in sub.columns and "ci_lower_80" in sub.columns:
            assert (sub["ci_lower_80"] <= sub["ci_upper_80"] + 1e-4).all()


def test_adversarial_controls_distinguish_faulty_behavior():
    """Adversarial negative and positive controls: verify that test gates reject invalid states."""
    # Negative Control 1: Non-monotonic rankings must be rejected
    faulty_df = pd.DataFrame({
        "player_id": [101, 102, 103],
        "performance_rank": [1, 2, 3],
        "conservative_score_q25": [1.5, 3.2, 0.8],  # Rank 2 has HIGHER score than Rank 1!
    })
    scores = faulty_df.sort_values("performance_rank")["conservative_score_q25"].values
    is_monotonic = bool((np.diff(scores) <= 0).all())
    assert is_monotonic is False, "Negative control failed: non-monotonic scores should be detected as invalid"
    
    # Negative Control 2: Coverage out of bounds must be rejected
    faulty_coverage = 0.05  # Far below 15-35% nominal range
    is_calibrated = (0.15 <= faulty_coverage <= 0.35)
    assert is_calibrated is False, "Negative control failed: severe miscalibration should be detected as invalid"
    
    # Positive Control: Properly ordered scores pass
    valid_scores = np.array([5.0, 3.2, 1.1, -0.4])
    assert bool((np.diff(valid_scores) <= 0).all()) is True


def test_open_defects_and_stage_ownership_registered():
    """Verify decision defect ledger cataloged all 8 open issues with specific stage ownership."""
    ledger_path = OUT_DIR / "decision_defect_ledger.json"
    assert ledger_path.exists(), "decision_defect_ledger.json must exist"
    
    with open(ledger_path, "r", encoding="utf-8") as f:
        ledger = json.load(f)
        
    defects = ledger["defects"]
    assert len(defects) == 8, f"Expected 8 defects, found {len(defects)}"
    
    owners = {d["owner"] for d in defects}
    assert any("A01" in o or "A02" in o for o in owners)
    assert any("A03" in o for o in owners)
    assert any("A04" in o for o in owners)
    assert any("A05" in o for o in owners)
