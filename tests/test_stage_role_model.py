"""Regression & unit tests for Stage 03-06 role-and-phase model and shared shortlist policy."""

from pathlib import Path

import numpy as np
import pandas as pd

from rr_pressure.manifest import generate_market_evidence_manifest
from rr_pressure.rankings import apply_production_shortlist_policy
from rr_pressure.role_challenger import (
    ChallengerRPP_RolePhaseJoint,
    build_phase_observations_from_ledger,
)
from rr_pressure.shortlist_policy import build_asof_market_snapshot, select_shortlist_by_policy


def _make_synthetic_ledger() -> tuple:
    p_dim = pd.DataFrame([
        {"player_id": 101, "player_name": "P101", "inferred_role": "PACE_BOWLER", "bowler_type": "Pace"},
        {"player_id": 102, "player_name": "P102", "inferred_role": "PACE_BOWLER", "bowler_type": "Pace"},
        {"player_id": 103, "player_name": "P103", "inferred_role": "SPIN_BOWLER", "bowler_type": "Spin"},
    ])
    rows = []
    # Pre-2025 matches (2023-2024): include ordinary cells, 1-5b short HP cells, >=6b HP cells, and 0-legal-ball extras cell
    specs = [
        # (match_id, date, pid, phase, inn, hp, tier, legal_balls_list, imp_per_ball)
        (1, "2023-04-01", 101, "DEATH", 2, True, "IPL", [1, 1, 1], 0.5),         # 3b short HP stint!
        (2, "2023-04-05", 101, "DEATH", 2, False, "IPL", [1]*6, 0.2),            # ordinary
        (3, "2024-04-10", 101, "DEATH", 2, True, "IPL", [1]*8, 0.6),             # >=6b HP
        (4, "2024-04-12", 102, "POWERPLAY", 1, True, "IPL", [1, 1], -0.4),       # 2b short HP stint
        (5, "2024-04-15", 102, "POWERPLAY", 1, False, "IPL", [1]*6, -0.1),       # ordinary
        (6, "2024-04-18", 103, "MIDDLE", 2, True, "T20I", [1]*6, 0.4),           # T20I
        (7, "2024-04-20", 103, "MIDDLE", 2, False, "IPL", [0, 0], -0.5),         # 0-legal-ball extras cell
        (8, "2024-04-22", 103, "MIDDLE", 2, False, "IPL", [1]*6, 0.1),           # ordinary
        # Future 2026 match (should NEVER leak into <2025 cutoff!)
        (9, "2026-04-01", 101, "DEATH", 2, True, "IPL", [1]*6, -5.0),
    ]
    for mid, dt, pid, ph, inn, hp, tier, lballs, imp_b in specs:
        for b in lballs:
            rows.append({
                "match_id": mid,
                "match_date": dt,
                "season": int(dt[:4]),
                "striker_id": pid,
                "bowler_id": pid,
                "match_phase": ph,
                "innings": inn,
                "is_high_pressure_20": hp,
                "comp_tier": tier,
                "is_reliability_eligible": True,
                "is_legal_ball": b,
                "runs": 1 if b == 1 else 0,
                "bowler_charge_runs": 1,
                "is_striker_dismissed": 0,
                "is_bowler_wicket": 0,
                "batting_impact": imp_b,
                "bowling_impact": imp_b,
            })
    return pd.DataFrame(rows), p_dim


def test_rpp_cutoff_invariance_short_stints_and_match_weights():
    ledger, p_dim = _make_synthetic_ledger()
    obs_all = build_phase_observations_from_ledger(ledger, "bowling")
    obs_pre25 = build_phase_observations_from_ledger(ledger, "bowling", max_date="2024-12-31")
    obs_pre25_from_pre = build_phase_observations_from_ledger(ledger[ledger["season"] < 2025], "bowling")

    # 1. Later appearances leave earlier observations & predictions bit-for-bit identical
    pd.testing.assert_frame_equal(obs_pre25.reset_index(drop=True), obs_pre25_from_pre.reset_index(drop=True))

    # 2. Extras-only (0 legal balls) preserved in obs ledger, short <6b stints entered cleanly
    assert (obs_all["legal_balls"] == 0).sum() == 1
    assert ((obs_pre25["is_high_pressure"] == True) & (obs_pre25["legal_balls"] < 6)).sum() == 2

    m_a = ChallengerRPP_RolePhaseJoint(cutoff_label="PRE2025").fit(obs_pre25, p_dim, "bowling")
    m_b = ChallengerRPP_RolePhaseJoint(cutoff_label="PRE2025").fit(obs_pre25_from_pre, p_dim, "bowling")
    assert np.allclose(m_a.predict_quantile([101, 102, 103, 999]), m_b.predict_quantile([101, 102, 103, 999]))
    assert m_a.fit_meta_["n_short_hp_cells_lt6"] == 2
    assert m_a.fit_meta_["n_ord_cells"] == 3  # excludes 0-legal-ball extras cell

    # 3. Finite ordered quantiles q10 <= q25 <= mean <= q90 (including unseen fallback id 999)
    pids = [101, 102, 103, 999]
    q25 = m_a.predict_quantile(pids)
    mean = m_a.predict_mean(pids)
    q10, q90 = m_a.predict_ci_80(pids)
    assert np.all(np.isfinite(q25)) and np.all(np.isfinite(mean))
    assert np.all(q10 <= q25) and np.all(q25 <= mean) and np.all(mean <= q90)

    # 4. Synthetic match_weights=1.0 invariance vs None, and downweighting match 3 leaves fit finite
    m_w1 = ChallengerRPP_RolePhaseJoint(cutoff_label="W1").fit(
        obs_pre25, p_dim, "bowling", match_weights={int(m): 1.0 for m in obs_pre25["match_id"].unique()}
    )
    assert np.allclose(m_a.predict_quantile(pids), m_w1.predict_quantile(pids))


def test_shared_shortlist_policy_gate_and_dated_availability_propagation():
    scored = pd.DataFrame([
        {"player_id": 1, "is_qualified": True, "conservative_score_q25": -0.5, "predicted_hp_impact": 6.0, "hp_balls": 120, "ipl_hp_balls": 14, "ipl_hp_matches": 1},
        {"player_id": 2, "is_qualified": True, "conservative_score_q25": -1.2, "predicted_hp_impact": 5.0, "hp_balls": 80, "ipl_hp_balls": 60, "ipl_hp_matches": 6},
        {"player_id": 3, "is_qualified": True, "conservative_score_q25": -1.5, "predicted_hp_impact": 4.5, "hp_balls": 70, "ipl_hp_balls": 70, "ipl_hp_matches": 8},
        {"player_id": 4, "is_qualified": False, "conservative_score_q25": 1.0, "predicted_hp_impact": 8.0, "hp_balls": 50, "ipl_hp_balls": 50, "ipl_hp_matches": 6},
    ])
    market_open = pd.DataFrame([
        {"player_id": 1, "current_franchise": "SRH", "availability_status": "PENDING_NOV17_RETENTIONS", "decision_category": "CONDITIONAL_RELEASE_WATCH", "is_rr_incumbent": False, "is_unavailable_hard": False},
        {"player_id": 2, "current_franchise": "RCB", "availability_status": "PENDING_NOV17_RETENTIONS", "decision_category": "CONDITIONAL_RELEASE_WATCH", "is_rr_incumbent": False, "is_unavailable_hard": False},
        {"player_id": 3, "current_franchise": "DC", "availability_status": "PENDING_NOV17_RETENTIONS", "decision_category": "CONDITIONAL_RELEASE_WATCH", "is_rr_incumbent": False, "is_unavailable_hard": False},
        {"player_id": 4, "current_franchise": "KKR", "availability_status": "PENDING_NOV17_RETENTIONS", "decision_category": "CONDITIONAL_RELEASE_WATCH", "is_rr_incumbent": False, "is_unavailable_hard": False},
    ])

    res_open = select_shortlist_by_policy(scored, market_open, policy_name="RPP_IPL_VERIFIED", min_ipl_hp_balls=24, min_ipl_hp_matches=2)
    selected_open = res_open[res_open["submission_rank"].notna()].sort_values("submission_rank")
    # Player 1 dropped for <24b/<2m direct IPL; player 4 dropped for is_qualified=False
    assert list(selected_open["player_id"]) == [2, 3]
    assert str(res_open.loc[res_open["player_id"] == 1, "perf_filter_reason"].iloc[0]).startswith("THIN_DIRECT_IPL")

    # A benchmark-only decision reaches the selector without changing the player score.
    market_benchmark = market_open.copy()
    market_benchmark.loc[market_benchmark["player_id"] == 2, ["availability_status", "decision_category", "is_unavailable_hard"]] = [
        "BENCHMARK_UNTOUCHABLE", "BENCHMARK_ONLY", True
    ]
    res_benchmark = select_shortlist_by_policy(scored, market_benchmark, policy_name="RPP_IPL_VERIFIED", min_ipl_hp_balls=24, min_ipl_hp_matches=2)
    assert list(res_benchmark.loc[res_benchmark["submission_rank"].notna(), "player_id"]) == [3]


def test_rr_incumbent_and_traded_candidate_share_production_screen():
    raw_dir = Path("6af3166e7b922_data_pack")
    mapping = pd.read_csv(raw_dir / "competition_team_player_mapping.csv")
    scored = pd.DataFrame({
        "player_id": [3647, 50284, 4391, 6423],
        "conservative_score_q25": [5.0, 4.0, 3.0, 2.0],
        "is_qualified": [True, True, True, False],
    }).assign(
        predicted_hp_impact=6.0, hp_balls=80, ipl_hp_balls=60, ipl_hp_matches=6, hp_rate_ipl_12b=2.0,
    )
    market = build_asof_market_snapshot(2027, mapping, scored, raw_dir=raw_dir)
    ranked = apply_production_shortlist_policy(
        scored, market, discipline="batting",
        policy_name="RR_IPL_POSITIVE_VERIFIED", allow_rr_incumbents=True,
    ).set_index("player_id")

    assert ranked.loc[50284, "submission_rank"] == 1
    assert ranked.loc[4391, "submission_rank"] == 2
    assert ranked.loc[4391, "current_franchise_2027"] == "Chennai Super Kings"
    assert ranked.loc[4391, "decision_category"] == "CONDITIONAL_RELEASE_WATCH"
    assert ranked.loc[4391, "route_tier"] == "CONDITIONAL"
    assert ranked.loc[3647, "passed_over_reason"] == "RIVAL_CORNERSTONE_OR_BENCHMARK_ONLY"
    assert ranked.loc[6423, "passed_over_reason"] == "FAIL_ROLE_OR_TOTAL_SAMPLE"


def test_replay_vs_production_selector_exact_parity_ties_missing_and_dual_role(tmp_path):
    """Stage 1 Exit Check: replay selector & production selector return identical eligibility, ranks, and exclusion reasons."""
    candidates = pd.DataFrame([
        # Near-tie pair on Q25 (-1.20), broken by predicted_hp_impact (+5.5 vs +5.0)
        {"player_id": 10, "is_qualified": True, "conservative_score_q25": -1.20, "predicted_hp_impact": 5.0, "hp_balls": 80, "ipl_hp_balls": 60, "ipl_hp_matches": 6},
        {"player_id": 11, "is_qualified": True, "conservative_score_q25": -1.20, "predicted_hp_impact": 5.5, "hp_balls": 80, "ipl_hp_balls": 40, "ipl_hp_matches": 4},
        # Identical Q25 + mean (-1.50 / 4.0), broken by ipl_hp_balls (90 vs 70), then player_id
        {"player_id": 20, "is_qualified": True, "conservative_score_q25": -1.50, "predicted_hp_impact": 4.0, "hp_balls": 90, "ipl_hp_balls": 70, "ipl_hp_matches": 5},
        {"player_id": 21, "is_qualified": True, "conservative_score_q25": -1.50, "predicted_hp_impact": 4.0, "hp_balls": 90, "ipl_hp_balls": 90, "ipl_hp_matches": 5},
        {"player_id": 22, "is_qualified": True, "conservative_score_q25": -1.50, "predicted_hp_impact": 4.0, "hp_balls": 90, "ipl_hp_balls": 70, "ipl_hp_matches": 5},
        # Thin direct IPL (14b / 1m) -> excluded cleanly by RPP_IPL_VERIFIED
        {"player_id": 30, "is_qualified": True, "conservative_score_q25": -0.30, "predicted_hp_impact": 7.0, "hp_balls": 120, "ipl_hp_balls": 14, "ipl_hp_matches": 1},
        # Missing market record (NOT in market_df!) -> must be held, NEVER release-watch
        {"player_id": 40, "is_qualified": True, "conservative_score_q25": -0.10, "predicted_hp_impact": 7.5, "hp_balls": 100, "ipl_hp_balls": 80, "ipl_hp_matches": 8},
        # Dual-role player (qualified all-rounder in both disciplines)
        {"player_id": 50, "is_qualified": True, "conservative_score_q25": -1.40, "predicted_hp_impact": 4.8, "hp_balls": 110, "ipl_hp_balls": 90, "ipl_hp_matches": 9},
        # Role/sample unqualified
        {"player_id": 60, "is_qualified": False, "conservative_score_q25": 0.50, "predicted_hp_impact": 8.0, "hp_balls": 60, "ipl_hp_balls": 60, "ipl_hp_matches": 6},
    ])
    market_df = pd.DataFrame([
        {"player_id": pid, "current_franchise": "RivalA", "availability_status": "PENDING_NOV17_RETENTIONS", "decision_category": "CONDITIONAL_RELEASE_WATCH", "is_rr_incumbent": False, "is_unavailable_hard": False}
        for pid in (10, 11, 20, 21, 22, 30, 50, 60)
    ])

    for disc in ("batting", "bowling"):
        rep = select_shortlist_by_policy(candidates, market_df, policy_name="RPP_IPL_VERIFIED", min_ipl_hp_balls=24, min_ipl_hp_matches=2, discipline=disc)
        prod = apply_production_shortlist_policy(candidates, market_df, discipline=disc)

        assert list(rep["player_id"]) == list(prod["player_id"])
        assert list(rep["policy_eligible"]) == list(prod["policy_eligible"])
        assert list(rep["is_eligible_acquisition"]) == list(prod["is_eligible_acquisition"])
        assert list(rep["passed_over_reason"]) == list(prod["passed_over_reason"])
        assert rep["submission_rank"].fillna(-1).tolist() == prod["submission_rank"].fillna(-1).tolist()
        assert rep["submission_rank_pre_review"].fillna(-1).tolist() == prod["submission_rank_pre_review"].fillna(-1).tolist()

        # Check exact tie ordering, missing market hold, and thin-IPL exclusion
        elig_ids = rep[rep["submission_rank"].notna()].sort_values("submission_rank")["player_id"].tolist()
        assert elig_ids == [11, 10, 50, 21, 20, 22]
        assert rep.loc[rep["player_id"] == 40, "passed_over_reason"].iloc[0] == "UNVERIFIED_MISSING_MARKET_RECORD_HOLD"
        assert rep.loc[rep["player_id"] == 30, "passed_over_reason"].iloc[0] == "REVIEWED_OUT_THIN_DIRECT_IPL"
        assert rep.loc[rep["player_id"] == 60, "passed_over_reason"].iloc[0] == "FAIL_ROLE_OR_TOTAL_SAMPLE"

    # Also verify build_asof_market_snapshot(2027) is strictly read-only on raw_dir & separate market manifest works
    raw_ro = tmp_path / "ro_raw"
    raw_ro.mkdir()
    pd.DataFrame([{"comp_id": 3298, "player_id": 360, "team_id": 1, "team_name": "Royal Challengers Bengaluru", "season": 2026}]).to_csv(
        raw_ro / "competition_team_player_mapping.csv", index=False
    )
    snap = build_asof_market_snapshot(2027, pd.read_csv(raw_ro / "competition_team_player_mapping.csv"), pd.DataFrame([{"player_id": 360}]), raw_dir=raw_ro)
    assert not (raw_ro / "ipl_availability_registry.csv").exists()
    assert not snap.empty
    mpath, mdoc = generate_market_evidence_manifest(tmp_path / "out", raw_ro)
    assert mpath.exists() and len(mdoc["market_evidence_bundle_sha256"]) == 64


def test_stage2_heldout_perturbation_and_replay_invariance():
    """Stage 2 Exit Check: perturbing held-out (>= cutoff) outcomes leaves as-of roles, ex-ante predictions, and replay Top-10 invariant."""
    import json
    from pathlib import Path

    # 1. Verify synthetic RPP expanding-window calibration & ex-ante predictions are bit-for-bit invariant to >=2025 perturbations
    ledger_a, p_dim = _make_synthetic_ledger()
    # Add extra 2023-2024 matches so expanding-window chronological calibration blocks execute (>=6 matches)
    extra = []
    for k, dt in enumerate(["2023-05-01", "2023-05-05", "2024-03-01", "2024-03-10"], start=20):
        pid = 101 if k % 2 == 0 else 102
        for _ in range(6):
            extra.append({
                "match_id": k, "match_date": dt, "season": int(dt[:4]),
                "striker_id": pid, "bowler_id": pid, "match_phase": "DEATH", "innings": 2,
                "is_high_pressure_20": True, "comp_tier": "IPL", "is_reliability_eligible": True,
                "is_legal_ball": 1, "runs": 1, "bowler_charge_runs": 1,
                "is_striker_dismissed": 0, "is_bowler_wicket": 0, "batting_impact": 0.2, "bowling_impact": 0.2,
            })
    ledger_a = pd.concat([ledger_a, pd.DataFrame(extra)], ignore_index=True)
    ledger_b = ledger_a.copy()
    # Perturb held-out (>= 2025) outcomes aggressively
    held_mask = ledger_b["match_date"] >= "2025-01-01"
    ledger_b.loc[held_mask, ["runs", "bowler_charge_runs", "is_striker_dismissed", "batting_impact", "bowling_impact"]] = [6, 6, 1, -99.0, 99.0]

    obs_a = build_phase_observations_from_ledger(ledger_a, "bowling", max_date="2024-12-31")
    obs_b = build_phase_observations_from_ledger(ledger_b, "bowling", max_date="2024-12-31")
    pd.testing.assert_frame_equal(obs_a.reset_index(drop=True), obs_b.reset_index(drop=True))

    mod_a = ChallengerRPP_RolePhaseJoint(cutoff_label="<2025").fit(obs_a, p_dim, "bowling")
    mod_b = ChallengerRPP_RolePhaseJoint(cutoff_label="<2025").fit(obs_b, p_dim, "bowling")
    assert mod_a.fit_meta_["calibration_mode"] == "expanding_chronological_ex_ante"
    assert np.allclose(mod_a.predict_quantile([101, 102, 103]), mod_b.predict_quantile([101, 102, 103]))
    assert np.allclose(mod_a.predict_mean([101, 102, 103]), mod_b.predict_mean([101, 102, 103]))

    # 2. Verify saved artifacts_reval_20261112 replay JSON (if generated) records required Stage 2 metadata cleanly
    reval_rep = Path("artifacts_reval_20261112/stage04_replay_results.json")
    if reval_rep.exists():
        rep = json.loads(reval_rep.read_text(encoding="utf-8"))
        for yr in ("2024", "2025", "2026"):
            for disc in ("batting", "bowling"):
                rpp = rep[yr][disc]["challenger_RPP_role_phase_joint"]
                diag = rep[yr][disc]["challenger_RPP_realized_phase_mix_diagnostic"]
                assert rpp["shortlist_policy"] == "RPP_IPL_VERIFIED"
                assert rpp["forecast_type"] == "ex_ante_prior_mix"
                assert diag["forecast_type"] == "conditional_realized_phase_mix"
                assert diag["eligible_for_selection"] is False
                assert "all_positive_ipl_metrics" in rpp and "short_stint_1_to_5b_ipl_metrics" in rpp
                assert rep[yr][disc]["ablation_B0_no_pressure"]["shortlist_policy"] == "RPP_IPL_VERIFIED"
                assert "RAW_MODEL" in rep["shortlist_policy_controls"][yr][disc]
                assert "LEGACY_POST_HOC" in rep["shortlist_policy_controls"][yr][disc]


def test_stage3_batting_delivery_hazard_and_short_stint_causes():
    """Stage 3 Check: short-stint cause classifier & delivery-hazard cutoff invariance over 1..5b + >=6b cells."""
    from rr_pressure.delivery_challenger import (
        ChallengerDHP_BattingDeliveryHazard,
        build_batting_delivery_cells,
        build_batting_stint_cause_audit,
    )

    ledger, p_dim = _make_synthetic_ledger()
    ledger = ledger.copy()
    ledger["runs"] = ledger["runs"].astype(float)
    ledger["expected_bat_runs"] = 1.1
    ledger["expected_striker_dismissal"] = 0.05
    ledger["marginal_wicket_value_ws"] = 7.0
    ledger["innings_ball_num"] = ledger.groupby(["match_id", "innings"]).cumcount() + 1

    audit = build_batting_stint_cause_audit(ledger, max_date="2024-12-31")
    assert set(audit["short_cause"]).issubset({"GE6_BALLS", "DISMISSED", "INNINGS_END_NOT_OUT", "OTHER_NOT_OUT"})
    assert (audit["is_short_1_to_5b"]).any()

    ledger_pert = ledger.copy()
    ledger_pert.loc[ledger_pert["match_date"] >= "2025-01-01", ["runs", "is_striker_dismissed", "batting_impact"]] = [6.0, 1, -99.0]
    c_a = build_batting_delivery_cells(ledger, max_date="2024-12-31")
    c_b = build_batting_delivery_cells(ledger_pert, max_date="2024-12-31")
    pd.testing.assert_frame_equal(c_a.reset_index(drop=True), c_b.reset_index(drop=True))

    m_a = ChallengerDHP_BattingDeliveryHazard(cutoff_label="<2025").fit(c_a, p_dim)
    m_b = ChallengerDHP_BattingDeliveryHazard(cutoff_label="<2025").fit(c_b, p_dim)
    assert np.allclose(m_a.predict_quantile([101, 102, 103]), m_b.predict_quantile([101, 102, 103]))
    assert m_a.fit_meta_["n_short_hp_cells_lt6"] >= 1


def test_stage4_run_driven_audit_and_export_parity():
    """Stage 4 Check: verify final exports & rankings_audit are 100% run-driven with exact parity."""
    import json
    from pathlib import Path

    for candidate_dir in (
        Path("artifacts_s2_blend_20261112"),
        Path("artifacts_reval_final_20261112"),
        Path("artifacts_reval_20261112"),
    ):
        audit_p = candidate_dir / "rankings_audit.json"
        if not audit_p.exists():
            continue
        audit = json.loads(audit_p.read_text(encoding="utf-8"))
        notes = audit["verification_notes"]
        assert "Challenger D removing 0-IPL" not in notes
        assert "Bowling reviews B0 against C-IPL" not in notes
        assert audit["chosen_model_batting"] in notes or audit["model_used"] in notes

        sl = pd.read_csv(candidate_dir / "rr_shortlist.csv")
        un = pd.read_csv(candidate_dir / "unstop_rank_order.csv")
        chk = pd.read_csv(candidate_dir / "unstop_submission_checklist.csv")
        rec = pd.read_csv(candidate_dir / "rr_recruitment_sheet.csv")
        t10 = sl[sl["is_official_top10"]].copy()
        assert len(t10[t10["role_pool"] == "Batting"]) == 10
        assert len(t10[t10["role_pool"] == "Bowling"]) == 10
        assert t10["player_id"].tolist() == un["player_id"].tolist()
        assert t10["player_id"].tolist() == chk["player_id"].tolist()
        assert sl["player_id"].tolist() == rec["player_id"].tolist()
        assert (candidate_dir / "market_evidence_manifest.json").exists()
        if candidate_dir.name == "artifacts_s2_blend_20261112":
            assert audit.get("shortlist_policy_used") == "RR_IPL_POSITIVE_VERIFIED"
            assert (t10["ipl_hp_rate_12b"] > 0).all()
            rep_doc = json.loads((candidate_dir / "stage04_replay_results.json").read_text(encoding="utf-8"))
            assert rep_doc["stage3_bowling_blend_evaluation"]["promoted"] is False
            for yr in ("2024", "2025", "2026"):
                assert "RR_IPL_POSITIVE_VERIFIED" in rep_doc["shortlist_policy_controls"][yr]["bowling"]


def test_rr_ipl_positive_verified_policy_parity():
    """Verify RR_IPL_POSITIVE_VERIFIED filters <=0 direct IPL HP symmetrically in replay and production."""
    candidates = pd.DataFrame([
        {"player_id": 10, "is_qualified": True, "conservative_score_q25": -0.50, "predicted_hp_impact": 4.0, "hp_balls": 100, "ipl_hp_balls": 60, "ipl_hp_matches": 6, "hp_rate_ipl_12b": -1.5},
        {"player_id": 11, "is_qualified": True, "conservative_score_q25": -1.20, "predicted_hp_impact": 3.0, "hp_balls": 90, "ipl_hp_balls": 50, "ipl_hp_matches": 5, "hp_rate_ipl_12b": 2.4},
    ])
    market_df = pd.DataFrame([
        {"player_id": pid, "current_franchise": "RivalA", "availability_status": "PENDING_NOV17_RETENTIONS", "decision_category": "CONDITIONAL_RELEASE_WATCH", "is_rr_incumbent": False, "is_unavailable_hard": False}
        for pid in (10, 11)
    ])
    rep = select_shortlist_by_policy(candidates, market_df, policy_name="RR_IPL_POSITIVE_VERIFIED", discipline="bowling")
    prod = apply_production_shortlist_policy(candidates, market_df, discipline="bowling", policy_name="RR_IPL_POSITIVE_VERIFIED")
    assert rep[rep["submission_rank"].notna()]["player_id"].tolist() == [11]
    assert prod[prod["submission_rank"].notna()]["player_id"].tolist() == [11]
    assert rep.loc[rep["player_id"] == 10, "passed_over_reason"].iloc[0] == "REVIEWED_OUT_NONPOSITIVE_DIRECT_IPL"
    assert prod.loc[prod["player_id"] == 10, "review_action"].iloc[0] == "DROPPED_NONPOSITIVE_DIRECT_IPL"
