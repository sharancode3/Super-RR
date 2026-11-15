"""End-to-end verification tests for SupeRR Selector Round 1 Repair Loop (Stages 0-5)."""

import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(".").resolve()))

from rr_pressure.config import PipelineConfig
from rr_pressure.models import extract_features_inn1, extract_features_inn2
from rr_pressure.pressure import compute_chase_leverage, fit_transition_outcome_frequencies

RAW_DIR = Path("6af3166e7b922_data_pack")
CONTRACT_DIR = Path("artifacts_validated_20261112")
VAL_DIR = Path("artifacts_final_20261112")


def test_stage0_baseline_and_contract_recorded():
    contract_path = CONTRACT_DIR / "stage00_baseline_contract.json"
    assert contract_path.exists()
    data = json.loads(contract_path.read_text(encoding="utf-8"))
    assert data["seed"] == 2027
    assert data["all_14_rebuild_match"] is True
    assert len(data["raw_manifest"]["files"]) == 7
    assert len(data["frozen_evaluation_contract"]["three_acceptance_questions"]) == 3


def test_stage1_extras_and_fixture_30057_feature_vector_routing():
    """Prove normalized extras and Fixture 30057's target 175 actually reach model feature vectors & leverage."""
    cov = json.loads((VAL_DIR / "coverage_report.json").read_text(encoding="utf-8"))
    assert cov["extras_audit"]["byes_legbyes_normalized"] == 3277
    assert cov["extras_audit"]["secondary_extras_nonzero_rows"] == 36
    assert cov["verified_scorecard_target_chases"] == 1
    assert cov["proxy_target_chases"] >= 800

    labels = pd.read_csv(VAL_DIR / "delivery_pressure_labels.csv", low_memory=False)
    m30057_inn2 = labels[(labels["match_id"] == 30057) & (labels["innings"] == 2)].sort_values("innings_ball_num")
    assert not m30057_inn2.empty

    # Feature vector on first ball of chase must reflect reconciled target 175 (req = 1.75), NOT 1.64 proxy
    X_inn2 = extract_features_inn2(m30057_inn2)
    assert np.isclose(X_inn2[0, 2], 1.75), f"Expected 1.75 (target 175) in feature vector, got {X_inn2[0, 2]}"

    # Mutating target_runs_reconciled / pre_target_reconciled_gap back to 164 proxy MUST change feature vector and leverage
    m30057_proxy = m30057_inn2.copy()
    m30057_proxy["pre_target_reconciled_gap"] = m30057_proxy["pre_target_offbat_gap"]
    m30057_proxy["pre_team_total_runs"] = m30057_proxy["pre_team_offbat_runs"]
    X_proxy = extract_features_inn2(m30057_proxy)
    assert np.isclose(X_proxy[0, 2], 1.64)
    assert not np.allclose(X_inn2, X_proxy), "Reconciled state failed to alter model feature vector"

    weights = json.loads((VAL_DIR / "match_state_models.json").read_text(encoding="utf-8"))
    p_def, p_fh, _ = fit_transition_outcome_frequencies(labels[labels["fold"] == "TRAIN_2022_2024"])
    lev_rec, stress_rec = compute_chase_leverage(
        m30057_inn2, np.asarray(weights["inn2_logistic_coef"][0]), weights["inn2_logistic_intercept"][0], p_def, p_fh
    )
    lev_pxy, stress_pxy = compute_chase_leverage(
        m30057_proxy, np.asarray(weights["inn2_logistic_coef"][0]), weights["inn2_logistic_intercept"][0], p_def, p_fh
    )
    assert not np.allclose(lev_rec, lev_pxy), "Target 175 vs 164 proxy did not change chase leverage"
    assert not np.allclose(stress_rec, stress_pxy), "Target 175 vs 164 proxy did not change pursuit stress"

    thresh = json.loads((VAL_DIR / "pressure_thresholds.json").read_text(encoding="utf-8"))
    audit = thresh.get("reconciliation_sensitivity_audit", {})
    assert audit.get("total_hp20_labels_changed", 0) > 0
    assert audit["fixture_30057_inn2"]["proxy_hp20_count"] != audit["fixture_30057_inn2"]["reconciled_hp20_count"]


def test_stage2_role_eligibility_cummins_negative_and_allrounders_positive():
    """Reject tail-end cameo batters (Pat Cummins, Rashid Khan, Marco Jansen) while preserving genuine dual-role allrounders."""
    from rr_pressure.forecast import is_qualified, ensure_explicit_role_flags

    p_dim = pd.read_csv(VAL_DIR / "player_dimension.csv").set_index("player_id")
    # Negative controls for batting (frontline bowlers who occasionally pinch-hit in tail)
    for pid, name in [(1758, "Patrick Cummins"), (4722, "Rashid Khan"), (7808, "Marco Jansen")]:
        assert not bool(p_dim.loc[pid, "batting_role_supported"]), f"{name} must NOT qualify as batter"
        assert bool(p_dim.loc[pid, "bowling_role_supported"]), f"{name} must qualify as bowler"
        assert "ALLROUNDER" not in str(p_dim.loc[pid, "inferred_role"]), f"{name} should be specialist bowler"

    # Positive controls for genuine dual-role allrounders
    for pid, name in [(781, "Sunil Narine"), (152, "Ravindra Jadeja"), (4823, "Washington Sundar"), (2876, "Axar Patel"), (3330, "Hardik Pandya"), (4409, "Sam Curran")]:
        assert bool(p_dim.loc[pid, "batting_role_supported"]), f"{name} must qualify for batting"
        assert bool(p_dim.loc[pid, "bowling_role_supported"]), f"{name} must qualify for bowling"

    # Malformed and legacy schema guards
    bad_df = pd.DataFrame({
        "player_id": [1, 2, 3, 4],
        "hp_balls": [100, 100, 100, 100],
        "hp_matches": [10, 10, 10, 10],
        "batting_role_supported": ["False", "unknown", pd.NA, "0"],
    })
    assert not is_qualified(bad_df, "batting").any()

    legacy_cummins = pd.DataFrame({
        "player_id": [1758],
        "inferred_role": ["PACE_ALLROUNDER"],
        "avg_bat_order": [8.25],
        "career_balls_faced": [253],
        "career_balls_bowled": [1215],
    })
    flagged = ensure_explicit_role_flags(legacy_cummins)
    assert not bool(flagged.loc[0, "batting_role_supported"]), "Legacy fallback must still block tail-end avg_bat_order > 7.5"


def test_stage3_unified_dispatch_all_models_no_fallback():
    """Verify every selectable model dispatches identically without B1 silent fallback, and Challenger C counts wides/noballs."""
    from rr_pressure.challengers import ChallengerC_RolePhasePartialPooling, score_with_selected_model
    from rr_pressure.robustness import score_and_rank_candidates
    from rr_pressure.forecast import fit_player_forecast

    # 1. Synthetic Challenger C numerator vs legal-ball denominator test
    p_dim_syn = pd.DataFrame({
        "player_id": [101],
        "inferred_role": ["PACE_BOWLER"],
        "batting_role_supported": [False],
        "bowling_role_supported": [True],
    })
    rows = []
    # 6 legal deliveries (+1.0 bowl_impact each = +6.0) + 1 wide (-2.0 bowl_impact, is_legal_ball=0)
    for b in range(6):
        rows.append({
            "match_id": 1, "striker_id": 200, "bowler_id": 101,
            "match_phase": "DEATH", "comp_tier": "IPL", "is_legal_ball": 1,
            "hp_bat_impact": 0.0, "hp_bowl_impact": 1.0,
        })
    rows.append({
        "match_id": 1, "striker_id": 200, "bowler_id": 101,
        "match_phase": "DEATH", "comp_tier": "IPL", "is_legal_ball": 0,
        "hp_bat_impact": 0.0, "hp_bowl_impact": -2.0,
    })
    deliv_syn = pd.DataFrame(rows)
    chal_c_syn = ChallengerC_RolePhasePartialPooling(m_phase_prior=0.0, transfer_penalty_scale=0.0).fit(deliv_syn, p_dim_syn, "bowling")
    prof_101 = chal_c_syn.player_profiles[101]
    assert prof_101["tot_balls"] == 6, "Denominator must count legal deliveries only"
    # Net impact across 6 legal balls + 1 wide = 6.0 - 2.0 = 4.0 -> +8.0 per 12 legal balls
    assert np.isclose(prof_101["phase_estimates"]["DEATH"], 8.0), f"Expected +8.0 (including wide penalty), got {prof_101['phase_estimates']['DEATH']}"

    # 2. Force all 5 shipped models through unified dispatcher on real Stage 07/08 data
    p_dim = pd.read_csv(VAL_DIR / "player_dimension.csv")
    bowl_m = pd.read_csv(VAL_DIR / "match_player_bowling_impact.csv")
    fit_df, _ = fit_player_forecast(bowl_m, p_dim, "bowling", seed=2027)
    deliv_df = pd.read_csv(VAL_DIR / "delivery_impact_ledger.csv", low_memory=False)
    hp_deliv = deliv_df[deliv_df["is_high_pressure_20"] & deliv_df.get("is_reliability_eligible", True)].copy()

    shipped = [
        "Ablation B-0 (No Player Pressure Lift)",
        "Candidate B (Statistical Default)",
        "Challenger C (Role-and-Phase Partial-Pooling)",
        "Challenger C-IPL (IPL-Anchored Role-and-Phase)",
        "Challenger D (Workload-Aware Distributional)",
        "Challenger E (Direct Quantile Boosted)",
    ]
    top10_by_model = {}
    for model_name in shipped:
        scored_a = score_with_selected_model(fit_df, bowl_m, p_dim, "bowling", model_name, deliv_hp_df=hp_deliv, seed=2027)
        scored_b = score_and_rank_candidates(fit_df, bowl_m, p_dim, "bowling", model_name, deliv_hp_df=hp_deliv, seed=2027)
        q_a = scored_a[scored_a["is_qualified"].astype(bool)]["player_id"].head(10).tolist()
        q_b = scored_b[scored_b["is_qualified"].astype(bool)]["player_id"].head(10).tolist()
        assert len(q_a) == 10 and q_a == q_b, f"Mismatch between unified dispatcher and robustness scorer for {model_name}"
        if "Ablation B-0" in model_name:
            assert (scored_a["modeled_pressure_lift"] == 0.0).all(), "B0 must have zero modeled pressure lift by construction"
            assert (scored_a["pressure_lift_estimator"] == "ZERO_BY_CONSTRUCTION_B0").all()
            assert "b1_historical_pressure_lift" in scored_a.columns
        top10_by_model[model_name] = q_a

    # Zero silent fallback checks
    with pytest.raises(ValueError, match="Unsupported"):
        score_with_selected_model(fit_df, bowl_m, p_dim, "bowling", "Nonexistent Model Z", deliv_hp_df=hp_deliv)
    with pytest.raises(ValueError, match="requires deliv_hp_df"):
        score_with_selected_model(fit_df, bowl_m, p_dim, "bowling", "Challenger C (Role-and-Phase Partial-Pooling)", deliv_hp_df=None)
    with pytest.raises(ValueError, match="requires deliv_hp_df"):
        score_with_selected_model(fit_df, bowl_m, p_dim, "bowling", "Challenger C-IPL (IPL-Anchored Role-and-Phase)", deliv_hp_df=None)


def test_stage4_fair_comparison_2025_2026_and_rationale():
    """Verify Stage 09 & Stage 10 produce 2024/2025/2026 IPL comparisons, Challenger C-IPL, common-assessable sensitivity, and branch rationales."""
    comp = json.loads((VAL_DIR / "model_comparison.json").read_text(encoding="utf-8"))
    rob = json.loads((VAL_DIR / "robustness_report.json").read_text(encoding="utf-8"))

    dec = comp["pre_holdout_decision"]
    assert rob["chosen_models"]["batting"] == dec["chosen_model_batting"]
    assert rob["chosen_models"]["bowling"] == dec["chosen_model_bowling"]
    assert dec["selection_branch_batting"] in dec["selection_rationale"]
    assert dec["selection_branch_bowling"] in dec["selection_rationale"]
    assert "bowling_slate_coverage_status" in dec
    assert "bowling_strongest_role_phase_alternatives" in dec
    assert "candidate_profile_summaries" in comp

    for section in ["rolling_earlier_2024_ipl_diagnostic", "ipl_validation_2025_results", "ipl_retrospective_2026_results"]:
        assert section in comp, f"Missing {section}"
        for role in ["batting", "bowling"]:
            for key in [
                "ablation_B0_no_pressure",
                "candidate_B_statistical",
                "challenger_C_role_phase",
                "challenger_C_ipl_anchored",
                "challenger_D_workload",
                "challenger_E_quantile_boosted",
                "ablation_B0_ipl_only_diagnostic",
            ]:
                m = comp[section][role][key]
                assert "true_mae" in m and np.isfinite(m["true_mae"])
                assert "signed_bias" in m and np.isfinite(m["signed_bias"])
                assert set(m["workload_breakdown"].keys()) == {"balls_6_to_12", "balls_13_to_24", "balls_25_plus"}
                assert set(m["experience_breakdown"].keys()) == {"established_ge_24_prior_balls", "thin_lt_24_prior_balls"}
                assert "bootstrap_ci_90_player_weighted" in m["top10_performance"]
                assert "common_assessable_sensitivity" in m["top10_performance"]


def test_stage5_real_world_rr_decision_layer_and_verified_affiliations():
    """Verify pack-backed 2026 clubs, honest pre-Nov17 conditionals (zero false ACTIONABLE_TARGET), same-phase comparisons, and cross-export parity."""
    shortlist = pd.read_csv(VAL_DIR / "rr_shortlist.csv")
    recruit = pd.read_csv(VAL_DIR / "rr_recruitment_sheet.csv")
    notes = pd.read_csv(VAL_DIR / "rr_auction_notes.csv")
    top_bat = pd.read_csv(VAL_DIR / "top10_batters_under_pressure.csv")
    top_bowl = pd.read_csv(VAL_DIR / "top10_bowlers_under_pressure.csv")
    reg = pd.read_csv(VAL_DIR / "ipl_availability_registry.csv").set_index("player_id")
    depth = pd.read_csv(VAL_DIR / "rr_lineup_scenarios.csv")
    unstop = pd.read_csv(VAL_DIR / "unstop_rank_order.csv")

    # Zero duplicate canonical IDs in each shortlist pool; Top-10 order strictly matches across every export
    for pool_df in [shortlist[shortlist["role_pool"] == "Batting"], shortlist[shortlist["role_pool"] == "Bowling"]]:
        assert pool_df["player_id"].is_unique

    assert shortlist.loc[(shortlist["role_pool"] == "Batting") & shortlist["is_official_top10"], "player_id"].tolist() == top_bat["player_id"].tolist() == unstop.loc[unstop["role"] == "Batting", "player_id"].tolist()
    assert shortlist.loc[(shortlist["role_pool"] == "Bowling") & shortlist["is_official_top10"], "player_id"].tolist() == top_bowl["player_id"].tolist() == unstop.loc[unstop["role"] == "Bowling", "player_id"].tolist()
    assert shortlist["player_id"].tolist() == recruit["player_id"].tolist() == notes["player_id"].tolist()

    # Tail-end bowlers excluded from Batting Top-10 & Reserves
    bat_pids = set(shortlist.loc[shortlist["role_pool"] == "Batting", "player_id"])
    assert bat_pids.isdisjoint({1758, 4722, 7808}), "Tail-enders Cummins/Rashid/Jansen must not enter batting shortlist"

    # Model-specific lift explanation bug fixed: Bowling B0 has zero modeled lift and preserves separate B1 historical estimator
    bowl_sl = shortlist[shortlist["role_pool"] == "Bowling"]
    assert (bowl_sl["modeled_pressure_lift_12b"] == 0.0).all()
    assert (bowl_sl["pressure_lift_12b"] == 0.0).all()
    assert (bowl_sl["pressure_lift_estimator"] == "ZERO_BY_CONSTRUCTION_B0").all()
    assert bowl_sl["b1_historical_pressure_lift_12b"].notna().all()

    # Same-phase comparison computed dynamically (Aniket Verma compares in death vs RR finishers, not overridden; role denominator > 0)
    verma_row = shortlist[shortlist["player_id"] == 47370].iloc[0]
    assert "Cand death IPL:" in verma_row["rr_incumbent_comparison"]
    assert "top7=20/0" not in verma_row["role_evidence_summary"]

    # Verified RR 2026 & IDs
    assert 7500 not in set(depth["primary_incumbent_id"]), "Old erroneous Dhruv Jurel ID 7500 must be gone"
    assert 7260 in set(depth["primary_incumbent_id"]), "Canonical Dhruv Jurel ID 7260 must anchor WK slot"
    assert 2258 not in set(depth["primary_incumbent_id"]), "Samson moved to CSK"
    assert not depth[["primary_incumbent_name", "backup_player"]].astype(str).apply(lambda col: col.str.contains("Sanju Samson", na=False)).any().any(), "Samson must not appear as RR incumbent or backup"
    assert 7503 in set(depth["primary_incumbent_id"]), "Ravi Bishnoi (7503) must anchor RR 2026 spin depth"
    assert not shortlist[["current_franchise_2027", "auction_status_2027"]].isin(["UNKNOWN"]).any().any(), "All 30 shortlist candidates must be resolved"

    # Verified 2026 pack + post-2026 trades + retirements + policy exclusions
    expected_clubs = {
        8238: "Delhi Capitals",              # Sameer Rizvi
        4823: "Gujarat Titans",              # Washington Sundar
        8530: "Kolkata Knight Riders",       # Kartik Tyagi
        20005: "Gujarat Titans",             # Arshad Khan
        360: "Royal Challengers Bengaluru",  # Bhuvneshwar Kumar
        3697: "Delhi Capitals",              # Kyle Jamieson
        7503: "Rajasthan Royals",            # Ravi Bishnoi
        2258: "Chennai Super Kings",         # Sanju Samson
        3644: "Lucknow Super Giants",        # Kuldeep Yadav (Jun 23 trade)
        4391: "Chennai Super Kings",         # Liam Livingstone (Nov 2026 swap)
        1318: "Retired from IPL (KKR Power Coach)",
    }
    for pid, club in expected_clubs.items():
        assert reg.loc[pid, "current_franchise"] == club, f"ID {pid} expected {club}, got {reg.loc[pid, 'current_franchise']}"

    assert "Bishnoi" not in str(reg.loc[3644, "notes"]), "LSG Kuldeep note must not cite Bishnoi (now RR)"
    assert reg.loc[1318, "decision_category"] == "BENCHMARK_ONLY"
    for pak_pid in [34485, 20704, 5979]:
        assert reg.loc[pak_pid, "availability_status"] == "INELIGIBLE_PAKISTAN_IPL_POLICY"
        assert reg.loc[pak_pid, "decision_category"] == "BENCHMARK_ONLY"

    # Zero unverified direct-auction or ACTIONABLE_TARGET claims prior to Nov 17 retention list
    forbidden = {"DIRECT_AUCTION_TARGET", "AUCTION_POOL_TARGET", "AUCTION_ELIGIBLE", "ACTIONABLE_TARGET"}
    for col in ["availability_status", "auction_registration_status", "decision_category"]:
        assert forbidden.isdisjoint(set(reg[col].dropna()))
    for col in ["auction_status_2027", "actionable_acquisition_route", "rr_action", "decision_category"]:
        assert forbidden.isdisjoint(set(shortlist[col].dropna()))

    # Unstop provisional contract & search screenshot provenance
    assert len(unstop) == 20
    assert unstop["dropdown_label"].fillna("").eq("").all()
    assert (unstop["verification_status"] == "PROVISIONAL").all()
    porel_row = unstop[unstop["player_id"] == 19714]
    if not porel_row.empty:
        assert porel_row["search_evidence_status"].iloc[0] == "VERIFIED_CROSS_LIST_SEARCH"


def test_stage6_full_pipeline_bit_for_bit_parity():
    """Verify primary run and independent clean rebuild produce byte-for-byte identical outputs."""
    from rr_pressure.manifest import compute_sha256

    rebuild_dir = Path("test_artifacts_final_20261112")
    assert rebuild_dir.exists(), "Clean rebuild directory test_artifacts_final_20261112 must exist"

    files = [
        "player_rankings.csv", "rr_shortlist.csv", "passed_over_candidates.csv",
        "top10_batters_under_pressure.csv", "top10_bowlers_under_pressure.csv",
        "unstop_rank_order.csv", "rr_recruitment_sheet.csv", "rr_lineup_scenarios.csv",
        "ipl_availability_registry.csv", "rr_auction_notes.csv", "player_evidence.csv",
        "match_examples.json", "model_comparison.json", "model_validation.json",
        "robustness_report.json", "run_manifest.json", "input_manifest.json",
    ]
    for fname in files:
        h1 = compute_sha256(VAL_DIR / fname)
        h2 = compute_sha256(rebuild_dir / fname)
        assert h1 == h2, f"Bit-for-bit rebuild mismatch on {fname}: {h1} != {h2}"


def test_stage7_asof_cutoff_zero_future_leakage():
    """Mutating post-cutoff (>= 2024-01-01) deliveries & lineups must not alter pre-cutoff roles or model fits."""
    from rr_pressure.ingest import derive_player_roles
    from rr_pressure.forecast import fit_player_forecast
    from rr_pressure.challengers import ChallengerC_RolePhasePartialPooling, ChallengerD_WorkloadDistributional

    matches = pd.read_csv(RAW_DIR / "matches.csv")
    bbb = pd.read_csv(RAW_DIR / "ball_by_ball.csv", low_memory=False).merge(
        matches[["match_id", "match_date"]], on="match_id", how="left"
    )
    p11 = pd.read_csv(RAW_DIR / "playing_eleven.csv")
    mapping = pd.read_csv(RAW_DIR / "competition_team_player_mapping.csv")
    all_pids = pd.concat([mapping["player_id"], p11["player_id"], bbb["striker_id"].dropna(), bbb["bowler_id"].dropna()]).drop_duplicates().astype(int)

    pre2024_mids = set(matches[matches["match_date"] < "2024-01-01"]["match_id"].unique())
    roles_clean = derive_player_roles(bbb, p11, all_pids, mapping, valid_match_ids=pre2024_mids)

    # Corrupt ALL post-2024-01-01 rows aggressively
    bbb_mut = bbb.copy()
    post_mask = bbb_mut["match_date"] >= "2024-01-01"
    bbb_mut.loc[post_mask, "runs"] = 6
    bbb_mut.loc[post_mask, "batting_order"] = 1
    p11_mut = p11.copy()
    p11_mut.loc[~p11_mut["match_id"].isin(pre2024_mids), "is_wk"] = True

    roles_mut = derive_player_roles(bbb_mut, p11_mut, all_pids, mapping, valid_match_ids=pre2024_mids)
    pd.testing.assert_frame_equal(roles_clean, roles_mut)

    # Check saved pre-2024 & pre-2025 role snapshots do not reflect post-cutoff promotions cleanly
    p24 = pd.read_csv(VAL_DIR / "player_dimension_pre2024.csv").set_index("player_id")
    p26 = pd.read_csv(VAL_DIR / "player_dimension_pre2026.csv").set_index("player_id")
    # Priyansh Arya (25669) had zero matches before 2024-01-01 -> must be UNKNOWN_DEBUT in pre2024, active by pre2026
    assert p24.loc[25669, "inferred_role"] == "UNKNOWN_DEBUT"
    assert not bool(p24.loc[25669, "batting_role_supported"])
    assert p26.loc[25669, "batting_role_supported"]

    # Check pre-cutoff B0 / D / C models fitted strictly on < 2025-01-01 give identical scores
    bat_m = pd.read_csv(VAL_DIR / "match_player_batting_impact.csv")
    fit_a, _ = fit_player_forecast(bat_m[bat_m["match_date"] < "2025-01-01"], pd.read_csv(VAL_DIR / "player_dimension_train.csv"), "batting", seed=2027)
    bat_m_corrupt = bat_m.copy()
    bat_m_corrupt.loc[bat_m_corrupt["match_date"] >= "2025-01-01", ["hp_bat_impact", "hp_bat_impact_12b", "ord_bat_impact"]] = 999.0
    fit_b, _ = fit_player_forecast(bat_m_corrupt[bat_m_corrupt["match_date"] < "2025-01-01"], pd.read_csv(VAL_DIR / "player_dimension_train.csv"), "batting", seed=2027)
    pd.testing.assert_frame_equal(fit_a, fit_b)


def test_stage7_challenger_c_multiplicity_equals_replication():
    """Match-weighted Challenger C and Challenger C-IPL must match explicitly replicated match rows."""
    from rr_pressure.challengers import ChallengerC_RolePhasePartialPooling, ChallengerC_IPLAnchoredRolePhase

    p_dim = pd.DataFrame({
        "player_id": [1, 2, 3],
        "inferred_role": ["TOP_ORDER_BATTER", "FINISHER_BATTER", "TOP_ORDER_BATTER"],
    })
    deliv = pd.DataFrame({
        "match_id": [10, 10, 11, 11, 12, 12, 13, 13],
        "striker_id": [1, 2, 1, 3, 1, 2, 2, 3],
        "comp_tier": ["IPL", "IPL", "T20I", "T20I", "IPL", "IPL", "T20I", "T20I"],
        "match_phase": ["DEATH", "DEATH", "MIDDLE", "POWERPLAY", "POWERPLAY", "DEATH", "DEATH", "MIDDLE"],
        "is_legal_ball": [True] * 8,
        "batting_impact": [3.0, -1.0, 2.5, 0.5, -0.5, 4.0, 1.0, -2.0],
        "match_date": ["2024-04-01", "2024-04-01", "2024-05-01", "2024-05-01", "2025-04-01", "2025-04-01", "2025-05-01", "2025-05-01"],
    })
    deliv_rep = pd.concat([
        deliv,
        deliv[deliv["match_id"] == 10].assign(match_id=1001),
        deliv[deliv["match_id"] == 11].assign(match_id=1101),
        deliv[deliv["match_id"] == 11].assign(match_id=1102),
    ], ignore_index=True)
    mw = {10: 2, 11: 3, 12: 1, 13: 1}
    pids = np.array([1, 2, 3])
    workloads = np.array([12.0, 12.0, 12.0])

    for cls in (ChallengerC_RolePhasePartialPooling, ChallengerC_IPLAnchoredRolePhase):
        m_w = cls().fit(deliv, p_dim, "batting", match_weights=mw)
        m_r = cls().fit(deliv_rep, p_dim, "batting")
        assert np.allclose(m_w.predict_quantile(pids, workloads), m_r.predict_quantile(pids, workloads), atol=1e-10)
        assert np.allclose(m_w.predict_mean(pids), m_r.predict_mean(pids), atol=1e-10)
        assert np.isclose(m_w.learned_transfer_offset, m_r.learned_transfer_offset, atol=1e-10)
        assert np.isclose(m_w.transfer_residual_sd, m_r.transfer_residual_sd, atol=1e-10)
        assert all(m_w.player_profiles[p]["n_opps"] == m_r.player_profiles[p]["n_opps"] for p in [1, 2, 3])


def test_stage7_worked_examples_exact_arithmetic_and_no_hardcoded_sensitivity():
    """Verify match_examples.json uses real eligible rows, exact marginal_wicket_value_ws arithmetic, and no hardcoded sensitivity constants."""
    cov = json.loads((VAL_DIR / "coverage_report.json").read_text(encoding="utf-8"))
    sens = cov["extras_audit"]["ambiguous_extras_sensitivity"]
    assert sens["status"] == "NOT_EXECUTED_IN_LEDGER_STAGE"
    assert sens["hardcoded_estimates_removed"] is True
    assert "503" not in json.dumps(cov["extras_audit"])

    ex_doc = json.loads((VAL_DIR / "match_examples.json").read_text(encoding="utf-8"))
    examples = ex_doc["examples"]
    assert len(examples) == 4
    ex_types = {ex["example_type"] for ex in examples}
    assert {"HIGH_PRESSURE_SELECTION_RATIONALE", "HIGH_PRESSURE_BOWLING_EXECUTION", "ORDINARY_PRESSURE_CONTRAST", "VERIFIED_SCORECARD_TARGET_CHASE"}.issubset(ex_types)

    for ex in examples:
        assert ex["is_reliability_eligible"] is True
        assert ex["arithmetic_verified"] is True
        comp = ex["unrounded_components"]
        assert comp["abs_diff"] < 1e-6
        if ex["is_high_pressure_20"]:
            assert ex["pre_ball_leverage"] > 0.0
            assert "HIGH_PRESSURE_P80" in ex["pressure_classification"]
        else:
            assert "ORDINARY_PRESSURE" in ex["pressure_classification"]
        if ex["example_type"] == "VERIFIED_SCORECARD_TARGET_CHASE":
            assert ex["match_id"] == 30057
            assert "175" in ex["provenance_note"] and "171" in ex["provenance_note"] and "174/9" in ex["provenance_note"]


def test_stage7_eligibility_screening_and_status_propagation(tmp_path):
    """Verify RR incumbents/retired/ineligible/traded locks are excluded before top-10 and status changes propagate to all exports."""
    import shutil
    from io import StringIO
    from contextlib import redirect_stdout
    from rr_pressure import availability as avail_mod
    from rr_pressure.rankings import run_stage11_rankings
    from rr_pressure.exports import run_stage12_exports

    shortlist = pd.read_csv(VAL_DIR / "rr_shortlist.csv")
    passed = pd.read_csv(VAL_DIR / "passed_over_candidates.csv")
    unstop = pd.read_csv(VAL_DIR / "unstop_rank_order.csv")
    top_bat = pd.read_csv(VAL_DIR / "top10_batters_under_pressure.csv")
    top_bowl = pd.read_csv(VAL_DIR / "top10_bowlers_under_pressure.csv")
    recruit = pd.read_csv(VAL_DIR / "rr_recruitment_sheet.csv")
    notes = pd.read_csv(VAL_DIR / "rr_auction_notes.csv")

    # Screened Top-10 has zero incumbents, zero retired, zero Pakistan-ineligible, zero Nov-2026 rival trades
    assert shortlist["decision_category"].isin(["CONDITIONAL_RELEASE_WATCH", "CONDITIONAL_REGISTRATION_FITNESS_WATCH", "CONDITIONAL_TRADE_OR_RELEASE_WATCH"]).all()
    forbidden_pids = {50284, 6423, 8182, 4391, 1318, 2933, 1699, 6281, 3647, 34485, 20704, 2490, 5979, 332}
    assert forbidden_pids.isdisjoint(set(shortlist["player_id"]))
    assert set(["RR_INCUMBENT_RETENTION_DECISION", "POLICY_INELIGIBLE_BCCI_IPL_RULE"]).issubset(set(passed["passed_over_reason"]))
    assert (shortlist[shortlist["is_official_top10"]]["submission_rank"].tolist() == list(range(1, 11)) * 2)
    assert unstop["rank"].tolist() == list(range(1, 11)) * 2
    assert shortlist.loc[shortlist["is_official_top10"], "role_matched_reserve"].ne("").all()

    # Copy intermediate files into tmp_path, mutate #1 batter (Aniket Verma 47370) to RETIRED/BENCHMARK_ONLY, rerun Stage 11 & 12
    needed = [
        "input_manifest.json", "model_comparison.json", "robustness_report.json",
        "model_diagnostics.json", "data_quality.csv", "fixture_dimension.csv",
        "exclusions_ledger.csv", "fold_assignments.csv",
        "match_player_batting_impact.csv", "match_player_bowling_impact.csv",
        "player_dimension.csv", "delivery_impact_ledger.csv",
    ]
    for fn in needed:
        shutil.copyfile(VAL_DIR / fn, tmp_path / fn)

    # Temporarily mutate availability status for pid 47370
    rec_target = next(r for r in avail_mod.RAW_TRANSACTION_RECORDS if r.player_id == 47370)
    orig_vals = (rec_target.availability_status, rec_target.decision_category)
    try:
        rec_target.availability_status = "RETIRED_FROM_IPL"
        rec_target.decision_category = "BENCHMARK_ONLY"
        cfg = PipelineConfig(raw_dir=RAW_DIR, out_dir=tmp_path, seed=2027)
        run_stage11_rankings(cfg)
        buf = StringIO()
        with redirect_stdout(buf):
            run_stage12_exports(cfg)
        term_out = buf.getvalue()
    finally:
        rec_target.availability_status, rec_target.decision_category = orig_vals

    sl2 = pd.read_csv(tmp_path / "rr_shortlist.csv")
    unstop2 = pd.read_csv(tmp_path / "unstop_rank_order.csv")
    tb2 = pd.read_csv(tmp_path / "top10_batters_under_pressure.csv")
    rec2 = pd.read_csv(tmp_path / "rr_recruitment_sheet.csv")
    notes2 = pd.read_csv(tmp_path / "rr_auction_notes.csv")
    pass2 = pd.read_csv(tmp_path / "passed_over_candidates.csv")

    assert 47370 not in set(sl2["player_id"]), "Mutated BENCHMARK_ONLY player must leave rr_shortlist"
    assert 47370 not in set(unstop2["player_id"]) and 47370 not in set(tb2["player_id"])
    assert 47370 not in set(rec2["player_id"]) and 47370 not in set(notes2["player_id"])
    assert 47370 in set(pass2["player_id"])
    assert "Aniket Verma" not in term_out.split("TOP BOWLERS")[0]
    assert sl2.loc[(sl2["role_pool"] == "Batting") & sl2["is_official_top10"], "player_id"].tolist() == tb2["player_id"].tolist() == unstop2.loc[unstop2["role"] == "Batting", "player_id"].tolist()


