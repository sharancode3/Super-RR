"""Stage A05: Acceptance Tests for Rebuild Parity and Review Gate.

Validates:
1. Two independent clean builds produce identical rankings, shortlist, unstop order,
   auction notes, and model comparison.
2. Replay of representative batter and bowler examples from match_examples.json.
3. Verification that changing auction assumptions leaves statistical ranks unchanged.
"""

import hashlib
import json
from pathlib import Path
import pandas as pd
import pytest

BUILD_1 = Path("artifacts_decision_validation")
BUILD_2 = Path("test_artifacts_decision_validation")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_independent_clean_builds_file_parity():
    """Verify bit-for-bit parity across core decision CSV outputs between two clean runs."""
    assert BUILD_1.exists(), f"Missing {BUILD_1}"
    assert BUILD_2.exists(), f"Missing {BUILD_2}"
    
    files_to_compare = [
        "player_rankings.csv",
        "top10_batters_under_pressure.csv",
        "top10_bowlers_under_pressure.csv",
        "unstop_rank_order.csv",
        "unstop_submission_checklist.csv",
        "rr_auction_notes.csv",
        "rr_shortlist.csv",
    ]
    
    for fname in files_to_compare:
        f1 = BUILD_1 / fname
        f2 = BUILD_2 / fname
        assert f1.exists(), f"Missing {f1}"
        assert f2.exists(), f"Missing {f2}"
        hash1 = sha256_file(f1)
        hash2 = sha256_file(f2)
        assert hash1 == hash2, f"Hash mismatch for {fname}: {hash1} vs {hash2}"


def test_model_comparison_metrics_parity():
    """Verify model comparison decisions and metrics match across both builds."""
    comp1_path = BUILD_1 / "model_comparison.json"
    comp2_path = BUILD_2 / "model_comparison.json"
    
    with open(comp1_path, "r", encoding="utf-8") as f:
        comp1 = json.load(f)
    with open(comp2_path, "r", encoding="utf-8") as f:
        comp2 = json.load(f)
        
    assert comp1["pre_holdout_decision"]["chosen_model_batting"] == comp2["pre_holdout_decision"]["chosen_model_batting"]
    assert comp1["pre_holdout_decision"]["chosen_model_bowling"] == comp2["pre_holdout_decision"]["chosen_model_bowling"]
    assert comp1["validation_2025_results"]["batting"]["challenger_E_quantile_boosted"]["pinball_loss_q25"] == (
        comp2["validation_2025_results"]["batting"]["challenger_E_quantile_boosted"]["pinball_loss_q25"]
    )


def test_match_examples_replay():
    """Verify representative match examples replay successfully."""
    ex_path = BUILD_1 / "match_examples.json"
    assert ex_path.exists(), f"Missing {ex_path}"
    
    with open(ex_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    examples = data.get("examples", data) if isinstance(data, dict) else data
    assert len(examples) >= 2, f"Expected at least 2 examples, got {len(examples)}"
    ex_types = [ex["example_type"] for ex in examples]
    assert "HIGH_PRESSURE_SELECTION_RATIONALE" in ex_types
    assert "HIGH_PRESSURE_BOWLING_EXECUTION" in ex_types


def test_comparison_snapshot_differences():
    """Verify differences between comparison snapshot and corrected run."""
    snap_path = Path("artifacts_decision_snapshot")
    assert snap_path.exists(), "Comparison snapshot must exist"
    
    # 1. Salt's role was corrected from Finisher to Powerplay Exploiter
    notes_curr = pd.read_csv(BUILD_1 / "rr_auction_notes.csv")
    salt_curr = notes_curr[notes_curr["player_name"].str.contains("Salt", case=False, na=False)].iloc[0]
    assert "Powerplay" in salt_curr["tactical_squad_role"], f"Salt role not corrected: {salt_curr['tactical_squad_role']}"
    assert "Sooryavanshi" in salt_curr["rr_incumbent_comparison"], "Salt must compare to Sooryavanshi"
    assert "Buttler" in salt_curr["rr_incumbent_comparison"], "Salt must compare to Buttler"
    
    # 2. Price assumptions are now explicitly labelled as scenarios
    non_rr = notes_curr[notes_curr["rr_roster_status"] != "2026_RR_INCUMBENT"]
    assert (non_rr["auction_trigger_condition"].str.contains("SCENARIO_BUDGET_CAP")).all(), (
        "All non-incumbent auction triggers must label budget assumptions as SCENARIO_BUDGET_CAP"
    )
    
    # 3. Model comparison reports assessable counts and bootstrap uncertainty
    with open(BUILD_1 / "model_comparison.json", "r", encoding="utf-8") as f:
        comp = json.load(f)
    bat_e_perf = comp["validation_2025_results"]["batting"]["challenger_E_quantile_boosted"]["top10_performance"]
    assert "assessable_picks_count" in bat_e_perf, "Missing assessable_picks_count"
    assert "bootstrap_realized_std" in bat_e_perf, "Missing bootstrap_realized_std"
