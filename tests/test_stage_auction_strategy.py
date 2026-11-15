"""Acceptance and unit tests for Stage 1-5 Auction Strategy and IPL Decision Layer."""

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(".").resolve()))

from rr_pressure.availability import (
    RAW_TRANSACTION_RECORDS,
    RR_DEPTH_CHART,
    PLAYER_STRATEGY_MAP,
    build_ipl_availability_registry,
    build_rr_depth_chart,
)
from rr_pressure.config import PipelineConfig
from rr_pressure.ledger import build_scoreboard_ledger
from rr_pressure.compare import MODEL_METRIC_KEYS, SHIPPED_MODELS

RAW_DIR = Path("6af3166e7b922_data_pack")


def test_fixture_30057_scoreboard_reconciliation():
    """Verify that Fixture 30057 (DC vs PBKS) target is reconciled to official 175."""
    config = PipelineConfig(raw_dir=RAW_DIR, out_dir=Path("artifacts_role_repaired_20261111"), seed=2027)
    bbb, _, _, _ = build_scoreboard_ledger(config)

    m30057 = bbb[bbb["match_id"] == 30057]
    assert len(m30057) > 0, "Fixture 30057 must exist in delivery ledger"

    m30057_inn1 = m30057[m30057["innings"] == 1]
    m30057_inn2 = m30057[m30057["innings"] == 2]

    # Verify 1st innings off-bat runs = 164
    assert m30057_inn1["runs"].sum() == 164, "Fixture 30057 inn 1 off-bat runs must be 164"

    # Verify 2nd innings reconciled target is exactly 175 (official scorecard DC 174/9 + 1)
    targets = m30057_inn2["target_runs_reconciled"].unique()
    assert len(targets) == 1 and targets[0] == 175, f"Expected reconciled target 175, got {targets}"

    # Verify target source and proxy status
    sources = m30057_inn2["target_source"].unique()
    assert len(sources) == 1 and sources[0] == "VERIFIED_OFFICIAL_SCORECARD"
    proxies = m30057_inn2["target_proxy_status"].unique()
    assert len(proxies) == 1 and proxies[0] == "EXACT_RECONCILED"

    # Verify pre_target_reconciled_gap at first ball of chase is 175
    first_ball_gap = m30057_inn2.iloc[0]["pre_target_reconciled_gap"]
    assert first_ball_gap == 175, f"Expected starting gap of 175, got {first_ball_gap}"


def test_availability_registry_dated_facts():
    """Verify dated facts for Kuldeep, Sooryavanshi, Behrendorff, Pathirana, Bumrah, Surya."""
    registry = build_ipl_availability_registry()
    assert not registry.empty
    assert len(registry) >= len(RAW_TRANSACTION_RECORDS)

    reg_dict = registry.set_index("player_id").to_dict("index")

    # 1. Kuldeep Yadav (ID 3644): Traded to LSG on 2026-06-23
    assert 3644 in reg_dict
    kuldeep = reg_dict[3644]
    assert kuldeep["current_franchise"] == "Lucknow Super Giants"
    assert kuldeep["effective_date"] == "2026-06-23"
    assert kuldeep["transaction_type"] == "TRADE"
    assert kuldeep["availability_status"] == "PENDING_NOV17_RETENTIONS"
    assert kuldeep["decision_category"] == "CONDITIONAL_RELEASE_WATCH"

    # 2. Vaibhav Sooryavanshi (ID 50284): RR 2026 squad incumbent
    assert 50284 in reg_dict
    vaibhav = reg_dict[50284]
    assert vaibhav["current_franchise"] == "Rajasthan Royals"
    assert vaibhav["availability_status"] == "INCUMBENT_RR"
    assert vaibhav["decision_category"] == "INCUMBENT_RETENTION"

    # 3. Jason Behrendorff (ID 2054): Shoulder surgery, unverified for IPL auction
    assert 2054 in reg_dict
    jason = reg_dict[2054]
    assert jason["availability_status"] == "AUCTION_REGISTRATION_UNVERIFIED"
    assert jason["fitness_clearance_status"] == "HIGH_FITNESS_RISK_SHOULDER_SURGERY"
    assert jason["decision_category"] == "CONDITIONAL_REGISTRATION_FITNESS_WATCH"

    # 4. Matheesha Pathirana (ID 8661): Hamstring injury in 2026, fitness clearance required
    assert 8661 in reg_dict
    pathirana = reg_dict[8661]
    assert pathirana["availability_status"] == "FITNESS_CLEARANCE_REQUIRED"
    assert pathirana["fitness_clearance_status"] == "HAMSTRING_REHABILITATION"
    assert pathirana["decision_category"] == "CONDITIONAL_REGISTRATION_FITNESS_WATCH"

    # 5. Jasprit Bumrah (ID 2933) & Suryakumar Yadav (ID 1699): Benchmark only
    assert 2933 in reg_dict and reg_dict[2933]["decision_category"] == "BENCHMARK_ONLY"
    assert 1699 in reg_dict and reg_dict[1699]["decision_category"] == "BENCHMARK_ONLY"

    # 6. Sunil Narine (ID 781): Benchmark only
    assert 781 in reg_dict and reg_dict[781]["decision_category"] == "BENCHMARK_ONLY"


def test_rr_depth_chart_structure():
    """Verify that RR depth chart models the tactical squad vacancies."""
    depth_df = build_rr_depth_chart()
    assert len(depth_df) >= 7
    expected_roles = {
        "TOP_ORDER_OPENER",
        "WICKETKEEPER_BATTER",
        "MIDDLE_ORDER_STABILIZER",
        "DEATH_FINISHER",
        "NEW_BALL_SEAM",
        "MIDDLE_OVERS_SPIN",
        "DEATH_PACE_BOWLER",
    }
    assert set(depth_df["tactical_role"]) == expected_roles
    assert (depth_df["tactical_need_rating"].str.len() > 0).all()


def test_player_strategy_map_four_questions():
    """Verify that every mapped candidate answers all 4 strategic questions."""
    for pid, strat in PLAYER_STRATEGY_MAP.items():
        assert isinstance(pid, int)
        assert len(strat["tactical_squad_role"]) > 5, f"Missing tactical_squad_role for player {pid}"
        assert len(strat["rr_incumbent_comparison"]) > 10, f"Missing incumbent comparison for player {pid}"
        assert len(strat["actionable_acquisition_route"]) > 5, f"Missing route for player {pid}"
        assert len(strat["rival_incentives"]) > 10, f"Missing rival incentives for player {pid}"
        assert len(strat["price_scenario"]) > 3, f"Missing price scenario for player {pid}"


def test_challenger_c_wiring():
    """Verify that Challenger C (Role-Phase Partial Pooling) is registered."""
    assert "challenger_C_role_phase" in MODEL_METRIC_KEYS.values()
    assert "Challenger C (Role-and-Phase Partial-Pooling)" in SHIPPED_MODELS
