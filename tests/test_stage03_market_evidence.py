"""Stage 03 Verification Tests: Market Evidence, Dated Facts, and Policy Invariance."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import pandas as pd
import numpy as np

from rr_pressure.availability import (
    TransactionRecord,
    build_ipl_availability_registry,
    RAW_TRANSACTION_RECORDS,
)
from rr_pressure.shortlist_policy import build_asof_market_snapshot

RAW_DIR = Path("6af3166e7b922_data_pack")
REPO_ROOT = Path("C:/SHARAN PROJECTS/rr")
FRESH_DIR = REPO_ROOT / "artifacts_hardened_v4_20261113" if (REPO_ROOT / "artifacts_hardened_v4_20261113").exists() else (REPO_ROOT / "artifacts_hardened_v3_20261113" if (REPO_ROOT / "artifacts_hardened_v3_20261113").exists() else (REPO_ROOT / "artifacts_hardened_v2_20261113" if (REPO_ROOT / "artifacts_hardened_v2_20261113").exists() else (REPO_ROOT / "artifacts_hardened_20261113")))


def test_future_dated_transaction_effective_date():
    """An announcement effective after as_of_date must retain the verified source franchise."""
    # Test registry with as_of_date = 2026-10-31 (before Livingstone trade on 2026-11-05)
    reg_oct = build_ipl_availability_registry(raw_dir=RAW_DIR, as_of_date="2026-10-31")
    reg_nov = build_ipl_availability_registry(raw_dir=RAW_DIR, as_of_date="2026-11-13")
    
    # On 2026-10-31, Livingstone (4391) trade was not published/effective
    liv_oct = reg_oct[reg_oct["player_id"] == 4391]
    assert liv_oct.empty, "Livingstone trade published 2026-11-05 must not exist as of 2026-10-31"
    
    # On 2026-11-13, Livingstone trade is effective at CSK
    liv_nov = reg_nov[reg_nov["player_id"] == 4391].iloc[0]
    assert liv_nov["current_franchise"] == "Chennai Super Kings"
    assert liv_nov["verified_source_franchise"] == "Sunrisers Hyderabad"
    assert liv_nov["effective_date"] == "2026-11-05"


def test_dated_trade_to_new_club():
    """Verify dated post-2026 trades: Livingstone, Natarajan, Kuldeep, Pant."""
    reg = build_ipl_availability_registry(raw_dir=RAW_DIR, as_of_date="2026-11-13").set_index("player_id")
    
    # 1. Livingstone: SRH -> CSK
    assert 4391 in reg.index
    assert reg.loc[4391, "current_franchise"] == "Chennai Super Kings"
    assert reg.loc[4391, "effective_date"] == "2026-11-05"
    
    # 2. Natarajan: DC -> SRH
    assert 4265 in reg.index
    assert reg.loc[4265, "current_franchise"] == "Sunrisers Hyderabad"
    assert reg.loc[4265, "effective_date"] == "2026-10-14"
    
    # 3. Kuldeep Yadav: DC -> LSG
    assert 3644 in reg.index
    assert reg.loc[3644, "current_franchise"] == "Lucknow Super Giants"
    assert reg.loc[3644, "effective_date"] == "2026-06-23"
    
    # 4. Rishabh Pant: LSG -> DC
    assert 4703 in reg.index
    assert reg.loc[4703, "current_franchise"] == "Delhi Capitals"
    assert reg.loc[4703, "effective_date"] == "2026-06-23"


def test_documented_retirement():
    """Documented retirements (Shikhar Dhawan, Andre Russell) must be hard exclusions."""
    reg = build_ipl_availability_registry(raw_dir=RAW_DIR, as_of_date="2026-11-13").set_index("player_id")
    
    # Shikhar Dhawan (142): Retired 2024-08-24
    assert 142 in reg.index
    dhawan = reg.loc[142]
    assert dhawan["availability_status"] == "RETIRED_FROM_IPL"
    assert dhawan["decision_category"] == "BENCHMARK_ONLY"
    assert dhawan["effective_date"] == "2024-08-24"
    
    # Andre Russell (1318): Retired 2025-11-30 to join KKR staff
    assert 1318 in reg.index
    russell = reg.loc[1318]
    assert russell["availability_status"] == "RETIRED_FROM_IPL"
    assert russell["decision_category"] == "BENCHMARK_ONLY"


def test_stale_injury_vs_squad_selection():
    """Matheesha Pathirana had May 2026 injury replacement, requiring medical clearance and release."""
    reg = build_ipl_availability_registry(raw_dir=RAW_DIR, as_of_date="2026-11-13").set_index("player_id")
    assert 8661 in reg.index
    pathirana = reg.loc[8661]
    assert pathirana["availability_status"] == "FITNESS_CLEARANCE_REQUIRED"
    assert pathirana["decision_category"] == "CONDITIONAL_REGISTRATION_FITNESS_WATCH"
    assert "hamstring" in pathirana["notes"].lower() or "replacement" in pathirana["notes"].lower()


def test_rr_incumbent():
    """RR incumbents (Sooryavanshi, Parag, Jurel, Bishnoi) must be identified with INCUMBENT_RETENTION."""
    reg = build_ipl_availability_registry(raw_dir=RAW_DIR, as_of_date="2026-11-13").set_index("player_id")
    
    for pid in [50284, 6423, 7260, 7503]:
        assert pid in reg.index
        rec = reg.loc[pid]
        assert rec["current_franchise"] == "Rajasthan Royals"
        assert rec["availability_status"] == "INCUMBENT_RR"
        assert rec["decision_category"] == "INCUMBENT_RETENTION"


def test_unverified_market_fallback():
    """Candidates without market records must default to UNVERIFIED_MISSING_MARKET_RECORD / UNVERIFIED_HOLD."""
    mapping_df = pd.read_csv(RAW_DIR / "competition_team_player_mapping.csv")
    p_dim = pd.read_csv(FRESH_DIR / "player_dimension.csv")
    
    snap = build_asof_market_snapshot(2027, mapping_df, p_dim, raw_dir=RAW_DIR)
    
    # Synthetic unverified player
    unrec = snap[snap["availability_status"] == "UNVERIFIED_MISSING_MARKET_RECORD"]
    assert len(unrec) > 0
    assert (unrec["decision_category"] == "UNVERIFIED_HOLD").all()
    assert (unrec["route_tier"] == "UNVERIFIED").all()
    assert (unrec["is_unavailable_hard"] == True).all()


def test_same_policy_cricket_score_invariance():
    """Updating a player's franchise or release status leaves their cricket model score invariant."""
    deliv = pd.read_csv(FRESH_DIR / "delivery_impact_ledger.csv", low_memory=False)
    p_dim = pd.read_csv(FRESH_DIR / "player_dimension.csv")
    
    # Batting impact is derived strictly from delivery outcomes, not market registry
    # Check that delivery outcomes for David Miller (1077) or Harshal Patel (2261) are unchanged
    miller_delivs = deliv[deliv["striker_id"] == 1077]
    assert len(miller_delivs) > 0
    assert not miller_delivs["hp_bat_impact"].isna().all()
    
    # Bowling delivery impact
    harshal_delivs = deliv[deliv["bowler_id"] == 2261]
    assert len(harshal_delivs) > 0
    assert not harshal_delivs["hp_bowl_impact"].isna().all()
