"""Test Stage R05: Clean rebuild verification, hash equality, and backend review gate."""

from pathlib import Path
import pandas as pd
import pytest

from rr_pressure.manifest import compute_sha256


DIR1 = Path("artifacts_rank_validation")
DIR2 = Path("test_artifacts_rank_validation")


def test_independent_rebuild_hash_parity():
    """Verify independent clean rebuild reproduces identical SHA-256 hashes for all core artifacts."""
    core_files = [
        "player_rankings.csv",
        "unstop_rank_order.csv",
        "rr_auction_notes.csv",
        "rr_shortlist.csv",
        "model_comparison.json",
        "player_reliability_forecasts_batting.csv",
        "player_reliability_forecasts_bowling.csv",
    ]
    for fname in core_files:
        f1 = DIR1 / fname
        f2 = DIR2 / fname
        assert f1.exists(), f"Primary artifact {f1} missing"
        assert f2.exists(), f"Rebuilt artifact {f2} missing"
        h1 = compute_sha256(f1)
        h2 = compute_sha256(f2)
        assert h1 == h2, f"Hash mismatch on {fname}: {h1} != {h2}"


def test_three_outputs_contract_fidelity():
    """Verify three outputs maintain exact fidelity without cross-contamination."""
    # 1. Performance rankings
    p_rank = pd.read_csv(DIR1 / "player_rankings.csv")
    assert len(p_rank) > 50
    assert "conservative_score_q25" in p_rank.columns
    assert "performance_rank" in p_rank.columns
    
    # 2. Unstop form order
    unstop = pd.read_csv(DIR1 / "unstop_rank_order.csv")
    assert len(unstop) == 20
    assert set(unstop["role"].unique()) == {"Batting", "Bowling"}
    assert unstop["dropdown_label"].fillna("").eq("").all()
    assert (unstop["verification_status"] == "PROVISIONAL").all()
    
    # 3. RR auction notes
    notes = pd.read_csv(DIR1 / "rr_auction_notes.csv")
    assert len(notes) >= 20
    assert (notes["auction_status_2027"] == "UNKNOWN").all()
    assert set(notes["rr_roster_status"].unique()) == {"2026_RR_INCUMBENT", "NON_RR"}
    
    # Check Sooryavanshi and Jaiswal consistency
    vs = notes[notes["player_id"] == 50284]
    assert len(vs) == 1
    assert vs.iloc[0]["rr_roster_status"] == "2026_RR_INCUMBENT"
    assert vs.iloc[0]["rr_action"] == "BENCHMARK_INCUMBENT"
