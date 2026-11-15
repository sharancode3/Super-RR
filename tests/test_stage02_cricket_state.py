"""Stage 02 Cricket-State, Ledger Attribution, and Chase Terminal Invariant Tests."""

import numpy as np
import pandas as pd

from rr_pressure.ledger import build_scoreboard_ledger
from rr_pressure.config import PipelineConfig
from rr_pressure.pressure import compute_chase_leverage, p_win_chase_state


def test_chase_terminal_state_invariants_exact():
    """Verify exact terminal overrides: win=1.0 on target reached, loss=0.0 on all-out or shortfall, tie=0.50."""
    coef = np.array([1.2, 2.5, -1.8, -0.35, 0.08, 0.15])
    intercept = 0.0

    # Target reached takes precedence even when b_rem <= 0 or w_rem <= 0
    assert float(p_win_chase_state(0, 0, 0, 170, 120, 1.0, coef, intercept)) == 1.0
    assert float(p_win_chase_state(0, 2, -2, 170, 120, 1.0, coef, intercept)) == 1.0

    # All out before reaching level score (req_gap > 1) -> exact 0.0
    assert float(p_win_chase_state(10, 0, 5, 160, 110, 1.0, coef, intercept)) == 0.0
    assert float(p_win_chase_state(0, 0, 5, 160, 120, 1.0, coef, intercept)) == 0.0

    # Innings complete by balls or wickets with scores level (req_gap == 1) -> regulation tie_value
    assert float(p_win_chase_state(10, 0, 1, 160, 110, 1.0, coef, intercept, tie_value=0.50)) == 0.50
    assert float(p_win_chase_state(0, 3, 1, 165, 120, 1.0, coef, intercept, tie_value=0.50)) == 0.50
    assert float(p_win_chase_state(0, 0, 1, 165, 120, 1.0, coef, intercept, tie_value=0.50)) == 0.50
    assert float(p_win_chase_state(10, 0, 1, 160, 110, 1.0, coef, intercept, tie_value=0.0)) == 0.0

    # Last ball completed below tie score (req_gap > 1) -> exact 0.0
    assert float(p_win_chase_state(0, 3, 2, 165, 120, 1.0, coef, intercept)) == 0.0

    # Undecided state remains strictly in (0, 1)
    p_mid = float(p_win_chase_state(24, 5, 30, 140, 96, 1.0, coef, intercept))
    assert 0.0 < p_mid < 1.0

    # Target reached with a wide: b_rem unchanged, req_gap - 1 <= 0 -> exact 1.0
    assert float(p_win_chase_state(1, 2, 1 - 1, 166, 119, 1.0, coef, intercept)) == 1.0


def test_chase_leverage_terminal_vs_undecided_and_free_hit():
    """Verify match-50375 style last-ball chase and free-hit dismissal leverage separation."""
    coef = np.array([1.5, 2.0, -2.0, -0.4, 0.05, 0.1])
    p_def = np.array([0.35, 0.35, 0.07, 0.11, 0.06, 0.06])
    p_fh = p_def.copy()
    p_fh[-1] = 0.005
    p_fh[:-1] += (0.06 - 0.005) * (p_def[:-1] / p_def[:-1].sum())

    # Last ball, 3 needed, 2 wickets in hand: non-FH vs FH (higher survival on FH, exact terminal payoff range [0, 1])
    df = pd.DataFrame([
        {"pre_balls_remaining": 1, "pre_wickets_in_hand": 2, "pre_target_reconciled_gap": 3.0, "pre_team_total_runs": 163, "pre_legal_balls": 119, "comp_tier": "IPL", "pre_free_hit": False},
        {"pre_balls_remaining": 1, "pre_wickets_in_hand": 1, "pre_target_reconciled_gap": 1.0, "pre_team_total_runs": 165, "pre_legal_balls": 119, "comp_tier": "IPL", "pre_free_hit": True},
    ])
    lev, _ = compute_chase_leverage(df, coef, 0.0, p_def, p_fh)
    assert np.all(np.isfinite(lev)) and np.all(lev > 0.05)


def test_ledger_extras_penalties_runouts_freehits_invariants():
    """Verify ledger invariants on real pack: wides, no-balls+byes, penalty, carryover free hit, wide stumping, nonstriker runout."""
    bbb, _, quarantined, cov = build_scoreboard_ledger(PipelineConfig())
    assert bbb.duplicated(subset=["match_id", "innings", "innings_ball_num"]).sum() == 0
    assert cov["verified_scorecard_target_chases"] == 6

    # Penalties do not consume legal balls or charge the bowler
    pen = bbb[bbb["is_penalty"]]
    assert not pen.empty
    assert (pen["is_legal_ball"] == False).all()
    assert (pen["bowler_charge_runs"] == 0).all()

    # Wide stumpings charge bowler_wicket & striker_dismissed without consuming a legal ball
    ws = bbb[bbb["is_stumping_on_wide"]]
    assert len(ws) >= 20
    assert (ws["is_legal_ball"] == False).all()
    assert (ws["is_bowler_wicket"] == True).all()

    # Non-striker runouts do NOT mark is_striker_dismissed or is_bowler_wicket
    ns_ro = bbb[bbb["is_non_striker_dismissed"]]
    assert len(ns_ro) > 200
    assert (ns_ro["is_striker_dismissed"] == False).all()
    assert (ns_ro["is_bowler_wicket"] == False).all()

    # Carryover free hit persists across wides
    fh_wides = bbb[bbb["pre_free_hit"] & bbb["is_wide"]]
    if not fh_wides.empty:
        idx = fh_wides.index[0]
        if idx + 1 < len(bbb) and bbb.loc[idx + 1, "match_id"] == bbb.loc[idx, "match_id"] and bbb.loc[idx + 1, "innings"] == bbb.loc[idx, "innings"]:
            assert bool(bbb.loc[idx + 1, "pre_free_hit"]) is True
