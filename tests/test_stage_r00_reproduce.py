"""Stage R00 Verification Tests: Freeze and Reproduce Baseline Evidence and Case Studies."""

import json
from pathlib import Path
import pytest
import pandas as pd

from rr_pressure.manifest import compute_sha256

RAW_DIR = Path("6af3166e7b922_data_pack")
DIAGNOSTIC_DIR = Path("artifacts_forecast_audit_20261111")
OUT_DIR = Path("artifacts_rank_validation")

EXPECTED_RAW_HASHES = {
    "ball_by_ball.csv": "a3926f49d2c684dca2a5d2de535a02c5ee46ea654ca1e79dd31c69e7544e9889",
    "competitions.csv": "507ceb7189f972d4e4f299ddcfc97f3c3247af1913f6291106f161fa8353fd9b",
    "competition_team_player_mapping.csv": "1ded4e42a933618572d6e2c3a521c3257eb1844fab4456d567d77cbb2d3bbb12",
    "matches.csv": "bb100ab84b8b9a15160c1f2315cf675210131a30e779ec5079fd5403dcf56eef",
    "playing_eleven.csv": "7517c73722a28d5d61c808ccf0cbed315a8780586d02e946eb9a7f5daf011c27",
    "Round 1 Problem Statement _ SupeRR Selector Season 2.docx.pdf": "8f7965c616d4a64b779e770a6b2c17dde6a2d6ccbf7de12a58b04db792162489",
    "teams.csv": "a65e5922a9b3bf49247b24fc9471782e700efb31f8dcc5042923238b87c50a5d",
}


def test_raw_data_pack_hashes():
    """Verify all 7 raw pack files match immutable sha256 checksums."""
    for fname, exp_hash in EXPECTED_RAW_HASHES.items():
        p = RAW_DIR / fname
        assert p.exists(), f"Missing raw file: {fname}"
        assert compute_sha256(p) == exp_hash, f"Hash mismatch for {fname}"


def test_suryakumar_yadav_reproduction():
    """Verify Suryakumar Yadav (ID 1699): 717 runs in IPL 2025, 73 off 43 in match 40759, rank 5 under B0, 60 under D."""
    bbb = pd.read_csv(RAW_DIR / "ball_by_ball.csv", low_memory=False)
    matches = pd.read_csv(RAW_DIR / "matches.csv")
    
    # Raw pack IPL 2025 verification (comp_id 2725)
    sky = bbb[bbb["striker_id"] == 1699]
    mids_ipl_2025 = matches[matches["comp_id"] == 2725]["match_id"]
    sky_ipl = sky[sky["match_id"].isin(mids_ipl_2025)]
    assert sky_ipl["runs"].sum() == 717
    assert sky_ipl["match_id"].nunique() == 16
    
    # Match 40759
    sky_40759 = sky[sky["match_id"] == 40759]
    assert sky_40759["runs"].sum() == 73
    assert len(sky_40759) == 43
    
    # Diagnostic rankings check
    rankings = pd.read_csv(DIAGNOSTIC_DIR / "player_rankings.csv")
    sky_row = rankings[rankings["player_id"] == 1699].iloc[0]
    assert sky_row["performance_rank"] == 60.0
    assert abs(sky_row["conservative_score_q25"] - (-3.898)) < 0.05
    assert sky_row["hp_matches"] == 49


def test_vaibhav_sooryavanshi_reproduction():
    """Verify Vaibhav Sooryavanshi (ID 50284): 776 IPL 2026 runs, 737 in regulation (39 in 50137 excluded), rank 1 B0/B1, 13 D."""
    bbb = pd.read_csv(RAW_DIR / "ball_by_ball.csv", low_memory=False)
    matches = pd.read_csv(RAW_DIR / "matches.csv")
    
    # Raw pack IPL 2026 verification (comp_id 3298)
    vs = bbb[bbb["striker_id"] == 50284]
    mids_ipl_2026 = matches[matches["comp_id"] == 3298]["match_id"]
    vs_ipl = vs[vs["match_id"].isin(mids_ipl_2026)]
    assert vs_ipl["runs"].sum() == 776
    assert vs_ipl["match_id"].nunique() == 16
    
    # Excluded match 50137
    vs_50137 = vs[vs["match_id"] == 50137]
    assert vs_50137["runs"].sum() == 39
    assert vs_ipl[vs_ipl["match_id"] != 50137]["runs"].sum() == 737
    assert vs_ipl[vs_ipl["match_id"] != 50137]["match_id"].nunique() == 15
    
    # Diagnostic rankings check
    rankings = pd.read_csv(DIAGNOSTIC_DIR / "player_rankings.csv")
    vs_row = rankings[rankings["player_id"] == 50284].iloc[0]
    assert vs_row["performance_rank"] == 13.0
    
    # Qualified batters B0 ranking
    bat_qual = rankings[rankings["inferred_role"].str.contains("BATTER|ALLROUNDER") & (rankings["is_qualified"] == True)]
    b0_order = bat_qual.sort_values("b0_q25", ascending=False).reset_index(drop=True)
    assert b0_order.iloc[0]["player_id"] == 50284  # Rank 1 under B0!


def test_bhanuka_rajapaksa_reproduction():
    """Verify Bhanuka Rajapaksa has canonical ID 2003 (not 686) and rank 1 under D."""
    rankings = pd.read_csv(DIAGNOSTIC_DIR / "player_rankings.csv")
    raj = rankings[rankings["player_id"] == 2003].iloc[0]
    assert "Rajapaksa" in raj["player_name"]
    assert raj["performance_rank"] == 1.0
    assert raj["hp_matches"] == 9
    assert raj["hp_balls"] == 50
    assert raj["conservative_score_q25"] > 2.0


def test_rank_defect_ledger_presence():
    """Verify rank_defect_ledger.json exists and catalogs all 8 audit defects."""
    ledger_path = OUT_DIR / "rank_defect_ledger.json"
    assert ledger_path.exists()
    with open(ledger_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data["defects"]) == 8
    defect_ids = [d["id"] for d in data["defects"]]
    assert "RANK_DEFECT_01_PRESSURE_DEFINITION_SETTING_TOTAL" in defect_ids
    assert "RANK_DEFECT_02_THIN_SUPPORT_ARTIFACT" in defect_ids
    assert "RANK_DEFECT_03_PASTED_SCOUTING_IDENTITY_ERRORS" in defect_ids
    assert "RANK_DEFECT_07_RANK_DERIVED_AUCTION_LABELS" in defect_ids
    assert "RANK_DEFECT_08_OUTPUT_SEPARATION_VIOLATION" in defect_ids
