"""Stage F00 Verification Tests: Reproduce and Preserve."""

import json
from pathlib import Path
import pandas as pd
import pytest
from rr_pressure.manifest import compute_sha256

RAW_DIR = Path("6af3166e7b922_data_pack")
REVIEW_DIR = Path("artifacts_release_review")
HARDENED_DIR = Path("artifacts_hardened")

EXPECTED_RAW_HASHES = {
    "ball_by_ball.csv": "a3926f49d2c684dca2a5d2de535a02c5ee46ea654ca1e79dd31c69e7544e9889",
    "competitions.csv": "507ceb7189f972d4e4f299ddcfc97f3c3247af1913f6291106f161fa8353fd9b",
    "competition_team_player_mapping.csv": "1ded4e42a933618572d6e2c3a521c3257eb1844fab4456d567d77cbb2d3bbb12",
    "matches.csv": "bb100ab84b8b9a15160c1f2315cf675210131a30e779ec5079fd5403dcf56eef",
    "playing_eleven.csv": "7517c73722a28d5d61c808ccf0cbed315a8780586d02e946eb9a7f5daf011c27",
    "Round 1 Problem Statement _ SupeRR Selector Season 2.docx.pdf": "8f7965c616d4a64b779e770a6b2c17dde6a2d6ccbf7de12a58b04db792162489",
    "teams.csv": "a65e5922a9b3bf49247b24fc9471782e700efb31f8dcc5042923238b87c50a5d",
}


def test_raw_input_hashes_immutable():
    """Verify all 7 raw data pack files match their immutable SHA-256 checksums."""
    for fname, exp_hash in EXPECTED_RAW_HASHES.items():
        fpath = RAW_DIR / fname
        assert fpath.exists(), f"Missing raw file: {fname}"
        actual_hash = compute_sha256(fpath)
        assert actual_hash == exp_hash, f"Hash mismatch for {fname}: {actual_hash} vs {exp_hash}"


def test_defect_ledger_contains_all_material_issues():
    """Verify release_defect_ledger.json documents the 8 material issues from the audit."""
    ledger_path = REVIEW_DIR / "release_defect_ledger.json"
    assert ledger_path.exists()
    with open(ledger_path, "r", encoding="utf-8") as f:
        ledger = json.load(f)
        
    defect_ids = [d["id"] for d in ledger["defects"]]
    assert "REL_DEFECT_01_WORKLOAD_LEAKAGE" in defect_ids
    assert "REL_DEFECT_02_IN_SAMPLE_CONTAMINATION" in defect_ids
    assert "REL_DEFECT_03_COHERENCE_AND_DISPATCH" in defect_ids
    assert "REL_DEFECT_04_UNMODELLED_EXAMPLE_PROVENANCE" in defect_ids
    assert "REL_DEFECT_05_EXCLUDED_DELIVERIES_LABELED_HP" in defect_ids
    assert "REL_DEFECT_06_UNALIGNED_ROBUSTNESS_ESTIMATOR" in defect_ids
    assert "REL_DEFECT_07_POOLED_VS_IPL_EVIDENCE_FOR_CHALLENGER" in defect_ids
    assert "REL_DEFECT_08_HASH_COLLISION_AND_STATIC_TEXT" in defect_ids


def test_reproduce_hazlewood_unmodelled_fixture():
    """Verify that Josh Hazlewood example came from excluded match 13612."""
    excl = pd.read_csv("artifacts_release_review/exclusions_ledger.csv")
    assert 13612 in excl["match_id"].values
    
    with open(Path("artifacts_revalidated") / "match_examples.json", "r", encoding="utf-8") as f:
        mex = json.load(f)
    hazlewood = next((ex for ex in mex["examples"] if "Hazlewood" in ex.get("player_name", "")), None)
    assert hazlewood is not None
    assert hazlewood["match_id"] == 13612
