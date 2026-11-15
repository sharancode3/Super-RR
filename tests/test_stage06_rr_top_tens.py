"""Stage 06 Verification Tests: Rajasthan Royals Top Tens, Auction Scenarios, and Review Order."""
import json
from pathlib import Path
import pandas as pd
import pytest

REPO_ROOT = Path("C:/SHARAN PROJECTS/rr")
FRESH_DIR = REPO_ROOT / "artifacts_hardened_v4_20261113" if (REPO_ROOT / "artifacts_hardened_v4_20261113").exists() else (REPO_ROOT / "artifacts_hardened_v3_20261113" if (REPO_ROOT / "artifacts_hardened_v3_20261113").exists() else (REPO_ROOT / "artifacts_hardened_v2_20261113" if (REPO_ROOT / "artifacts_hardened_v2_20261113").exists() else (REPO_ROOT / "artifacts_hardened_20261113")))


def test_stage06_artifacts_exist():
    """Verify all required Stage 06 artifacts exist and are non-empty."""
    required = [
        "top10_batters_under_pressure.csv",
        "top10_bowlers_under_pressure.csv",
        "rr_shortlist.csv",
        "rr_auction_notes.csv",
        "rr_recruitment_sheet.csv",
        "rr_lineup_scenarios.csv",
        "unstop_rank_order.csv",
        "unstop_submission_checklist.csv",
        "player_rankings.csv",
        "rankings_audit.json",
        "checkpoint.json",
    ]
    for fname in required:
        p = FRESH_DIR / fname
        assert p.exists(), f"Missing required Stage 06 artifact: {fname}"
        assert p.stat().st_size > 0, f"Artifact is empty: {fname}"


def test_top10_batters_exact_ten_and_unique():
    """Verify 10 unique, qualified batters with valid ranks and data."""
    df = pd.read_csv(FRESH_DIR / "top10_batters_under_pressure.csv")
    assert len(df) == 10
    assert df["player_id"].nunique() == 10
    assert list(df["submission_rank"]) == list(range(1, 11))

    expected_batters = [
        "Abishek Porel",
        "Aniket Verma",
        "Dewald Brevis",
        "Donovan Ferreira",
        "Liam Livingstone",
        "Jacob Bethell",
        "Riyan Parag",
        "Vaibhav Sooryavanshi",
        "Priyansh Arya",
        "Mitchell Marsh",
    ]
    assert list(df["player_name"]) == expected_batters


def test_top10_bowlers_exact_ten_and_unique():
    """Verify 10 unique, qualified bowlers with valid ranks and data."""
    df = pd.read_csv(FRESH_DIR / "top10_bowlers_under_pressure.csv")
    assert len(df) == 10
    assert df["player_id"].nunique() == 10
    assert list(df["submission_rank"]) == list(range(1, 11))

    expected_bowlers = [
        "Mustafizur Rahman",
        "Matheesha Pathirana",
        "Varun Chakravarthy",
        "Bhuvneshwar Kumar",
        "Kuldeep Yadav",
        "Eshan Malinga",
        "Lungi Ngidi",
        "Mitchell Santner",
        "Jofra Archer",
        "Mohammed Shami",
    ]
    assert list(df["player_name"]) == expected_bowlers


def test_auction_notes_contract():
    """Verify auction notes contain required explanatory fields for all 20 picks."""
    df = pd.read_csv(FRESH_DIR / "rr_auction_notes.csv")
    top20 = df[df["is_official_top10"]].copy()
    assert len(top20) == 20

    required_fields = [
        "player_id",
        "player_name",
        "role_pool",
        "submission_rank",
        "inferred_role",
        "tactical_squad_role",
        "current_franchise_2027",
        "auction_status_2027",
        "actionable_acquisition_route",
        "decision_category",
        "rr_incumbent_comparison",
        "role_matched_reserve",
        "representative_performance",
        "downside_or_uncertainty",
    ]
    for col in required_fields:
        assert col in top20.columns, f"Missing required column: {col}"
        assert top20[col].notna().all(), f"Null values found in {col}"


def test_rr_incumbent_qualification():
    """Verify RR incumbents qualify under the verified selector."""
    df = pd.read_csv(FRESH_DIR / "rr_shortlist.csv")
    top20 = df[df["is_official_top10"]].copy()

    rr_incumbents = top20[top20["current_franchise_2027"] == "Rajasthan Royals"]
    assert len(rr_incumbents) >= 4  # Ferreira, Parag, Sooryavanshi, Archer

    for _, r in rr_incumbents.iterrows():
        assert r["decision_category"] == "INCUMBENT_RETENTION"
        assert r["actionable_acquisition_route"] == "INTERNAL_SQUAD_RETENTION"


def test_lineup_scenarios():
    """Verify RR lineup depth chart covers core tactical jobs and baselines."""
    scen = pd.read_csv(FRESH_DIR / "rr_lineup_scenarios.csv")
    assert len(scen) >= 7
    roles = set(scen["tactical_role"])
    assert "TOP_ORDER_OPENER" in roles
    assert "WICKETKEEPER_BATTER" in roles
    assert "MIDDLE_ORDER_STABILIZER" in roles
    assert "DEATH_FINISHER" in roles
    assert "NEW_BALL_SEAM" in roles
    assert "MIDDLE_OVERS_SPIN" in roles
    assert "DEATH_PACE_BOWLER" in roles
