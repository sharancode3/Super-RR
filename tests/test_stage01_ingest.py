"""Regression test suite for Stage 01 ingestion and identity reconciliation."""

import pandas as pd
import pytest
from pathlib import Path

RAW_DIR = Path("6af3166e7b922_data_pack")
ARTIFACTS_DIR = Path("artifacts")


def test_delivery_key_uniqueness():
    bbb = pd.read_csv(RAW_DIR / "ball_by_ball.csv", usecols=["match_id", "innings", "innings_ball_num"])
    dups = bbb.duplicated(subset=["match_id", "innings", "innings_ball_num"]).sum()
    assert dups == 0, f"Found {dups} duplicate delivery keys in ball_by_ball.csv"


def test_fixture_grain_and_uniqueness():
    matches = pd.read_csv(RAW_DIR / "matches.csv")
    dups = matches.duplicated(subset=["match_id"]).sum()
    assert dups == 0, f"Found {dups} duplicate match_ids in matches.csv"
    assert len(matches) == 883, f"Expected 883 matches, got {len(matches)}"


def test_xi_join_multiplication_regression():
    """Independent regression fixture: proves an un-deduplicated XI join inflates row count,
    while the audited deduplicated XI preserves exact grain of ball_by_ball (200,999 rows)."""
    bbb = pd.read_csv(RAW_DIR / "ball_by_ball.csv", low_memory=False)
    p11_raw = pd.read_csv(RAW_DIR / "playing_eleven.csv")
    
    # 1. Verify un-deduplicated join FAILS by multiplying rows
    raw_joined = bbb.merge(p11_raw, left_on=["match_id", "striker_id"], right_on=["match_id", "player_id"], how="left")
    assert len(raw_joined) > len(bbb), "Raw join should have inflated row count due to duplicate XI records"
    assert len(raw_joined) - len(bbb) == 780, f"Expected 780 row inflation, got {len(raw_joined) - len(bbb)}"
    
    # 2. Verify clean deduplicated XI maintains exact delivery count (200,999)
    p11_clean = pd.read_csv(ARTIFACTS_DIR / "playing_eleven_deduped.csv")
    clean_joined = bbb.merge(p11_clean, left_on=["match_id", "striker_id"], right_on=["match_id", "player_id"], how="left")
    assert len(clean_joined) == len(bbb), f"Clean join altered grain: {len(clean_joined)} vs {len(bbb)}"
    assert len(clean_joined) == 200999, f"Clean delivery count is not 200999: {len(clean_joined)}"


def test_missing_deliveries_explained():
    """All 16 missing delivery fixtures must be documented as Match Abandoned."""
    missing = pd.read_csv(ARTIFACTS_DIR / "missing_delivery_fixtures.csv")
    assert len(missing) == 16, f"Expected 16 missing delivery fixtures, got {len(missing)}"
    assert missing["is_abandoned"].all(), "Not all missing fixtures are marked as abandoned"


def test_as_of_role_leakage():
    """Verify that earlier player profile is invariant to adding or modifying later matches."""
    from rr_pressure.ingest import derive_player_roles
    
    bbb = pd.read_csv(RAW_DIR / "ball_by_ball.csv", low_memory=False)
    matches = pd.read_csv(RAW_DIR / "matches.csv")
    matches["match_date"] = pd.to_datetime(matches["match_date"])
    p11 = pd.read_csv(RAW_DIR / "playing_eleven.csv")
    mapping = pd.read_csv(RAW_DIR / "competition_team_player_mapping.csv")
    
    train_mids = set(matches[matches["match_date"] <= "2024-12-31"]["match_id"].unique())
    all_players = mapping["player_id"].drop_duplicates()
    
    # Baseline as-of 2024-12-31
    base_dim = derive_player_roles(bbb, p11, all_players, mapping, valid_match_ids=train_mids)
    
    # Artificial modification to 2025+ deliveries
    later_mids = set(matches[matches["match_date"] > "2024-12-31"]["match_id"].unique())
    bbb_modified = bbb.copy()
    bbb_modified.loc[bbb_modified["match_id"].isin(later_mids), "runs"] += 100
    
    modified_dim = derive_player_roles(bbb_modified, p11, all_players, mapping, valid_match_ids=train_mids)
    
    # Assert historical profiles are strictly identical
    pd.testing.assert_frame_equal(base_dim, modified_dim)
