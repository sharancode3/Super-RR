"""Stage 06: Pre-Ball Leverage and Pressure Classification Module."""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from rr_pressure.config import PipelineConfig
from rr_pressure.manifest import compute_sha256


def fit_transition_outcome_frequencies(train_df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """Learn empirical transition outcome probabilities from historical training deliveries."""
    dots = (train_df["runs"] == 0) & (~train_df["is_wicket"])
    ones = (train_df["runs"] == 1) & (~train_df["is_wicket"])
    twos = (train_df["runs"] == 2) & (~train_df["is_wicket"])
    fours = (train_df["runs"] == 4) & (~train_df["is_wicket"])
    sixes = (train_df["runs"] == 6) & (~train_df["is_wicket"])
    wkts = train_df["is_wicket"].astype(bool)
    
    counts = np.array([dots.sum(), ones.sum(), twos.sum(), fours.sum(), sixes.sum(), wkts.sum()], dtype=float)
    p_default = counts / counts.sum()
    
    # On Free Hit: bowler cannot credit wickets; only run-outs possible (~0.5%)
    p_fh = p_default.copy()
    p_fh[-1] = 0.005
    p_fh[:-1] += (p_default[-1] - 0.005) * (p_default[:-1] / p_default[:-1].sum())
    
    metadata = {
        "training_counts": {
            "dot": int(counts[0]),
            "one": int(counts[1]),
            "two": int(counts[2]),
            "four": int(counts[3]),
            "six": int(counts[4]),
            "wicket": int(counts[5]),
        },
        "probabilities_default": p_default.tolist(),
        "probabilities_free_hit": p_fh.tolist(),
    }
    return p_default, p_fh, metadata


def p_win_chase_state(
    b_rem: np.ndarray | float,
    w_rem: np.ndarray | float,
    req_gap: np.ndarray | float,
    curr_runs: np.ndarray | float,
    leg_b: np.ndarray | float,
    ipl_flag: np.ndarray | float,
    coef: np.ndarray,
    intercept: float,
    tie_value: float = 0.50,
) -> np.ndarray | float:
    """Evaluate 2nd-innings chase win probability with exact terminal state resolution."""
    b = np.maximum(0, b_rem) / 120.0
    w = np.maximum(0, w_rem) / 10.0
    req = req_gap / 100.0
    rrr = np.clip(req_gap / (np.maximum(0, b_rem) / 6.0 + 0.1), -10.0, 36.0)
    crr = curr_runs / (leg_b + 1.0) * 6.0
    z = b * coef[0] + w * coef[1] + req * coef[2] + rrr * coef[3] + crr * coef[4] + ipl_flag * coef[5] + intercept
    p_log = 1.0 / (1.0 + np.exp(-np.clip(z, -15, 15)))
    # Terminal precedence:
    # 1. Target reached (req_gap <= 0): batting win = 1.0 (even if balls or wickets exhausted on same ball)
    # 2. Innings complete by balls or wickets and scores level (req_gap == 1): regulation tie = tie_value (0.50)
    # 3. Innings complete below level score (req_gap > 1): batting loss = 0.0
    # 4. Otherwise: pre-ball logistic model probability
    is_win = req_gap <= 0
    is_complete = (w_rem <= 0) | (b_rem <= 0)
    is_tie = is_complete & (req_gap == 1)
    is_loss = is_complete & (req_gap > 1)

    return np.where(
        is_win,
        1.0,
        np.where(
            is_tie,
            float(tie_value),
            np.where(
                is_loss,
                0.0,
                p_log,
            ),
        ),
    )


def compute_chase_leverage(
    df_chase: pd.DataFrame,
    coef: np.ndarray,
    intercept: float,
    p_default: np.ndarray,
    p_fh: np.ndarray,
    tie_value: float = 0.50,
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute pre-ball leverage and pursuit stress for 2nd innings chases with exact terminal states."""
    b_cur = df_chase["pre_balls_remaining"].values
    w_cur = df_chase["pre_wickets_in_hand"].values
    req_col = "pre_target_reconciled_gap" if "pre_target_reconciled_gap" in df_chase.columns else "pre_target_offbat_gap"
    runs_col = "pre_team_total_runs" if "pre_team_total_runs" in df_chase.columns else "pre_team_offbat_runs"
    req_cur = df_chase[req_col].values
    runs_cur = df_chase[runs_col].values
    leg_cur = df_chase["pre_legal_balls"].values
    ipl_cur = (df_chase["comp_tier"] == "IPL").astype(float).values
    is_fh = df_chase["pre_free_hit"].values.astype(bool)

    # Successor state probabilities (legal ball branches with terminal state overrides)
    q_dot = p_win_chase_state(b_cur - 1, w_cur, req_cur, runs_cur, leg_cur + 1, ipl_cur, coef, intercept, tie_value)
    q_1   = p_win_chase_state(b_cur - 1, w_cur, req_cur - 1, runs_cur + 1, leg_cur + 1, ipl_cur, coef, intercept, tie_value)
    q_2   = p_win_chase_state(b_cur - 1, w_cur, req_cur - 2, runs_cur + 2, leg_cur + 1, ipl_cur, coef, intercept, tie_value)
    q_4   = p_win_chase_state(b_cur - 1, w_cur, req_cur - 4, runs_cur + 4, leg_cur + 1, ipl_cur, coef, intercept, tie_value)
    q_6   = p_win_chase_state(b_cur - 1, w_cur, req_cur - 6, runs_cur + 6, leg_cur + 1, ipl_cur, coef, intercept, tie_value)
    q_wkt = p_win_chase_state(b_cur - 1, w_cur - 1, req_cur, runs_cur, leg_cur + 1, ipl_cur, coef, intercept, tie_value)

    q_stack = np.column_stack([q_dot, q_1, q_2, q_4, q_6, q_wkt])
    
    # Vectorized leverage calculation with learned transition probabilities
    q_bar = np.dot(q_stack, p_default)
    leverage = np.dot(np.abs(q_stack - q_bar[:, None]), p_default)
    
    if is_fh.any():
        q_bar_fh = np.dot(q_stack[is_fh], p_fh)
        leverage[is_fh] = np.dot(np.abs(q_stack[is_fh] - q_bar_fh[:, None]), p_fh)

    # Pursuit stress score
    rrr_unclipped = req_cur / (np.maximum(1, b_cur) / 6.0)
    stress = np.clip((rrr_unclipped - 6.0) / 6.0 + (10 - w_cur) / 10.0, 0.0, 3.0)
    return leverage, stress


def compute_inn1_leverage(
    df_inn1: pd.DataFrame,
    coef: np.ndarray,
    intercept: float,
    p_default: np.ndarray,
    p_fh: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute pre-ball leverage and resource stress for 1st innings setting total."""
    def p_win(b_rem, w_rem, curr_runs, leg_b, ipl_flag):
        b = np.maximum(0, b_rem) / 120.0
        w = np.maximum(0, w_rem) / 10.0
        runs = curr_runs / 150.0
        crr = curr_runs / (leg_b + 1.0) * 6.0
        bw = b * w
        z = b * coef[0] + w * coef[1] + runs * coef[2] + crr * coef[3] + bw * coef[4] + ipl_flag * coef[5] + intercept
        return 1.0 / (1.0 + np.exp(-np.clip(z, -15, 15)))

    b_cur = df_inn1["pre_balls_remaining"].values
    w_cur = df_inn1["pre_wickets_in_hand"].values
    runs_col = "pre_team_total_runs" if "pre_team_total_runs" in df_inn1.columns else "pre_team_offbat_runs"
    runs_cur = df_inn1[runs_col].values
    leg_cur = df_inn1["pre_legal_balls"].values
    ipl_cur = (df_inn1["comp_tier"] == "IPL").astype(float).values
    is_fh = df_inn1["pre_free_hit"].values.astype(bool)

    q_dot = p_win(b_cur - 1, w_cur, runs_cur, leg_cur + 1, ipl_cur)
    q_1   = p_win(b_cur - 1, w_cur, runs_cur + 1, leg_cur + 1, ipl_cur)
    q_2   = p_win(b_cur - 1, w_cur, runs_cur + 2, leg_cur + 1, ipl_cur)
    q_4   = p_win(b_cur - 1, w_cur, runs_cur + 4, leg_cur + 1, ipl_cur)
    q_6   = p_win(b_cur - 1, w_cur, runs_cur + 6, leg_cur + 1, ipl_cur)
    q_wkt = p_win(b_cur - 1, w_cur - 1, runs_cur, leg_cur + 1, ipl_cur)

    q_stack = np.column_stack([q_dot, q_1, q_2, q_4, q_6, q_wkt])
    
    q_bar = np.dot(q_stack, p_default)
    leverage = np.dot(np.abs(q_stack - q_bar[:, None]), p_default)
    
    if is_fh.any():
        q_bar_fh = np.dot(q_stack[is_fh], p_fh)
        leverage[is_fh] = np.dot(np.abs(q_stack[is_fh] - q_bar_fh[:, None]), p_fh)

    # Resource stress score
    wkts_lost = 10 - w_cur
    stress = np.clip(wkts_lost / 5.0 + (120 - b_cur) / 120.0, 0.0, 3.0)
    return leverage, stress


def _score_pressure_states(rows: pd.DataFrame, weights: dict, p_default: np.ndarray, p_fh: np.ndarray) -> pd.DataFrame:
    scores = pd.DataFrame(0.0, index=rows.index, columns=["pre_ball_leverage", "pre_ball_stress"])
    for innings, scorer in ((1, compute_inn1_leverage), (2, compute_chase_leverage)):
        sample = rows[rows["innings"] == innings]
        if not sample.empty:
            leverage, stress = scorer(
                sample, np.asarray(weights[f"inn{innings}_logistic_coef"][0]),
                weights[f"inn{innings}_logistic_intercept"][0], p_default, p_fh,
            )
            scores.loc[sample.index, "pre_ball_leverage"] = leverage
            scores.loc[sample.index, "pre_ball_stress"] = stress
    return scores


def _apply_pressure_reference(df: pd.DataFrame, rows: pd.Series, history: pd.Series, weights: dict) -> dict:
    p_default, p_fh, frequency_metadata = fit_transition_outcome_frequencies(df.loc[history])
    reference = _score_pressure_states(df.loc[history], weights, p_default, p_fh)
    scores = _score_pressure_states(df.loc[rows], weights, p_default, p_fh)

    first = reference.loc[df.loc[history, "innings"].eq(1)]
    stress_std = first["pre_ball_stress"].std(ddof=0)
    if stress_std > 0:
        scale = 0.5 * first["pre_ball_leverage"].std(ddof=0) / stress_std
        median = first["pre_ball_stress"].median()
        for values in (reference, scores):
            innings_one = df.loc[values.index, "innings"].eq(1)
            values.loc[innings_one, "pre_ball_leverage"] = (
                values.loc[innings_one, "pre_ball_leverage"] +
                scale * (values.loc[innings_one, "pre_ball_stress"] - median)
            ).clip(lower=0)

    df.loc[rows, scores.columns] = scores
    metadata = {"transition_frequencies": frequency_metadata}
    for (innings, tier), group in df.loc[history].groupby(["innings", "comp_tier"]):
        levels = dict(zip(("p75", "p80", "p85"), np.percentile(reference.loc[group.index, "pre_ball_leverage"], [75, 80, 85]).tolist()))
        metadata[f"inn_{innings}_{tier}"] = levels
        applicable = rows & df["is_cohort_eligible"] & df["innings"].eq(innings) & df["comp_tier"].eq(tier)
        for share, quantile in ((20, "p80"), (15, "p85"), (25, "p75")):
            df.loc[applicable, f"is_high_pressure_{share}"] = df.loc[applicable, "pre_ball_leverage"].ge(levels[quantile])
    return metadata


def run_stage06_pressure(config: PipelineConfig) -> Tuple[Dict[str, Any], Dict[str, str]]:
    out = config.out_dir
    out.mkdir(parents=True, exist_ok=True)
    
    df = pd.read_csv(out / "delivery_ledger_proxy.csv", low_memory=False)
    folds = pd.read_csv(out / "fold_assignments.csv")
    df = df.merge(folds[["match_id", "fold"]], on="match_id", how="left")
    
    with open(out / "match_state_models.json", "r", encoding="utf-8") as f:
        weights = json.load(f)
        
    train_mask = df["fold"].eq("TRAIN_2022_2024") & df["is_cohort_eligible"]
    df["pre_ball_leverage"] = 0.0
    df["pre_ball_stress"] = 0.0
    df["pressure_reference_cutoff"] = ""
    for share in (15, 20, 25):
        df[f"is_high_pressure_{share}"] = False

    historical = weights.get("historical_reference_fits", {})
    pre2025_cutoffs = [c for c in sorted(historical) if c < "2025-01-01"]
    reference_metadata = {}
    for cutoff, next_cutoff in zip(pre2025_cutoffs, [*pre2025_cutoffs[1:], "2025-01-01"]):
        rows = df["match_date"].ge(cutoff) & df["match_date"].lt(next_cutoff)
        earlier = train_mask & df["match_date"].lt(cutoff)
        reference_metadata[cutoff] = _apply_pressure_reference(df, rows, earlier, historical[cutoff])
        df.loc[rows, "pressure_reference_cutoff"] = cutoff

    rows_2025 = (df["match_date"].ge("2025-01-01") & df["match_date"].lt("2026-01-01")) if (pre2025_cutoffs or "2026-01-01" in historical) else pd.Series(True, index=df.index)
    thresholds_json = _apply_pressure_reference(df, rows_2025, train_mask, weights)
    df.loc[rows_2025, "pressure_reference_cutoff"] = "2025-01-01"

    if "2026-01-01" in historical:
        rows_2026 = df["match_date"].ge("2026-01-01")
        earlier_2026 = df["is_cohort_eligible"] & df["match_date"].lt("2026-01-01")
        reference_metadata["2026-01-01"] = _apply_pressure_reference(df, rows_2026, earlier_2026, historical["2026-01-01"])
        df.loc[rows_2026, "pressure_reference_cutoff"] = "2026-01-01"
    else:
        rows_2026 = df["match_date"].ge("2026-01-01")
        _apply_pressure_reference(df, rows_2026, train_mask, weights)
        df.loc[rows_2026, "pressure_reference_cutoff"] = "2025-01-01"
    thresholds_json["historical_reference_fits"] = reference_metadata

    # Audit impact of reconciled total runs & targets vs legacy offbat proxy
    if "pre_target_reconciled_gap" in df.columns and "pre_target_offbat_gap" in df.columns:
        df_proxy = df.copy()
        df_proxy["pre_target_reconciled_gap"] = df_proxy["pre_target_offbat_gap"]
        df_proxy["pre_team_total_runs"] = df_proxy["pre_team_offbat_runs"]
        for cutoff, next_cutoff in zip(pre2025_cutoffs, [*pre2025_cutoffs[1:], "2025-01-01"]):
            rows_p = df_proxy["match_date"].ge(cutoff) & df_proxy["match_date"].lt(next_cutoff)
            earlier_p = train_mask & df_proxy["match_date"].lt(cutoff)
            _apply_pressure_reference(df_proxy, rows_p, earlier_p, historical[cutoff])
        _apply_pressure_reference(df_proxy, rows_2025, train_mask, weights)
        if "2026-01-01" in historical:
            _apply_pressure_reference(df_proxy, rows_2026, df_proxy["is_cohort_eligible"] & df_proxy["match_date"].lt("2026-01-01"), historical["2026-01-01"])

        m30057_mask = (df["match_id"] == 30057) & (df["innings"] == 2)
        thresholds_json["reconciliation_sensitivity_audit"] = {
            "total_hp20_labels_changed": int((df["is_high_pressure_20"] != df_proxy["is_high_pressure_20"]).sum()),
            "total_deliveries_leverage_changed": int((np.abs(df["pre_ball_leverage"] - df_proxy["pre_ball_leverage"]) > 1e-9).sum()),
            "fixture_30057_inn2": {
                "reconciled_target": float(df.loc[m30057_mask, "target_runs_reconciled"].iloc[0]) if m30057_mask.any() else None,
                "proxy_mean_leverage": float(df_proxy.loc[m30057_mask, "pre_ball_leverage"].mean()) if m30057_mask.any() else None,
                "reconciled_mean_leverage": float(df.loc[m30057_mask, "pre_ball_leverage"].mean()) if m30057_mask.any() else None,
                "proxy_hp20_count": int(df_proxy.loc[m30057_mask, "is_high_pressure_20"].sum()) if m30057_mask.any() else 0,
                "reconciled_hp20_count": int(df.loc[m30057_mask, "is_high_pressure_20"].sum()) if m30057_mask.any() else 0,
            }
        }

    # Audit chase terminal tie sensitivity, wide/noball/3-run expansion, and proxy +/-3 target uncertainty
    elig_inn2 = df[(df["innings"] == 2) & df["is_cohort_eligible"]].copy()
    if not elig_inn2.empty:
        p_def_tr, p_fh_tr, _ = fit_transition_outcome_frequencies(df[train_mask])
        coef_25 = np.asarray(weights["inn2_logistic_coef"][0])
        int_25 = float(weights["inn2_logistic_intercept"][0])
        lev_t05, _ = compute_chase_leverage(elig_inn2, coef_25, int_25, p_def_tr, p_fh_tr, tie_value=0.50)
        lev_t00, _ = compute_chase_leverage(elig_inn2, coef_25, int_25, p_def_tr, p_fh_tr, tie_value=0.00)
        lev_t10, _ = compute_chase_leverage(elig_inn2, coef_25, int_25, p_def_tr, p_fh_tr, tie_value=1.00)

        # Expanded 9-outcome chase leverage including legal 3s, wides, and no-balls
        tr_ch = df[train_mask]
        is_w = tr_ch["extras_type"].astype(str).eq("wide")
        is_nb = tr_ch["extras_type"].astype(str).isin(["Overstep", "other"])
        is_leg = (~is_w) & (~is_nb)
        wkt_tr = tr_ch["is_wicket"].astype(bool)
        c9 = np.array([
            (is_leg & (tr_ch["runs"] == 0) & (~wkt_tr)).sum(),
            (is_leg & (tr_ch["runs"] == 1) & (~wkt_tr)).sum(),
            (is_leg & (tr_ch["runs"] == 2) & (~wkt_tr)).sum(),
            (is_leg & (tr_ch["runs"] == 3) & (~wkt_tr)).sum(),
            (is_leg & (tr_ch["runs"] == 4) & (~wkt_tr)).sum(),
            (is_leg & (tr_ch["runs"] == 6) & (~wkt_tr)).sum(),
            (is_leg & wkt_tr).sum(),
            is_w.sum(),
            is_nb.sum(),
        ], dtype=float)
        p9 = c9 / c9.sum() if c9.sum() > 0 else np.ones(9) / 9.0
        b_c = elig_inn2["pre_balls_remaining"].values
        w_c = elig_inn2["pre_wickets_in_hand"].values
        rq_c = elig_inn2["pre_target_reconciled_gap"].values
        rn_c = elig_inn2["pre_team_total_runs"].values
        lg_c = elig_inn2["pre_legal_balls"].values
        ip_c = (elig_inn2["comp_tier"] == "IPL").astype(float).values
        q9 = np.column_stack([
            p_win_chase_state(b_c - 1, w_c, rq_c, rn_c, lg_c + 1, ip_c, coef_25, int_25),
            p_win_chase_state(b_c - 1, w_c, rq_c - 1, rn_c + 1, lg_c + 1, ip_c, coef_25, int_25),
            p_win_chase_state(b_c - 1, w_c, rq_c - 2, rn_c + 2, lg_c + 1, ip_c, coef_25, int_25),
            p_win_chase_state(b_c - 1, w_c, rq_c - 3, rn_c + 3, lg_c + 1, ip_c, coef_25, int_25),
            p_win_chase_state(b_c - 1, w_c, rq_c - 4, rn_c + 4, lg_c + 1, ip_c, coef_25, int_25),
            p_win_chase_state(b_c - 1, w_c, rq_c - 6, rn_c + 6, lg_c + 1, ip_c, coef_25, int_25),
            p_win_chase_state(b_c - 1, w_c - 1, rq_c, rn_c, lg_c + 1, ip_c, coef_25, int_25),
            p_win_chase_state(b_c, w_c, rq_c - 1, rn_c + 1, lg_c, ip_c, coef_25, int_25),
            p_win_chase_state(b_c, w_c, rq_c - 1, rn_c + 1, lg_c, ip_c, coef_25, int_25),
        ])
        lev9 = np.dot(np.abs(q9 - np.dot(q9, p9)[:, None]), p9)

        # Proxy target +/-3 run sensitivity for non-verified chases
        proxy_err = elig_inn2.copy()
        is_px = proxy_err["target_source"].eq("OFFBAT_PLUS_EXTRAS_PROXY").to_numpy()
        proxy_err.loc[is_px, "pre_target_reconciled_gap"] = proxy_err.loc[is_px, "pre_target_reconciled_gap"] + 3.0
        lev_plus3, _ = compute_chase_leverage(proxy_err, coef_25, int_25, p_def_tr, p_fh_tr, tie_value=0.50)

        m50375_last = df[(df["match_id"] == 50375) & (df["innings"] == 2)].tail(1)
        thresholds_json["chase_terminal_and_transition_audit"] = {
            "tie_value_used": 0.50,
            "last_ball_tie_eligible_rows": int(((elig_inn2["pre_balls_remaining"] == 1) & (elig_inn2["pre_target_reconciled_gap"].between(1, 6))).sum()),
            "tie_sensitivity_max_abs_diff_0_vs_05": float(np.max(np.abs(lev_t05 - lev_t00))),
            "tie_sensitivity_max_abs_diff_1_vs_05": float(np.max(np.abs(lev_t10 - lev_t05))),
            "expanded_9class_corr_with_6class": float(np.corrcoef(lev_t05, lev9)[0, 1]),
            "expanded_9class_max_abs_diff": float(np.max(np.abs(lev9 - lev_t05))),
            "proxy_target_plus3_corr": float(np.corrcoef(lev_t05, lev_plus3)[0, 1]),
            "match_50375_last_ball": {
                "pre_balls_remaining": int(m50375_last["pre_balls_remaining"].iloc[0]) if not m50375_last.empty else None,
                "pre_wickets_in_hand": int(m50375_last["pre_wickets_in_hand"].iloc[0]) if not m50375_last.empty else None,
                "pre_target_reconciled_gap": float(m50375_last["pre_target_reconciled_gap"].iloc[0]) if not m50375_last.empty else None,
                "pre_ball_leverage": float(m50375_last["pre_ball_leverage"].iloc[0]) if not m50375_last.empty else None,
                "is_high_pressure_20": bool(m50375_last["is_high_pressure_20"].iloc[0]) if not m50375_last.empty else None,
            },
        }
    
    # Save delivery pressure labels
    labels_path = out / "delivery_pressure_labels.csv"
    df.to_csv(labels_path, index=False)
    
    thresholds_path = out / "pressure_thresholds.json"
    with open(thresholds_path, "w", encoding="utf-8") as f:
        json.dump(thresholds_json, f, indent=2)
        
    # Replay examples
    gap_col = "pre_target_reconciled_gap" if "pre_target_reconciled_gap" in df.columns else "pre_target_offbat_gap"
    tight_chase = df[(df["innings"] == 2) & (df["pre_balls_remaining"].between(6, 18)) & (df["pre_ball_leverage"] > 0.08)].head(2)
    lost_chase = df[(df["innings"] == 2) & (df["pre_balls_remaining"].between(6, 18)) & (df[gap_col] > 40)].head(2)
    easy_chase = df[(df["innings"] == 2) & (df["pre_balls_remaining"] > 24) & (df[gap_col] < 15)].head(2)
    collapse_inn1 = df[(df["innings"] == 1) & (df["pre_legal_balls"] < 36) & (df["pre_team_wickets"] >= 3)].head(2)
    
    def format_examples(subset: pd.DataFrame, scenario: str) -> List[Dict[str, Any]]:
        exs = []
        for _, r in subset.iterrows():
            exs.append({
                "scenario": scenario,
                "match_id": int(r["match_id"]),
                "innings": int(r["innings"]),
                "ball_num": int(r["innings_ball_num"]),
                "over": int(r["pre_over"]),
                "balls_remaining": int(r["pre_balls_remaining"]),
                "wickets_in_hand": int(r["pre_wickets_in_hand"]),
                "target_gap": float(r[gap_col]) if pd.notna(r[gap_col]) else None,
                "target_gap_offbat_proxy": float(r["pre_target_offbat_gap"]) if pd.notna(r["pre_target_offbat_gap"]) else None,
                "pre_ball_leverage": float(r["pre_ball_leverage"]),
                "pre_ball_stress": float(r["pre_ball_stress"]),
                "is_high_pressure_20": bool(r["is_high_pressure_20"]),
            })
        return exs
        
    replay_examples = {
        "tight_late_chase": format_examples(tight_chase, "Tight Late Chase (High Leverage, High Stress)"),
        "virtually_lost_chase": format_examples(lost_chase, "Virtually Lost Chase (Low Leverage, Extreme Stress)"),
        "easy_chase": format_examples(easy_chase, "Easy Chase (Low Leverage, Low Stress)"),
        "first_innings_collapse": format_examples(collapse_inn1, "First Innings Powerplay Collapse (High Stress)"),
    }
    
    replay_path = out / "replay_examples.json"
    with open(replay_path, "w", encoding="utf-8") as f:
        json.dump(replay_examples, f, indent=2)
        
    evidence = {
        "total_deliveries_labeled": len(df),
        "high_pressure_20_count": int(df["is_high_pressure_20"].sum()),
        "high_pressure_20_pct": float(df["is_high_pressure_20"].mean() * 100.0),
        "thresholds_summary": thresholds_json,
    }
    
    output_files = {
        "delivery_pressure_labels.csv": labels_path,
        "pressure_thresholds.json": thresholds_path,
        "replay_examples.json": replay_path,
    }
    output_fingerprints = {fname: compute_sha256(fpath) for fname, fpath in output_files.items()}
    return evidence, output_fingerprints
