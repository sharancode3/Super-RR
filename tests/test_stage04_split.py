"""Regression and validation tests for Stage 04 Evaluation Split & Reference Protocol."""

import json
from pathlib import Path
import pandas as pd
import pytest

ARTIFACTS_DIR = Path("artifacts_revalidated") if Path("artifacts_revalidated").exists() else Path("artifacts")


def test_fold_assignments_leakage_and_uniqueness():
    fold_path = ARTIFACTS_DIR / "fold_assignments.csv"
    assert fold_path.exists(), "fold_assignments.csv does not exist"
    df = pd.read_csv(fold_path)
    
    # Assert each match belongs to exactly one fold
    assert df["match_id"].duplicated().sum() == 0, "Duplicate matches found in fold assignments"
    
    # Assert all three folds exist
    folds = set(df["fold"].unique())
    expected = {"TRAIN_2022_2024", "VAL_2025", "TEST_HOLDOUT_2026"}
    assert folds == expected, f"Folds mismatch: {folds} vs {expected}"


def test_strict_chronological_ordering():
    manifest_path = ARTIFACTS_DIR / "evaluation_split_manifest.json"
    assert manifest_path.exists(), "evaluation_split_manifest.json does not exist"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    train_end = manifest["folds"]["TRAIN_2022_2024"]["date_range"][1]
    val_start = manifest["folds"]["VAL_2025"]["date_range"][0]
    val_end = manifest["folds"]["VAL_2025"]["date_range"][1]
    test_start = manifest["folds"]["TEST_HOLDOUT_2026"]["date_range"][0]
    
    assert train_end < val_start, f"Train ({train_end}) leaks into Val ({val_start})"
    assert val_end < test_start, f"Val ({val_end}) leaks into Test ({test_start})"
    assert manifest["assertions"]["train_val_strict_order"] is True
    assert manifest["assertions"]["val_test_strict_order"] is True


def test_reference_protocol_spec():
    ref_path = ARTIFACTS_DIR / "reference_protocol.json"
    assert ref_path.exists(), "reference_protocol.json does not exist"
    with open(ref_path, "r", encoding="utf-8") as f:
        ref = json.load(f)
    
    assert "comparison_target" in ref
    assert ref["comparison_target"]["unit"] == "12 legal-ball equivalents (standardized role workload)"
    assert "conservative_metric" in ref["comparison_target"]
    assert "candidate_models" in ref
    assert len(ref["candidate_models"]) == 3
    assert "selection_criteria" in ref
    assert "tiebreak_hierarchy" in ref
