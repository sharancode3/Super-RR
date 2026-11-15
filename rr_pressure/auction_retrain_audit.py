"""Rebuild and compare RR forecasts independently on both supplied pack versions."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from rr_pressure import auction_challenger as model
from rr_pressure import auction_lock as prior


RECIPES = ("incumbent", "pressure_only", "split_targets", "split_targets_blend", "ipl_only")


def ledger_from_rebuild(raw, rebuild):
    manifest = json.loads((rebuild / "input_manifest.json").read_text(encoding="utf-8"))
    progress = json.loads((rebuild / "round1_progress.json").read_text(encoding="utf-8"))
    for name, info in manifest["files"].items():
        if model.compute_sha256(raw / name) != info["sha256"]:
            raise ValueError(f"Rebuild raw file hash differs for {name}")
    ledger_path = rebuild / "delivery_impact_ledger.csv"
    stages = progress["stages"]
    for stage in ("00", "01", "02", "03", "04", "05", "06", "07"):
        if stages[stage]["status"] != "PASS":
            raise ValueError(f"Rebuild failed stage {stage}")
    digest = model.compute_sha256(ledger_path)
    if digest != stages["07"]["output_fingerprints"][ledger_path.name]:
        raise ValueError("Rebuilt delivery ledger hash differs from the recorded preprocessing output")
    fields = [*prior.COLUMNS, "innings", "pre_legal_balls", "innings_ball_num", "pressure_reference_cutoff", "is_bowler_wicket", "is_run_out"]
    ledger = pd.read_csv(ledger_path, usecols=fields, parse_dates=["match_date", "pressure_reference_cutoff"], low_memory=False)
    eligible = ledger.loc[ledger["is_reliability_eligible"] & ledger["match_phase"].isin(model.PHASES)].copy()
    innings_keys = ["match_id", "innings"]
    if ledger.duplicated([*innings_keys, "innings_ball_num"]).any():
        raise ValueError("Each scored delivery must be unique within its innings")
    ordered = ledger.sort_values([*innings_keys, "innings_ball_num"])
    before_ball = ordered.groupby(innings_keys)["is_legal_ball"].cumsum() - ordered["is_legal_ball"]
    if not np.array_equal(before_ball, ordered["pre_legal_balls"]):
        raise ValueError("Illegal deliveries must not advance legal-ball state")
    if eligible["pressure_reference_cutoff"].isna().any() or eligible["pressure_reference_cutoff"].gt(eligible["match_date"]).any():
        raise ValueError("Pressure references must predate the deliveries they label")
    if (ledger["is_bowler_wicket"] & ledger["is_run_out"]).any():
        raise ValueError("Run-outs must not be credited to the bowler")
    if (eligible["is_high_pressure_15"] & ~eligible["is_high_pressure_20"]).any() or (eligible["is_high_pressure_20"] & ~eligible["is_high_pressure_25"]).any():
        raise ValueError("Pressure thresholds must be nested")
    return eligible, {"raw_deliveries": len(ledger), "eligible_deliveries": len(eligible),
                      "eligible_fixtures": eligible["match_id"].nunique(), "ledger_sha256": digest}


def completed_ipl_labels(labels, cutoff, season_ends):
    closing_season = labels["end"].sub(pd.Timedelta(days=1)).dt.year
    played_through = closing_season.map(season_ends).add(pd.Timedelta(days=1))
    label_end = labels["end"].where(played_through.isna() | labels["end"].lt(played_through), played_through)
    return labels.loc[label_end.le(cutoff)]


def fit_split_targets(training, features):
    """Learn usual impact and the pressure uplift with separate sample weights."""
    x = training[model.FEATURE_SET]
    predict_x = features[model.FEATURE_SET]
    ordinary_balls, pressure_balls = training["ordinary_balls"], training["hp_balls"]
    harmonic_balls = ordinary_balls * pressure_balls / (ordinary_balls + pressure_balls)
    result = []
    for y, support in (
        (training["actual_ordinary"], ordinary_balls),
        (training["actual_pressure"] - training["actual_ordinary"], harmonic_balls),
    ):
        fit = make_pipeline(model.HistoricalBounds(), StandardScaler(), Ridge(alpha=60))
        fit.fit(x, y, ridge__sample_weight=np.sqrt(support.clip(upper=72)))
        result.append(fit.predict(predict_x))
    return result[0] + .75 * result[1]


def context(ledger, role):
    history = model.make_match_profiles(ledger, role, 20)
    roles = model.role_history(ledger, role)
    ipl_history = history.loc[history["comp_tier"].eq("IPL")]
    ends = ipl_history.groupby(ipl_history["match_date"].dt.year)["match_date"].max()
    old_labels = model.previous_labels(ledger, history, roles, role)
    ipl_labels = model.previous_labels(ledger, ipl_history, roles, role)
    dense = pd.concat([snapshot for year in range(2023, 2027) for snapshot in model.dense_labels(history, roles, role, year)])
    matchups = model.matchup_history(ledger, role, 20) if role == "bowling" else None
    return history, roles, ipl_history, ends, old_labels, ipl_labels, dense, matchups


def train_variants(data, cutoff, pool, role):
    history, _, local, ends, old, local_old, dense, matchups = data
    features = model.enrich(history, cutoff).reindex(pool.index)
    original = model.fit_models(completed_ipl_labels(old, cutoff, ends))
    baseline = model.predict(features, original)["ensemble"]
    if role == "bowling":
        adjusted = model.adjust_for_opposition(matchups, cutoff, pool.index)
        baseline = .60 * baseline + .40 * (.80 * adjusted + .20 * features["transfer_skill"])
    train = dense.loc[dense["assessable"] & dense["end"].le(cutoff)]
    split = fit_split_targets(train, features)
    # IPL-only uses the full prospect cohort. Cold starts fall back to a peer prior of zero impact.
    local_features = model.player_features(local, cutoff).reindex(pool.index).fillna(0)
    local_fit = model.fit_models(completed_ipl_labels(local_old, cutoff, ends))
    local_estimate = model.predict(local_features, local_fit)["ensemble"].where(local_features["effective_balls"].gt(0), 0)
    estimates = pd.DataFrame({
        "incumbent":baseline, "pressure_only":features["pressure"], "split_targets":split,
        "split_targets_blend":.70 * baseline + .30 * split, "ipl_only":local_estimate,
    })
    order = estimates.apply(lambda pred: model.penalize_sparse_evidence(pred, features))
    return estimates, order, len(train)


def recent_ipl_evidence(history, cutoff):
    recent = history.loc[history["comp_tier"].eq("IPL") & history["match_date"].dt.year.eq(cutoff.year)
                         & history["match_date"].lt(cutoff)]
    fields = ["hp_balls", "hp_impact", "ordinary_balls", "ordinary_impact"]
    evidence = recent.groupby("player_id")[fields].sum()
    evidence["pressure_runs_per_12"] = 12 * evidence["hp_impact"] / evidence["hp_balls"].where(evidence["hp_balls"].gt(0))
    evidence["ordinary_runs_per_12"] = 12 * evidence["ordinary_impact"] / evidence["ordinary_balls"].where(evidence["ordinary_balls"].gt(0))
    evidence["observed_pressure_uplift"] = evidence["pressure_runs_per_12"] - evidence["ordinary_runs_per_12"]
    return evidence.drop(columns=["hp_impact", "ordinary_impact"])


def assess(ledger, dim, historical, pool_source, role, source):
    data = context(ledger, role)
    history, roles = data[:2]
    windows = [(y, s, e, "forward") for y,s,e in model.rolling_windows(ledger) if y >= 2024]
    windows += [(y, pd.Timestamp(s), pd.Timestamp(y+1,1,1), "auction") for y,s in model.AUCTIONS.items()]
    trials = []
    for year, start, end, lane in windows:
        features = model.player_features(history, start)
        sufficient = model.usable(features, model.role_support(roles, role, start))
        pool = model.add_deployment(features.loc[sufficient], dim, roles, role, start)
        if lane == "auction":
            market = model.historical_market(historical, year)
            pool = pool.loc[pool.index.isin(market.loc[~market["is_unavailable_hard"], "player_id"])]
        estimates, order, rows = train_variants(data, start, pool, role)
        actual = model.realized_ipl(history, start, end)
        same = actual.reindex(pool.index)
        for recipe in RECIPES:
            selected = model.candidate_order(order[recipe], pool, role)
            selected_actual = same.reindex(selected)
            errors = (same["target"] - estimates[recipe]).abs()
            trials.append({"source":source,"season":year,"role":role,"lane":lane,"cutoff":start.date().isoformat(),
                           "recipe":recipe,"training_rows":rows,"candidate_count":len(pool),"mae":errors.mean(),
                           "assessed":selected_actual["target"].count(),"impact":selected_actual["target"].sum()/10,
                           "pressure":selected_actual["actual_pressure"].sum()/10})
    cutoff = pd.Timestamp(model.MARKET_AS_OF)
    pool = pool_source.loc[pool_source["role"].eq(role) & pool_source["base_eligible"]].set_index("player_id")
    features = model.player_features(history, cutoff)
    supported = model.usable(features, model.role_support(roles, role, cutoff))
    pool = pool.loc[supported.reindex(pool.index, fill_value=False)]
    predictions, priorities, _ = train_variants(data, cutoff, pool, role)
    deployment = model.add_deployment(features.reindex(pool.index), dim, roles, role, cutoff)["deployment"]
    pool = pool.assign(deployment=deployment)
    evidence = recent_ipl_evidence(history, cutoff)
    ranked = []
    for recipe in RECIPES:
        score = priorities[recipe]
        selected = model.candidate_order(score, pool, role)
        if len(selected) != 10:
            raise ValueError(f"Could not find ten role-supported {role} picks for {source}")
        ranked.append(pool.loc[selected, ["player_name", "deployment"]].join(evidence).assign(
            source=source,role=role,recipe=recipe,rank=range(1, 11),priority=score.reindex(selected),
            predicted_impact=predictions.loc[selected,recipe],
        ).reset_index())
    return pd.DataFrame(trials), pd.concat(ranked, ignore_index=True)


def promote(comparison, role):
    forward = comparison.loc[comparison["role"].eq(role) & comparison["lane"].eq("forward")
                             & comparison["source"].eq("recorded_extras") & comparison["season"].lt(2026)]
    summary = forward.groupby("recipe")[["impact", "pressure", "mae", "assessed"]].mean()
    gains = summary.subtract(summary.loc["incumbent"])
    by_year = forward.groupby(["recipe", "season"])["impact"].mean().unstack()
    consistent = by_year.subtract(by_year.loc["incumbent"]).min(axis=1).ge(-.10)
    qualified = gains.loc[gains["impact"].ge(.15) & gains["pressure"].ge(-.10)
                          & gains["mae"].le(.10) & gains["assessed"].ge(-.50) & consistent]
    return qualified["impact"].idxmax() if len(qualified) else "incumbent"


def run(args):
    args.output.mkdir(parents=True, exist_ok=True)
    candidates = pd.read_csv(args.previous_dir / "auction_recruitment_pool.csv")
    reports, rankings, provenance = [], [], {}
    for source, raw, rebuild in (("attached", args.attached_raw, args.attached_rebuild),
                                 ("recorded_extras", args.corrected_raw, args.corrected_rebuild)):
        ledger, provenance[source] = ledger_from_rebuild(raw, rebuild)
        dimension = pd.read_csv(rebuild / "player_dimension.csv")
        mapping = pd.read_csv(raw / "competition_team_player_mapping.csv")
        market = model.match_market(Path(__file__).parent / "data" / "historical_ipl_auction.csv", mapping)
        for role in ("batting", "bowling"):
            report, slate = assess(ledger, dimension, market, candidates, role, source)
            reports.append(report)
            rankings.append(slate)
            print(source, role, list(slate.loc[slate["recipe"].eq("incumbent"), "player_name"]), flush=True)
    results = pd.concat(reports, ignore_index=True)
    orders = pd.concat(rankings, ignore_index=True)
    choices = {role:promote(results, role) for role in ("batting", "bowling")}
    final = [orders.loc[orders["source"].eq("recorded_extras") & orders["role"].eq(role) & orders["recipe"].eq(choose)]
             for role, choose in choices.items()]
    results.to_csv(args.output / "retraining_comparison.csv", index=False)
    orders.to_csv(args.output / "rankings_by_source_and_model.csv", index=False)
    pd.concat(final, ignore_index=True).to_csv(args.output / "recommended_rankings.csv", index=False)
    (args.output / "retraining_audit.json").write_text(json.dumps({"sources":provenance,"selected":choices},indent=2), encoding="utf-8")
    print(choices, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("attached-raw", "attached-rebuild", "corrected-raw", "corrected-rebuild", "previous-dir", "output"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    with threadpool_limits(limits=1):
        run(parser.parse_args())
