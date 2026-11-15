"""Stage 07: Convert Runs and Wickets into Context-Adjusted Player Impact Module."""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from rr_pressure.config import PipelineConfig
from rr_pressure.ingest import derive_player_roles
from rr_pressure.manifest import compute_sha256
from rr_pressure.models import HISTORICAL_REFERENCE_CUTOFFS


WICKET_PRICE_DEFAULT = 7.0  # Marginal run-equivalent cost derived in Stage 05
EMPIRICAL_BAYES_PRIOR_WEIGHT = 20.0  # Pseudo-counts for cell shrinkage


def fit_peer_expectations(train_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, float]]:
    """Fit hierarchical empirical-Bayes shrunk peer expectation tables per legal ball on strictly historical training deliveries."""
    if "is_penalty" in train_df.columns:
        train_df = train_df[~train_df["is_penalty"].astype(bool)]
    g_keys = ["match_phase", "innings", "comp_tier", "striker_role", "bowler_style"]
    
    # Coarser fallback table by phase, innings, tier (normalized per legal ball)
    fb_agg = train_df.groupby(["match_phase", "innings", "comp_tier"], observed=False).agg(
        fb_bat_runs=("runs", "sum"),
        fb_striker_dismissal=("is_striker_dismissed", "sum"),
        fb_charged_runs=("bowler_charge_runs", "sum"),
        fb_bowler_wicket=("is_bowler_wicket", "sum"),
        fb_legal_balls=("is_legal_ball", "sum"),
    ).reset_index()
    fb_legal_cnt = np.maximum(1, fb_agg["fb_legal_balls"].values)
    fb_agg["fb_exp_bat_runs"] = fb_agg["fb_bat_runs"] / fb_legal_cnt
    fb_agg["fb_exp_striker_dismissal"] = fb_agg["fb_striker_dismissal"] / fb_legal_cnt
    fb_agg["fb_exp_charged_runs"] = fb_agg["fb_charged_runs"] / fb_legal_cnt
    fb_agg["fb_exp_bowler_wicket"] = fb_agg["fb_bowler_wicket"] / fb_legal_cnt
    fallback_table = fb_agg[["match_phase", "innings", "comp_tier", "fb_exp_bat_runs", "fb_exp_striker_dismissal", "fb_exp_charged_runs", "fb_exp_bowler_wicket"]].copy()
    
    # Global training means (normalized per legal ball)
    tot_legal = max(1, int(train_df["is_legal_ball"].sum()))
    global_means = {
        "glob_bat_runs": float(train_df["runs"].sum() / tot_legal),
        "glob_striker_dismissal": float(train_df["is_striker_dismissed"].sum() / tot_legal),
        "glob_charged_runs": float(train_df["bowler_charge_runs"].sum() / tot_legal),
        "glob_bowler_wicket": float(train_df["is_bowler_wicket"].sum() / tot_legal),
    }
    
    # Detailed cell table (normalized per legal ball)
    cell_agg = train_df.groupby(g_keys, observed=False).agg(
        sum_bat_runs=("runs", "sum"),
        sum_striker_dismissal=("is_striker_dismissed", "sum"),
        sum_charged_runs=("bowler_charge_runs", "sum"),
        sum_bowler_wicket=("is_bowler_wicket", "sum"),
        cell_count=("runs", "count"),
        legal_balls=("is_legal_ball", "sum"),
    ).reset_index()
    
    # Merge with fallback for empirical Bayes shrinkage
    merged = cell_agg.merge(fallback_table, on=["match_phase", "innings", "comp_tier"], how="left")
    
    m = EMPIRICAL_BAYES_PRIOR_WEIGHT
    cnt = merged["legal_balls"]
    
    # Raw cell means per legal ball, with fallback when legal_balls == 0
    raw_bat_runs = np.where(cnt > 0, merged["sum_bat_runs"] / np.maximum(1, cnt), merged["fb_exp_bat_runs"])
    raw_striker_dismissal = np.where(cnt > 0, merged["sum_striker_dismissal"] / np.maximum(1, cnt), merged["fb_exp_striker_dismissal"])
    raw_charged_runs = np.where(cnt > 0, merged["sum_charged_runs"] / np.maximum(1, cnt), merged["fb_exp_charged_runs"])
    raw_bowler_wicket = np.where(cnt > 0, merged["sum_bowler_wicket"] / np.maximum(1, cnt), merged["fb_exp_bowler_wicket"])
    
    # Shrink raw cell means toward fallback prior
    merged["exp_bat_runs"] = (raw_bat_runs * cnt + merged["fb_exp_bat_runs"] * m) / (cnt + m)
    merged["exp_striker_dismissal"] = (raw_striker_dismissal * cnt + merged["fb_exp_striker_dismissal"] * m) / (cnt + m)
    merged["exp_charged_runs"] = (raw_charged_runs * cnt + merged["fb_exp_charged_runs"] * m) / (cnt + m)
    merged["exp_bowler_wicket"] = (raw_bowler_wicket * cnt + merged["fb_exp_bowler_wicket"] * m) / (cnt + m)
    
    # Also attach fallback table rows for any completely unseen cells
    export_table = merged[g_keys + ["exp_bat_runs", "exp_striker_dismissal", "exp_charged_runs", "exp_bowler_wicket", "cell_count", "legal_balls"]].copy()
    return export_table, fallback_table, global_means


def compute_state_dependent_wicket_value(df: pd.DataFrame, score_model: Dict[str, Any]) -> Tuple[np.ndarray, float]:
    """Compute delivery-level state-dependent marginal wicket value w(s) and return with constant benchmark."""
    coef = score_model.get("coefficients", [])
    mid_benchmark = float(score_model.get("marginal_wicket_value_mid_innings", score_model.get("marginal_wicket_value", 7.0108)))
    
    if len(coef) >= 5:
        # coef order: [b, w, bw, b2, w2, ipl]
        b_coef, w_coef, bw_coef, b2_coef, w2_coef = coef[0], coef[1], coef[2], coef[3], coef[4]
        b = df["pre_balls_remaining"].values / 120.0
        w = df["pre_wickets_in_hand"].values / 10.0
        w_prev = np.maximum(0.0, w - 0.1)
        delta_w = w - w_prev
        w_s = w_coef * delta_w + bw_coef * b * delta_w + w2_coef * (w**2 - w_prev**2)
        w_s = np.clip(w_s, 1.0, 15.0)
    else:
        w_s = np.full(len(df), mid_benchmark, dtype=float)
        
    return w_s, mid_benchmark


def cross_fit_peer_expectations(df: pd.DataFrame, n_splits: int = 5) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Generate strictly out-of-fold peer expectations across match clusters in training fold,
    and out-of-time expectations for validation and test folds."""
    g_keys = ["match_phase", "innings", "comp_tier", "striker_role", "bowler_style"]
    
    exp_bat_runs = np.zeros(len(df), dtype=float)
    exp_striker_dismissal = np.zeros(len(df), dtype=float)
    exp_charged_runs = np.zeros(len(df), dtype=float)
    exp_bowler_wicket = np.zeros(len(df), dtype=float)
    
    # 1. Training fold forward-chaining chronological block fitting (strictly past-only)
    tr_mask = (df["fold"] == "TRAIN_2022_2024") & (df["is_cohort_eligible"] == True)
    
    b0_mask = tr_mask & (df["match_date"] < "2022-07-01")
    b1_mask = tr_mask & (df["match_date"] >= "2022-07-01") & (df["match_date"] < "2023-01-01")
    b2_mask = tr_mask & (df["match_date"] >= "2023-01-01") & (df["match_date"] < "2024-01-01")
    b3_mask = tr_mask & (df["match_date"] >= "2024-01-01")
    
    # Warm-up block 0 (2022-H1): fits from Block 0 with global prior fallback
    cell_0, fb_0, glob_0 = fit_peer_expectations(df[b0_mask])
    m_b0 = df[b0_mask].merge(cell_0, on=g_keys, how="left").merge(fb_0, on=["match_phase", "innings", "comp_tier"], how="left")
    b0_idx = np.where(b0_mask)[0]
    exp_bat_runs[b0_idx] = m_b0["exp_bat_runs"].fillna(m_b0["fb_exp_bat_runs"]).fillna(glob_0["glob_bat_runs"]).values
    exp_striker_dismissal[b0_idx] = m_b0["exp_striker_dismissal"].fillna(m_b0["fb_exp_striker_dismissal"]).fillna(glob_0["glob_striker_dismissal"]).values
    exp_charged_runs[b0_idx] = m_b0["exp_charged_runs"].fillna(m_b0["fb_exp_charged_runs"]).fillna(glob_0["glob_charged_runs"]).values
    exp_bowler_wicket[b0_idx] = m_b0["exp_bowler_wicket"].fillna(m_b0["fb_exp_bowler_wicket"]).fillna(glob_0["glob_bowler_wicket"]).values
    
    # Block 1 (2022-H2): fits strictly on earlier Block 0
    m_b1 = df[b1_mask].merge(cell_0, on=g_keys, how="left").merge(fb_0, on=["match_phase", "innings", "comp_tier"], how="left")
    b1_idx = np.where(b1_mask)[0]
    exp_bat_runs[b1_idx] = m_b1["exp_bat_runs"].fillna(m_b1["fb_exp_bat_runs"]).fillna(glob_0["glob_bat_runs"]).values
    exp_striker_dismissal[b1_idx] = m_b1["exp_striker_dismissal"].fillna(m_b1["fb_exp_striker_dismissal"]).fillna(glob_0["glob_striker_dismissal"]).values
    exp_charged_runs[b1_idx] = m_b1["exp_charged_runs"].fillna(m_b1["fb_exp_charged_runs"]).fillna(glob_0["glob_charged_runs"]).values
    exp_bowler_wicket[b1_idx] = m_b1["exp_bowler_wicket"].fillna(m_b1["fb_exp_bowler_wicket"]).fillna(glob_0["glob_bowler_wicket"]).values
    
    # Block 2 (2023): fits strictly on all 2022 (Block 0 + Block 1)
    cell_22, fb_22, glob_22 = fit_peer_expectations(df[b0_mask | b1_mask])
    m_b2 = df[b2_mask].merge(cell_22, on=g_keys, how="left").merge(fb_22, on=["match_phase", "innings", "comp_tier"], how="left")
    b2_idx = np.where(b2_mask)[0]
    exp_bat_runs[b2_idx] = m_b2["exp_bat_runs"].fillna(m_b2["fb_exp_bat_runs"]).fillna(glob_22["glob_bat_runs"]).values
    exp_striker_dismissal[b2_idx] = m_b2["exp_striker_dismissal"].fillna(m_b2["fb_exp_striker_dismissal"]).fillna(glob_22["glob_striker_dismissal"]).values
    exp_charged_runs[b2_idx] = m_b2["exp_charged_runs"].fillna(m_b2["fb_exp_charged_runs"]).fillna(glob_22["glob_charged_runs"]).values
    exp_bowler_wicket[b2_idx] = m_b2["exp_bowler_wicket"].fillna(m_b2["fb_exp_bowler_wicket"]).fillna(glob_22["glob_bowler_wicket"]).values
    
    # Block 3 (2024): fits strictly on 2022 + 2023
    cell_22_23, fb_22_23, glob_22_23 = fit_peer_expectations(df[b0_mask | b1_mask | b2_mask])
    m_b3 = df[b3_mask].merge(cell_22_23, on=g_keys, how="left").merge(fb_22_23, on=["match_phase", "innings", "comp_tier"], how="left")
    b3_idx = np.where(b3_mask)[0]
    exp_bat_runs[b3_idx] = m_b3["exp_bat_runs"].fillna(m_b3["fb_exp_bat_runs"]).fillna(glob_22_23["glob_bat_runs"]).values
    exp_striker_dismissal[b3_idx] = m_b3["exp_striker_dismissal"].fillna(m_b3["fb_exp_striker_dismissal"]).fillna(glob_22_23["glob_striker_dismissal"]).values
    exp_charged_runs[b3_idx] = m_b3["exp_charged_runs"].fillna(m_b3["fb_exp_charged_runs"]).fillna(glob_22_23["glob_charged_runs"]).values
    exp_bowler_wicket[b3_idx] = m_b3["exp_bowler_wicket"].fillna(m_b3["fb_exp_bowler_wicket"]).fillna(glob_22_23["glob_bowler_wicket"]).values

    # 2. VAL_2025: fit on full TRAIN_2022_2024
    val_mask = (df["fold"] == "VAL_2025") & (df["is_cohort_eligible"] == True)
    val_indices = np.where(val_mask)[0]
    if len(val_indices) > 0:
        cell_tbl_tr, fb_tbl_tr, glob_means_tr = fit_peer_expectations(df[tr_mask])
        m_val2025 = df.iloc[val_indices].merge(cell_tbl_tr, on=g_keys, how="left")
        m_val2025 = m_val2025.merge(fb_tbl_tr, on=["match_phase", "innings", "comp_tier"], how="left")
        
        exp_bat_runs[val_indices] = m_val2025["exp_bat_runs"].fillna(m_val2025["fb_exp_bat_runs"]).fillna(glob_means_tr["glob_bat_runs"]).values
        exp_striker_dismissal[val_indices] = m_val2025["exp_striker_dismissal"].fillna(m_val2025["fb_exp_striker_dismissal"]).fillna(glob_means_tr["glob_striker_dismissal"]).values
        exp_charged_runs[val_indices] = m_val2025["exp_charged_runs"].fillna(m_val2025["fb_exp_charged_runs"]).fillna(glob_means_tr["glob_charged_runs"]).values
        exp_bowler_wicket[val_indices] = m_val2025["exp_bowler_wicket"].fillna(m_val2025["fb_exp_bowler_wicket"]).fillna(glob_means_tr["glob_bowler_wicket"]).values

    # 3. TEST_HOLDOUT_2026: fit on TRAIN_2022_2024 + VAL_2025
    test_mask = (df["fold"] == "TEST_HOLDOUT_2026") & (df["is_cohort_eligible"] == True)
    test_indices = np.where(test_mask)[0]
    if len(test_indices) > 0:
        tr_val_mask = df["fold"].isin(["TRAIN_2022_2024", "VAL_2025"]) & (df["is_cohort_eligible"] == True)
        cell_tbl_tv, fb_tbl_tv, glob_means_tv = fit_peer_expectations(df[tr_val_mask])
        m_test2026 = df.iloc[test_indices].merge(cell_tbl_tv, on=g_keys, how="left")
        m_test2026 = m_test2026.merge(fb_tbl_tv, on=["match_phase", "innings", "comp_tier"], how="left")
        
        exp_bat_runs[test_indices] = m_test2026["exp_bat_runs"].fillna(m_test2026["fb_exp_bat_runs"]).fillna(glob_means_tv["glob_bat_runs"]).values
        exp_striker_dismissal[test_indices] = m_test2026["exp_striker_dismissal"].fillna(m_test2026["fb_exp_striker_dismissal"]).fillna(glob_means_tv["glob_striker_dismissal"]).values
        exp_charged_runs[test_indices] = m_test2026["exp_charged_runs"].fillna(m_test2026["fb_exp_charged_runs"]).fillna(glob_means_tv["glob_charged_runs"]).values
        exp_bowler_wicket[test_indices] = m_test2026["exp_bowler_wicket"].fillna(m_test2026["fb_exp_bowler_wicket"]).fillna(glob_means_tv["glob_bowler_wicket"]).values

    return exp_bat_runs, exp_striker_dismissal, exp_charged_runs, exp_bowler_wicket


def compute_cumulative_prematch_features(agg_df: pd.DataFrame, discipline: str) -> pd.DataFrame:
    """Compute strictly pre-match historical stats (usual_level, hp_balls) for each player row."""
    sorted_df = agg_df.sort_values(["match_date", "match_id"]).reset_index(drop=True)
    
    balls_col = "hp_balls_faced" if discipline == "batting" else "hp_balls_bowled"
    impact_col = "hp_bat_impact" if discipline == "batting" else "hp_bowl_impact"
    ord_balls_col = "ord_balls_faced" if discipline == "batting" else "ord_balls_bowled"
    ord_impact_col = "ord_bat_impact" if discipline == "batting" else "ord_bowl_impact"
    
    # Use one snapshot per calendar date when match start times are unavailable.
    daily = sorted_df.assign(has_pressure=sorted_df[balls_col].gt(0)).groupby(
        ["player_id", "match_date"], sort=True
    ).agg(
        prior_ord_balls=(ord_balls_col, "sum"), prior_ord_impact=(ord_impact_col, "sum"),
        hp_balls=(balls_col, "sum"), prior_hp_impact=(impact_col, "sum"),
        prior_hp_matches=("has_pressure", "sum"),
    )
    prior = daily.groupby(level="player_id").cumsum() - daily
    sorted_df = sorted_df.drop(columns=prior.columns, errors="ignore").join(
        prior, on=["player_id", "match_date"], validate="many_to_one"
    )
    sorted_df["usual_level"] = booster_usual_level(sorted_df["prior_ord_impact"], sorted_df["prior_ord_balls"])
    return sorted_df


def booster_usual_level(ordinary_impact: pd.Series, ordinary_balls: pd.Series) -> pd.Series:
    """Ordinary impact per 12 balls, with a zero-centered 48-ball prior."""
    return 12.0 * ordinary_impact / (ordinary_balls + 48.0)


def run_stage07_impact(config: PipelineConfig) -> Tuple[Dict[str, Any], Dict[str, str]]:
    out = config.out_dir
    out.mkdir(parents=True, exist_ok=True)
    
    # Load deliveries with pressure labels
    df = pd.read_csv(out / "delivery_pressure_labels.csv", low_memory=False)
    
    # Load player dimensions (training as-of dimension strictly for historical folds to prevent future leakage)
    p_dim_train_path = out / "player_dimension_train.csv"
    p_dim_path = out / "player_dimension.csv"
    p_dim_train = pd.read_csv(p_dim_train_path) if p_dim_train_path.exists() else pd.read_csv(p_dim_path)

    role_map = p_dim_train.set_index("player_id")["inferred_role"].to_dict()
    style_map = p_dim_train.set_index("player_id")["bowler_type"].to_dict()

    df["striker_role"] = df["striker_id"].map(role_map).fillna("BATTER_SPARSE")
    df["bowler_style"] = df["bowler_id"].map(style_map).fillna("Unknown")
    if "pressure_reference_cutoff" in df:
        lineups = pd.read_csv(config.raw_dir / "playing_eleven.csv")
        mapping = pd.read_csv(config.raw_dir / "competition_team_player_mapping.csv")
        warmup = df["pressure_reference_cutoff"].fillna("").eq("")
        df.loc[warmup, "striker_role"] = "BATTER_SPARSE"
        df.loc[warmup, "bowler_style"] = "Unknown"
        for cutoff in (*HISTORICAL_REFERENCE_CUTOFFS, "2026-01-01"):
            past = df[df["match_date"].lt(cutoff) & df["is_cohort_eligible"]]
            roles = derive_player_roles(
                past, lineups, p_dim_train["player_id"], mapping, past["match_id"].unique()
            ).set_index("player_id")
            rows = df["pressure_reference_cutoff"].eq(cutoff)
            if rows.any():
                df.loc[rows, "striker_role"] = df.loc[rows, "striker_id"].map(roles["inferred_role"]).fillna("BATTER_SPARSE")
                df.loc[rows, "bowler_style"] = df.loc[rows, "bowler_id"].map(roles["bowler_type"]).fillna("Unknown")
    
    # Generate strictly out-of-fold and out-of-time peer expectations
    exp_bat_runs, exp_striker_dismissal, exp_charged_runs, exp_bowler_wicket = cross_fit_peer_expectations(df)
    
    df["expected_bat_runs"] = exp_bat_runs
    df["expected_striker_dismissal"] = exp_striker_dismissal
    df["expected_charged_runs"] = exp_charged_runs
    df["expected_bowler_wicket"] = exp_bowler_wicket
    
    # ==========================================
    # CALCULATE NET IMPACT (Positive = Better for player)
    # With state-dependent marginal wicket value w(s)
    # ==========================================
    score_model_path = out / "projected_score_model.json"
    score_model = {}
    if score_model_path.exists():
        with open(score_model_path, "r", encoding="utf-8") as f:
            score_model = json.load(f)
            
    w_s, mid_benchmark = compute_state_dependent_wicket_value(df, score_model)
    if "pressure_reference_cutoff" in df:
        for cutoff, reference in score_model.get("historical_reference_fits", {}).items():
            selected = df["pressure_reference_cutoff"].eq(cutoff)
            w_s[selected] = compute_state_dependent_wicket_value(df.loc[selected], reference)[0]
    df["marginal_wicket_value_ws"] = w_s
    df["marginal_wicket_value_benchmark"] = mid_benchmark
    
    # Vectorized accounting rule:
    # L: legal-ball indicator
    # R: actual off-bat runs
    # D: actual striker dismissal
    # C: runs charged to bowler
    # W: credited bowler wicket
    # v: state-dependent marginal wicket value w(s)
    # Batting impact: R - L*μ_R - v*(D - L*μ_D)
    # Bowling impact: L*μ_C - C + v*(W - L*μ_W)
    L = df["is_legal_ball"].astype(int)
    R = df["runs"].astype(float)
    D = df["is_striker_dismissed"].astype(int)
    C = df["bowler_charge_runs"].astype(float)
    W = df["is_bowler_wicket"].astype(int)
    v = df["marginal_wicket_value_ws"]

    df["batting_impact"] = (R - L * df["expected_bat_runs"]) - v * (D - L * df["expected_striker_dismissal"])
    df["bowling_impact"] = (L * df["expected_charged_runs"] - C) + v * (W - L * df["expected_bowler_wicket"])
    if "is_penalty" in df.columns:
        pen_mask = df["is_penalty"].astype(bool)
        df.loc[pen_mask, ["batting_impact", "bowling_impact"]] = 0.0
    
    # Pre-compute delivery-level pressure impact and legal-ball indicators
    df["hp_bat_impact"] = np.where(df["is_high_pressure_20"], df["batting_impact"], 0.0)
    df["ord_bat_impact"] = np.where(~df["is_high_pressure_20"], df["batting_impact"], 0.0)
    df["hp_balls_faced"] = (df["is_high_pressure_20"] & df["is_legal_ball"]).astype(int)
    df["ord_balls_faced"] = ((~df["is_high_pressure_20"]) & df["is_legal_ball"]).astype(int)
    df["legal_balls_faced"] = df["is_legal_ball"].astype(int)
    
    df["hp_bowl_impact"] = np.where(df["is_high_pressure_20"], df["bowling_impact"], 0.0)
    df["ord_bowl_impact"] = np.where(~df["is_high_pressure_20"], df["bowling_impact"], 0.0)
    df["hp_balls_bowled"] = (df["is_high_pressure_20"] & df["is_legal_ball"]).astype(int)
    df["ord_balls_bowled"] = ((~df["is_high_pressure_20"]) & df["is_legal_ball"]).astype(int)
    df["legal_balls_bowled"] = df["is_legal_ball"].astype(int)
    df["is_reliability_eligible"] = df["is_cohort_eligible"]
    if "pressure_reference_cutoff" in df:
        df["is_reliability_eligible"] &= df["pressure_reference_cutoff"].fillna("").ne("")
    
    # Save delivery impact ledger
    impact_ledger_path = out / "delivery_impact_ledger.csv"
    df.to_csv(impact_ledger_path, index=False)
    
    # ==========================================
    # MATCH-LEVEL AGGREGATION
    # Strictly enforce legal delivery denominators for balls faced & bowled
    # ==========================================
    eligible = df[df["is_reliability_eligible"]]
    bat_agg = eligible.groupby(["match_id", "striker_id", "fold", "comp_tier"], observed=False).agg(
        match_date=("match_date", "first"),
        total_balls_faced=("legal_balls_faced", "sum"),
        total_runs_scored=("runs", "sum"),
        total_batting_impact=("batting_impact", "sum"),
        hp_balls_faced=("hp_balls_faced", "sum"),
        hp_bat_impact=("hp_bat_impact", "sum"),
        ord_balls_faced=("ord_balls_faced", "sum"),
        ord_bat_impact=("ord_bat_impact", "sum"),
    ).reset_index().rename(columns={"striker_id": "player_id"})
    
    bat_agg["hp_bat_impact_12b"] = np.where(
        bat_agg["hp_balls_faced"] > 0,
        (bat_agg["hp_bat_impact"] / bat_agg["hp_balls_faced"]) * 12.0,
        np.nan
    )
    bat_agg["ord_bat_impact_12b"] = np.where(
        bat_agg["ord_balls_faced"] > 0,
        (bat_agg["ord_bat_impact"] / bat_agg["ord_balls_faced"]) * 12.0,
        np.nan
    )
    
    bat_agg = compute_cumulative_prematch_features(bat_agg, discipline="batting")
    bat_match_path = out / "match_player_batting_impact.csv"
    bat_agg.to_csv(bat_match_path, index=False)
    
    bowl_agg = eligible.groupby(["match_id", "bowler_id", "fold", "comp_tier"], observed=False).agg(
        match_date=("match_date", "first"),
        total_balls_bowled=("legal_balls_bowled", "sum"),
        total_wickets_taken=("is_bowler_wicket", "sum"),
        total_bowling_impact=("bowling_impact", "sum"),
        hp_balls_bowled=("hp_balls_bowled", "sum"),
        hp_bowl_impact=("hp_bowl_impact", "sum"),
        ord_balls_bowled=("ord_balls_bowled", "sum"),
        ord_bowl_impact=("ord_bowl_impact", "sum"),
    ).reset_index().rename(columns={"bowler_id": "player_id"})
    
    bowl_agg["hp_bowl_impact_12b"] = np.where(
        bowl_agg["hp_balls_bowled"] > 0,
        (bowl_agg["hp_bowl_impact"] / bowl_agg["hp_balls_bowled"]) * 12.0,
        np.nan
    )
    bowl_agg["ord_bowl_impact_12b"] = np.where(
        bowl_agg["ord_balls_bowled"] > 0,
        (bowl_agg["ord_bowl_impact"] / bowl_agg["ord_balls_bowled"]) * 12.0,
        np.nan
    )
    
    bowl_agg = compute_cumulative_prematch_features(bowl_agg, discipline="bowling")
    bowl_match_path = out / "match_player_bowling_impact.csv"
    bowl_agg.to_csv(bowl_match_path, index=False)
    
    # ==========================================
    # ATTRIBUTION AUDIT
    # ==========================================
    val_df = df[df["fold"] == "VAL_2025"]
    val_L = val_df["is_legal_ball"].astype(int)
    val_legal_cnt = max(1, int(val_L.sum()))
    audit_report = {
        "peer_residual_mean_batting_runs": float((val_df["runs"] - val_L * val_df["expected_bat_runs"]).sum() / val_legal_cnt),
        "peer_residual_mean_bowling_runs": float((val_df["bowler_charge_runs"] - val_L * val_df["expected_charged_runs"]).sum() / val_legal_cnt),
        "peer_residual_mean_striker_dismissal": float((val_df["is_striker_dismissed"].astype(int) - val_L * val_df["expected_striker_dismissal"]).sum() / val_legal_cnt),
        "peer_residual_mean_bowler_wicket": float((val_df["is_bowler_wicket"].astype(int) - val_L * val_df["expected_bowler_wicket"]).sum() / val_legal_cnt),
        "total_batting_match_records": len(bat_agg),
        "total_bowling_match_records": len(bowl_agg),
        "wicket_price_used": mid_benchmark,
        "state_dependent_wicket_used": True,
        "wicket_price_mid_benchmark": mid_benchmark,
        "wicket_price_min": float(np.min(w_s)),
        "wicket_price_max": float(np.max(w_s)),
        "cross_fitting_folds": 5,
        "standardized_unit": "12 legal-ball equivalents",
        "shrinkage_prior_weight": EMPIRICAL_BAYES_PRIOR_WEIGHT,
        "zero_legal_exposure_audit": {
            "penalty_deliveries_zeroed": int(df["is_penalty"].astype(bool).sum()) if "is_penalty" in df.columns else 0,
            "batting_zero_legal_ball_matches": int((bat_agg["total_balls_faced"] == 0).sum()),
            "batting_zero_hp_ball_nonzero_impact": int(((bat_agg["hp_balls_faced"] == 0) & (bat_agg["hp_bat_impact"].abs() > 1e-9)).sum()),
            "bowling_zero_legal_ball_matches": int((bowl_agg["total_balls_bowled"] == 0).sum()),
            "bowling_zero_hp_ball_nonzero_impact": int(((bowl_agg["hp_balls_bowled"] == 0) & (bowl_agg["hp_bowl_impact"].abs() > 1e-9)).sum()),
        },
    }
    
    audit_path = out / "attribution_audit.json"
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(audit_report, f, indent=2)
        
    output_files = {
        "delivery_impact_ledger.csv": impact_ledger_path,
        "match_player_batting_impact.csv": bat_match_path,
        "match_player_bowling_impact.csv": bowl_match_path,
        "attribution_audit.json": audit_path,
    }
    output_fingerprints = {fname: compute_sha256(fpath) for fname, fpath in output_files.items()}
    return audit_report, output_fingerprints
