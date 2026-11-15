"""Stage 08: Fit the Reliability Forecast using Empirical Bayes Partial Pooling."""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from rr_pressure.config import PipelineConfig
from rr_pressure.manifest import compute_sha256

Z_25 = 0.67449
Z_80 = 1.28155
MIN_PRESSURE_BALLS = 48
MIN_PRESSURE_MATCHES = 6
M_ORD_PRIOR = 48.0
M_HP_PRIOR = 36.0


def normalize_boolean_series(s: pd.Series) -> pd.Series:
    """Explicit boolean normalization safely handling strings ('False', 'unknown', '0', 'no'),
    booleans, numbers, pd.NA, and np.nan without relying on naive Python truthiness.
    """
    if s is None or len(s) == 0:
        return pd.Series(dtype=bool)
    
    def _to_bool(val: Any) -> bool:
        if pd.isna(val):
            return False
        if isinstance(val, (bool, np.bool_)):
            return bool(val)
        if isinstance(val, (int, float, np.number)):
            return bool(val == 1)
        val_str = str(val).strip().lower()
        if val_str in ("true", "1", "yes", "t", "y"):
            return True
        return False

    return s.map(_to_bool).astype(bool)


def ensure_explicit_role_flags(p_dim: pd.DataFrame) -> pd.DataFrame:
    """Normalize or explicitly derive role-support flags without permissive legacy fallback."""
    out_df = p_dim.copy()
    if "batting_role_supported" not in out_df.columns:
        if {"top7_innings", "batting_innings", "avg_bat_order"}.issubset(out_df.columns):
            t7_sh = np.where(
                out_df["batting_innings"] > 0,
                out_df["top7_innings"] / out_df["batting_innings"],
                0.0,
            )
            out_df["batting_role_supported"] = (
                (out_df["top7_innings"] >= 5)
                & (t7_sh >= 0.50)
                & (pd.to_numeric(out_df["avg_bat_order"], errors="coerce").fillna(99.0) <= 7.5)
            )
        elif {"inferred_role", "avg_bat_order", "career_balls_faced"}.issubset(out_df.columns):
            out_df["batting_role_supported"] = (
                out_df["inferred_role"].astype(str).str.contains("BATTER|ALLROUNDER")
                & (pd.to_numeric(out_df["avg_bat_order"], errors="coerce").fillna(99.0) <= 7.5)
                & (pd.to_numeric(out_df["career_balls_faced"], errors="coerce").fillna(0) >= 60)
            )
        else:
            out_df["batting_role_supported"] = False
    else:
        out_df["batting_role_supported"] = normalize_boolean_series(out_df["batting_role_supported"])

    if "bowling_role_supported" not in out_df.columns:
        if {"bowling_matches", "legal_balls_bowled", "overs_per_bowling_match"}.issubset(out_df.columns):
            out_df["bowling_role_supported"] = (
                (out_df["bowling_matches"] >= 5)
                & (out_df["legal_balls_bowled"] >= 60)
                & (out_df["overs_per_bowling_match"] >= 1.85)
            )
        elif {"inferred_role", "career_balls_bowled"}.issubset(out_df.columns):
            out_df["bowling_role_supported"] = (
                out_df["inferred_role"].astype(str).str.contains("BOWLER|ALLROUNDER")
                & (pd.to_numeric(out_df["career_balls_bowled"], errors="coerce").fillna(0) >= 60)
            )
        else:
            out_df["bowling_role_supported"] = False
    else:
        out_df["bowling_role_supported"] = normalize_boolean_series(out_df["bowling_role_supported"])
    return out_df


def is_qualified(
    profiles: pd.DataFrame,
    role_type: str,
    min_balls: int = 48,
    min_matches: int = 6,
) -> pd.Series:
    """Canonical qualification check for batting and bowling pressure rankings.
    
    Separates independent orthogonal gates:
    1. Role Support: Demonstrated credible deployment in that discipline.
       Must be explicitly present and True. Strings like 'False', 'unknown',
       pd.NA, or missing role evidence are strictly normalized to False.
    2. Statistical Sample Sufficiency: hp_balls >= min_balls and hp_matches >= min_matches.
    """
    role_col = "batting_role_supported" if str(role_type).lower() == "batting" else "bowling_role_supported"
    if role_col in profiles.columns:
        role_supported = normalize_boolean_series(profiles[role_col])
        role_supported.index = profiles.index
    else:
        # Missing role evidence column -> explicitly UNRESOLVED, NEVER qualify!
        role_supported = pd.Series(False, index=profiles.index)
        
    sample_sufficient = (profiles["hp_balls"] >= min_balls) & (profiles["hp_matches"] >= min_matches)
    return role_supported & sample_sufficient


def fit_player_forecast(
    match_df: pd.DataFrame,
    p_dim: pd.DataFrame,
    role_type: str,  # 'batting' or 'bowling'
    seed: int = 2027,
    folds: Any = None,
    baseline_only: bool = False,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    # Columns mapping
    if role_type == "batting":
        hp_balls_col = "hp_balls_faced"
        hp_impact_col = "hp_bat_impact"
        ord_balls_col = "ord_balls_faced"
        ord_impact_col = "ord_bat_impact"
        impact_12b_col = "hp_bat_impact_12b"
    else:
        hp_balls_col = "hp_balls_bowled"
        hp_impact_col = "hp_bowl_impact"
        ord_balls_col = "ord_balls_bowled"
        ord_impact_col = "ord_bowl_impact"
        impact_12b_col = "hp_bowl_impact_12b"
        
    # Fit on specified folds or historical training + validation (pre-2026)
    if folds is None:
        target_folds = ["TRAIN_2022_2024", "VAL_2025"]
    else:
        target_folds = folds
    hist_matches = match_df[match_df["fold"].isin(target_folds)].copy()
    
    # Estimate match-level variance
    valid_workloads = hist_matches[hist_matches[hp_balls_col] >= 6]
    sigma_match = float(valid_workloads[impact_12b_col].std())
    if np.isnan(sigma_match) or sigma_match < 2.0:
        sigma_match = 7.0
        
    # Player aggregations (explicitly handle malformed or legacy role schemas)
    p_dim_active = ensure_explicit_role_flags(p_dim)
        
    cols_to_join = [
        c for c in [
            "player_name", "inferred_role", "bowler_type",
            "batting_role_supported", "bowling_role_supported",
            "batting_display_role", "bowling_display_role"
        ] if c in p_dim_active.columns
    ]
    p_stats = hist_matches.groupby("player_id").agg(
        total_matches=("match_id", "nunique"),
        hp_balls=(hp_balls_col, "sum"),
        hp_impact=(hp_impact_col, "sum"),
        ord_matches=(ord_balls_col, lambda s: int((s > 0).sum())),
        ord_balls=(ord_balls_col, "sum"),
        ord_impact=(ord_impact_col, "sum"),
    ).join(p_dim_active.set_index("player_id")[cols_to_join])
    p_stats["hp_matches"] = (
        hist_matches[hist_matches[hp_balls_col].gt(0)].groupby("player_id")["match_id"].nunique()
        .reindex(p_stats.index, fill_value=0)
    )
    
    # Standardized 12-ball rate: retain NaN when exposure is zero (do NOT inject artificial 0.0)
    p_stats["hp_rate_12b"] = np.where(p_stats["hp_balls"] > 0, (p_stats["hp_impact"] / p_stats["hp_balls"]) * 12.0, np.nan)
    p_stats["ord_rate_12b"] = np.where(p_stats["ord_balls"] > 0, (p_stats["ord_impact"] / p_stats["ord_balls"]) * 12.0, np.nan)
    
    # Role group priors: strictly exclude unexposed players (balls == 0) from median calculation
    valid_ord = p_stats[p_stats["ord_balls"] > 0]
    role_ord_median = valid_ord.groupby("inferred_role")["ord_rate_12b"].median().to_dict()
    global_ord_median = float(valid_ord["ord_rate_12b"].median()) if len(valid_ord) > 0 else 0.0
    
    valid_both = p_stats[(p_stats["hp_balls"] > 0) & (p_stats["ord_balls"] > 0)].copy()
    valid_both["raw_lift_sample"] = valid_both["hp_rate_12b"] - valid_both["ord_rate_12b"]
    role_lift_median = valid_both.groupby("inferred_role")["raw_lift_sample"].median().to_dict()
    global_lift_median = float(valid_both["raw_lift_sample"].median()) if len(valid_both) > 0 else 0.0
    
    p_stats["prior_ord"] = p_stats["inferred_role"].map(role_ord_median).fillna(global_ord_median)
    p_stats["prior_lift"] = p_stats["inferred_role"].map(role_lift_median).fillna(global_lift_median)
    
    # Empirical Bayes Shrinkage
    ord_rate_safe = p_stats["ord_rate_12b"].fillna(p_stats["prior_ord"])
    p_stats["usual_level"] = (
        p_stats["ord_balls"] * ord_rate_safe + M_ORD_PRIOR * p_stats["prior_ord"]
    ) / (p_stats["ord_balls"] + M_ORD_PRIOR)
    
    raw_lift_player = np.where(p_stats["hp_balls"] > 0, p_stats["hp_rate_12b"] - p_stats["usual_level"], p_stats["prior_lift"])
    p_stats["pressure_lift"] = (
        p_stats["hp_balls"] * raw_lift_player + M_HP_PRIOR * p_stats["prior_lift"]
    ) / (p_stats["hp_balls"] + M_HP_PRIOR)
    
    # Forecast conditional on high pressure opportunity
    p_stats["predicted_hp_impact"] = p_stats["usual_level"] + p_stats["pressure_lift"]
    # Ablation without player pressure effect (pure baseline extrapolated)
    p_stats["predicted_hp_impact_ablation"] = p_stats["usual_level"]
    
    # Uncertainty decomposition
    se_param = sigma_match / np.sqrt(p_stats["hp_matches"] + 1.0)
    p_stats["param_se"] = se_param
    p_stats["match_sigma"] = sigma_match
    p_stats["predictive_sigma"] = np.sqrt(sigma_match**2 + se_param**2)
    
    # Candidate B0 (Ablation without player pressure effect: pure baseline extrapolated)
    p_stats["b0_mean"] = p_stats["usual_level"]
    p_stats["b0_q25"] = p_stats["b0_mean"] - Z_25 * p_stats["predictive_sigma"]
    p_stats["b0_ci_lower_80"] = p_stats["b0_mean"] - Z_80 * p_stats["predictive_sigma"]
    p_stats["b0_ci_upper_80"] = p_stats["b0_mean"] + Z_80 * p_stats["predictive_sigma"]
    
    # Candidate B1 (Statistical model with shrunk personal pressure lift)
    p_stats["b1_mean"] = p_stats["usual_level"] + p_stats["pressure_lift"]
    p_stats["b1_q25"] = p_stats["b1_mean"] - Z_25 * p_stats["predictive_sigma"]
    p_stats["b1_ci_lower_80"] = p_stats["b1_mean"] - Z_80 * p_stats["predictive_sigma"]
    p_stats["b1_ci_upper_80"] = p_stats["b1_mean"] + Z_80 * p_stats["predictive_sigma"]
    
    # Tier exposure breakdown
    if "comp_tier" in hist_matches.columns:
        ipl_rows = hist_matches[hist_matches["comp_tier"] == "IPL"]
        t20i_rows = hist_matches[hist_matches["comp_tier"].isin(["T20I", "INTERNATIONAL"])]
        emerging_rows = hist_matches[~hist_matches["comp_tier"].isin(["IPL", "T20I", "INTERNATIONAL"])]
        
        p_stats["ipl_hp_balls"] = p_stats.index.map(ipl_rows.groupby("player_id")[hp_balls_col].sum()).fillna(0).astype(int)
        p_stats["t20i_hp_balls"] = p_stats.index.map(t20i_rows.groupby("player_id")[hp_balls_col].sum()).fillna(0).astype(int)
        p_stats["emerging_hp_balls"] = p_stats.index.map(emerging_rows.groupby("player_id")[hp_balls_col].sum()).fillna(0).astype(int)
    else:
        p_stats["ipl_hp_balls"] = 0
        p_stats["t20i_hp_balls"] = 0
        p_stats["emerging_hp_balls"] = 0
    
    if not baseline_only:
        from rr_pressure.challengers import ChallengerD_WorkloadDistributional, ChallengerE_DirectQuantileBoosted
        profiles = p_stats.reset_index()
        for prefix, model, inputs in (
            ("d", ChallengerD_WorkloadDistributional(), p_dim),
            ("e", ChallengerE_DirectQuantileBoosted(seed=seed), profiles),
        ):
            predictions = model.fit(hist_matches, inputs, role_type).predict_player_forecast(profiles)
            for field, values in zip(("q25", "mean", "ci_lower_80", "ci_upper_80"), predictions):
                p_stats[f"{prefix}_{field}"] = values
    
    # Backward-compatible aliases
    p_stats["predicted_hp_impact"] = p_stats["b1_mean"]
    p_stats["predicted_hp_impact_ablation"] = p_stats["b0_mean"]
    p_stats["conservative_score_q25"] = p_stats["b1_q25"]
    p_stats["ci_lower_80"] = p_stats["b1_ci_lower_80"]
    p_stats["ci_upper_80"] = p_stats["b1_ci_upper_80"]
    
    # Independent Qualification & Eligibility Checks
    role_col = "batting_role_supported" if role_type.lower() == "batting" else "bowling_role_supported"
    if role_col in p_stats.columns:
        p_stats["is_role_unresolved"] = p_stats[role_col].isna()
        p_stats["role_supported"] = normalize_boolean_series(p_stats[role_col]).values
    else:
        p_stats["is_role_unresolved"] = True
        p_stats["role_supported"] = False
        
    p_stats["sample_sufficient"] = (p_stats["hp_balls"] >= MIN_PRESSURE_BALLS) & (p_stats["hp_matches"] >= MIN_PRESSURE_MATCHES)
    p_stats["is_qualified"] = is_qualified(p_stats, role_type, MIN_PRESSURE_BALLS, MIN_PRESSURE_MATCHES)
    p_stats["is_watchlist"] = ~p_stats["is_qualified"]
    
    exclusion_reasons = []
    for _, r in p_stats.iterrows():
        if bool(r.get("is_role_unresolved", False)):
            reason = "UNRESOLVED_ROLE_EVIDENCE"
        elif not bool(r.get("role_supported", False)):
            reason = "NO_BATTING_ROLE_SUPPORT_TAIL_ENDER" if role_type.lower() == "batting" else "NO_BOWLING_ROLE_SUPPORT_OCCASIONAL_BOWLER"
        elif not bool(r.get("sample_sufficient", False)):
            reason = "INSUFFICIENT_PRESSURE_SAMPLE"
        else:
            reason = ""
        exclusion_reasons.append(reason)
    p_stats["exclusion_reason"] = exclusion_reasons
    p_stats["unstop_dropdown_status"] = "PROVISIONAL_UNRESOLVED"
    p_stats["auction_status_2027"] = "UNKNOWN"
    
    # Match bootstrap for rank stability (50 replicates) preserving match multiplicity
    rng = np.random.default_rng(seed)
    unique_matches = hist_matches["match_id"].unique()
    boot_scores = {pid: [] for pid in p_stats.index}
    
    m_ids = hist_matches["match_id"].values
    p_ids = hist_matches["player_id"].values
    m_hp_balls = hist_matches[hp_balls_col].values
    m_hp_impact = hist_matches[hp_impact_col].values
    
    for _ in range(0 if baseline_only else 50):
        sample_mids = rng.choice(unique_matches, size=len(unique_matches), replace=True)
        mid_counts = pd.Series(sample_mids).value_counts().to_dict()
        weights = np.array([mid_counts.get(m, 0) for m in m_ids])
        
        w_balls = m_hp_balls * weights
        w_impact = m_hp_impact * weights
        
        b_df = pd.DataFrame({"player_id": p_ids, "w_balls": w_balls, "w_impact": w_impact})
        b_agg = b_df.groupby("player_id", observed=False).sum()
        rates = np.where(b_agg["w_balls"] > 0, (b_agg["w_impact"] / b_agg["w_balls"]) * 12.0, 0.0)
        rate_map = dict(zip(b_agg.index, rates))
        
        for pid in p_stats.index:
            boot_scores[pid].append(rate_map.get(pid, 0.0))
            
    if not baseline_only:
        p_stats["bootstrap_rank_std"] = [float(np.std(boot_scores[pid])) for pid in p_stats.index]
    
    p_stats = p_stats.reset_index().sort_values(
        ["is_qualified", "conservative_score_q25", "predicted_hp_impact", "hp_matches"],
        ascending=[False, False, False, False]
    ).reset_index(drop=True)
    
    # Assign performance rank among qualified
    p_stats["performance_rank"] = np.nan
    p_stats.loc[p_stats["is_qualified"], "performance_rank"] = np.arange(1, p_stats["is_qualified"].sum() + 1)
    
    diagnostics = {
        "role_type": role_type,
        "sigma_match": sigma_match,
        "total_players_evaluated": len(p_stats),
        "qualified_players_count": int(p_stats["is_qualified"].sum()),
        "watchlist_players_count": int(p_stats["is_watchlist"].sum()),
        "top_qualifier": p_stats.iloc[0]["player_name"],
        "top_qualifier_score": float(p_stats.iloc[0]["conservative_score_q25"]),
    }
    return p_stats, diagnostics


def run_stage08_forecast(config: PipelineConfig) -> Tuple[Dict[str, Any], Dict[str, str]]:
    out = config.out_dir
    out.mkdir(parents=True, exist_ok=True)
    
    bat_match_df = pd.read_csv(out / "match_player_batting_impact.csv")
    bowl_match_df = pd.read_csv(out / "match_player_bowling_impact.csv")
    
    p_dim_train_path = out / "player_dimension_train.csv"
    p_dim = pd.read_csv(out / "player_dimension.csv")
    if p_dim_train_path.exists():
        p_dim_train = pd.read_csv(p_dim_train_path)
        train_roles = p_dim_train.set_index("player_id")["inferred_role"].to_dict()
        p_dim["inferred_role"] = p_dim["player_id"].map(train_roles).fillna(p_dim["inferred_role"])
    
    # Fit Batting Model
    bat_forecast, bat_diag = fit_player_forecast(bat_match_df, p_dim, role_type="batting", seed=config.seed)
    bat_out_path = out / "player_reliability_forecasts_batting.csv"
    bat_forecast.to_csv(bat_out_path, index=False)
    
    # Fit Bowling Model
    bowl_forecast, bowl_diag = fit_player_forecast(bowl_match_df, p_dim, role_type="bowling", seed=config.seed)
    bowl_out_path = out / "player_reliability_forecasts_bowling.csv"
    bowl_forecast.to_csv(bowl_out_path, index=False)
    
    forecast_diagnostics = {
        "batting_model": bat_diag,
        "bowling_model": bowl_diag,
        "standardized_unit": "12 legal-ball equivalents",
        "evidence_floor": {
            "min_pressure_balls": MIN_PRESSURE_BALLS,
            "min_pressure_matches": MIN_PRESSURE_MATCHES,
        },
        "formula": "conservative_score_q25 = predicted_hp_impact - 0.67449 * sqrt(sigma_match^2 + se_param^2)",
    }
    
    diag_path = out / "forecast_diagnostics.json"
    with open(diag_path, "w", encoding="utf-8") as f:
        json.dump(forecast_diagnostics, f, indent=2)
        
    output_files = {
        "player_reliability_forecasts_batting.csv": bat_out_path,
        "player_reliability_forecasts_bowling.csv": bowl_out_path,
        "forecast_diagnostics.json": diag_path,
    }
    output_fingerprints = {fname: compute_sha256(fpath) for fname, fpath in output_files.items()}
    return forecast_diagnostics, output_fingerprints
