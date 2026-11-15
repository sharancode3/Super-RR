"""Stage 04/05 Shared Shortlist Policy & Chronological Replay Engine.

Provides ONE canonical selection function `select_shortlist_by_policy` shared identically
between historical replay (2024, 2025, 2026 cutoffs) and 2027 production shortlist
construction, plus exact reproduction of the locked legacy post-hoc policy as a control.
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from rr_pressure.availability import build_ipl_availability_registry
from rr_pressure.challengers import (
    ChallengerC_IPLAnchoredRolePhase,
    ChallengerD_WorkloadDistributional,
    score_with_selected_model,
)
from rr_pressure.forecast import fit_player_forecast
from rr_pressure.role_challenger import ChallengerRPP_RolePhaseJoint, infer_role_family


RR_TEAM_ID = 3
PRIOR_IPL_COMP_BY_EVAL_YEAR = {
    2024: 1715,  # IPL 2023
    2025: 2193,  # IPL 2024
    2026: 2725,  # IPL 2025
    2027: 3298,  # IPL 2026
}


def build_asof_market_snapshot(
    cutoff_year: int,
    mapping_df: pd.DataFrame,
    p_dim: pd.DataFrame,
    raw_dir: Optional[Any] = None,
) -> pd.DataFrame:
    """Build strictly pre-cutoff market/roster eligibility snapshot for historical replay or 2027 production."""
    if cutoff_year >= 2027 and raw_dir is not None:
        from rr_pressure.availability import (
            derive_decision_category,
            derive_route_tier,
        )
        reg = build_ipl_availability_registry(output_dir=None, raw_dir=raw_dir).copy()
        reg_pids = set(reg["player_id"].astype(int).tolist())
        m26 = mapping_df[mapping_df["comp_id"] == 3298] if mapping_df is not None else pd.DataFrame()
        m26_team = m26.groupby("player_id")["team_name"].first().to_dict() if not m26.empty else {}
        extra_rows = []
        for pid in p_dim["player_id"].astype(int).unique():
            if pid in reg_pids:
                continue
            tm = m26_team.get(pid)
            if tm == "Rajasthan Royals":
                extra_rows.append({
                    "player_id": pid, "current_franchise": tm,
                    "availability_status": "INCUMBENT_RR", "decision_category": "INCUMBENT_RETENTION",
                })
            else:
                # Missing TransactionRecord NEVER defaults silently to PENDING_NOV17_RETENTIONS / CONDITIONAL_RELEASE_WATCH
                extra_rows.append({
                    "player_id": pid, "current_franchise": tm or "UNVERIFIED_CLUB",
                    "availability_status": "UNVERIFIED_MISSING_MARKET_RECORD", "decision_category": "UNVERIFIED_HOLD",
                })
        if extra_rows:
            reg = pd.concat([reg, pd.DataFrame(extra_rows)], ignore_index=True)
        reg["is_rr_incumbent"] = reg["current_franchise"].astype(str) == "Rajasthan Royals"
        reg["decision_category"] = [
            derive_decision_category(str(st), str(dc))
            for st, dc in zip(reg["availability_status"], reg["decision_category"])
        ]
        reg["route_tier"] = reg["availability_status"].map(derive_route_tier)
        reg["is_unavailable_hard"] = reg["availability_status"].isin([
            "INCUMBENT_RR",
            "RETIRED_FROM_IPL",
            "INELIGIBLE_PAKISTAN_IPL_POLICY",
            "BENCHMARK_UNTOUCHABLE",
            "CONTRACTED_RIVAL_CORE",
            "UNVERIFIED_MISSING_MARKET_RECORD",
        ]) | reg["decision_category"].isin([
            "INCUMBENT_RETENTION",
            "RETIRED_FROM_IPL_UNAVAILABLE",
            "POLICY_INELIGIBLE_BCCI_IPL_RULE",
            "BENCHMARK_ONLY",
            "UNVERIFIED_HOLD",
        ])

        def _mkt_reason(st: str, dcat: str, unavail: bool) -> str:
            if not unavail:
                return ""
            if dcat == "UNVERIFIED_HOLD":
                return "UNVERIFIED_MISSING_MARKET_RECORD_HOLD"
            st_u = str(st).upper()
            if "PAKISTAN" in st_u or "INELIGIBLE" in st_u:
                return "POLICY_INELIGIBLE_BCCI_IPL_RULE"
            if "RETIRED" in st_u:
                return "RETIRED_FROM_IPL_UNAVAILABLE"
            if dcat == "INCUMBENT_RETENTION":
                return "RR_INCUMBENT_RETENTION_DECISION"
            return "RIVAL_CORNERSTONE_OR_BENCHMARK_ONLY"

        reg["market_exclusion_reason"] = [
            _mkt_reason(str(st), str(dc), bool(un))
            for st, dc, un in zip(reg["availability_status"], reg["decision_category"], reg["is_unavailable_hard"])
        ]
        return reg[["player_id", "current_franchise", "availability_status", "decision_category", "route_tier", "is_rr_incumbent", "is_unavailable_hard", "market_exclusion_reason"]].drop_duplicates("player_id")

    # Historical replay (<2024, <2025, <2026): use ONLY prior IPL competition mappings (<= cutoff_year - 1)
    prior_comp_id = PRIOR_IPL_COMP_BY_EVAL_YEAR.get(cutoff_year)
    prior_ipl_comps = [cid for yr, cid in PRIOR_IPL_COMP_BY_EVAL_YEAR.items() if yr <= cutoff_year]
    m_prior = mapping_df[mapping_df["comp_id"] == prior_comp_id] if prior_comp_id else pd.DataFrame()
    m_hist_ipl = mapping_df[mapping_df["comp_id"].isin(prior_ipl_comps)]

    prior_team_map = m_prior.groupby("player_id")["team_name"].first().to_dict() if not m_prior.empty else {}
    prior_rr_ids = set(m_prior[m_prior["team_id"] == RR_TEAM_ID]["player_id"].unique()) if not m_prior.empty else set()
    any_hist_ipl_ids = set(m_hist_ipl["player_id"].unique()) if not m_hist_ipl.empty else set()

    # For historical replay, mark prior-season RR roster for the policy's incumbent option
    # and distinguish players with prior IPL mapping from unmapped non-IPL players; rival retention/release lists
    # are unknown in historical pack (documented scope limitation).
    rows = []
    for pid in p_dim["player_id"].astype(int).unique():
        is_rr = pid in prior_rr_ids
        team = prior_team_map.get(pid, "Prior IPL Unmapped" if pid not in any_hist_ipl_ids else "Prior IPL Other Season")
        rows.append({
            "player_id": pid,
            "current_franchise": team,
            "availability_status": "INCUMBENT_RR_PRIOR_SEASON" if is_rr else ("PRIOR_IPL_MAPPED" if pid in any_hist_ipl_ids else "NO_PRIOR_IPL_MAPPING"),
            "decision_category": "INCUMBENT_RETENTION" if is_rr else "HISTORICAL_CONDITIONAL_POOL",
            "route_tier": "CONFIRMED" if is_rr else ("CONDITIONAL" if pid in any_hist_ipl_ids else "UNVERIFIED"),
            "is_rr_incumbent": is_rr,
            "is_unavailable_hard": is_rr,
            "market_exclusion_reason": "RR_INCUMBENT_RETENTION_DECISION" if is_rr else "",
        })
    return pd.DataFrame(rows)


def select_shortlist_by_policy(
    scored_df: pd.DataFrame,
    market_df: pd.DataFrame,
    policy_name: str = "RPP_IPL_VERIFIED",
    min_ipl_hp_balls: int = 24,
    min_ipl_hp_matches: int = 2,
    cipl_ranks: Optional[Dict[int, float]] = None,
    b0_ranks: Optional[Dict[int, float]] = None,
    discipline: str = "batting",
    allow_rr_incumbents: bool = False,
    require_indian_majority: bool = False,
    min_indians: int = 6,
    target_top_n: int = 10,
    eb_shrink_pseudo_balls: float = 24.0,
) -> pd.DataFrame:
    """Apply ONE shared shortlist selection policy cleanly separating performance filters from market feasibility.

    Shared by BOTH historical replay (compare.py) and 2027 production (rankings.py).

    Supported policies:
      - 'RAW_MODEL': qualified + non-hard-unavailable ordered strictly by conservative_score_q25.
      - 'RPP_IPL_VERIFIED': qualified + direct IPL proof (ipl_hp_balls >= min_ipl_hp_balls,
        ipl_hp_matches >= min_ipl_hp_matches) + market eligibility ordered deterministically by
        (conservative_score_q25, predicted_hp_impact, ipl_hp_balls, player_id).
      - 'LEGACY_POST_HOC': explicit control reproducing locked Batch 11 rule.
    """
    if scored_df.empty:
        return scored_df.copy()

    work = scored_df.copy()
    if "ipl_hp_balls" not in work.columns:
        work["ipl_hp_balls"] = 0
    if "ipl_hp_matches" not in work.columns:
        work["ipl_hp_matches"] = 0
    work = work.sort_values(
        ["conservative_score_q25", "predicted_hp_impact", "ipl_hp_balls", "player_id"],
        ascending=[False, False, False, True],
    ).drop_duplicates(subset=["player_id"], keep="first").reset_index(drop=True)

    mkt_cols = ["player_id", "current_franchise", "availability_status", "decision_category", "is_rr_incumbent", "is_unavailable_hard"]
    for opt_col in ("route_tier", "market_exclusion_reason"):
        if opt_col in market_df.columns:
            mkt_cols.append(opt_col)
    mkt_dedup = market_df[mkt_cols].drop_duplicates(subset=["player_id"], keep="first")

    df = work.merge(mkt_dedup, on="player_id", how="left", suffixes=("", "_mkt"))
    for c in ("current_franchise", "availability_status", "decision_category", "is_rr_incumbent", "is_unavailable_hard", "route_tier", "market_exclusion_reason"):
        mc = f"{c}_mkt"
        if mc in df.columns:
            df[c] = df[mc]
            df = df.drop(columns=[mc])

    missing_mkt = df["availability_status"].isna()
    df["current_franchise"] = df["current_franchise"].fillna("UNVERIFIED_CLUB")
    df["availability_status"] = df["availability_status"].fillna("UNVERIFIED_MISSING_MARKET_RECORD")
    df["decision_category"] = df["decision_category"].fillna("UNVERIFIED_HOLD")
    df["is_rr_incumbent"] = df["is_rr_incumbent"].map(lambda v: bool(v) if pd.notna(v) else False)
    df["is_unavailable_hard"] = np.where(
        missing_mkt,
        True,
        df["is_unavailable_hard"].map(lambda v: bool(v) if pd.notna(v) else False),
    )
    if "route_tier" not in df.columns:
        df["route_tier"] = np.where(df["is_rr_incumbent"], "CONFIRMED", np.where(missing_mkt, "UNVERIFIED", "CONDITIONAL"))
    else:
        df["route_tier"] = df["route_tier"].fillna("UNVERIFIED")
    if "market_exclusion_reason" not in df.columns:
        df["market_exclusion_reason"] = ""
    df["market_exclusion_reason"] = df["market_exclusion_reason"].fillna("")
    df.loc[missing_mkt, "market_exclusion_reason"] = "UNVERIFIED_MISSING_MARKET_RECORD_HOLD"
    df.loc[df["is_unavailable_hard"] & (df["market_exclusion_reason"] == ""), "market_exclusion_reason"] = (
        df.loc[df["is_unavailable_hard"] & (df["market_exclusion_reason"] == ""), "decision_category"].astype(str)
    )
    if allow_rr_incumbents:
        rr_keep = (
            df["is_rr_incumbent"]
            & df["decision_category"].eq("INCUMBENT_RETENTION")
            & df["availability_status"].isin(["INCUMBENT_RR", "INCUMBENT_RR_PRIOR_SEASON"])
        )
        df.loc[rr_keep, "is_unavailable_hard"] = False
        df.loc[rr_keep, "market_exclusion_reason"] = ""

    df["is_qualified"] = df["is_qualified"].map(lambda v: bool(v) if pd.notna(v) else False)
    if "non_ipl_hp_balls" not in df.columns:
        df["non_ipl_hp_balls"] = (df.get("hp_balls", 0) - df["ipl_hp_balls"]).clip(lower=0)

    df["perf_filter_reason"] = "PASS"
    df["market_filter_reason"] = "ELIGIBLE"
    df.loc[~df["is_qualified"], "perf_filter_reason"] = "FAIL_ROLE_OR_TOTAL_SAMPLE"
    df.loc[df["is_unavailable_hard"], "market_filter_reason"] = df["market_exclusion_reason"]

    elig = df["is_qualified"] & (~df["is_unavailable_hard"])

    # Deterministic pre-review submission rank (before optional IPL/legacy scouting floor)
    pre_cand = df[elig].sort_values(
        ["conservative_score_q25", "predicted_hp_impact", "ipl_hp_balls", "player_id"],
        ascending=[False, False, False, True],
    )
    df["submission_rank_pre_review"] = np.nan
    for pre_rk, idx in enumerate(pre_cand.index, start=1):
        df.at[idx, "submission_rank_pre_review"] = pre_rk

    if policy_name == "RAW_MODEL":
        df["policy_eligible"] = elig
        cand = pre_cand
    elif policy_name == "RPP_IPL_VERIFIED":
        ipl_ok = (df["ipl_hp_balls"] >= min_ipl_hp_balls) & (df["ipl_hp_matches"] >= min_ipl_hp_matches)
        df.loc[elig & (~ipl_ok), "perf_filter_reason"] = f"THIN_DIRECT_IPL (<{min_ipl_hp_balls}b_or_<{min_ipl_hp_matches}m)"
        df["policy_eligible"] = elig & ipl_ok
        cand = df[df["policy_eligible"]].sort_values(
            ["conservative_score_q25", "predicted_hp_impact", "ipl_hp_balls", "player_id"],
            ascending=[False, False, False, True],
        )
    elif policy_name == "RR_IPL_POSITIVE_VERIFIED":
        rate_col = "hp_rate_ipl_12b" if "hp_rate_ipl_12b" in df.columns else ("ipl_hp_rate_calc" if "ipl_hp_rate_calc" in df.columns else None)
        ipl_rate = pd.to_numeric(df[rate_col], errors="coerce") if rate_col else pd.Series(np.nan, index=df.index)
        ipl_sample_ok = (df["ipl_hp_balls"] >= min_ipl_hp_balls) & (df["ipl_hp_matches"] >= min_ipl_hp_matches)
        ipl_pos_ok = ipl_rate.notna() & (ipl_rate > 0.0)
        df.loc[elig & (~ipl_sample_ok), "perf_filter_reason"] = f"THIN_DIRECT_IPL (<{min_ipl_hp_balls}b_or_<{min_ipl_hp_matches}m)"
        df.loc[elig & ipl_sample_ok & (~ipl_pos_ok), "perf_filter_reason"] = "NONPOSITIVE_DIRECT_IPL_HP (<=0_12b)"
        df["policy_eligible"] = elig & ipl_sample_ok & ipl_pos_ok
        cand = df[df["policy_eligible"]].sort_values(
            ["conservative_score_q25", "predicted_hp_impact", "ipl_hp_balls", "player_id"],
            ascending=[False, False, False, True],
        )
    elif policy_name == "RR_SHRUNK_POSITIVE_VERIFIED":
        rate_col = "hp_rate_ipl_12b" if "hp_rate_ipl_12b" in df.columns else ("ipl_hp_rate_calc" if "ipl_hp_rate_calc" in df.columns else None)
        ipl_rate = pd.to_numeric(df[rate_col], errors="coerce") if rate_col else pd.Series(np.nan, index=df.index)
        ipl_b = pd.to_numeric(df["ipl_hp_balls"], errors="coerce").fillna(0.0)
        pos_mask = ipl_b > 0
        if "inferred_role" in df.columns and pos_mask.any():
            tmp = df.loc[pos_mask, ["inferred_role"]].copy()
            tmp["_b"] = ipl_b.loc[pos_mask]
            tmp["_imp"] = tmp["_b"] * ipl_rate.loc[pos_mask].fillna(0.0)
            g_role = tmp.groupby("inferred_role").agg(b=("_b", "sum"), imp=("_imp", "sum"))
            g_mean = float(tmp["_imp"].sum() / max(1.0, tmp["_b"].sum()))
            role_prior_map = {r: float(row["imp"] / max(1.0, row["b"])) for r, row in g_role.iterrows()}
            prior_s = df["inferred_role"].map(role_prior_map).fillna(g_mean)
        else:
            g_mean = float((ipl_b.loc[pos_mask] * ipl_rate.loc[pos_mask].fillna(0.0)).sum() / max(1.0, ipl_b.loc[pos_mask].sum())) if pos_mask.any() else 0.0
            prior_s = pd.Series(g_mean, index=df.index)
        shrunk_rate = (ipl_b * ipl_rate.fillna(0.0) + eb_shrink_pseudo_balls * prior_s) / (ipl_b + eb_shrink_pseudo_balls)
        df["shrunk_ipl_hp_rate_12b"] = shrunk_rate
        ipl_sample_ok = (df["ipl_hp_balls"] >= min_ipl_hp_balls) & (df["ipl_hp_matches"] >= min_ipl_hp_matches)
        ipl_pos_ok = ipl_rate.notna() & (shrunk_rate > 0.0)
        df.loc[elig & (~ipl_sample_ok), "perf_filter_reason"] = f"THIN_DIRECT_IPL (<{min_ipl_hp_balls}b_or_<{min_ipl_hp_matches}m)"
        df.loc[elig & ipl_sample_ok & (~ipl_pos_ok), "perf_filter_reason"] = "NONPOSITIVE_SHRUNK_DIRECT_IPL_HP (<=0_12b)"
        df["policy_eligible"] = elig & ipl_sample_ok & ipl_pos_ok
        cand = df[df["policy_eligible"]].sort_values(
            ["conservative_score_q25", "predicted_hp_impact", "ipl_hp_balls", "player_id"],
            ascending=[False, False, False, True],
        )
    elif policy_name == "LEGACY_POST_HOC":
        if discipline == "batting":
            drop_mask = elig & (df["ipl_hp_balls"] == 0) & (df["availability_status"].isin(["AUCTION_REGISTRATION_UNVERIFIED", "NO_PRIOR_IPL_MAPPING"]))
            df.loc[drop_mask, "perf_filter_reason"] = "LEGACY_DROP_ZERO_IPL_UNVERIFIED"
            df["policy_eligible"] = elig & (~drop_mask)
            cand = df[df["policy_eligible"]].sort_values(
                ["conservative_score_q25", "predicted_hp_impact", "hp_matches", "player_id"],
                ascending=[False, False, False, True],
            )
        else:
            # Bowling legacy 3-tier rule
            c_map = cipl_ranks or {}
            b_map = b0_ranks or {}
            tiers: List[Tuple[int, float, int]] = []
            for idx, r in df.loc[elig].iterrows():
                pid = int(r["player_id"])
                ipl_b = float(r.get("ipl_hp_balls", 0) or 0)
                ipl_r = r.get("hp_rate_ipl_12b", np.nan)
                non_b = float(r.get("non_ipl_hp_balls", 0) or 0)
                st = str(r.get("availability_status", ""))
                dcat = str(r.get("decision_category", ""))
                b0_r = float(b_map.get(pid, 999.0))
                cipl_r = float(c_map.get(pid, 999.0))
                if ipl_b >= 24 and pd.notna(ipl_r) and float(ipl_r) < -2.0:
                    df.at[idx, "perf_filter_reason"] = "LEGACY_DROP_NEG_IPL"
                    continue
                if ipl_b == 0 and st in ("AUCTION_REGISTRATION_UNVERIFIED", "NO_PRIOR_IPL_MAPPING") and non_b < 160:
                    df.at[idx, "perf_filter_reason"] = "LEGACY_DROP_ZERO_IPL"
                    continue
                if cipl_r <= 10.0 and dcat != "CONDITIONAL_TRADE_OR_RELEASE_WATCH":
                    tiers.append((1, cipl_r, idx))
                elif b0_r <= 15.0 and (ipl_b > 0 or st not in ("AUCTION_REGISTRATION_UNVERIFIED", "NO_PRIOR_IPL_MAPPING") or non_b >= 220):
                    tiers.append((2, b0_r, idx))
                else:
                    tiers.append((3, cipl_r, idx))
            df["policy_eligible"] = False
            ordered_indices = [t[2] for t in sorted(tiers, key=lambda x: (x[0], x[1]))]
            df.loc[ordered_indices, "policy_eligible"] = True
            cand = df.loc[ordered_indices]
    else:
        raise ValueError(f"Unknown shortlist policy: {policy_name}")

    if require_indian_majority and "slot_nationality" in df.columns:
        max_os = target_top_n - min_indians
        top_indices: List[Any] = []
        os_count = 0
        bypassed_indices: List[Any] = []
        for idx, r in cand.iterrows():
            is_os = str(r.get("slot_nationality", "OS")).upper() == "OS"
            if len(top_indices) < target_top_n:
                if is_os:
                    if os_count < max_os:
                        top_indices.append(idx)
                        os_count += 1
                    else:
                        bypassed_indices.append(idx)
                else:
                    top_indices.append(idx)
            else:
                break
        remaining_indices = [idx for idx in cand.index if idx not in top_indices]
        ordered_indices = top_indices + remaining_indices
        cand = df.loc[ordered_indices]
        for b_idx in bypassed_indices:
            df.at[b_idx, "perf_filter_reason"] = "BYPASSED_FOR_INDIAN_MAJORITY_SQUAD_BALANCE"

    df["submission_rank"] = np.nan
    for rk, idx in enumerate(cand.index, start=1):
        df.at[idx, "submission_rank"] = rk
    df["is_eligible_acquisition"] = df["policy_eligible"].astype(bool)
    df["passed_over_reason"] = ""
    df.loc[~df["is_qualified"], "passed_over_reason"] = "FAIL_ROLE_OR_TOTAL_SAMPLE"
    df.loc[df["is_qualified"] & df["is_unavailable_hard"], "passed_over_reason"] = df.loc[
        df["is_qualified"] & df["is_unavailable_hard"], "market_exclusion_reason"
    ]
    if policy_name == "RPP_IPL_VERIFIED":
        df.loc[elig & (~df["policy_eligible"]), "passed_over_reason"] = "REVIEWED_OUT_THIN_DIRECT_IPL"
    elif policy_name in ("RR_IPL_POSITIVE_VERIFIED", "RR_SHRUNK_POSITIVE_VERIFIED"):
        thin_mask = elig & (~df["policy_eligible"]) & df["perf_filter_reason"].astype(str).str.startswith("THIN_DIRECT_IPL")
        nonpos_mask = elig & (~df["policy_eligible"]) & (~thin_mask)
        df.loc[thin_mask, "passed_over_reason"] = "REVIEWED_OUT_THIN_DIRECT_IPL"
        df.loc[nonpos_mask, "passed_over_reason"] = (
            "REVIEWED_OUT_NONPOSITIVE_DIRECT_IPL" if policy_name == "RR_IPL_POSITIVE_VERIFIED"
            else "REVIEWED_OUT_NONPOSITIVE_SHRUNK_DIRECT_IPL"
        )
    else:
        df.loc[elig & (~df["policy_eligible"]), "passed_over_reason"] = df.loc[
            elig & (~df["policy_eligible"]), "perf_filter_reason"
        ]
    sort_cols = ["submission_rank"]
    sort_asc = [True]
    if "performance_rank" in df.columns:
        sort_cols.append("performance_rank")
        sort_asc.append(True)
    sort_cols.extend(["conservative_score_q25", "player_id"])
    sort_asc.extend([False, True])
    return df.sort_values(sort_cols, ascending=sort_asc, na_position="last").reset_index(drop=True)


def evaluate_top10_slate_on_window(
    top10_ids: List[int],
    eval_obs: pd.DataFrame,
    min_balls_assessable: int = 12,
    seed: int = 2027,
) -> Dict[str, Any]:
    """Evaluate realized IPL HP and ordinary performance for replayed Top-10 picks + match-block CI."""
    if eval_obs.empty:
        return {"assessable_count": 0, "player_weighted_hp_12b": None}
    hp_ev = eval_obs[(eval_obs["comp_tier"] == "IPL") & (eval_obs["is_high_pressure"] == True) & (eval_obs["player_id"].isin(top10_ids))]
    ord_ev = eval_obs[(eval_obs["comp_tier"] == "IPL") & (eval_obs["is_high_pressure"] == False) & (eval_obs["player_id"].isin(top10_ids))]

    grp = hp_ev.groupby("player_id").agg(b=("legal_balls", "sum"), imp=("total_impact", "sum"), matches=("match_id", "nunique"))
    ord_grp = ord_ev.groupby("player_id").agg(b=("legal_balls", "sum"), imp=("total_impact", "sum"))

    rates = []
    ord_rates = []
    outcomes = []
    for pid in top10_ids:
        b = int(grp.loc[pid, "b"]) if pid in grp.index else 0
        imp = float(grp.loc[pid, "imp"]) if pid in grp.index else 0.0
        m = int(grp.loc[pid, "matches"]) if pid in grp.index else 0
        ob = int(ord_grp.loc[pid, "b"]) if pid in ord_grp.index else 0
        oimp = float(ord_grp.loc[pid, "imp"]) if pid in ord_grp.index else 0.0
        is_ass = b >= min_balls_assessable
        rate = float(12.0 * imp / b) if is_ass else None
        orate = float(12.0 * oimp / ob) if ob >= 12 else None
        if rate is not None:
            rates.append(rate)
        if orate is not None:
            ord_rates.append(orate)
        outcomes.append({
            "player_id": int(pid),
            "eval_ipl_hp_balls": b,
            "eval_ipl_hp_matches": m,
            "eval_ipl_hp_12b": round(rate, 2) if rate is not None else None,
            "eval_ipl_ord_12b": round(orate, 2) if orate is not None else None,
            "is_assessable": bool(is_ass),
            "missing_reason": None if is_ass else ("ZERO_EVAL_IPL_HP" if b == 0 else f"THIN_EVAL_IPL_HP_{b}b"),
        })

    # Match-block bootstrap (200 resamples over evaluation IPL matches)
    rng = np.random.default_rng(seed)
    eval_mids = eval_obs[eval_obs["comp_tier"] == "IPL"]["match_id"].unique()
    m_player = hp_ev.groupby(["match_id", "player_id"]).agg(b=("legal_balls", "sum"), imp=("total_impact", "sum")).reset_index()
    boot_vals = []
    if len(eval_mids) > 5 and not m_player.empty:
        # Pre-index by match_id for fast bootstrap
        by_m = {int(mid): g for mid, g in m_player.groupby("match_id")}
        for _ in range(200):
            draw = rng.choice(eval_mids, size=len(eval_mids), replace=True)
            parts = [by_m[int(m)] for m in draw if int(m) in by_m]
            if not parts:
                continue
            df_b = pd.concat(parts, ignore_index=True).groupby("player_id").agg(b=("b", "sum"), imp=("imp", "sum"))
            df_bq = df_b[df_b["b"] >= min_balls_assessable]
            if len(df_bq) > 0:
                boot_vals.append(float((12.0 * df_bq["imp"] / df_bq["b"]).mean()))

    return {
        "assessable_count": int(len(rates)),
        "total_picks": int(len(top10_ids)),
        "player_weighted_hp_12b": round(float(np.mean(rates)), 3) if rates else None,
        "player_weighted_ord_12b": round(float(np.mean(ord_rates)), 3) if ord_rates else None,
        "boot_ci90_pw_hp_12b": [round(float(np.quantile(boot_vals, 0.05)), 3), round(float(np.quantile(boot_vals, 0.95)), 3)] if len(boot_vals) >= 20 else [None, None],
        "outcomes": outcomes,
    }
