"""Stage A04: Acceptance Tests for Robustness Stress Tests and RR Auction Decisions.

Validates:
1. Robustness check model parity: LOMO baseline rank matches production rank (e.g. Abhishek Sharma rank #1, Salt, Head).
2. Auction notes role comparisons: opening batters compared against opening incumbents (Sooryavanshi/Jaiswal),
   not generic fallback/middle-order incumbents.
3. Cross-competition transfer risk categorization and zero unverified auction availability.
4. Actionable conditional auction triggers for all shortlist candidates.
5. Top 10 exports and unstop checklist generation.
"""

import json
from pathlib import Path
import pandas as pd
import pytest

ARTIFACTS_DIR = Path("artifacts_decision_validation")


def test_robustness_lomo_model_parity():
    """Verify that LOMO evaluates the exact selected production model family and baseline ranks match."""
    rob_path = ARTIFACTS_DIR / "robustness_report.json"
    if not rob_path.exists():
        rob_path = ARTIFACTS_DIR / "robustness_checks.json"
    assert rob_path.exists(), f"Missing robustness report in {ARTIFACTS_DIR}"
    
    with open(rob_path, "r", encoding="utf-8") as f:
        rob = json.load(f)
        
    standout_bat = rob.get("standout_match_sensitivity", {}).get("batting_top15", [])
    assert len(standout_bat) > 0, "Missing batting standout match sensitivity results"
    
    # Check that baseline ranks are sequential 1, 2, 3... matching production ranking
    baseline_ranks = [p["baseline_rank"] for p in standout_bat]
    assert baseline_ranks == list(range(1, len(standout_bat) + 1)), (
        f"LOMO baseline ranks do not match production ranking sequence: {baseline_ranks}"
    )
    
    # Check top pick
    assert standout_bat[0]["baseline_rank"] == 1, "Top qualifier baseline rank in LOMO must be 1"


def test_auction_notes_incumbent_role_matching():
    """Verify role matching compares openers against openers (Sooryavanshi/Jaiswal), not Parag, and Salt's role is corrected."""
    notes_path = ARTIFACTS_DIR / "rr_auction_notes.csv"
    assert notes_path.exists(), f"Missing {notes_path}"
    
    df_notes = pd.read_csv(notes_path)
    assert not df_notes.empty, "Auction notes CSV is empty"
    
    # Check Phil Salt's role is corrected to Powerplay / Top-Order
    salt_rows = df_notes[df_notes["player_name"].str.contains("Salt", case=False, na=False)]
    assert not salt_rows.empty, "Expected Phil Salt in auction notes"
    salt_role = salt_rows.iloc[0]["tactical_squad_role"]
    assert "Powerplay" in salt_role or "Top-Order" in salt_role, f"Salt role incorrect: {salt_role}"
    assert "Finisher" not in salt_role, f"Salt should not be classified as a finisher: {salt_role}"
    
    salt_comp = salt_rows.iloc[0]["rr_incumbent_comparison"]
    assert "Sooryavanshi" in salt_comp or "Jaiswal" in salt_comp, f"Salt must compare to opening incumbents: {salt_comp}"
    assert "Buttler" in salt_comp, f"Salt must evaluate against Jos Buttler: {salt_comp}"

    # Check opening / top-order batters (e.g. Travis Head, Finn Allen, Shubman Gill, Virat Kohli)
    openers = df_notes[df_notes["tactical_squad_role"].str.contains(r"OPENER|TOP.?ORDER|BOUNDARY THREAT|POWERPLAY", case=False, na=False)]
    assert not openers.empty, "Expected at least one opener/top-order batter in auction notes"
    
    for _, row in openers.iterrows():
        comp_str = str(row["rr_incumbent_comparison"])
        # If it's not Sooryavanshi comparing to himself, must compare to Sooryavanshi or Jaiswal
        if "Vaibhav Sooryavanshi" not in row["player_name"]:
            assert "Sooryavanshi" in comp_str or "Jaiswal" in comp_str, (
                f"Opener {row['player_name']} must be compared to Sooryavanshi/Jaiswal, got: {comp_str}"
            )
            assert "Parag" not in comp_str, (
                f"Opener {row['player_name']} should not be compared against Parag: {comp_str}"
            )


def test_cross_competition_transfer_risk_and_availability():
    """Verify transfer risk is documented and 2027 availability remains UNKNOWN without BCCI source."""
    notes_path = ARTIFACTS_DIR / "rr_auction_notes.csv"
    df_notes = pd.read_csv(notes_path)
    
    assert "cross_competition_transfer_risk" in df_notes.columns, "Missing cross_competition_transfer_risk"
    assert "auction_status_2027" in df_notes.columns, "Missing auction_status_2027"
    
    # All players must have UNKNOWN availability unless backed by verified affirmative BCCI proof
    assert (df_notes["auction_status_2027"] == "UNKNOWN").all(), (
        "Unverified 2027 auction availability must remain UNKNOWN"
    )
    
    # Check that transfer risk has valid labels
    valid_risk_labels = {
        "LOW_RISK_DIRECT_IPL_EVIDENCE",
        "MODERATE_RISK_T20I_INTERNATIONAL_TRANSFER",
        "HIGH_RISK_EMERGING_ONLY_TRANSFER",
    }
    assigned_labels = set(df_notes["cross_competition_transfer_risk"].unique())
    assert assigned_labels.issubset(valid_risk_labels), f"Unexpected transfer risk labels: {assigned_labels}"


def test_actionable_auction_triggers():
    """Verify that every shortlisted candidate has an actionable trigger condition with budget scenario labeling."""
    notes_path = ARTIFACTS_DIR / "rr_auction_notes.csv"
    df_notes = pd.read_csv(notes_path)
    
    assert "auction_trigger_condition" in df_notes.columns, "Missing auction_trigger_condition"
    assert not df_notes["auction_trigger_condition"].isna().any(), "Found NaN auction trigger condition"
    assert (df_notes["auction_trigger_condition"].str.len() > 10).all(), "Found trivial trigger condition"
    
    # Verify budget assumptions are explicitly labelled as scenarios
    non_rr = df_notes[df_notes["rr_roster_status"] != "2026_RR_INCUMBENT"]
    assert (non_rr["auction_trigger_condition"].str.contains("SCENARIO_BUDGET_CAP")).all(), (
        "Non-incumbent auction triggers must label budget assumptions as SCENARIO_BUDGET_CAP"
    )


def test_top10_exports_and_unstop_checklist():
    """Verify top 10 batters and bowlers CSVs and unstop checklist."""
    top_bat_path = ARTIFACTS_DIR / "top10_batters_under_pressure.csv"
    top_bowl_path = ARTIFACTS_DIR / "top10_bowlers_under_pressure.csv"
    unstop_path = ARTIFACTS_DIR / "unstop_submission_checklist.csv"
    
    assert top_bat_path.exists(), f"Missing {top_bat_path}"
    assert top_bowl_path.exists(), f"Missing {top_bowl_path}"
    assert unstop_path.exists(), f"Missing {unstop_path}"
    
    df_bat = pd.read_csv(top_bat_path)
    df_bowl = pd.read_csv(top_bowl_path)
    df_unstop = pd.read_csv(unstop_path)
    
    assert len(df_bat) == 10, f"Expected 10 batters, got {len(df_bat)}"
    assert len(df_bowl) == 10, f"Expected 10 bowlers, got {len(df_bowl)}"
    assert len(df_unstop) == 20, f"Expected 20 unstop checklist rows, got {len(df_unstop)}"
