"""Stage 02: Scoreboard state ledger builder and validation module."""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from rr_pressure.config import PipelineConfig
from rr_pressure.manifest import compute_sha256
from rr_pressure.progress import record_stage, get_default_progress_path


BOWLER_CREDITED_DISMISSALS = {"Bowled", "Caught", "LBW", "Stump", "Hit Wicket"}
ILLEGAL_DELIVERY_EXTRAS = {"wide", "Overstep", "Penalty", "other"}
LEGACY_EXTRA_CODES = {"Overstep": 1, "wide": 2, "legbyes": 3, "byes": 4, "other": 5, "Penalty": 7}


def build_scoreboard_ledger(config: PipelineConfig) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    raw = config.raw_dir
    out = config.out_dir
    
    # Load required data
    bbb = pd.read_csv(raw / "ball_by_ball.csv", low_memory=False)
    matches = pd.read_csv(raw / "matches.csv")
    comps = pd.read_csv(raw / "competitions.csv")
    
    # 1. Identify exclusions (DLS, revised overs, rain, super overs, abandoned)
    m_comps = matches.merge(comps, on="comp_id", how="left")
    
    abandoned_mask = m_comps["result"].str.contains("Abandoned", case=False, na=False)
    revision_mask = (
        m_comps["first_inn_revised_overs"].notna()
        | m_comps["second_inn_revised_overs"].notna()
        | m_comps["revised_target"].notna()
    )
    unusual_result_mask = m_comps["result"].str.contains(
        "DLS|D/L|Tie|No Result|Super over|Rain", case=False, na=False
    )
    
    excluded_mask = abandoned_mask | revision_mask | unusual_result_mask
    excluded_matches = m_comps[excluded_mask].copy()
    
    def get_exclusion_reason(r: pd.Series) -> str:
        reasons = []
        if pd.notna(r["result"]) and "abandoned" in str(r["result"]).lower():
            reasons.append("Abandoned")
        if pd.notna(r["first_inn_revised_overs"]) or pd.notna(r["second_inn_revised_overs"]):
            reasons.append("RevisedOvers")
        if pd.notna(r["revised_target"]):
            reasons.append("RevisedTarget")
        if pd.notna(r["result"]) and any(token in str(r["result"]).lower() for token in ["dls", "d/l"]):
            reasons.append("DLSMethod")
        if pd.notna(r["result"]) and "tie" in str(r["result"]).lower():
            reasons.append("TiedMatch")
        if pd.notna(r["result"]) and "no result" in str(r["result"]).lower():
            reasons.append("NoResult")
        if pd.notna(r["result"]) and "super over" in str(r["result"]).lower():
            reasons.append("SuperOver")
        return "; ".join(reasons) if reasons else "OtherRevision"

    excluded_matches["exclusion_reason"] = excluded_matches.apply(get_exclusion_reason, axis=1)
    
    # 2. Track quarantined discrepancies
    non_wkt_with_id = bbb[(bbb["is_wicket"] == False) & (bbb["dismissed_player_id"].notna())].copy()
    non_wkt_with_id["discrepancy_type"] = "NON_WICKET_WITH_DISMISSED_ID"
    
    wkt_without_id = bbb[(bbb["is_wicket"] == True) & (bbb["dismissed_player_id"].isna())].copy()
    wkt_without_id["discrepancy_type"] = "WICKET_WITHOUT_DISMISSED_ID"
    
    quarantined = pd.concat([non_wkt_with_id, wkt_without_id], ignore_index=True)
    
    # 3. Construct chronological state ledger
    bbb["match_id"] = bbb["match_id"].astype(int)
    bbb["innings"] = bbb["innings"].astype(int)
    bbb["innings_ball_num"] = bbb["innings_ball_num"].astype(int)
    bbb = bbb.sort_values(["match_id", "innings", "innings_ball_num"]).reset_index(drop=True)
    
    # Merge competition tier and date metadata
    fixture_meta = m_comps[["match_id", "match_date", "season", "comp_name", "match_format", "venue_id"]].copy()
    def get_tier(row):
        name = str(row["comp_name"]).upper()
        if "IPL" in name or "INDIAN PREMIER LEAGUE" in name:
            return "IPL"
        elif row["match_format"] == "T20I":
            return "T20I"
        elif "EMERGING" in name or "RISING STARS" in name:
            return "EMERGING"
        return "OTHER"
    fixture_meta["comp_tier"] = fixture_meta.apply(get_tier, axis=1)
    bbb = bbb.merge(fixture_meta[["match_id", "match_date", "season", "comp_tier", "venue_id"]], on="match_id", how="left")
    
    # Pre-calculate first innings total off-bat runs per match
    first_inn_runs = bbb[bbb["innings"] == 1].groupby("match_id")["runs"].sum().rename("first_inn_total_offbat")
    bbb = bbb.merge(first_inn_runs, on="match_id", how="left")
    bbb["first_inn_total_offbat"] = bbb["first_inn_total_offbat"].fillna(0).astype(int)
    
    # Legal ball flag: wides, oversteps, penalties, and 'other' do not consume legal balls
    bbb["is_legal_ball"] = ~bbb["extras_type"].isin(ILLEGAL_DELIVERY_EXTRAS)
    
    # Event-type breakdown (normalize both singular and plural raw spellings)
    bbb["is_wide"] = bbb["extras_type"] == "wide"
    bbb["is_noball"] = bbb["extras_type"] == "Overstep"
    bbb["is_other_noball"] = bbb["extras_type"] == "other"
    bbb["is_bye_legbye"] = bbb["extras_type"].isin(["bye", "byes", "legbye", "legbyes"])
    bbb["is_penalty"] = bbb["extras_type"] == "Penalty"
    primary = pd.to_numeric(bbb["extras1_runs"], errors="raise")
    legacy_codes = bbb["extras_type"].map(LEGACY_EXTRA_CODES).fillna(6).astype(int)
    clean_deliveries = bbb["extras_type"].isna() & primary.notna()
    normal_values = set(primary[clean_deliveries].unique())
    if 0 in normal_values and 6 in normal_values:
        raise ValueError("Mixed primary extras schemas")
    uses_recorded_runs = 0 in normal_values
    if uses_recorded_runs:
        if primary.isna().any() or primary.lt(0).any() or primary.mod(1).ne(0).any():
            raise ValueError("Recorded extras must be nonnegative whole runs")
        primary = primary.astype(int)
        bbb["extras1_category_code"] = legacy_codes
    else:
        bbb["extras1_category_code"] = primary.fillna(6).astype(int)
    bbb["extras2_secondary_runs"] = pd.to_numeric(bbb.get("extras_2_runs", 0), errors="coerce").fillna(0).astype(int)
    
    # Off-bat runs explicit labeling
    bbb["offbat_runs"] = bbb["runs"]
    
    # Wides and no-ball penalties are charged to the bowler. Byes and leg-byes go to the team only.
    charged_extra = bbb["is_wide"] | bbb["is_noball"] | bbb["is_other_noball"]
    bbb["bowler_charge_runs_proxy"] = bbb["runs"] + charged_extra.astype(int)
    bbb["bowler_charge_runs"] = (
        bbb["runs"] + primary.where(charged_extra, 0) if uses_recorded_runs else bbb["bowler_charge_runs_proxy"]
    )
    bbb["bowler_charge_certainty"] = "PACK_RECORDED_EXTRA_RUNS" if uses_recorded_runs else "PROXY_SINGLE_EXTRA"
    
    # Wicket attribution
    bbb["is_bowler_wicket"] = (
        (bbb["is_wicket"] == True)
        & (bbb["dismissal_type"].isin(BOWLER_CREDITED_DISMISSALS))
    )
    bbb["is_stumping_on_wide"] = (
        bbb["is_wide"]
        & (bbb["dismissal_type"] == "Stump")
    )
    bbb["is_run_out"] = (
        (bbb["is_wicket"] == True)
        & (bbb["dismissal_type"].isin(["RunOut", "Run Out"]))
    )
    bbb["is_striker_dismissed"] = (
        (bbb["is_wicket"] == True)
        & (bbb["dismissed_player_id"] == bbb["striker_id"])
    )
    bbb["is_non_striker_dismissed"] = (
        (bbb["is_wicket"] == True)
        & (bbb["dismissed_player_id"] == bbb["non_striker_id"])
    )
    
    # Cumulative calculations group by match_id and innings
    grp = bbb.groupby(["match_id", "innings"])
    
    bbb["pre_team_offbat_runs"] = grp["runs"].cumsum() - bbb["runs"]
    bbb["pre_team_wickets"] = grp["is_wicket"].cumsum() - bbb["is_wicket"].astype(int)
    bbb["pre_legal_balls"] = grp["is_legal_ball"].cumsum() - bbb["is_legal_ball"].astype(int)
    
    # Reconciled targets and extras tracking (includes secondary bye/legbye runs on no-balls)
    bbb["delivery_offbat_runs"] = bbb["runs"]
    proxy_primary = (
        charged_extra.astype(int)
        + bbb["is_bye_legbye"].astype(int)
        + (bbb["is_penalty"].astype(int) * 5)
    )
    bbb["delivery_extras"] = (primary if uses_recorded_runs else proxy_primary) + bbb["extras2_secondary_runs"]
    bbb["delivery_team_runs"] = bbb["runs"] + bbb["delivery_extras"]
    
    # Cumulative extras and total team runs
    bbb["pre_delivery_extras"] = grp["delivery_extras"].cumsum() - bbb["delivery_extras"]
    bbb["pre_team_total_runs"] = bbb["pre_team_offbat_runs"] + bbb["pre_delivery_extras"]
    
    # Pre-calculate first innings total extras and team runs per match
    first_inn_extras = bbb[bbb["innings"] == 1].groupby("match_id")["delivery_extras"].sum().rename("first_inn_total_extras")
    first_inn_team = bbb[bbb["innings"] == 1].groupby("match_id")["delivery_team_runs"].sum().rename("first_inn_total_team_runs")
    bbb = bbb.merge(first_inn_extras, on="match_id", how="left").merge(first_inn_team, on="match_id", how="left")
    bbb["first_inn_total_extras"] = bbb["first_inn_total_extras"].fillna(0).astype(int)
    bbb["first_inn_total_team_runs"] = bbb["first_inn_total_team_runs"].fillna(0).astype(int)

    # Official scorecard targets for verified fixtures (independently audited IPL finals & close chases)
    VERIFIED_SCORECARD_AUDIT = {
        30057: {"match_date": "2024-03-23", "fixture": "PBKS vs DC (IPL 2024)", "target": 175, "source_url": "https://www.iplt20.com/match/2024/30057", "verified_date": "2026-11-11"},
        15190: {"match_date": "2022-05-29", "fixture": "GT vs RR (IPL 2022 Final)", "target": 131, "source_url": "https://www.iplt20.com/match/2022/15190", "verified_date": "2026-11-12"},
        31292: {"match_date": "2024-05-26", "fixture": "KKR vs SRH (IPL 2024 Final)", "target": 114, "source_url": "https://www.iplt20.com/match/2024/31292", "verified_date": "2026-11-12"},
        40767: {"match_date": "2025-06-03", "fixture": "RCB vs PBKS (IPL 2025 Final)", "target": 191, "source_url": "https://www.iplt20.com/match/2025/40767", "verified_date": "2026-11-12"},
        50375: {"match_date": "2026-05-10", "fixture": "RCB vs MI (IPL 2026 M54)", "target": 167, "source_url": "https://www.iplt20.com/match/2026/50375", "verified_date": "2026-11-12"},
        50945: {"match_date": "2026-05-31", "fixture": "RCB vs GT (IPL 2026 Final)", "target": 156, "source_url": "https://www.iplt20.com/match/2026/50945", "verified_date": "2026-11-12"},
    }
    VERIFIED_SCORECARD_TARGETS = {mid: meta["target"] for mid, meta in VERIFIED_SCORECARD_AUDIT.items()}
    
    # Bounds and resources
    bbb["pre_balls_remaining"] = np.maximum(0, 120 - bbb["pre_legal_balls"])
    bbb["pre_wickets_in_hand"] = np.maximum(0, 10 - bbb["pre_team_wickets"])
    bbb["pre_over"] = (bbb["pre_legal_balls"] // 6) + 1
    bbb["pre_ball_in_over"] = (bbb["pre_legal_balls"] % 6) + 1
    
    # Match phase
    bbb["match_phase"] = pd.cut(
        bbb["pre_over"],
        bins=[0, 6, 15, 20],
        labels=["POWERPLAY", "MIDDLE", "DEATH"],
        right=True,
    )
    
    # Chase proxy target gap and reconciled target gap
    is_inn2 = bbb["innings"] == 2
    bbb["pre_target_offbat_gap"] = np.where(
        is_inn2,
        bbb["first_inn_total_offbat"] - bbb["pre_team_offbat_runs"],
        np.nan,
    )
    
    match_targets = bbb["match_id"].map(VERIFIED_SCORECARD_TARGETS)
    reconciled_targets = np.where(
        match_targets.notna(),
        match_targets,
        bbb["first_inn_total_team_runs"] + 1,
    )
    bbb["target_runs_reconciled"] = np.where(is_inn2, reconciled_targets, np.nan)
    
    target_src = pd.Series(np.nan, index=bbb.index, dtype=object)
    target_src[is_inn2 & match_targets.notna()] = "VERIFIED_OFFICIAL_SCORECARD"
    reconstructed_source = "PACK_RECORDED_EXTRAS" if uses_recorded_runs else "OFFBAT_PLUS_EXTRAS_PROXY"
    target_src[is_inn2 & match_targets.isna()] = reconstructed_source
    bbb["target_source"] = target_src
    
    target_px = pd.Series(np.nan, index=bbb.index, dtype=object)
    target_px[is_inn2 & match_targets.notna()] = "EXACT_RECONCILED"
    target_px[is_inn2 & match_targets.isna()] = "RECONSTRUCTED_PACK" if uses_recorded_runs else "ESTIMATED_PROXY"
    bbb["target_proxy_status"] = target_px
    
    bbb["pre_target_reconciled_gap"] = np.where(
        is_inn2,
        bbb["target_runs_reconciled"] - bbb["pre_team_total_runs"],
        np.nan,
    )
    
    # Vectorized fast free hit carryover loop
    match_ids = bbb["match_id"].values
    innings = bbb["innings"].values
    extras = bbb["extras_type"].values
    n = len(bbb)
    free_hits = np.zeros(n, dtype=bool)
    
    curr_fh = False
    last_mi = (match_ids[0], innings[0])
    for i in range(n):
        mi = (match_ids[i], innings[i])
        if mi != last_mi:
            curr_fh = False
            last_mi = mi
        free_hits[i] = curr_fh
        ex = extras[i]
        if ex in ("Overstep", "other"):
            curr_fh = True
        elif curr_fh:
            if ex in ("wide", "Overstep", "other"):
                curr_fh = True
            else:
                curr_fh = False
        else:
            curr_fh = False
            
    bbb["pre_free_hit"] = free_hits
    
    # Post-ball states
    bbb["post_team_offbat_runs"] = bbb["pre_team_offbat_runs"] + bbb["runs"]
    bbb["post_delivery_extras"] = bbb["pre_delivery_extras"] + bbb["delivery_extras"]
    bbb["post_team_total_runs"] = bbb["pre_team_total_runs"] + bbb["delivery_team_runs"]
    bbb["post_team_wickets"] = bbb["pre_team_wickets"] + bbb["is_wicket"].astype(int)
    bbb["post_legal_balls"] = bbb["pre_legal_balls"] + bbb["is_legal_ball"].astype(int)
    bbb["post_balls_remaining"] = np.maximum(0, 120 - bbb["post_legal_balls"])
    bbb["post_wickets_in_hand"] = np.maximum(0, 10 - bbb["post_team_wickets"])
    bbb["is_terminal_chase_delivery"] = (bbb["innings"] == 2) & (
        bbb["post_team_total_runs"] >= bbb["target_runs_reconciled"]
    )
    
    # Tag cohort eligibility and proxy route labeling
    bbb["is_cohort_eligible"] = ~bbb["match_id"].isin(excluded_matches["match_id"])
    bbb["is_exact_state"] = False
    state_route = "RR_RECORDED_EXTRAS" if uses_recorded_runs else "RR_OFFBAT_PROXY"
    bbb["state_route"] = state_route
    bbb["source_lane"] = state_route
    bbb["exact_lane_omission_reason"] = "NO_INDEPENDENT_DELIVERY_VERIFICATION" if uses_recorded_runs else "PUBLIC_BALL_ARCHIVE_UNAVAILABLE"
    
    # 4. Coverage breakdown
    eligible_bbb = bbb[bbb["is_cohort_eligible"]]
    elig_inn2 = eligible_bbb[eligible_bbb["innings"] == 2]
    coverage_report = {
        "total_deliveries": len(bbb),
        "cohort_eligible_deliveries": len(eligible_bbb),
        "total_fixtures": len(matches),
        "excluded_fixtures_count": len(excluded_matches),
        "eligible_fixtures_count": len(matches) - len(excluded_matches),
        "verified_scorecard_target_chases": int(
            elig_inn2.loc[elig_inn2["target_source"] == "VERIFIED_OFFICIAL_SCORECARD", "match_id"].nunique()
        ),
        "verified_target_audit": [
            {
                "match_id": int(mid),
                **meta,
                "proxy_reconstructed_target": int(
                    bbb.loc[(bbb["match_id"] == mid) & (bbb["innings"] == 1), "delivery_team_runs"].sum() + 1
                ) if (bbb["match_id"] == mid).any() else None,
                "discrepancy_official_minus_proxy": (
                    int(meta["target"] - (bbb.loc[(bbb["match_id"] == mid) & (bbb["innings"] == 1), "delivery_team_runs"].sum() + 1))
                    if (bbb["match_id"] == mid).any() else None
                ),
            }
            for mid, meta in VERIFIED_SCORECARD_AUDIT.items()
        ],
        "proxy_target_chases": int(
            elig_inn2.loc[elig_inn2["target_source"] == "OFFBAT_PLUS_EXTRAS_PROXY", "match_id"].nunique()
        ),
        "pack_reconstructed_target_chases": int(
            elig_inn2.loc[elig_inn2["target_source"] == "PACK_RECORDED_EXTRAS", "match_id"].nunique()
        ),
        "extras_audit": {
            "wides": int(bbb["is_wide"].sum()),
            "overstep_noballs": int(bbb["is_noball"].sum()),
            "other_noballs_proxy": int(bbb["is_other_noball"].sum()),
            "byes_legbyes_normalized": int(bbb["is_bye_legbye"].sum()),
            "penalties": int(bbb["is_penalty"].sum()),
            "secondary_extras_nonzero_rows": int((bbb["extras2_secondary_runs"] > 0).sum()),
            "secondary_extras_with_primary_noball": int(
                ((bbb["extras2_secondary_runs"] > 0) & bbb["extras_type"].isin(["Overstep", "other"])).sum()
            ),
            "secondary_extras_missing_primary": int(
                ((bbb["extras2_secondary_runs"] > 0) & bbb["extras_type"].isna()).sum()
            ),
            "extras1_runs_schema": "recorded_primary_runs" if uses_recorded_runs else "category_code_1_to_7",
            "extras2_runs_schema": "recorded_secondary_runs",
            "other_extras_certainty": "INTERPRETED_AS_NO_BALL_FROM_CONTINUING_OVER_AND_DISMISSAL_EVIDENCE",
            "ambiguous_extras_sensitivity": {
                "status": "NOT_EXECUTED_IN_LEDGER_STAGE",
                "definition": "Compare strict Overstep-only vs proxy continuing-over other-noball rule against dated input_manifest_sha256",
                "hardcoded_estimates_removed": True,
            },
        },
        "coverage_by_season": eligible_bbb["season"].value_counts().to_dict(),
        "coverage_by_tier": eligible_bbb["comp_tier"].value_counts().to_dict(),
        "coverage_by_phase": eligible_bbb["match_phase"].value_counts().to_dict(),
        "coverage_by_innings": eligible_bbb["innings"].value_counts().to_dict(),
        "quarantined_discrepancies_count": len(quarantined),
        "notes": {
            "route_used": state_route,
            "reason_for_proxy": (
                "Used primary and secondary runs from the updated pack. Official target overrides are recorded above."
                if uses_recorded_runs else
                "Legacy category codes require single-run wide, no-ball, bye and leg-bye proxies."
            ),
            "exact_score_status": "PACK_RECONSTRUCTED" if uses_recorded_runs else "WITHHELD_PROXY_FEATURE_ONLY",
        }
    }
    
    return bbb, excluded_matches, quarantined, coverage_report


def run_stage02_ledger(config: PipelineConfig) -> Tuple[Dict[str, Any], Dict[str, str]]:
    out = config.out_dir
    out.mkdir(parents=True, exist_ok=True)
    
    ledger_df, exclusions_df, quarantined_df, coverage_report = build_scoreboard_ledger(config)
    
    # Save outputs as CSV
    ledger_path = out / "delivery_ledger_proxy.csv"
    ledger_df.to_csv(ledger_path, index=False)
    
    exclusions_path = out / "exclusions_ledger.csv"
    exclusions_df.to_csv(exclusions_path, index=False)
    
    quarantined_path = out / "quarantined_discrepancies.csv"
    quarantined_df.to_csv(quarantined_path, index=False)
    
    coverage_path = out / "coverage_report.json"
    with open(coverage_path, "w", encoding="utf-8") as f:
        json.dump(coverage_report, f, indent=2)
        
    output_files = {
        "delivery_ledger_proxy.csv": ledger_path,
        "exclusions_ledger.csv": exclusions_path,
        "quarantined_discrepancies.csv": quarantined_path,
        "coverage_report.json": coverage_path,
    }
    output_fingerprints = {fname: compute_sha256(fpath) for fname, fpath in output_files.items()}
    return coverage_report, output_fingerprints
