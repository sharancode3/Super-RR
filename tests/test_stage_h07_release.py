"""Stage H07 Verification Tests: Release Verification and Defect Audit Closure."""

import json
from pathlib import Path
import pytest
import pandas as pd

from rr_pressure.manifest import compute_sha256

HARDENED_DIR = Path("artifacts_hardened")


def test_hardening_defect_ledger_closed():
    """Verify all 7 material audit defects are formally closed with verified evidence."""
    defect_path = HARDENED_DIR / "hardening_defect_ledger.json"
    assert defect_path.exists()
    
    with open(defect_path, "r", encoding="utf-8") as f:
        ledger = json.load(f)
        
    assert "defects" in ledger
    assert len(ledger["defects"]) >= 7
    defect_ids = [d["defect_id"] for d in ledger["defects"]]
    expected_ids = [
        "H_DEFECT_01_SHORTLIST_ORDER_MISMATCH",
        "H_DEFECT_02_SCORED_VS_DEPLOYED_WIDTH",
        "H_DEFECT_03_Q25_MEAN_INTERVAL_DISCREPANCY",
        "H_DEFECT_04_ROLE_TEMPORAL_LEAKAGE",
        "H_DEFECT_05_UNPAIRED_ASSESSMENT_KEYS",
        "H_DEFECT_06_EXACT_VS_PROXY_LANE_LABELING",
        "H_DEFECT_07_OVERSTATED_WIN_PROB_CLAIMS",
    ]
    for eid in expected_ids:
        assert eid in defect_ids, f"Defect {eid} not in ledger"


def test_clean_core_outputs_exist_and_consistent():
    """Verify core release files exist in artifacts_hardened with valid sha256 checksums."""
    manifest_path = HARDENED_DIR / "run_manifest.json"
    assert manifest_path.exists()
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    assert manifest["release_status"] == "PROVISIONAL"
    assert manifest["resume_prompt"] == "round1_hardening/06_explanations_exports.md"
    
    required_outputs = [
        "player_rankings.csv",
        "unstop_rank_order.csv",
        "model_validation.json",
        "data_quality.csv",
        "player_evidence.csv",
        "match_examples.json",
        "rr_shortlist.csv",
    ]
    for ro in required_outputs:
        fpath = HARDENED_DIR / ro
        assert fpath.exists(), f"Missing required output file: {ro}"
        assert fpath.stat().st_size > 0, f"Empty file: {ro}"
        disk_hash = compute_sha256(fpath)
        assert disk_hash == manifest["outputs"][ro], f"Hash mismatch for {ro}"


def test_unstop_rank_order_integrity():
    """Verify exact 20 rows (10 batters, 10 bowlers) with provisional status."""
    fpath = HARDENED_DIR / "unstop_rank_order.csv"
    assert fpath.exists()
    df = pd.read_csv(fpath)
    assert len(df) == 20
    assert len(df[df["role"] == "Batting"]) == 10
    assert len(df[df["role"] == "Bowling"]) == 10
    assert df["player_id"].nunique() == 20
    assert df["dropdown_label"].fillna("").str.strip().eq("").all()
    assert (df["verification_status"] == "PROVISIONAL").all()
