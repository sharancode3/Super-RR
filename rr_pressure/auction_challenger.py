"""Compare pressure-aware forecasts and evaluate the resulting RR decisions."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import HuberRegressor, LogisticRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

from rr_pressure.auction_review import AUCTIONS, CORE_WATCH, MARKET_AS_OF, historical_market, match_market
from rr_pressure.auction_robust import (
    AUCTION_CORE_EVIDENCE, FEATURES, PHASES, SCORE_FIELDS, TIER_WEIGHT,
    add_deployment, candidate_order, candidate_pool, fit_models, make_match_profiles,
    penalize_sparse_evidence, player_features, predict, realized_ipl, role_history, role_support,
    rolling_windows, usable,
)
from rr_pressure.availability import build_ipl_availability_registry
from rr_pressure.manifest import compute_sha256


RECIPES = (
    "previous", "ordinary", "phase_pool", "dynamic", "ridge", "huber", "boost", "blend",
    "consensus", "opportunity", "opportunity_phase", "joint_shrinkage", "joint_ensemble", "median_blend",
    "adjusted_matchups", "adjusted_ensemble",
)
CHALLENGERS = RECIPES[2:]
EXTRA = [
    "ipl_skill", "transfer_skill", "short_form", "phase_pool", "dynamic",
    "pressure_downside", "pressure_repeatability", "recent_ipl_workload", "recent_ipl_matches", "ipl_days",
]
FEATURE_SET = [*FEATURES, *EXTRA]
OPPORTUNITY_FEATURES = [
    "recent_ipl_workload", "recent_ipl_matches", "ipl_days",
    "log_ipl_pressure", "log_ipl_ordinary", "log_effective_pressure", "pp_share", "middle_share", "death_share",
]


class HistoricalBounds(BaseEstimator, TransformerMixin):
    """Prevent tiny early cohorts from extrapolating extreme feature values."""

    def fit(self, x, y=None):
        values = np.asarray(x, dtype=float)
        self.lower_, self.upper_ = np.quantile(values, [.025, .975], axis=0)
        return self

    def transform(self, x):
        return np.clip(np.asarray(x, dtype=float), self.lower_, self.upper_)


def joint_shrinkage(weighted, index):
    """Fit ordinary ability and its pressure interaction jointly with Gaussian shrinkage."""
    ordinary = weighted["ordinary_balls"].to_numpy()
    pressure = weighted["hp_balls"].to_numpy()
    rhs_ordinary = weighted["ordinary_impact"].to_numpy() * 12
    rhs_pressure = weighted["hp_impact"].to_numpy() * 12
    # Precision of two player effects. A pressure-specific deviation needs stronger evidence.
    a = ordinary + pressure + 48
    b = pressure
    c = pressure + 60
    determinant = a * c - b * b
    level = (c * (rhs_ordinary + rhs_pressure) - b * rhs_pressure) / determinant
    lift = (a * rhs_pressure - b * (rhs_ordinary + rhs_pressure)) / determinant
    return pd.Series(level + .75 * lift, index=weighted.index).reindex(index, fill_value=0)


def matchup_history(ledger, role, threshold):
    actor, opponent = ("striker_id", "bowler_id") if role == "batting" else ("bowler_id", "striker_id")
    cols = [actor, opponent, "venue_id", "match_date", "match_id", "comp_tier"]
    frame = ledger[cols].rename(columns={actor: "player", opponent: "opponent"}).copy()
    frame["pressure"] = ledger[f"is_high_pressure_{threshold}"]
    frame["impact"] = ledger[f"{role}_impact"]
    frame["balls"] = ledger["is_legal_ball"].astype(int)
    return frame.groupby([*frame.columns[:-2]], observed=True, dropna=False)[["impact", "balls"]].sum().reset_index()


def adjust_for_opposition(history, cutoff, candidates, fixture_weights=None):
    """Jointly estimate player, pressure interaction, opponent and ground effects on IPL stints."""
    before = history.loc[history["match_date"].lt(cutoff) & history["comp_tier"].eq("IPL")].copy()
    if fixture_weights is not None:
        before["multiplicity"] = before["match_id"].map(fixture_weights).fillna(0)
        before = before.loc[before["multiplicity"].gt(0)]
    if before.empty:
        return pd.Series(0., index=candidates)
    one_hot = OneHotEncoder(handle_unknown="ignore").fit(before[["player", "opponent", "venue_id"]])
    player, opponent, venue = (len(column) for column in one_hot.categories_)
    encoded = one_hot.transform(before[["player", "opponent", "venue_id"]])
    main = encoded[:, :player]
    high_pressure = before["pressure"].to_numpy()
    # Less prior variance on the pressure interaction and ground terms.
    model_matrix = hstack([
        main, main.multiply(high_pressure[:, None]) * .7, encoded[:, player:player + opponent] * .7,
        encoded[:, -venue:] * .5, csr_matrix(high_pressure[:, None], dtype=float),
    ], format="csr")
    effective_balls = before["balls"].clip(lower=1)
    decay = np.exp2(-(cutoff - before["match_date"]).dt.days / 540)
    fit = Ridge(alpha=45, solver="lsqr").fit(
        model_matrix, 12 * before["impact"] / effective_balls,
        sample_weight=effective_balls * decay * before.get("multiplicity", 1),
    )
    rating = fit.coef_[:player] + .75 * .7 * fit.coef_[player:2 * player]
    return pd.Series(rating, index=one_hot.categories_[0]).reindex(candidates, fill_value=0)


def enrich(history, cutoff, fixture_weights=None):
    base = player_features(history, cutoff, fixture_weights=fixture_weights)
    past = history.loc[history["match_date"].lt(cutoff)].copy()
    age = (cutoff - past["match_date"]).dt.days
    multiplicity = 1 if fixture_weights is None else past["match_id"].map(fixture_weights).fillna(0)
    tier = past["comp_tier"].map(TIER_WEIGHT).fillna(.05)
    weights = np.exp2(-age / 540) * multiplicity
    ipl = past["comp_tier"].eq("IPL")
    recent_ipl = past.loc[ipl & age.le(400) & (multiplicity > 0)].copy()
    recent_ipl["workload"] = recent_ipl["hp_balls"] + recent_ipl["ordinary_balls"]
    if fixture_weights is not None:
        recent_ipl["workload"] *= multiplicity.loc[recent_ipl.index]
    base["recent_ipl_workload"] = np.log1p(recent_ipl.groupby("player_id")["workload"].sum()).reindex(base.index, fill_value=0)
    base["recent_ipl_matches"] = np.log1p(recent_ipl.groupby("player_id")["match_id"].nunique()).reindex(base.index, fill_value=0)
    last_ipl = past.loc[ipl & (multiplicity > 0)].groupby("player_id")["match_date"].max()
    base["ipl_days"] = (cutoff - last_ipl).dt.days.reindex(base.index).clip(upper=1_080).fillna(1_080) / 365
    for label, mask, shrink in (
        ("ipl_skill", ipl, 24), ("transfer_skill", ~ipl, 48), ("short_form", ipl & age.le(400), 32),
    ):
        agg = past.loc[mask, SCORE_FIELDS].mul(weights[mask], axis=0).groupby(past.loc[mask, "player_id"]).sum()
        agg = agg.reindex(base.index, fill_value=0)
        base[label] = (12 * agg["hp_impact"] + shrink * base["pressure"]) / (agg["hp_balls"] + shrink)
    # Estimate phase-specific skill, then standardize to the player's observed IPL workload.
    base["phase_pool"] = sum(base[key + "_rate"] * base[key + "_share"] for key in ("pp", "middle", "death"))
    # A rapidly changing skill component with continuous shrinkage toward long-run pressure performance.
    current = past[SCORE_FIELDS].mul(np.exp2(-age / 270) * multiplicity * tier, axis=0).groupby(past["player_id"]).sum()
    base["dynamic"] = (12 * current["hp_impact"] + 42 * base["pressure"]) / (current["hp_balls"] + 42)
    match = past[["player_id", "match_id", "hp_balls", "hp_impact"]].copy()
    match[["hp_balls", "hp_impact"]] = match[["hp_balls", "hp_impact"]].mul(weights * tier, axis=0)
    match = match.groupby(["player_id", "match_id"])[["hp_balls", "hp_impact"]].sum().reset_index()
    match = match[match["hp_balls"].gt(0)]
    # Use the number of balls to weight stints, including very short spells.
    match["below"] = match["hp_impact"].clip(upper=0)
    match["above_zero"] = match["hp_balls"].where(match["hp_impact"].gt(0), 0)
    aggregate = match.groupby("player_id")[["hp_balls", "below", "above_zero"]].sum().reindex(base.index, fill_value=0)
    base["pressure_downside"] = (12 * aggregate["below"] - 60) / (aggregate["hp_balls"] + 24)
    base["pressure_repeatability"] = (aggregate["above_zero"] + 12) / (aggregate["hp_balls"] + 24)
    weighted = past[SCORE_FIELDS].mul(weights * tier, axis=0).groupby(past["player_id"]).sum()
    base["joint_shrinkage"] = joint_shrinkage(weighted, base.index)
    return base


def dense_labels(history, roles, role, season, stride=14, horizon=42):
    dates = history.loc[history["comp_tier"].eq("IPL") & history["match_date"].dt.year.eq(season), "match_date"]
    if dates.empty:
        return []
    windows = []
    start = dates.min()
    last = dates.max()
    while start <= last - pd.Timedelta(days=20):
        end = min(start + pd.Timedelta(days=horizon), last + pd.Timedelta(days=1))
        features = enrich(history, start)
        qualified = usable(features, role_support(roles, role, start))
        outcome = realized_ipl(history, start, end)
        window = features[qualified].join(outcome).assign(end=end)
        windows.append(window.assign(assessable=window["target"].notna()))
        start += pd.Timedelta(days=stride)
    return windows


def fit_challengers(training):
    observed = training.loc[training["assessable"]]
    x = observed[FEATURE_SET]
    y = observed["target"]
    weights = np.sqrt(observed["hp_balls"].clip(upper=72))
    opportunity = make_pipeline(HistoricalBounds(), StandardScaler(), LogisticRegression(C=.20, max_iter=500))
    opportunity.fit(training[OPPORTUNITY_FEATURES], training["assessable"])
    return {
        "ridge": make_pipeline(HistoricalBounds(), StandardScaler(), Ridge(alpha=60)).fit(x, y, ridge__sample_weight=weights),
        "huber": make_pipeline(HistoricalBounds(), StandardScaler(), HuberRegressor(alpha=3, epsilon=1.5, max_iter=400)).fit(
            x, y, huberregressor__sample_weight=weights,
        ),
        "boost": HistGradientBoostingRegressor(
            max_iter=90, max_leaf_nodes=7, min_samples_leaf=24, l2_regularization=8, random_state=2027,
        ).fit(x, y, sample_weight=weights),
    }, opportunity


def forecasts(features, previous_fit, fitted):
    regressors, opportunity = fitted
    predictions = pd.DataFrame(index=features.index)
    predictions["previous"] = predict(features, previous_fit)["ensemble"]
    predictions["ordinary"] = features["ordinary"]
    predictions["phase_pool"] = .50 * features["phase_pool"] + .25 * features["ipl_skill"] + .25 * features["ordinary"]
    predictions["dynamic"] = .50 * features["dynamic"] + .25 * features["short_form"] + .25 * features["ordinary"]
    x = features[FEATURE_SET]
    for name, model in regressors.items():
        predictions[name] = model.predict(x)
    predictions["blend"] = .40 * predictions["dynamic"] + .35 * predictions["huber"] + .25 * predictions["boost"]
    predictions["consensus"] = .65 * predictions["previous"] + .20 * predictions["phase_pool"] + .15 * predictions["dynamic"]
    predictions["opportunity"] = predictions["previous"]
    predictions["opportunity_phase"] = predictions["consensus"]
    predictions["joint_shrinkage"] = features["joint_shrinkage"]
    predictions["joint_ensemble"] = .65 * predictions["previous"] + .35 * predictions["joint_shrinkage"]
    predictions["median_blend"] = predictions[["previous", "dynamic", "phase_pool", "joint_shrinkage", "boost"]].median(axis=1)
    predictions["adjusted_matchups"] = .80 * features["adjusted_matchups"] + .20 * features["transfer_skill"]
    predictions["adjusted_ensemble"] = .60 * predictions["previous"] + .40 * predictions["adjusted_matchups"]
    chance = pd.Series(opportunity.predict_proba(features[OPPORTUNITY_FEATURES])[:, 1], index=features.index)
    return predictions, chance


def priorities(predictions, chance, features):
    order = predictions.apply(lambda scores: penalize_sparse_evidence(scores, features))
    # Deployment likelihood affects auction priority. The impact forecast stays conditional on playing.
    order[["opportunity", "opportunity_phase"]] = order[["opportunity", "opportunity_phase"]].add(
        2.5 * (chance - .5), axis=0,
    )
    return order


def assess(predictions, chance, cohort, actual, role, season, start, lane, training_rows):
    rows, errors = [], []
    order = priorities(predictions, chance, cohort)
    observed_opportunity = cohort.index.isin(actual.index)
    reference_chance = float(observed_opportunity.mean())
    for recipe in RECIPES:
        selected = candidate_order(order[recipe], cohort, role)
        assessed = actual.reindex(selected)
        common = actual.join(predictions[recipe].rename("prediction"), how="inner")
        error = common["target"] - common["prediction"]
        rows.append({
            "role": role, "season": season, "cutoff": start.date().isoformat(), "lane": lane, "recipe": recipe,
            "training_rows": training_rows, "assessed_candidates": len(common), "selected": len(selected),
            "assessed_picks": assessed["target"].count(), "mae": error.abs().mean(),
            "pressure_per_slot": assessed["actual_pressure"].sum() / 10,
            "pressure_assessed_mean": assessed["actual_pressure"].mean(),
            "target_per_slot": assessed["target"].sum() / 10,
            "target_assessed_mean": assessed["target"].mean(),
            "opportunity_brier": np.mean((chance - observed_opportunity) ** 2),
            "opportunity_observed_rate": reference_chance,
            "opportunity_predicted_rate": chance.mean(),
        })
        errors.append(common[["prediction", "target", "hp_balls"]].assign(
            recipe=recipe, role=role, season=season, cutoff=start.date().isoformat(), lane=lane, residual=error,
        ).reset_index())
    return rows, errors


def previous_labels(ledger, history, roles, role):
    records = []
    for _, start, end in rolling_windows(ledger):
        features = player_features(history, start)
        qualified = usable(features, role_support(roles, role, start))
        records.append(features[qualified].join(realized_ipl(history, start, end), how="inner").assign(end=end))
    return pd.concat(records)


def model_choice(table):
    """Promote a challenger only with validation gains in impact and comparable coverage."""
    val = table.loc[table["lane"].eq("forward") & table["season"].lt(2026)]
    summary = val.groupby("recipe").agg(
        impact=("target_per_slot", "mean"), pressure=("pressure_per_slot", "mean"),
        assessed=("assessed_picks", "sum"), mae=("mae", "mean"),
    )
    baseline = summary.loc["previous"]
    challengers = summary.loc[list(CHALLENGERS)]
    eligible = challengers.loc[
        challengers["impact"].gt(baseline["impact"] + .15)
        & challengers["pressure"].ge(baseline["pressure"] - .10)
        & challengers["assessed"].ge(max(16, baseline["assessed"] - 2))
        & challengers["mae"].le(baseline["mae"] + .10)
    ]
    order = eligible.sort_values(["impact", "pressure", "mae"], ascending=[False, False, True])
    return order.index[0] if len(order) else "previous"


def empirical_band(errors, alpha=.05):
    residual = np.sort(np.abs(np.asarray(errors)))
    index = int(np.ceil((len(residual) + 1) * (1 - alpha))) - 1
    return float(residual[index]) if index < len(residual) else np.nan


def auction_case(pool, registry):
    status = registry.set_index("player_id")["availability_status"].reindex(pool.index)
    conditional = pool.index.isin([*CORE_WATCH, *AUCTION_CORE_EVIDENCE]) | status.isin({
        "BENCHMARK_UNTOUCHABLE", "CONTRACTED_RIVAL_CORE", "CONTRACTED_RIVAL_BENCHMARK",
    })
    conditional |= status.str.contains("FITNESS_CLEARANCE|NOC_AND_POLICY|REGISTRATION_UNVERIFIED", na=False)
    return pool.loc[~conditional | status.eq("INCUMBENT_RR")]


def decision_scenarios(pool, scores, registry, role):
    """Keep cricket scores fixed while checking how selection assumptions change the list."""
    base = auction_case(pool, registry)
    # Dated fitness contingencies, not player ratings or confirmed IPL 2027 exclusions.
    scenarios = [("base_case", base, True), ("score_order_only", base, False)]
    if role == "bowling":
        scenarios.extend([
            ("without_lungi_ngidi", base.drop(index=4641, errors="ignore"), True),
            ("without_harshit_rana", base.drop(index=29888, errors="ignore"), True),
            ("fitness_contingency", base.drop(index=[4641, 29888], errors="ignore"), True),
        ])
    else:
        scenarios.append(("without_riyan_parag", base.drop(index=6423, errors="ignore"), True))
    statuses = registry.set_index("player_id")["availability_status"].reindex(pool.index)
    blocked = statuses.str.contains("FITNESS_CLEARANCE|NOC_AND_POLICY|REGISTRATION_UNVERIFIED", na=False)
    wider = pool.loc[~blocked | statuses.eq("INCUMBENT_RR")]
    scenarios.append(("wider_release_case", wider, True))
    rows = []
    for label, eligible, apply_fit in scenarios:
        selected = candidate_order(scores.reindex(eligible.index), eligible, role, apply_fit=apply_fit)
        rows.append(eligible.loc[selected, ["player_name", "deployment"]].assign(
            role=role, scenario=label, rank=range(1, len(selected) + 1), priority=scores.reindex(selected),
        ).reset_index())
    return pd.concat(rows, ignore_index=True)


def stability(history, matchup, pool, cutoff, role, chosen, previous_fit, fitted, count):
    groups = [
        frame["match_id"].unique() for _, frame in history.groupby([history["match_date"].dt.year, "comp_tier"])
    ]
    rng = np.random.default_rng(2027)
    winners = []
    for _ in range(count):
        weights = pd.Series(np.concatenate([rng.choice(ids, len(ids), replace=True) for ids in groups])).value_counts()
        if chosen == "previous":
            features = player_features(history, cutoff, fixture_weights=weights).reindex(pool.index)
            pred = predict(features, previous_fit)["ensemble"]
            order = penalize_sparse_evidence(pred, features)
        else:
            features = enrich(history, cutoff, weights).reindex(pool.index)
            features["adjusted_matchups"] = (
                adjust_for_opposition(matchup, cutoff, pool.index, weights) if chosen.startswith("adjusted_") else 0.
            )
            pred, chance = forecasts(features, previous_fit, fitted)
            order = priorities(pred, chance, features)[chosen]
        winners.append(pool.index.isin(candidate_order(order, pool, role)))
    return np.asarray(winners)


def rule_pressure(ledger):
    """Sensitivity check based on the scoreboard and phase at the start of the delivery."""
    remaining = ledger["pre_balls_remaining"]
    gap = ledger["pre_target_reconciled_gap"]
    wickets = ledger["pre_wickets_in_hand"]
    chasing = ledger["innings"].eq(2)
    required = 6 * gap / remaining.clip(lower=1)
    close_chase = chasing & remaining.between(1, 24) & gap.gt(0) & required.between(6, 15)
    low_resources = wickets.le(5) & remaining.ge(12) & (~chasing | required.ge(8))
    setting_death = ~chasing & ledger["match_phase"].eq("DEATH")
    return close_chase | low_resources | setting_death


def match_context(ledger, role, selected):
    player = "striker_id" if role == "batting" else "bowler_id"
    matchup = "pace_or_spin" if role == "batting" else "batting_type"
    cohort = ledger.loc[
        ledger[player].isin(selected) & ledger["comp_tier"].eq("IPL") & ledger["is_high_pressure_20"]
    ].assign(recent=lambda rows: rows["match_date"].dt.year.eq(2026))
    result = cohort.groupby([player, "match_phase", matchup, "recent"], observed=True).agg(
        pressure_balls=("is_legal_ball", "sum"), fixtures=("match_id", "nunique"), impact=(role + "_impact", "sum"),
    ).reset_index().rename(columns={player: "player_id", matchup: "opponent_type"})
    result["impact_per_12"] = 12 * result["impact"] / result["pressure_balls"].replace(0, np.nan)
    return result


def run(raw, base, output, count):
    output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((base / "input_manifest.json").read_text(encoding="utf-8"))
    for name, record in manifest["files"].items():
        if compute_sha256(raw / name) != record["sha256"]:
            raise ValueError(f"Ledger input does not match the official pack: {name}")
    ledger_path = base / "delivery_impact_ledger.csv"
    ledger = pd.read_csv(ledger_path, parse_dates=["match_date"], usecols=[
        "match_id", "match_date", "comp_tier", "match_phase", "venue_id", "striker_id", "bowler_id",
        "batting_order", "pace_or_spin", "is_legal_ball", "is_reliability_eligible", "batting_impact", "bowling_impact",
        "batting_type", "innings", "pre_balls_remaining", "pre_wickets_in_hand", "pre_target_reconciled_gap",
        "is_high_pressure_15", "is_high_pressure_20", "is_high_pressure_25",
    ], low_memory=False)
    ledger = ledger.loc[ledger["is_reliability_eligible"] & ledger["match_phase"].isin(PHASES)]
    mapping = pd.read_csv(raw / "competition_team_player_mapping.csv")
    dim = pd.read_csv(base / "player_dimension.csv")
    registry = build_ipl_availability_registry(raw_dir=raw, as_of_date=MARKET_AS_OF)
    official = match_market(Path(__file__).parent / "data" / "historical_ipl_auction.csv", mapping)
    production = pd.Timestamp(MARKET_AS_OF)
    reports, forecasts_audit, slates, stress, contexts, scenarios = [], [], [], [], [], []
    summaries = {}
    ledger = ledger.assign(is_high_pressure_rules=rule_pressure(ledger))
    eda = ledger.loc[ledger["is_legal_ball"]].assign(year=lambda frame: frame["match_date"].dt.year)
    eda = eda.groupby(["year", "comp_tier", "match_phase"]).agg(
        fixtures=("match_id", "nunique"), legal_balls=("is_legal_ball", "size"),
        pressure15=("is_high_pressure_15", "sum"), pressure20=("is_high_pressure_20", "sum"),
        pressure25=("is_high_pressure_25", "sum"), pressure_rules=("is_high_pressure_rules", "sum"),
    )
    eda.to_csv(output / "pressure_eda.csv")
    for role in ("batting", "bowling"):
        history = make_match_profiles(ledger, role, 20)
        matchup = matchup_history(ledger, role, 20)
        roles = role_history(ledger, role)
        old_labels = previous_labels(ledger, history, roles, role)
        dense = pd.concat([
            frame for season in range(2023, 2027) for frame in dense_labels(history, roles, role, season)
        ])
        report, errors = [], []
        forward = [(season, start, end, "forward") for season, start, end in rolling_windows(ledger) if season >= 2024]
        auction = [
            (season, pd.Timestamp(start), pd.Timestamp(season + 1, 1, 1), "auction")
            for season, start in AUCTIONS.items()
        ]
        for season, start, end, lane in [*forward, *auction]:
            training = dense.loc[dense["end"].le(start)]
            previous_fit = fit_models(old_labels.loc[old_labels["end"].le(start)])
            fitted = fit_challengers(training)
            features = enrich(history, start)
            pool = add_deployment(features.loc[usable(features, role_support(roles, role, start))], dim, roles, role, start)
            if lane == "auction":
                market = historical_market(official, season)
                pool = pool.loc[pool.index.isin(market.loc[~market["is_unavailable_hard"], "player_id"])]
            pool["adjusted_matchups"] = adjust_for_opposition(matchup, start, pool.index)
            predictions, chance = forecasts(pool, previous_fit, fitted)
            rows, details = assess(
                predictions, chance, pool, realized_ipl(history, start, end),
                role, season, start, lane, len(training),
            )
            report.extend(rows)
            errors.extend(details)
        report = pd.DataFrame(report)
        errors = pd.concat(errors, ignore_index=True)
        chosen = model_choice(report)
        residual = errors.loc[errors["lane"].eq("forward") & errors["recipe"].eq(chosen)]
        band = empirical_band(residual.loc[residual["season"].lt(2026), "residual"])
        held = residual.loc[residual["season"].eq(2026), "residual"]
        ranked_pool = candidate_pool(enrich(history, production), dim, roles, role, production, registry)
        ranked_pool["adjusted_matchups"] = adjust_for_opposition(matchup, production, ranked_pool.index)
        previous_fit = fit_models(old_labels)
        fitted = fit_challengers(dense)
        predictions, chance = forecasts(ranked_pool, previous_fit, fitted)
        priority = priorities(predictions, chance, ranked_pool)[chosen]
        scenarios.append(decision_scenarios(ranked_pool, priority, registry, role))
        production_pool = auction_case(ranked_pool, registry)
        projection = predictions[chosen].reindex(production_pool.index)
        scores = priority.reindex(production_pool.index)
        picks = candidate_order(scores, production_pool, role)
        draws = stability(history, matchup, production_pool, production, role, chosen, previous_fit, fitted, count)
        if len(picks) != 10:
            raise ValueError(f"Expected ten eligible {role} recommendations")
        final = production_pool.assign(
            predicted_impact=projection, priority=scores, top10_stability=draws.mean(axis=0),
            nominal95_low=projection - band, nominal95_high=projection + band,
            opportunity_forecast=chance,
        ).loc[picks]
        slates.append(final.assign(role=role, rank=range(1, 11), recipe=chosen).reset_index())
        contexts.append(match_context(ledger, role, picks).assign(role=role))
        for thresh in (15, 25, "rules"):
            alt = make_match_profiles(ledger, role, thresh)
            alt_old = previous_labels(ledger, alt, roles, role)
            alt_dense = pd.concat([
                frame for year in range(2023, 2027) for frame in dense_labels(alt, roles, role, year)
            ])
            alt_features = enrich(alt, production).reindex(production_pool.index)
            alt_features["adjusted_matchups"] = (
                adjust_for_opposition(matchup_history(ledger, role, thresh), production, alt_features.index)
                if chosen.startswith("adjusted_") else 0.
            )
            alt_pred, alt_chance = forecasts(alt_features, fit_models(alt_old), fit_challengers(alt_dense))
            variant = candidate_order(priorities(alt_pred, alt_chance, alt_features)[chosen], production_pool, role)
            stress.append({"role": role, "pressure_cutoff": thresh, "overlap": len(set(picks) & set(variant))})
        summaries[role] = {
            "chosen_recipe": chosen, "dense_training_rows": len(dense),
            "dense_rows_with_impact_label": int(dense["assessable"].sum()),
            "auction_pool_candidates": len(production_pool),
            "median_stability": float(final["top10_stability"].median()),
            "players_at_95_percent": int(final["top10_stability"].ge(.95).sum()),
            "exact_slate_frequency": float((draws == production_pool.index.isin(picks)).all(axis=1).mean()),
            "nominal_95_band_half_width": band, "observed_2026_band_coverage": float(held.abs().le(band).mean()),
            "observed_2026_band_sample": len(held),
        }
        reports.append(report)
        forecasts_audit.append(errors)
        print(role, summaries[role], flush=True)
    pd.concat(reports, ignore_index=True).to_csv(output / "comparison.csv", index=False)
    pd.concat(forecasts_audit, ignore_index=True).to_csv(output / "prediction_audit.csv", index=False)
    pd.concat(slates, ignore_index=True).to_csv(output / "auction_shortlist.csv", index=False)
    pd.DataFrame(stress).to_csv(output / "pressure_sensitivity.csv", index=False)
    pd.concat(contexts, ignore_index=True).to_csv(output / "phase_matchup_evidence.csv", index=False)
    pd.concat(scenarios, ignore_index=True).to_csv(output / "auction_scenarios.csv", index=False)
    (output / "validation.json").write_text(json.dumps({
        "summary": summaries, "fixture_bootstrap_replicates": count, "input_manifest": manifest["files"],
        "ledger_sha256": compute_sha256(ledger_path),
        "interval_scope": "Empirical 2024–25 forward residual band with 95% nominal level, measured on the 2026 replay. Player and time dependence limit coverage guarantees.",
        "bootstrap_scope": "Whole-fixture resampling within year and tier. Refits feature aggregates conditional on the final fitted coefficients, fixed role constraints and the auction scenario.",
        "selection_scope": "Selected on 2024–25 forward windows; 2026 is a retrospective audit. Historical auction windows are a decision stress test. Partial-season windows overlap in training only.",
    }, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("raw-dir", "baseline-dir", "out-dir"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--bootstrap", type=int, default=500)
    args = parser.parse_args()
    if args.bootstrap < 2:
        parser.error("At least two fixture resamples are required")
    with threadpool_limits(limits=1):
        run(args.raw_dir, args.baseline_dir, args.out_dir, args.bootstrap)


if __name__ == "__main__":
    main()
