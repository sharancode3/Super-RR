"""Regression and validation tests for Stage 12 Terminal Exports and Evidence Files."""

import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(".").resolve()))

import pandas as pd
import pytest

from rr_pressure.manifest import compute_sha256

ARTIFACTS_DIR = Path("artifacts_revalidated") if Path("artifacts_revalidated").exists() else Path("artifacts")

REQUIRED_EXPORTS = [
    "player_rankings.csv",
    "unstop_rank_order.csv",
    "model_validation.json",
    "data_quality.csv",
    "player_evidence.csv",
    "match_examples.json",
    "rr_shortlist.csv",
    "run_manifest.json",
]


def test_all_exports_exist():
    for fname in REQUIRED_EXPORTS:
        fpath = ARTIFACTS_DIR / fname
        assert fpath.exists(), f"Missing required export file: {fname}"


def test_unstop_rank_order_contract():
    df = pd.read_csv(ARTIFACTS_DIR / "unstop_rank_order.csv")
    assert len(df) == 20, f"Expected exactly 20 rows in unstop_rank_order.csv, found {len(df)}"
    
    bat = df[df["role"] == "Batting"]
    bowl = df[df["role"] == "Bowling"]
    
    assert len(bat) == 10
    assert len(bowl) == 10
    assert bat["player_id"].nunique() == 10
    assert bowl["player_id"].nunique() == 10
    assert (bat["rank"].values == range(1, 11)).all()
    assert (bowl["rank"].values == range(1, 11)).all()
    # Unverified dropdown labels must remain blank per rules contract
    assert df["dropdown_label"].fillna("").eq("").all()
    assert (df["verification_status"] == "PROVISIONAL").all()


def test_data_quality_reconciliation():
    dq = pd.read_csv(ARTIFACTS_DIR / "data_quality.csv")
    assert len(dq) == 883, f"Expected 883 reconciled fixtures, found {len(dq)}"
    assert (dq["cohort_status"] == "EXCLUDED").sum() == 77
    assert (dq["cohort_status"] == "INCLUDED_STANDARD_COHORT").sum() == 806


def test_match_examples_provenance():
    with open(ARTIFACTS_DIR / "match_examples.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "examples" in data
    assert len(data["examples"]) >= 3
    for ex in data["examples"]:
        assert "provenance_note" in ex
        assert "pressure_classification" in ex


def test_replays_match_ledger_regression():
    """Verify that match examples match the exact scoreboard state from delivery_impact_ledger."""
    with open(ARTIFACTS_DIR / "match_examples.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    ex_map = {ex.get("match_id"): ex for ex in data["examples"] if "match_id" in ex}
    
    # Klaasen match 15407: real ledger pre_balls_remaining is 65 (not 58)
    assert 15407 in ex_map
    assert ex_map[15407]["pre_ball_scoreboard"]["balls_remaining"] == 65
    assert ex_map[15407]["pre_ball_scoreboard"]["runs_off_bat"] == 53
    assert ex_map[15407]["pre_ball_scoreboard"]["wickets_lost"] == 3
    
    # Hazlewood match 13612: real ledger pre_balls_remaining is 114 (not 107)
    assert 13612 in ex_map
    assert ex_map[13612]["pre_ball_scoreboard"]["balls_remaining"] == 114
    
    # Brandon King match 13511: real ledger pre_balls_remaining is 30 (not 23)
    assert 13511 in ex_map
    assert ex_map[13511]["pre_ball_scoreboard"]["balls_remaining"] == 30


def test_run_manifest_integrity():
    with open(ARTIFACTS_DIR / "run_manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    assert manifest["release_status"] == "PROVISIONAL"
    with open(ARTIFACTS_DIR / "model_comparison.json", "r", encoding="utf-8") as f:
        comp = json.load(f)
    expected_model = comp.get("pre_holdout_decision", {}).get("chosen_model", "Selected Production Model")
    assert manifest["selected_model"] == expected_model
    assert manifest["resume_prompt"] == "round1_prompts/11_rankings_and_eligibility.md"
    
    # Verify hash integrity of all exports
    for fname, expected_hash in manifest["outputs"].items():
        actual_hash = compute_sha256(ARTIFACTS_DIR / fname)
        assert actual_hash == expected_hash, f"Hash mismatch for {fname}"
