"""Stage 10: Robustness Checks and Shortlist Sensitivity Analysis."""

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
from rr_pressure.manifest import compute_sha256

Z_25 = 0.67449


def compute_jaccard_similarity(list1: List[Any], list2: List[Any]) -> float:
    s1, s2 = set(list1), set(list2)
    denom = len(s1 | s2)
    return float(len(s1 & s2) / denom) if denom > 0 else 0.0


def score_and_rank_candidates(
    fit_df: pd.DataFrame,
    match_df: pd.DataFrame,
    p_dim: pd.DataFrame,
    role_type: str,
    chosen_model: str,
    seed: int = 2027,
    deliv_hp_df: pd.DataFrame = None,
    obs_df: pd.DataFrame = None,
    cal_override: Any = None,
) -> pd.DataFrame:
    return score_with_selected_model(
        fit_df=fit_df,
        match_df=match_df,
        p_dim=p_dim,
        discipline=role_type,
        chosen_model=chosen_model,
        deliv_hp_df=deliv_hp_df,
        seed=seed,
        obs_df=obs_df,
        cal_override=cal_override,
    )


def run_standout_match_check(
    match_df: pd.DataFrame,
    p_dim: pd.DataFrame,
    role_type: str,
    top15_ids: List[int],
    seed: int = 2027,
    chosen_model: str = "Ablation B-0",
    all_folds: List[str] = None,
    deliv_hp_df: pd.DataFrame = None,
    obs_df: pd.DataFrame = None,
) -> List[Dict[str, Any]]:
    """Evaluate if player's rank collapses when their single best match is removed."""
    balls_col = "hp_balls_faced" if role_type == "batting" else "hp_balls_bowled"
    impact_col = "hp_bat_impact" if role_type == "batting" else "hp_bowl_impact"
    
    # Baseline fit using full history folds matching production ranking
    target_folds = all_folds if all_folds is not None else ["TRAIN_2022_2024", "VAL_2025", "TEST_HOLDOUT_2026"]
    hist = match_df[match_df["fold"].isin(target_folds)].copy()
    base_fit, _ = fit_player_forecast(hist, p_dim, role_type, seed=seed, folds=target_folds, baseline_only=True)
    base_ranked = score_and_rank_candidates(base_fit, hist, p_dim, role_type, chosen_model, seed=seed, deliv_hp_df=deliv_hp_df, obs_df=obs_df)
    base_ranks = base_ranked[base_ranked["is_qualified"]].set_index("player_id")["performance_rank"].to_dict()
    base_scores = base_ranked.set_index("player_id")["conservative_score_q25"].to_dict()
    
    cal_ref = None
    if obs_df is not None and ("Challenger RPP" in chosen_model or "Role-Phase Regularized" in chosen_model):
        from rr_pressure.role_challenger import ChallengerRPP_RolePhaseJoint
        full_mod = ChallengerRPP_RolePhaseJoint().fit(obs_df, p_dim, role_type)
        cal_ref = (full_mod.sig_cal_ge6_, full_mod.role_sig_)

    p_names = p_dim.set_index("player_id")["player_name"].to_dict()
    standout_results = []
    
    for pid in top15_ids:
        # Find player's matches
        p_matches = hist[hist["player_id"] == pid]
        if len(p_matches) == 0:
            continue
        # Single best match
        best_mid = p_matches.sort_values(impact_col, ascending=False).iloc[0]["match_id"]
        # Remove the complete match from the refit, including other players.
        lomo_hist = hist[hist["match_id"] != best_mid]
        lomo_fit, _ = fit_player_forecast(lomo_hist, p_dim, role_type, seed=seed, folds=target_folds, baseline_only=True)
        lomo_obs = obs_df[obs_df["match_id"] != best_mid] if obs_df is not None else None
        lomo_ranked = score_and_rank_candidates(lomo_fit, lomo_hist, p_dim, role_type, chosen_model, seed=seed, deliv_hp_df=deliv_hp_df, obs_df=lomo_obs, cal_override=cal_ref)
        lomo_ranks = lomo_ranked[lomo_ranked["is_qualified"]].set_index("player_id")["performance_rank"].to_dict()
        lomo_scores = lomo_ranked.set_index("player_id")["conservative_score_q25"].to_dict()
        
        orig_rank = base_ranks.get(pid, np.nan)
        new_rank = lomo_ranks.get(pid, np.nan)
        orig_score = base_scores.get(pid, np.nan)
        new_score = lomo_scores.get(pid, np.nan)
        rank_delta = int(new_rank - orig_rank) if not np.isnan(new_rank) and not np.isnan(orig_rank) else None
        
        standout_results.append({
            "player_id": int(pid),
            "player_name": p_names.get(pid, f"Player_{pid}"),
            "baseline_rank": int(orig_rank) if not np.isnan(orig_rank) else None,
            "removed_match_id": int(best_mid),
            "lomo_rank": int(new_rank) if not np.isnan(new_rank) else None,
            "rank_drop": rank_delta,
            "baseline_score": float(orig_score),
            "lomo_score": float(new_score),
            "is_sensitive_to_single_match": rank_delta is not None and rank_delta > 5,
        })
        
    return standout_results


def run_bootstrap_stability(
    match_df: pd.DataFrame,
    p_dim: pd.DataFrame,
    role_type: str,
    top15_ids: List[int],
    n_replicates: int = 100,
    seed: int = 2027,
    chosen_model: str = "Ablation B-0",
    all_folds: List[str] = None,
    deliv_hp_df: pd.DataFrame = None,
    obs_df: pd.DataFrame = None,
    market_df: pd.DataFrame = None,
    shortlist_policy: str = "RR_IPL_POSITIVE_VERIFIED",
    allow_rr_incumbents: bool = False,
) -> Dict[int, Dict[str, Any]]:
    """Match-level cluster bootstrap to assess rank intervals and top-10 inclusion refitting selected model."""
    target_folds = all_folds if all_folds is not None else ["TRAIN_2022_2024", "VAL_2025", "TEST_HOLDOUT_2026"]
    hist = match_df[match_df["fold"].isin(target_folds)].copy()
    unique_mids = hist["match_id"].unique()
    rng = np.random.default_rng(seed)
    
    boot_ranks = {pid: [] for pid in top15_ids}
    in_top10_count = {pid: 0 for pid in top15_ids}
    boot_slist_ranks = {pid: [] for pid in top15_ids}
    in_slist_top10_count = {pid: 0 for pid in top15_ids}

    cal_ref = None
    if obs_df is not None and ("Challenger RPP" in chosen_model or "Role-Phase Regularized" in chosen_model):
        from rr_pressure.role_challenger import ChallengerRPP_RolePhaseJoint
        full_mod = ChallengerRPP_RolePhaseJoint().fit(obs_df, p_dim, role_type)
        cal_ref = (full_mod.sig_cal_ge6_, full_mod.role_sig_)

    from rr_pressure.rankings import apply_production_shortlist_policy
    balls_col = "hp_balls_faced" if role_type == "batting" else "hp_balls_bowled"
    imp_col = "hp_bat_impact" if role_type == "batting" else "hp_bowl_impact"

    for _ in range(n_replicates):
        sample_mids = rng.choice(unique_mids, size=len(unique_mids), replace=True)
        mid_counts = pd.Series(sample_mids).value_counts()
        sample = hist.loc[hist.index.repeat(hist["match_id"].map(mid_counts).fillna(0).astype(int))]
        fit, _ = fit_player_forecast(sample, p_dim, role_type, seed=seed, folds=target_folds, baseline_only=True)
        ranked = score_and_rank_candidates(fit, sample, p_dim, role_type, chosen_model, seed=seed, deliv_hp_df=deliv_hp_df, obs_df=obs_df, cal_override=cal_ref)
        qual = ranked[ranked["is_qualified"]]
        rank_map = qual.set_index("player_id")["performance_rank"].astype(int).to_dict()
        
        for pid in top15_ids:
            r = rank_map.get(pid, len(qual) + 1)
            boot_ranks[pid].append(r)
            if r <= 10:
                in_top10_count[pid] += 1
                
        if market_df is not None:
            ipl_mask = sample["comp_tier"].eq("IPL")
            ipl_b = sample[ipl_mask].groupby("player_id")[balls_col].sum()
            ipl_m = sample[ipl_mask & sample[balls_col].gt(0)].groupby("player_id")["match_id"].nunique()
            ipl_imp = sample[ipl_mask].groupby("player_id")[imp_col].sum()
            ipl_r = 12 * ipl_imp / ipl_b.replace(0, np.nan)
            
            work_df = ranked.copy()
            work_df["ipl_hp_balls"] = work_df["player_id"].map(ipl_b).fillna(0).astype(int)
            work_df["ipl_hp_matches"] = work_df["player_id"].map(ipl_m).fillna(0).astype(int)
            work_df["hp_rate_ipl_12b"] = work_df["player_id"].map(ipl_r)
            
            slist = apply_production_shortlist_policy(
                work_df,
                market_df,
                discipline=role_type.lower(),
                policy_name=shortlist_policy,
                min_ipl_hp_balls=24,
                min_ipl_hp_matches=2,
                chosen_model_name=chosen_model,
                allow_rr_incumbents=allow_rr_incumbents,
            )
            s_map = slist[slist["submission_rank"].notna()].set_index("player_id")["submission_rank"].astype(int).to_dict()
            for pid in top15_ids:
                sr = s_map.get(pid, 999)
                boot_slist_ranks[pid].append(sr)
                if sr <= 10:
                    in_slist_top10_count[pid] += 1

    stability_summary = {}
    p_names = p_dim.set_index("player_id")["player_name"].to_dict()
    for pid in top15_ids:
        ranks = np.array(boot_ranks[pid])
        s_ranks_all = np.array(boot_slist_ranks[pid]) if market_df is not None else ranks
        valid_s_ranks = s_ranks_all[s_ranks_all < 999]
        valid_ci_90 = [int(np.percentile(valid_s_ranks, 5)), int(np.percentile(valid_s_ranks, 95))] if len(valid_s_ranks) > 0 else []
        valid_median = float(np.median(valid_s_ranks)) if len(valid_s_ranks) > 0 else None
        stability_summary[pid] = {
            "player_id": int(pid),
            "player_name": p_names.get(pid, f"Player_{pid}"),
            "top10_draws": int(in_slist_top10_count[pid]) if market_df is not None else int(in_top10_count[pid]),
            "eligible_draws": int(len(valid_s_ranks)) if market_df is not None else int(n_replicates),
            "total_draws": int(n_replicates),
            "central_rank_range": valid_ci_90 if len(valid_s_ranks) > 0 else [],
            "top10_inclusion_freq": float(in_top10_count[pid] / n_replicates),
            "median_rank": float(np.median(ranks)),
            "rank_ci_90": [int(np.percentile(ranks, 5)), int(np.percentile(ranks, 95))],
            "std_rank": float(np.std(ranks)),
            "shortlist_top10_inclusion_freq": float(in_slist_top10_count[pid] / n_replicates) if market_df is not None else float(in_top10_count[pid] / n_replicates),
            "shortlist_eligible_draws": int(len(valid_s_ranks)) if market_df is not None else n_replicates,
            "shortlist_median_rank": valid_median,
            "shortlist_rank_ci_90": valid_ci_90,
        }
    return stability_summary


def run_stage10_robustness(config: PipelineConfig) -> Tuple[Dict[str, Any], Dict[str, str]]:
    out = config.out_dir
    out.mkdir(parents=True, exist_ok=True)
    
    deliv_df = pd.read_csv(out / "delivery_impact_ledger.csv", low_memory=False)
    p_dim = ensure_explicit_role_flags(pd.read_csv(out / "player_dimension.csv"))
    bat_match_df = pd.read_csv(out / "match_player_batting_impact.csv")
    bowl_match_df = pd.read_csv(out / "match_player_bowling_impact.csv")
    
    comp_path = out / "model_comparison.json"
    if comp_path.exists():
        with open(comp_path, "r", encoding="utf-8") as f:
            comp_data = json.load(f)
            decision = comp_data.get("pre_holdout_decision", {})
            chosen_overall = decision.get("chosen_model", "Selected Production Model")
            chosen_bat = decision.get("chosen_model_batting", chosen_overall)
            chosen_bowl = decision.get("chosen_model_bowling", chosen_overall)
    else:
        chosen_overall = "Candidate B (Statistical Default)"
        chosen_bat = chosen_overall
        chosen_bowl = chosen_overall

    all_folds = ["TRAIN_2022_2024", "VAL_2025", "TEST_HOLDOUT_2026"]
    rel_mask = deliv_df["is_reliability_eligible"].astype(bool) if "is_reliability_eligible" in deliv_df.columns else pd.Series(True, index=deliv_df.index)
    deliv_hp_20 = deliv_df[deliv_df["is_high_pressure_20"] & rel_mask].copy()
    deliv_elig = deliv_df[rel_mask].copy()
    bat_obs_20 = build_phase_observations_from_ledger(deliv_elig, "batting")
    bowl_obs_20 = build_phase_observations_from_ledger(deliv_elig, "bowling")

    # 1. Baseline top 15 under the same forecast used in every stress refit.
    from rr_pressure.shortlist_policy import build_asof_market_snapshot
    from rr_pressure.rankings import apply_production_shortlist_policy
    mapping_path = config.raw_dir / "competition_team_player_mapping.csv"
    mapping_df = pd.read_csv(mapping_path) if mapping_path.exists() else pd.DataFrame()
    market_snapshot_2027 = build_asof_market_snapshot(2027, mapping_df, p_dim, raw_dir=config.raw_dir)

    def fit_and_rank(history, role, model, hp_df=None, obs_df=None):
        history = history[history["fold"].isin(all_folds)]
        profiles, _ = fit_player_forecast(history, p_dim, role, seed=config.seed, folds=all_folds, baseline_only=True)
        return score_and_rank_candidates(profiles, history, p_dim, role, model, seed=config.seed, deliv_hp_df=hp_df, obs_df=obs_df)

    def get_shortlist_top10(scored_df: pd.DataFrame, discipline: str, match_history: pd.DataFrame, chosen_name: str) -> List[int]:
        work = scored_df.copy()
        ipl_mask = match_history["comp_tier"].eq("IPL")
        balls_col = "hp_balls_faced" if discipline == "batting" else "hp_balls_bowled"
        impact_col = "hp_bat_impact" if discipline == "batting" else "hp_bowl_impact"
        ipl_b = match_history[ipl_mask].groupby("player_id")[balls_col].sum()
        ipl_m = match_history[ipl_mask & match_history[balls_col].gt(0)].groupby("player_id")["match_id"].nunique()
        ipl_imp = match_history[ipl_mask].groupby("player_id")[impact_col].sum()
        ipl_r = 12 * ipl_imp / ipl_b.replace(0, np.nan)
        
        work["ipl_hp_balls"] = work["player_id"].map(ipl_b).fillna(0).astype(int)
        work["ipl_hp_matches"] = work["player_id"].map(ipl_m).fillna(0).astype(int)
        work["hp_rate_ipl_12b"] = work["player_id"].map(ipl_r)
        
        slist = apply_production_shortlist_policy(
            work,
            market_snapshot_2027,
            discipline=discipline.lower(),
            policy_name="RR_IPL_POSITIVE_VERIFIED",
            min_ipl_hp_balls=24,
            min_ipl_hp_matches=2,
            chosen_model_name=chosen_name,
            allow_rr_incumbents=True,
        )
        t10 = slist[slist["submission_rank"].between(1, 10)].sort_values("submission_rank")["player_id"].tolist()
        return t10

    bat_base = fit_and_rank(bat_match_df, "batting", chosen_bat, hp_df=deliv_hp_20, obs_df=bat_obs_20)
    bowl_base = fit_and_rank(bowl_match_df, "bowling", chosen_bowl, hp_df=deliv_hp_20, obs_df=bowl_obs_20)
    top15_bat_ids = bat_base.loc[bat_base["is_qualified"], "player_id"].head(15).tolist()
    top15_bowl_ids = bowl_base.loc[bowl_base["is_qualified"], "player_id"].head(15).tolist()
    top10_bat_base, top10_bowl_base = top15_bat_ids[:10], top15_bowl_ids[:10]
    shortlist_top10_bat_base = get_shortlist_top10(bat_base, "batting", bat_match_df, chosen_bat)
    shortlist_top10_bowl_base = get_shortlist_top10(bowl_base, "bowling", bowl_match_df, chosen_bowl)

    # 2. Pressure Percentile Sensitivity (15% vs 20% vs 25%)
    def alternate_top_ten(history, role, model, hp_df=None, obs_df=None):
        ranked = fit_and_rank(history, role, model, hp_df=hp_df, obs_df=obs_df)
        return ranked.loc[ranked["is_qualified"], "player_id"].head(10).tolist()

    def with_pressure_threshold(history, deliveries, player_col, impact_col, role):
        balls = "faced" if role == "batting" else "bowled"
        action = "bat" if role == "batting" else "bowl"
        hp_balls, hp_impact = f"hp_balls_{balls}", f"hp_{action}_impact"
        ord_balls, ord_impact = f"ord_balls_{balls}", f"ord_{action}_impact"
        keys = ["match_id", "player_id", "fold"]
        pressure = deliveries.groupby(["match_id", player_col, "fold"]).agg(
            **{hp_balls: ("is_legal_ball", "sum"), hp_impact: (impact_col, "sum")}
        ).reset_index().rename(columns={player_col: "player_id"})
        updated = history.drop(columns=[hp_balls, hp_impact]).merge(pressure, on=keys, how="left", validate="one_to_one")
        updated[[hp_balls, hp_impact]] = updated[[hp_balls, hp_impact]].fillna(0)
        updated[ord_balls] = updated[f"total_balls_{balls}"] - updated[hp_balls]
        updated[ord_impact] = updated[f"total_{role}_impact"] - updated[hp_impact]
        updated[f"hp_{action}_impact_12b"] = 12 * updated[hp_impact] / updated[hp_balls].replace(0, np.nan)
        updated[f"ord_{action}_impact_12b"] = 12 * updated[ord_impact] / updated[ord_balls].replace(0, np.nan)
        return updated

    pressure_sensitivity = {}
    for p_cut, col_name in [(15, "is_high_pressure_15"), (25, "is_high_pressure_25")]:
        hp_d = deliv_df[deliv_df[col_name] & rel_mask].copy()
        deliv_p = deliv_elig.copy()
        deliv_p["is_high_pressure_20"] = deliv_p[col_name]
        bat_cut = with_pressure_threshold(bat_match_df, hp_d, "striker_id", "batting_impact", "batting")
        bowl_cut = with_pressure_threshold(bowl_match_df, hp_d, "bowler_id", "bowling_impact", "bowling")
        bat_cut_obs = build_phase_observations_from_ledger(deliv_p, "batting") if "Challenger RPP" in chosen_bat else None
        bowl_cut_obs = build_phase_observations_from_ledger(deliv_p, "bowling") if "Challenger RPP" in chosen_bowl else None
        bat_cut_scored = fit_and_rank(bat_cut, "batting", chosen_bat, hp_df=hp_d, obs_df=bat_cut_obs)
        bowl_cut_scored = fit_and_rank(bowl_cut, "bowling", chosen_bowl, hp_df=hp_d, obs_df=bowl_cut_obs)
        top10_cut_bat = bat_cut_scored.loc[bat_cut_scored["is_qualified"], "player_id"].head(10).tolist()
        top10_cut_bowl = bowl_cut_scored.loc[bowl_cut_scored["is_qualified"], "player_id"].head(10).tolist()
        slist_cut_bat = get_shortlist_top10(bat_cut_scored, "batting", bat_cut, chosen_bat)
        slist_cut_bowl = get_shortlist_top10(bowl_cut_scored, "bowling", bowl_cut, chosen_bowl)
        
        pressure_sensitivity[f"cutoff_{p_cut}_percent"] = {
            "batting_top10_jaccard_similarity": compute_jaccard_similarity(top10_bat_base, top10_cut_bat),
            "bowling_top10_jaccard_similarity": compute_jaccard_similarity(top10_bowl_base, top10_cut_bowl),
            "top10_batting_retained": len(set(top10_bat_base) & set(top10_cut_bat)),
            "top10_bowling_retained": len(set(top10_bowl_base) & set(top10_cut_bowl)),
            "shortlist_batting_top10_jaccard": compute_jaccard_similarity(shortlist_top10_bat_base, slist_cut_bat),
            "shortlist_bowling_top10_jaccard": compute_jaccard_similarity(shortlist_top10_bowl_base, slist_cut_bowl),
            "shortlist_top10_batting_retained": len(set(shortlist_top10_bat_base) & set(slist_cut_bat)),
            "shortlist_top10_bowling_retained": len(set(shortlist_top10_bowl_base) & set(slist_cut_bowl)),
        }
        
    # 3. Competition Tier Sensitivity (Pooled vs Non-Emerging vs IPL-only)
    tier_sensitivity = {}
    
    # Non-Emerging (IPL + T20I only)
    non_emerging_bat = bat_match_df[bat_match_df["comp_tier"].isin(["IPL", "T20I"])]
    scored_non_em_bat = fit_and_rank(non_emerging_bat, "batting", chosen_bat, hp_df=deliv_hp_20[deliv_hp_20["comp_tier"].isin(["IPL", "T20I"])], obs_df=bat_obs_20[bat_obs_20["comp_tier"].isin(["IPL", "T20I"])])
    top10_non_em_bat = scored_non_em_bat.loc[scored_non_em_bat["is_qualified"], "player_id"].head(10).tolist()
    slist_non_em_bat = get_shortlist_top10(scored_non_em_bat, "batting", non_emerging_bat, chosen_bat)
    
    non_emerging_bowl = bowl_match_df[bowl_match_df["comp_tier"].isin(["IPL", "T20I"])]
    scored_non_em_bowl = fit_and_rank(non_emerging_bowl, "bowling", chosen_bowl, hp_df=deliv_hp_20[deliv_hp_20["comp_tier"].isin(["IPL", "T20I"])], obs_df=bowl_obs_20[bowl_obs_20["comp_tier"].isin(["IPL", "T20I"])])
    top10_non_em_bowl = scored_non_em_bowl.loc[scored_non_em_bowl["is_qualified"], "player_id"].head(10).tolist()
    slist_non_em_bowl = get_shortlist_top10(scored_non_em_bowl, "bowling", non_emerging_bowl, chosen_bowl)
    
    # IPL only
    ipl_only_bat = bat_match_df[bat_match_df["comp_tier"] == "IPL"]
    scored_ipl_bat = fit_and_rank(ipl_only_bat, "batting", chosen_bat, hp_df=deliv_hp_20[deliv_hp_20["comp_tier"] == "IPL"], obs_df=bat_obs_20[bat_obs_20["comp_tier"] == "IPL"])
    top10_ipl_bat = scored_ipl_bat.loc[scored_ipl_bat["is_qualified"], "player_id"].head(10).tolist()
    slist_ipl_bat = get_shortlist_top10(scored_ipl_bat, "batting", ipl_only_bat, chosen_bat)
    
    ipl_only_bowl = bowl_match_df[bowl_match_df["comp_tier"] == "IPL"]
    scored_ipl_bowl = fit_and_rank(ipl_only_bowl, "bowling", chosen_bowl, hp_df=deliv_hp_20[deliv_hp_20["comp_tier"] == "IPL"], obs_df=bowl_obs_20[bowl_obs_20["comp_tier"] == "IPL"])
    top10_ipl_bowl = scored_ipl_bowl.loc[scored_ipl_bowl["is_qualified"], "player_id"].head(10).tolist()
    slist_ipl_bowl = get_shortlist_top10(scored_ipl_bowl, "bowling", ipl_only_bowl, chosen_bowl)
    
    tier_sensitivity["non_emerging_top10_overlap"] = {
        "batting_jaccard": compute_jaccard_similarity(top10_bat_base, top10_non_em_bat),
        "bowling_jaccard": compute_jaccard_similarity(top10_bowl_base, top10_non_em_bowl),
        "batting_retained": len(set(top10_bat_base) & set(top10_non_em_bat)),
        "bowling_retained": len(set(top10_bowl_base) & set(top10_non_em_bowl)),
        "shortlist_batting_jaccard": compute_jaccard_similarity(shortlist_top10_bat_base, slist_non_em_bat),
        "shortlist_bowling_jaccard": compute_jaccard_similarity(shortlist_top10_bowl_base, slist_non_em_bowl),
        "shortlist_batting_retained": len(set(shortlist_top10_bat_base) & set(slist_non_em_bat)),
        "shortlist_bowling_retained": len(set(shortlist_top10_bowl_base) & set(slist_non_em_bowl)),
    }
    tier_sensitivity["ipl_only_top10_overlap"] = {
        "batting_jaccard": compute_jaccard_similarity(top10_bat_base, top10_ipl_bat),
        "bowling_jaccard": compute_jaccard_similarity(top10_bowl_base, top10_ipl_bowl),
        "batting_retained": len(set(top10_bat_base) & set(top10_ipl_bat)),
        "bowling_retained": len(set(top10_bowl_base) & set(top10_ipl_bowl)),
        "shortlist_batting_jaccard": compute_jaccard_similarity(shortlist_top10_bat_base, slist_ipl_bat),
        "shortlist_bowling_jaccard": compute_jaccard_similarity(shortlist_top10_bowl_base, slist_ipl_bowl),
        "shortlist_batting_retained": len(set(shortlist_top10_bat_base) & set(slist_ipl_bat)),
        "shortlist_bowling_retained": len(set(shortlist_top10_bowl_base) & set(slist_ipl_bowl)),
    }
    
    # 4. Workload Evidence Floor Sensitivity
    # Compare Standard (48b, 6m) vs Narrow (36b, 4m) vs Strict (72b, 8m)
    workload_sensitivity = {
        "standard_floor_48b_6m": {
            "qualified_batters": int(bat_base["is_qualified"].sum()),
            "qualified_bowlers": int(bowl_base["is_qualified"].sum()),
        },
        "narrow_floor_36b_4m": {
            "qualified_batters": int(((bat_base["hp_balls"] >= 36) & (bat_base["hp_matches"] >= 4)).sum()),
            "qualified_bowlers": int(((bowl_base["hp_balls"] >= 36) & (bowl_base["hp_matches"] >= 4)).sum()),
        },
        "strict_floor_72b_8m": {
            "qualified_batters": int(((bat_base["hp_balls"] >= 72) & (bat_base["hp_matches"] >= 8)).sum()),
            "qualified_bowlers": int(((bowl_base["hp_balls"] >= 72) & (bowl_base["hp_matches"] >= 8)).sum()),
        },
    }
    
    all_folds = ["TRAIN_2022_2024", "VAL_2025", "TEST_HOLDOUT_2026"]
    
    # 5. Standout Match Sensitivity (Refit within selected model family on full production dataset)
    standout_bat = run_standout_match_check(bat_match_df, p_dim, "batting", top15_bat_ids, seed=config.seed, chosen_model=chosen_bat, all_folds=all_folds, deliv_hp_df=deliv_hp_20, obs_df=bat_obs_20)
    standout_bowl = run_standout_match_check(bowl_match_df, p_dim, "bowling", top15_bowl_ids, seed=config.seed, chosen_model=chosen_bowl, all_folds=all_folds, deliv_hp_df=deliv_hp_20, obs_df=bowl_obs_20)
    
    # 6. Cluster Bootstrap Stability (100 replicates, refitting within selected model family)
    boot_bat = run_bootstrap_stability(
        bat_match_df,
        p_dim,
        "batting",
        list(dict.fromkeys(top15_bat_ids + shortlist_top10_bat_base)),
        n_replicates=100,
        seed=config.seed,
        chosen_model=chosen_bat,
        all_folds=all_folds,
        deliv_hp_df=deliv_hp_20,
        obs_df=bat_obs_20,
        market_df=market_snapshot_2027,
        shortlist_policy="RR_IPL_POSITIVE_VERIFIED",
        allow_rr_incumbents=True,
    )
    boot_bowl = run_bootstrap_stability(
        bowl_match_df,
        p_dim,
        "bowling",
        list(dict.fromkeys(top15_bowl_ids + shortlist_top10_bowl_base)),
        n_replicates=100,
        seed=config.seed,
        chosen_model=chosen_bowl,
        all_folds=all_folds,
        deliv_hp_df=deliv_hp_20,
        obs_df=bowl_obs_20,
        market_df=market_snapshot_2027,
        shortlist_policy="RR_IPL_POSITIVE_VERIFIED",
        allow_rr_incumbents=True,
    )
    
    # 7. Borderline Cohort Review (Ranks 8 to 15)
    borderline_review_bat = []
    for r in range(7, 15):
        row = bat_base[bat_base["is_qualified"]].iloc[r]
        pid = int(row["player_id"])
        boot_info = boot_bat.get(pid, {})
        borderline_review_bat.append({
            "rank": r + 1,
            "player_id": pid,
            "player_name": row["player_name"],
            "role": row["inferred_role"],
            "score_q25": float(row["conservative_score_q25"]),
            "hp_matches": int(row["hp_matches"]),
            "hp_balls": int(row["hp_balls"]),
            "top10_freq_boot": boot_info.get("top10_inclusion_freq", 0.0),
            "rank_ci_90": boot_info.get("rank_ci_90", []),
            "shortlist_top10_freq_boot": boot_info.get("shortlist_top10_inclusion_freq", boot_info.get("top10_inclusion_freq", 0.0)),
            "shortlist_rank_ci_90": boot_info.get("shortlist_rank_ci_90", boot_info.get("rank_ci_90", [])),
            "shortlist_eligible_draws": boot_info.get("shortlist_eligible_draws", 100),
            "shortlist_central_rank_range": boot_info.get("central_rank_range", []),
            "assessment": f"{int(boot_info.get('top10_inclusion_freq', 0.0) * 100)}% bootstrap inclusion",
            "shortlist_assessment": f"{int(boot_info.get('shortlist_top10_inclusion_freq', 0.0) * 100)}% shortlist inclusion",
        })
        
    borderline_review_bowl = []
    for r in range(7, 15):
        row = bowl_base[bowl_base["is_qualified"]].iloc[r]
        pid = int(row["player_id"])
        boot_info = boot_bowl.get(pid, {})
        borderline_review_bowl.append({
            "rank": r + 1,
            "player_id": pid,
            "player_name": row["player_name"],
            "role": row["inferred_role"],
            "score_q25": float(row["conservative_score_q25"]),
            "hp_matches": int(row["hp_matches"]),
            "hp_balls": int(row["hp_balls"]),
            "top10_freq_boot": boot_info.get("top10_inclusion_freq", 0.0),
            "rank_ci_90": boot_info.get("rank_ci_90", []),
            "shortlist_top10_freq_boot": boot_info.get("shortlist_top10_inclusion_freq", boot_info.get("top10_inclusion_freq", 0.0)),
            "shortlist_rank_ci_90": boot_info.get("shortlist_rank_ci_90", boot_info.get("rank_ci_90", [])),
            "shortlist_eligible_draws": boot_info.get("shortlist_eligible_draws", 100),
            "shortlist_central_rank_range": boot_info.get("central_rank_range", []),
            "assessment": f"{int(boot_info.get('top10_inclusion_freq', 0.0) * 100)}% bootstrap inclusion",
            "shortlist_assessment": f"{int(boot_info.get('shortlist_top10_inclusion_freq', 0.0) * 100)}% shortlist inclusion",
        })
        
    chosen_model_name = chosen_overall

    robustness_report = {
        "stage": "10_robustness_checks",
        "chosen_models": {
            "overall": chosen_model_name,
            "batting": chosen_bat,
            "bowling": chosen_bowl,
        },
        "pressure_percentile_sensitivity": pressure_sensitivity,
        "competition_tier_sensitivity": tier_sensitivity,
        "workload_evidence_floor_sensitivity": workload_sensitivity,
        "standout_match_sensitivity": {
            "batting_top15": standout_bat,
            "bowling_top15": standout_bowl,
        },
        "bootstrap_stability_100_replicates": {
            "batting_top15": [boot_bat[pid] for pid in top15_bat_ids],
            "bowling_top15": [boot_bowl[pid] for pid in top15_bowl_ids],
            "batting_shortlist_top10": [boot_bat[pid] for pid in shortlist_top10_bat_base],
            "bowling_shortlist_top10": [boot_bowl[pid] for pid in shortlist_top10_bowl_base],
        },
        "borderline_cohort_review_ranks_8_to_15": {
            "batting": borderline_review_bat,
            "bowling": borderline_review_bowl,
        },
        "governance_decision": (
            f"Model parameters and rankings remain strictly frozen on {chosen_model_name} "
            f"with 20% leverage threshold and standard evidence floor (48b, 6m). "
            f"Emerging-tier dependency and standout-match sensitivity are surfaced to inform "
            f"Stage 11 auction eligibility and Rajasthan Royals squad-fit decisions."
        ),
    }
    
    out_path = out / "robustness_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(robustness_report, f, indent=2)
        
    checks_path = out / "robustness_checks.json"
    with open(checks_path, "w", encoding="utf-8") as f:
        json.dump(robustness_report, f, indent=2)
        
    output_files = {
        "robustness_report.json": out_path,
        "robustness_checks.json": checks_path,
    }
    output_fingerprints = {fname: compute_sha256(fpath) for fname, fpath in output_files.items()}
    return robustness_report, output_fingerprints
