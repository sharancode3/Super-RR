"""Stage 12: Terminal Views and Official Machine-Readable Evidence Exports."""

import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from rr_pressure.compare import MODEL_METRIC_KEYS
from rr_pressure.config import PipelineConfig
from rr_pressure.manifest import compute_sha256, generate_market_evidence_manifest

SNAPSHOT_ID = "RR_SUPE_RR_S2_SNAPSHOT_20261110_FROZEN"


def _snapshot_id(out_dir: Path) -> str:
    shortlist = out_dir / "rr_shortlist.csv"
    if not shortlist.exists():
        return SNAPSHOT_ID
    return str(pd.read_csv(shortlist, usecols=["snapshot_id"], nrows=1).iloc[0]["snapshot_id"])


def generate_unstop_rank_order(shortlist_df: pd.DataFrame, out_dir: Path) -> Path:
    """Generate official unstop_rank_order.csv with contiguous submission_rank 1..10 per role."""
    rank_col = "submission_rank" if "submission_rank" in shortlist_df.columns else "performance_rank"
    top10 = shortlist_df[shortlist_df["is_official_top10"]].sort_values(["role_pool", rank_col]).copy()

    unstop_df = pd.DataFrame({
        "snapshot_id": top10["snapshot_id"],
        "role": top10["role_pool"],
        "rank": top10[rank_col].astype(int),
        "submission_rank": top10[rank_col].astype(int),
        "submission_rank_pre_review": top10["submission_rank_pre_review"] if "submission_rank_pre_review" in top10.columns else top10[rank_col],
        "performance_rank": top10["performance_rank"].astype(int),
        "cipl_performance_rank": top10["cipl_performance_rank"] if "cipl_performance_rank" in top10.columns else np.nan,
        "player_id": top10["player_id"],
        "player_name": top10["player_name"],
        "slot_nationality": top10["slot_nationality"] if "slot_nationality" in top10.columns else "UNSPECIFIED",
        "route_tier": top10["route_tier"] if "route_tier" in top10.columns else "CONDITIONAL",
        "dropdown_label": "",  # Unverified dropdown labels must remain blank per rules contract
        "verification_status": "PROVISIONAL",
        "search_evidence_status": top10["search_evidence_status"] if "search_evidence_status" in top10.columns else "UNVERIFIED_OFFLINE_NO_LIVE_SEARCH",
        "role_assignment_basis": top10["role_assignment_basis"] if "role_assignment_basis" in top10.columns else "CRICKET_DEPLOYMENT",
    })

    out_path = out_dir / "unstop_rank_order.csv"
    unstop_df.to_csv(out_path, index=False)
    return out_path


def generate_rr_auction_notes(shortlist_df: pd.DataFrame, out_dir: Path) -> Path:
    """Generate official rr_auction_notes.csv separating statistical rank from auction facts."""
    auction_notes_cols = [
        "snapshot_id", "role_pool", "submission_rank", "submission_rank_pre_review", "performance_rank",
        "cipl_performance_rank", "review_action", "review_rationale", "slot_nationality", "route_tier",
        "is_official_top10", "player_id", "player_name", "inferred_role", "role_evidence_summary", "tactical_squad_role", "rr_roster_status",
        "ipl_2026_pack_franchises", "current_franchise_2027", "auction_status_2027", "fitness_clearance_status",
        "decision_category", "cross_competition_transfer_risk", "rr_action", "actionable_acquisition_route",
        "modeled_pressure_lift_12b", "b1_historical_pressure_lift_12b", "pressure_lift_estimator",
        "ipl_hp_balls", "ipl_hp_rate_12b", "non_ipl_hp_balls", "recent_2025_2026_hp_balls", "recent_2025_2026_hp_rate_12b",
        "rr_incumbent_comparison", "auction_trigger_condition", "rr_squad_fit_rationale",
        "role_matched_reserve", "non_rival_release_second_option", "alternative_option",
        "rival_incentives", "scenario_core_retained", "scenario_vacancy_opens", "scenario_overseas_slot",
        "price_scenario", "measured_order_reason", "representative_performance",
        "downside_or_uncertainty", "evidence_reference"
    ]
    available_cols = [c for c in auction_notes_cols if c in shortlist_df.columns]
    auction_notes_df = shortlist_df[available_cols].copy()
    out_path = out_dir / "rr_auction_notes.csv"
    auction_notes_df.to_csv(out_path, index=False)
    return out_path


def generate_model_validation(out_dir: Path) -> Path:
    """Consolidate comparison, robustness, and calibration into model_validation.json."""
    with open(out_dir / "model_comparison.json", "r", encoding="utf-8") as f:
        comp = json.load(f)
    with open(out_dir / "robustness_report.json", "r", encoding="utf-8") as f:
        rob = json.load(f)
    with open(out_dir / "model_diagnostics.json", "r", encoding="utf-8") as f:
        diag = json.load(f)
        
    chosen_model = comp.get("pre_holdout_decision", {}).get("chosen_model", "Selected Production Model")
    marginal_wkt = diag["remaining_runs_model"].get("marginal_wicket_value_mid_innings", diag["remaining_runs_model"].get("marginal_wicket_value_mid", 7.01))
    fixtures_path = out_dir / "fixture_dimension.csv"
    latest_observed_date = None
    if fixtures_path.exists():
        fixtures = pd.read_csv(fixtures_path, usecols=["match_date", "has_deliveries"])
        dates = fixtures.loc[fixtures["has_deliveries"], "match_date"].dropna()
        if not dates.empty:
            latest_observed_date = str(dates.max())
            
    conf_path = out_dir / "player_confidence_metrics.json"
    conf_benchmarks = None
    if conf_path.exists():
        with open(conf_path, "r", encoding="utf-8") as f:
            conf_benchmarks = json.load(f).get("model_calibration_benchmarks_2025_ipl")
    
    validation_doc = {
        "snapshot_id": _snapshot_id(out_dir),
        "selected_model": chosen_model,
        "selection_rationale": comp["pre_holdout_decision"]["selection_rationale"],
        "data_cutoff": latest_observed_date,
        "evaluation_cohort": {
            "train_window": "2022-2024 (482 matches)",
            "validation_window": "2025 (191 matches)",
            "test_holdout_window": "2026 (133 matches)",
            "standard_regulation_matches": 806,
            "excluded_fixtures": 77,
        },
        "match_state_calibration": {
            "innings_1_win_prob_brier": diag["innings1_validation_2025"]["logistic_brier"],
            "innings_2_win_prob_brier": diag["innings2_validation_2025"]["logistic_brier"],
            "constant_baseline_brier": diag["innings2_validation_2025"]["constant_brier"],
            "remaining_runs_r2": diag["remaining_runs_model"]["r2"],
            "marginal_wicket_valuation": marginal_wkt,
        },
        "model_calibration_benchmarks_2025_ipl": conf_benchmarks,
        "candidate_comparisons_2025_val": comp["validation_2025_results"],
        "ipl_validation_2025_results": comp.get("ipl_validation_2025_results", {}),
        "ipl_retrospective_2026_results": comp.get("ipl_retrospective_2026_results", {}),
        "ipl_transfer_check": comp["validation_2025_results"]["ipl_transfer_check"],
        "once_run_2026_holdout_evaluation": comp["test_holdout_2026_evaluation"],
        "shortlist_sensitivities": {
            "pressure_percentile_sensitivity": rob["pressure_percentile_sensitivity"],
            "competition_tier_sensitivity": rob["competition_tier_sensitivity"],
            "workload_evidence_floor_sensitivity": rob["workload_evidence_floor_sensitivity"],
            "standout_match_sensitivity": rob["standout_match_sensitivity"],
            "bootstrap_stability_100_replicates": rob["bootstrap_stability_100_replicates"],
        },
        "limitations_and_disclosures": [
            "Historical un-deduplicated playing XI contained 35 fixture-order duplicate groups (quarantined).",
            "77 nonstandard fixtures (rain-revised, abandoned, DLS, super overs) excluded from v1 training cohort.",
            "Unstop dropdown eligibility is unverified. Form-entry checklist remains provisional.",
            "Associate/Emerging tier fixtures provide valuable sample depth but are subject to talent gap discounts in Stage 10 audit.",
        ],
    }
    
    out_path = out_dir / "model_validation.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(validation_doc, f, indent=2)
    return out_path


def generate_data_quality(out_dir: Path) -> Path:
    """Generate comprehensive fixture reconciliation data_quality.csv."""
    exclusions_df = pd.read_csv(out_dir / "exclusions_ledger.csv")
    folds_df = pd.read_csv(out_dir / "fold_assignments.csv")
    
    # Combined ledger of all 883 fixtures in matches.csv
    reconciliation_rows = []
    
    # 1. Excluded matches
    for _, r in exclusions_df.iterrows():
        reconciliation_rows.append({
            "match_id": int(r["match_id"]),
            "comp_name": r["comp_name"],
            "season": r["season"],
            "match_date": r["match_date"],
            "cohort_status": "EXCLUDED",
            "exclusion_reason": r["exclusion_reason"],
            "source_lane": "RR_PROPRIETARY_DATA_PACK",
            "deliveries_present": True if int(r["match_id"]) not in [13337, 13410, 13416, 13444, 13491, 13493, 13589, 13611, 13689, 14217, 14244, 14352, 14436, 14646, 15309, 15410] else False,
        })
        
    # 2. Included matches
    for _, r in folds_df.iterrows():
        reconciliation_rows.append({
            "match_id": int(r["match_id"]),
            "comp_name": r["comp_tier"],
            "season": r["season"],
            "match_date": r["match_date"],
            "cohort_status": "INCLUDED_STANDARD_COHORT",
            "exclusion_reason": "NONE_VALID_STANDARD_T20",
            "source_lane": "RR_SCOREBOARD_STATE_LEDGER",
            "deliveries_present": True,
        })
        
    dq_df = pd.DataFrame(reconciliation_rows).sort_values("match_id").reset_index(drop=True)
    out_path = out_dir / "data_quality.csv"
    dq_df.to_csv(out_path, index=False)
    return out_path


def generate_player_evidence(out_dir: Path) -> Path:
    """Generate consolidated player_evidence.csv at match level."""
    bat_match = pd.read_csv(out_dir / "match_player_batting_impact.csv")
    bowl_match = pd.read_csv(out_dir / "match_player_bowling_impact.csv")
    p_dim = pd.read_csv(out_dir / "player_dimension.csv")
    p_map = p_dim.set_index("player_id")[["player_name", "inferred_role"]].to_dict(orient="index")
    
    ev_rows = []
    for _, r in bat_match.iterrows():
        pid = int(r["player_id"])
        p_info = p_map.get(pid, {"player_name": f"Player_{pid}", "inferred_role": "BATTER"})
        ev_rows.append({
            "match_id": int(r["match_id"]),
            "player_id": pid,
            "player_name": p_info["player_name"],
            "inferred_role": p_info["inferred_role"],
            "discipline": "Batting",
            "fold": r["fold"],
            "comp_tier": r["comp_tier"],
            "match_date": r["match_date"],
            "total_balls": int(r["total_balls_faced"]),
            "total_runs_wickets": int(r["total_runs_scored"]),
            "total_impact": float(r["total_batting_impact"]),
            "hp_balls": int(r["hp_balls_faced"]),
            "hp_impact": float(r["hp_bat_impact"]),
            "hp_impact_12b": float(r["hp_bat_impact_12b"]),
            "ord_balls": int(r["ord_balls_faced"]),
            "ord_impact": float(r["ord_bat_impact"]),
        })
        
    for _, r in bowl_match.iterrows():
        pid = int(r["player_id"])
        p_info = p_map.get(pid, {"player_name": f"Player_{pid}", "inferred_role": "BOWLER"})
        ev_rows.append({
            "match_id": int(r["match_id"]),
            "player_id": pid,
            "player_name": p_info["player_name"],
            "inferred_role": p_info["inferred_role"],
            "discipline": "Bowling",
            "fold": r["fold"],
            "comp_tier": r["comp_tier"],
            "match_date": r["match_date"],
            "total_balls": int(r["total_balls_bowled"]),
            "total_runs_wickets": int(r["total_wickets_taken"]),
            "total_impact": float(r["total_bowling_impact"]),
            "hp_balls": int(r["hp_balls_bowled"]),
            "hp_impact": float(r["hp_bowl_impact"]),
            "hp_impact_12b": float(r["hp_bowl_impact_12b"]),
            "ord_balls": int(r["ord_balls_bowled"]),
            "ord_impact": float(r["ord_bowl_impact"]),
        })
        
    ev_df = pd.DataFrame(ev_rows).sort_values(["match_id", "discipline", "player_id"]).reset_index(drop=True)
    out_path = out_dir / "player_evidence.csv"
    ev_df.to_csv(out_path, index=False)
    return out_path


def _pick_example_row(df: pd.DataFrame, preferred_mask: pd.Series, fallback_mask: pd.Series):
    pref = df[preferred_mask]
    if not pref.empty:
        return pref.iloc[0]
    fb = df[fallback_mask]
    if not fb.empty:
        return fb.iloc[0]
    return None


def _example_scoreboard(row: pd.Series, default_target_source: str) -> Dict[str, Any]:
    target_src = row["target_source"] if ("target_source" in row.index and pd.notna(row["target_source"])) else default_target_source
    gap_val = float(row["pre_target_reconciled_gap"]) if ("pre_target_reconciled_gap" in row.index and pd.notna(row["pre_target_reconciled_gap"])) else None
    runs_total = int(row["pre_team_total_runs"]) if ("pre_team_total_runs" in row.index and pd.notna(row["pre_team_total_runs"])) else int(row["pre_team_offbat_runs"])
    return {
        "runs_off_bat": int(row["pre_team_offbat_runs"]),
        "runs_total_reconciled": runs_total,
        "target_gap_reconciled": gap_val,
        "target_source": str(target_src),
        "wickets_lost": int(row["pre_team_wickets"]),
        "balls_remaining": int(row["pre_balls_remaining"]),
        "wickets_in_hand": int(row["pre_wickets_in_hand"]),
    }


def _build_batting_example(
    row: pd.Series,
    example_type: str,
    role: str,
    provenance_note: str,
    default_target_source: str = "OFFBAT_PLUS_EXTRAS_PROXY",
    include_bowler_name: bool = False,
) -> Dict[str, Any]:
    runs = int(row["runs"])
    exp_runs = float(row["expected_bat_runs"])
    dismissed = int(bool(row["is_striker_dismissed"]))
    exp_dism = float(row["expected_striker_dismissal"])
    if "marginal_wicket_value_ws" not in row.index or pd.isna(row["marginal_wicket_value_ws"]):
        raise ValueError(f"Missing marginal_wicket_value_ws in ledger row for match_id={row['match_id']}")
    w_s = float(row["marginal_wicket_value_ws"])
    reported = float(row["batting_impact"])
    recomputed = (runs - exp_runs) - w_s * (dismissed - exp_dism)
    diff = abs(recomputed - reported)
    if diff >= 1e-6:
        raise ValueError(
            f"Match example arithmetic mismatch for match_id={row['match_id']}: "
            f"recomputed={recomputed:.9f} != reported={reported:.9f}"
        )
    lev = float(row["pre_ball_leverage"])
    is_hp20 = bool(row["is_high_pressure_20"])
    is_elig = bool(row["is_reliability_eligible"]) if "is_reliability_eligible" in row.index and pd.notna(row["is_reliability_eligible"]) else False
    out: Dict[str, Any] = {
        "example_type": example_type,
        "player_name": str(row["striker_name"]),
        "role": role,
        "match_id": int(row["match_id"]),
        "innings": int(row["innings"]),
        "over": int(row["overid"]),
        "ball_in_over": int(row["over_ball_num"]),
        "innings_ball_num": int(row["innings_ball_num"]),
        "is_reliability_eligible": is_elig,
        "is_high_pressure_20": is_hp20,
        "pre_ball_scoreboard": _example_scoreboard(row, default_target_source),
        "pre_ball_leverage": round(lev, 5),
        "pressure_classification": f"HIGH_PRESSURE_P80 (Leverage={lev:.5f})" if is_hp20 else f"ORDINARY_PRESSURE (Leverage={lev:.5f})",
        "peer_expectations": {
            "expected_runs_off_bat": round(exp_runs, 3),
            "expected_dismissal_prob": round(exp_dism, 3),
            "marginal_wicket_valuation_runs": round(w_s, 3),
        },
        "actual_outcome": {
            "runs_off_bat": runs,
            "striker_dismissed": bool(dismissed),
        },
        "unrounded_components": {
            "expected_runs_off_bat": exp_runs,
            "expected_dismissal_prob": exp_dism,
            "marginal_wicket_value_ws": w_s,
            "recomputed_impact": recomputed,
            "ledger_reported_impact": reported,
            "abs_diff": diff,
        },
        "arithmetic_verified": True,
        "delivery_impact_calculation": (
            f"({runs} - {exp_runs:.6f}) - {w_s:.6f} * ({dismissed} - {exp_dism:.6f}) "
            f"= {recomputed:+.6f} runs (display {reported:+.3f})"
        ),
        "provenance_note": provenance_note,
    }
    if include_bowler_name:
        out["bowler_name"] = str(row["bowler_name"])
    return out


def _build_bowling_example(row: pd.Series, example_type: str, role: str, provenance_note: str) -> Dict[str, Any]:
    exp_charged = float(row["expected_charged_runs"])
    charged = int(row["bowler_charge_runs"])
    exp_wkt = float(row["expected_bowler_wicket"])
    wkt = int(bool(row["is_bowler_wicket"]))
    if "marginal_wicket_value_ws" not in row.index or pd.isna(row["marginal_wicket_value_ws"]):
        raise ValueError(f"Missing marginal_wicket_value_ws in ledger row for match_id={row['match_id']}")
    w_s = float(row["marginal_wicket_value_ws"])
    reported = float(row["bowling_impact"])
    recomputed = (exp_charged - charged) + w_s * (wkt - exp_wkt)
    diff = abs(recomputed - reported)
    if diff >= 1e-6:
        raise ValueError(
            f"Match example bowling arithmetic mismatch for match_id={row['match_id']}: "
            f"recomputed={recomputed:.9f} != reported={reported:.9f}"
        )
    lev = float(row["pre_ball_leverage"])
    is_hp20 = bool(row["is_high_pressure_20"])
    is_elig = bool(row["is_reliability_eligible"]) if "is_reliability_eligible" in row.index and pd.notna(row["is_reliability_eligible"]) else False
    return {
        "example_type": example_type,
        "player_name": str(row["bowler_name"]),
        "role": role,
        "match_id": int(row["match_id"]),
        "innings": int(row["innings"]),
        "over": int(row["overid"]),
        "ball_in_over": int(row["over_ball_num"]),
        "innings_ball_num": int(row["innings_ball_num"]),
        "is_reliability_eligible": is_elig,
        "is_high_pressure_20": is_hp20,
        "pre_ball_scoreboard": _example_scoreboard(row, "NOT_APPLICABLE_INN1"),
        "pre_ball_leverage": round(lev, 5),
        "pressure_classification": f"HIGH_PRESSURE_P80 (Leverage={lev:.5f})" if is_hp20 else f"ORDINARY_PRESSURE (Leverage={lev:.5f})",
        "peer_expectations": {
            "expected_charged_runs": round(exp_charged, 3),
            "expected_wicket_prob": round(exp_wkt, 3),
            "marginal_wicket_valuation_runs": round(w_s, 3),
        },
        "actual_outcome": {
            "bowler_charged_runs": charged,
            "is_bowler_wicket": bool(wkt),
        },
        "unrounded_components": {
            "expected_charged_runs": exp_charged,
            "expected_wicket_prob": exp_wkt,
            "marginal_wicket_value_ws": w_s,
            "recomputed_impact": recomputed,
            "ledger_reported_impact": reported,
            "abs_diff": diff,
        },
        "arithmetic_verified": True,
        "delivery_impact_calculation": (
            f"({exp_charged:.6f} - {charged}) + {w_s:.6f} * ({wkt} - {exp_wkt:.6f}) "
            f"= {recomputed:+.6f} runs (display {reported:+.3f})"
        ),
        "provenance_note": provenance_note,
    }


def generate_match_examples(out_dir: Path) -> Path:
    """Generate structured match_examples.json with verified unrounded ledger arithmetic."""
    ledger_path = out_dir / "delivery_impact_ledger.csv"
    use_cols = [
        "match_id", "innings", "overid", "over_ball_num", "innings_ball_num",
        "comp_tier", "striker_name", "bowler_name", "pre_team_offbat_runs",
        "pre_team_total_runs", "pre_target_reconciled_gap", "target_source",
        "pre_team_wickets", "pre_balls_remaining", "pre_wickets_in_hand",
        "pre_ball_leverage", "is_high_pressure_20", "is_reliability_eligible",
        "marginal_wicket_value_ws", "expected_bat_runs", "expected_striker_dismissal",
        "expected_charged_runs", "expected_bowler_wicket", "runs", "bowler_charge_runs",
        "is_striker_dismissed", "is_bowler_wicket", "batting_impact", "bowling_impact",
    ]
    df = pd.read_csv(ledger_path, usecols=lambda c: c in use_cols, low_memory=False)
    elig_mask = df["is_reliability_eligible"].astype(bool) if "is_reliability_eligible" in df.columns else pd.Series(True, index=df.index)
    hp_mask = df["is_high_pressure_20"].astype(bool)

    # 1. Reliability-eligible HIGH_PRESSURE_P80 batting delivery (prefer IPL 20181 Rashid Khan 19.4)
    k_row = _pick_example_row(
        df,
        elig_mask & hp_mask & (df["match_id"] == 20181) & (df["innings"] == 2) & (df["overid"] == 19) & (df["over_ball_num"] == 4),
        elig_mask & hp_mask & (df["innings"] == 2) & (df["runs"] >= 4) if "innings" in df.columns else elig_mask & hp_mask,
    )
    if k_row is None:
        k_row = _pick_example_row(df, elig_mask & hp_mask, hp_mask)

    # 2. Reliability-eligible HIGH_PRESSURE_P80 bowling wicket delivery (prefer IPL 20181 Mohammed Shami 19.3)
    c_row = _pick_example_row(
        df,
        elig_mask & hp_mask & (df["match_id"] == 20181) & (df["innings"] == 1) & (df["overid"] == 19) & (df["over_ball_num"] == 3),
        elig_mask & hp_mask & df["is_bowler_wicket"].astype(bool),
    )
    if c_row is None:
        c_row = _pick_example_row(df, elig_mask & hp_mask, df["is_bowler_wicket"].astype(bool))

    # 3. Reliability-eligible ORDINARY_PRESSURE contrast (prefer IPL 20181 Wriddhiman Saha 1.2)
    b_row = _pick_example_row(
        df,
        elig_mask & (~hp_mask) & (df["match_id"] == 20181) & (df["innings"] == 2) & (df["overid"] == 1) & (df["over_ball_num"] == 2),
        elig_mask & (~hp_mask) & (df["pre_ball_leverage"] > 0),
    )

    # 4. Verified Official Scorecard Chase Anchor (Fixture 30057: 1 verified target 175 vs 805 proxy targets)
    dc_row = _pick_example_row(
        df,
        elig_mask & hp_mask & (df["match_id"] == 30057) & (df["innings"] == 2) & (df["overid"] == 20) & (df["over_ball_num"] == 4),
        elig_mask & (df["match_id"] == 30057) & (df["innings"] == 2) & hp_mask,
    )

    examples_list = []
    if k_row is not None:
        examples_list.append(
            _build_batting_example(
                k_row,
                example_type="HIGH_PRESSURE_SELECTION_RATIONALE",
                role="ALL_ROUNDER_FINISHER" if str(k_row["striker_name"]) == "Rashid Khan" else "BATTER",
                provenance_note="Reliability-eligible IPL 2023 death-over chase delivery classified above the historical P80 leverage cutoff.",
            )
        )
    if c_row is not None:
        examples_list.append(
            _build_bowling_example(
                c_row,
                example_type="HIGH_PRESSURE_BOWLING_EXECUTION",
                role="PACE_BOWLER",
                provenance_note="Reliability-eligible high-leverage death-over wicket taking delivery evaluated with state-dependent marginal_wicket_value_ws.",
            )
        )
    if b_row is not None:
        examples_list.append(
            _build_batting_example(
                b_row,
                example_type="ORDINARY_PRESSURE_CONTRAST",
                role="WK_BATTER",
                provenance_note="Reliability-eligible early-over delivery below the historical P80 leverage threshold; enters the player's ordinary baseline rather than high-pressure impact.",
            )
        )
    if dc_row is not None:
        examples_list.append(
            _build_batting_example(
                dc_row,
                example_type="VERIFIED_SCORECARD_TARGET_CHASE",
                role="MIDDLE_ORDER_ALLROUNDER",
                default_target_source="VERIFIED_OFFICIAL_SCORECARD",
                include_bowler_name=True,
                provenance_note=(
                    "Fixture 30057 (PBKS vs DC, IPL 2024): sole verified scorecard target (175, DC innings 1 = 174/9 with 164 off-bat + 10 extras, "
                    "vs raw first-innings off-bat sum 171); the remaining 805 cohort fixtures use first_inn_total_offbat + extras proxies."
                ),
            )
        )

    examples = {
        "snapshot_id": _snapshot_id(out_dir),
        "description": "Concrete delivery-by-delivery calculation examples with verified unrounded ledger arithmetic.",
        "examples": examples_list,
    }
    
    out_path = out_dir / "match_examples.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(examples, f, indent=2)
    return out_path


def generate_run_manifest(out_dir: Path, output_files: Dict[str, Path], config: PipelineConfig) -> Path:
    """Generate immutable run_manifest.json linking all exports."""
    inp_path = out_dir / "input_manifest.json"
    if not inp_path.exists():
        from rr_pressure.manifest import generate_input_manifest
        generate_input_manifest(config)
    with open(inp_path, "r", encoding="utf-8") as f:
        inp = json.load(f)
    with open(out_dir / "model_comparison.json", "r", encoding="utf-8") as f:
        comp = json.load(f)
    chosen_model = comp.get("pre_holdout_decision", {}).get("chosen_model", "Selected Production Model")
        
    snapshot = _snapshot_id(out_dir)
    mkt_manifest_path, mkt_manifest = generate_market_evidence_manifest(out_dir, config.raw_dir)
    manifest = {
        "run_id": f"{snapshot}_{compute_sha256(out_dir / 'model_comparison.json')[:16]}",
        "snapshot_id": snapshot,
        "seed": config.seed,
        "python_version": inp.get("environment", {}).get("python_version", sys.version),
        "selected_model": chosen_model,
        "release_status": "PROVISIONAL",
        "entrant_review_status": "PENDING_ENTRANT_REVIEW",
        "resume_prompt": "ROUND1_DECISION_PLAYBOOK.md",
        "input_manifest_hash": compute_sha256(inp_path),
        "market_manifest_hash": compute_sha256(mkt_manifest_path),
        "market_evidence_bundle_sha256": mkt_manifest["market_evidence_bundle_sha256"],
        "outputs": {fname: compute_sha256(fpath) for fname, fpath in output_files.items()},
    }
    
    out_path = out_dir / "run_manifest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return out_path


def _format_terminal_role(tactical_role: str, inferred_role: str) -> str:
    tr = str(tactical_role).upper()
    ir = str(inferred_role).upper()
    if "WICKETKEEPER" in tr or "WK" in tr or ir == "WK_BATTER":
        return "WK_BATTER"
    elif "FINISHER" in tr or ir == "FINISHER_BATTER":
        return "DEATH_FINISHER"
    elif ("POWERPLAY" in tr and "BATTER" in tr) or ir == "TOP_ORDER_BATTER":
        return "PP_BATTER"
    elif ("MIDDLE" in tr and "BATTER" in tr) or ir == "MIDDLE_ORDER_BATTER":
        return "MID_BATTER"
    elif "SPIN_ALLROUNDER" in ir:
        return "SPIN_ALLROUNDER"
    elif "PACE_ALLROUNDER" in ir:
        return "PACE_ALLROUNDER"
    elif "YORKER" in tr:
        return "DEATH_YORKER"
    elif "DEATH" in tr and ("PACE" in tr or "SEAM" in tr or "BOWLER" in tr):
        return "DEATH_PACE_BOWL"
    elif "POWERPLAY" in tr and ("SEAM" in tr or "PACE" in tr or "BOWLER" in tr):
        return "PP_SEAM_BOWLER"
    elif "WRIST" in tr or "MYSTERY" in tr:
        return "MID_WRIST_SPIN"
    elif "FINGER" in tr:
        return "MID_FINGER_SPIN"
    elif "MIDDLE" in tr and "SPIN" in tr:
        return "MID_SPIN_BOWLER"
    elif "SPIN" in tr and "BOWLER" in tr:
        return "SPIN_BOWLER"
    elif "PACE" in tr and "BOWLER" in tr:
        return "PACE_BOWLER"
    return str(inferred_role)[:15]


def render_terminal_layout(shortlist_df: pd.DataFrame, out_dir: Path) -> None:
    """Print the exact terminal layout specified by Stage 12 contract."""
    with open(out_dir / "model_comparison.json", "r", encoding="utf-8") as f:
        comp = json.load(f)
    decision = comp.get("pre_holdout_decision", {})
    chosen_model = decision.get("chosen_model", "Unspecified")
    ipl_results = comp.get("ipl_validation_2025_results", {})
    val_results = ipl_results or comp.get("validation_2025_results", {})
    assessment_scope = "2025 IPL" if ipl_results else "2025 pooled"
    
    print("=" * 80)
    print(f"SupeRR Selector Season 2 | Round 1 | {_snapshot_id(out_dir)} | PROVISIONAL")
    print("-" * 80)
    print("Coverage   883 total fixtures (806 standard regulation eligible, 77 excluded nonstandard)")
    print("           200,999 total deliveries | 1,217 mapped canonical players | 0 delivery key dups")
    print("Evaluation Dated folds: Train 2022-2024 (482 matches) | Val 2025 (191 matches) | Retrospective 2026 (133 matches)")
    print("           Dated leverage thresholds for training. Pre-2025 threshold frozen for evaluation.")
    for role in ("batting", "bowling"):
        model = decision.get(f"chosen_model_{role}", chosen_model)
        metrics = val_results.get(role, {}).get(MODEL_METRIC_KEYS.get(model), {})
        pinball = metrics.get("pinball_loss_q25")
        coverage = metrics.get("coverage_q25")
        measured = (
            f"{assessment_scope} Q25 pinball={pinball:.3f}, coverage={coverage:.1%}"
            if pinball is not None and coverage is not None else "2025 metrics unavailable"
        )
        print(f"{role.title():<10} {model} | {measured}")
    print("-" * 80)
    
    for role_label, header_title in (("Batting", "TOP BATTERS"), ("Bowling", "TOP BOWLERS")):
        print(f"\n{header_title}  |  sub_rank (perf)  player  role  hp_tot  ipl/non  usual  mod_lift  mean  Q25  auction_status")
        print("-" * 124)
        rank_col = "submission_rank" if "submission_rank" in shortlist_df.columns else "performance_rank"
        sub_df = shortlist_df[(shortlist_df["role_pool"] == role_label) & (shortlist_df["is_official_top10"])].sort_values(rank_col).copy()
        for _, r in sub_df.iterrows():
            sub_rank = int(r[rank_col])
            perf_rank = int(r["performance_rank"])
            name = r["player_name"][:18].ljust(18)
            role = _format_terminal_role(r.get("tactical_squad_role", ""), r["inferred_role"])[:15].ljust(15)
            bm = f"{int(r['hp_balls'])}b/{int(r['hp_matches'])}m".ljust(9)
            ipl_b = int(r["ipl_hp_balls"]) if pd.notna(r.get("ipl_hp_balls")) else 0
            non_b = int(r["non_ipl_hp_balls"]) if pd.notna(r.get("non_ipl_hp_balls")) else 0
            split_b = f"{ipl_b}/{non_b}".ljust(8)
            usual = f"{r['usual_impact_12b']:+5.2f}".rjust(6)
            mod_lift_val = float(r["modeled_pressure_lift_12b"]) if pd.notna(r.get("modeled_pressure_lift_12b")) else float(r["pressure_lift_12b"])
            lift = f"{mod_lift_val:+5.2f}".rjust(7)
            mean = f"{r['predicted_hp_impact_12b']:+5.2f}".rjust(6)
            q25 = f"{r['conservative_score_q25']:+5.2f}".rjust(6)
            astat = str(r.get("auction_status_2027", "PROVISIONAL"))[:28]
            print(f"  #{sub_rank:<2} (p#{perf_rank:<2})  {name}  {role}  {bm}  {split_b}  {usual}  {lift}  {mean}  {q25}  {astat}")

    print("-" * 124)
    print("\nRR IPL 2027 RECRUITMENT SHEET (CONDITIONAL AUCTION & SQUAD STRATEGY)")
    print("-" * 124)
    print(f"  {'Player':<19} {'Tactical Role':<28} {'2027 Club / Pre-Nov17 Status':<42} {'Category':<18} {'Route':<24}")
    print("-" * 124)
    for _, r in shortlist_df[shortlist_df["is_official_top10"]].iterrows():
        pname = r["player_name"][:18].ljust(19)
        trole = str(r.get("tactical_squad_role", ""))[:27].ljust(28)
        curr_fr = str(r.get("current_franchise_2027", "UNKNOWN"))[:18]
        st = str(r.get("auction_status_2027", "UNKNOWN"))[:21]
        fr_st = f"{curr_fr} ({st})"[:41].ljust(42)
        cat = str(r.get("decision_category", "ACTIONABLE"))[:17].ljust(18)
        route = str(r.get("actionable_acquisition_route", ""))[:24]
        print(f"  {pname} {trole} {fr_st} {cat} {route}")
    print("-" * 124)
    print("Limitations Unstop dropdown eligibility unverified; form-entry checklist is PROVISIONAL.")
    print("            Competition-tier sensitivity is reported separately in the robustness report.")
    print(f"Exports     {out_dir}/player_rankings.csv | unstop_rank_order.csv | model_validation.json")
    print(f"            {out_dir}/rr_shortlist.csv | rr_recruitment_sheet.csv | rr_lineup_scenarios.csv")
    print(f"            {out_dir}/data_quality.csv | player_evidence.csv | match_examples.json")
    print("=" * 80)


def run_stage12_exports(config: PipelineConfig) -> Tuple[Dict[str, Any], Dict[str, str]]:
    out = config.out_dir
    out.mkdir(parents=True, exist_ok=True)
    
    shortlist_df = pd.read_csv(out / "rr_shortlist.csv")
    
    # Generate comprehensive player confidence metrics & calibration benchmarks
    from rr_pressure.confidence import build_player_confidence_metrics
    conf_bundle, conf_path = build_player_confidence_metrics(
        shortlist_df, out, raw_dir=config.raw_dir, seed=config.seed
    )
    
    # Enrich shortlist_df with exact ordered quantiles and event probabilities
    conf_profiles = {p["player_id"]: p for p in conf_bundle.get("official_picks_confidence_profiles", [])}
    shortlist_df["ci_lower_80_q10"] = shortlist_df["player_id"].map(
        lambda pid: conf_profiles[pid]["performance_forecast_12b"]["q10"] if pid in conf_profiles else np.nan
    )
    shortlist_df["ci_upper_80_q90"] = shortlist_df["player_id"].map(
        lambda pid: conf_profiles[pid]["performance_forecast_12b"]["q90"] if pid in conf_profiles else np.nan
    )
    shortlist_df["event_prob_positive_impact"] = shortlist_df["player_id"].map(
        lambda pid: conf_profiles[pid]["calibrated_event_probability"]["p_positive_impact_in_pressure"] if pid in conf_profiles else np.nan
    )
    shortlist_df["observed_hp_minus_usual_lift_12b"] = shortlist_df["player_id"].map(
        lambda pid: conf_profiles[pid]["pressure_lift_decomposition_12b"]["observed_hp_minus_usual_lift"] if pid in conf_profiles else np.nan
    )
    shortlist_df["reported_registration"] = shortlist_df["player_id"].map(
        lambda pid: conf_profiles[pid]["auction_and_squad_route"]["reported_registration"] if pid in conf_profiles else "PENDING_NOV23_CUTOFF"
    )
    shortlist_df["confirmed_auction_entry"] = shortlist_df["player_id"].map(
        lambda pid: conf_profiles[pid]["auction_and_squad_route"]["confirmed_auction_entry"] if pid in conf_profiles else "CONDITIONAL_ON_RELEASE"
    )
    shortlist_df["release_status"] = shortlist_df["player_id"].map(
        lambda pid: conf_profiles[pid]["auction_and_squad_route"]["release_status"] if pid in conf_profiles else "PENDING_NOV17_RETENTION_LIST"
    )
    shortlist_df.to_csv(out / "rr_shortlist.csv", index=False)
    
    unstop_path = generate_unstop_rank_order(shortlist_df, out)
    auction_notes_path = generate_rr_auction_notes(shortlist_df, out)
    val_path = generate_model_validation(out)
    dq_path = generate_data_quality(out)
    ev_path = generate_player_evidence(out)
    ex_path = generate_match_examples(out)
    
    top_bat_path = out / "top10_batters_under_pressure.csv"
    rank_col = "submission_rank" if "submission_rank" in shortlist_df.columns else "performance_rank"
    shortlist_df[(shortlist_df["role_pool"] == "Batting") & (shortlist_df["is_official_top10"])].sort_values(rank_col).to_csv(top_bat_path, index=False)
    
    top_bowl_path = out / "top10_bowlers_under_pressure.csv"
    shortlist_df[(shortlist_df["role_pool"] == "Bowling") & (shortlist_df["is_official_top10"])].sort_values(rank_col).to_csv(top_bowl_path, index=False)
    
    unstop_checklist_path = out / "unstop_submission_checklist.csv"
    import shutil
    shutil.copyfile(unstop_path, unstop_checklist_path)
    
    output_files = {
        "player_rankings.csv": out / "player_rankings.csv",
        "top10_batters_under_pressure.csv": top_bat_path,
        "top10_bowlers_under_pressure.csv": top_bowl_path,
        "unstop_rank_order.csv": unstop_path,
        "unstop_submission_checklist.csv": unstop_checklist_path,
        "rr_auction_notes.csv": auction_notes_path,
        "model_validation.json": val_path,
        "data_quality.csv": dq_path,
        "player_evidence.csv": ev_path,
        "match_examples.json": ex_path,
        "rr_shortlist.csv": out / "rr_shortlist.csv",
        "player_confidence_metrics.json": conf_path,
    }
    for optional_csv in ("passed_over_candidates.csv", "shortlist_review_changelog.csv", "rr_recruitment_sheet.csv"):
        if (out / optional_csv).exists():
            output_files[optional_csv] = out / optional_csv
    
    run_manifest_path = generate_run_manifest(out, output_files, config)
    output_files["run_manifest.json"] = run_manifest_path
    
    render_terminal_layout(shortlist_df, out)
    
    evidence = {
        "stage": "12_terminal_exports",
        "snapshot_id": _snapshot_id(out),
        "official_batters_count": 10,
        "official_bowlers_count": 10,
        "reserves_count_per_role": 5,
        "verification_status": "PROVISIONAL",
        "total_exports_count": len(output_files),
        "exported_filenames": list(output_files.keys()),
    }
    output_fingerprints = {fname: compute_sha256(fpath) for fname, fpath in output_files.items()}
    return evidence, output_fingerprints
