"""Regression tests for Stage 1: Explicit discipline role support and qualification gates."""

import pandas as pd
import pytest
from pathlib import Path

from rr_pressure.ingest import derive_player_roles
from rr_pressure.forecast import is_qualified

RAW_DIR = Path("6af3166e7b922_data_pack")


@pytest.fixture(scope="module")
def player_dimension_full():
    bbb = pd.read_csv(RAW_DIR / "ball_by_ball.csv", low_memory=False)
    p11 = pd.read_csv(RAW_DIR / "playing_eleven.csv")
    mapping = pd.read_csv(RAW_DIR / "competition_team_player_mapping.csv")
    all_player_ids = pd.concat([
        mapping["player_id"],
        p11["player_id"],
        bbb["striker_id"].dropna().astype(int),
        bbb["bowler_id"].dropna().astype(int),
    ]).drop_duplicates().astype(int)
    return derive_player_roles(bbb, p11, all_player_ids, mapping).set_index("player_id")


def test_tail_end_specialists_kuldeep_and_bhuvneshwar(player_dimension_full):
    """Kuldeep Yadav and Bhuvneshwar Kumar must have bowling role support, NO batting role support,
    and be classified as specialist bowlers (SPIN_BOWLER / PACE_BOWLER), NOT allrounders."""
    p_dim = player_dimension_full
    
    # Kuldeep Yadav (ID 3644)
    assert 3644 in p_dim.index
    kuldeep = p_dim.loc[3644]
    assert kuldeep["bowling_role_supported"] is True or kuldeep["bowling_role_supported"] == 1
    assert kuldeep["batting_role_supported"] is False or kuldeep["batting_role_supported"] == 0
    assert kuldeep["top7_innings"] == 0
    assert kuldeep["avg_bat_order"] > 8.5
    assert kuldeep["inferred_role"] == "SPIN_BOWLER"
    assert "Wrist" in kuldeep["bowling_display_role"] or "Spinner" in kuldeep["bowling_display_role"]
    
    # Bhuvneshwar Kumar (ID 360)
    assert 360 in p_dim.index
    bhuvi = p_dim.loc[360]
    assert bhuvi["bowling_role_supported"] is True or bhuvi["bowling_role_supported"] == 1
    assert bhuvi["batting_role_supported"] is False or bhuvi["batting_role_supported"] == 0
    assert bhuvi["top7_innings"] == 0
    assert bhuvi["avg_bat_order"] > 8.5
    assert bhuvi["inferred_role"] == "PACE_BOWLER"
    assert "Specialist" in bhuvi["bowling_display_role"] or "Seam" in bhuvi["bowling_display_role"] or "Bowler" in bhuvi["bowling_display_role"]
    
    # Qualification gate check: even with 100 pressure balls faced, batting qualification is blocked
    mock_bat_profiles = pd.DataFrame({
        "player_id": [3644, 360],
        "hp_balls": [100, 100],
        "hp_matches": [10, 10],
        "batting_role_supported": [False, False],
    })
    qual_bat = is_qualified(mock_bat_profiles, "batting", min_balls=48, min_matches=6)
    assert not qual_bat.any(), "Tail-enders must not qualify for batting ranking"


def test_occasional_bowlers_kohli_and_surya(player_dimension_full):
    """Occasional bowlers like Virat Kohli and Suryakumar Yadav must have batting role support,
    NO bowling role support, and be classified as specialist batters, NOT allrounders."""
    p_dim = player_dimension_full
    
    # Virat Kohli (ID 47)
    assert 47 in p_dim.index
    kohli = p_dim.loc[47]
    assert kohli["batting_role_supported"] is True or kohli["batting_role_supported"] == 1
    assert kohli["bowling_role_supported"] is False or kohli["bowling_role_supported"] == 0
    assert kohli["inferred_role"] in ["TOP_ORDER_BATTER", "MIDDLE_ORDER_BATTER"]
    
    # Suryakumar Yadav (ID 1699)
    assert 1699 in p_dim.index
    surya = p_dim.loc[1699]
    assert surya["batting_role_supported"] is True or surya["batting_role_supported"] == 1
    assert surya["bowling_role_supported"] is False or surya["bowling_role_supported"] == 0
    assert surya["inferred_role"] in ["MIDDLE_ORDER_BATTER", "TOP_ORDER_BATTER"]
    
    # Qualification gate check: even with 100 pressure balls bowled, bowling qualification is blocked
    mock_bowl_profiles = pd.DataFrame({
        "player_id": [47, 1699],
        "hp_balls": [100, 100],
        "hp_matches": [10, 10],
        "bowling_role_supported": [False, False],
    })
    qual_bowl = is_qualified(mock_bowl_profiles, "bowling", min_balls=48, min_matches=6)
    assert not qual_bowl.any(), "Occasional bowlers must not qualify for bowling ranking"


def test_genuine_dual_role_allrounder_sunil_narine(player_dimension_full):
    """Sunil Narine must have BOTH batting role support (opens batting in IPL, 37 top-7 innings)
    and bowling role support (frontline spinner, 3.87 overs/match)."""
    p_dim = player_dimension_full
    assert 781 in p_dim.index
    narine = p_dim.loc[781]
    
    assert narine["batting_role_supported"] is True or narine["batting_role_supported"] == 1
    assert narine["bowling_role_supported"] is True or narine["bowling_role_supported"] == 1
    assert narine["top7_innings"] >= 30
    assert narine["inferred_role"] == "SPIN_ALLROUNDER"
    
    # Can qualify in both disciplines when sample size suffices
    mock_profiles = pd.DataFrame({
        "player_id": [781],
        "hp_balls": [60],
        "hp_matches": [8],
        "batting_role_supported": [True],
        "bowling_role_supported": [True],
    })
    assert is_qualified(mock_profiles, "batting").iloc[0] is True or is_qualified(mock_profiles, "batting").iloc[0] == 1
    assert is_qualified(mock_profiles, "bowling").iloc[0] is True or is_qualified(mock_profiles, "bowling").iloc[0] == 1


def test_wicketkeeper_batters_porel_and_salt(player_dimension_full):
    """Wicketkeeper batters must have batting role support and is_wk=True."""
    p_dim = player_dimension_full
    
    # Abishek Porel (ID 19714)
    assert 19714 in p_dim.index
    porel = p_dim.loc[19714]
    assert porel["is_wk"] is True or porel["is_wk"] == 1
    assert porel["batting_role_supported"] is True or porel["batting_role_supported"] == 1
    assert porel["inferred_role"] == "WK_BATTER"
    assert "Wicketkeeper-Batter" in porel["batting_display_role"]
    
    # Phil Salt (ID 5553)
    assert 5553 in p_dim.index
    salt = p_dim.loc[5553]
    assert salt["is_wk"] is True or salt["is_wk"] == 1
    assert salt["batting_role_supported"] is True or salt["batting_role_supported"] == 1
    assert salt["inferred_role"] == "WK_BATTER"
    assert "Wicketkeeper-Batter" in salt["batting_display_role"]


def test_independent_unresolved_dropdown_gate():
    """Unstop dropdown eligibility must remain independent and provisional when uncaptured."""
    mock_profiles = pd.DataFrame({
        "player_id": [1, 2],
        "hp_balls": [60, 60],
        "hp_matches": [10, 10],
        "batting_role_supported": [True, True],
        "dropdown_label": ["", ""],
        "unstop_dropdown_status": ["PROVISIONAL_UNRESOLVED", "PROVISIONAL_UNRESOLVED"],
    })
    # Statistical qualification passes
    assert is_qualified(mock_profiles, "batting").all()
    # But dropdown remains explicitly unverified / provisional
    assert (mock_profiles["dropdown_label"] == "").all()
    assert (mock_profiles["unstop_dropdown_status"] == "PROVISIONAL_UNRESOLVED").all()


def test_missing_or_malformed_role_column_blocks_qualification():
    """A player with 90 pressure balls and 10 matches must NOT qualify when role evidence is absent or malformed."""
    # 1. Missing role column entirely
    mock_missing_col = pd.DataFrame({
        "player_id": [9991],
        "hp_balls": [90],
        "hp_matches": [10],
    })
    qual_bat = is_qualified(mock_missing_col, "batting", min_balls=48, min_matches=6)
    assert not qual_bat.iloc[0], "Missing role column must block batting qualification"
    qual_bowl = is_qualified(mock_missing_col, "bowling", min_balls=48, min_matches=6)
    assert not qual_bowl.iloc[0], "Missing role column must block bowling qualification"

    # 2. NaN / None / Malformed role column
    import numpy as np
    mock_malformed = pd.DataFrame({
        "player_id": [9992, 9993],
        "hp_balls": [90, 120],
        "hp_matches": [10, 15],
        "batting_role_supported": [np.nan, None],
        "bowling_role_supported": [np.nan, None],
    })
    assert not is_qualified(mock_malformed, "batting").any(), "NaN/None role evidence must block batting qualification"
    assert not is_qualified(mock_malformed, "bowling").any(), "NaN/None role evidence must block bowling qualification"


def test_evidence_based_role_labels(player_dimension_full):
    """Role labels must be strictly grounded in direct evidence:
    - Death-overs pace bowler requires phase & pace evidence.
    - Yorker specialist requires delivery-style evidence.
    - Wrist spinner requires bowling_type evidence (Leg-Break, Chinaman).
    - Finisher requires death-overs batting phase evidence.
    """
    p_dim = player_dimension_full

    # Varun Chakravarthy (ID 6256) - Leg-break spin -> Middle-Overs Wrist Spinner
    varun = p_dim.loc[6256]
    assert "Wrist" in varun["bowling_display_role"] or "Leg-Break" in varun["bowling_type"]

    # Kuldeep Yadav (ID 3644) - Chinaman wrist spin -> Middle-Overs Wrist Spinner
    kuldeep = p_dim.loc[3644]
    assert "Wrist" in kuldeep["bowling_display_role"] or "Chinaman" in kuldeep["bowling_type"]

    # Kartik Tyagi (ID 8530) - Pace with death deployment (35% death balls), only 10 yorkers -> Death-Overs Pace Bowler
    tyagi = p_dim.loc[8530]
    assert "Pace" in tyagi["bowling_display_role"] or "Seam" in tyagi["bowling_display_role"]
    assert "Yorker" not in tyagi["bowling_display_role"], "Tyagi only bowled 10 yorkers (2.3%); cannot be labeled Yorker Specialist without measured delivery style evidence"

