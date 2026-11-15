"""Stage I06 Verification Tests: Shortlist Integrity, Explanations, and Artifact Manifest."""

import json
from pathlib import Path
import pytest
import pandas as pd

from rr_pressure.manifest import compute_sha256

REVIEW_DIR = Path("artifacts_release_review")


def test_unstop_rank_order_specification():
    """Verify unstop_rank_order.csv meets all submission and audit requirements."""
    fpath = REVIEW_DIR / "unstop_rank_order.csv"
    assert fpath.exists()
    
    df = pd.read_csv(fpath)
    assert len(df) == 20
    
    # Check 10 batters and 10 bowlers
    batters = df[df["role"] == "Batting"]
    bowlers = df[df["role"] == "Bowling"]
    assert len(batters) == 10
    assert len(bowlers) == 10
    assert list(batters["rank"]) == list(range(1, 11))
    assert list(bowlers["rank"]) == list(range(1, 11))
    
    # Check that dropdown_label is empty string (blank) and verification_status is PROVISIONAL
    assert df["dropdown_label"].fillna("").str.len().max() == 0
    assert (df["verification_status"] == "PROVISIONAL").all()


def test_player_evidence_integrity():
    """Verify player_evidence.csv and rr_shortlist.csv contain complete, non-hallucinated evidence."""
    ev_path = REVIEW_DIR / "player_evidence.csv"
    assert ev_path.exists()
    ev_df = pd.read_csv(ev_path)
    assert len(ev_df) > 10000
    assert (ev_df["match_id"] > 0).all()
    assert (ev_df["player_id"] > 0).all()
    assert "hp_impact_12b" in ev_df.columns
    assert "ord_impact" in ev_df.columns
    
    shortlist_path = REVIEW_DIR / "rr_shortlist.csv"
    assert shortlist_path.exists()
    s_df = pd.read_csv(shortlist_path)
    assert len(s_df) == 30
    assert (s_df["player_id"] > 0).all()
    assert s_df["tactical_squad_role"].str.len().min() > 5
    assert s_df["rr_squad_fit_rationale"].str.len().min() > 10
    assert s_df["downside_or_uncertainty"].str.len().min() > 10
    assert s_df["measured_order_reason"].str.len().min() > 10


def test_model_validation_and_manifest():
    """Verify model_validation.json and run_manifest.json outputs and SHA-256 integrity."""
    val_path = REVIEW_DIR / "model_validation.json"
    assert val_path.exists()
    with open(val_path, "r", encoding="utf-8") as f:
        val_doc = json.load(f)
    assert "selected_model" in val_doc
    assert "evaluation_cohort" in val_doc
    assert "match_state_calibration" in val_doc
    assert "candidate_comparisons_2025_val" in val_doc
    assert "once_run_2026_holdout_evaluation" in val_doc
    
    manifest_path = REVIEW_DIR / "run_manifest.json"
    assert manifest_path.exists()
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["release_status"] == "PROVISIONAL"
    assert "outputs" in manifest
    
    # Verify hashes match on disk
    for fname, exp_hash in manifest["outputs"].items():
        disk_path = REVIEW_DIR / fname
        assert disk_path.exists(), f"Missing output file: {fname}"
        actual_hash = compute_sha256(disk_path)
        assert actual_hash == exp_hash, f"Hash mismatch for {fname}: {actual_hash} vs {exp_hash}"
