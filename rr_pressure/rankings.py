"""Stage 11: Final Player Rankings, RR Auction Shortlist, and Eligibility Verification."""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from rr_pressure.config import PipelineConfig
from rr_pressure.forecast import fit_player_forecast, ensure_explicit_role_flags
from rr_pressure.challengers import (
    ChallengerD_WorkloadDistributional,
    ChallengerE_DirectQuantileBoosted,
    score_with_selected_model,
)
from rr_pressure.role_challenger import build_phase_observations_from_ledger
from rr_pressure.shortlist_policy import build_asof_market_snapshot, select_shortlist_by_policy
from rr_pressure.availability import (
    PLAYER_STRATEGY_MAP,
    RAW_TRANSACTION_RECORDS,
    build_ipl_availability_registry,
    build_rr_depth_chart,
    derive_decision_category,
    derive_route_tier,
    get_player_strategy,
    get_role_alternative,
)
from rr_pressure.manifest import compute_sha256

Z_25 = 0.67449
RR_2026_AUCTION_RECORD = "https://www.rajasthanroyals.com/ipl-auction"
RR_PHASE_COMPARATORS = {
    ("Batting", "POWERPLAY"): {"Vaibhav Sooryavanshi", "Yashasvi Jaiswal"},
    ("Batting", "MIDDLE"): {"Riyan Parag", "Dhruv Jurel", "Shimron Hetmyer", "Ravindra Jadeja"},
    ("Batting", "DEATH"): {"Shimron Hetmyer", "Dhruv Jurel", "Riyan Parag", "Shubham Dubey", "Ravindra Jadeja"},
    ("Bowling", "PACE"): {"Jofra Archer", "Sandeep Sharma", "Tushar Deshpande", "Nandre Burger"},
    ("Bowling", "SPIN"): {"Ravi Bishnoi", "Ravindra Jadeja"},
}


def _describe_support(r: pd.Series) -> str:
    if pd.notna(r.get("model_fit_matches")):
        return (
            f"{int(r['model_fit_matches'])} fitted pressure matches ({int(r['model_fit_hp_balls'])} balls). "
            f"Overall observed pressure exposure {int(r['hp_matches'])} matches ({int(r['hp_balls'])} balls)"
        )
    return f"{int(r['hp_matches'])} observed pressure matches ({int(r['hp_balls'])} balls)"


def _describe_order(r: pd.Series, rank: int, model: str) -> str:
    perf_rank = int(r["performance_rank"]) if pd.notna(r.get("performance_rank")) else rank
    sub_rank = int(r["submission_rank"]) if pd.notna(r.get("submission_rank")) else rank
    q25 = float(r["conservative_score_q25"])
    usual = float(r.get("usual_level", 0.0) or 0.0)
    mu_hp = float(r.get("predicted_hp_impact", usual) or usual)
    delta = mu_hp - usual
    rev_why = str(r.get("review_rationale", "")).strip()
    if "Challenger RPP" in model:
        c_txt = ""
        if pd.notna(r.get("cipl_performance_rank")):
            c_txt = f"; Challenger C-IPL comparator #{int(r['cipl_performance_rank'])} (Q25 {float(r['cipl_q25']):+.3f})"
        order = (
            f"Scouting shortlist submission #{sub_rank} ({model} model rank #{perf_rank}, "
            f"Q25 {q25:+.3f}, usual IPL baseline {usual:+.2f}, expected HP {mu_hp:+.2f}, pressure change {delta:+.2f}{c_txt})."
        )
    elif pd.notna(r.get("cipl_performance_rank")):
        c_pr = int(r["cipl_performance_rank"])
        c_q25 = float(r["cipl_q25"])
        c_mean = float(r["cipl_mean"])
        order = (
            f"Scouting shortlist submission #{sub_rank}, informed by both frozen validation baseline "
            f"{model} (model rank #{perf_rank}, Q25 {q25:+.3f}, ordinary-ball baseline {usual:+.2f}) "
            f"and IPL-anchored Challenger C-IPL (model rank #{c_pr}, Q25 {c_q25:+.3f}, mean {c_mean:+.2f})."
        )
    else:
        order = (
            f"Scouting shortlist submission #{sub_rank} ({model} model rank #{perf_rank}, "
            f"Q25 {q25:+.3f}, usual {usual:+.2f}, expected HP {mu_hp:+.2f}, pressure change {delta:+.2f} runs/12b)."
        )
        if "Ablation B-0" in model:
            order += f" Forecast uses the ordinary-ball baseline ({usual:+.2f})."
    if rev_why:
        order += f" Review rationale: {rev_why}"
    return f"{order} {_describe_support(r)}."


UNSTOP_SEARCH_EVIDENCE_PLAYERS = {
    19714: "VERIFIED_CROSS_LIST_SEARCH",  # Abishek Porel
    8530: "VERIFIED_CROSS_LIST_SEARCH",   # Kartik Tyagi
}


def _compute_exposure_splits(p_matches: pd.DataFrame, role_type: str) -> Dict[str, Any]:
    """Compute IPL-vs-transferred, ordinary-vs-HP, LOMO, and 2025-26 exposure metrics."""
    balls_col = "hp_balls_faced" if role_type == "batting" else "hp_balls_bowled"
    imp_col = "hp_bat_impact" if role_type == "batting" else "hp_bowl_impact"
    ord_balls_col = "ord_balls_faced" if role_type == "batting" else "ord_balls_bowled"
    ord_imp_col = "ord_bat_impact" if role_type == "batting" else "ord_bowl_impact"
    if p_matches.empty:
        return {
            "ipl_hp_balls": 0, "ipl_hp_rate_12b": None,
            "ipl_ord_balls": 0, "ipl_ord_rate_12b": None,
            "non_ipl_hp_balls": 0, "non_ipl_hp_rate_12b": None,
            "recent_hp_balls": 0, "recent_hp_rate_12b": None,
            "career_hp_rate_12b": None,
            "lomo_ipl_hp_balls": 0, "lomo_ipl_hp_rate_12b": None,
            "best_ipl_hp_match_id": None, "best_ipl_hp_impact": None,
        }
    ipl_m = p_matches[p_matches["comp_tier"].eq("IPL")]
    non_m = p_matches[~p_matches["comp_tier"].eq("IPL")]
    rec_m = p_matches[p_matches["match_date"].astype(str) >= "2025-01-01"]

    def _agg(sub_df: pd.DataFrame):
        b = int(sub_df[balls_col].sum()) if not sub_df.empty else 0
        rate = round(float(sub_df[imp_col].sum() / b * 12.0), 2) if b > 0 else None
        return b, rate

    ipl_b, ipl_r = _agg(ipl_m)
    ipl_ord_b = int(ipl_m[ord_balls_col].sum()) if (not ipl_m.empty and ord_balls_col in ipl_m.columns) else 0
    ipl_ord_r = (
        round(float(ipl_m[ord_imp_col].sum() / ipl_ord_b * 12.0), 2)
        if (ipl_ord_b > 0 and ord_imp_col in ipl_m.columns)
        else None
    )
    non_b, non_r = _agg(non_m)
    rec_b, rec_r = _agg(rec_m)
    _, tot_r = _agg(p_matches)

    ipl_hp_m = ipl_m[ipl_m[balls_col] > 0]
    best_mid, best_imp, lomo_b, lomo_r = None, None, 0, None
    if not ipl_hp_m.empty:
        best_row = ipl_hp_m.sort_values([imp_col, "match_id"], ascending=[False, True]).iloc[0]
        best_mid = int(best_row["match_id"])
        best_imp = round(float(best_row[imp_col]), 2)
        rem_ipl = ipl_hp_m[ipl_hp_m["match_id"] != best_mid]
        lomo_b, lomo_r = _agg(rem_ipl)

    return {
        "ipl_hp_balls": ipl_b,
        "ipl_hp_rate_12b": ipl_r,
        "ipl_ord_balls": ipl_ord_b,
        "ipl_ord_rate_12b": ipl_ord_r,
        "non_ipl_hp_balls": non_b,
        "non_ipl_hp_rate_12b": non_r,
        "recent_hp_balls": rec_b,
        "recent_hp_rate_12b": rec_r,
        "career_hp_rate_12b": tot_r,
        "lomo_ipl_hp_balls": lomo_b,
        "lomo_ipl_hp_rate_12b": lomo_r,
        "best_ipl_hp_match_id": best_mid,
        "best_ipl_hp_impact": best_imp,
    }


def _compute_left_arm_ipl_pace_summary(bowl_match_df: pd.DataFrame, p_dim: pd.DataFrame) -> str:
    """Summarize IPL HP performance of verified left-arm IPL pace comparators directly from match ledger."""
    ipl_b = (
        bowl_match_df[bowl_match_df["comp_tier"].eq("IPL")]
        .groupby("player_id")
        .agg(b=("hp_balls_bowled", "sum"), imp=("hp_bowl_impact", "sum"))
        .reset_index()
        .merge(p_dim[["player_id", "player_name"]], on="player_id", how="left")
    )
    parts = []
    for pname in ("Trent Boult", "T Natarajan", "Arshdeep Singh", "Nandre Burger"):
        sub = ipl_b[(ipl_b["player_name"] == pname) & (ipl_b["b"] > 0)]
        if not sub.empty:
            r0 = sub.iloc[0]
            rate = 12.0 * float(r0["imp"]) / float(r0["b"])
            parts.append(f"{pname} ({int(r0['b'])}b at {rate:+.2f}/12b)")
    return "; ".join(parts)


def _generate_dynamic_scout(
    r: pd.Series,
    rank: int,
    player_matches: pd.DataFrame,
    chosen_model_name: str,
    role_type: str,
    cutoff_gap_note: str = "",
    left_arm_context: str = "",
) -> Dict[str, Any]:
    disp_col = "batting_display_role" if role_type == "batting" else "bowling_display_role"
    balls_col = "hp_balls_faced" if role_type == "batting" else "hp_balls_bowled"
    imp_col = "hp_bat_impact" if role_type == "batting" else "hp_bowl_impact"

    if pd.notna(r.get(disp_col)):
        tactical_role = str(r[disp_col])
    else:
        role_raw = str(r.get("inferred_role", "UNKNOWN")).upper()
        tactical_role = role_raw.replace("_", " ").title()

    pressure_matches = player_matches[player_matches[balls_col].gt(0)]
    if not pressure_matches.empty:
        best_m = pressure_matches.nlargest(1, imp_col).iloc[0]
        noun = "balls faced under pressure" if role_type == "batting" else "balls bowled (runs prevented/wickets)"
        best_desc = (
            f"Match {best_m['match_id']} ({best_m['match_date']}, {best_m['comp_tier']}): "
            f"{best_m[imp_col]:+.2f} net runs over {int(best_m[balls_col])} {noun}."
        )
    else:
        best_desc = "No pressure appearance in the available data."

    splits = _compute_exposure_splits(player_matches, role_type)
    ipl_ord_txt = f"IPL ord: {splits['ipl_ord_balls']}b ({splits['ipl_ord_rate_12b']:+.2f}/12b)" if splits["ipl_ord_rate_12b"] is not None else "IPL ord: 0b"
    ipl_txt = f"IPL HP: {splits['ipl_hp_balls']}b ({splits['ipl_hp_rate_12b']:+.2f}/12b)" if splits["ipl_hp_rate_12b"] is not None else "IPL HP: 0b"
    non_txt = f"T20I/Emg HP: {splits['non_ipl_hp_balls']}b ({splits['non_ipl_hp_rate_12b']:+.2f}/12b)" if splits["non_ipl_hp_rate_12b"] is not None else "T20I/Emg HP: 0b"
    rec_txt = f"Recent 2025-26: {splits['recent_hp_balls']}b ({splits['recent_hp_rate_12b']:+.2f}/12b)" if splits["recent_hp_rate_12b"] is not None else "Recent 2025-26: 0b"
    lomo_txt = (
        f"LOMO IPL HP (excl. best match {splits['best_ipl_hp_match_id']}): {splits['lomo_ipl_hp_balls']}b ({splits['lomo_ipl_hp_rate_12b']:+.2f}/12b)"
        if splits["lomo_ipl_hp_rate_12b"] is not None
        else "LOMO IPL HP: 0 remaining balls"
    )

    order_reason = _describe_order(r, rank, chosen_model_name)
    downside = (
        f"Model 80% interval [{r['ci_lower_80']:.2f}, {r['ci_upper_80']:.2f}] runs/12b. "
        f"{ipl_ord_txt} | {ipl_txt} | {lomo_txt} | {non_txt} | {rec_txt}."
    )

    pid = int(r["player_id"])
    ipl_r = splits["ipl_hp_rate_12b"]
    ipl_b = splits["ipl_hp_balls"]
    modeled_lift = float(r.get("modeled_pressure_lift", 0.0 if "Ablation B-0" in chosen_model_name else r.get("pressure_lift", 0.0)) or 0.0)
    if "Ablation B-0" in chosen_model_name and ipl_r is not None and ipl_r < 0:
        downside += (
            f" DATA CONFLICT: {chosen_model_name} forces modeled_lift={modeled_lift:+.2f} and ranks on ordinary-ball prior "
            f"({float(r.get('usual_level', 0.0)):+.2f}) despite negative direct IPL HP ({ipl_r:+.2f}/12b over {ipl_b}b)."
        )
    if ipl_b < 48:
        downside += f" Small IPL HP sample ({ipl_b}b < 48b)."
    if str(r.get("route_tier", "")) == "UNVERIFIED":
        downside += " UNVERIFIED AUCTION REGISTRATION: Dec 16 Goa pool entry unconfirmed ahead of Nov 23 cutoff."
    if pid == 4373 and left_arm_context:
        downside += (
            f" Policy/NOC caution: released pre-2026 by KKR; BCB reported Nov 11 registration ahead of Nov 23 cutoff, "
            f"but final IPL auction-list inclusion and BCCI/BCB NOC clearance remain unverified. "
            f"IPL left-arm pace comparators: {left_arm_context}."
        )
    elif pid == 3644:
        downside += (
            " Route split: traded DC -> LSG on 2026-06-23 (INR 13.50 Cr); Route 1 requires direct LSG trade, "
            "while Route 2 is a lower-probability conditional Dec 16 auction bid only if released by Nov 17."
        )
    if cutoff_gap_note:
        downside += f" {cutoff_gap_note}"

    if role_type == "bowling":
        ipl_matches = player_matches[player_matches["comp_tier"] == "IPL"]
        if not ipl_matches.empty:
            last_ipl_date = str(ipl_matches["match_date"].max())
            if last_ipl_date < "2024-01-01":
                downside += f" Stale IPL warning: last IPL appearance in {last_ipl_date[:4]}."
        elif ipl_b == 0:
            downside += " Zero direct IPL evidence in pack."

    return {
        "tactical_role": tactical_role,
        "order_reason": order_reason,
        "representative_perf": best_desc,
        "downside_uncertainty": downside,
        **splits,
    }


def generate_dynamic_batter_scout(
    r: pd.Series,
    rank: int,
    player_matches: pd.DataFrame,
    chosen_model_name: str,
    cutoff_gap_note: str = "",
) -> Dict[str, Any]:
    return _generate_dynamic_scout(
        r, rank, player_matches, chosen_model_name, "batting", cutoff_gap_note=cutoff_gap_note
    )


def generate_dynamic_bowler_scout(
    r: pd.Series,
    rank: int,
    player_matches: pd.DataFrame,
    chosen_model_name: str,
    cutoff_gap_note: str = "",
    left_arm_context: str = "",
) -> Dict[str, Any]:
    return _generate_dynamic_scout(
        r,
        rank,
        player_matches,
        chosen_model_name,
        "bowling",
        cutoff_gap_note=cutoff_gap_note,
        left_arm_context=left_arm_context,
    )


def _ipl_phase_evidence(ledger_path: Path, players: pd.DataFrame) -> dict:
    columns = ["player_id", "match_phase", "matches", "balls", "impact", "player_name"]
    if not ledger_path.exists():
        return {role: pd.DataFrame(columns=columns) for role in ("Batting", "Bowling")}
    ledger = pd.read_csv(ledger_path, usecols=[
        "match_id", "comp_tier", "is_high_pressure_20", "match_phase", "is_legal_ball",
        "striker_id", "bowler_id", "hp_bat_impact", "hp_bowl_impact",
    ])
    ipl = ledger[ledger["comp_tier"].eq("IPL") & ledger["is_high_pressure_20"]]
    profiles = {}
    for role, player, impact in (("Batting", "striker_id", "hp_bat_impact"), ("Bowling", "bowler_id", "hp_bowl_impact")):
        profiles[role] = ipl.groupby([player, "match_phase"]).agg(
            matches=("match_id", "nunique"), balls=("is_legal_ball", "sum"), impact=(impact, "sum")
        ).reset_index().rename(columns={player: "player_id"}).merge(
            players[["player_id", "player_name"]], on="player_id", how="left", validate="many_to_one"
        )
    return profiles


def _auction_evidence(player: pd.Series, role: str, phases: pd.DataFrame, incumbent: bool) -> dict:
    history = phases[phases["player_id"].eq(player["player_id"]) & phases["balls"].gt(0)]
    trigger = (
        "Back within RR if retained for IPL 2027. Confirm retention and planned deployment with the official RR roster."
        if incumbent
        else "Conditional on 17 Nov retention/replacement-conversion list, 23 Nov player registration cutoff (for 16 Dec Goa auction), fitness/NOC clearance, and RR purse/OS slot fit."
    )
    if history.empty:
        return {
            "rr_incumbent_comparison": "UNCONFIRMED: Zero IPL high-pressure balls in pack for same-phase comparison.",
            "auction_trigger_condition": trigger,
            "rr_squad_fit_rationale": "Zero direct IPL phase evidence; scout IPL readiness before allocating scarce purse/OS slot.",
        }

    strongest = history.sort_values(["balls", "match_phase"], ascending=[False, True]).iloc[0]
    phase = str(strongest["match_phase"])
    cand_balls = int(strongest["balls"])
    cand_rate = 12.0 * float(strongest["impact"]) / cand_balls
    thin_cand = cand_balls < 24
    profile = f"{phase.title()} IPL HP: {cand_rate:+.2f} runs/12b over {cand_balls}b/{int(strongest['matches'])}m."
    if thin_cand:
        profile += " [UNCONFIRMED: thin <24b IPL phase sample]"

    style = str(player.get("bowler_type", "")).upper()
    inferred_role = str(player.get("inferred_role", "")).upper()
    display_role = str(player.get("batting_display_role" if role == "Batting" else "bowling_display_role", "")).upper()

    if role == "Batting":
        if "FINISHER" in inferred_role and (history["match_phase"] == "DEATH").any():
            phase_for_comp = "DEATH"
            comparator_key = "DEATH"
        elif ("TOP_ORDER" in inferred_role or "POWERPLAY" in display_role) and (history["match_phase"] == "POWERPLAY").any():
            phase_for_comp = "POWERPLAY"
            comparator_key = "POWERPLAY"
        else:
            phase_for_comp = phase
            comparator_key = phase
    else:
        comparator_key = style if style in {"PACE", "SPIN"} else ("PACE" if "SEAM" in style or "FAST" in style else "SPIN")
        phase_for_comp = phase

    cand_phase_rows = history[history["match_phase"].eq(phase_for_comp)]
    if not cand_phase_rows.empty:
        c_b = int(cand_phase_rows["balls"].sum())
        c_m = int(cand_phase_rows["matches"].max())
        c_r = 12.0 * float(cand_phase_rows["impact"].sum()) / c_b
        cand_summary = f"Cand {phase_for_comp.lower()} IPL: {c_r:+.2f}/12b ({c_b}b/{c_m}m)"
    else:
        c_b = cand_balls
        cand_summary = f"Cand {phase.lower()} IPL: {cand_rate:+.2f}/12b ({cand_balls}b)"

    names = RR_PHASE_COMPARATORS.get((role, comparator_key), set())
    peers = phases[
        phases["player_name"].isin(names) & phases["match_phase"].eq(phase_for_comp)
        & phases["balls"].gt(0) & phases["player_id"].ne(player["player_id"])
    ].sort_values(["balls", "player_id"], ascending=[False, True])

    if not peers.empty:
        peer_txts = []
        for _, peer in peers.head(2).iterrows():
            p_b = int(peer["balls"])
            p_r = 12.0 * float(peer["impact"]) / p_b
            tag = " [thin <24b]" if p_b < 24 else ""
            peer_txts.append(f"{peer['player_name']} ({p_r:+.2f}/12b, {p_b}b/{int(peer['matches'])}m){tag}")
        comparison = f"{cand_summary} vs RR {phase_for_comp.lower()} incumbent(s): " + "; ".join(peer_txts) + "."
        if role == "Batting" and phase_for_comp == "POWERPLAY":
            comparison += " Low marginal top-order urgency given settled Jaiswal-Sooryavanshi pair."
    else:
        comparison = f"{cand_summary}; no matching RR IPL {phase_for_comp.lower()} incumbent with pressure sample in pack."
    if c_b < 24:
        comparison += " [UNCONFIRMED: candidate <24b in phase]."

    return {
        "rr_incumbent_comparison": comparison,
        "auction_trigger_condition": trigger,
        "rr_squad_fit_rationale": profile,
    }


def compute_transfer_risk(p_matches: pd.DataFrame, hp_col: str) -> str:
    """Classify cross-competition transfer risk based on high-pressure ball exposure."""
    if p_matches.empty:
        return "HIGH_RISK_EMERGING_ONLY_TRANSFER"
    ipl_balls = float(p_matches.loc[p_matches["comp_tier"] == "IPL", hp_col].sum()) if "comp_tier" in p_matches.columns else 0.0
    t20i_balls = float(p_matches.loc[p_matches["comp_tier"].isin(["T20I", "INTERNATIONAL"]), hp_col].sum()) if "comp_tier" in p_matches.columns else 0.0
    if ipl_balls >= 48:
        return "LOW_RISK_DIRECT_IPL_EVIDENCE"
    elif t20i_balls >= 30 or ipl_balls >= 12:
        return "MODERATE_RISK_T20I_INTERNATIONAL_TRANSFER"
    else:
        return "HIGH_RISK_EMERGING_ONLY_TRANSFER"


def apply_production_shortlist_policy(
    frame: pd.DataFrame,
    market_snapshot: pd.DataFrame,
    discipline: str,
    policy_name: str = "RPP_IPL_VERIFIED",
    min_ipl_hp_balls: int = 24,
    min_ipl_hp_matches: int = 2,
    chosen_model_name: str = "",
    allow_rr_incumbents: bool = False,
    require_indian_majority: bool = False,
    min_indians: int = 6,
) -> pd.DataFrame:
    """Canonical Stage 11 production entrypoint delegating directly to shortlist_policy.select_shortlist_by_policy."""
    selected = select_shortlist_by_policy(
        frame,
        market_snapshot,
        policy_name=policy_name,
        min_ipl_hp_balls=min_ipl_hp_balls,
        min_ipl_hp_matches=min_ipl_hp_matches,
        discipline=str(discipline).lower(),
        allow_rr_incumbents=allow_rr_incumbents,
        require_indian_majority=require_indian_majority,
        min_indians=min_indians,
    )
    selected["current_franchise_2027"] = selected["current_franchise"]
    selected["auction_status_2027"] = selected["availability_status"]
    actions, rationales = [], []
    for _, row in selected.iterrows():
        ipl_b = int(row.get("ipl_hp_balls") or 0)
        ipl_m = int(row.get("ipl_hp_matches") or 0)
        rec_b = int(row.get("ipl_25_26_hp_balls") or 0)
        t20i_b = int(row.get("t20i_hp_balls_calc") or 0)
        ipl_r = row.get("ipl_hp_rate_calc")
        sub_r = row.get("submission_rank")
        pre_r = row.get("submission_rank_pre_review")
        reason = str(row.get("passed_over_reason") or "")
        extra_notes: List[str] = []
        if "Ablation B-0" in chosen_model_name and pd.notna(ipl_r) and float(ipl_r) < 0:
            extra_notes.append(f"conflict: direct IPL HP {float(ipl_r):+.2f}/12b < 0 while B-0 uses modeled_lift=0.0")
        if str(row.get("route_tier", "")) == "UNVERIFIED":
            extra_notes.append("unverified Dec 16 auction registration (Nov 23 cutoff)")
        elif int(row.get("player_id") or 0) == 4373:
            extra_notes.append("Nov 11 BCB reg reported; final auction list & BCCI/NOC clearance pending")
        extra_suffix = f" [{' | '.join(extra_notes)}]" if extra_notes else ""
        if pd.notna(sub_r):
            r_int = int(sub_r)
            pre_int = int(pre_r) if pd.notna(pre_r) else r_int
            if r_int <= 10:
                act = "PROMOTED" if r_int < pre_int else "RETAINED_AS_RANKED"
                why = f"Qualified under shared >=24b/2m IPL gate ({ipl_b}b/{ipl_m}m IPL HP, {rec_b}b in 2025-26){extra_suffix}"
                if r_int < pre_int:
                    why = f"Promoted pre-review #{pre_int} -> #{r_int}; " + why
            else:
                act = "RESERVE_OR_DEPTH"
                why = f"Reserve/depth rank #{r_int} ({ipl_b}b/{ipl_m}m IPL HP, {rec_b}b in 2025-26){extra_suffix}"
        elif reason == "REVIEWED_OUT_THIN_DIRECT_IPL":
            act = "DROPPED_THIN_DIRECT_IPL"
            why = (
                f"Filtered by shared IPL-proof gate (<24b or <2m direct IPL HP: {ipl_b}b/{ipl_m}m IPL, {t20i_b}b T20I); "
                "held on watchlist/reserve audit rather than automatic Top-10."
            )
        elif reason == "REVIEWED_OUT_NONPOSITIVE_DIRECT_IPL":
            ipl_r_disp = f"{float(ipl_r):+.2f}" if pd.notna(ipl_r) else "NA"
            act = "DROPPED_NONPOSITIVE_DIRECT_IPL"
            why = (
                f"Filtered by replayed RR_IPL_POSITIVE_VERIFIED gate (direct IPL HP {ipl_r_disp}/12b <= 0 over {ipl_b}b/{ipl_m}m IPL, "
                f"{t20i_b}b T20I; resolves B0 modeled_lift=0.0 conflict)."
            )
        else:
            act = "UNQUALIFIED"
            why = reason
        actions.append(act)
        rationales.append(why)
    selected["review_action"] = actions
    selected["review_rationale"] = rationales
    return selected


def run_stage11_rankings(config: PipelineConfig) -> Tuple[Dict[str, Any], Dict[str, str]]:
    out = config.out_dir
    out.mkdir(parents=True, exist_ok=True)
    
    competitions = pd.read_csv(config.raw_dir / "competitions.csv")
    teams = pd.read_csv(config.raw_dir / "teams.csv")
    mapping = pd.read_csv(config.raw_dir / "competition_team_player_mapping.csv")
    ipl_2026 = competitions.loc[competitions["comp_name"].eq("IPL 2026"), "comp_id"]
    rr_2026 = teams.loc[
        teams["comp_id"].isin(ipl_2026) & teams["team_name"].eq("Rajasthan Royals"),
        ["comp_id", "team_id"],
    ]
    if len(rr_2026) != 1:
        raise ValueError("The data pack must identify one Rajasthan Royals team in IPL 2026.")
    roster_2026 = mapping[mapping["comp_id"].isin(ipl_2026)]
    rr_2026_pids = set(roster_2026.merge(rr_2026, on=["comp_id", "team_id"])["player_id"])
    franchises_by_player = roster_2026.groupby("player_id")["team_name"].agg(
        lambda names: " / ".join(sorted(names.dropna().unique()))
    ).to_dict()

    bat_match_df = pd.read_csv(out / "match_player_batting_impact.csv")
    bowl_match_df = pd.read_csv(out / "match_player_bowling_impact.csv")
    p_dim = ensure_explicit_role_flags(pd.read_csv(out / "player_dimension.csv"))
    phase_evidence = _ipl_phase_evidence(out / "delivery_impact_ledger.csv", p_dim)
    
    # 1. Load dynamic model decision from Stage 09
    comp_data: Dict[str, Any] = {}
    comp_path = out / "model_comparison.json"
    if comp_path.exists():
        with open(comp_path, "r", encoding="utf-8") as f:
            comp_data = json.load(f)
            decision = comp_data.get("pre_holdout_decision", {})
            chosen_overall = decision.get("chosen_model", "Ablation B-0 (No Player Pressure Lift)")
            chosen_bat = decision.get("chosen_model_batting", chosen_overall)
            chosen_bowl = decision.get("chosen_model_bowling", chosen_overall)
    else:
        chosen_overall = "Ablation B-0 (No Player Pressure Lift)"
        chosen_bat = chosen_overall
        chosen_bowl = chosen_overall
        
    all_folds = ["TRAIN_2022_2024", "VAL_2025", "TEST_HOLDOUT_2026"]
    
    bat_refit, bat_diag = fit_player_forecast(bat_match_df, p_dim, "batting", seed=config.seed, folds=all_folds)
    bowl_refit, bowl_diag = fit_player_forecast(bowl_match_df, p_dim, "bowling", seed=config.seed, folds=all_folds)

    deliv_hp_df = None
    bat_obs_df = pd.read_csv(out / "player_match_phase_batting_obs.csv") if (out / "player_match_phase_batting_obs.csv").exists() else None
    bowl_obs_df = pd.read_csv(out / "player_match_phase_bowling_obs.csv") if (out / "player_match_phase_bowling_obs.csv").exists() else None
    if (out / "delivery_impact_ledger.csv").exists():
        deliv_all = pd.read_csv(out / "delivery_impact_ledger.csv", low_memory=False)
        rel_mask = deliv_all["is_reliability_eligible"].astype(bool) if "is_reliability_eligible" in deliv_all.columns else pd.Series(True, index=deliv_all.index)
        deliv_hp_df = deliv_all[deliv_all["is_high_pressure_20"] & rel_mask & deliv_all["fold"].isin(all_folds)].copy()
        if bat_obs_df is None and "Challenger RPP" in chosen_bat:
            bat_obs_df = build_phase_observations_from_ledger(deliv_all[deliv_all["fold"].isin(all_folds)], "batting")
        if bowl_obs_df is None and "Challenger RPP" in chosen_bowl:
            bowl_obs_df = build_phase_observations_from_ledger(deliv_all[deliv_all["fold"].isin(all_folds)], "bowling")

    bat_refit = score_with_selected_model(
        bat_refit,
        bat_match_df[bat_match_df["fold"].isin(all_folds)],
        p_dim,
        "batting",
        chosen_bat,
        deliv_hp_df=deliv_hp_df,
        seed=config.seed,
        obs_df=bat_obs_df,
    )
    bowl_refit = score_with_selected_model(
        bowl_refit,
        bowl_match_df[bowl_match_df["fold"].isin(all_folds)],
        p_dim,
        "bowling",
        chosen_bowl,
        deliv_hp_df=deliv_hp_df,
        seed=config.seed,
        obs_df=bowl_obs_df,
    )

    # Also evaluate Challenger C-IPL on the exact same bowling pool & attach IPL/T20I rates for review
    cipl_rank_map: Dict[int, int] = {}
    cipl_q25_map: Dict[int, float] = {}
    cipl_mean_map: Dict[int, float] = {}
    if deliv_hp_df is not None and not deliv_hp_df.empty:
        cipl_bowl = score_with_selected_model(
            bowl_refit.copy(),
            bowl_match_df[bowl_match_df["fold"].isin(all_folds)],
            p_dim,
            "bowling",
            "Challenger C-IPL (IPL-Anchored Role-and-Phase)",
            deliv_hp_df=deliv_hp_df,
            seed=config.seed,
        )
        cipl_q = cipl_bowl[cipl_bowl["is_qualified"]].drop_duplicates("player_id").copy()
        cipl_rank_map = {int(r["player_id"]): int(r["performance_rank"]) for _, r in cipl_q.iterrows()}
        cipl_q25_map = {int(r["player_id"]): float(r["conservative_score_q25"]) for _, r in cipl_q.iterrows()}
        cipl_mean_map = {int(r["player_id"]): float(r["predicted_hp_impact"]) for _, r in cipl_q.iterrows()}

    bat_ipl_rates = (
        bat_match_df[bat_match_df["comp_tier"] == "IPL"]
        .groupby("player_id")
        .agg(b=("hp_balls_faced", "sum"), imp=("hp_bat_impact", "sum"))
    )
    bat_ipl_rate_map = {
        int(pid): float(12.0 * r["imp"] / r["b"])
        for pid, r in bat_ipl_rates.iterrows()
        if r["b"] > 0
    }
    bowl_ipl_rates = (
        bowl_match_df[bowl_match_df["comp_tier"] == "IPL"]
        .groupby("player_id")
        .agg(b=("hp_balls_bowled", "sum"), imp=("hp_bowl_impact", "sum"))
    )
    bowl_ipl_rate_map = {
        int(pid): float(12.0 * r["imp"] / r["b"])
        for pid, r in bowl_ipl_rates.iterrows()
        if r["b"] > 0
    }
    bowl_t20i_map = (
        bowl_match_df[bowl_match_df["comp_tier"].isin(["T20I", "INTERNATIONAL"])]
        .groupby("player_id")["hp_balls_bowled"]
        .sum()
        .to_dict()
    )
    bat_t20i_map = (
        bat_match_df[bat_match_df["comp_tier"].isin(["T20I", "INTERNATIONAL"])]
        .groupby("player_id")["hp_balls_faced"]
        .sum()
        .to_dict()
    )

    # Derive factual IND vs OS slot nationality strictly from non-IPL pack team mappings
    non_ipl_teams = mapping[~mapping["comp_name"].astype(str).str.contains("IPL|Indian", case=False, na=False)]
    india_team_tokens = {"India", "India A", "India B", "India Blue", "India Green", "India Red", "India Under-19s"}
    os_pids = set(
        non_ipl_teams.loc[~non_ipl_teams["team_name"].isin(india_team_tokens), "player_id"].dropna().astype(int)
    )
    for rec in RAW_TRANSACTION_RECORDS:
        if any(tok in f"{rec.verified_source_franchise} {rec.current_franchise} {rec.notes}" for tok in ("Overseas", "overseas", "South Africa", "England", "Australia", "New Zealand", "Sri Lanka", "Bangladesh", "Afghanistan", "Ireland", "UAE", "West Indies", "Zimbabwe", "Pakistan", "Hong Kong")):
            os_pids.add(rec.player_id)
    for pid_key, strat_info in PLAYER_STRATEGY_MAP.items():
        ov = str(strat_info.get("scenario_overseas_slot", "")).lower()
        if "domestic" not in ov and ("consumes" in ov or ov.startswith("overseas")):
            os_pids.add(int(pid_key))

    # 2. Screen & rank full role-qualified pool using the ONE shared shortlist policy callable
    avail_map = {rec.player_id: rec for rec in RAW_TRANSACTION_RECORDS}
    market_snapshot_2027 = build_asof_market_snapshot(2027, mapping, p_dim, raw_dir=config.raw_dir)

    def _enrich_metadata_cols(row: pd.Series, disc: str) -> pd.Series:
        pid = int(row["player_id"])
        slot_nat = "OS" if pid in os_pids else "IND"
        ipl_b = float(row.get("ipl_hp_balls", 0) or 0)
        non_ipl_b = float((row.get("t20i_hp_balls", 0) or 0) + (row.get("emerging_hp_balls", 0) or 0))
        if disc == "Bowling":
            ipl_r = bowl_ipl_rate_map.get(pid, np.nan)
            t20i_b = float(bowl_t20i_map.get(pid, 0) or 0)
            cipl_pr = cipl_rank_map.get(pid, np.nan)
        else:
            ipl_r = bat_ipl_rate_map.get(pid, np.nan)
            t20i_b = float(bat_t20i_map.get(pid, 0) or 0)
            cipl_pr = np.nan
        return pd.Series({
            "slot_nationality": slot_nat,
            "hp_rate_ipl_12b": ipl_r,
            "ipl_hp_rate_calc": ipl_r,
            "non_ipl_hp_balls_calc": non_ipl_b,
            "t20i_hp_balls_calc": t20i_b,
            "cipl_performance_rank": cipl_pr,
            "cipl_q25": cipl_q25_map.get(pid, np.nan) if disc == "Bowling" else np.nan,
            "cipl_mean": cipl_mean_map.get(pid, np.nan) if disc == "Bowling" else np.nan,
        })

    bat_ipl_matches_map = (
        bat_match_df[bat_match_df["comp_tier"].eq("IPL") & bat_match_df["hp_balls_faced"].gt(0)]
        .groupby("player_id")["match_id"].nunique().to_dict()
    )
    bowl_ipl_matches_map = (
        bowl_match_df[bowl_match_df["comp_tier"].eq("IPL") & bowl_match_df["hp_balls_bowled"].gt(0)]
        .groupby("player_id")["match_id"].nunique().to_dict()
    )
    bat_refit["ipl_hp_matches"] = bat_refit["player_id"].map(bat_ipl_matches_map).fillna(0).astype(int)
    bowl_refit["ipl_hp_matches"] = bowl_refit["player_id"].map(bowl_ipl_matches_map).fillna(0).astype(int)
    bat_refit["ipl_25_26_hp_balls"] = bat_refit["player_id"].map(
        bat_match_df[bat_match_df["comp_tier"].eq("IPL") & (bat_match_df["match_date"].astype(str) >= "2025-01-01")].groupby("player_id")["hp_balls_faced"].sum()
    ).fillna(0).astype(int)
    bowl_refit["ipl_25_26_hp_balls"] = bowl_refit["player_id"].map(
        bowl_match_df[bowl_match_df["comp_tier"].eq("IPL") & (bowl_match_df["match_date"].astype(str) >= "2025-01-01")].groupby("player_id")["hp_balls_bowled"].sum()
    ).fillna(0).astype(int)

    bat_refit_raw = bat_refit.copy()
    bowl_refit_raw = bowl_refit.copy()

    def _run_prod_policy(
        frame: pd.DataFrame,
        disc_lbl: str,
        chosen_name: str,
        indian_majority: bool = False,
    ) -> pd.DataFrame:
        enriched = frame.apply(lambda row: _enrich_metadata_cols(row, disc_lbl), axis=1)
        work = frame.copy()
        for col in enriched.columns:
            work[col] = enriched[col]
        return apply_production_shortlist_policy(
            work,
            market_snapshot_2027,
            discipline=disc_lbl.lower(),
            policy_name="RR_IPL_POSITIVE_VERIFIED",
            min_ipl_hp_balls=24,
            min_ipl_hp_matches=2,
            chosen_model_name=chosen_name,
            allow_rr_incumbents=True,
            require_indian_majority=indian_majority,
            min_indians=6,
        )

    bat_refit = _run_prod_policy(bat_refit_raw, "Batting", chosen_bat)
    bowl_refit = _run_prod_policy(bowl_refit_raw, "Bowling", chosen_bowl)
    left_arm_pace_ctx = _compute_left_arm_ipl_pace_summary(bowl_match_df, p_dim)

    # Preserve performance-rank ordering among qualified before downstream slice lookups
    bat_refit["role_pool"] = "Batting"
    bowl_refit["role_pool"] = "Bowling"
    
    snapshot_inputs = pd.concat([bat_refit, bowl_refit], ignore_index=True)
    snapshot_id = "RR_SUPE_RR_S2_" + hashlib.sha256(
        snapshot_inputs.to_csv(index=False, lineterminator="\n").encode("utf-8")
    ).hexdigest()[:20]
    bat_refit["snapshot_id"] = snapshot_id
    bowl_refit["snapshot_id"] = snapshot_id
    
    bat_refit["dropdown_verification_status"] = "PROVISIONAL_PENDING_UNSTOP_DROPDOWN"
    bowl_refit["dropdown_verification_status"] = "PROVISIONAL_PENDING_UNSTOP_DROPDOWN"
    
    combined_rankings = pd.concat([bat_refit, bowl_refit], ignore_index=True)
    rankings_path = out / "player_rankings.csv"
    combined_rankings.to_csv(rankings_path, index=False)
    
    # 4. Build RR Screened Acquisition Shortlist (submission_rank 1..10 + Reserves 11..15)
    p_dim_idx = p_dim.set_index("player_id") if "player_id" in p_dim.columns else p_dim

    def _role_evidence_text(pid: int, disc_lower: str) -> str:
        if pid not in p_dim_idx.index:
            return "Role metadata missing in player_dimension."
        prow = p_dim_idx.loc[pid]
        if disc_lower == "batting":
            t7 = int(prow.get("top7_innings", 0) or 0)
            bm = int(prow.get("batting_innings", prow.get("batting_matches", 0)) or 0)
            t7s = float(prow.get("top7_share", 0.0) or 0.0)
            rt7s = float(prow.get("recent_top7_share", 0.0) or 0.0)
            ord_pos = float(prow.get("avg_bat_order", np.nan))
            bf = int(prow.get("legal_balls_faced", prow.get("career_balls_faced", 0)) or 0)
            return f"top7={t7}/{bm} ({t7s:.0%}, recent={rt7s:.0%}), avg_ord={ord_pos:.1f}, balls_faced={bf}"
        bm = int(prow.get("bowling_matches", 0) or 0)
        bb = int(prow.get("legal_balls_bowled", prow.get("career_balls_bowled", 0)) or 0)
        opm = float(prow.get("overs_per_bowling_match", 0.0) or 0.0)
        btype = str(prow.get("bowler_type", "Unknown"))
        return f"bowl_m={bm}, legal_balls={bb}, overs/m={opm:.2f}, type={btype}"

    def _build_shortlist_row(r: pd.Series, role_pool: str, cutoff_gap_note: str = "") -> Dict[str, Any]:
        disc_lower = role_pool.lower()
        balls_col = "hp_balls_faced" if disc_lower == "batting" else "hp_balls_bowled"
        match_src = bat_match_df if disc_lower == "batting" else bowl_match_df
        chosen_name = chosen_bat if disc_lower == "batting" else chosen_bowl

        pid = int(r["player_id"])
        perf_rank = int(r["performance_rank"])
        sub_rank = int(r["submission_rank"])
        is_rr = bool(r["is_rr_incumbent"])
        p_matches = match_src[match_src["player_id"] == pid]
        scout = _generate_dynamic_scout(
            r,
            sub_rank,
            p_matches,
            chosen_name,
            disc_lower,
            cutoff_gap_note=cutoff_gap_note,
            left_arm_context=left_arm_pace_ctx if disc_lower == "bowling" else "",
        )

        rec = avail_map.get(pid)
        strat = get_player_strategy(pid)

        current_franchise = str(r.get("current_franchise_2027") or (rec.current_franchise if rec else franchises_by_player.get(pid, "UNKNOWN")))
        availability_status = str(r.get("auction_status_2027") or (rec.availability_status if rec else "PENDING_NOV17_RETENTIONS"))
        fitness_status = rec.fitness_clearance_status if rec else "FIT"
        decision_cat = str(r.get("decision_category") or derive_decision_category(availability_status, rec.decision_category if rec else ""))

        tactical_role = strat.get("tactical_squad_role") or scout["tactical_role"]
        acq_route = (
            "INTERNAL_SQUAD_RETENTION" if is_rr
            else strat.get("actionable_acquisition_route") or "CONDITIONAL_AUCTION_IF_RELEASED"
        )

        rr_roster_status = "2026_RR_INCUMBENT" if pid in rr_2026_pids else "NON_RR"
        auction_evidence = _auction_evidence(r, role_pool, phase_evidence[role_pool], is_rr)
        # Never let static strategy text overwrite dynamic same-phase comparison
        incumbent_comp = auction_evidence["rr_incumbent_comparison"]
        transfer_risk = compute_transfer_risk(p_matches, balls_col)

        modeled_lift = float(r.get("modeled_pressure_lift", 0.0 if "Ablation B-0" in chosen_name else r["pressure_lift"]))
        b1_hist_lift = float(r.get("b1_historical_pressure_lift", r["pressure_lift"]))
        lift_estimator = str(
            r.get("pressure_lift_estimator", "ZERO_BY_CONSTRUCTION_B0" if "Ablation B-0" in chosen_name else "MODEL_IMPLIED_MINUS_USUAL")
        )
        alt_option = strat.get("alternative_option") or get_role_alternative(r["inferred_role"], r["player_name"])
        is_wk_flag = bool(p_dim_idx.loc[pid, "is_wk"]) if (pid in p_dim_idx.index and "is_wk" in p_dim_idx.columns) else (str(r["inferred_role"]).upper() == "WK_BATTER")

        search_status = UNSTOP_SEARCH_EVIDENCE_PLAYERS.get(pid, "UNVERIFIED_OFFLINE_NO_LIVE_SEARCH")
        return {
            "snapshot_id": snapshot_id,
            "role_pool": role_pool,
            "submission_rank": sub_rank,
            "submission_rank_pre_review": int(r["submission_rank_pre_review"]) if pd.notna(r.get("submission_rank_pre_review")) else None,
            "performance_rank": perf_rank,
            "cipl_performance_rank": int(r["cipl_performance_rank"]) if pd.notna(r.get("cipl_performance_rank")) else None,
            "cipl_q25": float(r["cipl_q25"]) if pd.notna(r.get("cipl_q25")) else None,
            "cipl_mean_12b": float(r["cipl_mean"]) if pd.notna(r.get("cipl_mean")) else None,
            "review_action": str(r.get("review_action", "")),
            "review_rationale": str(r.get("review_rationale", "")),
            "slot_nationality": str(r.get("slot_nationality", "OS")),
            "route_tier": str(r.get("route_tier", "CONDITIONAL")),
            "is_wk": is_wk_flag,
            "is_official_top10": sub_rank <= 10,
            "is_reserve": 11 <= sub_rank <= 15,
            "player_id": pid,
            "player_name": r["player_name"],
            "dropdown_label_proxy": "",  # Unverified dropdown labels must remain blank per audit contract
            "search_evidence_status": search_status,
            "role_assignment_basis": "CRICKET_DEPLOYMENT",
            "inferred_role": r["inferred_role"],
            "role_evidence_summary": _role_evidence_text(pid, disc_lower),
            "conservative_score_q25": float(r["conservative_score_q25"]),
            "predicted_hp_impact_12b": float(r["predicted_hp_impact"]),
            "pressure_lift_12b": modeled_lift,
            "modeled_pressure_lift_12b": modeled_lift,
            "b1_historical_pressure_lift_12b": b1_hist_lift,
            "pressure_lift_estimator": lift_estimator,
            "usual_impact_12b": float(r["usual_level"]),
            "hp_matches": int(r["hp_matches"]),
            "hp_balls": int(r["hp_balls"]),
            "ipl_hp_balls": scout["ipl_hp_balls"],
            "ipl_hp_rate_12b": scout["ipl_hp_rate_12b"],
            "non_ipl_hp_balls": scout["non_ipl_hp_balls"],
            "non_ipl_hp_rate_12b": scout["non_ipl_hp_rate_12b"],
            "recent_2025_2026_hp_balls": scout["recent_hp_balls"],
            "recent_2025_2026_hp_rate_12b": scout["recent_hp_rate_12b"],
            "career_hp_rate_12b": scout["career_hp_rate_12b"],
            "model_fit_matches": r.get("model_fit_matches"),
            "model_fit_hp_balls": r.get("model_fit_hp_balls"),
            "total_matches": int(r["total_matches"]),
            "tactical_squad_role": tactical_role,
            "rr_roster_status": rr_roster_status,
            "ipl_2026_pack_franchises": franchises_by_player.get(pid, "NONE_IN_2026_PACK"),
            "current_franchise_2027": current_franchise,
            "auction_status_2027": availability_status,
            "fitness_clearance_status": fitness_status,
            "decision_category": decision_cat,
            "cross_competition_transfer_risk": transfer_risk,
            "rr_action": acq_route,
            "actionable_acquisition_route": acq_route,
            "rr_incumbent_comparison": incumbent_comp,
            "auction_trigger_condition": auction_evidence.get("auction_trigger_condition", ""),
            "rr_squad_fit_rationale": auction_evidence.get("rr_squad_fit_rationale", ""),
            "alternative_option": alt_option,
            "rival_incentives": strat.get("rival_incentives", ""),
            "scenario_core_retained": strat.get("scenario_core_retained", ""),
            "scenario_vacancy_opens": strat.get("scenario_vacancy_opens", ""),
            "scenario_overseas_slot": strat.get("scenario_overseas_slot", ""),
            "price_scenario": strat.get("price_scenario", ""),
            "measured_order_reason": scout["order_reason"],
            "representative_performance": scout["representative_perf"],
            "downside_or_uncertainty": scout["downside_uncertainty"],
            "dropdown_verification_status": "PROVISIONAL",
            "entrant_ownership_note": (
                f"{chosen_name} shortlist under shared RR_IPL_POSITIVE_VERIFIED (>=48b/6m career HP, >=24b/2m IPL HP, IPL HP > 0/12b) rule; "
                "eligible RR incumbents and conditional auction options share the same performance screen. "
                "Usual baseline, expected HP, pressure change, and Q25 reported on common IPL role scale."
            ),
            "evidence_reference": f"delivery_impact_ledger.csv; {RR_2026_AUCTION_RECORD}",
        }

    shortlist_rows: List[Dict[str, Any]] = []
    passed_over_rows: List[Dict[str, Any]] = []
    changelog_rows: List[Dict[str, Any]] = []
    cutoff_diagnostics: Dict[str, Any] = {}
    for role_pool, frame in (("Batting", bat_refit), ("Bowling", bowl_refit)):
        eligible_pool = frame[frame["is_qualified"] & frame["is_eligible_acquisition"]].sort_values("submission_rank").drop_duplicates("player_id")
        top15 = eligible_pool.head(15).reset_index(drop=True)
        if len(top15) >= 11:
            r10 = top15.iloc[9]
            r11 = top15.iloc[10]
            cutoff_diagnostics[role_pool.lower()] = {
                "rank10_player": str(r10["player_name"]),
                "rank10_q25": round(float(r10["conservative_score_q25"]), 4),
                "rank11_player": str(r11["player_name"]),
                "rank11_q25": round(float(r11["conservative_score_q25"]), 4),
                "q25_gap_10_vs_11": round(float(r10["conservative_score_q25"] - r11["conservative_score_q25"]), 4),
            }
        for i, r in top15.iterrows():
            gap_parts: List[str] = []
            q_here = float(r["conservative_score_q25"])
            if i + 1 < len(top15):
                nxt = top15.iloc[i + 1]
                diff_nxt = q_here - float(nxt["conservative_score_q25"])
                if diff_nxt < 0.05 or i == 9:
                    gap_parts.append(f"Cutoff/near-tie vs #{int(nxt['submission_rank'])} {nxt['player_name']}: +{diff_nxt:.3f} Q25")
            if i > 0:
                prv = top15.iloc[i - 1]
                diff_prv = float(prv["conservative_score_q25"]) - q_here
                if diff_prv < 0.05 or i == 10:
                    gap_parts.append(f"Cutoff/near-tie vs #{int(prv['submission_rank'])} {prv['player_name']}: -{diff_prv:.3f} Q25")
            shortlist_rows.append(_build_shortlist_row(r, role_pool, cutoff_gap_note="; ".join(gap_parts)))

        # Audit changelog across top 15 pre/post review, C-IPL top 15 (Bowling), and key audit cases
        audit_ids = {4904, 6628, 8530, 4487, 2985, 6523, 7741, 3605, 47370, 19714, 5553, 4246, 3782}
        in_scope = frame["is_qualified"] & (
            frame["submission_rank"].le(15).fillna(False)
            | frame["submission_rank_pre_review"].le(15).fillna(False)
            | frame["player_id"].isin(audit_ids)
            | (frame["cipl_performance_rank"].le(15).fillna(False) if role_pool == "Bowling" else False)
        )
        for _, r in frame[in_scope].drop_duplicates("player_id").sort_values(
            ["submission_rank", "performance_rank"], na_position="last"
        ).iterrows():
            pid = int(r["player_id"])
            r_matches = (bat_match_df if role_pool == "Batting" else bowl_match_df)
            p_m = r_matches[r_matches["player_id"] == pid]
            ev_txt = _auction_evidence(r, role_pool, phase_evidence[role_pool], bool(r["is_rr_incumbent"]))["rr_incumbent_comparison"]
            pre_r = int(r["submission_rank_pre_review"]) if pd.notna(r.get("submission_rank_pre_review")) else None
            new_r = int(r["submission_rank"]) if pd.notna(r.get("submission_rank")) else None
            b0_pr = int(r["performance_rank"]) if pd.notna(r.get("performance_rank")) else None
            c_pr = int(r["cipl_performance_rank"]) if pd.notna(r.get("cipl_performance_rank")) else None
            action = str(r.get("review_action", "")) or str(r.get("passed_over_reason", ""))
            if pre_r is not None and new_r is not None and action in ("RETAINED_AS_RANKED", ""):
                if new_r < pre_r:
                    action = "PROMOTED"
                elif new_r > pre_r:
                    action = "DEMOTED"
            changelog_rows.append({
                "snapshot_id": snapshot_id,
                "role_pool": role_pool,
                "player_id": pid,
                "player_name": str(r["player_name"]),
                "slot_nationality": str(r.get("slot_nationality", "OS")),
                "inferred_role": str(r["inferred_role"]),
                "pre_review_sub_rank": pre_r,
                "reviewed_sub_rank": new_r,
                "model_performance_rank": b0_pr,
                "cipl_performance_rank": c_pr,
                "ipl_hp_balls": int(r.get("ipl_hp_balls", 0) or 0),
                "t20i_hp_balls": int(r.get("t20i_hp_balls_calc", 0) or 0),
                "ipl_hp_rate_12b": round(float(r["ipl_hp_rate_calc"]), 2) if pd.notna(r.get("ipl_hp_rate_calc")) else None,
                "same_phase_vs_rr_incumbent": ev_txt,
                "current_franchise_2027": str(r.get("current_franchise_2027", "")),
                "route_tier": str(r.get("route_tier", "")),
                "acquisition_condition": str(r.get("auction_status_2027", "")),
                "review_action": action,
                "change_reason": str(r.get("review_rationale") or r.get("passed_over_reason") or "Preserved baseline screen order."),
            })

        max_perf = max(
            float(top15["performance_rank"].max()) if not top15.empty else 0.0,
            float(frame.loc[frame["submission_rank_pre_review"].le(15).fillna(False), "performance_rank"].max())
            if frame["submission_rank_pre_review"].le(15).any() else 0.0,
        )
        omitted = frame[
            frame["is_qualified"] & (~frame["is_eligible_acquisition"]) & (frame["performance_rank"] <= max_perf)
        ].drop_duplicates("player_id")
        for _, r in omitted.iterrows():
            passed_over_rows.append({
                "snapshot_id": snapshot_id,
                "role_pool": role_pool,
                "performance_rank": int(r["performance_rank"]),
                "player_id": int(r["player_id"]),
                "player_name": str(r["player_name"]),
                "slot_nationality": str(r.get("slot_nationality", "OS")),
                "inferred_role": str(r["inferred_role"]),
                "conservative_score_q25": float(r["conservative_score_q25"]),
                "predicted_hp_impact_12b": float(r["predicted_hp_impact"]),
                "ipl_hp_balls": int(r["ipl_hp_balls"]) if pd.notna(r.get("ipl_hp_balls")) else 0,
                "current_franchise_2027": str(r["current_franchise_2027"]),
                "route_tier": str(r.get("route_tier", "")),
                "auction_status_2027": str(r["auction_status_2027"]),
                "decision_category": str(r["decision_category"]),
                "passed_over_reason": str(r["passed_over_reason"]),
            })

    shortlist_df = pd.DataFrame(shortlist_rows)

    reserve_lookup: Dict[int, str] = {}
    second_opt_lookup: Dict[int, str] = {}
    for role_pool in ("Batting", "Bowling"):
        sub = shortlist_df[shortlist_df["role_pool"] == role_pool]
        reserves = sub[sub["submission_rank"] > 10]
        # Free-agent / non-rival-release eligible backups from full screened frame
        src_frame = bat_refit if role_pool == "Batting" else bowl_refit
        fa_pool = src_frame[
            src_frame["is_qualified"]
            & src_frame["is_eligible_acquisition"]
            & (src_frame["auction_status_2027"] == "AUCTION_REGISTRATION_UNVERIFIED")
        ].sort_values("performance_rank")

        for _, r in sub.iterrows():
            pid = int(r["player_id"])
            r_role = str(r["inferred_role"]).upper()
            r_nat = str(r.get("slot_nationality", "OS"))
            r_fr = str(r.get("current_franchise_2027", ""))
            r_route = str(r.get("route_tier", "CONDITIONAL"))
            r_status = str(r.get("auction_status_2027", ""))
            is_incumbent = r["decision_category"] == "INCUMBENT_RETENTION"
            if int(r["submission_rank"]) > 10:
                reserve_lookup[pid] = "SELF_RESERVE"
                if is_incumbent:
                    second_opt_lookup[pid] = "RR squad depth if retained for IPL 2027."
                elif r_route == "CONDITIONAL":
                    if role_pool == "Bowling":
                        second_opt_lookup[pid] = "No-rival-release fallback: retain RR internal Sandeep Sharma / Tushar Deshpande (IND) or scout unattached Saqib Mahmood (OS; registration closes Nov 23 for Dec 16 auction)."
                    else:
                        second_opt_lookup[pid] = "No-rival-release fallback: retain RR internal Dhruv Jurel / Shubham Dubey / Donovan Ferreira (or bid unattached Jonny Bairstow if registered by Nov 23 cutoff)."
                else:
                    second_opt_lookup[pid] = "No rival release needed; subject to Nov 23 player registration cutoff ahead of Dec 16 Goa mini-auction."
                continue

            if role_pool == "Bowling":
                fam_tok = "SPIN" if "SPIN" in r_role else "PACE"
                same_phase = reserves[reserves["inferred_role"].astype(str).str.contains(fam_tok, na=False)]
            elif r_role == "WK_BATTER":
                # Keeper roles MUST verify keeping skill (never suggest non-keeper Markram as WK cover)
                same_phase = reserves[reserves["is_wk"].astype(bool)] if "is_wk" in reserves.columns else reserves[reserves["inferred_role"].astype(str).eq("WK_BATTER")]
            elif r_role == "FINISHER_BATTER":
                same_phase = reserves[reserves["inferred_role"].astype(str).str.contains("FINISHER|PACE_ALLROUNDER|MIDDLE_ORDER", na=False)]
            elif r_role == "SPIN_ALLROUNDER":
                same_phase = reserves[reserves["inferred_role"].astype(str).str.contains("SPIN_ALLROUNDER|PACE_ALLROUNDER|MIDDLE_ORDER", na=False)]
            else:
                same_phase = reserves[reserves["inferred_role"].astype(str).str.contains(r_role.split("_")[0], na=False)]

            if r_role == "WK_BATTER" and same_phase.empty:
                reserve_lookup[pid] = (
                    "No verified wicketkeeper in reserves #11-15 (ranked reserves offer batting/all-rounder cover only; "
                    "RR relies on incumbent keeper Dhruv Jurel or unranked keeper targets e.g. Kumar Kushagra / Robin Minz)"
                )
                chosen_res = None
            else:
                phase_pool = same_phase if not same_phase.empty else reserves
                slot_matched = phase_pool[phase_pool["slot_nationality"] == r_nat]
                if r_nat == "IND" and not slot_matched.empty:
                    cand_res_pool = slot_matched
                elif not slot_matched.empty:
                    cand_res_pool = slot_matched
                else:
                    ind_conv = phase_pool[phase_pool["slot_nationality"] == "IND"]
                    cand_res_pool = ind_conv if not ind_conv.empty else phase_pool

                ipl_res = cand_res_pool[cand_res_pool["ipl_hp_balls"].fillna(0) >= 24]
                chosen_res = ipl_res.iloc[0] if not ipl_res.empty else (cand_res_pool.iloc[0] if not cand_res_pool.empty else None)
                if chosen_res is not None:
                    res_b = int(chosen_res["ipl_hp_balls"]) if pd.notna(chosen_res["ipl_hp_balls"]) else 0
                    res_rate = f"{float(chosen_res['ipl_hp_rate_12b']):+.2f}/12b" if res_b > 0 and pd.notna(chosen_res["ipl_hp_rate_12b"]) else "0 IPL HP balls"
                    res_nat = str(chosen_res.get("slot_nationality", "OS"))
                    res_fr = str(chosen_res["current_franchise_2027"])
                    res_st = str(chosen_res.get("auction_status_2027", ""))
                    if chosen_res["decision_category"] == "INCUMBENT_RETENTION":
                        res_cond = " [RR squad option if retained for IPL 2027]"
                    elif "RELEASED" in res_st:
                        res_cond = " [Already released pre-2026; requires BCB NOC / BCCI clearance & Nov 23 registration cutoff for Dec 16 auction]"
                    elif "REPLACEMENT_CONVERSION" in res_st:
                        res_cond = f" [2026 replacement contract: reverts to auction pool (Nov 23 reg cutoff) unless {res_fr} converts/retains by Nov 17]"
                    elif chosen_res.get("route_tier") == "CONDITIONAL":
                        res_cond = f" [Requires release by {res_fr} and auction registration]"
                    else:
                        res_cond = " [Unattached; subject to Nov 23 player registration cutoff for Dec 16 auction]"
                    slot_note = f"; consumes 1 OS slot vs {r_nat} pick" if (r_nat == "IND" and res_nat == "OS") else ""
                    reserve_lookup[pid] = (
                        f"#{int(chosen_res['submission_rank'])} {chosen_res['player_name']} ({res_nat}, {chosen_res['inferred_role']}, "
                        f"{res_fr}, IPL {res_b}b at {res_rate}{slot_note}){res_cond}"
                    )
                else:
                    reserve_lookup[pid] = "No eligible reserve in band"

            if is_incumbent:
                second_opt_lookup[pid] = "Back within RR if retained for IPL 2027. Use the role-matched reserve if the role opens."
                continue

            # Second option NOT dependent on any rival franchise release
            if r_role == "WK_BATTER":
                fa_wk = fa_pool[fa_pool["is_wk"].astype(bool)] if "is_wk" in fa_pool.columns else fa_pool[fa_pool["inferred_role"].astype(str).eq("WK_BATTER")]
                fa_pick = fa_wk.iloc[0] if not fa_wk.empty else None
            else:
                fa_sub = fa_pool[fa_pool["inferred_role"].astype(str).str.contains("SPIN" if "SPIN" in r_role else ("PACE" if "PACE" in r_role else "BATTER|ALLROUNDER"), na=False)]
                fa_pick = fa_sub.iloc[0] if not fa_sub.empty else (fa_pool.iloc[0] if not fa_pool.empty else None)
            fa_txt = f"unattached {fa_pick['player_name']} (registration closes Nov 23 ahead of Dec 16 Goa auction)" if fa_pick is not None else "uncapped domestic auction scout (Nov 23 reg cutoff)"
            if role_pool == "Bowling":
                rr_hold = "Ravi Bishnoi / Ravindra Jadeja (IND)" if "SPIN" in r_role else ("Sandeep Sharma / Tushar Deshpande (IND)" if r_nat == "IND" else "Jofra Archer / Nandre Burger (OS) or Sandeep Sharma (IND)")
            else:
                rr_hold = "Dhruv Jurel (IND, WK_BATTER)" if r_role == "WK_BATTER" else ("Ravindra Jadeja / Shubham Dubey (IND)" if r_nat == "IND" else "Donovan Ferreira / Shimron Hetmyer (OS)")

            if "REPLACEMENT_CONVERSION" in r_status:
                second_opt_lookup[pid] = f"Remainder-of-2026 replacement with {r_fr} (reverts to Dec 16 pool subject to Nov 23 reg cutoff unless converted/retained by Nov 17); non-rival-release 2nd option: hold RR internal {rr_hold} or target {fa_txt}."
            elif r_route == "CONDITIONAL":
                second_opt_lookup[pid] = f"Primary relies on release by {r_fr} and auction registration. Otherwise, keep {rr_hold} within RR or target {fa_txt}."
            else:
                second_opt_lookup[pid] = f"No rival release needed (unattached; registration closes Nov 23 for Dec 16 auction); backup hold: RR internal {rr_hold} or {fa_txt}."

    shortlist_df["role_matched_reserve"] = shortlist_df["player_id"].map(reserve_lookup).fillna("")
    shortlist_df["non_rival_release_second_option"] = shortlist_df["player_id"].map(second_opt_lookup).fillna("")
    shortlist_path = out / "rr_shortlist.csv"
    shortlist_df.to_csv(shortlist_path, index=False)

    def _build_scenario_shortlist_df(bat_frm: pd.DataFrame, bowl_frm: pd.DataFrame) -> pd.DataFrame:
        scen_rows: List[Dict[str, Any]] = []
        for r_pool, frm in (("Batting", bat_frm), ("Bowling", bowl_frm)):
            elig = frm[frm["is_qualified"] & frm["is_eligible_acquisition"]].sort_values("submission_rank").drop_duplicates("player_id")
            for _, r in elig.head(15).reset_index(drop=True).iterrows():
                scen_rows.append(_build_shortlist_row(r, r_pool))
        scen_df = pd.DataFrame(scen_rows)
        for r_pool in ("Batting", "Bowling"):
            sub_s = scen_df[scen_df["role_pool"] == r_pool]
            scen_res = sub_s[sub_s["submission_rank"] > 10]
            for _, r in sub_s.iterrows():
                pid = int(r["player_id"])
                r_role = str(r["inferred_role"]).upper()
                if int(r["submission_rank"]) > 10:
                    scen_df.loc[(scen_df["player_id"] == pid) & (scen_df["role_pool"] == r_pool), "role_matched_reserve"] = "SELF_RESERVE"
                else:
                    if r_pool == "Bowling":
                        fam = "SPIN" if "SPIN" in r_role else "PACE"
                        match_res = scen_res[scen_res["inferred_role"].astype(str).str.contains(fam, na=False)]
                    elif r_role == "WK_BATTER":
                        match_res = scen_res[scen_res["is_wk"].astype(bool)] if "is_wk" in scen_res.columns else scen_res[scen_res["inferred_role"].astype(str).eq("WK_BATTER")]
                    elif r_role == "FINISHER_BATTER":
                        match_res = scen_res[scen_res["inferred_role"].astype(str).str.contains("FINISHER|PACE_ALLROUNDER|MIDDLE_ORDER", na=False)]
                    else:
                        match_res = scen_res[scen_res["inferred_role"].astype(str).str.contains("SPIN_ALLROUNDER|PACE_ALLROUNDER|MIDDLE_ORDER", na=False)]
                    if not match_res.empty:
                        best_res = match_res.iloc[0]
                        scen_df.loc[(scen_df["player_id"] == pid) & (scen_df["role_pool"] == r_pool), "role_matched_reserve"] = f"#{int(best_res['submission_rank'])} {best_res['player_name']} ({best_res['inferred_role']})"
                    elif r_role == "WK_BATTER":
                        scen_df.loc[(scen_df["player_id"] == pid) & (scen_df["role_pool"] == r_pool), "role_matched_reserve"] = "NO_VERIFIED_WK_RESERVE (HOLD JUREL / SCOUT KUSHAGRA)"
                    else:
                        scen_df.loc[(scen_df["player_id"] == pid) & (scen_df["role_pool"] == r_pool), "role_matched_reserve"] = "GENERAL_RESERVE"
        return scen_df

    # Keep the legacy filename for existing readers. The primary shortlist now includes eligible RR incumbents.
    shortlist_retain_path = out / "rr_shortlist_retain_inclusive.csv"
    shortlist_df.to_csv(shortlist_retain_path, index=False)

    bat_ind = _run_prod_policy(bat_refit_raw, "Batting", chosen_bat, indian_majority=True)
    bowl_ind = _run_prod_policy(bowl_refit_raw, "Bowling", chosen_bowl, indian_majority=True)
    shortlist_ind_df = _build_scenario_shortlist_df(bat_ind, bowl_ind)
    shortlist_ind_path = out / "rr_shortlist_indian_majority.csv"
    shortlist_ind_df.to_csv(shortlist_ind_path, index=False)

    passed_over_df = pd.DataFrame(passed_over_rows)
    passed_over_path = out / "passed_over_candidates.csv"
    passed_over_df.to_csv(passed_over_path, index=False)

    changelog_df = pd.DataFrame(changelog_rows)
    changelog_path = out / "shortlist_review_changelog.csv"
    changelog_df.to_csv(changelog_path, index=False)

    # 5. Build official RR Auction Decision Notes (rr_auction_notes.csv)
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
    auction_notes_path = out / "rr_auction_notes.csv"
    auction_notes_df.to_csv(auction_notes_path, index=False)

    # 6. Build pack-verified dated IPL availability registry, live-metric RR depth chart, and recruitment sheet
    build_ipl_availability_registry(out, raw_dir=config.raw_dir)
    build_rr_depth_chart(out).to_csv(out / "rr_lineup_scenarios.csv", index=False)

    recruitment_cols = [
        "role_pool", "submission_rank", "submission_rank_pre_review", "performance_rank", "cipl_performance_rank",
        "review_action", "slot_nationality", "route_tier", "is_official_top10", "player_id", "player_name", "inferred_role",
        "role_evidence_summary", "decision_category", "tactical_squad_role", "ipl_2026_pack_franchises",
        "current_franchise_2027", "auction_status_2027", "fitness_clearance_status", "actionable_acquisition_route",
        "conservative_score_q25", "predicted_hp_impact_12b", "cipl_q25", "cipl_mean_12b",
        "modeled_pressure_lift_12b", "b1_historical_pressure_lift_12b", "pressure_lift_estimator",
        "hp_balls", "hp_matches", "ipl_hp_balls", "ipl_hp_rate_12b", "non_ipl_hp_balls",
        "recent_2025_2026_hp_balls", "recent_2025_2026_hp_rate_12b",
        "rr_incumbent_comparison", "role_matched_reserve", "non_rival_release_second_option", "alternative_option",
        "rival_incentives", "scenario_core_retained", "scenario_vacancy_opens", "price_scenario",
    ]
    recruitment_df = shortlist_df[[c for c in recruitment_cols if c in shortlist_df.columns]].copy()
    recruitment_path = out / "rr_recruitment_sheet.csv"
    recruitment_df.to_csv(recruitment_path, index=False)

    salt_bat_df = bat_refit[bat_refit["player_id"] == 5553]
    salt_d_df = score_with_selected_model(
        bat_match_df[bat_match_df["fold"].isin(all_folds)].pipe(
            lambda m: fit_player_forecast(m, p_dim, "batting", seed=config.seed, folds=all_folds)[0]
        ),
        bat_match_df[bat_match_df["fold"].isin(all_folds)],
        p_dim,
        "batting",
        "Challenger D (Workload-Aware Distributional)",
        seed=config.seed,
    )
    salt_d_row = salt_d_df[salt_d_df["player_id"] == 5553]
    salt_diag: Dict[str, Any] = {}
    if not salt_bat_df.empty:
        sr = salt_bat_df.iloc[0]
        salt_m = bat_match_df[(bat_match_df["player_id"] == 5553) & (bat_match_df["comp_tier"] == "IPL")]
        salt_ord_b = int(salt_m["ord_balls_faced"].sum())
        salt_hp_b = int(salt_m["hp_balls_faced"].sum())
        salt_ord_r = round(float(12.0 * salt_m["ord_bat_impact"].sum() / salt_ord_b), 2) if salt_ord_b > 0 else None
        salt_hp_r = round(float(12.0 * salt_m["hp_bat_impact"].sum() / salt_hp_b), 2) if salt_hp_b > 0 else None
        salt_diag = {
            "player_id": 5553,
            "player_name": "Phil Salt",
            "ipl_ord_balls": salt_ord_b,
            "ipl_ord_rate_12b": salt_ord_r,
            "ipl_hp_balls": salt_hp_b,
            "ipl_hp_rate_12b": salt_hp_r,
            "selected_model": chosen_bat,
            "selected_model_perf_rank": int(sr["performance_rank"]) if pd.notna(sr.get("performance_rank")) else None,
            "selected_model_q25": round(float(sr["conservative_score_q25"]), 3),
            "challenger_d_perf_rank": int(salt_d_row.iloc[0]["performance_rank"]) if not salt_d_row.empty and pd.notna(salt_d_row.iloc[0].get("performance_rank")) else None,
            "challenger_d_q25": round(float(salt_d_row.iloc[0]["conservative_score_q25"]), 3) if not salt_d_row.empty else None,
        }

    data_conflicts = [
        {
            "role_pool": str(r["role_pool"]),
            "submission_rank": int(r["submission_rank"]),
            "player_name": str(r["player_name"]),
            "ipl_hp_balls": int(r["ipl_hp_balls"]),
            "ipl_hp_rate_12b": float(r["ipl_hp_rate_12b"]) if pd.notna(r["ipl_hp_rate_12b"]) else None,
            "modeled_pressure_lift_12b": round(float(r["modeled_pressure_lift_12b"]), 3),
            "route_tier": str(r["route_tier"]),
            "auction_status_2027": str(r["auction_status_2027"]),
        }
        for _, r in shortlist_df.iterrows()
        if (
            (pd.notna(r["ipl_hp_rate_12b"]) and float(r["ipl_hp_rate_12b"]) < 0)
            or str(r["route_tier"]) == "UNVERIFIED"
            or int(r["player_id"]) == 4373
        )
    ]

    audit_summary = {
        "stage": "11_rankings_and_eligibility",
        "snapshot_id": snapshot_id,
        "refit_cutoff": "FULL_HISTORY_THROUGH_2026",
        "model_used": chosen_overall,
        "chosen_model_batting": chosen_bat,
        "chosen_model_bowling": chosen_bowl,
        "selection_rationale": comp_data.get("pre_holdout_decision", {}).get("selection_rationale", ""),
        "shortlist_policy_used": "RR_IPL_POSITIVE_VERIFIED",
        "canonical_market_policy": {
            "allow_rr_incumbents": True,
            "exclude_internal_untouchables": True,
            "exclude_on_recent_trade_alone": False,
        },
        "policy_selection_summary": {
            "statistical_model_audit_under_RPP_IPL_VERIFIED": {
                "chosen_batting": chosen_bat,
                "chosen_bowling": chosen_bowl,
                "stage3_blend_promoted": comp_data.get("stage3_bowling_blend_evaluation", {}).get("promoted", False),
            },
            "replayed_shortlist_policy": {
                "policy_name": "RR_IPL_POSITIVE_VERIFIED",
                "rules": ">=48b/6m career HP, role supported, >=24b/2m direct IPL HP, direct IPL HP > 0/12b, dated market eligibility",
                "replay_summary": comp_data.get("stage3_bowling_blend_evaluation", {}).get("feasibility_screen_replay_summary", {}),
                "incumbent_inclusive_replay": "model_comparison.json / shortlist_policy_controls / RETAIN_INCLUSIVE_POSITIVE_VERIFIED",
                "historical_market_scope": "Prior-season franchise mappings approximate the candidate pool for replay. Current benchmark decisions and trade records apply to the current shortlist.",
            },
        },
        "evidence_floor": {
            "min_pressure_balls": 48,
            "min_pressure_matches": 6,
            "min_ipl_hp_balls": 24,
            "min_ipl_hp_matches": 2,
            "min_ipl_hp_rate_exclusive": 0.0,
        },
        "cutoff_diagnostics": cutoff_diagnostics,
        "salt_vs_challenger_d_check": salt_diag,
        "data_conflicts_and_caveats": data_conflicts,
        "batting_summary": {
            "total_evaluated": int(len(bat_refit)),
            "qualified_candidates": int(bat_refit["is_qualified"].sum()),
            "eligible_acquisition_candidates": int(bat_refit["is_eligible_acquisition"].sum()),
            "passed_over_above_top15": int(len(passed_over_df[passed_over_df["role_pool"] == "Batting"])) if not passed_over_df.empty else 0,
            "top10_names": shortlist_df[(shortlist_df["role_pool"] == "Batting") & (shortlist_df["is_official_top10"])]["player_name"].tolist(),
            "reserves_names": shortlist_df[(shortlist_df["role_pool"] == "Batting") & (shortlist_df["is_reserve"])]["player_name"].tolist(),
            "shortfall": 0,
        },
        "bowling_summary": {
            "total_evaluated": int(len(bowl_refit)),
            "qualified_candidates": int(bowl_refit["is_qualified"].sum()),
            "eligible_acquisition_candidates": int(bowl_refit["is_eligible_acquisition"].sum()),
            "passed_over_above_top15": int(len(passed_over_df[passed_over_df["role_pool"] == "Bowling"])) if not passed_over_df.empty else 0,
            "top10_names": shortlist_df[(shortlist_df["role_pool"] == "Bowling") & (shortlist_df["is_official_top10"])]["player_name"].tolist(),
            "reserves_names": shortlist_df[(shortlist_df["role_pool"] == "Bowling") & (shortlist_df["is_reserve"])]["player_name"].tolist(),
            "shortfall": 0,
        },
        "scenarios_summary": {
            "retain_inclusive_top10_batting": shortlist_df[(shortlist_df["role_pool"] == "Batting") & (shortlist_df["is_official_top10"])]["player_name"].tolist(),
            "retain_inclusive_top10_bowling": shortlist_df[(shortlist_df["role_pool"] == "Bowling") & (shortlist_df["is_official_top10"])]["player_name"].tolist(),
            "indian_majority_top10_batting": shortlist_ind_df[(shortlist_ind_df["role_pool"] == "Batting") & (shortlist_ind_df["is_official_top10"])]["player_name"].tolist(),
            "indian_majority_top10_bowling": shortlist_ind_df[(shortlist_ind_df["role_pool"] == "Bowling") & (shortlist_ind_df["is_official_top10"])]["player_name"].tolist(),
        },
        "verification_status": "PROVISIONAL",
        "verification_notes": (
            f"Ranks canonical role-qualified players under {chosen_overall} using ONE shared policy "
            f"RR_IPL_POSITIVE_VERIFIED (>=48b/6m career HP, >=24b/2m direct IPL HP, and IPL HP > 0/12b), "
            f"replacing RPP_IPL_VERIFIED while preserving statistical selection audit (RPP_IPL_VERIFIED selected {chosen_overall}; "
            f"pre-2025 B0-RPP blend challenger not promoted). "
            f"RR incumbents can qualify. Internal untouchables are screened out. Trade history updates the club and leaves a conditional release route. "
            f"Missing market records are strictly held as UNVERIFIED_MISSING_MARKET_RECORD (never release-watch). "
            f"Stage 3 Challenger DHP was evaluated on >=6b, all >0b, and 1..5b short-stint batting slices and not promoted; "
            f"cutoff gaps (#10 vs #11: bat {cutoff_diagnostics.get('batting', {}).get('q25_gap_10_vs_11', 'N/A')}, "
            f"bowl {cutoff_diagnostics.get('bowling', {}).get('q25_gap_10_vs_11', 'N/A')}) and {len(data_conflicts)} "
            f"direct-IPL or registration caveats are logged dynamically in data_conflicts_and_caveats, "
            f"rr_shortlist.csv, rr_auction_notes.csv, and shortlist_review_changelog.csv. Unstop dropdown eligibility remains PROVISIONAL."
        ),
    }

    audit_path = out / "rankings_audit.json"
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(audit_summary, f, indent=2)

    output_files = {
        "player_rankings.csv": rankings_path,
        "rr_shortlist.csv": shortlist_path,
        "rr_shortlist_retain_inclusive.csv": shortlist_retain_path,
        "rr_shortlist_indian_majority.csv": shortlist_ind_path,
        "passed_over_candidates.csv": passed_over_path,
        "shortlist_review_changelog.csv": changelog_path,
        "rr_auction_notes.csv": auction_notes_path,
        "rr_recruitment_sheet.csv": recruitment_path,
        "rr_lineup_scenarios.csv": out / "rr_lineup_scenarios.csv",
        "ipl_availability_registry.csv": out / "ipl_availability_registry.csv",
        "rankings_audit.json": audit_path,
    }
    output_fingerprints = {fname: compute_sha256(fpath) for fname, fpath in output_files.items()}
    return audit_summary, output_fingerprints
