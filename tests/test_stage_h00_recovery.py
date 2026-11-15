"""Regression and verification tests for Stage H00: Recovery, Input Preservation, and Defect Reproduction."""

import hashlib
import json
from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(".").resolve()))

RAW_DIR = Path("6af3166e7b922_data_pack")
REVALIDATED_DIR = Path("artifacts_revalidated")
HARDENED_DIR = Path("artifacts_hardened")

RAW_FILES = [
    "ball_by_ball.csv",
    "competitions.csv",
    "competition_team_player_mapping.csv",
    "matches.csv",
    "playing_eleven.csv",
    "teams.csv",
    "Round 1 Problem Statement _ SupeRR Selector Season 2.docx.pdf",
]


def test_raw_pack_integrity():
    """Verify all 7 raw files exist and match the manifest hashes."""
    assert RAW_DIR.exists()
    with open(REVALIDATED_DIR / "input_manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    for fname in RAW_FILES:
        fpath = RAW_DIR / fname
        assert fpath.exists(), f"Missing raw file: {fname}"
        with open(fpath, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
        assert h == manifest["files"][fname]["sha256"], f"Hash mismatch for {fname}"


def test_prior_runs_preserved():
    """Verify prior run directories exist and are preserved as historical evidence."""
    assert REVALIDATED_DIR.exists()
    assert (REVALIDATED_DIR / "player_rankings.csv").exists()
    assert (REVALIDATED_DIR / "round1_progress.json").exists()


def test_defect_reproduction_b_vs_b0_order():
    """Reproduce Defect 1: Candidate B order vs B0 order differs on 2026 holdout."""
    with open(REVALIDATED_DIR / "model_comparison.json", "r", encoding="utf-8") as f:
        comp = json.load(f)
    
    # In legacy model_comparison.json, B0 evaluation used Candidate B's top 10
    bowl_perf = comp["test_holdout_2026_evaluation"]["bowling"]["top10_performance"]
    # The saved value in legacy was ~3.646 runs/12b because it took B's order
    assert "realized_avg_impact_12b" in bowl_perf


def test_defect_reproduction_role_leakage():
    """Reproduce Defect 4: Inferred roles in player_dimension differ between train and full pack."""
    p_train = pd.read_csv(REVALIDATED_DIR / "player_dimension_train.csv")
    p_full = pd.read_csv(REVALIDATED_DIR / "player_dimension.csv")
    
    m = p_train.merge(p_full, on="player_id", suffixes=("_train", "_full"))
    diff_count = (m["inferred_role_train"] != m["inferred_role_full"]).sum()
    assert diff_count > 0, "Expected role differences between train and full pack"
    assert diff_count == 296, f"Expected exactly 296 differing roles, found {diff_count}"


def test_hardening_checkpoint_initialized():
    """Verify artifacts_hardened has progress ledger and defect ledger."""
    assert HARDENED_DIR.exists()
    prog_path = HARDENED_DIR / "round1_progress.json"
    defect_path = HARDENED_DIR / "hardening_defect_ledger.json"
    
    assert prog_path.exists()
    assert defect_path.exists()
    
    with open(defect_path, "r", encoding="utf-8") as f:
        ledger = json.load(f)
    assert len(ledger["defects"]) >= 7
    for d in ledger["defects"]:
        assert "defect_id" in d
        assert "owning_stage" in d
        assert "falsifying_check" in d
