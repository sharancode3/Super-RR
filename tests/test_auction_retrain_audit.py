import pandas as pd

from rr_pressure.auction_retrain_audit import completed_ipl_labels, promote, recent_ipl_evidence
from rr_pressure.cli import build_parser


def test_completed_ipl_outcomes_enter_the_auction_fit_but_not_the_earlier_forecast():
    rows = pd.DataFrame({"end": pd.to_datetime(["2026-05-01", "2027-01-01"])})
    season_ends = pd.Series({2026: pd.Timestamp("2026-05-31")})
    assert completed_ipl_labels(rows, pd.Timestamp("2026-05-20"), season_ends).index.to_list() == [0]
    assert completed_ipl_labels(rows, pd.Timestamp("2026-06-01"), season_ends).index.to_list() == [0, 1]


def test_promotion_compares_verified_source_and_requires_two_season_support():
    comparisons = pd.DataFrame([
        {"role": "bowling", "lane": "forward", "season": season, "source": source, "recipe": recipe,
         "impact": gain, "pressure": gain, "mae": 4., "assessed": 6}
        for season in (2024, 2025, 2026)
        for source in ("attached", "recorded_extras")
        for recipe, gain in [("incumbent", 0.), ("challenger", -.2 if source == "recorded_extras" and season == 2024 else 1.)]
    ])
    assert promote(comparisons, "bowling") == "incumbent"
    comparisons.loc[comparisons["recipe"].eq("challenger"), "impact"] = .2
    assert promote(comparisons, "bowling") == "challenger"


def test_pipeline_prefers_recorded_extras_and_respects_explicit_attachment(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    original = "6af3166e7b922_data_pack"
    corrected = "6af458274c1e8_data_pack"
    assert build_parser().parse_args(["manifest"]).raw_dir == original
    (tmp_path / corrected).mkdir()
    assert build_parser().parse_args(["manifest"]).raw_dir == corrected
    assert build_parser().parse_args(["manifest", "--raw-dir", original]).raw_dir == original


def test_recent_evidence_compares_same_ipl_year_and_preserves_missing_baselines():
    history = pd.DataFrame({
        "player_id": [6, 6, 6, 7, 8],
        "match_date": pd.to_datetime(["2026-04-01", "2026-04-15", "2025-04-01", "2026-04-03", "2026-05-01"]),
        "comp_tier": ["IPL", "T20I", "IPL", "IPL", "IPL"],
        "hp_balls": [3, 3, 3, 6, 3], "hp_impact": [2, 5, 5, 3, 5],
        "ordinary_balls": [9, 9, 9, 0, 9], "ordinary_impact": [3, 6, 6, 0, 6],
    })
    evidence = recent_ipl_evidence(history, pd.Timestamp("2026-04-30"))
    assert evidence.index.to_list() == [6, 7]
    assert evidence.loc[6, "observed_pressure_uplift"] == 4
    assert pd.isna(evidence.loc[7, "observed_pressure_uplift"])
