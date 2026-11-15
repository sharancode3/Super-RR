"""Stage 01: Ingestion and identity reconciliation module."""

import json
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd

from rr_pressure.config import PipelineConfig
from rr_pressure.manifest import compute_sha256
from rr_pressure.progress import record_stage, get_default_progress_path


def classify_competition_tier(comp_name: str, match_format: str) -> str:
    name_upper = str(comp_name).upper()
    if "IPL" in name_upper or "INDIAN PREMIER LEAGUE" in name_upper:
        return "IPL"
    elif match_format == "T20I":
        return "T20I"
    elif "EMERGING" in name_upper or "RISING STARS" in name_upper:
        return "EMERGING"
    else:
        return "OTHER"


def derive_player_roles(
    bbb: pd.DataFrame,
    p11: pd.DataFrame,
    all_player_ids: pd.Series,
    mapping: pd.DataFrame,
    valid_match_ids: Any = None,
) -> pd.DataFrame:
    """Derive player roles from historical batting order, overs bowled, and fielding attributes.
    
    If valid_match_ids is specified, only deliveries and lineups from those matches are used,
    preventing future match information from leaking into historical role classifications.
    """
    if valid_match_ids is not None:
        bbb_sub = bbb[bbb["match_id"].isin(valid_match_ids)]
        p11_sub = p11[p11["match_id"].isin(valid_match_ids)]
    else:
        bbb_sub = bbb
        p11_sub = p11

    # Batting statistics (distinct legal balls faced excludes wides)
    bbb_sub = bbb_sub.copy()
    bbb_sub["is_legal_bat_ball"] = bbb_sub["extras_type"] != "wide"

    bat_innings = bbb_sub.groupby("striker_id")["match_id"].nunique().rename("batting_innings")
    top7_inn = bbb_sub[bbb_sub["batting_order"] <= 7].groupby("striker_id")["match_id"].nunique().rename("top7_innings")
    tail_inn = bbb_sub[bbb_sub["batting_order"] >= 8].groupby("striker_id")["match_id"].nunique().rename("tail_innings")
    pp_bat = bbb_sub[bbb_sub["overid"] <= 6].groupby("striker_id").size().rename("pp_bat_balls")
    mid_bat = bbb_sub[(bbb_sub["overid"] >= 7) & (bbb_sub["overid"] <= 15)].groupby("striker_id").size().rename("mid_bat_balls")
    death_bat = bbb_sub[bbb_sub["overid"] >= 16].groupby("striker_id").size().rename("death_bat_balls")
    legal_bat_balls = bbb_sub[bbb_sub["is_legal_bat_ball"]].groupby("striker_id").size().rename("legal_balls_faced")

    # Recent batting position share (up to last 12 batting appearances strictly in this slice)
    order_cols = ["striker_id", "match_date", "match_id"] if "match_date" in bbb_sub.columns else ["striker_id", "match_id"]
    bat_app = bbb_sub[["striker_id", "match_id", "batting_order"] + (["match_date"] if "match_date" in bbb_sub.columns else [])].drop_duplicates(
        subset=["striker_id", "match_id"]
    ).sort_values(order_cols)
    last12_bat = bat_app.groupby("striker_id", sort=False).tail(12)
    recent_bat_inn = last12_bat.groupby("striker_id")["match_id"].nunique().rename("recent_batting_innings")
    recent_top7_inn = last12_bat[last12_bat["batting_order"] <= 7].groupby("striker_id")["match_id"].nunique().rename("recent_top7_innings")

    bat_stats = bbb_sub.groupby("striker_id").agg(
        career_balls_faced=("runs", "count"),
        career_runs_scored=("runs", "sum"),
        avg_bat_order=("batting_order", "mean"),
    ).join([bat_innings, top7_inn, tail_inn, pp_bat, mid_bat, death_bat, legal_bat_balls, recent_bat_inn, recent_top7_inn]).fillna({
        "top7_innings": 0, "tail_innings": 0, "batting_innings": 0,
        "pp_bat_balls": 0, "mid_bat_balls": 0, "death_bat_balls": 0,
        "legal_balls_faced": 0, "recent_batting_innings": 0, "recent_top7_innings": 0,
    })
    
    # Bowling statistics
    # Wickets credited to bowler (exclude run-outs)
    bowler_wickets = bbb_sub[
        (bbb_sub["is_wicket"] == 1) & (~bbb_sub["dismissal_type"].isin(["run out", "retired hurt", "retired out", "handled the ball", "obstructing the field"]))
    ].groupby("bowler_id").size().rename("career_wickets_taken")
    
    # Legal balls bowled
    illegal_extras = {"wide", "Overstep", "Penalty", "other"}
    legal_mask = ~bbb_sub["extras_type"].isin(illegal_extras)
    legal_balls = bbb_sub[legal_mask].groupby("bowler_id").size().rename("legal_balls_bowled")
    yorkers = bbb_sub[bbb_sub["delivery_style"] == "Yorker"].groupby("bowler_id").size().rename("yorker_balls")
    
    bowl_matches = bbb_sub.groupby("bowler_id")["match_id"].nunique().rename("bowling_matches")
    pp_balls = bbb_sub[bbb_sub["overid"] <= 6].groupby("bowler_id").size().rename("pp_bowling_balls")
    mid_balls = bbb_sub[(bbb_sub["overid"] >= 7) & (bbb_sub["overid"] <= 15)].groupby("bowler_id").size().rename("mid_bowling_balls")
    death_balls = bbb_sub[bbb_sub["overid"] >= 16].groupby("bowler_id").size().rename("death_bowling_balls")
    
    bowl_stats = bbb_sub.groupby("bowler_id").agg(
        career_balls_bowled=("runs", "count"),
        bowler_type=("pace_or_spin", lambda s: s.mode()[0] if len(s.mode()) > 0 and pd.notna(s.mode()[0]) else "Unknown"),
        bowling_type=("bowling_type", lambda s: s.mode()[0] if len(s.mode()) > 0 and pd.notna(s.mode()[0]) else "Unknown"),
    ).join([bowler_wickets, bowl_matches, legal_balls, yorkers, pp_balls, mid_balls, death_balls]).fillna({
        "career_wickets_taken": 0, "bowling_matches": 0, "legal_balls_bowled": 0, "yorker_balls": 0,
        "pp_bowling_balls": 0, "mid_bowling_balls": 0, "death_bowling_balls": 0
    })
    
    # Keeper & Captain flags
    wk_ids = set(p11_sub[p11_sub["is_wk"] == True]["player_id"].unique())
    capt_ids = set(p11_sub[p11_sub["is_captain"] == True]["player_id"].unique())
    impact_ids = set(p11_sub[p11_sub["is_impact"] == 1]["player_id"].unique())
    
    # Player canonical names
    player_names = mapping.groupby("player_id")["player_name"].first()
    
    df = pd.DataFrame({"player_id": all_player_ids.unique()}).set_index("player_id")
    df = df.join(player_names).join(bat_stats).join(bowl_stats)
    
    df["career_balls_faced"] = df["career_balls_faced"].fillna(0).astype(int)
    df["legal_balls_faced"] = df["legal_balls_faced"].fillna(0).astype(int)
    df["career_runs_scored"] = df["career_runs_scored"].fillna(0).astype(int)
    df["career_balls_bowled"] = df["career_balls_bowled"].fillna(0).astype(int)
    df["legal_balls_bowled"] = df["legal_balls_bowled"].fillna(0).astype(int)
    df["yorker_balls"] = df["yorker_balls"].fillna(0).astype(int)
    df["career_wickets_taken"] = df["career_wickets_taken"].fillna(0).astype(int)
    df["batting_innings"] = df["batting_innings"].fillna(0).astype(int)
    df["top7_innings"] = df["top7_innings"].fillna(0).astype(int)
    df["tail_innings"] = df["tail_innings"].fillna(0).astype(int)
    df["recent_batting_innings"] = df["recent_batting_innings"].fillna(0).astype(int)
    df["recent_top7_innings"] = df["recent_top7_innings"].fillna(0).astype(int)
    df["pp_bat_balls"] = df["pp_bat_balls"].fillna(0).astype(int)
    df["mid_bat_balls"] = df["mid_bat_balls"].fillna(0).astype(int)
    df["death_bat_balls"] = df["death_bat_balls"].fillna(0).astype(int)
    df["bowling_matches"] = df["bowling_matches"].fillna(0).astype(int)
    df["pp_bowling_balls"] = df["pp_bowling_balls"].fillna(0).astype(int)
    df["mid_bowling_balls"] = df["mid_bowling_balls"].fillna(0).astype(int)
    df["death_bowling_balls"] = df["death_bowling_balls"].fillna(0).astype(int)
    df["avg_bat_order"] = df["avg_bat_order"].fillna(99.0)
    df["bowler_type"] = df["bowler_type"].fillna("Unknown")
    df["bowling_type"] = df["bowling_type"].fillna("Unknown")
    df["top7_share"] = np.where(df["batting_innings"] > 0, df["top7_innings"] / df["batting_innings"], 0.0)
    df["recent_top7_share"] = np.where(df["recent_batting_innings"] > 0, df["recent_top7_innings"] / df["recent_batting_innings"], 0.0)
    df["overs_per_bowling_match"] = np.where(df["bowling_matches"] > 0, (df["legal_balls_bowled"] / 6.0) / df["bowling_matches"], 0.0)
    df["is_wk"] = df.index.isin(wk_ids)
    df["is_captain"] = df.index.isin(capt_ids)
    df["is_impact"] = df.index.isin(impact_ids)
    
    # Explicit sustained discipline role support (adapts minimum count only for early tiny warmup windows)
    n_matches_slice = int(bbb_sub["match_id"].nunique())
    min_top7_req = 3 if n_matches_slice < 120 else 5
    min_bat_balls_req = 30 if n_matches_slice < 120 else 60
    min_bowl_matches_req = 3 if n_matches_slice < 120 else 5
    min_bowl_balls_req = 36 if n_matches_slice < 120 else 60

    df["batting_role_supported"] = (
        (
            (df["top7_innings"] >= min_top7_req)
            & (df["top7_share"] >= 0.50)
            & (df["recent_top7_share"] >= 0.50)
            & (df["avg_bat_order"] <= 7.5)
            & (df["legal_balls_faced"] >= min_bat_balls_req)
        )
        | (df["is_wk"] & (df["top7_innings"] >= 3) & (df["top7_share"] >= 0.50) & (df["legal_balls_faced"] >= 20))
    )
    
    df["bowling_role_supported"] = (
        (df["bowling_matches"] >= min_bowl_matches_req)
        & (df["legal_balls_bowled"] >= min_bowl_balls_req)
        & (df["overs_per_bowling_match"] >= 1.85)
    )
    
    # Role assignment and presentation logic strictly grounded in direct evidence
    roles = []
    bat_display_roles = []
    bowl_display_roles = []
    
    for pid, r in df.iterrows():
        bf = r["career_balls_faced"]
        bb = r["career_balls_bowled"]
        order = r["avg_bat_order"]
        btype = r["bowler_type"]
        b_style = str(r["bowling_type"])
        is_wk = r["is_wk"]
        bat_sup = bool(r["batting_role_supported"])
        bowl_sup = bool(r["bowling_role_supported"])
        
        # Debuts / unobserved players in this historical slice
        if bf == 0 and bb == 0:
            role = "UNKNOWN_DEBUT"
        elif is_wk and bat_sup:
            role = "WK_BATTER"
        elif bat_sup and bowl_sup:
            if btype == "Spin":
                role = "SPIN_ALLROUNDER"
            elif btype == "Pace":
                role = "PACE_ALLROUNDER"
            else:
                role = "ALLROUNDER"
        elif bowl_sup:
            if btype == "Spin":
                role = "SPIN_BOWLER"
            elif btype == "Pace":
                role = "PACE_BOWLER"
            else:
                role = "BOWLER"
        elif bat_sup:
            death_bat_pct = r["death_bat_balls"] / max(1, bf)
            if (death_bat_pct >= 0.25) or (order >= 5.5 and r["death_bat_balls"] >= 15):
                role = "FINISHER_BATTER"
            elif order <= 3.2:
                role = "TOP_ORDER_BATTER"
            elif order <= 5.5:
                role = "MIDDLE_ORDER_BATTER"
            else:
                role = "FINISHER_BATTER"
        else:
            if bb > bf:
                role = "BOWLER_SPARSE"
            else:
                role = "BATTER_SPARSE"
        roles.append(role)
        
        # Batting display role: requires phase usage and batting order evidence
        if not bat_sup:
            bat_role = "Tail-End Batter" if bf > 0 else "Non-Batter"
        elif is_wk:
            pp_bat_pct = r["pp_bat_balls"] / max(1, bf)
            bat_role = "Top-Order Powerplay Exploiter (Wicketkeeper-Batter)" if (pp_bat_pct >= 0.35 or order <= 3.2) else "Middle-Order Anchor (Wicketkeeper-Batter)"
        else:
            death_bat_pct = r["death_bat_balls"] / max(1, bf)
            pp_bat_pct = r["pp_bat_balls"] / max(1, bf)
            if death_bat_pct >= 0.25 or (order >= 5.5 and r["death_bat_balls"] >= 15):
                bat_role = "Death-Overs Finisher"
            elif pp_bat_pct >= 0.40 or order <= 3.2:
                bat_role = "Top-Order Powerplay Batter"
            elif order <= 5.5:
                bat_role = "Middle-Overs Anchor / Stabilizer"
            else:
                bat_role = "Death-Overs Finisher"
        bat_display_roles.append(bat_role)
        
        # Bowling display role: requires pace/phase and measured delivery/bowling-type evidence
        if not bowl_sup:
            bowl_role = "Occasional / Part-Time Bowler" if bb > 0 else "Non-Bowler"
        else:
            death_pct = r["death_bowling_balls"] / max(1, bb)
            pp_pct = r["pp_bowling_balls"] / max(1, bb)
            mid_pct = r["mid_bowling_balls"] / max(1, bb)
            yorker_cnt = r["yorker_balls"]
            yorker_pct = yorker_cnt / max(1, bb)
            
            # Check wrist spin vs finger spin from bowling_type evidence
            is_wrist = any(term in b_style for term in ["Leg-Break", "Chinaman", "wrist", "Wrist"])
            is_finger = any(term in b_style for term in ["offbreak", "orthodox", "Offbreak", "Orthodox", "finger", "Finger"])
            
            if btype == "Pace":
                if death_pct >= 0.30:
                    # Yorker specialist requires measured delivery-style evidence
                    if yorker_cnt >= 40 and yorker_pct >= 0.08:
                        bowl_role = "Death-Overs Yorker Specialist"
                    else:
                        bowl_role = "Death-Overs Pace Bowler"
                elif pp_pct >= 0.40:
                    bowl_role = "Powerplay Seam Bowler"
                elif mid_pct >= 0.50:
                    bowl_role = "Middle-Overs Pace Bowler"
                else:
                    bowl_role = "Multi-Phase Pace Bowler"
            elif btype == "Spin":
                if mid_pct >= 0.50:
                    if is_wrist:
                        bowl_role = "Middle-Overs Wrist Spinner"
                    elif is_finger:
                        bowl_role = "Middle-Overs Finger Spinner"
                    else:
                        bowl_role = "Middle-Overs Spin Bowler"
                elif pp_pct >= 0.40:
                    bowl_role = "Powerplay Finger Spinner" if is_finger else "Powerplay Spin Bowler"
                elif death_pct >= 0.30:
                    bowl_role = "Death-Overs Spin Bowler"
                else:
                    bowl_role = "Multi-Phase Wrist Spinner" if is_wrist else "Multi-Phase Spin Bowler"
            else:
                bowl_role = "Multi-Phase Bowler"
                
        bowl_display_roles.append(bowl_role)
        
    df["inferred_role"] = roles
    df["batting_display_role"] = bat_display_roles
    df["bowling_display_role"] = bowl_display_roles
    return df.reset_index()


def run_identity_audit(config: PipelineConfig) -> Tuple[Dict[str, Any], Dict[str, str]]:
    raw = config.raw_dir
    out = config.out_dir
    out.mkdir(parents=True, exist_ok=True)
    
    # 1. Load tables
    bbb = pd.read_csv(raw / "ball_by_ball.csv", low_memory=False)
    matches = pd.read_csv(raw / "matches.csv")
    comps = pd.read_csv(raw / "competitions.csv")
    teams = pd.read_csv(raw / "teams.csv")
    mapping = pd.read_csv(raw / "competition_team_player_mapping.csv")
    p11 = pd.read_csv(raw / "playing_eleven.csv")
    
    # 2. Date parsing and sorting
    matches["match_date"] = pd.to_datetime(matches["match_date"])
    matches = matches.sort_values(["match_date", "match_id"]).reset_index(drop=True)
    
    # Sort delivery ledger numerically by key
    bbb["match_id"] = bbb["match_id"].astype(int)
    bbb["innings"] = bbb["innings"].astype(int)
    bbb["innings_ball_num"] = bbb["innings_ball_num"].astype(int)
    bbb = bbb.sort_values(["match_id", "innings", "innings_ball_num"]).reset_index(drop=True)
    
    # 3. Check delivery key uniqueness
    deliv_dups = bbb.duplicated(subset=["match_id", "innings", "innings_ball_num"]).sum()
    assert deliv_dups == 0, f"Delivery key has {deliv_dups} duplicates!"
    
    # 4. Check fixture uniqueness
    match_dups = matches.duplicated(subset=["match_id"]).sum()
    assert match_dups == 0, f"Match key has {match_dups} duplicates!"
    
    # Match physical duplicate screening
    matches["team_pair"] = matches.apply(lambda r: tuple(sorted([int(r["home_team_id"]), int(r["away_team_id"])])), axis=1)
    physical_dups = matches.duplicated(subset=["match_date", "team_pair"]).sum()
    
    # 5. Competitions tiering & Match dimension
    m_comps = matches.merge(comps, on="comp_id", how="left")
    m_comps["comp_tier"] = m_comps.apply(lambda r: classify_competition_tier(r["comp_name"], r["match_format"]), axis=1)
    
    # Deliveries coverage by match
    bbb_match_ids = set(bbb["match_id"].unique())
    m_comps["has_deliveries"] = m_comps["match_id"].isin(bbb_match_ids)
    m_comps["is_abandoned"] = m_comps["result"].str.contains("Abandoned", case=False, na=False)
    
    missing_fixtures = m_comps[~m_comps["has_deliveries"]].copy()
    missing_fixtures_path = out / "missing_delivery_fixtures.csv"
    missing_fixtures.to_csv(missing_fixtures_path, index=False)
    
    fixture_dim_path = out / "fixture_dimension.csv"
    m_comps.to_csv(fixture_dim_path, index=False)
    
    # 6. Playing XI conflict resolution & quarantine
    p11_dup_mask = p11.duplicated(subset=["match_id", "player_id"], keep=False)
    xi_conflicts = p11[p11_dup_mask].copy().sort_values(["match_id", "player_id"])
    xi_conflicts_path = out / "xi_conflicts.csv"
    xi_conflicts.to_csv(xi_conflicts_path, index=False)
    
    # Clean deduplicated XI: keep first row per match_id, player_id
    p11_clean = p11.drop_duplicates(subset=["match_id", "player_id"], keep="first").copy()
    p11_clean_path = out / "playing_eleven_deduped.csv"
    p11_clean.to_csv(p11_clean_path, index=False)
    
    # 7. Player Dimension & Aliases
    all_player_ids = pd.concat([
        mapping["player_id"],
        p11["player_id"],
        bbb["striker_id"].dropna().astype(int),
        bbb["bowler_id"].dropna().astype(int),
    ]).drop_duplicates().astype(int)
    
    bbb_dated = bbb.merge(matches[["match_id", "match_date"]], on="match_id", how="left")
    player_dim = derive_player_roles(bbb_dated, p11, all_player_ids, mapping)
    player_dim_path = out / "player_dimension.csv"
    player_dim.to_csv(player_dim_path, index=False)
    
    # Historical pre-2023-H2 player dimension (strictly < 2023-07-01 for July 2023 T20I transfer cutoff)
    pre2023_h2_match_ids = set(matches[matches["match_date"] < "2023-07-01"]["match_id"].unique())
    player_dim_pre2023_h2 = derive_player_roles(bbb_dated, p11, all_player_ids, mapping, valid_match_ids=pre2023_h2_match_ids)
    player_dim_pre2023_h2_path = out / "player_dimension_pre2023_h2.csv"
    player_dim_pre2023_h2.to_csv(player_dim_pre2023_h2_path, index=False)

    # Historical pre-2024 player dimension (strictly through 2023-12-31 for earlier rolling 2024 diagnostic)
    pre2024_match_ids = set(matches[matches["match_date"] <= "2023-12-31"]["match_id"].unique())
    player_dim_pre2024 = derive_player_roles(bbb_dated, p11, all_player_ids, mapping, valid_match_ids=pre2024_match_ids)
    player_dim_pre2024_path = out / "player_dimension_pre2024.csv"
    player_dim_pre2024.to_csv(player_dim_pre2024_path, index=False)

    # Historical training as-of player dimension (strictly pre-2025 matches)
    train_match_ids = set(matches[matches["match_date"] <= "2024-12-31"]["match_id"].unique())
    player_dim_train = derive_player_roles(bbb_dated, p11, all_player_ids, mapping, valid_match_ids=train_match_ids)
    player_dim_train_path = out / "player_dimension_train.csv"
    player_dim_train.to_csv(player_dim_train_path, index=False)
    
    # Historical pre-2026 player dimension (strictly through 2025-12-31 for 2026 retrospective)
    pre2026_match_ids = set(matches[matches["match_date"] <= "2025-12-31"]["match_id"].unique())
    player_dim_pre2026 = derive_player_roles(bbb_dated, p11, all_player_ids, mapping, valid_match_ids=pre2026_match_ids)
    player_dim_pre2026_path = out / "player_dimension_pre2026.csv"
    player_dim_pre2026.to_csv(player_dim_pre2026_path, index=False)
    
    # Aliases
    aliases = mapping[["player_id", "player_name", "team_name", "comp_name"]].drop_duplicates()
    aliases_path = out / "player_aliases.csv"
    aliases.to_csv(aliases_path, index=False)
    
    # 8. Schema audit summary
    audit_data = {
        "raw_counts": {
            "ball_by_ball": len(bbb),
            "matches": len(matches),
            "competitions": len(comps),
            "teams": len(teams),
            "competition_team_player_mapping": len(mapping),
            "playing_eleven": len(p11),
        },
        "fixture_audit": {
            "total_fixtures": len(matches),
            "fixtures_with_deliveries": int(m_comps["has_deliveries"].sum()),
            "fixtures_without_deliveries": int((~m_comps["has_deliveries"]).sum()),
            "abandoned_without_deliveries": int(missing_fixtures["is_abandoned"].sum()),
            "physical_duplicates": int(physical_dups),
            "tier_breakdown": m_comps["comp_tier"].value_counts().to_dict(),
        },
        "delivery_audit": {
            "total_deliveries": len(bbb),
            "delivery_key_duplicates": int(deliv_dups),
            "min_innings_ball_num": int(bbb["innings_ball_num"].min()),
            "max_innings_ball_num": int(bbb["innings_ball_num"].max()),
        },
        "playing_eleven_audit": {
            "raw_rows": len(p11),
            "conflict_rows": len(xi_conflicts),
            "conflict_groups": int(xi_conflicts.groupby(["match_id", "player_id"]).ngroups),
            "clean_deduped_rows": len(p11_clean),
        },
        "player_dimension_audit": {
            "total_unique_players": len(player_dim),
            "role_distribution": player_dim["inferred_role"].value_counts().to_dict(),
        },
    }
    
    audit_path = out / "schema_audit.json"
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)
        
    output_files = {
        "schema_audit.json": audit_path,
        "fixture_dimension.csv": fixture_dim_path,
        "player_dimension.csv": player_dim_path,
        "player_dimension_pre2023_h2.csv": player_dim_pre2023_h2_path,
        "player_dimension_pre2024.csv": player_dim_pre2024_path,
        "player_dimension_train.csv": player_dim_train_path,
        "player_dimension_pre2026.csv": player_dim_pre2026_path,
        "player_aliases.csv": aliases_path,
        "xi_conflicts.csv": xi_conflicts_path,
        "missing_delivery_fixtures.csv": missing_fixtures_path,
        "playing_eleven_deduped.csv": p11_clean_path,
    }
    output_fingerprints = {fname: compute_sha256(fpath) for fname, fpath in output_files.items()}
    return audit_data, output_fingerprints
