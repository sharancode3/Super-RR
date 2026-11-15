"""Audit the working shortlist against season transfer and graded pressure challengers."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from rr_pressure import auction_challenger as model


BASE = {"batting": "previous", "bowling": "adjusted_ensemble"}
COLUMNS = [
    "match_id", "match_date", "comp_tier", "match_phase", "venue_id", "striker_id", "bowler_id",
    "batting_order", "pace_or_spin", "is_legal_ball", "is_reliability_eligible", "batting_impact",
    "bowling_impact", "is_high_pressure_15", "is_high_pressure_20", "is_high_pressure_25",
]


def graded_profiles(ledger, role):
    """Average three nested pressure definitions while preserving delivery totals."""
    profiles = [model.make_match_profiles(ledger, role, size) for size in (15, 20, 25)]
    reference = profiles[1].copy()
    reference[model.SCORE_FIELDS] = sum(p[model.SCORE_FIELDS] for p in profiles) / len(profiles)
    return reference


def forecast(history, graded, matchup, pool, cut, role, fitted, graded_fit, weights=None):
    features = model.enrich(history, cut, weights).reindex(pool.index)
    baseline = model.predict(features, fitted)["ensemble"]
    soft = model.player_features(graded, cut, fixture_weights=weights).reindex(pool.index)
    graded_forecast = model.predict(soft, graded_fit)["ensemble"]
    if role == "bowling":
        adjusted = model.adjust_for_opposition(matchup, cut, pool.index, weights)
        opponent_rating = .80 * adjusted + .20 * features["transfer_skill"]
        baseline = .60 * baseline + .40 * opponent_rating
        graded_forecast = .60 * graded_forecast + .40 * opponent_rating
    ipl_form = features["recent_pressure"] * .75 + features["recent_ordinary"] * .25
    workload = np.sqrt(features["recent_balls"].clip(lower=0))
    return pd.DataFrame({
        "incumbent": baseline,
        "graded": graded_forecast,
        "graded_blend": .5 * baseline + .5 * graded_forecast,
        "ipl_form_blend": .75 * baseline + .25 * ipl_form,
    }), features, workload


def rank_scores(predictions, features, workload):
    priority = predictions.apply(lambda score: model.penalize_sparse_evidence(score, features))
    # Test a moderate recency tie-breaker without assigning unobserved players zero skill.
    priority["recent_evidence"] = priority["incumbent"] + .75 * workload / (workload + 6)
    return priority


def select_recipe(result):
    forward = result[result["lane"].eq("forward") & result["season"].lt(2026)]
    metrics = forward.groupby("recipe").agg(
        impact=("target_per_slot", "mean"), pressure=("pressure_per_slot", "mean"),
        assessed=("assessed_picks", "sum"), mae=("mae", "mean"),
    )
    reference = metrics.loc["incumbent"]
    year_gains = forward.groupby(["recipe", "season"])["target_per_slot"].mean().unstack()
    year_floor = year_gains.sub(year_gains.loc["incumbent"]).min(axis=1)
    eligible = metrics[
        metrics["impact"].gt(reference["impact"] + .15) & metrics["pressure"].ge(reference["pressure"] - .10)
        & metrics["assessed"].ge(reference["assessed"] - 2) & metrics["mae"].le(reference["mae"] + .10)
        & year_floor.ge(-.10)
    ]
    return eligible["impact"].idxmax() if len(eligible) else "incumbent"


def fitness_pool(pool, role):
    # Rana's return to match load remains unverified after a full IPL season out.
    # Keep Ngidi's rehabilitation contingency separate given the longer auction horizon.
    return pool.drop(index=29888, errors="ignore") if role == "bowling" else pool


def evaluate(ledger, dim, registry, markets, role, previous_report, previous_slate, previous_metrics, count):
    history = model.make_match_profiles(ledger, role, 20)
    graded = graded_profiles(ledger, role)
    matchup = model.matchup_history(ledger, role, 20)
    roles = model.role_history(ledger, role)
    labels = model.previous_labels(ledger, history, roles, role)
    graded_labels = model.previous_labels(ledger, graded, roles, role)
    windows = [(y, start, end, "forward") for y, start, end in model.rolling_windows(ledger) if y >= 2024]
    windows += [(y, pd.Timestamp(start), pd.Timestamp(y + 1, 1, 1), "auction") for y, start in model.AUCTIONS.items()]
    rows = []
    for year, start, end, lane in windows:
        form = model.enrich(history, start)
        pool = model.add_deployment(form.loc[model.usable(form, model.role_support(roles, role, start))], dim, roles, role, start)
        if lane == "auction":
            market = model.historical_market(markets, year)
            pool = pool.loc[pool.index.isin(market.loc[~market["is_unavailable_hard"], "player_id"])]
        fit = model.fit_models(labels.loc[labels["end"].le(start)])
        soft_fit = model.fit_models(graded_labels.loc[graded_labels["end"].le(start)])
        predictions, features, workload = forecast(history, graded, matchup, pool, start, role, fit, soft_fit)
        priorities = rank_scores(predictions, features, workload)
        actual = model.realized_ipl(history, start, end).reindex(pool.index)
        for recipe, priority in priorities.items():
            assessed = actual.reindex(model.candidate_order(priority, pool, role))
            error = actual["target"] - predictions["incumbent" if recipe == "recent_evidence" else recipe]
            rows.append({
                "role": role, "season": year, "cutoff": start.date().isoformat(), "lane": lane, "recipe": recipe,
                "assessed_picks": assessed["target"].count(), "mae": error.abs().mean(),
                "target_per_slot": assessed["target"].sum() / 10,
                "pressure_per_slot": assessed["actual_pressure"].sum() / 10,
            })
    result = pd.DataFrame(rows)
    keys = ["season", "cutoff", "lane"]
    metrics = ["assessed_picks", "mae", "target_per_slot", "pressure_per_slot"]
    expected = previous_report.loc[previous_report["role"].eq(role) & previous_report["recipe"].eq(BASE[role])]
    replay = result.loc[result["recipe"].eq("incumbent")]
    pd.testing.assert_frame_equal(replay.set_index(keys)[metrics].sort_index(), expected.set_index(keys)[metrics].sort_index())
    selected = select_recipe(result)
    cutoff = pd.Timestamp(model.MARKET_AS_OF)
    full = model.candidate_pool(model.enrich(history, cutoff), dim, roles, role, cutoff, registry)
    market = model.auction_case(full, registry)
    pool = fitness_pool(market, role)
    fit, soft_fit = model.fit_models(labels), model.fit_models(graded_labels)
    predictions, features, workload = forecast(history, graded, matchup, pool, cutoff, role, fit, soft_fit)
    order = rank_scores(predictions, features, workload)[selected]
    picks = model.candidate_order(order, pool, role)
    if len(picks) != 10:
        raise ValueError(f"Expected ten distinct {role} picks")

    if role == "batting" and selected == "incumbent":
        old = previous_slate.loc[previous_slate["role"].eq(role)].set_index("player_id")
        if picks != old.index.to_list():
            raise ValueError("Saved batting bootstrap does not match the rebuilt shortlist")
        np.testing.assert_allclose(order.reindex(picks), old["priority"])
        stability = old["top10_stability"]
        exact = previous_metrics["summary"][role]["exact_slate_frequency"]
        count = previous_metrics["fixture_bootstrap_replicates"]
    elif selected == "incumbent":
        draws = model.stability(history, matchup, pool, cutoff, role, BASE[role], fit, model.fit_challengers(pd.concat([
            frame for year in range(2023, 2027) for frame in model.dense_labels(history, roles, role, year)
        ])), count)
        stability = pd.Series(draws.mean(axis=0), index=pool.index)
        exact = float((draws == pool.index.isin(picks)).all(axis=1).mean())
    else:
        fixtures = [group["match_id"].unique() for _, group in history.groupby([history["match_date"].dt.year, "comp_tier"])]
        rng = np.random.default_rng(2027)
        draws = []
        for _ in range(count):
            weights = pd.Series(np.concatenate([rng.choice(ids, len(ids), replace=True) for ids in fixtures])).value_counts()
            pred, sample, work = forecast(history, graded, matchup, pool, cutoff, role, fit, soft_fit, weights)
            replay_picks = model.candidate_order(rank_scores(pred, sample, work)[selected], pool, role)
            draws.append(pool.index.isin(replay_picks))
        draws = np.asarray(draws)
        stability = pd.Series(draws.mean(axis=0), index=pool.index)
        exact = float((draws == pool.index.isin(picks)).all(axis=1).mean())

    predicted = predictions["incumbent" if selected == "recent_evidence" else selected]
    stats = ["player_name", "deployment", "ipl_balls", "recent_balls", "ipl_pressure_observed", "ipl_ordinary_observed"]
    candidates = pool[stats].assign(priority=order, prediction=predicted).sort_values("priority", ascending=False)
    slate = candidates.loc[picks].assign(
        top10_stability=stability, role=role, rank=range(1, 11), recipe=selected,
    ).reset_index()
    status = registry.set_index("player_id")["availability_status"]
    slate["route"] = np.where(slate["player_id"].map(status).eq("INCUMBENT_RR"), "RR squad decision", "If available at auction")
    summaries = dict(recipe=selected, resamples=count, exact_set_frequency=exact,
                     median_top10_stability=float(slate["top10_stability"].median()),
                     minimum_top10_stability=float(slate["top10_stability"].min()),
                     at_least_90=int(slate["top10_stability"].ge(.90).sum()))
    return result, slate, candidates.assign(role=role).reset_index(), summaries


def run(args):
    args.out_dir.mkdir(parents=True, exist_ok=True)
    verified = json.loads((args.previous_dir / "validation.json").read_text(encoding="utf-8"))
    for name, record in verified["input_manifest"].items():
        if model.compute_sha256(args.raw_dir / name) != record["sha256"]:
            raise ValueError(f"Verified raw input mismatch for {name}")
    ledger_file = args.baseline_dir / "delivery_impact_ledger.csv"
    if model.compute_sha256(ledger_file) != verified["ledger_sha256"]:
        raise ValueError("Verified ledger mismatch")
    ledger = pd.read_csv(ledger_file, usecols=COLUMNS, parse_dates=["match_date"], low_memory=False)
    ledger = ledger.loc[ledger["is_reliability_eligible"] & ledger["match_phase"].isin(model.PHASES)]
    dim = pd.read_csv(args.baseline_dir / "player_dimension.csv")
    mapping = pd.read_csv(args.raw_dir / "competition_team_player_mapping.csv")
    registry = model.build_ipl_availability_registry(raw_dir=args.raw_dir, as_of_date=model.MARKET_AS_OF)
    markets = model.match_market(Path(__file__).parent / "data" / "historical_ipl_auction.csv", mapping)
    previous_report = pd.read_csv(args.previous_dir / "comparison.csv")
    previous_slate = pd.read_csv(args.previous_dir / "auction_shortlist.csv")
    reports, slates, pools, summaries = [], [], [], {}
    for role in BASE:
        report, slate, pool, summary = evaluate(
            ledger, dim, registry, markets, role, previous_report, previous_slate, verified, args.bootstrap,
        )
        reports.append(report)
        slates.append(slate)
        pools.append(pool)
        summaries[role] = summary
        print(role, summary, flush=True)
    for name, frames in [("final_comparison", reports), ("final_shortlist", slates), ("candidate_evidence", pools)]:
        pd.concat(frames, ignore_index=True).to_csv(args.out_dir / f"{name}.csv", index=False)
    (args.out_dir / "uncertainty.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("raw-dir", "baseline-dir", "previous-dir", "out-dir"):
        parser.add_argument(f"--{flag}", type=Path, required=True)
    parser.add_argument("--bootstrap", type=int, default=1000)
    options = parser.parse_args()
    if options.bootstrap < 2:
        parser.error("At least two resamples are required")
    with threadpool_limits(limits=1):
        run(options)
