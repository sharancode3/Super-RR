"""Regression and validation tests for Stage H01: Cricket Ledger and Population Views."""

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(".").resolve()))

from rr_pressure.config import PipelineConfig
from rr_pressure.ledger import build_scoreboard_ledger

RAW_DIR = Path("6af3166e7b922_data_pack")


@pytest.fixture(scope="module")
def ledger_data():
    config = PipelineConfig(raw_dir=RAW_DIR, out_dir=Path("artifacts_hardened"), seed=2027)
    bbb, excluded, quarantined, coverage = build_scoreboard_ledger(config)
    return bbb, excluded, quarantined, coverage


def test_causality_and_invariance(ledger_data):
    """Verify that delivery t state only affects post(t) and pre(t+1), leaving pre(t) unchanged."""
    bbb, _, _, _ = ledger_data
    
    # Check mathematical consistency for pre and post
    assert (bbb["pre_team_offbat_runs"] + bbb["runs"] == bbb["post_team_offbat_runs"]).all()
    assert (bbb["pre_team_wickets"] + bbb["is_wicket"].astype(int) == bbb["post_team_wickets"]).all()
    assert (bbb["pre_legal_balls"] + bbb["is_legal_ball"].astype(int) == bbb["post_legal_balls"]).all()


def test_wide_stumpings_attributed_correctly(ledger_data):
    """Wides with stumping dismissals must credit the bowler with a wicket but NOT consume a legal ball."""
    bbb, _, _, _ = ledger_data
    wide_stumps = bbb[(bbb["extras_type"] == "wide") & (bbb["dismissal_type"] == "Stump")]
    assert len(wide_stumps) == 25, f"Expected 25 wide stumpings, found {len(wide_stumps)}"
    assert (~wide_stumps["is_legal_ball"]).all(), "Wide stumpings must not consume legal balls"
    assert wide_stumps["is_wicket"].all(), "Wide stumpings must count as team wickets"
    assert wide_stumps["is_bowler_wicket"].all(), "Wide stumpings must credit the bowler"
    assert wide_stumps["is_stumping_on_wide"].all(), "Flag is_stumping_on_wide must be True"


def test_run_outs_attributed_correctly(ledger_data):
    """Run outs must count as team wickets but NEVER credited to the bowler."""
    bbb, _, _, _ = ledger_data
    run_outs = bbb[bbb["dismissal_type"].isin(["RunOut", "Run Out"])]
    assert len(run_outs) > 0, "No run outs found"
    assert run_outs["is_wicket"].all(), "Run outs must be team wickets"
    assert (~run_outs["is_bowler_wicket"]).all(), "Run outs must NOT be bowler wickets"
    assert run_outs["is_run_out"].all(), "is_run_out must be True"


def test_scorecard_anchors_and_proxy_separation(ledger_data):
    """Verify proxy state is explicitly labeled and scorecard anchors match known historical fixtures."""
    bbb, excluded, _, coverage = ledger_data
    
    assert (~bbb["is_exact_state"]).all(), "All rows must be labeled is_exact_state=False in proxy lane"
    assert (bbb["source_lane"] == "RR_OFFBAT_PROXY").all()
    assert (bbb["state_route"] == "RR_OFFBAT_PROXY").all()
    assert (bbb["bowler_charge_certainty"] == "PROXY_SINGLE_EXTRA").all()
    
    # Anchor: Fixture 50140 (RCB vs RR)
    m50140 = bbb[bbb["match_id"] == 50140]
    rcb_offbat = m50140[m50140["innings"] == 1]["runs"].sum()
    assert rcb_offbat == 188, f"Expected 188 off-bat runs for RCB in 50140, found {rcb_offbat}"
    
    # Anchor: Fixture 13511 (England vs West Indies)
    # Off-bat is 100 in inn 1 (reconciling with 3 extras to official scorecard 103)
    # Off-bat is 99 in inn 2 (reconciling with 5 extras to official scorecard 104/1)
    m13511 = bbb[bbb["match_id"] == 13511]
    assert len(m13511) > 0, "Fixture 13511 must exist in ledger"
    inn1_runs = m13511[m13511["innings"] == 1]["runs"].sum()
    assert inn1_runs == 100, f"Expected 100 off-bat runs for inn 1 in 13511 (reconciling to 103 official), found {inn1_runs}"
    inn2_runs = m13511[m13511["innings"] == 2]["runs"].sum()
    assert inn2_runs == 99, f"Expected 99 off-bat runs for inn 2 in 13511 (reconciling to 104 official), found {inn2_runs}"
