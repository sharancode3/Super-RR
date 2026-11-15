"""Test auction recommendations under competing forecasts and compounded availability changes."""

import argparse
import json
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from rr_pressure import auction_challenger as model
from rr_pressure import auction_lock as prior


RELIABILITY_FIELDS = [*model.OPPORTUNITY_FEATURES, "ordinary", "pressure", "recent_pressure",
                      "pressure_downside", "pressure_repeatability", "pressure_lift"]

# RCB confirmed Dayal would miss IPL 2026. Reconsider him on confirmed 2027 availability.
PENDING_AVAILABILITY = {7322}
def fit_opportunity(training):
    features = training[RELIABILITY_FIELDS]
    assessable = training["assessable"]
    positive = assessable & training["actual_pressure"].gt(0) & training["target"].gt(0)
    # Non-observation contributes zero measurable value per offered slot. Skill remains conditional on playing.
    direct_target = training["target"].where(assessable, 0)
    return [
        make_pipeline(model.HistoricalBounds(), StandardScaler(), LogisticRegression(C=.2)).fit(features, assessable),
        make_pipeline(model.HistoricalBounds(), StandardScaler(), LogisticRegression(C=.2)).fit(features, positive),
        make_pipeline(model.HistoricalBounds(), StandardScaler(), Ridge(alpha=60)).fit(features, direct_target),
    ]


def forecast_options(context, cutoff, pool, training, production=False):
    history, graded, matchup, labels, graded_labels, role = context
    old_fit = model.fit_models(labels if production else labels.loc[labels["end"].le(cutoff)])
    soft_fit = model.fit_models(graded_labels if production else graded_labels.loc[graded_labels["end"].le(cutoff)])
    predicted, features, workload = prior.forecast(history, graded, matchup, pool, cutoff, role, old_fit, soft_fit)
    basic = prior.rank_scores(predicted, features, workload)
    x = features[RELIABILITY_FIELDS]
    opportunity_fit, positive_fit, slot_fit = fit_opportunity(training)
    chance = opportunity_fit.predict_proba(x)[:, 1]
    positive = positive_fit.predict_proba(x)[:, 1]
    direct = slot_fit.predict(x)
    scores = pd.DataFrame({
        "incumbent": basic["incumbent"],
        "expected_impact": model.penalize_sparse_evidence(predicted["incumbent"] * chance, features),
        "positive_impact": basic["incumbent"] + 4 * (positive - .5),
        "positive_impact_blend": basic["incumbent"] + 2 * (positive - .5),
        "direct_value": model.penalize_sparse_evidence(pd.Series(direct, index=pool.index), features),
        "robust_forecasts": basic[["incumbent", "graded", "ipl_form_blend"]].quantile(.25, axis=1),
    })
    end_season = history.loc[history["comp_tier"].eq("IPL")].groupby(history["match_date"].dt.year)["match_date"].max()
    actual_close = labels["end"].sub(pd.Timedelta(days=1)).dt.year.map(end_season).add(pd.Timedelta(days=1))
    completed = labels.loc[labels["end"].where(labels["end"].lt(actual_close), actual_close).le(cutoff)]
    if production or len(completed) == int(labels["end"].le(cutoff).sum()):
        scores["completed_ipl_season"] = scores["incumbent"]
    else:
        corrected = model.predict(features, model.fit_models(completed))["ensemble"]
        if role == "bowling":
            # Reuse the identical matchup rating from the incumbent when updating the fit window.
            corrected = predicted["incumbent"] + .60 * (corrected - model.predict(features, old_fit)["ensemble"])
        scores["completed_ipl_season"] = model.penalize_sparse_evidence(corrected, features)
    return scores, pd.Series(chance, index=pool.index), pd.Series(positive, index=pool.index)


def score_shortlist(actual, selected):
    picks = actual.reindex(selected)
    assessed = picks["target"].notna()
    return {
        "assessed": int(assessed.sum()), "positive": int((picks["target"].gt(0) & picks["actual_pressure"].gt(0)).sum()),
        "impact": picks["target"].sum() / len(selected), "pressure": picks["actual_pressure"].sum() / len(selected),
        "observed_mean": picks["target"].mean(),
    }


def promote(replays):
    forward = replays.loc[replays["lane"].eq("forward") & replays["season"].lt(2026)]
    auction = replays.loc[replays["lane"].eq("auction") & replays["season"].lt(2026)]
    rates = forward.groupby("recipe")[["impact", "pressure", "assessed", "positive"]].mean()
    gains = rates.subtract(rates.loc["incumbent"])
    auction_scores = auction.set_index("recipe")["impact"]
    winners = gains.loc[
        gains["impact"].ge(.15) & gains["pressure"].ge(-.10) & gains["assessed"].ge(-.50)
        & gains["positive"].ge(0) & auction_scores.ge(auction_scores.loc["incumbent"] - .10)
    ]
    return winners["impact"].idxmax() if len(winners) else "incumbent"


def stress_options(pool, scores, role):
    primary = model.candidate_order(scores["incumbent"], pool, role)
    outsiders = pool["route"].ne("RR squad decision").reindex(primary)
    restricted = pool["route"].ne("RR squad decision") & ~pool["country"].eq("India")
    highest_outside = outsiders[outsiders].index[:2].to_list()
    domestic_only = pool.index[restricted].to_list()
    scenarios = {
        "current_market": [], "two_highest_external_picks_unavailable": highest_outside,
        "no_new_overseas_slot": domestic_only,
        "no_new_overseas_slot_and_top_outside_picks_unavailable": sorted(set(domestic_only + highest_outside)),
    }
    if role == "bowling":
        scenarios.update({"ngidi_unavailable": [4641],
                          "gujarat_keeps_both_and_ngidi_unavailable": [5944, 2633, 4641],
                          "five_external_bowlers_unavailable": [5944, 2633, 4641, 2320, 1566]})
    else:
        scenarios.update({"parag_and_inglis_unavailable": [6423, 4736],
                          "inglis_and_connolly_unavailable": [4736, 8654]})
    rows = []
    for label, excluded in scenarios.items():
        eligible = pool.drop(index=excluded, errors="ignore")
        for recipe, values in scores.items():
            ranked = values.reindex(eligible.index)
            picks = model.candidate_order(ranked, eligible, role)
            if len(picks) != 10:
                raise ValueError(f"Expected ten {role} picks in {label}")
            rows.append(eligible.loc[picks, ["player_name", "deployment", "route"]].assign(
                recipe=recipe, scenario=label, rank=range(1,11), priority=ranked.reindex(picks), role=role,
            ).reset_index())
    return pd.concat(rows, ignore_index=True)


def backup_coverage(pool, scores, role):
    """Count where reserves enter when one to three outside targets become unavailable."""
    original = model.candidate_order(scores, pool, role)
    outside = pool.loc[original, "route"].ne("RR squad decision")
    outside_ids = outside.index[outside]
    records = []
    for count in (1, 2, 3):
        cases = list(combinations(outside_ids, count))
        frequency = {}
        for excluded in cases:
            eligible = pool.drop(index=list(excluded))
            selected = model.candidate_order(scores.reindex(eligible.index), eligible, role)
            if len(selected) != 10 or set(selected).intersection(excluded):
                raise ValueError("An availability stress case produced an invalid shortlist")
            for player in set(selected).difference(original):
                frequency[player] = frequency.get(player, 0) + 1
        for player, included in frequency.items():
            records.append({"role":role,"removed_picks":count,"cases":len(cases),"reserve_id":player,
                            "reserve":pool.at[player,"player_name"],"role_coverage":pool.at[player,"deployment"],
                            "cases_selected":included})
    return pd.DataFrame(records).sort_values(["removed_picks", "cases_selected", "reserve_id"], ascending=[True, False, True])


def compare_pairs(history, pool, scores, role):
    recent = history.loc[history["comp_tier"].eq("IPL") & history["match_date"].dt.year.eq(2026)]
    by_fixture = recent.groupby(["player_id", "match_id"])[["hp_balls", "hp_impact"]].sum()
    exposure = by_fixture.assign(played=by_fixture["hp_balls"].gt(0)).groupby("player_id").agg(
        balls=("hp_balls", "sum"), impact=("hp_impact", "sum"),
        fixtures=("played", "sum"), largest_fixture_balls=("hp_balls", "max"),
    )
    exposure["pressure_per_12"] = 12 * exposure["impact"] / exposure["balls"].replace(0, np.nan)
    # Drop one match at a time from observed 2026 evidence to expose single-fixture dependence.
    jackknife = by_fixture.loc[by_fixture["hp_balls"].gt(0)].join(exposure[["balls", "impact"]], on="player_id")
    remaining_balls = jackknife["balls"] - jackknife["hp_balls"]
    jackknife["rate"] = 12 * (jackknife["impact"] - jackknife["hp_impact"]) / remaining_balls.replace(0, np.nan)
    exposure = exposure.join(jackknife.groupby("player_id")["rate"].agg(loo_min="min", loo_max="max"))
    picked = model.candidate_order(scores["incumbent"], pool, role)
    rows = []
    ranks = scores.rank(ascending=False, method="min")
    for index, player in enumerate(picked, start=1):
        role_pool = pool.index[pool["deployment"].eq(pool.at[player, "deployment"])]
        backups = scores.loc[role_pool.difference(picked), "incumbent"].nlargest(2).index
        candidate_ids = [player, *backups]
        evidence = pool.loc[candidate_ids, ["player_name", "deployment", "route"]].join(exposure).join(
            scores["incumbent"].rename("priority")
        ).join(ranks.add_suffix("_rank"))
        rows.append(evidence.assign(slot=index, original_pick=evidence.index == player, role=role).reset_index())
    return pd.concat(rows, ignore_index=True)


def run(args):
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((args.verified_dir / "validation.json").read_text(encoding="utf-8"))
    ledger_file = args.baseline_dir / "delivery_impact_ledger.csv"
    if model.compute_sha256(ledger_file) != manifest["ledger_sha256"]:
        raise ValueError("Ledger differs from the audited source")
    for name, info in manifest["input_manifest"].items():
        if model.compute_sha256(args.raw_dir / name) != info["sha256"]:
            raise ValueError(f"Raw file differs from the audited source: {name}")
    ledger = pd.read_csv(ledger_file, usecols=prior.COLUMNS, parse_dates=["match_date"], low_memory=False)
    ledger = ledger.loc[ledger["is_reliability_eligible"] & ledger["match_phase"].isin(model.PHASES)]
    dim = pd.read_csv(args.baseline_dir / "player_dimension.csv")
    mapping = pd.read_csv(args.raw_dir / "competition_team_player_mapping.csv")
    markets = model.match_market(Path(__file__).parent / "data" / "historical_ipl_auction.csv", mapping)
    latest_market = markets.loc[markets["season"].eq(2026) & markets["player_id"].notna()]
    nationalities = latest_market.drop_duplicates("player_id").set_index("player_id")["country"]
    squad_ids = mapping.loc[mapping["comp_name"].eq("IPL 2026"), "player_id"]
    supported_routes = set(latest_market["player_id"]) | set(squad_ids)
    stored = pd.read_csv(args.decision_dir / "candidate_evidence.csv")
    baseline_replays = pd.read_csv(args.decision_dir / "final_comparison.csv")
    registry = model.build_ipl_availability_registry(raw_dir=args.raw_dir, as_of_date=model.MARKET_AS_OF)
    statuses = registry.set_index("player_id")["availability_status"]
    all_replays, all_scenarios, all_pairs, recs, backups, chosen = [], [], [], [], [], {}
    for role in prior.BASE:
        history = model.make_match_profiles(ledger, role, 20)
        graded = prior.graded_profiles(ledger, role)
        matchup = model.matchup_history(ledger, role, 20)
        roles = model.role_history(ledger, role)
        context = (history, graded, matchup, model.previous_labels(ledger, history, roles, role),
                   model.previous_labels(ledger, graded, roles, role), role)
        training = pd.concat([frame for year in range(2023, 2027) for frame in model.dense_labels(history, roles, role, year)])
        windows = [(y, s, e, "forward") for y, s, e in model.rolling_windows(ledger) if y >= 2024]
        windows += [(y, pd.Timestamp(s), pd.Timestamp(y+1, 1, 1), "auction") for y, s in model.AUCTIONS.items()]
        results = []
        for year, cutoff, end, lane in windows:
            features = model.enrich(history, cutoff)
            pool = model.add_deployment(features.loc[model.usable(features, model.role_support(roles, role, cutoff))], dim, roles, role, cutoff)
            if lane == "auction":
                market = model.historical_market(markets, year)
                pool = pool.loc[pool.index.isin(market.loc[~market["is_unavailable_hard"], "player_id"])]
            past = training.loc[training["end"].le(cutoff)]
            scores, chance, positive = forecast_options(context, cutoff, pool, past)
            actual = model.realized_ipl(history, cutoff, end)
            aligned = actual.reindex(pool.index)
            label = aligned["target"].gt(0) & aligned["actual_pressure"].gt(0)
            previous_rate = (past["target"].gt(0) & past["actual_pressure"].gt(0)).mean()
            for recipe, ratings in scores.items():
                picks = model.candidate_order(ratings, pool, role)
                results.append(dict(role=role, season=year, cutoff=cutoff.date().isoformat(), lane=lane, recipe=recipe,
                                    positive_brier=np.mean((positive - label) ** 2), prevalence_brier=np.mean((previous_rate - label) ** 2),
                                    assessable_brier=np.mean((chance - aligned["target"].notna()) ** 2),
                                    **score_shortlist(actual, picks)))
        result = pd.DataFrame(results)
        baseline = baseline_replays.loc[baseline_replays["role"].eq(role) & baseline_replays["recipe"].eq("incumbent")]
        keys = ["season", "cutoff", "lane"]
        metrics = ["assessed", "impact", "pressure"]
        renamed = baseline.rename(columns={"assessed_picks":"assessed", "target_per_slot":"impact", "pressure_per_slot":"pressure"})
        pd.testing.assert_frame_equal(result.query('recipe == "incumbent"').set_index(keys)[metrics].sort_index(), renamed.set_index(keys)[metrics].sort_index())
        selected = promote(result)
        chosen[role] = selected
        all_replays.append(result)
        cutoff = pd.Timestamp(model.MARKET_AS_OF)
        pool = stored.loc[stored["role"].eq(role)].set_index("player_id")
        pool["route"] = np.where(statuses.reindex(pool.index).eq("INCUMBENT_RR"), "RR squad decision", "If available at auction")
        pool["country"] = nationalities.reindex(pool.index)
        if training["end"].gt(cutoff).any() or history.loc[history["comp_tier"].eq("IPL"), "match_date"].max() >= cutoff:
            raise ValueError("Production fits require completed IPL outcomes")
        scores, chance, positive = forecast_options(context, cutoff, pool, training, production=True)
        np.testing.assert_allclose(scores["incumbent"], pool["priority"], atol=1e-10)
        eligible = (pool.index.isin(supported_routes) | pool["route"].eq("RR squad decision")) & ~pool.index.isin(PENDING_AVAILABILITY)
        pool = pool.loc[eligible]
        scores = scores.reindex(pool.index)
        scenarios = stress_options(pool, scores, role)
        all_scenarios.append(scenarios)
        all_pairs.append(compare_pairs(history, pool, scores, role))
        backups.append(backup_coverage(pool, scores[selected], role))
        slate = scenarios.loc[scenarios["recipe"].eq(selected) & scenarios["scenario"].eq("current_market")].copy()
        recs.append(slate)
        print(role, selected, list(slate["player_name"]), flush=True)
    for name, frames in [("historical_comparison", all_replays), ("scenario_rankings", all_scenarios),
                         ("same_role_comparisons", all_pairs), ("recommended_rankings", recs),
                         ("exhaustive_backups", backups)]:
        pd.concat(frames, ignore_index=True).to_csv(args.output / f"{name}.csv", index=False)
    (args.output / "selected_methods.json").write_text(json.dumps(chosen, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("raw-dir", "baseline-dir", "verified-dir", "decision-dir", "output"):
        parser.add_argument(f"--{flag}", type=Path, required=True)
    with threadpool_limits(limits=1):
        run(parser.parse_args())
