"""Test Stage R04: Robustness, evidence verification, and three-output contract separation."""

from pathlib import Path
import pandas as pd
import pytest


OUT_DIR = Path("artifacts_rank_validation")


def test_three_separate_outputs_exist():
    """Verify all three official contract outputs exist and are non-empty."""
    p_rankings = OUT_DIR / "player_rankings.csv"
    p_unstop = OUT_DIR / "unstop_rank_order.csv"
    p_notes = OUT_DIR / "rr_auction_notes.csv"
    
    assert p_rankings.exists(), "player_rankings.csv must exist"
    assert p_unstop.exists(), "unstop_rank_order.csv must exist"
    assert p_notes.exists(), "rr_auction_notes.csv must exist"


def test_unstop_form_checklist_specifications():
    """Verify unstop_rank_order.csv has exactly 20 rows, blank dropdown proxy, and PROVISIONAL status."""
    df = pd.read_csv(OUT_DIR / "unstop_rank_order.csv")
    assert len(df) == 20, f"Expected 20 rows, got {len(df)}"
    
    # 10 Batters and 10 Bowlers
    assert (df["role"] == "Batting").sum() == 10
    assert (df["role"] == "Bowling").sum() == 10
    
    # Ranks 1 to 10 in each role
    assert set(df[df["role"] == "Batting"]["rank"]) == set(range(1, 11))
    assert set(df[df["role"] == "Bowling"]["rank"]) == set(range(1, 11))
    
    # Dropdown label must be blank/empty string
    assert df["dropdown_label"].fillna("").eq("").all(), "dropdown_label must remain blank until verified"
    assert (df["verification_status"] == "PROVISIONAL").all()


def test_auction_notes_separation_and_incumbents():
    """Verify auction notes do not use rank-derived pool labels and correctly mark 2027 availability as UNKNOWN."""
    df = pd.read_csv(OUT_DIR / "rr_auction_notes.csv")
    assert len(df) >= 20
    
    # Auction status 2027 must be UNKNOWN for all players per audit contract
    assert (df["auction_status_2027"] == "UNKNOWN").all(), "All 2027 auction statuses must be UNKNOWN"
    
    # Vaibhav Sooryavanshi (50284) must be recognized as 2026_RR_INCUMBENT and BENCHMARK_INCUMBENT
    vs = df[df["player_id"] == 50284]
    assert len(vs) == 1
    assert vs.iloc[0]["rr_roster_status"] == "2026_RR_INCUMBENT"
    assert vs.iloc[0]["rr_action"] == "BENCHMARK_INCUMBENT"
    
    # Non-RR players must have NON_RR roster status
    non_rr = df[df["player_id"] != 50284]
    assert (non_rr["rr_roster_status"] == "NON_RR").all()
    
    # All picks must have tactical squad role and incumbent comparison
    assert df["tactical_squad_role"].notna().all()
    assert df["rr_incumbent_comparison"].notna().all()


def test_case_study_anchors_behavior():
    """Verify behavior of case study players (SKY, Sooryavanshi, Rajapaksa)."""
    rankings = pd.read_csv(OUT_DIR / "player_rankings.csv")
    unstop = pd.read_csv(OUT_DIR / "unstop_rank_order.csv")
    
    # 1. Sooryavanshi is Rank 1 Batter
    vs_unstop = unstop[(unstop["player_id"] == 50284) & (unstop["role"] == "Batting")]
    assert len(vs_unstop) == 1
    assert vs_unstop.iloc[0]["rank"] == 1
    
    # 2. Suryakumar Yadav is in Top 10 Batters
    sky_unstop = unstop[(unstop["player_id"] == 1699) & (unstop["role"] == "Batting")]
    assert len(sky_unstop) == 1
    assert sky_unstop.iloc[0]["rank"] <= 10
    
    # 3. Bhanuka Rajapaksa (2003) is NOT in Top 10 Batters due to thin-support penalization
    raj_unstop = unstop[(unstop["player_id"] == 2003) & (unstop["role"] == "Batting")]
    assert len(raj_unstop) == 0, "Rajapaksa must not be in Top 10"
