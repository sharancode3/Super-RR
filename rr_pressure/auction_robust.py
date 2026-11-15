"""Forward validation and franchise-neutral RR recruitment recommendations."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from rr_pressure.auction_review import CORE_WATCH, MARKET_AS_OF, match_market, production_slots
from rr_pressure.availability import build_ipl_availability_registry
from rr_pressure.manifest import compute_sha256


PHASES = ("POWERPLAY", "MIDDLE", "DEATH")
TIER_WEIGHT = {"IPL": 1.0, "T20I": 0.25, "INTERNATIONAL": 0.25, "EMERGING": 0.10}
MODELS = ("ordinary", "pressure", "pooled", "recent", "ridge", "boosted", "ensemble", "hybrid", "form_blend")
FEATURES = [
    "ordinary", "pressure", "recent_pressure", "recent_ordinary", "pressure_lift",
    "log_ipl_pressure", "log_effective_pressure", "log_pressure_matches", "log_ipl_ordinary",
    "pp_rate", "middle_rate", "death_rate", "pp_share", "middle_share", "death_share",
]
TARGET_WEIGHT = 0.75
SCORE_FIELDS = ["hp_balls", "hp_impact", "ordinary_balls", "ordinary_impact"]
AUCTION_CORE_EVIDENCE = {
    5039: "RCB captain in the 2026 title win",
    4260: "2026 retained SRH specialist finisher",
    1758: "2026 retained SRH senior pace option",
    3628: "2026 Purple Cap winner for Gujarat",
}


def make_match_profiles(ledger, role, threshold):
    """Keep extras in the impact numerator and count only legal workload."""
    player = "striker_id" if role == "batting" else "bowler_id"
    outcome = f"{role}_impact"
    hp = ledger[f"is_high_pressure_{threshold}"]
    work = ledger[["match_id", "match_date", "comp_tier", "match_phase", "venue_id", player]].copy()
    work = work.rename(columns={player: "player_id"})
    work["hp_balls"] = (ledger["is_legal_ball"] & hp).astype(int)
    work["ordinary_balls"] = (ledger["is_legal_ball"] & ~hp).astype(int)
    work["hp_impact"] = ledger[outcome].where(hp, 0)
    work["ordinary_impact"] = ledger[outcome].where(~hp, 0)
    groups = ["player_id", "match_id", "match_date", "comp_tier", "match_phase", "venue_id"]
    return work.groupby(groups, observed=True, dropna=False)[SCORE_FIELDS].sum().reset_index()


def rolling_windows(ledger):
    ipl = ledger.loc[ledger["comp_tier"].eq("IPL"), "match_date"]
    for season in range(2023, 2027):
        dates = sorted(ipl.loc[ipl.dt.year.eq(season)].unique())
        middle = pd.Timestamp(dates[len(dates) // 2])
        for start, end in ((pd.Timestamp(season, 1, 1), middle), (middle, pd.Timestamp(season + 1, 1, 1))):
            yield season, start, end


def role_history(ledger, role):
    if role == "batting":
        positions = ledger.loc[ledger["batting_order"].between(1, 11), [
            "match_date", "match_id", "striker_id", "batting_order",
        ]].drop_duplicates(["match_id", "striker_id"]).rename(columns={"striker_id": "player_id"})
        return positions.assign(top7=positions["batting_order"].le(7))
    style = ledger["pace_or_spin"].str.casefold().eq("spin") & ledger["is_legal_ball"]
    return ledger.assign(spin=style).groupby(["match_date", "match_id", "bowler_id"], observed=True).agg(
        balls=("is_legal_ball", "sum"), spin=("spin", "sum"),
    ).reset_index().rename(columns={"bowler_id": "player_id"})


def role_support(history, role, cutoff):
    prior = history[history["match_date"].lt(cutoff)].sort_values("match_date")
    recent = prior.groupby("player_id", observed=True).tail(15)
    if role == "batting":
        top_seven = prior.groupby("player_id")["top7"].agg(["sum", "mean"])
        latest = recent.groupby("player_id")["top7"].mean()
        return top_seven["sum"].ge(5) & top_seven["mean"].ge(.5) & latest.ge(.5)
    workload = prior.groupby("player_id")["balls"].agg(["sum", "count"])
    return workload["sum"].ge(72) & workload["count"].ge(6) & workload["sum"].div(workload["count"]).ge(10.8)


def player_features(history, cutoff, half_life=540, fixture_weights=None):
    """Form features on matches strictly earlier than the requested cutoff."""
    before = history[history["match_date"].lt(cutoff)].copy()
    age = (cutoff - before["match_date"]).dt.days
    ipl = before["comp_tier"].eq("IPL")
    recent = age.le(400) & ipl
    mult = 1 if fixture_weights is None else before["match_id"].map(fixture_weights).fillna(0)
    decay = np.exp2(-age / half_life) * mult
    before["weight"] = decay * before["comp_tier"].map(TIER_WEIGHT).fillna(.05)
    weighted = before[SCORE_FIELDS].mul(before["weight"], axis=0).groupby(before["player_id"]).sum()
    ipl_observations = before[SCORE_FIELDS].mul(mult, axis=0)
    direct = ipl_observations.loc[ipl].groupby(before["player_id"]).sum()
    new = ipl_observations.loc[recent].groupby(before["player_id"]).sum()
    features = pd.DataFrame(index=weighted.index)
    for source, name in ((direct, "ipl"), (new, "recent")):
        features[f"{name}_balls"] = source["hp_balls"].reindex(features.index, fill_value=0)
        features[f"{name}_pressure_observed"] = 12 * source["hp_impact"] / source["hp_balls"].replace(0, np.nan)
        features[f"{name}_ordinary_observed"] = 12 * source["ordinary_impact"] / source["ordinary_balls"].replace(0, np.nan)
    features["ordinary"] = 12 * weighted["ordinary_impact"] / (weighted["ordinary_balls"] + 48)
    features["pressure"] = (12 * weighted["hp_impact"] + 24 * features["ordinary"]) / (weighted["hp_balls"] + 24)
    features["recent_pressure"] = (12 * new["hp_impact"] + 24 * features["pressure"]) / (new["hp_balls"] + 24)
    features["recent_ordinary"] = (12 * new["ordinary_impact"] + 48 * features["ordinary"]) / (new["ordinary_balls"] + 48)
    features["recent_pressure"] = features["recent_pressure"].fillna(features["pressure"])
    features["recent_ordinary"] = features["recent_ordinary"].fillna(features["ordinary"])
    features["pressure_lift"] = features["pressure"] - features["ordinary"]
    observed = before["hp_balls"].gt(0) & (mult > 0)
    fixtures = before.loc[observed].groupby("player_id")["match_id"].nunique()
    features["log_ipl_pressure"] = np.log1p(features["ipl_balls"])
    features["log_ipl_ordinary"] = np.log1p(direct["ordinary_balls"]).reindex(features.index, fill_value=0)
    features["log_effective_pressure"] = np.log1p(weighted["hp_balls"])
    features["log_pressure_matches"] = np.log1p(fixtures.reindex(features.index, fill_value=0))
    features["effective_balls"] = weighted["hp_balls"]
    features["pressure_matches"] = fixtures.reindex(features.index, fill_value=0)
    deployment = ipl_observations["ordinary_balls"] + ipl_observations["hp_balls"]
    ipl_phase = deployment.loc[ipl].groupby([before["player_id"], before["match_phase"]], observed=True).sum()
    other_phase = deployment.groupby([before["player_id"], before["match_phase"]], observed=True).sum()
    ipl_phase = ipl_phase.unstack().reindex(index=features.index, columns=PHASES)
    other_phase = other_phase.unstack().reindex(index=features.index, columns=PHASES)
    ipl_phase = ipl_phase.where(ipl_phase.sum(axis=1).gt(0), other_phase, axis=0).fillna(0)
    for phase, key in zip(PHASES, ("pp", "middle", "death")):
        part = before[before["match_phase"].eq(phase)]
        sums = part[["hp_balls", "hp_impact"]].mul(part["weight"], axis=0).groupby(part["player_id"]).sum()
        sums = sums.reindex(features.index, fill_value=0)
        features[f"{key}_rate"] = (12 * sums["hp_impact"] + 24 * features["pressure"]) / (sums["hp_balls"] + 24)
        features[f"{key}_share"] = ipl_phase[phase] / ipl_phase.sum(axis=1).clip(lower=1)
    features[FEATURES] = features[FEATURES].fillna(0)
    return features


def usable(features, support):
    direct = features["ipl_balls"].ge(12) & features["pressure_matches"].ge(4)
    transfer = features["effective_balls"].ge(22) & features["pressure_matches"].ge(10)
    return support.reindex(features.index, fill_value=False) & (direct | transfer)


def realized_ipl(history, start, end):
    window = history.loc[
        history["match_date"].ge(start) & history["match_date"].lt(end) & history["comp_tier"].eq("IPL")
    ]
    actual = window.groupby("player_id")[SCORE_FIELDS].sum()
    actual = actual[actual["hp_balls"].ge(12) & actual["ordinary_balls"].ge(12)].copy()
    actual["actual_pressure"] = 12 * actual["hp_impact"] / actual["hp_balls"]
    actual["actual_ordinary"] = 12 * actual["ordinary_impact"] / actual["ordinary_balls"]
    actual["target"] = TARGET_WEIGHT * actual["actual_pressure"] + (1 - TARGET_WEIGHT) * actual["actual_ordinary"]
    return actual


def fit_models(training):
    x = training[FEATURES]
    y = training["target"]
    weights = np.sqrt(training["hp_balls"].clip(upper=72))
    ridge = make_pipeline(StandardScaler(), Ridge(alpha=40)).fit(x, y, ridge__sample_weight=weights)
    boosted = HistGradientBoostingRegressor(
        max_iter=100, max_leaf_nodes=7, min_samples_leaf=22, l2_regularization=6, random_state=2027,
    ).fit(x, y, sample_weight=weights)
    return ridge, boosted


def predict(features, fitted=None):
    result = pd.DataFrame(index=features.index)
    result["ordinary"] = features["ordinary"]
    result["pressure"] = features["pressure"]
    result["pooled"] = (
        .45 * features["pressure"] + .30 * features["recent_pressure"]
        + .15 * features["ordinary"] + .10 * features["recent_ordinary"]
    )
    result["recent"] = .60 * features["recent_pressure"] + .20 * features["pressure"] + .20 * features["recent_ordinary"]
    if fitted is not None:
        ridge, boosted = fitted
        result["ridge"] = ridge.predict(features[FEATURES])
        result["boosted"] = boosted.predict(features[FEATURES])
        result["ensemble"] = .50 * result["pooled"] + .30 * result["ridge"] + .20 * result["boosted"]
        result["hybrid"] = .70 * result["pooled"] + .30 * result["ridge"]
        result["form_blend"] = .45 * result["recent"] + .35 * result["pressure"] + .20 * result["boosted"]
    return result


def score_runs(ledger, history, roles, role, dim):
    snapshots, results = [], []
    for season, start, end in rolling_windows(ledger):
        features = player_features(history, start)
        use = usable(features, role_support(roles, role, start))
        actual = realized_ipl(history, start, end)
        current = features[use].join(actual, how="inner").assign(end=end)
        if season >= 2024:
            training = pd.concat([frame for frame in snapshots if frame["end"].max() <= start])
            if training["end"].max() > start:
                raise ValueError("Training labels cross the forecast cutoff")
            cohort = add_deployment(features[use], dim, roles, role, start)
            predictions = predict(cohort, fit_models(training))
            for model in MODELS:
                scores = penalize_sparse_evidence(predictions[model], cohort)
                ranked = candidate_order(scores, cohort, role)
                observed = current.reindex(ranked)
                joined = current.join(predictions[model].rename("prediction"))
                err = joined["prediction"] - joined["target"]
                correlation = (
                    joined["prediction"].corr(joined["target"], method="spearman")
                    if joined["prediction"].nunique() > 1 else np.nan
                )
                results.append({
                    "role": role, "season": season, "cutoff": str(start.date()), "model": model,
                    "training_rows": len(training), "assessed_candidates": len(joined),
                    "assessed_picks": observed["target"].count(),
                    "mean_assessed_target": observed["target"].mean(),
                    "target_per_slot": observed["target"].sum() / 10,
                    "pressure_per_slot": observed["actual_pressure"].sum() / 10,
                    "mae": err.abs().mean(), "spearman": correlation,
                })
        snapshots.append(current)
    return pd.concat(snapshots), pd.DataFrame(results)


def choose_model(replays):
    selection = replays.loc[
        replays["season"].lt(2026) & ~replays["model"].isin(["ordinary", "ridge", "boosted"])
    ]
    summaries = selection.groupby("model").agg(
        utility=("target_per_slot", "mean"), coverage=("assessed_picks", "sum"), mae=("mae", "mean"),
    )
    qualified = summaries.loc[summaries["coverage"].ge(16)]
    if qualified.empty:
        raise ValueError("Fewer than four assessable picks per validation window for all pressure recipes")
    return qualified.sort_values(["utility", "coverage", "mae"], ascending=[False, False, True]).index[0]


def candidate_order(scores, profiles, role, apply_fit=True):
    """Diversify only to cover distinct RR roles, using the same score in every group."""
    names = scores.dropna().sort_index().sort_values(ascending=False, kind="stable")
    groups = profiles["deployment"].reindex(names.index)
    if not apply_fit:
        return names.head(10).index.to_list()
    minimum = {"FINISHER": 2, "MIDDLE": 2} if role == "batting" else {"DEATH": 3, "SPIN": 2, "POWERPLAY": 2}
    selected = set()
    for group, count in minimum.items():
        selected.update(groups[groups.eq(group)].head(count).index)
    selected.update(names[~names.index.isin(selected)].head(10 - len(selected)).index)
    return names[names.index.isin(selected)].index.to_list()


def score_candidate_set(features, model, fitted):
    return penalize_sparse_evidence(predict(features, fitted)[model], features)


def penalize_sparse_evidence(scores, features):
    # Sparse transferable evidence raises the uncertainty penalty without blocking the player.
    return scores - 2.5 / np.sqrt(1 + features["effective_balls"] / 12) - 0.9 / np.sqrt(1 + features["recent_balls"] / 18)


def add_deployment(features, dim, roles, role, cutoff):
    result = features.join(dim.set_index("player_id")["player_name"]).dropna(subset=["player_name"])
    if role == "batting":
        result["deployment"] = np.select(
            [result["pp_share"].ge(.45), result["death_share"].ge(.25)], ["POWERPLAY", "FINISHER"], default="MIDDLE",
        )
    else:
        bowling = roles[roles["match_date"].lt(cutoff)].groupby("player_id")[["balls", "spin"]].sum()
        is_spin = bowling["spin"].div(bowling["balls"].clip(lower=1)).gt(.5).reindex(result.index, fill_value=False)
        result["deployment"] = np.select(
            [is_spin, result["death_share"].ge(.30),
             result["pp_share"].ge(.38)], ["SPIN", "DEATH", "POWERPLAY"], default="MIDDLE",
        )
    return result


def candidate_pool(features, dim, roles, role, cutoff, registry):
    supported = usable(features, role_support(roles, role, cutoff))
    unavailable = registry.loc[registry["availability_status"].isin({
        "RETIRED_FROM_IPL", "INELIGIBLE_PAKISTAN_IPL_POLICY",
    }), "player_id"]
    return add_deployment(features.loc[supported & ~features.index.isin(unavailable)], dim, roles, role, cutoff)


def bootstrap(history, full, actionable, cutoff, role, model, fitted, count):
    by_group = [
        group["match_id"].unique() for _, group in history.groupby(
            [history["match_date"].dt.year, "comp_tier"], observed=True, sort=True,
        )
    ]
    rng = np.random.default_rng(2027)
    score_matrix, selections, scenario_selections, ranks = [], [], [], []
    for _ in range(count):
        weights = pd.Series(np.concatenate([rng.choice(group, size=len(group), replace=True) for group in by_group])).value_counts()
        features = player_features(history, cutoff, fixture_weights=weights).reindex(full.index)
        scores = score_candidate_set(features, model, fitted)
        score_matrix.append(scores.to_numpy())
        selections.append(full.index.isin(candidate_order(scores, full, role)))
        scenario_selections.append(full.index.isin(candidate_order(scores.reindex(actionable.index), actionable, role)))
        ranks.append(scores.rank(ascending=False, method="min").to_numpy())
    samples = np.array(score_matrix)
    # The range of each centered score draw bounds its errors across every pairwise contrast.
    center = score_candidate_set(full, model, fitted).to_numpy()
    crit = np.quantile(np.ptp(samples - center, axis=1), .95)
    difference = center[:, None] - center[None, :]
    rank_min = 1 + (difference > crit).sum(axis=0)
    rank_max = len(center) - (difference < -crit).sum(axis=0)
    return np.array(selections), np.array(scenario_selections), np.array(ranks), rank_min, rank_max


def run(raw, base, out, count):
    manifest = json.loads((base / "input_manifest.json").read_text(encoding="utf-8"))
    hashes = {name: compute_sha256(raw / name) for name in manifest["files"]}
    if any(digest != manifest["files"][name]["sha256"] for name, digest in hashes.items()):
        raise ValueError("Delivery ledger inputs do not match the supplied raw data")
    columns = [
        "match_id", "match_date", "comp_tier", "match_phase", "venue_id", "striker_id", "bowler_id",
        "batting_order", "pace_or_spin", "is_legal_ball", "is_reliability_eligible", "batting_impact", "bowling_impact",
        "is_high_pressure_15", "is_high_pressure_20", "is_high_pressure_25",
    ]
    ledger = pd.read_csv(base / "delivery_impact_ledger.csv", usecols=columns, parse_dates=["match_date"], low_memory=False)
    ledger = ledger[ledger["is_reliability_eligible"] & ledger["match_phase"].isin(PHASES)]
    dim = pd.read_csv(base / "player_dimension.csv")
    registry = build_ipl_availability_registry(raw_dir=raw, as_of_date=MARKET_AS_OF)
    mapping = pd.read_csv(raw / "competition_team_player_mapping.csv")
    official = match_market(Path(__file__).parent / "data" / "historical_ipl_auction.csv", mapping)
    slots = production_slots(official, mapping)
    cutoff = pd.Timestamp(MARKET_AS_OF)
    all_replays, all_candidates, scenario_records, exact, target_lists = [], [], [], {}, []
    out.mkdir(parents=True, exist_ok=True)

    for role in ("batting", "bowling"):
        roles = role_history(ledger, role)
        tables = {threshold: make_match_profiles(ledger, role, threshold) for threshold in (15, 20, 25)}
        hist = tables[20]
        training, replays = score_runs(ledger, hist, roles, role, dim)
        chosen = choose_model(replays)
        final_fit = fit_models(training)
        main = candidate_pool(player_features(hist, cutoff), dim, roles, role, cutoff, registry)
        scores = score_candidate_set(main, chosen, final_fit)
        order = candidate_order(scores, main, role)
        if len(order) != 10:
            raise ValueError(f"Shortlist has {len(order)} players for {role}")
        variants = {
            "performance_only": candidate_order(scores, main, role, apply_fit=False),
            "historical_one_year": candidate_order(
                score_candidate_set(player_features(hist, cutoff, half_life=365).reindex(main.index), chosen, final_fit), main, role,
            ),
            "historical_two_years": candidate_order(
                score_candidate_set(player_features(hist, cutoff, half_life=730).reindex(main.index), chosen, final_fit), main, role,
            ),
        }
        for threshold in (15, 25):
            pressure_history = tables[threshold]
            threshold_training, _ = score_runs(ledger, pressure_history, roles, role, dim)
            threshold_fit = fit_models(threshold_training)
            features = player_features(pressure_history, cutoff).reindex(main.index)
            variants[f"pressure_{threshold}"] = candidate_order(
                score_candidate_set(features, chosen, threshold_fit), main, role,
            )
        for model in MODELS:
            variants[f"model_{model}"] = candidate_order(score_candidate_set(main, model, final_fit), main, role)
        for scenario, ids in variants.items():
            scenario_records.extend({
                "role": role, "scenario": scenario, "rank": rank, "player_id": pid,
                "player_name": main.loc[pid, "player_name"], "on_main_list": pid in order,
            } for rank, pid in enumerate(ids, start=1))
        counts = pd.Series([pid for ids in variants.values() for pid in ids]).value_counts()
        main["scenario_inclusions"] = main.index.map(counts).fillna(0).astype(int)
        main["scenario_count"] = len(variants)
        main["role"] = role
        main["model"] = chosen
        main["score"] = scores
        main["shortlist_rank"] = main.index.map({pid: i for i, pid in enumerate(order, 1)})
        main["slot"] = main.index.map(slots).fillna("UNKNOWN")
        main = main.join(registry.set_index("player_id")[["current_franchise", "availability_status", "fitness_clearance_status"]])
        franchise = mapping.loc[mapping["comp_id"].eq(3298)].drop_duplicates("player_id").set_index("player_id")["team_name"]
        main["current_franchise"] = main["current_franchise"].fillna(pd.Series(main.index.map(franchise), index=main.index))
        likely_core = main.index.isin([*CORE_WATCH, *AUCTION_CORE_EVIDENCE]) | main["availability_status"].isin({
            "BENCHMARK_UNTOUCHABLE", "CONTRACTED_RIVAL_CORE", "CONTRACTED_RIVAL_BENCHMARK",
        })
        main["conditional_risk"] = np.select(
            [main["availability_status"].eq("INCUMBENT_RR"), likely_core,
             main["availability_status"].str.contains("FITNESS_CLEARANCE|NOC_AND_POLICY|REGISTRATION_UNVERIFIED", na=False)],
            ["RR_INCUMBENT", "RIVAL_CORE_SCENARIO", "CLEARANCE_OR_REGISTRATION"], default="RELEASE_OR_LISTING_UNCONFIRMED",
        )
        main["additional_auction_core_evidence"] = main.index.map(AUCTION_CORE_EVIDENCE)
        actionable = main[~main["conditional_risk"].isin(["RIVAL_CORE_SCENARIO", "CLEARANCE_OR_REGISTRATION"])]
        actionable_order = candidate_order(actionable["score"], actionable, role)
        selection, scenario_selection, rank_samples, lower, upper = bootstrap(
            hist, main, actionable, cutoff, role, chosen, final_fit, count,
        )
        main["bootstrap_top10"] = selection.mean(axis=0)
        main["auction_scenario_bootstrap_top10"] = scenario_selection.mean(axis=0)
        main["bootstrap_rank_p025"] = np.quantile(rank_samples, .025, axis=0, method="lower").astype(int)
        main["bootstrap_rank_p975"] = np.quantile(rank_samples, .975, axis=0, method="higher").astype(int)
        main["rank95_low_unconstrained"] = lower
        main["rank95_high_unconstrained"] = upper
        exact[role] = {
            "model": chosen,
            "whole_slate_frequency": float((selection == main.index.isin(order)).all(axis=1).mean()),
            "players_at_95_percent": int((main.loc[order, "bootstrap_top10"] >= .95).sum()),
            "auction_scenario_whole_slate_frequency": float(
                (scenario_selection == main.index.isin(actionable_order)).all(axis=1).mean(),
            ),
            "auction_scenario_players_at_95_percent": int((main.loc[actionable_order, "auction_scenario_bootstrap_top10"] >= .95).sum()),
            "eligible_players": len(main),
        }
        target_lists.append(main.loc[actionable_order].assign(auction_case_rank=range(1, 1 + len(actionable_order))).reset_index())
        all_candidates.append(main.reset_index())
        all_replays.append(replays)
        print(role, exact[role], flush=True)

    candidates = pd.concat(all_candidates, ignore_index=True)
    picks = candidates[candidates["shortlist_rank"].notna()].sort_values(["role", "shortlist_rank"])
    if picks.groupby("role")["player_id"].nunique().to_dict() != {"batting": 10, "bowling": 10}:
        raise ValueError("Expected ten distinct picks per discipline")
    auction = pd.concat(target_lists, ignore_index=True)
    if auction.groupby("role")["player_id"].nunique().to_dict() != {"batting": 10, "bowling": 10}:
        raise ValueError("Expected ten distinct auction-scenario picks per discipline")
    candidates.to_csv(out / "candidate_evidence.csv", index=False)
    picks.to_csv(out / "shortlist.csv", index=False)
    auction.to_csv(out / "auction_scenario.csv", index=False)
    pd.concat(all_replays, ignore_index=True).to_csv(out / "rolling_validation.csv", index=False)
    pd.DataFrame(scenario_records).to_csv(out / "sensitivity.csv", index=False)
    (out / "review.json").write_text(json.dumps({
        "raw_hashes": hashes, "fixture_bootstrap_replicates": count, "seed": 2027,
        "holdout_role": "2026 measured after model selection on 2024–25. These seasons were examined in prior project runs.",
        "confidence_scope": "Conditional on the ledger, fitted supervised coefficients, player pool and selection rule. Marginal bootstrap rank ranges describe resampled ranks. Approximate simultaneous rank sets bound score differences across eligible players and exclude 2027 distribution shift.",
        "method": "Model chosen on four 2024–25 forward half-season windows. At least 16 of 40 picks must be assessable. 2026 stays out of model choice. Opponent franchise has no role in the primary score or pool. Auction scenario excludes curated low-availability core and clearance risks without adjusting sporting forecasts.",
        "results": exact,
    }, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("raw-dir", "baseline-dir", "out-dir"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--bootstrap", type=int, default=300)
    args = parser.parse_args()
    if args.bootstrap < 2:
        parser.error("At least two bootstrap replicates are required")
    with threadpool_limits(limits=1):
        run(args.raw_dir, args.baseline_dir, args.out_dir, args.bootstrap)


if __name__ == "__main__":
    main()
