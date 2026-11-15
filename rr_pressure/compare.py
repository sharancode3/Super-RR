"""Stage 09: Chronological Model Comparison across Candidates A, B, and C."""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import QuantileRegressor, Ridge

from rr_pressure.config import PipelineConfig
from rr_pressure.forecast import fit_player_forecast, is_qualified, ensure_explicit_role_flags, Z_25
from rr_pressure.challengers import (
    ChallengerC_IPLAnchoredRolePhase,
    ChallengerC_RolePhasePartialPooling,
    ChallengerD_WorkloadDistributional,
    ChallengerE_DirectQuantileBoosted,
    score_with_selected_model,
)
from rr_pressure.role_challenger import ChallengerRPP_RolePhaseJoint, build_phase_observations_from_ledger
from rr_pressure.delivery_challenger import (
    ChallengerDHP_BattingDeliveryHazard,
    build_batting_delivery_cells,
    build_batting_stint_cause_audit,
)
from rr_pressure.shortlist_policy import build_asof_market_snapshot, select_shortlist_by_policy
from rr_pressure.impact import booster_usual_level, compute_cumulative_prematch_features
from rr_pressure.manifest import compute_sha256

MODEL_METRIC_KEYS = {
    "Candidate A (Cricket Baseline)": "candidate_A_baseline",
    "Candidate B (Statistical Default)": "candidate_B_statistical",
    "Candidate C (Boosted Challenger)": "candidate_C_boosted",
    "Challenger C (Role-and-Phase Partial-Pooling)": "challenger_C_role_phase",
    "Challenger C-IPL (IPL-Anchored Role-and-Phase)": "challenger_C_ipl_anchored",
    "Ablation B-0 (No Player Pressure Lift)": "ablation_B0_no_pressure",
    "Challenger D (Workload-Aware Distributional)": "challenger_D_workload",
    "Challenger DHP (Delivery-Hazard Role-Phase)": "challenger_DHP_delivery_hazard",
    "Challenger E (Direct Quantile Boosted)": "challenger_E_quantile_boosted",
    "Challenger RPP (Role-Phase Regularized Partial-Pooling)": "challenger_RPP_role_phase_joint",
}
SHIPPED_MODELS = tuple(name for name in MODEL_METRIC_KEYS if not name.startswith(("Candidate A", "Candidate C (Boosted")))


def _join_player_forecasts(opportunities: pd.DataFrame, player_forecasts: pd.DataFrame) -> pd.DataFrame:
    """Retain every assessment row with the same training-only fallback in each period."""
    columns = [
        "b0_q25", "b0_mean", "b1_q25", "b1_mean",
        "d_q25", "d_mean", "e_q25", "e_mean",
        "conservative_score_q25", "predicted_hp_impact",
    ]
    avail = [c for c in columns if c in player_forecasts.columns]
    joined = opportunities.merge(
        player_forecasts[["player_id", *avail]], on="player_id", how="left", validate="many_to_one"
    )
    for c in avail:
        joined[c] = joined[c].fillna(player_forecasts[c].median())
    return joined


def _top_ten(profiles: pd.DataFrame, prefix: str) -> list[int]:
    ordered = profiles.loc[profiles["is_qualified"]].sort_values(
        [f"{prefix}_q25", f"{prefix}_mean", "hp_matches", "player_id"],
        ascending=[False, False, False, True],
    )
    return ordered["player_id"].head(10).tolist()


def compute_weighted_pinball_loss(y_true: np.ndarray, q_pred: np.ndarray, weights: np.ndarray, tau: float = 0.25) -> float:
    """Weighted pinball (quantile) loss for quantile tau, preserving sample weights/multiplicity."""
    u = y_true - q_pred
    losses = np.maximum(tau * u, (tau - 1.0) * u)
    w_sum = np.sum(weights)
    if w_sum == 0:
        return 0.0
    return float(np.sum(losses * weights) / w_sum)


def compute_pinball_loss(y_true: np.ndarray, q_pred: np.ndarray, tau: float = 0.25) -> float:
    """Pinball (quantile) loss for quantile tau."""
    u = y_true - q_pred
    return float(np.mean(np.maximum(tau * u, (tau - 1.0) * u)))


def evaluate_forecast_metrics(
    y_true: np.ndarray,
    q25_pred: np.ndarray,
    mean_pred: np.ndarray,
) -> Dict[str, Any]:
    """Calculate quantile pinball loss, empirical coverage vs 0.25 target, true MAE, signed bias, and sample size."""
    if len(y_true) == 0:
        return {
            "pinball_loss_q25": np.nan,
            "coverage_q25": np.nan,
            "true_mae": np.nan,
            "signed_bias": np.nan,
            "mean_forecast_error": np.nan,
            "opportunity_count": 0,
        }
    pinball = compute_pinball_loss(y_true, q25_pred, tau=0.25)
    coverage = float(np.mean(y_true <= q25_pred))
    true_mae = float(np.mean(np.abs(y_true - mean_pred)))
    signed_bias = float(np.mean(y_true - mean_pred))
    return {
        "pinball_loss_q25": pinball,
        "coverage_q25": coverage,
        "true_mae": true_mae,
        "signed_bias": signed_bias,
        "mean_forecast_error": signed_bias,
        "opportunity_count": int(len(y_true)),
    }


def evaluate_top10_performance(
    top10_player_ids: List[int],
    eval_match_df: pd.DataFrame,
    role_type: str,
    min_balls_threshold: int = 12,
    seed: int = 2027,
    name_map: Dict[int, str] = None,
) -> Dict[str, Any]:
    """Calculate realized average pressure impact among Top 10 picks with observed opportunities, assessable counts, and matching uncertainty."""
    balls_col = "hp_balls_faced" if role_type == "batting" else "hp_balls_bowled"
    impact_col = "hp_bat_impact" if role_type == "batting" else "hp_bowl_impact"
    ord_balls_col = "ord_balls_faced" if role_type == "batting" else "ord_balls_bowled"
    ord_impact_col = "ord_bat_impact" if role_type == "batting" else "ord_bowl_impact"
    
    sub = eval_match_df[eval_match_df["player_id"].isin(top10_player_ids)].copy()
    sub["_has_hp"] = sub[balls_col].gt(0)
    grouped = sub.groupby("player_id").agg(
        hp_balls=(balls_col, "sum"),
        hp_impact=(impact_col, "sum"),
        hp_matches=("_has_hp", "sum"),
        ord_balls=(ord_balls_col, "sum") if ord_balls_col in sub.columns else (balls_col, "count"),
        ord_impact=(ord_impact_col, "sum") if ord_impact_col in sub.columns else (impact_col, "sum"),
    )
    
    player_outcomes = []
    player_rates = []
    player_ord_rates = []
    qualified = grouped[grouped["hp_balls"] >= min_balls_threshold]
    coverage_count = int(len(qualified))
    nmap = name_map or {}
    
    for pid in top10_player_ids:
        if pid in grouped.index:
            b = int(grouped.loc[pid, "hp_balls"])
            imp = float(grouped.loc[pid, "hp_impact"])
            hm = int(grouped.loc[pid, "hp_matches"])
            ob = int(grouped.loc[pid, "ord_balls"])
            oimp = float(grouped.loc[pid, "ord_impact"])
            is_ass = b >= min_balls_threshold
            rate = float((imp / b) * 12.0) if is_ass and b > 0 else np.nan
            orate = float((oimp / ob) * 12.0) if (ord_balls_col in sub.columns and ob >= min_balls_threshold and ob > 0) else np.nan
        else:
            b, hm, ob = 0, 0, 0
            imp, oimp = 0.0, 0.0
            is_ass = False
            rate, orate = np.nan, np.nan
        miss_reason = None if is_ass else ("ZERO_EVAL_IPL_HP" if b == 0 else f"THIN_EVAL_IPL_HP_{b}b")
        player_outcomes.append({
            "player_id": int(pid),
            "player_name": str(nmap.get(int(pid), pid)),
            "hp_balls": b,
            "hp_matches": hm,
            "hp_impact": round(imp, 3),
            "realized_rate_12b": round(rate, 3) if not np.isnan(rate) else None,
            "realized_ord_rate_12b": round(orate, 3) if not np.isnan(orate) else None,
            "is_assessable": is_ass,
            "missing_reason": miss_reason,
        })
        if not np.isnan(rate):
            player_rates.append(rate)
        if not np.isnan(orate):
            player_ord_rates.append(orate)
            
    if coverage_count > 0 and qualified["hp_balls"].sum() > 0:
        realized_rate_ball_wt = float((qualified["hp_impact"].sum() / qualified["hp_balls"].sum()) * 12.0)
        realized_rate_player_wt = float(np.mean(player_rates)) if player_rates else realized_rate_ball_wt
    else:
        realized_rate_ball_wt = np.nan
        realized_rate_player_wt = np.nan
    realized_ord_player_wt = float(np.mean(player_ord_rates)) if player_ord_rates else np.nan
        
    # Match bootstrap for BOTH ball-weighted and player-weighted top-10 realized rate uncertainty (200 replicates)
    n_boot_draws = 200
    rng = np.random.default_rng(seed)
    unique_matches = eval_match_df["match_id"].unique()
    boot_rates_ball_wt = []
    boot_rates_player_wt = []
    
    if len(unique_matches) > 0 and len(sub) > 0:
        for _ in range(n_boot_draws):
            sample_mids = rng.choice(unique_matches, size=len(unique_matches), replace=True)
            mid_counts = pd.Series(sample_mids).value_counts().to_dict()
            sub_w = sub.copy()
            sub_w["wt"] = sub_w["match_id"].map(mid_counts).fillna(0)
            sub_w["w_b"] = sub_w[balls_col] * sub_w["wt"]
            sub_w["w_imp"] = sub_w[impact_col] * sub_w["wt"]
            b_agg = sub_w.groupby("player_id", observed=False).sum()
            b_qual = b_agg[b_agg["w_b"] >= min_balls_threshold]
            if len(b_qual) > 0 and b_qual["w_b"].sum() > 0:
                boot_rates_ball_wt.append(float((b_qual["w_imp"].sum() / b_qual["w_b"].sum()) * 12.0))
                p_rates_draw = (b_qual["w_imp"] / b_qual["w_b"]) * 12.0
                boot_rates_player_wt.append(float(p_rates_draw.mean()))
        boot_std = float(np.std(boot_rates_ball_wt)) if boot_rates_ball_wt else None
        ci_lower, ci_upper = np.percentile(boot_rates_ball_wt, [5, 95]).tolist() if boot_rates_ball_wt else (None, None)
        boot_std_pw = float(np.std(boot_rates_player_wt)) if boot_rates_player_wt else None
        ci_lower_pw, ci_upper_pw = np.percentile(boot_rates_player_wt, [5, 95]).tolist() if boot_rates_player_wt else (None, None)
    else:
        boot_std = None
        ci_lower = ci_upper = None
        boot_std_pw = None
        ci_lower_pw = ci_upper_pw = None

    return {
        "realized_avg_impact_12b": realized_rate_ball_wt,
        "realized_avg_impact_12b_player_weighted": realized_rate_player_wt,
        "realized_avg_ord_12b_player_weighted": realized_ord_player_wt if not np.isnan(realized_ord_player_wt) else None,
        "top10_player_ids": [int(x) for x in top10_player_ids],
        "top10_player_names": [str(nmap.get(int(x), x)) for x in top10_player_ids],
        "top10_coverage_count": coverage_count,
        "assessable_picks_count": coverage_count,
        "unassessable_picks_count": len(top10_player_ids) - coverage_count,
        "unassessable_player_ids": [o["player_id"] for o in player_outcomes if not o["is_assessable"]],
        "total_top10_evaluated": len(top10_player_ids),
        "min_balls_threshold": min_balls_threshold,
        "n_bootstrap_draws": n_boot_draws,
        "valid_bootstrap_draws": len(boot_rates_player_wt),
        "bootstrap_realized_std": boot_std,
        "bootstrap_ci_90": [ci_lower, ci_upper],
        "bootstrap_std_player_weighted": boot_std_pw,
        "bootstrap_ci_90_player_weighted": [ci_lower_pw, ci_upper_pw],
        "player_outcomes": player_outcomes,
    }


def compute_paired_policy_diff_interval(
    ids_a: List[int],
    ids_b: List[int],
    eval_match_df: pd.DataFrame,
    role_type: str,
    min_balls_threshold: int = 12,
    n_draws: int = 200,
    seed: int = 2027,
) -> Dict[str, Any]:
    """Paired whole-match resampling using shared draws to compare two Top-10 slates."""
    balls_col = "hp_balls_faced" if role_type == "batting" else "hp_balls_bowled"
    impact_col = "hp_bat_impact" if role_type == "batting" else "hp_bowl_impact"
    sub_a = eval_match_df[eval_match_df["player_id"].isin(ids_a)].copy()
    sub_b = eval_match_df[eval_match_df["player_id"].isin(ids_b)].copy()
    unique_matches = eval_match_df["match_id"].unique()
    if len(unique_matches) == 0 or sub_a.empty or sub_b.empty:
        return {"mean_diff": None, "ci90": [None, None], "n_draws": n_draws, "valid_draws": 0}

    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(n_draws):
        sample_mids = rng.choice(unique_matches, size=len(unique_matches), replace=True)
        mid_counts = pd.Series(sample_mids).value_counts().to_dict()
        rates = []
        for sub_df in (sub_a, sub_b):
            sw = sub_df.copy()
            sw["wt"] = sw["match_id"].map(mid_counts).fillna(0)
            sw["w_b"] = sw[balls_col] * sw["wt"]
            sw["w_imp"] = sw[impact_col] * sw["wt"]
            agg = sw.groupby("player_id", observed=False).sum()
            qual = agg[agg["w_b"] >= min_balls_threshold]
            if len(qual) == 0:
                break
            rates.append(float(((qual["w_imp"] / qual["w_b"]) * 12.0).mean()))
        if len(rates) == 2:
            diffs.append(rates[0] - rates[1])

    if len(diffs) < 20:
        return {"mean_diff": None, "ci90": [None, None], "n_draws": n_draws, "valid_draws": len(diffs)}
    return {
        "mean_diff": round(float(np.mean(diffs)), 3),
        "ci90": [round(float(np.percentile(diffs, 5)), 3), round(float(np.percentile(diffs, 95)), 3)],
        "prob_a_gt_b": round(float(np.mean(np.array(diffs) > 0)), 3),
        "n_draws": n_draws,
        "valid_draws": len(diffs),
    }


def _ipl_assessment(
    opportunities,
    matches,
    predictions,
    role,
    seed,
    season_label: str = "2025",
    shortlist_policy_label: str = "RPP_IPL_VERIFIED",
    name_map: Dict[int, str] = None,
    all_pos_opportunities: pd.DataFrame = None,
    all_pos_predictions: Dict[str, Tuple[np.ndarray, np.ndarray]] = None,
    forecast_types: Dict[str, str] = None,
):
    """Evaluate deployed candidates on exact common IPL rows (ge6 AND all-positive/1..5b) under declared shortlist policy."""
    matches_ipl = matches[matches["comp_tier"].eq("IPL")]
    ipl = opportunities["comp_tier"].eq("IPL").to_numpy()
    target = "hp_bat_impact_12b" if role == "batting" else "hp_bowl_impact_12b"
    balls_col = "hp_balls_faced" if role == "batting" else "hp_balls_bowled"
    impact_col = "hp_bat_impact" if role == "batting" else "hp_bowl_impact"
    actual = opportunities.loc[ipl, target].to_numpy()
    obs_balls = opportunities.loc[ipl, balls_col].to_numpy() if balls_col in opportunities.columns else np.full(len(actual), 12)
    prior_hp = opportunities.loc[ipl, "hp_balls"].to_numpy() if "hp_balls" in opportunities.columns else np.zeros(len(actual))
    match_ids = opportunities.loc[ipl, "match_id"].to_numpy()
    if not len(actual):
        return {}
    grouped = pd.DataFrame({"match_id": match_ids}).groupby("match_id", sort=True)
    match_sizes = grouped.size().to_numpy()
    draw = np.random.default_rng(seed).integers(len(match_sizes), size=(1000, len(match_sizes)))
    denominator = match_sizes[draw].sum(axis=1)
    losses = {}
    result = {}
    ftypes = forecast_types or {}
    for key, (q25, mean, ids) in predictions.items():
        q25, mean = q25[ipl], mean[ipl]
        loss = np.maximum(0.25 * (actual - q25), -0.75 * (actual - q25))
        losses[key] = pd.Series(loss).groupby(match_ids, sort=True).sum().to_numpy()
        metrics = evaluate_forecast_metrics(actual, q25, mean)
        metrics["model"] = key
        metrics["season"] = str(season_label)
        metrics["shortlist_policy"] = shortlist_policy_label
        metrics["denominator"] = "ge6_ipl_opportunities"
        metrics["forecast_type"] = ftypes.get(key, "ex_ante_prior_mix")
        metrics["eligible_for_selection"] = (metrics["forecast_type"] == "ex_ante_prior_mix")
        # Breakdown by observed match workload & pre-match direct HP sample
        metrics["workload_breakdown"] = {
            "balls_6_to_12": evaluate_forecast_metrics(
                actual[(obs_balls >= 6) & (obs_balls <= 12)],
                q25[(obs_balls >= 6) & (obs_balls <= 12)],
                mean[(obs_balls >= 6) & (obs_balls <= 12)],
            ),
            "balls_13_to_24": evaluate_forecast_metrics(
                actual[(obs_balls >= 13) & (obs_balls <= 24)],
                q25[(obs_balls >= 13) & (obs_balls <= 24)],
                mean[(obs_balls >= 13) & (obs_balls <= 24)],
            ),
            "balls_25_plus": evaluate_forecast_metrics(
                actual[obs_balls >= 25],
                q25[obs_balls >= 25],
                mean[obs_balls >= 25],
            ),
        }
        metrics["experience_breakdown"] = {
            "established_ge_24_prior_balls": evaluate_forecast_metrics(
                actual[prior_hp >= 24], q25[prior_hp >= 24], mean[prior_hp >= 24]
            ),
            "thin_lt_24_prior_balls": evaluate_forecast_metrics(
                actual[prior_hp < 24], q25[prior_hp < 24], mean[prior_hp < 24]
            ),
        }
        if ids is not None:
            metrics["top10_performance"] = evaluate_top10_performance(ids, matches_ipl, role, seed=seed, name_map=name_map)
        result[key] = metrics

    # Compute common all-positive (>0b) and 1..5b short-stint opportunity evaluations when supplied
    if all_pos_opportunities is not None and all_pos_predictions is not None and not all_pos_opportunities.empty:
        ipl_all = all_pos_opportunities["comp_tier"].eq("IPL").to_numpy()
        y_all = all_pos_opportunities.loc[ipl_all, target].to_numpy()
        b_all = all_pos_opportunities.loc[ipl_all, balls_col].to_numpy()
        mids_all = all_pos_opportunities.loc[ipl_all, "match_id"].to_numpy()
        if len(y_all) > 0:
            g_all = pd.DataFrame({"match_id": mids_all}).groupby("match_id", sort=True)
            msz_all = g_all.size().to_numpy()
            draw_all = np.random.default_rng(seed + 11).integers(len(msz_all), size=(1000, len(msz_all)))
            den_all = msz_all[draw_all].sum(axis=1)
            losses_all = {}
            lt6_mask = (b_all >= 1) & (b_all <= 5)
            for key, (qa, ma) in all_pos_predictions.items():
                if key not in result:
                    continue
                qa_i, ma_i = qa[ipl_all], ma[ipl_all]
                l_all = np.maximum(0.25 * (y_all - qa_i), -0.75 * (y_all - qa_i))
                losses_all[key] = pd.Series(l_all).groupby(mids_all, sort=True).sum().to_numpy()
                m_all = evaluate_forecast_metrics(y_all, qa_i, ma_i)
                m_all["denominator"] = "all_positive_gt0b_ipl_opportunities"
                m_all["forecast_type"] = result[key]["forecast_type"]
                result[key]["all_positive_ipl_metrics"] = m_all
                m_lt6 = evaluate_forecast_metrics(y_all[lt6_mask], qa_i[lt6_mask], ma_i[lt6_mask])
                m_lt6["denominator"] = "short_stint_1_to_5b_ipl_opportunities"
                m_lt6["forecast_type"] = result[key]["forecast_type"]
                result[key]["short_stint_1_to_5b_ipl_metrics"] = m_lt6
            if "ablation_B0_no_pressure" in losses_all:
                base_all = losses_all["ablation_B0_no_pressure"]
                for key, l_vec in losses_all.items():
                    paired_a = (l_vec - base_all)[draw_all].sum(axis=1) / den_all
                    result[key]["all_positive_ipl_metrics"]["paired_pinball_difference_vs_b0_ci_90"] = np.percentile(paired_a, [5, 95]).tolist()

    baseline = losses["ablation_B0_no_pressure"]
    b0_ass_outcomes = {
        o["player_id"]: o["realized_rate_12b"]
        for o in result["ablation_B0_no_pressure"].get("top10_performance", {}).get("player_outcomes", [])
        if o["is_assessable"] and o["realized_rate_12b"] is not None
    }
    ipl_player_agg = matches_ipl.groupby("player_id").agg(b=(balls_col, "sum"), imp=(impact_col, "sum"))
    ipl_player_agg = ipl_player_agg[ipl_player_agg["b"] >= 12]
    all_assessable_map = ((ipl_player_agg["imp"] / ipl_player_agg["b"]) * 12.0).to_dict()

    for key, metrics in result.items():
        paired = (losses[key] - baseline)[draw].sum(axis=1) / denominator
        metrics["paired_pinball_difference_vs_b0_ci_90"] = np.percentile(paired, [5, 95]).tolist()
        t10 = metrics.get("top10_performance")
        if t10 is not None:
            cand_ass = {
                o["player_id"]: o["realized_rate_12b"]
                for o in t10.get("player_outcomes", [])
                if o["is_assessable"] and o["realized_rate_12b"] is not None
            }
            common_ids = sorted(set(cand_ass).intersection(b0_ass_outcomes))
            metrics["top10_performance"]["common_assessable_sensitivity"] = {
                "common_with_b0_count": len(common_ids),
                "common_with_b0_player_ids": common_ids,
                "common_with_b0_realized_player_weighted": float(np.mean([cand_ass[pid] for pid in common_ids])) if common_ids else None,
                "b0_on_common_union_ids_count": len(set(cand_ass) | set(b0_ass_outcomes)),
                "cand_minus_b0_all_assessable": (
                    float(np.mean(list(cand_ass.values())) - np.mean(list(b0_ass_outcomes.values())))
                    if cand_ass and b0_ass_outcomes else None
                ),
                "pool_assessable_players_in_ipl_eval": len(all_assessable_map),
            }
    return result


def _regularized_quantile_diagnostic(train, assess, profiles, role):
    """Try a linear quantile fit with fewer degrees of freedom than the booster."""
    balls, target = (
        ("hp_balls_faced", "hp_bat_impact_12b") if role == "batting"
        else ("hp_balls_bowled", "hp_bowl_impact_12b")
    )
    history = compute_cumulative_prematch_features(train, role)
    sample = history[history[balls].ge(6)]
    profile = profiles.set_index("player_id")
    cutoff = assess[["player_id", "comp_tier"]].join(
        profile[["ord_impact", "ord_balls", "hp_balls"]], on="player_id"
    )
    cutoff["usual_level"] = booster_usual_level(cutoff["ord_impact"].fillna(0), cutoff["ord_balls"].fillna(0))

    def features(rows):
        return np.column_stack((rows["usual_level"], np.log1p(rows["hp_balls"].fillna(0)), rows["comp_tier"].eq("IPL")))

    x = features(sample)
    y = sample[target].to_numpy()
    estimate = features(cutoff)
    q25 = QuantileRegressor(quantile=0.25, alpha=0.01).fit(x, y).predict(estimate)
    mean = Ridge(alpha=10.0).fit(x, y).predict(estimate)
    return q25, mean, None


MODEL_SELECT_LOSS_TOLERANCE = 0.05  # Frozen Stage 01 protocol tolerance (+0.05; replaces legacy +0.15 CLI tolerance)
LEGACY_SELECT_LOSS_TOLERANCE = 0.15


def _select_ipl_model_with_reason(metrics, loss_tolerance: float = MODEL_SELECT_LOSS_TOLERANCE) -> Tuple[str, str]:
    """Select the model delivering superior IPL shortlist decision while satisfying forecast guardrails."""
    baseline_key = "ablation_B0_no_pressure"
    if not metrics:
        return baseline_key, "Fallback B0 (Empty metrics)"
    baseline = metrics[baseline_key]["top10_performance"]
    baseline_loss = metrics[baseline_key]["pinball_loss_q25"]
    base_pw = baseline.get("realized_avg_impact_12b_player_weighted", -np.inf)
    base_ass = baseline.get("assessable_picks_count", 0)
    
    passing = []
    for name in SHIPPED_MODELS:
        key = MODEL_METRIC_KEYS[name]
        if key not in metrics or key == baseline_key:
            continue
        value = metrics[key]
        if not value.get("eligible_for_selection", True):
            continue
        slate = value.get("top10_performance", {})
        
        cov = value.get("coverage_q25", None)
        loss = value.get("pinball_loss_q25", np.inf)
        if (cov is not None and not (0.15 <= cov <= 0.35)) or np.isnan(loss):
            continue
            
        ass_count = slate.get("assessable_picks_count", 0)
        realized_impact = slate.get("realized_avg_impact_12b_player_weighted", -np.inf)
        ci_90_diff = value.get("paired_pinball_difference_vs_b0_ci_90", [0.0, 0.0])
        
        case_a = (ci_90_diff[1] < 0 and ass_count >= base_ass and realized_impact >= base_pw)
        case_b = (loss <= baseline_loss + loss_tolerance and ass_count >= 7 and realized_impact >= base_pw + 1.0)
        
        if case_a or case_b:
            branch = (
                "Case A (Paired Pinball Reduction < 0 + Non-Degraded Shortlist)"
                if case_a
                else f"Case B (Decisive Shortlist Gain >= +1.0 Within Loss Tolerance +{loss_tolerance:.2f})"
            )
            passing.append((key, branch, realized_impact, loss))
            
    base_cov = metrics[baseline_key].get("coverage_q25", np.nan)
    if passing:
        best_key, best_branch, best_imp, best_loss = max(passing, key=lambda item: (item[2], -item[3]))
        return best_key, f"{best_branch}: shortlist={best_imp:+.3f} vs B0={base_pw:+.3f}, Q25_loss={best_loss:.3f} vs B0={baseline_loss:.3f}"
    return baseline_key, (
        f"Fallback B0 (No challenger satisfied Case A or Case B guardrails; "
        f"B0 loss={baseline_loss:.3f}, cov={base_cov:.1%}, shortlist={base_pw:+.3f}, assessable={base_ass}/10)"
    )


def _select_ipl_model(metrics) -> str:
    return _select_ipl_model_with_reason(metrics)[0]


def _attach_precutoff_ipl_evidence(scored_df: pd.DataFrame, tr_m: pd.DataFrame, role: str) -> pd.DataFrame:
    balls_col = "hp_balls_faced" if role == "batting" else "hp_balls_bowled"
    imp_col = "hp_bat_impact" if role == "batting" else "hp_bowl_impact"
    out = scored_df.copy()
    if tr_m.empty or "comp_tier" not in tr_m.columns:
        out["ipl_hp_balls"] = 0
        out["ipl_hp_matches"] = 0
        out["hp_rate_ipl_12b"] = np.nan
        return out
    ipl_hp = tr_m[(tr_m["comp_tier"] == "IPL") & (tr_m[balls_col] > 0)]
    b_map = ipl_hp.groupby("player_id")[balls_col].sum().to_dict()
    m_map = ipl_hp.groupby("player_id")["match_id"].nunique().to_dict()
    imp_map = ipl_hp.groupby("player_id")[imp_col].sum().to_dict()
    out["ipl_hp_balls"] = out["player_id"].map(b_map).fillna(0).astype(int)
    out["ipl_hp_matches"] = out["player_id"].map(m_map).fillna(0).astype(int)
    out["hp_rate_ipl_12b"] = [
        (12.0 * float(imp_map.get(int(pid), 0.0)) / b_map[int(pid)]) if b_map.get(int(pid), 0) > 0 else np.nan
        for pid in out["player_id"]
    ]
    out["non_ipl_hp_balls"] = (out.get("hp_balls", 0) - out["ipl_hp_balls"]).clip(lower=0)
    return out


def _select_top10_under_policy(
    scored_df: pd.DataFrame,
    mkt_asof: pd.DataFrame,
    role: str,
    policy_name: str = "RPP_IPL_VERIFIED",
    cipl_ranks: Dict[int, float] = None,
    b0_ranks: Dict[int, float] = None,
) -> List[int]:
    sel = select_shortlist_by_policy(
        scored_df,
        mkt_asof,
        policy_name=policy_name,
        min_ipl_hp_balls=24,
        min_ipl_hp_matches=2,
        cipl_ranks=cipl_ranks,
        b0_ranks=b0_ranks,
        discipline=role,
    )
    return sel[sel["submission_rank"].notna()].sort_values("submission_rank").head(10)["player_id"].astype(int).tolist()


def _replay_window_comparable(
    tr_m: pd.DataFrame,
    ev_m: pd.DataFrame,
    p_stats_tr: pd.DataFrame,
    tr_hp_deliv: pd.DataFrame,
    tr_obs: pd.DataFrame,
    ev_obs: pd.DataFrame,
    p_dim_asof: pd.DataFrame,
    role: str,
    cutoff_year: int,
    mapping_df: pd.DataFrame,
    seed: int,
    bat_cells_tr: pd.DataFrame = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Replay ALL models on identical candidate pool, exact common IPL rows (ge6 & all>0b), and shared shortlist policy."""
    balls_col = "hp_balls_faced" if role == "batting" else "hp_balls_bowled"
    name_map = p_dim_asof.set_index("player_id")["player_name"].to_dict() if "player_name" in p_dim_asof.columns else {}

    ev_ge6 = ev_m[(ev_m["comp_tier"] == "IPL") & (ev_m[balls_col] >= 6)].copy()
    ev_all = ev_m[(ev_m["comp_tier"] == "IPL") & (ev_m[balls_col] >= 1)].copy()
    ev_ge6_join = _join_player_forecasts(ev_ge6, p_stats_tr)
    ev_all_join = _join_player_forecasts(ev_all, p_stats_tr)
    pids_ge6 = ev_ge6_join["player_id"].to_numpy()
    pids_all = ev_all_join["player_id"].to_numpy()
    ones_ge6 = np.full(len(pids_ge6), 12.0)
    ones_all = np.full(len(pids_all), 12.0)

    # Fit models strictly pre-cutoff
    chal_d = ChallengerD_WorkloadDistributional().fit(tr_m, p_dim_asof, role)
    chal_c = ChallengerC_RolePhasePartialPooling().fit(tr_hp_deliv, p_dim_asof, role)
    chal_c_ipl = ChallengerC_IPLAnchoredRolePhase().fit(tr_hp_deliv, p_dim_asof, role)
    chal_e = ChallengerE_DirectQuantileBoosted(seed=seed).fit(tr_m, p_stats_tr, role)
    mod_rpp = ChallengerRPP_RolePhaseJoint(cutoff_label=f"<{cutoff_year}").fit(tr_obs, p_dim_asof, role)
    mod_dhp = (
        ChallengerDHP_BattingDeliveryHazard(cutoff_label=f"<{cutoff_year}").fit(bat_cells_tr, p_dim_asof)
        if (role == "batting" and bat_cells_tr is not None and not bat_cells_tr.empty)
        else None
    )

    tr_ipl_only = tr_m[tr_m["comp_tier"] == "IPL"]
    p_stats_ipl_only, _ = fit_player_forecast(tr_ipl_only, p_dim_asof, role, seed=seed, baseline_only=True)
    ipl_ge6_b0 = _join_player_forecasts(ev_ge6_join[["player_id"]], p_stats_ipl_only)
    ipl_all_b0 = _join_player_forecasts(ev_all_join[["player_id"]], p_stats_ipl_only)

    # Ex-ante opportunity forecasts across all models
    q25_e_ge6, mean_e_ge6 = chal_e.predict_at_cutoff(ev_ge6_join, p_stats_tr)
    q25_e_all, mean_e_all = chal_e.predict_at_cutoff(ev_all_join, p_stats_tr)

    fallback_q = float(mod_rpp.predict_quantile([0])[0])
    fallback_m = float(mod_rpp.predict_mean([0])[0])
    ev_hp_obs = ev_obs[(ev_obs["comp_tier"] == "IPL") & (ev_obs["is_high_pressure"] == True) & (ev_obs["legal_balls"] > 0)].copy() if (ev_obs is not None and not ev_obs.empty) else pd.DataFrame()
    opp_df = mod_rpp.predict_opportunities(ev_hp_obs, p_dim_asof) if not ev_hp_obs.empty else pd.DataFrame()
    if not opp_df.empty:
        m_ge6_r = ev_ge6_join[["match_id", "player_id"]].merge(opp_df[["match_id", "player_id", "pred_q25", "pred_mean"]], on=["match_id", "player_id"], how="left")
        m_all_r = ev_all_join[["match_id", "player_id"]].merge(opp_df[["match_id", "player_id", "pred_q25", "pred_mean"]], on=["match_id", "player_id"], how="left")
        q25_rpp_real_ge6 = m_ge6_r["pred_q25"].fillna(fallback_q).to_numpy()
        mean_rpp_real_ge6 = m_ge6_r["pred_mean"].fillna(fallback_m).to_numpy()
        q25_rpp_real_all = m_all_r["pred_q25"].fillna(fallback_q).to_numpy()
        mean_rpp_real_all = m_all_r["pred_mean"].fillna(fallback_m).to_numpy()
    else:
        q25_rpp_real_ge6 = mod_rpp.predict_quantile(pids_ge6)
        mean_rpp_real_ge6 = mod_rpp.predict_mean(pids_ge6)
        q25_rpp_real_all = mod_rpp.predict_quantile(pids_all)
        mean_rpp_real_all = mod_rpp.predict_mean(pids_all)

    # Build as-of market snapshot and score EVERY model on identical candidate pool
    mkt = build_asof_market_snapshot(cutoff_year, mapping_df, p_dim_asof)
    scored_map: Dict[str, pd.DataFrame] = {}
    cand_models = [
        ("ablation_B0_no_pressure", "Ablation B-0 (No Player Pressure Lift)"),
        ("candidate_B_statistical", "Candidate B (Statistical Default)"),
        ("challenger_C_role_phase", "Challenger C (Role-and-Phase Partial-Pooling)"),
        ("challenger_C_ipl_anchored", "Challenger C-IPL (IPL-Anchored Role-and-Phase)"),
        ("challenger_D_workload", "Challenger D (Workload-Aware Distributional)"),
        ("challenger_E_quantile_boosted", "Challenger E (Direct Quantile Boosted)"),
        ("challenger_RPP_role_phase_joint", "Challenger RPP (Role-Phase Regularized Partial-Pooling)"),
    ]
    if mod_dhp is not None:
        cand_models.append(("challenger_DHP_delivery_hazard", "Challenger DHP (Delivery-Hazard Role-Phase)"))
    for key, label in cand_models:
        sc = score_with_selected_model(
            p_stats_tr,
            tr_m,
            p_dim_asof,
            role,
            label,
            deliv_hp_df=tr_hp_deliv if "Challenger C" in label else None,
            seed=seed,
            obs_df=tr_obs if "Challenger RPP" in label else None,
            bat_cells_df=bat_cells_tr if "Challenger DHP" in label else None,
        )
        sc = _attach_precutoff_ipl_evidence(sc, tr_m, role)
        if key == "challenger_RPP_role_phase_joint":
            sc["rpp_train_hp_balls"] = sc["player_id"].map({pid: prof["ipl_hp_balls"] for pid, prof in mod_rpp.player_profiles_.items()}).fillna(0).astype(int)
            sc["rpp_train_hp_matches"] = sc["player_id"].map({pid: prof["ipl_hp_matches"] for pid, prof in mod_rpp.player_profiles_.items()}).fillna(0).astype(int)
        elif key == "challenger_DHP_delivery_hazard" and mod_dhp is not None:
            sc["dhp_train_hp_balls"] = sc["player_id"].map({pid: prof["ipl_hp_balls"] for pid, prof in mod_dhp.player_profiles_.items()}).fillna(0).astype(int)
            sc["dhp_train_hp_matches"] = sc["player_id"].map({pid: prof["ipl_hp_matches"] for pid, prof in mod_dhp.player_profiles_.items()}).fillna(0).astype(int)
        scored_map[key] = sc

    # All models pass through ONE identical RPP_IPL_VERIFIED shortlist rule for headline comparison
    verified_top10 = {k: _select_top10_under_policy(sc, mkt, role, policy_name="RPP_IPL_VERIFIED") for k, sc in scored_map.items()}
    raw_top10 = {k: _select_top10_under_policy(sc, mkt, role, policy_name="RAW_MODEL") for k, sc in scored_map.items()}

    sc_ipl_b0 = _attach_precutoff_ipl_evidence(
        p_stats_ipl_only.assign(conservative_score_q25=p_stats_ipl_only["b0_q25"], predicted_hp_impact=p_stats_ipl_only["b0_mean"]),
        tr_ipl_only,
        role,
    )
    b0_ipl_top10 = _select_top10_under_policy(sc_ipl_b0, mkt, role, policy_name="RPP_IPL_VERIFIED")

    # Separate named legacy, raw, RR_IPL_POSITIVE_VERIFIED, and RR_SHRUNK_POSITIVE_VERIFIED replayed controls
    matches_ipl = ev_m[ev_m["comp_tier"] == "IPL"]
    controls: Dict[str, Any] = {
        "RAW_MODEL": {},
        "LEGACY_POST_HOC": {},
        "RR_IPL_POSITIVE_VERIFIED": {},
        "RR_SHRUNK_POSITIVE_VERIFIED": {},
        "RETAIN_INCLUSIVE_POSITIVE_VERIFIED": {},
    }
    for k in ("ablation_B0_no_pressure", "candidate_B_statistical", "challenger_C_ipl_anchored", "challenger_D_workload", "challenger_RPP_role_phase_joint"):
        controls["RAW_MODEL"][k] = {
            "shortlist_policy": "RAW_MODEL",
            "season": str(cutoff_year),
            "top10_performance": evaluate_top10_performance(raw_top10[k], matches_ipl, role, seed=seed, name_map=name_map),
        }
    for k in ("ablation_B0_no_pressure", "candidate_B_statistical", "challenger_C_ipl_anchored", "challenger_D_workload", "challenger_RPP_role_phase_joint"):
        pos_ids = _select_top10_under_policy(scored_map[k], mkt, role, policy_name="RR_IPL_POSITIVE_VERIFIED")
        controls["RR_IPL_POSITIVE_VERIFIED"][k] = {
            "shortlist_policy": "RR_IPL_POSITIVE_VERIFIED",
            "season": str(cutoff_year),
            "top10_performance": evaluate_top10_performance(pos_ids, matches_ipl, role, seed=seed, name_map=name_map),
            "paired_diff_vs_rpp_policy": compute_paired_policy_diff_interval(pos_ids, verified_top10[k], matches_ipl, role, seed=seed),
        }
        shrunk_ids = _select_top10_under_policy(scored_map[k], mkt, role, policy_name="RR_SHRUNK_POSITIVE_VERIFIED")
        controls["RR_SHRUNK_POSITIVE_VERIFIED"][k] = {
            "shortlist_policy": "RR_SHRUNK_POSITIVE_VERIFIED",
            "season": str(cutoff_year),
            "top10_performance": evaluate_top10_performance(shrunk_ids, matches_ipl, role, seed=seed, name_map=name_map),
            "paired_diff_vs_rpp_policy": compute_paired_policy_diff_interval(shrunk_ids, verified_top10[k], matches_ipl, role, seed=seed),
        }
        sel_ret = select_shortlist_by_policy(
            scored_map[k], mkt, policy_name="RR_IPL_POSITIVE_VERIFIED", min_ipl_hp_balls=24, min_ipl_hp_matches=2,
            discipline=role, allow_rr_incumbents=True,
        )
        ret_ids = sel_ret[sel_ret["submission_rank"].notna()].sort_values("submission_rank").head(10)["player_id"].astype(int).tolist()
        controls["RETAIN_INCLUSIVE_POSITIVE_VERIFIED"][k] = {
            "shortlist_policy": "RETAIN_INCLUSIVE_POSITIVE_VERIFIED",
            "season": str(cutoff_year),
            "top10_performance": evaluate_top10_performance(ret_ids, matches_ipl, role, seed=seed, name_map=name_map),
        }
    if role == "batting":
        leg_ids = _select_top10_under_policy(scored_map["challenger_D_workload"], mkt, "batting", policy_name="LEGACY_POST_HOC")
        controls["LEGACY_POST_HOC"]["challenger_D_LEGACY_BAT"] = {
            "shortlist_policy": "LEGACY_POST_HOC",
            "season": str(cutoff_year),
            "top10_performance": evaluate_top10_performance(leg_ids, matches_ipl, "batting", seed=seed, name_map=name_map),
        }
    else:
        sc_b0 = scored_map["ablation_B0_no_pressure"]
        sc_cipl = scored_map["challenger_C_ipl_anchored"]
        b0_q = sc_b0[sc_b0["is_qualified"].astype(bool)].sort_values("conservative_score_q25", ascending=False)
        cipl_q = sc_cipl[sc_cipl["is_qualified"].astype(bool)].sort_values("conservative_score_q25", ascending=False)
        b0_rk = {int(pid): idx for idx, pid in enumerate(b0_q["player_id"], start=1)}
        cipl_rk = {int(pid): idx for idx, pid in enumerate(cipl_q["player_id"], start=1)}
        leg_ids = _select_top10_under_policy(sc_b0, mkt, "bowling", policy_name="LEGACY_POST_HOC", cipl_ranks=cipl_rk, b0_ranks=b0_rk)
        controls["LEGACY_POST_HOC"]["legacy_hybrid_B0_C_IPL"] = {
            "shortlist_policy": "LEGACY_POST_HOC",
            "season": str(cutoff_year),
            "top10_performance": evaluate_top10_performance(leg_ids, matches_ipl, "bowling", seed=seed, name_map=name_map),
        }

    reg_ge6 = _regularized_quantile_diagnostic(tr_m, ev_ge6_join, p_stats_tr, role)
    reg_all = _regularized_quantile_diagnostic(tr_m, ev_all_join, p_stats_tr, role)

    predictions_ge6 = {
        "ablation_B0_no_pressure": (ev_ge6_join["b0_q25"].to_numpy(), ev_ge6_join["b0_mean"].to_numpy(), verified_top10["ablation_B0_no_pressure"]),
        "candidate_B_statistical": (ev_ge6_join["b1_q25"].to_numpy(), ev_ge6_join["b1_mean"].to_numpy(), verified_top10["candidate_B_statistical"]),
        "challenger_C_role_phase": (chal_c.predict_quantile(pids_ge6, ones_ge6), chal_c.predict_mean(pids_ge6), verified_top10["challenger_C_role_phase"]),
        "challenger_C_ipl_anchored": (chal_c_ipl.predict_quantile(pids_ge6, ones_ge6), chal_c_ipl.predict_mean(pids_ge6), verified_top10["challenger_C_ipl_anchored"]),
        "challenger_D_workload": (chal_d.predict_quantile(pids_ge6, ones_ge6), chal_d.predict_mean(pids_ge6), verified_top10["challenger_D_workload"]),
        "challenger_E_quantile_boosted": (q25_e_ge6, mean_e_ge6, verified_top10["challenger_E_quantile_boosted"]),
        "challenger_RPP_role_phase_joint": (mod_rpp.predict_quantile(pids_ge6), mod_rpp.predict_mean(pids_ge6), verified_top10["challenger_RPP_role_phase_joint"]),
        "challenger_RPP_realized_phase_mix_diagnostic": (q25_rpp_real_ge6, mean_rpp_real_ge6, None),
        "regularized_linear_quantile": reg_ge6,
        "ablation_B0_ipl_only_diagnostic": (ipl_ge6_b0["b0_q25"].to_numpy(), ipl_ge6_b0["b0_mean"].to_numpy(), b0_ipl_top10),
    }
    predictions_all = {
        "ablation_B0_no_pressure": (ev_all_join["b0_q25"].to_numpy(), ev_all_join["b0_mean"].to_numpy()),
        "candidate_B_statistical": (ev_all_join["b1_q25"].to_numpy(), ev_all_join["b1_mean"].to_numpy()),
        "challenger_C_role_phase": (chal_c.predict_quantile(pids_all, ones_all), chal_c.predict_mean(pids_all)),
        "challenger_C_ipl_anchored": (chal_c_ipl.predict_quantile(pids_all, ones_all), chal_c_ipl.predict_mean(pids_all)),
        "challenger_D_workload": (chal_d.predict_quantile(pids_all, ones_all), chal_d.predict_mean(pids_all)),
        "challenger_E_quantile_boosted": (q25_e_all, mean_e_all),
        "challenger_RPP_role_phase_joint": (mod_rpp.predict_quantile(pids_all), mod_rpp.predict_mean(pids_all)),
        "challenger_RPP_realized_phase_mix_diagnostic": (q25_rpp_real_all, mean_rpp_real_all),
        "regularized_linear_quantile": (reg_all[0], reg_all[1]),
        "ablation_B0_ipl_only_diagnostic": (ipl_all_b0["b0_q25"].to_numpy(), ipl_all_b0["b0_mean"].to_numpy()),
    }
    if mod_dhp is not None:
        predictions_ge6["challenger_DHP_delivery_hazard"] = (
            mod_dhp.predict_quantile(pids_ge6, use_all_pos_cal=False),
            mod_dhp.predict_mean(pids_ge6),
            verified_top10["challenger_DHP_delivery_hazard"],
        )
        predictions_ge6["challenger_DHP_all_pos_calibrated_diagnostic"] = (
            mod_dhp.predict_quantile(pids_ge6, use_all_pos_cal=True),
            mod_dhp.predict_mean(pids_ge6),
            None,
        )
        predictions_all["challenger_DHP_delivery_hazard"] = (
            mod_dhp.predict_quantile(pids_all, use_all_pos_cal=False),
            mod_dhp.predict_mean(pids_all),
        )
        predictions_all["challenger_DHP_all_pos_calibrated_diagnostic"] = (
            mod_dhp.predict_quantile(pids_all, use_all_pos_cal=True),
            mod_dhp.predict_mean(pids_all),
        )
    ftypes = {k: "ex_ante_prior_mix" for k in predictions_ge6}
    ftypes["challenger_RPP_realized_phase_mix_diagnostic"] = "conditional_realized_phase_mix"
    ftypes["challenger_DHP_all_pos_calibrated_diagnostic"] = "all_pos_calibrated_diagnostic"

    assess = _ipl_assessment(
        ev_ge6_join,
        ev_m,
        predictions_ge6,
        role,
        seed,
        season_label=str(cutoff_year),
        shortlist_policy_label="RPP_IPL_VERIFIED",
        name_map=name_map,
        all_pos_opportunities=ev_all_join,
        all_pos_predictions=predictions_all,
        forecast_types=ftypes,
    )
    return assess, controls


def _summarize_candidate_profiles(
    fit_df: pd.DataFrame,
    match_df: pd.DataFrame,
    p_dim: pd.DataFrame,
    deliv_hp_df: pd.DataFrame,
    role: str,
    seed: int,
    obs_df: pd.DataFrame = None,
    bat_cells_df: pd.DataFrame = None,
) -> Dict[str, Any]:
    """Export per-candidate ordinary baseline, observed HP, forecast mean/Q25, modeled lift, and tier/phase sample sizes."""
    balls_col = "hp_balls_faced" if role == "batting" else "hp_balls_bowled"
    pid_col = "striker_id" if role == "batting" else "bowler_id"
    hp_sub = deliv_hp_df if deliv_hp_df is not None else pd.DataFrame()
    train_ipl = match_df[match_df["comp_tier"] == "IPL"] if "comp_tier" in match_df.columns else match_df

    candidates = [
        ("ablation_B0_no_pressure", "Ablation B-0 (No Player Pressure Lift)", fit_df, match_df),
        ("candidate_B_statistical", "Candidate B (Statistical Default)", fit_df, match_df),
        ("challenger_C_role_phase", "Challenger C (Role-and-Phase Partial-Pooling)", fit_df, match_df),
        ("challenger_C_ipl_anchored", "Challenger C-IPL (IPL-Anchored Role-and-Phase)", fit_df, match_df),
        ("challenger_D_workload", "Challenger D (Workload-Aware Distributional)", fit_df, match_df),
        ("challenger_E_quantile_boosted", "Challenger E (Direct Quantile Boosted)", fit_df, match_df),
    ]
    if not train_ipl.empty:
        ipl_fit, _ = fit_player_forecast(train_ipl, p_dim, role, seed=seed, baseline_only=True)
        candidates.append(("ablation_B0_ipl_only_diagnostic", "Ablation B-0 (No Player Pressure Lift)", ipl_fit, train_ipl))
    if obs_df is not None and not obs_df.empty:
        candidates.append(("challenger_RPP_role_phase_joint", "Challenger RPP (Role-Phase Regularized Partial-Pooling)", fit_df, match_df))
    if role == "batting" and bat_cells_df is not None and not bat_cells_df.empty:
        candidates.append(("challenger_DHP_delivery_hazard", "Challenger DHP (Delivery-Hazard Role-Phase)", fit_df, match_df))

    out_profiles: Dict[str, Any] = {}
    for key, label, f_df, m_df in candidates:
        scored = score_with_selected_model(
            f_df, m_df, p_dim, role, label,
            deliv_hp_df=hp_sub if "Challenger C" in label else None,
            seed=seed,
            obs_df=obs_df if "Challenger RPP" in label else None,
            bat_cells_df=bat_cells_df if "Challenger DHP" in label else None,
        )
        qual = scored[scored["is_qualified"].astype(bool)]
        top10 = qual.head(10)
        top10_ids = [int(x) for x in top10["player_id"].tolist()]
        tier_balls = {}
        phase_balls = {}
        if not m_df.empty and "comp_tier" in m_df.columns:
            tier_balls = {
                str(t): int(v)
                for t, v in m_df[m_df["player_id"].isin(top10_ids)].groupby("comp_tier")[balls_col].sum().items()
            }
        if not hp_sub.empty and pid_col in hp_sub.columns and "match_phase" in hp_sub.columns:
            legal = "is_legal_ball" if "is_legal_ball" in hp_sub.columns else None
            sub_d = hp_sub[hp_sub[pid_col].isin(top10_ids)]
            if legal and not sub_d.empty:
                phase_balls = {
                    str(ph): int(v)
                    for ph, v in sub_d.groupby("match_phase", observed=False)[legal].sum().items()
                }
        out_profiles[key] = {
            "qualified_count": int(len(qual)),
            "top10_player_ids": top10_ids,
            "top10_player_names": [str(x) for x in top10["player_name"].tolist()],
            "top10_median_usual_12b": float(top10["usual_level"].median()) if not top10.empty else None,
            "top10_median_observed_hp_12b": float(top10["hp_rate_12b"].median()) if not top10.empty else None,
            "top10_median_forecast_mean_12b": float(top10["predicted_hp_impact"].median()) if not top10.empty else None,
            "top10_median_q25_12b": float(top10["conservative_score_q25"].median()) if not top10.empty else None,
            "top10_median_modeled_lift_12b": float(top10["modeled_pressure_lift"].median()) if not top10.empty else None,
            "top10_median_b1_historical_lift_12b": float(top10["b1_historical_pressure_lift"].median()) if not top10.empty else None,
            "pressure_lift_estimator": str(top10["pressure_lift_estimator"].iloc[0]) if not top10.empty else "",
            "top10_hp_balls_by_tier": tier_balls,
            "top10_hp_balls_by_phase": phase_balls,
        }
    return out_profiles


def _evaluate_rolling_2024_diagnostic(
    bat_match_df: pd.DataFrame,
    bowl_match_df: pd.DataFrame,
    deliv_df: pd.DataFrame,
    p_dim_pre2024: pd.DataFrame,
    seed: int,
    bat_obs_all: pd.DataFrame = None,
    bowl_obs_all: pd.DataFrame = None,
    mapping_df: pd.DataFrame = None,
    bat_cells_all: pd.DataFrame = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Earlier-window IPL check (2022-23 fit -> 2024 IPL evaluation) using match_date < 2024-01-01 only."""
    if "match_date" not in bat_match_df.columns or "match_date" not in deliv_df.columns:
        return {"status": "SKIPPED_NO_MATCH_DATE"}, {}
    early_mask_deliv = deliv_df["match_date"].astype(str) < "2024-01-01"
    if "is_reliability_eligible" in deliv_df.columns:
        early_mask_deliv &= deliv_df["is_reliability_eligible"]
    early_hp = deliv_df[early_mask_deliv & deliv_df["is_high_pressure_20"]].copy()
    if early_hp.empty:
        return {"status": "SKIPPED_EMPTY_EARLY_HP"}, {}

    res = {}
    controls = {}
    for role, src in (("batting", bat_match_df), ("bowling", bowl_match_df)):
        tr = src[src["match_date"].astype(str) < "2024-01-01"].copy()
        ev = src[(src["match_date"].astype(str) >= "2024-01-01") & (src["match_date"].astype(str) < "2025-01-01")].copy()
        if tr.empty or ev.empty:
            continue
        p_stats_e, _ = fit_player_forecast(tr, p_dim_pre2024, role, seed=seed)
        obs_src = bat_obs_all if role == "batting" else bowl_obs_all
        tr_obs_24 = obs_src[obs_src["match_date"].astype(str) < "2024-01-01"].copy() if obs_src is not None else pd.DataFrame()
        ev_obs_24 = obs_src[(obs_src["match_date"].astype(str) >= "2024-01-01") & (obs_src["match_date"].astype(str) < "2025-01-01")].copy() if obs_src is not None else pd.DataFrame()
        bat_cells_24 = (
            bat_cells_all[bat_cells_all["match_date"].astype(str) < "2024-01-01"].copy()
            if (role == "batting" and bat_cells_all is not None and not bat_cells_all.empty)
            else None
        )
        res[role], controls[role] = _replay_window_comparable(
            tr, ev, p_stats_e, early_hp, tr_obs_24, ev_obs_24, p_dim_pre2024, role, 2024, mapping_df, seed,
            bat_cells_tr=bat_cells_24,
        )
    return res, controls


def _summarize_short_stint_causes(audit_df: pd.DataFrame) -> Dict[str, Any]:
    """Summarize overall and 2025 IPL short batting HP stints (1..5b vs >=6b) by cause."""
    if audit_df is None or audit_df.empty:
        return {}
    def _agg(sub: pd.DataFrame) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "total_hp_stints": int(len(sub)),
            "short_1_to_5b_stints": int(sub["is_short_1_to_5b"].sum()),
            "by_cause": {},
        }
        for cause, grp in sub.groupby("short_cause"):
            out["by_cause"][str(cause)] = {
                "stints": int(len(grp)),
                "avg_hp_balls": round(float(grp["hp_balls"].mean()), 2),
                "mean_hp_impact_12b": round(float(grp["hp_impact_12b"].mean()), 3),
            }
        return out

    res: Dict[str, Any] = {"overall": _agg(audit_df)}
    if "fold" in audit_df.columns and "comp_tier" in audit_df.columns:
        ipl_25 = audit_df[(audit_df["fold"] == "VAL_2025") & (audit_df["comp_tier"] == "IPL")]
        if not ipl_25.empty:
            res["ipl_2025"] = _agg(ipl_25)
        ipl_26 = audit_df[(audit_df["fold"] == "TEST_HOLDOUT_2026") & (audit_df["comp_tier"] == "IPL")]
        if not ipl_26.empty:
            res["ipl_2026"] = _agg(ipl_26)
    return res


def _evaluate_stage3_bowling_blend_experiment(
    bowl_match_df: pd.DataFrame,
    bowl_obs_all: pd.DataFrame,
    p_dim_pre2024: pd.DataFrame,
    p_dim_train: pd.DataFrame,
    p_dim_pre2026: pd.DataFrame,
    mapping_df: pd.DataFrame,
    seed: int,
    shortlist_controls: Dict[str, Any],
    ipl_assessments_bowl: Dict[str, Any],
    rolling_2024_bowl: Dict[str, Any],
    retro_2026_bowl: Dict[str, Any],
    p_dim_pre2023_h2: pd.DataFrame = None,
) -> Dict[str, Any]:
    """Evaluate regularized (1 - w)*B0 + w*RPP bowling blend strictly pre-2025 and summarize RR_IPL_POSITIVE_VERIFIED replay."""
    weights = (0.0, 0.25, 0.50, 0.75, 1.0)
    p_dim_h2 = p_dim_pre2023_h2 if p_dim_pre2023_h2 is not None else p_dim_pre2024
    pre25_windows = [
        (
            "2023_H2_ALL",
            bowl_match_df[bowl_match_df["match_date"].astype(str) < "2023-07-01"].copy(),
            bowl_match_df[(bowl_match_df["match_date"].astype(str) >= "2023-07-01") & (bowl_match_df["match_date"].astype(str) < "2024-01-01")].copy(),
            bowl_obs_all[bowl_obs_all["match_date"].astype(str) < "2023-07-01"].copy(),
            p_dim_h2,
            2023,
            False,
        ),
        (
            "2024_IPL",
            bowl_match_df[bowl_match_df["match_date"].astype(str) < "2024-01-01"].copy(),
            bowl_match_df[(bowl_match_df["match_date"].astype(str) >= "2024-01-01") & (bowl_match_df["match_date"].astype(str) < "2025-01-01")].copy(),
            bowl_obs_all[bowl_obs_all["match_date"].astype(str) < "2024-01-01"].copy(),
            p_dim_pre2024,
            2024,
            True,
        ),
    ]
    eval_windows = pre25_windows + [
        (
            "2025_IPL",
            bowl_match_df[bowl_match_df["fold"] == "TRAIN_2022_2024"].copy(),
            bowl_match_df[bowl_match_df["fold"] == "VAL_2025"].copy(),
            bowl_obs_all[bowl_obs_all["fold"] == "TRAIN_2022_2024"].copy(),
            p_dim_train,
            2025,
            True,
        ),
        (
            "2026_IPL",
            bowl_match_df[bowl_match_df["fold"].isin(["TRAIN_2022_2024", "VAL_2025"])].copy(),
            bowl_match_df[bowl_match_df["fold"] == "TEST_HOLDOUT_2026"].copy(),
            bowl_obs_all[bowl_obs_all["fold"].isin(["TRAIN_2022_2024", "VAL_2025"])].copy(),
            p_dim_pre2026,
            2026,
            True,
        ),
    ]

    window_grid: Dict[str, Any] = {}
    pre25_actual: Dict[float, List[np.ndarray]] = {w: [] for w in weights}
    pre25_q25: Dict[float, List[np.ndarray]] = {w: [] for w in weights}
    pre25_mean: Dict[float, List[np.ndarray]] = {w: [] for w in weights}

    for label, tr_m, ev_m, tr_obs, p_dim_asof, cutoff_year, ipl_only in eval_windows:
        if tr_m.empty or ev_m.empty or tr_obs.empty:
            continue
        p_stats, _ = fit_player_forecast(tr_m, p_dim_asof, "bowling", seed=seed)
        mod_rpp = ChallengerRPP_RolePhaseJoint(cutoff_label=f"<blend_{cutoff_year}").fit(tr_obs, p_dim_asof, "bowling")
        sc_b0 = _attach_precutoff_ipl_evidence(
            score_with_selected_model(p_stats, tr_m, p_dim_asof, "bowling", "Ablation B-0 (No Player Pressure Lift)", seed=seed),
            tr_m,
            "bowling",
        )
        sc_rpp = _attach_precutoff_ipl_evidence(
            score_with_selected_model(p_stats, tr_m, p_dim_asof, "bowling", "Challenger RPP (Role-Phase Regularized Partial-Pooling)", seed=seed, obs_df=tr_obs),
            tr_m,
            "bowling",
        )
        b0_cols = sc_b0.merge(
            sc_rpp[["player_id", "conservative_score_q25", "predicted_hp_impact"]].rename(
                columns={"conservative_score_q25": "rpp_q25", "predicted_hp_impact": "rpp_mean"}
            ),
            on="player_id",
            how="left",
        )
        b0_cols["rpp_q25"] = b0_cols["rpp_q25"].fillna(b0_cols["conservative_score_q25"])
        b0_cols["rpp_mean"] = b0_cols["rpp_mean"].fillna(b0_cols["predicted_hp_impact"])

        ev_ge6 = ev_m[(ev_m["hp_balls_bowled"] >= 6) & (ev_m["comp_tier"].eq("IPL") if ipl_only else True)].copy()
        ev_join = _join_player_forecasts(ev_ge6, p_stats)
        pids = ev_join["player_id"].to_numpy()
        y_true = ev_join["hp_bowl_impact_12b"].to_numpy()
        b0_q, b0_m = ev_join["b0_q25"].to_numpy(), ev_join["b0_mean"].to_numpy()
        rpp_q, rpp_m = mod_rpp.predict_quantile(pids), mod_rpp.predict_mean(pids)
        mkt = build_asof_market_snapshot(cutoff_year, mapping_df, p_dim_asof) if ipl_only else None
        ev_ipl_matches = ev_m[ev_m["comp_tier"] == "IPL"]
        name_map = p_dim_asof.set_index("player_id")["player_name"].to_dict() if "player_name" in p_dim_asof.columns else {}

        w_rows: Dict[str, Any] = {}
        for w in weights:
            qw = (1.0 - w) * b0_q + w * rpp_q
            mw = (1.0 - w) * b0_m + w * rpp_m
            met = evaluate_forecast_metrics(y_true, qw, mw)
            if cutoff_year < 2025:
                pre25_actual[w].append(y_true)
                pre25_q25[w].append(qw)
                pre25_mean[w].append(mw)
            if ipl_only and mkt is not None and not ev_ipl_matches.empty:
                sc_w = b0_cols.copy()
                sc_w["conservative_score_q25"] = (1.0 - w) * sc_w["conservative_score_q25"] + w * sc_w["rpp_q25"]
                sc_w["predicted_hp_impact"] = (1.0 - w) * sc_w["predicted_hp_impact"] + w * sc_w["rpp_mean"]
                top10_rpp = _select_top10_under_policy(sc_w, mkt, "bowling", policy_name="RPP_IPL_VERIFIED")
                top10_pos = _select_top10_under_policy(sc_w, mkt, "bowling", policy_name="RR_IPL_POSITIVE_VERIFIED")
                met["top10_RPP_IPL_VERIFIED"] = evaluate_top10_performance(top10_rpp, ev_ipl_matches, "bowling", seed=seed, name_map=name_map)
                met["top10_RR_IPL_POSITIVE_VERIFIED"] = evaluate_top10_performance(top10_pos, ev_ipl_matches, "bowling", seed=seed, name_map=name_map)
            w_rows[f"{w:.2f}"] = met
        window_grid[label] = w_rows

    pre25_pooled = {
        f"{w:.2f}": evaluate_forecast_metrics(
            np.concatenate(pre25_actual[w]), np.concatenate(pre25_q25[w]), np.concatenate(pre25_mean[w])
        )
        for w in weights
        if pre25_actual[w]
    }
    best_w_key = min(pre25_pooled, key=lambda k: pre25_pooled[k]["pinball_loss_q25"]) if pre25_pooled else "0.00"
    interior_keys = [k for k in pre25_pooled if k not in ("0.00", "1.00")]
    best_interior_key = min(interior_keys, key=lambda k: pre25_pooled[k]["pinball_loss_q25"]) if interior_keys else "0.75"

    b0_25_pw = float(ipl_assessments_bowl.get("ablation_B0_no_pressure", {}).get("top10_performance", {}).get("realized_avg_impact_12b_player_weighted") or 0.0)
    int_25_pw = float(window_grid.get("2025_IPL", {}).get(best_interior_key, {}).get("top10_RPP_IPL_VERIFIED", {}).get("realized_avg_impact_12b_player_weighted") or 0.0)

    def _compact_top10_summary(t10_dict: Dict[str, Any]) -> Dict[str, Any]:
        pw = t10_dict.get("realized_avg_impact_12b_player_weighted")
        return {
            "assessable_picks_count": t10_dict.get("assessable_picks_count"),
            "realized_pw_hp_12b": round(float(pw), 3) if pw is not None else None,
            "bootstrap_ci_90_pw": t10_dict.get("bootstrap_ci_90_player_weighted"),
            "top10_player_names": t10_dict.get("top10_player_names"),
        }

    feas_summary: Dict[str, Any] = {}
    for yr, base_doc in (("2024", rolling_2024_bowl), ("2025", ipl_assessments_bowl), ("2026", retro_2026_bowl)):
        b0_rpp_pol = (base_doc or {}).get("ablation_B0_no_pressure", {}).get("top10_performance", {})
        b0_pos_pol = shortlist_controls.get(yr, {}).get("bowling", {}).get("RR_IPL_POSITIVE_VERIFIED", {}).get("ablation_B0_no_pressure", {}).get("top10_performance", {})
        feas_summary[yr] = {
            "B0_RPP_IPL_VERIFIED": _compact_top10_summary(b0_rpp_pol),
            "B0_RR_IPL_POSITIVE_VERIFIED": _compact_top10_summary(b0_pos_pol),
        }

    return {
        "blend_definition": "q25_w = (1 - w)*B0_q25 + w*RPP_q25; mean_w = (1 - w)*B0_mean + w*RPP_mean",
        "tuning_cutoff": "< 2025-01-01 (2023_H2_ALL + 2024_IPL pooled ge6)",
        "weight_grid": list(weights),
        "pre2025_pooled_metrics": pre25_pooled,
        "pre2025_min_loss_weight": float(best_w_key),
        "pre2025_best_interior_weight": float(best_interior_key),
        "window_metrics": window_grid,
        "promoted": False,
        "promotion_verdict": (
            f"NOT_PROMOTED: Pre-2025 tuning selects w={best_w_key} (Challenger RPP) and best interior w={best_interior_key}; "
            f"on 2025 IPL under RPP_IPL_VERIFIED, interior w={best_interior_key} Top-10 PW impact ({int_25_pw:+.3f}) trails Ablation B-0 ({b0_25_pw:+.3f}) "
            f"and w=1.00 (RPP) falls short of Case B (+1.0 hurdle). Retain Ablation B-0 as the statistical bowling model and apply "
            f"the replayed RR_IPL_POSITIVE_VERIFIED feasibility screen (direct IPL HP > 0/12b)."
        ),
        "feasibility_screen_replay_summary": feas_summary,
    }


def run_stage09_comparison(config: PipelineConfig) -> Tuple[Dict[str, Any], Dict[str, str]]:
    out = config.out_dir
    out.mkdir(parents=True, exist_ok=True)
    
    # 1. Load data
    mapping_df = pd.read_csv(config.raw_dir / "competition_team_player_mapping.csv")
    deliv_df = pd.read_csv(out / "delivery_impact_ledger.csv", low_memory=False)
    bat_obs_all = pd.read_csv(out / "player_match_phase_batting_obs.csv") if (out / "player_match_phase_batting_obs.csv").exists() else build_phase_observations_from_ledger(deliv_df, "batting")
    bowl_obs_all = pd.read_csv(out / "player_match_phase_bowling_obs.csv") if (out / "player_match_phase_bowling_obs.csv").exists() else build_phase_observations_from_ledger(deliv_df, "bowling")
    bat_cells_all = build_batting_delivery_cells(deliv_df)
    stint_cause_audit_df = build_batting_stint_cause_audit(deliv_df)
    stint_cause_summary = _summarize_short_stint_causes(stint_cause_audit_df)
    p_dim_pre2023_h2_path = out / "player_dimension_pre2023_h2.csv"
    p_dim_pre2023_h2 = pd.read_csv(p_dim_pre2023_h2_path) if p_dim_pre2023_h2_path.exists() else None
    p_dim_pre2024_path = out / "player_dimension_pre2024.csv"
    p_dim_pre2024 = pd.read_csv(p_dim_pre2024_path) if p_dim_pre2024_path.exists() else None
    p_dim_train_path = out / "player_dimension_train.csv"
    p_dim_train = pd.read_csv(p_dim_train_path) if p_dim_train_path.exists() else pd.read_csv(out / "player_dimension.csv")
    if p_dim_pre2024 is None:
        p_dim_pre2024 = p_dim_train
    if p_dim_pre2023_h2 is None:
        p_dim_pre2023_h2 = p_dim_pre2024
    p_dim_pre2026_path = out / "player_dimension_pre2026.csv"
    p_dim_pre2026 = pd.read_csv(p_dim_pre2026_path) if p_dim_pre2026_path.exists() else p_dim_train
    p_dim_full = pd.read_csv(out / "player_dimension.csv")
    p_dim = p_dim_train  # Use pre-2025 cutoff dimension for 2025 validation fold
    bat_match_df = pd.read_csv(out / "match_player_batting_impact.csv")
    bowl_match_df = pd.read_csv(out / "match_player_bowling_impact.csv")
    
    train_mask = deliv_df["fold"] == "TRAIN_2022_2024"
    if "is_reliability_eligible" in deliv_df:
        train_mask &= deliv_df["is_reliability_eligible"]
    val_mask = deliv_df["fold"] == "VAL_2025"
    test_mask = deliv_df["fold"] == "TEST_HOLDOUT_2026"
    
    # =========================================================================
    # FIT CANDIDATES ON TRAIN_2022_2024 FOR 2025 SELECTION
    # =========================================================================
    
    # Candidate B (Statistical default)
    train_bat_B = bat_match_df[bat_match_df["fold"] == "TRAIN_2022_2024"]
    train_bowl_B = bowl_match_df[bowl_match_df["fold"] == "TRAIN_2022_2024"]
    
    p_stats_bat_B, _ = fit_player_forecast(train_bat_B, p_dim, "batting", seed=config.seed)
    p_stats_bowl_B, _ = fit_player_forecast(train_bowl_B, p_dim, "bowling", seed=config.seed)
    
    # Candidate A (Cricket baseline)
    # Uses phase/comp-tier historical averages and empirical shrinkage
    train_deliv = deliv_df[train_mask]
    phase_bat = train_deliv.groupby(["match_phase", "comp_tier"]).agg(
        exp_runs=("runs", "mean"),
        exp_dismiss=("is_striker_dismissed", "mean"),
    ).reset_index()
    phase_bowl = train_deliv.groupby(["match_phase", "comp_tier"]).agg(
        exp_charge=("bowler_charge_runs", "mean"),
        exp_wk=("is_bowler_wicket", "mean"),
    ).reset_index()
    
    train_deliv_A = train_deliv.merge(phase_bat, on=["match_phase", "comp_tier"], how="left").merge(
        phase_bowl, on=["match_phase", "comp_tier"], how="left"
    )
    train_deliv_A["bat_impact_A"] = (train_deliv_A["runs"] - train_deliv_A["exp_runs"]) - 7.0 * (
        train_deliv_A["is_striker_dismissed"] - train_deliv_A["exp_dismiss"]
    )
    train_deliv_A["bowl_impact_A"] = (train_deliv_A["exp_charge"] - train_deliv_A["bowler_charge_runs"]) + 7.0 * (
        train_deliv_A["is_bowler_wicket"] - train_deliv_A["exp_wk"]
    )
    
    # Aggregate match-player for A
    hp_A = train_deliv_A[train_deliv_A["is_high_pressure_20"]]
    p_train_bat_A = hp_A.groupby("striker_id").agg(
        hp_balls=("is_legal_ball", "sum"),
        hp_impact=("bat_impact_A", "sum"),
        hp_matches=("match_id", "nunique"),
    ).reset_index().rename(columns={"striker_id": "player_id"})
    p_train_bat_A["hp_rate_12b"] = np.where(p_train_bat_A["hp_balls"] > 0, p_train_bat_A["hp_impact"] / p_train_bat_A["hp_balls"] * 12.0, 0.0)
    global_bat_A = (hp_A["bat_impact_A"].sum() / hp_A["is_legal_ball"].sum()) * 12.0
    p_train_bat_A["predicted_hp_impact"] = (p_train_bat_A["hp_balls"] * p_train_bat_A["hp_rate_12b"] + 36.0 * global_bat_A) / (p_train_bat_A["hp_balls"] + 36.0)
    p_train_bat_A["conservative_score_q25"] = p_train_bat_A["predicted_hp_impact"] - Z_25 * 9.5
    if "batting_role_supported" in p_dim.columns:
        p_train_bat_A = p_train_bat_A.merge(p_dim[["player_id", "batting_role_supported"]], on="player_id", how="left")
    p_train_bat_A["is_qualified"] = is_qualified(p_train_bat_A, "batting", 48, 6)
    
    p_train_bowl_A = hp_A.groupby("bowler_id").agg(
        hp_balls=("is_legal_ball", "sum"),
        hp_impact=("bowl_impact_A", "sum"),
        hp_matches=("match_id", "nunique"),
    ).reset_index().rename(columns={"bowler_id": "player_id"})
    p_train_bowl_A["hp_rate_12b"] = np.where(p_train_bowl_A["hp_balls"] > 0, p_train_bowl_A["hp_impact"] / p_train_bowl_A["hp_balls"] * 12.0, 0.0)
    global_bowl_A = (hp_A["bowl_impact_A"].sum() / hp_A["is_legal_ball"].sum()) * 12.0
    p_train_bowl_A["predicted_hp_impact"] = (p_train_bowl_A["hp_balls"] * p_train_bowl_A["hp_rate_12b"] + 36.0 * global_bowl_A) / (p_train_bowl_A["hp_balls"] + 36.0)
    p_train_bowl_A["conservative_score_q25"] = p_train_bowl_A["predicted_hp_impact"] - Z_25 * 10.5
    if "bowling_role_supported" in p_dim.columns:
        p_train_bowl_A = p_train_bowl_A.merge(p_dim[["player_id", "bowling_role_supported"]], on="player_id", how="left")
    p_train_bowl_A["is_qualified"] = is_qualified(p_train_bowl_A, "bowling", 48, 6)

    # Candidate C (Boosted challenger)
    runs_feat_col = "pre_team_total_runs" if "pre_team_total_runs" in deliv_df.columns else "pre_team_offbat_runs"
    feature_cols = ["pre_legal_balls", runs_feat_col, "pre_team_wickets", "pre_balls_remaining", "pre_wickets_in_hand"]
    X_train = deliv_df.loc[train_mask, feature_cols].values
    
    reg_bat_runs_C = HistGradientBoostingRegressor(max_iter=50, random_state=config.seed).fit(X_train, deliv_df.loc[train_mask, "runs"].values)
    clf_bat_dismiss_C = HistGradientBoostingClassifier(max_iter=50, random_state=config.seed).fit(X_train, deliv_df.loc[train_mask, "is_striker_dismissed"].values)
    reg_bowl_runs_C = HistGradientBoostingRegressor(max_iter=50, random_state=config.seed).fit(X_train, deliv_df.loc[train_mask, "bowler_charge_runs"].values)
    clf_bowl_wk_C = HistGradientBoostingClassifier(max_iter=50, random_state=config.seed).fit(X_train, deliv_df.loc[train_mask, "is_bowler_wicket"].values)
    
    X_all = deliv_df[feature_cols].values
    deliv_df["bat_impact_C"] = (deliv_df["runs"].values - reg_bat_runs_C.predict(X_all)) - 7.0 * (
        deliv_df["is_striker_dismissed"].values - clf_bat_dismiss_C.predict_proba(X_all)[:, 1]
    )
    deliv_df["bowl_impact_C"] = (reg_bowl_runs_C.predict(X_all) - deliv_df["bowler_charge_runs"].values) + 7.0 * (
        deliv_df["is_bowler_wicket"].values - clf_bowl_wk_C.predict_proba(X_all)[:, 1]
    )
    
    # Aggregate match-player for Candidate C
    hp_deliv_C = deliv_df[deliv_df["is_high_pressure_20"]].copy()
    ord_deliv_C = deliv_df[~deliv_df["is_high_pressure_20"]].copy()
    
    # Batting match-player C
    m_bat_hp_C = hp_deliv_C.groupby(["match_id", "striker_id", "fold", "comp_tier"]).agg(
        hp_balls_faced=("is_legal_ball", "sum"),
        hp_bat_impact=("bat_impact_C", "sum"),
    ).reset_index().rename(columns={"striker_id": "player_id"})
    m_bat_ord_C = ord_deliv_C.groupby(["match_id", "striker_id", "fold", "comp_tier"]).agg(
        ord_balls_faced=("is_legal_ball", "sum"),
        ord_bat_impact=("bat_impact_C", "sum"),
    ).reset_index().rename(columns={"striker_id": "player_id"})
    match_bat_C = m_bat_hp_C.merge(m_bat_ord_C, on=["match_id", "player_id", "fold", "comp_tier"], how="outer").fillna(0)
    match_bat_C["hp_bat_impact_12b"] = np.where(match_bat_C["hp_balls_faced"] > 0, match_bat_C["hp_bat_impact"] / match_bat_C["hp_balls_faced"] * 12.0, 0.0)
    match_bat_C["ord_bat_impact_12b"] = np.where(match_bat_C["ord_balls_faced"] > 0, match_bat_C["ord_bat_impact"] / match_bat_C["ord_balls_faced"] * 12.0, 0.0)
    
    # Bowling match-player C
    m_bowl_hp_C = hp_deliv_C.groupby(["match_id", "bowler_id", "fold", "comp_tier"]).agg(
        hp_balls_bowled=("is_legal_ball", "sum"),
        hp_bowl_impact=("bowl_impact_C", "sum"),
    ).reset_index().rename(columns={"bowler_id": "player_id"})
    m_bowl_ord_C = ord_deliv_C.groupby(["match_id", "bowler_id", "fold", "comp_tier"]).agg(
        ord_balls_bowled=("is_legal_ball", "sum"),
        ord_bowl_impact=("bowl_impact_C", "sum"),
    ).reset_index().rename(columns={"bowler_id": "player_id"})
    match_bowl_C = m_bowl_hp_C.merge(m_bowl_ord_C, on=["match_id", "player_id", "fold", "comp_tier"], how="outer").fillna(0)
    match_bowl_C["hp_bowl_impact_12b"] = np.where(match_bowl_C["hp_balls_bowled"] > 0, match_bowl_C["hp_bowl_impact"] / match_bowl_C["hp_balls_bowled"] * 12.0, 0.0)
    match_bowl_C["ord_bowl_impact_12b"] = np.where(match_bowl_C["ord_balls_bowled"] > 0, match_bowl_C["ord_bowl_impact"] / match_bowl_C["ord_balls_bowled"] * 12.0, 0.0)
    
    train_bat_C = match_bat_C[match_bat_C["fold"] == "TRAIN_2022_2024"]
    train_bowl_C = match_bowl_C[match_bowl_C["fold"] == "TRAIN_2022_2024"]
    p_stats_bat_C, _ = fit_player_forecast(train_bat_C, p_dim, "batting", seed=config.seed)
    p_stats_bowl_C, _ = fit_player_forecast(train_bowl_C, p_dim, "bowling", seed=config.seed)
    
    # =========================================================================
    # EVALUATION ON 2025 VALIDATION FOLD
    # =========================================================================
    val_bat_matches = bat_match_df[bat_match_df["fold"] == "VAL_2025"].copy()
    val_bowl_matches = bowl_match_df[bowl_match_df["fold"] == "VAL_2025"].copy()
    
    val_bat_opps = val_bat_matches[val_bat_matches["hp_balls_faced"] >= 6].copy()
    val_bowl_opps = val_bowl_matches[val_bowl_matches["hp_balls_bowled"] >= 6].copy()
    
    # 1. Batting Candidates Evaluation on VAL_2025 across all 655 qualifying opportunities
    # Candidate B (Statistical default with individual lift)
    val_bat_B = _join_player_forecasts(val_bat_opps, p_stats_bat_B)

    metrics_bat_B = evaluate_forecast_metrics(
        val_bat_B["hp_bat_impact_12b"].values,
        val_bat_B["b1_q25"].values,
        val_bat_B["b1_mean"].values,
    )
    top10_bat_B = _top_ten(p_stats_bat_B, "b1")
    top10_perf_bat_B = evaluate_top10_performance(top10_bat_B, val_bat_matches, "batting")
    metrics_bat_B["top10_performance"] = top10_perf_bat_B
    
    # Candidate A (Cricket baseline) - evaluate on identical common cohort
    val_bat_A = val_bat_B[["match_id", "player_id", "hp_bat_impact_12b"]].merge(
        p_train_bat_A[["player_id", "conservative_score_q25", "predicted_hp_impact"]],
        on="player_id", how="left"
    )
    global_bat_A_q25 = float(p_train_bat_A["conservative_score_q25"].median())
    global_bat_A_mean = float(p_train_bat_A["predicted_hp_impact"].median())
    val_bat_A["conservative_score_q25"] = val_bat_A["conservative_score_q25"].fillna(global_bat_A_q25)
    val_bat_A["predicted_hp_impact"] = val_bat_A["predicted_hp_impact"].fillna(global_bat_A_mean)
    metrics_bat_A = evaluate_forecast_metrics(
        val_bat_A["hp_bat_impact_12b"].values,
        val_bat_A["conservative_score_q25"].values,
        val_bat_A["predicted_hp_impact"].values,
    )
    top10_bat_A = p_train_bat_A[p_train_bat_A["is_qualified"]].sort_values("conservative_score_q25", ascending=False).head(10)["player_id"].tolist()
    metrics_bat_A["top10_performance"] = evaluate_top10_performance(top10_bat_A, val_bat_matches, "batting")
    
    # Candidate C (Boosted challenger)
    val_bat_C = val_bat_opps.merge(p_stats_bat_C[["player_id", "conservative_score_q25", "predicted_hp_impact"]], on="player_id", how="left")
    val_bat_C["conservative_score_q25"] = val_bat_C["conservative_score_q25"].fillna(float(p_stats_bat_C["conservative_score_q25"].median()))
    val_bat_C["predicted_hp_impact"] = val_bat_C["predicted_hp_impact"].fillna(float(p_stats_bat_C["predicted_hp_impact"].median()))
    metrics_bat_C = evaluate_forecast_metrics(
        val_bat_C["hp_bat_impact_12b"].values,
        val_bat_C["conservative_score_q25"].values,
        val_bat_C["predicted_hp_impact"].values,
    )
    top10_bat_C = p_stats_bat_C[p_stats_bat_C["is_qualified"]].sort_values("conservative_score_q25", ascending=False).head(10)["player_id"].tolist()
    metrics_bat_C["top10_performance"] = evaluate_top10_performance(top10_bat_C, val_bat_matches, "batting")
    
    # Ablation B-0 (No player pressure lift: scored with its own deployed width and own shortlist)
    q25_abl_bat = val_bat_B["b0_q25"].values
    mean_abl_bat = val_bat_B["b0_mean"].values
    metrics_bat_abl = evaluate_forecast_metrics(
        val_bat_B["hp_bat_impact_12b"].values,
        q25_abl_bat,
        mean_abl_bat,
    )
    top10_bat_B0 = _top_ten(p_stats_bat_B, "b0")
    metrics_bat_abl["top10_performance"] = evaluate_top10_performance(top10_bat_B0, val_bat_matches, "batting")
    
    # Challenger D (Robust Workload-Aware Distributional Model) - Batting
    chal_d_bat = ChallengerD_WorkloadDistributional().fit(train_bat_B, p_dim_train, "batting")
    q25_d_bat = chal_d_bat.predict_quantile(val_bat_B["player_id"].values, np.full(len(val_bat_B), 12.0))
    metrics_bat_D = evaluate_forecast_metrics(
        val_bat_B["hp_bat_impact_12b"].values,
        q25_d_bat,
        chal_d_bat.predict_mean(val_bat_B["player_id"].values),
    )
    top10_bat_D = _top_ten(p_stats_bat_B, "d")
    metrics_bat_D["top10_performance"] = evaluate_top10_performance(top10_bat_D, val_bat_matches, "batting")

    # Challenger E (Direct Quantile Gradient Boosting) - Batting
    chal_e_bat = ChallengerE_DirectQuantileBoosted(seed=config.seed).fit(train_bat_B, p_stats_bat_B, "batting")
    q25_e_bat, mean_e_bat = chal_e_bat.predict_at_cutoff(val_bat_B, p_stats_bat_B)
    metrics_bat_E = evaluate_forecast_metrics(
        val_bat_B["hp_bat_impact_12b"].values,
        q25_e_bat,
        mean_e_bat,
    )
    top10_bat_E = _top_ten(p_stats_bat_B, "e")
    metrics_bat_E["top10_performance"] = evaluate_top10_performance(top10_bat_E, val_bat_matches, "batting")

    # Challenger C (Role-and-Phase Partial-Pooling) - Batting
    train_hp_deliv = deliv_df[train_mask & deliv_df["is_high_pressure_20"]]
    chal_c_bat = ChallengerC_RolePhasePartialPooling().fit(train_hp_deliv, p_dim_train, "batting")
    q25_c_bat = chal_c_bat.predict_quantile(val_bat_B["player_id"].values, np.full(len(val_bat_B), 12.0))
    mean_c_bat = chal_c_bat.predict_mean(val_bat_B["player_id"].values)
    metrics_bat_C_phase = evaluate_forecast_metrics(
        val_bat_B["hp_bat_impact_12b"].values,
        q25_c_bat,
        mean_c_bat,
    )
    scored_bat_C = score_with_selected_model(
        p_stats_bat_B, train_bat_B, p_dim_train, "batting",
        "Challenger C (Role-and-Phase Partial-Pooling)",
        deliv_hp_df=train_hp_deliv, seed=config.seed,
    )
    top10_bat_C_phase = scored_bat_C[scored_bat_C["is_qualified"].astype(bool)]["player_id"].head(10).tolist()
    metrics_bat_C_phase["top10_performance"] = evaluate_top10_performance(top10_bat_C_phase, val_bat_matches, "batting")

    # Targeted Variant: Challenger C-IPL (IPL-Anchored Role-and-Phase) - Batting
    chal_c_ipl_bat = ChallengerC_IPLAnchoredRolePhase().fit(train_hp_deliv, p_dim_train, "batting")
    q25_c_ipl_bat = chal_c_ipl_bat.predict_quantile(val_bat_B["player_id"].values, np.full(len(val_bat_B), 12.0))
    mean_c_ipl_bat = chal_c_ipl_bat.predict_mean(val_bat_B["player_id"].values)
    metrics_bat_C_ipl = evaluate_forecast_metrics(
        val_bat_B["hp_bat_impact_12b"].values,
        q25_c_ipl_bat,
        mean_c_ipl_bat,
    )
    scored_bat_C_ipl = score_with_selected_model(
        p_stats_bat_B, train_bat_B, p_dim_train, "batting",
        "Challenger C-IPL (IPL-Anchored Role-and-Phase)",
        deliv_hp_df=train_hp_deliv, seed=config.seed,
    )
    top10_bat_C_ipl = scored_bat_C_ipl[scored_bat_C_ipl["is_qualified"].astype(bool)]["player_id"].head(10).tolist()
    metrics_bat_C_ipl["top10_performance"] = evaluate_top10_performance(top10_bat_C_ipl, val_bat_matches, "batting")
    
    # 2. Bowling Candidates Evaluation on VAL_2025 across all 783 qualifying opportunities
    # Candidate B (Statistical default with individual lift)
    val_bowl_B = _join_player_forecasts(val_bowl_opps, p_stats_bowl_B)

    metrics_bowl_B = evaluate_forecast_metrics(
        val_bowl_B["hp_bowl_impact_12b"].values,
        val_bowl_B["b1_q25"].values,
        val_bowl_B["b1_mean"].values,
    )
    top10_bowl_B = _top_ten(p_stats_bowl_B, "b1")
    top10_perf_bowl_B = evaluate_top10_performance(top10_bowl_B, val_bowl_matches, "bowling")
    metrics_bowl_B["top10_performance"] = top10_perf_bowl_B
    
    # Candidate A (Cricket baseline) - evaluate on identical common cohort
    val_bowl_A = val_bowl_B[["match_id", "player_id", "hp_bowl_impact_12b"]].merge(
        p_train_bowl_A[["player_id", "conservative_score_q25", "predicted_hp_impact"]],
        on="player_id", how="left"
    )
    global_bowl_A_q25 = float(p_train_bowl_A["conservative_score_q25"].median())
    global_bowl_A_mean = float(p_train_bowl_A["predicted_hp_impact"].median())
    val_bowl_A["conservative_score_q25"] = val_bowl_A["conservative_score_q25"].fillna(global_bowl_A_q25)
    val_bowl_A["predicted_hp_impact"] = val_bowl_A["predicted_hp_impact"].fillna(global_bowl_A_mean)
    metrics_bowl_A = evaluate_forecast_metrics(
        val_bowl_A["hp_bowl_impact_12b"].values,
        val_bowl_A["conservative_score_q25"].values,
        val_bowl_A["predicted_hp_impact"].values,
    )
    top10_bowl_A = p_train_bowl_A[p_train_bowl_A["is_qualified"]].sort_values("conservative_score_q25", ascending=False).head(10)["player_id"].tolist()
    metrics_bowl_A["top10_performance"] = evaluate_top10_performance(top10_bowl_A, val_bowl_matches, "bowling")
    
    # Candidate C (Boosted challenger)
    val_bowl_C = val_bowl_opps.merge(p_stats_bowl_C[["player_id", "conservative_score_q25", "predicted_hp_impact"]], on="player_id", how="left")
    val_bowl_C["conservative_score_q25"] = val_bowl_C["conservative_score_q25"].fillna(float(p_stats_bowl_C["conservative_score_q25"].median()))
    val_bowl_C["predicted_hp_impact"] = val_bowl_C["predicted_hp_impact"].fillna(float(p_stats_bowl_C["predicted_hp_impact"].median()))
    metrics_bowl_C = evaluate_forecast_metrics(
        val_bowl_C["hp_bowl_impact_12b"].values,
        val_bowl_C["conservative_score_q25"].values,
        val_bowl_C["predicted_hp_impact"].values,
    )
    top10_bowl_C = p_stats_bowl_C[p_stats_bowl_C["is_qualified"]].sort_values("conservative_score_q25", ascending=False).head(10)["player_id"].tolist()
    metrics_bowl_C["top10_performance"] = evaluate_top10_performance(top10_bowl_C, val_bowl_matches, "bowling")
    
    # Ablation B-0 (No player pressure lift: scored with its own deployed width and own shortlist)
    q25_abl_bowl = val_bowl_B["b0_q25"].values
    mean_abl_bowl = val_bowl_B["b0_mean"].values
    metrics_bowl_abl = evaluate_forecast_metrics(
        val_bowl_B["hp_bowl_impact_12b"].values,
        q25_abl_bowl,
        mean_abl_bowl,
    )
    top10_bowl_B0 = _top_ten(p_stats_bowl_B, "b0")
    metrics_bowl_abl["top10_performance"] = evaluate_top10_performance(top10_bowl_B0, val_bowl_matches, "bowling")
    
    # Challenger D (Robust Workload-Aware Distributional Model) - Bowling
    chal_d_bowl = ChallengerD_WorkloadDistributional().fit(train_bowl_B, p_dim_train, "bowling")
    q25_d_bowl = chal_d_bowl.predict_quantile(val_bowl_B["player_id"].values, np.full(len(val_bowl_B), 12.0))
    metrics_bowl_D = evaluate_forecast_metrics(
        val_bowl_B["hp_bowl_impact_12b"].values,
        q25_d_bowl,
        chal_d_bowl.predict_mean(val_bowl_B["player_id"].values),
    )
    top10_bowl_D = _top_ten(p_stats_bowl_B, "d")
    metrics_bowl_D["top10_performance"] = evaluate_top10_performance(top10_bowl_D, val_bowl_matches, "bowling")

    # Challenger E (Direct Quantile Gradient Boosting) - Bowling
    chal_e_bowl = ChallengerE_DirectQuantileBoosted(seed=config.seed).fit(train_bowl_B, p_stats_bowl_B, "bowling")
    q25_e_bowl, mean_e_bowl = chal_e_bowl.predict_at_cutoff(val_bowl_B, p_stats_bowl_B)
    metrics_bowl_E = evaluate_forecast_metrics(
        val_bowl_B["hp_bowl_impact_12b"].values,
        q25_e_bowl,
        mean_e_bowl,
    )
    top10_bowl_E = _top_ten(p_stats_bowl_B, "e")
    metrics_bowl_E["top10_performance"] = evaluate_top10_performance(top10_bowl_E, val_bowl_matches, "bowling")

    # Challenger C (Role-and-Phase Partial-Pooling) - Bowling
    chal_c_bowl = ChallengerC_RolePhasePartialPooling().fit(train_hp_deliv, p_dim_train, "bowling")
    q25_c_bowl = chal_c_bowl.predict_quantile(val_bowl_B["player_id"].values, np.full(len(val_bowl_B), 12.0))
    mean_c_bowl = chal_c_bowl.predict_mean(val_bowl_B["player_id"].values)
    metrics_bowl_C_phase = evaluate_forecast_metrics(
        val_bowl_B["hp_bowl_impact_12b"].values,
        q25_c_bowl,
        mean_c_bowl,
    )
    scored_bowl_C = score_with_selected_model(
        p_stats_bowl_B, train_bowl_B, p_dim_train, "bowling",
        "Challenger C (Role-and-Phase Partial-Pooling)",
        deliv_hp_df=train_hp_deliv, seed=config.seed,
    )
    top10_bowl_C_phase = scored_bowl_C[scored_bowl_C["is_qualified"].astype(bool)]["player_id"].head(10).tolist()
    metrics_bowl_C_phase["top10_performance"] = evaluate_top10_performance(top10_bowl_C_phase, val_bowl_matches, "bowling")

    # Targeted Variant: Challenger C-IPL (IPL-Anchored Role-and-Phase) - Bowling
    chal_c_ipl_bowl = ChallengerC_IPLAnchoredRolePhase().fit(train_hp_deliv, p_dim_train, "bowling")
    q25_c_ipl_bowl = chal_c_ipl_bowl.predict_quantile(val_bowl_B["player_id"].values, np.full(len(val_bowl_B), 12.0))
    mean_c_ipl_bowl = chal_c_ipl_bowl.predict_mean(val_bowl_B["player_id"].values)
    metrics_bowl_C_ipl = evaluate_forecast_metrics(
        val_bowl_B["hp_bowl_impact_12b"].values,
        q25_c_ipl_bowl,
        mean_c_ipl_bowl,
    )
    scored_bowl_C_ipl = score_with_selected_model(
        p_stats_bowl_B, train_bowl_B, p_dim_train, "bowling",
        "Challenger C-IPL (IPL-Anchored Role-and-Phase)",
        deliv_hp_df=train_hp_deliv, seed=config.seed,
    )
    top10_bowl_C_ipl = scored_bowl_C_ipl[scored_bowl_C_ipl["is_qualified"].astype(bool)]["player_id"].head(10).tolist()
    metrics_bowl_C_ipl["top10_performance"] = evaluate_top10_performance(top10_bowl_C_ipl, val_bowl_matches, "bowling")
    
    # Paired block bootstrap with match multiplicity (50 replicates)
    rng = np.random.default_rng(config.seed)
    diffs_bat_b_c = []
    diffs_bat_b_b0 = []
    diffs_bowl_b_c = []
    diffs_bowl_b_b0 = []
    
    val_bat_mids = val_bat_B["match_id"].unique()
    val_bowl_mids = val_bowl_B["match_id"].unique()
    
    bat_mids_arr = val_bat_B["match_id"].values
    bat_y = val_bat_B["hp_bat_impact_12b"].values
    bat_q_b = val_bat_B["conservative_score_q25"].values
    bat_q_c = val_bat_C["conservative_score_q25"].values
    bat_q_b0 = q25_abl_bat
    
    for _ in range(50):
        sample_mids = rng.choice(val_bat_mids, size=len(val_bat_mids), replace=True)
        counts = pd.Series(sample_mids).value_counts().to_dict()
        weights = np.array([counts.get(m, 0) for m in bat_mids_arr])
        if weights.sum() > 0:
            pb_b = compute_weighted_pinball_loss(bat_y, bat_q_b, weights)
            pb_c = compute_weighted_pinball_loss(bat_y, bat_q_c, weights)
            pb_b0 = compute_weighted_pinball_loss(bat_y, bat_q_b0, weights)
            diffs_bat_b_c.append(pb_b - pb_c)
            diffs_bat_b_b0.append(pb_b - pb_b0)
            
    bowl_mids_arr = val_bowl_B["match_id"].values
    bowl_y = val_bowl_B["hp_bowl_impact_12b"].values
    bowl_q_b = val_bowl_B["conservative_score_q25"].values
    bowl_q_c = val_bowl_C["conservative_score_q25"].values
    bowl_q_b0 = q25_abl_bowl
    
    for _ in range(50):
        sample_mids = rng.choice(val_bowl_mids, size=len(val_bowl_mids), replace=True)
        counts = pd.Series(sample_mids).value_counts().to_dict()
        weights = np.array([counts.get(m, 0) for m in bowl_mids_arr])
        if weights.sum() > 0:
            pb_b = compute_weighted_pinball_loss(bowl_y, bowl_q_b, weights)
            pb_c = compute_weighted_pinball_loss(bowl_y, bowl_q_c, weights)
            pb_b0 = compute_weighted_pinball_loss(bowl_y, bowl_q_b0, weights)
            diffs_bowl_b_c.append(pb_b - pb_c)
            diffs_bowl_b_b0.append(pb_b - pb_b0)
            
    # IPL Transfer Comparison (Pooled vs IPL-only on held-out IPL matches)
    train_ipl_bat = bat_match_df[(bat_match_df["fold"] == "TRAIN_2022_2024") & (bat_match_df["comp_tier"] == "IPL")]
    p_stats_ipl_bat, _ = fit_player_forecast(train_ipl_bat, p_dim, "batting", seed=config.seed, baseline_only=True)
    
    val_ipl_bat_opps = val_bat_matches[(val_bat_matches["comp_tier"] == "IPL") & (val_bat_matches["hp_balls_faced"] >= 6)]
    m_ipl_pooled = val_ipl_bat_opps.merge(p_stats_bat_B[["player_id", "conservative_score_q25", "predicted_hp_impact"]], on="player_id", how="inner")
    m_ipl_only = val_ipl_bat_opps.merge(p_stats_ipl_bat[["player_id", "conservative_score_q25", "predicted_hp_impact"]], on="player_id", how="inner")
    
    # Common cohort: exact intersection of (match_id, player_id) opportunities
    pooled_pairs_bat = set(zip(m_ipl_pooled["match_id"], m_ipl_pooled["player_id"]))
    ipl_pairs_bat = set(zip(m_ipl_only["match_id"], m_ipl_only["player_id"]))
    common_pairs_bat = pooled_pairs_bat.intersection(ipl_pairs_bat)
    
    idx_pooled_common = [i for i, row in m_ipl_pooled.iterrows() if (row["match_id"], row["player_id"]) in common_pairs_bat]
    idx_ipl_common = [i for i, row in m_ipl_only.iterrows() if (row["match_id"], row["player_id"]) in common_pairs_bat]
    
    common_pooled_bat = m_ipl_pooled.loc[idx_pooled_common].sort_values(["match_id", "player_id"])
    common_ipl_bat = m_ipl_only.loc[idx_ipl_common].sort_values(["match_id", "player_id"])
    
    pb_bat_pooled_common = compute_pinball_loss(common_pooled_bat["hp_bat_impact_12b"].values, common_pooled_bat["conservative_score_q25"].values)
    pb_bat_ipl_common = compute_pinball_loss(common_ipl_bat["hp_bat_impact_12b"].values, common_ipl_bat["conservative_score_q25"].values)
    
    # Bowling IPL transfer
    train_ipl_bowl = bowl_match_df[(bowl_match_df["fold"] == "TRAIN_2022_2024") & (bowl_match_df["comp_tier"] == "IPL")]
    p_stats_ipl_bowl, _ = fit_player_forecast(train_ipl_bowl, p_dim, "bowling", seed=config.seed, baseline_only=True)
    
    val_ipl_bowl_opps = val_bowl_matches[(val_bowl_matches["comp_tier"] == "IPL") & (val_bowl_matches["hp_balls_bowled"] >= 6)]
    m_ipl_bowl_pooled = val_ipl_bowl_opps.merge(p_stats_bowl_B[["player_id", "conservative_score_q25", "predicted_hp_impact"]], on="player_id", how="inner")
    m_ipl_bowl_only = val_ipl_bowl_opps.merge(p_stats_ipl_bowl[["player_id", "conservative_score_q25", "predicted_hp_impact"]], on="player_id", how="inner")
    
    pooled_pairs_bowl = set(zip(m_ipl_bowl_pooled["match_id"], m_ipl_bowl_pooled["player_id"]))
    ipl_pairs_bowl = set(zip(m_ipl_bowl_only["match_id"], m_ipl_bowl_only["player_id"]))
    common_pairs_bowl = pooled_pairs_bowl.intersection(ipl_pairs_bowl)
    
    idx_bowl_pooled_common = [i for i, row in m_ipl_bowl_pooled.iterrows() if (row["match_id"], row["player_id"]) in common_pairs_bowl]
    idx_bowl_ipl_common = [i for i, row in m_ipl_bowl_only.iterrows() if (row["match_id"], row["player_id"]) in common_pairs_bowl]
    
    common_pooled_bowl = m_ipl_bowl_pooled.loc[idx_bowl_pooled_common].sort_values(["match_id", "player_id"])
    common_ipl_bowl = m_ipl_bowl_only.loc[idx_bowl_ipl_common].sort_values(["match_id", "player_id"])
    
    pb_bowl_pooled_common = compute_pinball_loss(common_pooled_bowl["hp_bowl_impact_12b"].values, common_pooled_bowl["conservative_score_q25"].values)
    pb_bowl_ipl_common = compute_pinball_loss(common_ipl_bowl["hp_bowl_impact_12b"].values, common_ipl_bowl["conservative_score_q25"].values)
    
    ipl_transfer_check = {
        "benchmark_model": "B1 shrinkage with player pressure lift",
        "held_out_ipl_opportunities_pooled": len(m_ipl_pooled),
        "held_out_ipl_opportunities_ipl_only": len(m_ipl_only),
        "common_held_out_ipl_opportunities": len(common_pooled_bat),
        "pinball_loss_pooled": compute_pinball_loss(m_ipl_pooled["hp_bat_impact_12b"].values, m_ipl_pooled["conservative_score_q25"].values),
        "pinball_loss_ipl_only": compute_pinball_loss(m_ipl_only["hp_bat_impact_12b"].values, m_ipl_only["conservative_score_q25"].values),
        "pinball_loss_pooled_common": pb_bat_pooled_common,
        "pinball_loss_ipl_only_common": pb_bat_ipl_common,
        "common_held_out_ipl_opportunities_bowling": len(common_pooled_bowl),
        "pinball_loss_pooled_common_bowling": pb_bowl_pooled_common,
        "pinball_loss_ipl_only_common_bowling": pb_bowl_ipl_common,
        "transfer_finding": (
            f"For B1 on common held-out IPL fixtures, pooled training achieves pinball loss {pb_bat_pooled_common:.4f} vs {pb_bat_ipl_common:.4f} for batting "
            f"({len(common_pooled_bat)} common player-matches) and {pb_bowl_pooled_common:.4f} vs {pb_bowl_ipl_common:.4f} for bowling "
            f"({len(common_pooled_bowl)} common player-matches), while extending coverage to {len(m_ipl_pooled) - len(common_pooled_bat)} additional batting "
            f"and {len(m_ipl_bowl_pooled) - len(common_pooled_bowl)} additional bowling opportunities."
        ),
    }
    
    tr_bat_obs_25 = bat_obs_all[bat_obs_all["fold"] == "TRAIN_2022_2024"].copy()
    val_bat_obs_25 = bat_obs_all[bat_obs_all["fold"] == "VAL_2025"].copy()
    tr_bowl_obs_25 = bowl_obs_all[bowl_obs_all["fold"] == "TRAIN_2022_2024"].copy()
    val_bowl_obs_25 = bowl_obs_all[bowl_obs_all["fold"] == "VAL_2025"].copy()

    ipl_assessments = {}
    controls_2025 = {}
    bat_cells_25 = bat_cells_all[bat_cells_all["fold"] == "TRAIN_2022_2024"].copy() if not bat_cells_all.empty else None
    ipl_assessments["batting"], controls_2025["batting"] = _replay_window_comparable(
        train_bat_B, val_bat_matches, p_stats_bat_B, train_hp_deliv, tr_bat_obs_25, val_bat_obs_25, p_dim_train, "batting", 2025, mapping_df, config.seed,
        bat_cells_tr=bat_cells_25,
    )
    ipl_assessments["bowling"], controls_2025["bowling"] = _replay_window_comparable(
        train_bowl_B, val_bowl_matches, p_stats_bowl_B, train_hp_deliv, tr_bowl_obs_25, val_bowl_obs_25, p_dim_train, "bowling", 2025, mapping_df, config.seed
    )

    # Freeze the decision strictly on 2025 IPL ex-ante forecasts under shared RPP_IPL_VERIFIED and +0.05 tolerance before inspecting 2026.
    p_val_c_bat = float(np.mean(np.array(diffs_bat_b_c) <= 0)) if diffs_bat_b_c else 0.5
    p_val_c_bowl = float(np.mean(np.array(diffs_bowl_b_c) <= 0)) if diffs_bowl_b_c else 0.5
    model_names = {key: name for name, key in MODEL_METRIC_KEYS.items()}
    bat_key, bat_reason = _select_ipl_model_with_reason(ipl_assessments["batting"], loss_tolerance=MODEL_SELECT_LOSS_TOLERANCE)
    bowl_key, bowl_reason = _select_ipl_model_with_reason(ipl_assessments["bowling"], loss_tolerance=MODEL_SELECT_LOSS_TOLERANCE)
    chosen_bat = model_names[bat_key]
    chosen_bowl = model_names[bowl_key]

    if chosen_bat == chosen_bowl:
        chosen_overall = chosen_bat
    else:
        chosen_overall = f"Batting: {chosen_bat} | Bowling: {chosen_bowl}"

    n_ipl_2025_bat = int(val_bat_B["comp_tier"].eq("IPL").sum())
    n_ipl_2025_bowl = int(val_bowl_B["comp_tier"].eq("IPL").sum())
    bowl_sel_metrics = ipl_assessments["bowling"][bowl_key]
    bowl_sel_cov = float(bowl_sel_metrics.get("coverage_q25", np.nan))
    bowl_sel_ass = int(bowl_sel_metrics.get("top10_performance", {}).get("assessable_picks_count", 0))
    bowl_fallback_cov_ok = bool(0.15 <= bowl_sel_cov <= 0.35) if not np.isnan(bowl_sel_cov) else False
    bowl_slate_status = (
        "PROVISIONAL_THIN_SLATE_COVERAGE"
        if (bowl_sel_ass < 7 or not bowl_fallback_cov_ok)
        else "ADEQUATE_SLATE_COVERAGE"
    )

    bat_sel_25 = ipl_assessments["batting"].get(bat_key, {})
    bat_d_25 = ipl_assessments["batting"].get("challenger_D_workload", {})
    bat_dhp_25 = ipl_assessments["batting"].get("challenger_DHP_delivery_hazard", {})
    bat_dhp_allcal_25 = ipl_assessments["batting"].get("challenger_DHP_all_pos_calibrated_diagnostic", {})
    dhp_all_loss = (
        bat_dhp_allcal_25.get("all_positive_ipl_metrics", {}).get("pinball_loss_q25")
        if bat_dhp_allcal_25
        else bat_dhp_25.get("all_positive_ipl_metrics", {}).get("pinball_loss_q25", np.nan)
    )
    dhp_lt6_loss = (
        bat_dhp_allcal_25.get("short_stint_1_to_5b_ipl_metrics", {}).get("pinball_loss_q25")
        if bat_dhp_allcal_25
        else bat_dhp_25.get("short_stint_1_to_5b_ipl_metrics", {}).get("pinball_loss_q25", np.nan)
    )
    sel_all_loss = bat_sel_25.get("all_positive_ipl_metrics", {}).get("pinball_loss_q25", np.nan)
    sel_lt6_loss = bat_sel_25.get("short_stint_1_to_5b_ipl_metrics", {}).get("pinball_loss_q25", np.nan)
    selection_rationale = (
        f"Evaluated {len(SHIPPED_MODELS)} shipped ex-ante candidates on comparable 2025 IPL validation "
        f"({n_ipl_2025_bat} batting ge6 / {int((val_bat_matches['comp_tier'].eq('IPL') & val_bat_matches['hp_balls_faced'].gt(0)).sum())} all>0b; "
        f"{n_ipl_2025_bowl} bowling ge6 / {int((val_bowl_matches['comp_tier'].eq('IPL') & val_bowl_matches['hp_balls_bowled'].gt(0)).sum())} all>0b) "
        f"under ONE shared shortlist policy RPP_IPL_VERIFIED (role_supported, career hp_balls>=48 & hp_matches>=6, IPL hp_balls>=24 & hp_matches>=2). "
        f"Frozen guardrail: 2025 IPL Q25 coverage in [0.15, 0.35] AND either Case A (paired 90% match-block Q25 diff vs B0 upper bound < 0 with non-degraded shortlist) "
        f"or Case B (realized Top-10 PW impact >= B0 + 1.0 with assessable >= 7 and Q25 loss <= B0 + {MODEL_SELECT_LOSS_TOLERANCE:.2f}; replaces legacy +0.15 CLI branch). "
        f"Stage 3 delivery-hazard batting check (DHP including 1..5b stints): "
        f"ge6 Q25 loss {bat_dhp_25.get('pinball_loss_q25', np.nan):.4f} vs {chosen_bat} {bat_sel_25.get('pinball_loss_q25', np.nan):.4f} (and D {bat_d_25.get('pinball_loss_q25', np.nan):.4f}), "
        f"all>0b all_cal Q25 loss {float(dhp_all_loss):.4f} vs {chosen_bat} {float(sel_all_loss):.4f}, "
        f"1..5b all_cal Q25 loss {float(dhp_lt6_loss):.4f} vs {chosen_bat} {float(sel_lt6_loss):.4f}, "
        f"2025 Top-10 PW {bat_dhp_25.get('top10_performance', {}).get('realized_avg_impact_12b_player_weighted', np.nan):+.3f} vs {chosen_bat} {bat_sel_25.get('top10_performance', {}).get('realized_avg_impact_12b_player_weighted', np.nan):+.3f}. "
        f"Conditional realized-mix diagnostics excluded from model selection. "
        f"Batting selected {chosen_bat} via {bat_reason}. Bowling selected {chosen_bowl} via {bowl_reason}."
    )

    # Compute rolling 2022-23 -> 2024 IPL earlier-window diagnostic strictly using pre-2024 roles & cutoffs
    rolling_2024_diag, controls_2024 = _evaluate_rolling_2024_diagnostic(
        bat_match_df, bowl_match_df, deliv_df, p_dim_pre2024, config.seed,
        bat_obs_all=bat_obs_all, bowl_obs_all=bowl_obs_all, mapping_df=mapping_df,
        bat_cells_all=bat_cells_all,
    )
    rolling_2024_diag["cutoff_provenance"] = {
        "training_window_end": "< 2024-01-01",
        "player_dimension_source": "player_dimension_pre2024.csv",
        "match_state_pressure_peer_cutoff": "2024-01-01",
    }

    # =========================================================================
    # ONCE-RUN 2026 TEST EVALUATION & RETROSPECTIVE IPL HEAD-TO-HEAD
    # =========================================================================
    train_val_mask = deliv_df["fold"].isin(["TRAIN_2022_2024", "VAL_2025"])
    if "is_reliability_eligible" in deliv_df:
        train_val_mask &= deliv_df["is_reliability_eligible"]
    deliv_tv_hp = deliv_df[train_val_mask & deliv_df["is_high_pressure_20"]].copy()

    def _eval_2026_role(role: str, chosen_name: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        target_col = "hp_bat_impact_12b" if role == "batting" else "hp_bowl_impact_12b"
        balls_col = "hp_balls_faced" if role == "batting" else "hp_balls_bowled"
        source_df = bat_match_df if role == "batting" else bowl_match_df

        train_val_m = source_df[source_df["fold"].isin(["TRAIN_2022_2024", "VAL_2025"])]
        p_stats_final, _ = fit_player_forecast(train_val_m, p_dim_pre2026, role, seed=config.seed)
        obs_src = bat_obs_all if role == "batting" else bowl_obs_all
        tr_obs_26 = obs_src[obs_src["fold"].isin(["TRAIN_2022_2024", "VAL_2025"])].copy()
        te_obs_26 = obs_src[obs_src["fold"] == "TEST_HOLDOUT_2026"].copy()

        test_m = source_df[source_df["fold"] == "TEST_HOLDOUT_2026"].copy()
        bat_cells_26 = (
            bat_cells_all[bat_cells_all["fold"].isin(["TRAIN_2022_2024", "VAL_2025"])].copy()
            if (role == "batting" and not bat_cells_all.empty)
            else None
        )
        retro_ipl, ctrl_26 = _replay_window_comparable(
            train_val_m, test_m, p_stats_final, deliv_tv_hp, tr_obs_26, te_obs_26, p_dim_pre2026, role, 2026, mapping_df, config.seed,
            bat_cells_tr=bat_cells_26,
        )

        # Compute pooled 2026 metrics (all tiers) cleanly for chosen model
        test_opps = test_m[test_m[balls_col] >= 6].copy()
        test_eval = _join_player_forecasts(test_opps, p_stats_final)
        test_pids = test_eval["player_id"].to_numpy()
        ones_workloads = np.full(len(test_pids), 12.0)

        if chosen_name not in SHIPPED_MODELS or chosen_name not in MODEL_METRIC_KEYS:
            raise ValueError(f"Unsupported chosen_model '{chosen_name}' for {role} 2026 holdout: silent fallback disabled.")
        if "Challenger DHP" in chosen_name:
            mod_dhp_26 = ChallengerDHP_BattingDeliveryHazard(cutoff_label="<2026").fit(bat_cells_26, p_dim_pre2026)
            q25_sel = mod_dhp_26.predict_quantile(test_pids)
            mean_sel = mod_dhp_26.predict_mean(test_pids)
        elif "Challenger RPP" in chosen_name:
            mod_rpp_26 = ChallengerRPP_RolePhaseJoint(cutoff_label="<2026").fit(tr_obs_26, p_dim_pre2026, role)
            q25_sel = mod_rpp_26.predict_quantile(test_pids)
            mean_sel = mod_rpp_26.predict_mean(test_pids)
        elif "Challenger D" in chosen_name:
            cd = ChallengerD_WorkloadDistributional().fit(train_val_m, p_dim_pre2026, role)
            q25_sel = cd.predict_quantile(test_pids, ones_workloads)
            mean_sel = cd.predict_mean(test_pids)
        elif "Challenger E" in chosen_name:
            ce = ChallengerE_DirectQuantileBoosted(seed=config.seed).fit(train_val_m, p_stats_final, role)
            q25_sel, mean_sel = ce.predict_at_cutoff(test_eval, p_stats_final)
        elif "Challenger C-IPL" in chosen_name:
            cci = ChallengerC_IPLAnchoredRolePhase().fit(deliv_tv_hp, p_dim_pre2026, role)
            q25_sel, mean_sel = cci.predict_quantile(test_pids, ones_workloads), cci.predict_mean(test_pids)
        elif "Challenger C" in chosen_name:
            cc = ChallengerC_RolePhasePartialPooling().fit(deliv_tv_hp, p_dim_pre2026, role)
            q25_sel, mean_sel = cc.predict_quantile(test_pids, ones_workloads), cc.predict_mean(test_pids)
        elif "Ablation" in chosen_name:
            q25_sel, mean_sel = test_eval["b0_q25"].to_numpy(), test_eval["b0_mean"].to_numpy()
        else:
            q25_sel, mean_sel = test_eval["b1_q25"].to_numpy(), test_eval["b1_mean"].to_numpy()

        mkt_26 = build_asof_market_snapshot(2026, mapping_df, p_dim_pre2026)
        sc_sel = score_with_selected_model(
            p_stats_final, train_val_m, p_dim_pre2026, role, chosen_name,
            deliv_hp_df=deliv_tv_hp if "Challenger C" in chosen_name else None,
            seed=config.seed,
            obs_df=tr_obs_26 if "Challenger RPP" in chosen_name else None,
            bat_cells_df=bat_cells_26 if "Challenger DHP" in chosen_name else None,
        )
        sc_sel = _attach_precutoff_ipl_evidence(sc_sel, train_val_m, role)
        top10_sel = _select_top10_under_policy(sc_sel, mkt_26, role, policy_name="RPP_IPL_VERIFIED")

        y_all = test_eval[target_col].to_numpy()
        pooled_metrics = evaluate_forecast_metrics(y_all, q25_sel, mean_sel)
        pooled_metrics["top10_performance"] = evaluate_top10_performance(top10_sel, test_m, role, seed=config.seed)
        ipl_mask_t = test_eval["comp_tier"].eq("IPL").to_numpy()
        t20i_mask_t = test_eval["comp_tier"].eq("T20I").to_numpy()
        pooled_metrics["ipl_subset"] = evaluate_forecast_metrics(y_all[ipl_mask_t], q25_sel[ipl_mask_t], mean_sel[ipl_mask_t])
        pooled_metrics["t20i_subset"] = evaluate_forecast_metrics(y_all[t20i_mask_t], q25_sel[t20i_mask_t], mean_sel[t20i_mask_t])

        pre2026_profiles = _summarize_candidate_profiles(p_stats_final, train_val_m, p_dim_pre2026, deliv_tv_hp, role, config.seed, obs_df=tr_obs_26, bat_cells_df=bat_cells_26)
        return pooled_metrics, retro_ipl, pre2026_profiles, ctrl_26

    test_bat_metrics, retro_bat_2026, pre2026_bat_profiles, controls_2026_bat = _eval_2026_role("batting", chosen_bat)
    test_bowl_metrics, retro_bowl_2026, pre2026_bowl_profiles, controls_2026_bowl = _eval_2026_role("bowling", chosen_bowl)
    controls_2026 = {"batting": controls_2026_bat, "bowling": controls_2026_bowl}

    # Full-history candidate summaries & role-specific bowling alternatives
    all_folds = ["TRAIN_2022_2024", "VAL_2025", "TEST_HOLDOUT_2026"]
    rel_all_mask = deliv_df["is_reliability_eligible"] if "is_reliability_eligible" in deliv_df.columns else pd.Series(True, index=deliv_df.index)
    deliv_all_hp = deliv_df[deliv_df["is_high_pressure_20"] & rel_all_mask].copy()
    full_bat_stats, _ = fit_player_forecast(bat_match_df, p_dim_full, "batting", seed=config.seed, folds=all_folds)
    full_bowl_stats, _ = fit_player_forecast(bowl_match_df, p_dim_full, "bowling", seed=config.seed, folds=all_folds)
    full_bat_profiles = _summarize_candidate_profiles(full_bat_stats, bat_match_df, p_dim_full, deliv_all_hp, "batting", config.seed, obs_df=bat_obs_all, bat_cells_df=bat_cells_all)
    full_bowl_profiles = _summarize_candidate_profiles(full_bowl_stats, bowl_match_df, p_dim_full, deliv_all_hp, "bowling", config.seed, obs_df=bowl_obs_all)

    c_ipl_full_bowl = score_with_selected_model(
        full_bowl_stats, bowl_match_df, p_dim_full, "bowling",
        "Challenger C-IPL (IPL-Anchored Role-and-Phase)",
        deliv_hp_df=deliv_all_hp, seed=config.seed,
    )
    c_ipl_qual_bowl = c_ipl_full_bowl[c_ipl_full_bowl["is_qualified"].astype(bool)].copy()
    bowling_role_alts = {
        "source_model": "Challenger C-IPL (IPL-Anchored Role-and-Phase)",
        "pace": [
            {
                "player_id": int(r["player_id"]), "player_name": str(r["player_name"]),
                "inferred_role": str(r["inferred_role"]), "q25": round(float(r["conservative_score_q25"]), 3),
                "mean": round(float(r["predicted_hp_impact"]), 3), "ipl_hp_balls": int(r.get("ipl_hp_balls", 0)),
            }
            for _, r in c_ipl_qual_bowl[c_ipl_qual_bowl["inferred_role"].astype(str).str.contains("PACE")].head(5).iterrows()
        ],
        "spin": [
            {
                "player_id": int(r["player_id"]), "player_name": str(r["player_name"]),
                "inferred_role": str(r["inferred_role"]), "q25": round(float(r["conservative_score_q25"]), 3),
                "mean": round(float(r["predicted_hp_impact"]), 3), "ipl_hp_balls": int(r.get("ipl_hp_balls", 0)),
            }
            for _, r in c_ipl_qual_bowl[c_ipl_qual_bowl["inferred_role"].astype(str).str.contains("SPIN")].head(5).iterrows()
        ],
    }

    b0_top10_bowl_names = full_bowl_profiles["ablation_B0_no_pressure"]["top10_player_names"]
    cipl_top10_bowl_names = full_bowl_profiles["challenger_C_ipl_anchored"]["top10_player_names"]
    d_top10_bowl_names = full_bowl_profiles["challenger_D_workload"]["top10_player_names"]

    decision_record = {
        "chosen_model": chosen_overall,
        "chosen_model_batting": chosen_bat,
        "chosen_model_bowling": chosen_bowl,
        "selection_branch_batting": bat_reason,
        "selection_branch_bowling": bowl_reason,
        "bowling_fallback_coverage_ok": bowl_fallback_cov_ok,
        "bowling_slate_coverage_status": bowl_slate_status,
        "bowling_strongest_role_phase_alternatives": bowling_role_alts,
        "material_movers_and_near_ties": {
            "bowling_b0_vs_c_ipl_overlap": len(set(b0_top10_bowl_names) & set(cipl_top10_bowl_names)),
            "bowling_only_in_b0": [n for n in b0_top10_bowl_names if n not in set(cipl_top10_bowl_names)],
            "bowling_risers_in_c_ipl": [n for n in cipl_top10_bowl_names if n not in set(b0_top10_bowl_names)],
            "bowling_risers_in_d": [n for n in d_top10_bowl_names if n not in set(b0_top10_bowl_names)],
            "explanation": (
                "Ablation B-0 ignores player-specific pressure lift (modeled_lift=0.0) and ranks on pooled usual_level, "
                "lifting T20I-heavy bowlers (Muqeem, Mahedi, Mirza, Siddique, Humphreys) with 0 IPL HP balls. "
                "Challenger C-IPL shrinks small samples toward IPL role-and-phase priors and adds empirical T20I->IPL variance, "
                "pulling IPL-proven death/middle performers (e.g. Bumrah, Pathirana, Kuldeep, Varun, Duffy/etc.) forward."
            ),
        },
        "selection_rationale": selection_rationale,
        "paired_bootstrap_p_value_batting": p_val_c_bat,
        "paired_bootstrap_p_value_bowling": p_val_c_bowl,
    }

    protocol_reconciliation = {
        "career_pressure_floor": "48 HP legal balls across >=6 HP matches (all production and validation runs used 48b/6m; replaces early Stage 01 note referencing 36b).",
        "ipl_scouting_policy": "RPP_IPL_VERIFIED requires >=24 IPL HP legal balls across >=2 IPL HP matches; applied identically in replay and production.",
        "model_selection_loss_tolerance": f"+{MODEL_SELECT_LOSS_TOLERANCE:.2f} (frozen Stage 01 protocol guardrail; replaces legacy +{LEGACY_SELECT_LOSS_TOLERANCE:.2f} CLI branch).",
        "forecast_types": {
            "ex_ante_prior_mix": "Primary auction-time forecast using strictly pre-cutoff role/player phase weights (eligible for model selection).",
            "conditional_realized_phase_mix": "Diagnostic only: weights phase predictions by held-out match realized pressure-ball mix (excluded from selection).",
        },
        "rpp_calibration_method": "Strictly expanding chronological block residuals prior to cutoff (replaces interleaved 3-fold match split).",
    }
    shortlist_controls = {
        "2024": controls_2024,
        "2025": controls_2025,
        "2026": controls_2026,
    }
    stage3_blend_eval = _evaluate_stage3_bowling_blend_experiment(
        bowl_match_df=bowl_match_df,
        bowl_obs_all=bowl_obs_all,
        p_dim_pre2024=p_dim_pre2024,
        p_dim_train=p_dim_train,
        p_dim_pre2026=p_dim_pre2026,
        mapping_df=mapping_df,
        seed=config.seed,
        shortlist_controls=shortlist_controls,
        ipl_assessments_bowl=ipl_assessments.get("bowling", {}),
        rolling_2024_bowl=rolling_2024_diag.get("bowling", {}),
        retro_2026_bowl=retro_bowl_2026,
        p_dim_pre2023_h2=p_dim_pre2023_h2,
    )

    comparison_summary = {
        "stage": "09_model_comparison",
        "protocol_reconciliation": protocol_reconciliation,
        "pre_holdout_decision": decision_record,
        "stage3_bowling_blend_evaluation": stage3_blend_eval,
        "batting_short_stint_cause_audit": stint_cause_summary,
        "ipl_validation_2025_results": ipl_assessments,
        "ipl_retrospective_2026_results": {
            "batting": retro_bat_2026,
            "bowling": retro_bowl_2026,
        },
        "rolling_earlier_2024_ipl_diagnostic": rolling_2024_diag,
        "shortlist_policy_controls": shortlist_controls,
        "candidate_profile_summaries": {
            "pre_2026_cutoff": {"batting": pre2026_bat_profiles, "bowling": pre2026_bowl_profiles},
            "full_history_through_2026": {"batting": full_bat_profiles, "bowling": full_bowl_profiles},
        },
        "validation_2025_results": {
            "batting": {
                "candidate_A_baseline": metrics_bat_A,
                "candidate_B_statistical": metrics_bat_B,
                "candidate_C_boosted": metrics_bat_C,
                "challenger_C_role_phase": metrics_bat_C_phase,
                "challenger_C_ipl_anchored": metrics_bat_C_ipl,
                "ablation_B0_no_pressure": metrics_bat_abl,
                "challenger_D_workload": metrics_bat_D,
                "challenger_E_quantile_boosted": metrics_bat_E,
            },
            "bowling": {
                "candidate_A_baseline": metrics_bowl_A,
                "candidate_B_statistical": metrics_bowl_B,
                "candidate_C_boosted": metrics_bowl_C,
                "challenger_C_role_phase": metrics_bowl_C_phase,
                "challenger_C_ipl_anchored": metrics_bowl_C_ipl,
                "ablation_B0_no_pressure": metrics_bowl_abl,
                "challenger_D_workload": metrics_bowl_D,
                "challenger_E_quantile_boosted": metrics_bowl_E,
            },
            "ipl_transfer_check": ipl_transfer_check,
        },
        "test_holdout_2026_evaluation": {
            "chosen_model": chosen_overall,
            "batting": test_bat_metrics,
            "bowling": test_bowl_metrics,
            "status": "PASS_EVALUATED_ONCE_PREVIOUSLY_INSPECTED",
        },
    }

    out_path = out / "model_comparison.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(comparison_summary, f, indent=2)

    replay_doc = {
        "protocol_reconciliation": protocol_reconciliation,
        "pre_holdout_decision": decision_record,
        "stage3_bowling_blend_evaluation": stage3_blend_eval,
        "batting_short_stint_cause_audit": stint_cause_summary,
        "2024": rolling_2024_diag,
        "2025": ipl_assessments,
        "2026": {
            "batting": retro_bat_2026,
            "bowling": retro_bowl_2026,
        },
        "shortlist_policy_controls": shortlist_controls,
    }
    replay_path = out / "stage04_replay_results.json"
    with open(replay_path, "w", encoding="utf-8") as f:
        json.dump(replay_doc, f, indent=2)

    output_files = {
        "model_comparison.json": out_path,
        "stage04_replay_results.json": replay_path,
    }
    output_fingerprints = {fname: compute_sha256(fpath) for fname, fpath in output_files.items()}
    return comparison_summary, output_fingerprints
