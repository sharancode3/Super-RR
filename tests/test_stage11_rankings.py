"""Regression and validation tests for Stage 11 Player Rankings and RR Shortlist."""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

ARTIFACTS_DIR = Path("artifacts_revalidated") if Path("artifacts_revalidated").exists() else Path("artifacts")


def test_refit_dispatches_selected_model_and_dropdown_labels_blank():
    """Verify Stage 11 repair:
    1. Full refit genuinely dispatches the winning model selected in Stage 09 (not hardcoded Candidate B).
    2. Unverified dropdown label fields remain blank ("") rather than injecting proxy names.
    3. Scouting rationales are dynamically derived from evidence rather than hardcoded text dicts.
    """
    comp_path = ARTIFACTS_DIR / "model_comparison.json"
    audit_path = ARTIFACTS_DIR / "rankings_audit.json"
    shortlist_path = ARTIFACTS_DIR / "rr_shortlist.csv"
    
    assert comp_path.exists()
    assert audit_path.exists()
    assert shortlist_path.exists()
    
    with open(comp_path, "r", encoding="utf-8") as f:
        comp = json.load(f)
    with open(audit_path, "r", encoding="utf-8") as f:
        audit = json.load(f)
        
    chosen_model = comp["pre_holdout_decision"]["chosen_model"]
    assert audit["model_used"] == chosen_model
    
    df = pd.read_csv(shortlist_path)
    # Dropdown label proxy must be blank/empty/NaN when unverified
    assert df["dropdown_label_proxy"].fillna("").eq("").all()
    assert (df["dropdown_verification_status"] == "PROVISIONAL").all()
    
    # Verify measured order reasons contain actual numbers
    for reason in df["measured_order_reason"]:
        assert "Ranked #" in reason
        assert "runs/12b" in reason


def test_ranking_and_shortlist_files_exist():
    assert (ARTIFACTS_DIR / "player_rankings.csv").exists()
    assert (ARTIFACTS_DIR / "rr_shortlist.csv").exists()
    assert (ARTIFACTS_DIR / "rankings_audit.json").exists()


def test_official_top10_completeness_and_uniqueness():
    df = pd.read_csv(ARTIFACTS_DIR / "rr_shortlist.csv")
    
    for role in ["Batting", "Bowling"]:
        sub = df[(df["role_pool"] == role) & (df["is_official_top10"])]
        assert len(sub) == 10, f"Expected 10 official picks for {role}, found {len(sub)}"
        assert sub["player_id"].nunique() == 10, f"Duplicate players found in {role} top 10"
        assert sub["player_name"].nunique() == 10, f"Duplicate names found in {role} top 10"
        assert (sub["performance_rank"].values == np.arange(1, 11)).all(), f"Ranks not contiguous 1-10 in {role}"
        
        # Verify required scouting fields are non-empty
        for col in ["tactical_squad_role", "rr_squad_fit_rationale", "measured_order_reason", "representative_performance", "downside_or_uncertainty"]:
            assert sub[col].notna().all(), f"Empty {col} in {role} shortlist"
            assert (sub[col].str.len() > 10).all(), f"Too short {col} in {role} shortlist"


def test_reserves_pool():
    df = pd.read_csv(ARTIFACTS_DIR / "rr_shortlist.csv")
    for role in ["Batting", "Bowling"]:
        res = df[(df["role_pool"] == role) & (df["is_reserve"])]
        assert len(res) == 5, f"Expected 5 reserves for {role}, found {len(res)}"
        assert (res["performance_rank"].values == np.arange(11, 16)).all()


def test_monotonic_conservative_score_ordering():
    df = pd.read_csv(ARTIFACTS_DIR / "rr_shortlist.csv")
    for role in ["Batting", "Bowling"]:
        sub = df[df["role_pool"] == role]
        # Conservative scores should be non-increasing with rank
        diffs = np.diff(sub["conservative_score_q25"].values)
        assert (diffs <= 1e-6).all(), f"Conservative score Q25 is not monotonically non-increasing in {role}"


def test_rankings_audit_provisional_governance():
    with open(ARTIFACTS_DIR / "rankings_audit.json", "r", encoding="utf-8") as f:
        audit = json.load(f)
        
    assert audit["batting_summary"]["shortfall"] == 0
    assert audit["bowling_summary"]["shortfall"] == 0
    assert len(audit["batting_summary"]["top10_names"]) == 10
    assert len(audit["bowling_summary"]["top10_names"]) == 10
    assert audit["verification_status"] == "PROVISIONAL"
