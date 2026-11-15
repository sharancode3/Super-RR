"""Stage I07 Verification Tests: Release Verification, Rebuild Parity, and Defect Closure."""

import json
from pathlib import Path
import pytest
import pandas as pd

from rr_pressure.manifest import compute_sha256

REVIEW_DIR = Path("artifacts_release_review")
TEST_DIR = Path("test_artifacts_release_review")


def test_release_defect_ledger_closed():
    """Verify all 8 material audit defects are formally cataloged in release_defect_ledger.json."""
    defect_path = REVIEW_DIR / "release_defect_ledger.json"
    assert defect_path.exists()
    
    with open(defect_path, "r", encoding="utf-8") as f:
        ledger = json.load(f)
        
    assert "defects" in ledger
    assert len(ledger["defects"]) == 8
    defect_ids = [d["id"] for d in ledger["defects"]]
    expected_ids = [
        "REL_DEFECT_01_WORKLOAD_LEAKAGE",
        "REL_DEFECT_02_IN_SAMPLE_CONTAMINATION",
        "REL_DEFECT_03_COHERENCE_AND_DISPATCH",
        "REL_DEFECT_04_UNMODELLED_EXAMPLE_PROVENANCE",
        "REL_DEFECT_05_EXCLUDED_DELIVERIES_LABELED_HP",
        "REL_DEFECT_06_UNALIGNED_ROBUSTNESS_ESTIMATOR",
        "REL_DEFECT_07_POOLED_VS_IPL_EVIDENCE_FOR_CHALLENGER",
        "REL_DEFECT_08_HASH_COLLISION_AND_STATIC_TEXT",
    ]
    for eid in expected_ids:
        assert eid in defect_ids, f"Defect {eid} not in ledger"


def test_clean_rebuild_deterministic_parity():
    """Verify 100% bit-for-bit checksum equality between artifacts_release_review and test_artifacts_release_review."""
    core_files = [
        "player_rankings.csv",
        "unstop_rank_order.csv",
        "model_validation.json",
        "data_quality.csv",
        "player_evidence.csv",
        "match_examples.json",
        "rr_shortlist.csv",
        "robustness_report.json",
        "model_comparison.json",
    ]
    for fname in core_files:
        f1 = REVIEW_DIR / fname
        f2 = TEST_DIR / fname
        assert f1.exists(), f"Missing {fname} in REVIEW_DIR"
        assert f2.exists(), f"Missing {fname} in TEST_DIR"
        h1 = compute_sha256(f1)
        h2 = compute_sha256(f2)
        assert h1 == h2, f"Deterministic rebuild hash mismatch for {fname}: {h1} vs {h2}"


def test_unstop_rank_order_integrity():
    """Verify exact 20 rows (10 batters, 10 bowlers) with provisional status."""
    fpath = REVIEW_DIR / "unstop_rank_order.csv"
    assert fpath.exists()
    df = pd.read_csv(fpath)
    assert len(df) == 20
    assert len(df[df["role"] == "Batting"]) == 10
    assert len(df[df["role"] == "Bowling"]) == 10
    assert df["player_id"].nunique() == 20
    assert df["dropdown_label"].fillna("").str.strip().eq("").all()
    assert (df["verification_status"] == "PROVISIONAL").all()


def test_manifest_integrity():
    """Verify manifest output hashes match files on disk."""
    manifest_path = REVIEW_DIR / "run_manifest.json"
    assert manifest_path.exists()
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["release_status"] == "PROVISIONAL"
    for ro, exp_hash in manifest["outputs"].items():
        fpath = REVIEW_DIR / ro
        assert fpath.exists()
        assert compute_sha256(fpath) == exp_hash
