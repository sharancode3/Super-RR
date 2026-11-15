"""Stage F01 Verification Tests: Reconcile cricket events and audit data."""

import json
from pathlib import Path
import pytest
import pandas as pd

from rr_pressure.manifest import compute_sha256

RAW_DIR = Path("6af3166e7b922_data_pack")
REVIEW_DIR = Path("artifacts_release_review")


def test_fixture_13612_excluded():
    """Verify fixture 13612 (DLS rain-affected match) is explicitly excluded from the modeling cohort."""
    exclusions = pd.read_csv(REVIEW_DIR / "exclusions_ledger.csv")
    ex_row = exclusions[exclusions["match_id"] == 13612]
    assert len(ex_row) == 1
    assert "RevisedOvers" in ex_row["exclusion_reason"].iloc[0] or "DLSMethod" in ex_row["exclusion_reason"].iloc[0]


def test_scorecard_anchors_and_proxy_lane():
    """Verify scorecard anchors 50140 (RR vs RCB) and 13511 (WI vs ENG) in proxy lane."""
    ledger = pd.read_csv(REVIEW_DIR / "delivery_ledger_proxy.csv", low_memory=False)
    
    # Fixture 50140
    m_50140 = ledger[ledger["match_id"] == 50140]
    assert len(m_50140) > 0
    assert m_50140["is_cohort_eligible"].all()
    assert (m_50140["source_lane"] == "RR_OFFBAT_PROXY").all()
    assert not m_50140["is_exact_state"].any()
    
    # Off-bat runs for Vaibhav Sooryavanshi in match 50140: 78 off 26 balls
    v_balls = m_50140[(m_50140["striker_name"].str.contains("Sooryavanshi", na=False)) & (m_50140["is_legal_ball"])]
    assert len(v_balls) == 26
    assert v_balls["runs"].sum() == 78
    
    # Fixture 13511
    m_13511 = ledger[ledger["match_id"] == 13511]
    assert len(m_13511) > 0
    # First innings off-bat runs: 100
    inn1_runs = m_13511[m_13511["innings"] == 1]["runs"].sum()
    assert inn1_runs == 100


def test_cricket_event_accounting_rules():
    """Verify wide stumpings, run outs, legal ball tracking, and bowler charges."""
    ledger = pd.read_csv(REVIEW_DIR / "delivery_ledger_proxy.csv", low_memory=False)
    
    # 1. Wide stumpings credited to bowler without legal ball consumption
    wide_stumpings = ledger[ledger["is_stumping_on_wide"]]
    assert len(wide_stumpings) == 25
    assert not wide_stumpings["is_legal_ball"].any()
    assert wide_stumpings["is_bowler_wicket"].all()
    
    # 2. Run outs credited to team, not bowler
    run_outs = ledger[ledger["is_run_out"]]
    assert len(run_outs) == 600
    assert not run_outs["is_bowler_wicket"].any()
    assert run_outs["is_wicket"].all()
    
    # 3. Quarantined discrepancies isolated
    quarantined = pd.read_csv(REVIEW_DIR / "quarantined_discrepancies.csv")
    assert len(quarantined) == 13
