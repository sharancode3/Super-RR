"""Stage 04: Freeze Folds, Reference Outcomes, and Selection Protocol Module."""

import json
from pathlib import Path
from typing import Any, Dict, Tuple

import pandas as pd

from rr_pressure.config import PipelineConfig
from rr_pressure.manifest import compute_sha256


REFERENCE_PROTOCOL = {
    "protocol_version": "1.0.0",
    "evaluation_design": {
        "paradigm": "Strict Chronological Forward Evaluation",
        "train_window": "2022-01-01 to 2024-12-31",
        "validation_window": "2025-01-01 to 2025-12-31",
        "test_holdout_window": "2026-01-01 to 2026-12-31",
        "leakage_rule": "Strict match-date cutoff; zero overlap across train, val, and test partitions.",
    },
    "comparison_target": {
        "unit": "12 legal-ball equivalents (standardized role workload)",
        "batting_impact": "actual_batter_runs - expected_batter_runs - wicket_cost * (actual_dismissal - expected_dismissal)",
        "bowling_impact": "expected_charged_runs - actual_charged_runs + wicket_cost * (actual_credited_wicket - expected_credited_wicket)",
        "sign_convention": "Positive is strictly beneficial for the player.",
        "conservative_metric": "25th percentile (Q25) of predicted match-level impact distribution",
    },
    "candidate_models": [
        {
            "name": "Cricket Baseline",
            "description": "Rule-based high-pressure state filter (death overs 16-20 + close chases) with historical role/phase run-rate and wicket-rate benchmarks."
        },
        {
            "name": "Statistical Model",
            "description": "Regularized logistic match-state leverage model + empirical Bayes partial pooling for player baseline and pressure lift (Default candidate)."
        },
        {
            "name": "Boosted Challenger",
            "description": "Calibrated Histogram Gradient Boosting / CatBoost match-state model + identical partial pooling reliability layer."
        }
    ],
    "selection_criteria": {
        "primary_metric": "25th percentile pinball loss and future realized impact lift on 2025 rolling validation",
        "post_selection_assessment": "2026 player outcomes evaluated once as previously inspected chronological evidence",
        "stability_metric": "Shortlist stability across rolling 2025 folds and bootstrap rank intervals",
        "win_model_diagnostics": "Brier score and log loss in close match states (P between 0.15 and 0.85)",
        "decision_rule": "Select candidate per role dynamically from 2025 measured metrics (pinball loss, coverage calibration, and realized top-10 lift).",
    },
    "evidence_floor": {
        "minimum_pressure_deliveries": 48,
        "minimum_distinct_matches": 6,
        "rationale": "Balances statistical power with sample retention (~80 qualifying players per role)."
    },
    "tiebreak_hierarchy": [
        "1. Conservative score (Q25)",
        "2. Mean predicted high-pressure impact",
        "3. Distinct high-pressure matches observed",
        "4. Stable Player ID"
    ]
}


def build_fold_assignments(df_ledger: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    # Filter to cohort-eligible matches
    df_cohort = df_ledger[df_ledger["is_cohort_eligible"] == True].copy()
    
    matches_df = df_cohort[["match_id", "match_date", "season", "comp_tier"]].drop_duplicates().copy()
    matches_df["match_date"] = pd.to_datetime(matches_df["match_date"])
    matches_df = matches_df.sort_values(["match_date", "match_id"]).reset_index(drop=True)
    
    years = matches_df["match_date"].dt.year
    
    # Assign folds
    folds = []
    for yr in years:
        if yr <= 2024:
            folds.append("TRAIN_2022_2024")
        elif yr == 2025:
            folds.append("VAL_2025")
        else:
            folds.append("TEST_HOLDOUT_2026")
            
    matches_df["fold"] = folds
    matches_df["is_ipl"] = matches_df["comp_tier"] == "IPL"
    matches_df["is_t20i"] = matches_df["comp_tier"] == "T20I"
    matches_df["is_emerging"] = matches_df["comp_tier"] == "EMERGING"
    
    # Fold summary
    fold_summary = {}
    for fold_name, grp in matches_df.groupby("fold"):
        fold_summary[fold_name] = {
            "match_count": len(grp),
            "date_range": [grp["match_date"].min().strftime("%Y-%m-%d"), grp["match_date"].max().strftime("%Y-%m-%d")],
            "tier_breakdown": grp["comp_tier"].value_counts().to_dict(),
        }
        
    return matches_df, fold_summary


def run_stage04_split(config: PipelineConfig) -> Tuple[Dict[str, Any], Dict[str, str]]:
    out = config.out_dir
    out.mkdir(parents=True, exist_ok=True)
    
    ledger_path = out / "delivery_ledger_proxy.csv"
    if not ledger_path.exists():
        raise FileNotFoundError(f"Delivery ledger not found at {ledger_path}")
        
    df_ledger = pd.read_csv(ledger_path, low_memory=False)
    matches_df, fold_summary = build_fold_assignments(df_ledger)
    
    # Save fold assignments
    fold_path = out / "fold_assignments.csv"
    matches_df.to_csv(fold_path, index=False)
    
    # Save split manifest
    split_manifest = {
        "split_strategy": "Chronological Whole-Match Partitions",
        "total_eligible_matches": len(matches_df),
        "folds": fold_summary,
        "assertions": {
            "no_match_overlap": len(set(matches_df["match_id"])) == len(matches_df),
            "train_val_strict_order": fold_summary["TRAIN_2022_2024"]["date_range"][1] < fold_summary["VAL_2025"]["date_range"][0],
            "val_test_strict_order": fold_summary["VAL_2025"]["date_range"][1] < fold_summary["TEST_HOLDOUT_2026"]["date_range"][0],
        }
    }
    split_manifest_path = out / "evaluation_split_manifest.json"
    with open(split_manifest_path, "w", encoding="utf-8") as f:
        json.dump(split_manifest, f, indent=2)
        
    # Save reference protocol
    ref_protocol_path = out / "reference_protocol.json"
    with open(ref_protocol_path, "w", encoding="utf-8") as f:
        json.dump(REFERENCE_PROTOCOL, f, indent=2)
        
    output_files = {
        "fold_assignments.csv": fold_path,
        "evaluation_split_manifest.json": split_manifest_path,
        "reference_protocol.json": ref_protocol_path,
    }
    output_fingerprints = {fname: compute_sha256(fpath) for fname, fpath in output_files.items()}
    return split_manifest, output_fingerprints
