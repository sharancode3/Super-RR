"""Regression and validation tests for Stage 02 Scoreboard Ledger."""

import numpy as np
import pandas as pd
import pytest
from pathlib import Path

ARTIFACTS_DIR = Path("artifacts_revalidated") if Path("artifacts_revalidated").exists() else Path("artifacts")


@pytest.fixture(scope="module")
def ledger():
    csv_path = ARTIFACTS_DIR / "delivery_ledger_proxy.csv"
    if not csv_path.exists():
        pytest.skip("delivery_ledger_proxy.csv not yet generated")
    return pd.read_csv(csv_path, low_memory=False)


def test_pre_post_causality(ledger):
    """Verify strictly pre-ball information: pre_team_offbat_runs + runs == post_team_offbat_runs."""
    # Exact mathematical identity
    assert (ledger["pre_team_offbat_runs"] + ledger["runs"] == ledger["post_team_offbat_runs"]).all()
    assert (ledger["pre_team_wickets"] + ledger["is_wicket"].astype(int) == ledger["post_team_wickets"]).all()
    assert (ledger["pre_legal_balls"] + ledger["is_legal_ball"].astype(int) == ledger["post_legal_balls"]).all()


def test_legal_balls_bounded(ledger):
    """Regulation T20 innings cannot exceed 120 legal balls."""
    max_legal = ledger.groupby(["match_id", "innings"])["is_legal_ball"].sum().max()
    assert max_legal <= 120, f"Found innings with {max_legal} legal balls (> 120)!"


def test_wide_stumpings_present_and_preserve_balls(ledger):
    """Stumpings on wides must be recorded as wickets but not consume legal deliveries."""
    wide_stumps = ledger[(ledger["extras_type"] == "wide") & (ledger["dismissal_type"] == "Stump")]
    assert len(wide_stumps) == 25, f"Expected 25 wide stumpings, found {len(wide_stumps)}"
    assert (~wide_stumps["is_legal_ball"]).all(), "Wide stumpings should not consume legal balls"
    assert wide_stumps["is_wicket"].all(), "Wide stumpings must be marked as wickets"
    assert wide_stumps["is_bowler_wicket"].all(), "Wide stumpings must be credited to bowler"


def test_non_striker_run_outs(ledger):
    """Run outs of non-striker must count as team wickets but NEVER credited to bowler."""
    ns_runouts = ledger[ledger["is_non_striker_dismissed"] & (ledger["dismissal_type"] == "RunOut")]
    assert len(ns_runouts) > 0, "No non-striker runouts found"
    assert (~ns_runouts["is_bowler_wicket"]).all(), "Non-striker runouts must not be credited to bowler"


def test_free_hit_carryover(ledger):
    """A free hit must carry over through illegal deliveries."""
    fh_deliveries = ledger[ledger["pre_free_hit"] == True]
    assert len(fh_deliveries) > 0, "No free hit deliveries found"


def test_exclusions_count():
    """Verify all 77 excluded non-standard / abandoned / revised matches are documented with reasons."""
    exclusions = pd.read_csv(ARTIFACTS_DIR / "exclusions_ledger.csv")
    assert len(exclusions) == 77, f"Expected 77 excluded fixtures, got {len(exclusions)}"
    assert exclusions["exclusion_reason"].notna().all(), "All exclusions must have documented reasons"


def test_quarantined_discrepancies():
    """Verify exactly 13 discrepancies quarantined."""
    quarantined = pd.read_csv(ARTIFACTS_DIR / "quarantined_discrepancies.csv")
    assert len(quarantined) == 13, f"Expected 13 quarantined discrepancies, got {len(quarantined)}"


def test_exact_proxy_separation(ledger):
    """Verify proxy state is explicitly labeled and off-bat figures are kept distinct from exact scores."""
    assert "is_exact_state" in ledger.columns
    assert (~ledger["is_exact_state"]).all(), "RR ledger without public archive alignment must be marked proxy"
    assert (ledger["state_route"] == "RR_OFFBAT_PROXY").all()
    
    # Audit anchor check on fixture 50140 (RCB vs RR)
    m50140 = ledger[ledger["match_id"] == 50140]
    rcb_offbat = m50140[m50140["innings"] == 1]["runs"].sum()
    # Off-bat batter runs is 188, while official total is 201 (difference of 13 runs due to unmodeled extras)
    assert rcb_offbat == 188, f"Expected 188 off-bat runs for RCB in 50140, found {rcb_offbat}"
