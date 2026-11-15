"""Check the live pack's recorded extras and the reconstructed score state."""

from pathlib import Path

import pytest

from rr_pressure.config import PipelineConfig
from rr_pressure.ledger import build_scoreboard_ledger


def test_recorded_extras_reconstruct_targets_and_bowler_charges():
    raw_dir = Path("6af458274c1e8_data_pack")
    if not raw_dir.is_dir():
        pytest.skip("Updated Unstop pack is unavailable")
    ledger, _, _, coverage = build_scoreboard_ledger(PipelineConfig(raw_dir=raw_dir))
    assert coverage["extras_audit"]["extras1_runs_schema"] == "recorded_primary_runs"
    assert coverage["pack_reconstructed_target_chases"] > 0
    assert coverage["proxy_target_chases"] == 0
    assert all(row["discrepancy_official_minus_proxy"] == 0 for row in coverage["verified_target_audit"])

    multi_wides = ledger[ledger["is_wide"] & ledger["extras1_runs"].gt(1)]
    assert len(multi_wides) == 607
    assert (~multi_wides["is_legal_ball"]).all()
    assert multi_wides["bowler_charge_runs"].eq(multi_wides["runs"] + multi_wides["extras1_runs"]).all()
    byes = ledger[ledger["is_bye_legbye"] & ledger["extras1_runs"].gt(1)]
    assert not byes.empty
    assert byes["bowler_charge_runs"].eq(byes["runs"]).all()
    assert ledger["delivery_extras"].eq(ledger["extras1_runs"] + ledger["extras2_secondary_runs"]).all()
    assert ledger["post_team_total_runs"].eq(ledger["pre_team_total_runs"] + ledger["delivery_team_runs"]).all()
