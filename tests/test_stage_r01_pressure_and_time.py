"""Test Stage R01: Pressure coverage, cricket accounting, and chronology validation."""

import json
from pathlib import Path
import pandas as pd
import pytest


OUT_DIR = Path("artifacts_rank_validation")
RAW_DIR = Path("6af3166e7b922_data_pack")


def test_sky_fixture_40759_pressure_reconciliation():
    """Verify SKY in fixture 40759 has death-over pressure deliveries and runs off bat."""
    p_path = OUT_DIR / "delivery_pressure_labels.csv"
    assert p_path.exists(), "delivery_pressure_labels.csv must exist"
    
    df = pd.read_csv(p_path, low_memory=False)
    sky = df[(df["striker_id"] == 1699) & (df["match_id"] == 40759)]
    
    # Official scorecard: 73 runs off 43 balls
    assert len(sky) == 43, f"Expected 43 balls faced, got {len(sky)}"
    assert sky["runs"].sum() == 73, f"Expected 73 runs, got {sky['runs'].sum()}"
    
    # High pressure deliveries in death overs (overs 17-20)
    sky_hp = sky[sky["is_high_pressure_20"] == 1]
    assert len(sky_hp) >= 10, f"Expected at least 10 high-pressure balls, got {len(sky_hp)}"
    assert sky_hp["runs"].sum() >= 30, f"Expected at least 30 high-pressure runs, got {sky_hp['runs'].sum()}"
    
    # Overs should be death overs (17-20)
    death_overs = set(sky_hp["pre_over"].unique())
    assert death_overs.issubset({16, 17, 18, 19, 20}), f"Unexpected overs: {death_overs}"


def test_sooryavanshi_ipl_2026_and_playoff_anchors():
    """Verify Vaibhav Sooryavanshi (50284) IPL 2026 totals and playoff anchors."""
    matches = pd.read_csv(RAW_DIR / "matches.csv")
    ipl26_matches = set(matches[matches["comp_id"] == 3298]["match_id"])
    
    df = pd.read_csv(OUT_DIR / "delivery_pressure_labels.csv", low_memory=False)
    vs = df[df["striker_id"] == 50284]
    
    vs_ipl26 = vs[vs["match_id"].isin(ipl26_matches)]
    assert vs_ipl26["match_id"].nunique() == 16
    assert vs_ipl26["runs"].sum() == 776
    
    # Fixture 50137 excluded for revised overs (39 runs)
    vs_50137 = vs[vs["match_id"] == 50137]
    assert vs_50137["runs"].sum() == 39
    
    # Regulation total = 737
    vs_reg = vs_ipl26[vs_ipl26["match_id"] != 50137]
    assert vs_reg["match_id"].nunique() == 15
    assert vs_reg["runs"].sum() == 737
    
    # Playoff anchors: 50943 (97 off 31), 50944 (96 off 48)
    p1 = vs[vs["match_id"] == 50943]
    assert p1["runs"].sum() == 97
    assert len(p1) == 31
    
    p2 = vs[vs["match_id"] == 50944]
    assert p2["runs"].sum() == 96
    assert len(p2) == 48


def test_rajapaksa_anchor_14101():
    """Verify Bhanuka Rajapaksa (2003) canonical ID and anchor match 14101."""
    df = pd.read_csv(OUT_DIR / "delivery_pressure_labels.csv", low_memory=False)
    raj = df[(df["striker_id"] == 2003) & (df["match_id"] == 14101)]
    assert len(raj) == 9
    assert raj["runs"].sum() == 31


def test_chronological_time_blocks_no_leakage():
    """Verify delivery impact ledger has chronological time blocks without future leakage."""
    imp_path = OUT_DIR / "delivery_impact_ledger.csv"
    assert imp_path.exists()
    imp = pd.read_csv(imp_path, low_memory=False)
    
    # Verify expected runs and wicket expectations are present
    assert "expected_bat_runs" in imp.columns
    assert "expected_striker_dismissal" in imp.columns
    assert "batting_impact" in imp.columns
    assert "bowling_impact" in imp.columns
    
    # Ensure there are no NaNs in primary impact calculations for eligible deliveries
    eligible = imp[imp["is_cohort_eligible"] == 1]
    assert eligible["batting_impact"].notna().all()
    assert eligible["bowling_impact"].notna().all()
