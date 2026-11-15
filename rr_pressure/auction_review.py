"""Replay actual IPL auction markets and produce an auditable RR shortlist."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import unicodedata

import numpy as np
import pandas as pd
from scipy.stats import norm
from threadpoolctl import threadpool_limits

from rr_pressure.availability import build_ipl_availability_registry
from rr_pressure.challengers import (
    ChallengerC_IPLAnchoredRolePhase, ChallengerD_WorkloadDistributional, score_with_selected_model,
)
from rr_pressure.delivery_challenger import build_batting_delivery_cells
from rr_pressure.forecast import fit_player_forecast
from rr_pressure.ingest import derive_player_roles
from rr_pressure.manifest import compute_sha256
from rr_pressure.role_challenger import build_phase_observations_from_ledger
from rr_pressure.shortlist_policy import build_asof_market_snapshot, select_shortlist_by_policy


AUCTIONS = {2025: "2024-11-24", 2026: "2025-12-16"}
MARKET_AS_OF = "2026-11-14"
SOURCES = {
    "2025_list": "https://www.iplt20.com/cms/files/jot2qw8s50z1/6E2lO7kLr5D84oVOWK5ObY/528abc7f4c308e5454e22988a2081107/IPL_2025_Auction_List_Nov_19.pdf",
    "2026_list": "https://www.iplt20.com/cms/files/jot2qw8s50z1/6I7aEzrceYYpeUVi2qZm3/ce1814c9d6d5b2a8e112f45202804884/TATA-IPL-2026-Auction-List-8.12.25.pdf",
    "2025_retained": "https://www.iplt20.com/news/article/tata-ipl-2025-player-retentions-list-announced",
    "2026_retained": "https://www.iplt20.com/news/article/tata-ipl-2026-player-retentions-announced",
}
ALIASES = {
    "MS Dhoni": "Mahendra Singh Dhoni",
    "Abhishek Porel": "Abishek Porel",
    "Shahrukh Khan": "M Shahrukh Khan",
    "Varun Chakaravarthy": "Varun Chakravarthy",
    "Tilak Varma": "Namboori Tilak Varma",
    "Tilak Verma": "Namboori Tilak Varma",
    "Pat Cummins": "Patrick Cummins",
    "Nitish Kumar Reddy": "Nitish Reddy",
    "Syed Khaleel Ahmed": "Khaleel Ahmed",
    "KL Rahul": "Lokesh Rahul",
    "Gurnoor Singh Brar": "Gurnoor Brar",
    "Mohammad Siraj": "Mohammed Siraj",
    "Mohd. Arshad Khan": "Arshad Khan",
    "Nishant Sindhu": "Nishant Kumar Sindhu",
    "R. Sai Kishore": "Sai Kishore",
    "Md Shami": "Mohammed Shami",
    "Mohammad Shami": "Mohammed Shami",
    "Raj Angad Bawa": "Raj Bawa",
    "Will Jacks": "William Jacks",
    "Mitch Owen": "Mitchell Owen",
    "Vyshak Vijaykumar": "Vyshak Kumar",
    "Lhuan-Dre Pretorious": "Lhuan Pretorius",
    "Vaibhav Suryavanshi": "Vaibhav Sooryavanshi",
    "Yashaswi Jaiswal": "Yashasvi Jaiswal",
    "Rasikh Dar": "Rasikh Salam",
    "Smaran Ravichandaran": "Ravichandran Smaran",
    "Lungisani Ngidi": "Lungi Ngidi",
    "Atharva Taide": "Atharwa Taide",
    "Ravichandaran Ashwin": "Ravichandran Ashwin",
    "Steve Smith": "Steven Smith",
    "Tom Curran": "Thomas Curran",
    "Josh Little": "Joshua Little",
    "Daniel Mousley": "Dan Mousley",
    "Zak Foulkes": "Zakary Foulkes",
    "Ben Howell": "Benny Howell",
    "Benjamin McDermott": "Ben McDermott",
    "Siddharth Kaul": "Siddarth Kaul",
    "Shahbaz Ahamad": "Shahbaz Ahmed",
    "Yash Raj Punja": "Yash Punja",
    "Mujeeb Rahman": "Mujeeb Ur Rahman",
    "Joshua Tongue": "Josh Tongue",
    "Wesley Agar": "Wes Agar",
    "Md Shoriful Islam": "Shoriful Islam",
    "Yudhvir Charak": "Yudhvir Singh",
}
CLUB_IDENTITY = {("Rashid Khan", "GT"): 4722, ("Abdul Samad", "LSG"): 7446}
# Scenarios only. Official IPL 2027 retentions supersede these recruitment assumptions.
CORE_WATCH = {
    6256: ("KKR retained its established Indian strike spinner in both replays.",
           "https://www.iplt20.com/teams/kochi-tuskers-kerala/squad-details/5432"),
    830: ("RCB retained its senior quick for 2026. He took key wickets in their title win.",
          "https://www.iplt20.com/news/article/tata-ipl-2026-final-rcb-v-gt-match-report"),
    360: ("RCB retained him for 2026. He took 28 wickets in their title-winning season.",
          "https://www.iplt20.com/news/article/tata-ipl-2026-final-rcb-v-gt-match-report"),
    3644: ("LSG specifically acquired the frontline India spinner at his existing Rs 13.50 crore fee.",
           "https://www.iplt20.com/news/article/rishabh-pant-and-kuldeep-yadav-complete-high-profile-trade-between-dc-and-lsg"),
    818: ("LSG retained its 2026 first-choice opener. Treat him as a release-only contingency.",
          SOURCES["2026_retained"]),
    813: ("GT's first-choice international wicketkeeper. The 2026 squad retained him.",
          SOURCES["2026_retained"]),
    5553: ("RCB's retained top-order wicketkeeper. Monitor official release before bidding.",
           SOURCES["2026_retained"]),
    6464: ("MI acquired him in a marquee November 2026 deal for a frontline pace role.",
           "https://www.iplt20.com/news/article/hardik-pandya-and-arshdeep-singh-complete-major-trade-between-pbks-and-mi"),
}
MODELS = {
    "batting": ("B0", "IPL-B0", "D6", "D-all", "IPL-EB", "IPL-EB-mix", "DHP", "DHP-blend", "D6-blend"),
    "bowling": ("B0", "IPL-B0", "D6", "D-all", "IPL-EB", "IPL-EB-mix", "C-IPL", "RPP", "IPL-EB-blend"),
}
COLUMNS = {
    "batting": ("hp_balls_faced", "hp_bat_impact", "ord_balls_faced", "ord_bat_impact"),
    "bowling": ("hp_balls_bowled", "hp_bowl_impact", "ord_balls_bowled", "ord_bowl_impact"),
}
FORECAST = ["conservative_score_q25", "predicted_hp_impact", "ci_lower_80", "ci_upper_80"]
TIER_WEIGHT = {"IPL": 1.0, "T20I": 0.20, "INTERNATIONAL": 0.20, "EMERGING": 0.05}
MIN_ASSESSED = 12


def name_key(value):
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", value).lower())


def match_market(path, mapping):
    identities = defaultdict(set)
    for name, pid in mapping[["player_name", "player_id"]].dropna().drop_duplicates().itertuples(index=False):
        identities[name_key(name)].add(pid)
    aliases = {name_key(k): name_key(v) for k, v in ALIASES.items()}
    official = pd.read_csv(path, keep_default_na=False)
    official["player_id"] = pd.array(
        [next(iter(ids)) if len(ids) == 1 else None for ids in (
            identities[aliases.get(name_key(name), name_key(name))] for name in official["player"]
        )], dtype="Int64"
    )
    for (name, club), pid in CLUB_IDENTITY.items():
        hit = official["player"].eq(name) & official["club"].eq(club)
        if pid not in identities[name_key(name)]:
            raise ValueError(f"Invalid market identity for {name}, {club}")
        official.loc[hit, "player_id"] = pid
    if official.loc[official["status"].eq("retained"), "player_id"].isna().any():
        raise ValueError("Unresolved official retention identity")
    return official


def historical_market(official, season):
    rows = official[official["season"].eq(season) & official["player_id"].notna()].copy()
    retained = rows["status"].eq("retained")
    if rows.loc[retained, "player_id"].duplicated().any():
        raise ValueError(f"Duplicate retention identities for {season}")
    rows = rows.loc[retained | ~rows["player_id"].isin(rows.loc[retained, "player_id"])].drop_duplicates("player_id")
    retained = rows["status"].eq("retained")
    rr = retained & rows["club"].eq("RR")
    return rows.assign(
        current_franchise=rows["club"],
        is_rr_incumbent=rr,
        is_unavailable_hard=retained & ~rr,
        availability_status=np.where(rr, "INCUMBENT_RR", np.where(retained, "RIVAL_RETAINED", "OFFICIAL_AUCTION_LIST")),
        decision_category=np.where(rr, "INCUMBENT_RETENTION", np.where(retained, "BENCHMARK_ONLY", "AUCTION")),
    )


def add_verified_roster_routes(market, mapping):
    """A 2026 squad link supports a conditional route when no dated override exists."""
    market = market.copy()
    roster = mapping.loc[mapping["comp_id"].eq(3298), ["player_id", "team_name"]].drop_duplicates()
    unique = roster.loc[~roster["player_id"].duplicated(keep=False)].set_index("player_id")["team_name"]
    club = market["player_id"].map(unique)
    eligible = market["availability_status"].eq("UNVERIFIED_MISSING_MARKET_RECORD") & club.notna()
    market.loc[eligible, "current_franchise"] = club[eligible]
    market.loc[eligible, "availability_status"] = "PENDING_NOV17_RETENTIONS"
    market.loc[eligible, "decision_category"] = "CONDITIONAL_RELEASE_WATCH"
    market.loc[eligible, "route_tier"] = "CONDITIONAL"
    market.loc[eligible, "is_unavailable_hard"] = False
    market.loc[eligible, "market_exclusion_reason"] = ""
    return market


def impact_stats(history, role):
    balls, impact, ordinary, ordinary_impact = COLUMNS[role]
    ipl = history[history["comp_tier"].eq("IPL")]
    evidence = ipl.groupby("player_id").agg(
        ipl_hp_balls=(balls, "sum"), ipl_hp_impact=(impact, "sum"),
        ipl_ordinary_balls=(ordinary, "sum"), ipl_ordinary_impact=(ordinary_impact, "sum"),
    )
    active = ipl.loc[ipl[balls].gt(0)]
    evidence["ipl_hp_matches"] = active.groupby("player_id")["match_id"].nunique()
    evidence["last_ipl_pressure"] = active.groupby("player_id")["match_date"].max()
    latest_year = str(ipl["match_date"].max())[:4]
    recent = ipl[ipl["match_date"].str[:4].eq(latest_year)]
    evidence["latest_ipl_hp_balls"] = recent.groupby("player_id")[balls].sum()
    evidence["latest_ipl_hp_matches"] = recent.loc[recent[balls].gt(0)].groupby("player_id")["match_id"].nunique()
    evidence["latest_ipl_hp_rate"] = recent.groupby("player_id")[impact].sum().mul(12).div(
        evidence["latest_ipl_hp_balls"].replace(0, np.nan),
    )
    evidence["ipl_hp_rate"] = evidence["ipl_hp_impact"].mul(12).div(evidence["ipl_hp_balls"].replace(0, np.nan))
    evidence["ipl_ordinary_rate"] = evidence["ipl_ordinary_impact"].mul(12).div(evidence["ipl_ordinary_balls"].replace(0, np.nan))
    evidence["ipl_hp_matches"] = evidence["ipl_hp_matches"].fillna(0).astype(int)
    return evidence


def baseline(history, dimension, role):
    return fit_player_forecast(history, dimension, role, folds=history["fold"].unique(), baseline_only=True)[0]


def ipl_empirical_bayes(history, profiles, role, cutoff, match_weights=None, mix=False):
    """Shrink recent, transferable pressure impact toward an IPL ordinary-play prior."""
    hp_balls, hp_impact, ord_balls, ord_impact = COLUMNS[role]
    metrics = [hp_balls, hp_impact, ord_balls, ord_impact]
    tier = history["comp_tier"].map(TIER_WEIGHT).fillna(0.05)
    dates = pd.to_datetime(history["match_date"])
    weights = np.exp2(-(pd.Timestamp(cutoff) - dates).dt.days / 730.0)
    if match_weights is not None:
        weights *= history["match_id"].map(match_weights).fillna(0)
    ordinary_ipl = weights * history["comp_tier"].eq("IPL")
    exposure = history[metrics].mul(weights * tier, axis=0)
    exposure[[ord_balls, ord_impact]] = history[[ord_balls, ord_impact]].mul(ordinary_ipl, axis=0)
    pooled = exposure.groupby(history["player_id"]).sum().reindex(profiles["player_id"]).fillna(0)
    roles = profiles.set_index("player_id")["inferred_role"]
    ordinary_rates = 12 * pooled[ord_impact] / pooled[ord_balls].replace(0, np.nan)
    role_average = ordinary_rates.where(pooled[ord_balls].ge(24)).groupby(roles).median()
    prior = roles.map(role_average).fillna(ordinary_rates.median()).fillna(0)
    usual = (12 * pooled[ord_impact] + 48 * prior) / (pooled[ord_balls] + 48)
    mean = (12 * pooled[hp_impact] + 36 * usual) / (pooled[hp_balls] + 36)
    # Estimate residual dispersion on IPL stints with enough exposure to measure it.
    well_observed = history["comp_tier"].eq("IPL") & history[hp_balls].ge(6)
    residual = 12 * history.loc[well_observed, hp_impact] / history.loc[well_observed, hp_balls]
    residual -= history.loc[well_observed, "player_id"].map(mean)
    mad = (residual - residual.median()).abs().median()
    sigma = max(3.0, float(mad) * 1.4826)
    predictive_sigma = sigma * np.sqrt(1 + 12 / (pooled[hp_balls] + 36))
    q25 = mean + norm.ppf(.25) * predictive_sigma
    if mix:
        # Weight pressure twice as heavily as baseline skill when ordering auction picks.
        priority = (2 * q25 + usual) / 3
    else:
        priority = q25
    lower = mean + norm.ppf(.10) * predictive_sigma
    upper = mean + norm.ppf(.90) * predictive_sigma
    return [series.to_numpy() for series in (q25, mean, lower, upper, priority)]


def score(model, profile, history, dimension, role, cutoff, phase, pressure, cells, weights=None):
    """Score a frozen candidate frame. Fixture weights affect fitting only."""
    def resample(frame):
        if weights is None:
            return frame
        return frame.loc[frame.index.repeat(frame["match_id"].map(weights).fillna(0).astype(int))]

    pids = profile["player_id"].to_numpy()
    workload = np.full(len(pids), 12.0)
    if model in {"DHP-blend", "IPL-EB-blend", "D6-blend"}:
        pressure_model = model.removesuffix("-blend")
        control = "B0" if role == "batting" else "IPL-B0"
        fields = [*FORECAST, "selection_priority"]
        pressure_fit = score(pressure_model, profile, history, dimension, role, cutoff, phase, pressure, cells, weights)
        control_fit = score(control, profile, history, dimension, role, cutoff, phase, pressure, cells, weights)
        values = ((2 * pressure_fit[fields] + control_fit[fields]) / 3).to_numpy().T
    elif model in {"B0", "IPL-B0"}:
        data = history if model == "B0" else history[history["comp_tier"].eq("IPL")]
        fitted = baseline(resample(data), dimension, role).set_index("player_id").reindex(pids)
        values = [fitted[f"b0_{key}"].to_numpy() for key in ("q25", "mean", "ci_lower_80", "ci_upper_80")]
    elif model in {"D6", "D-all", "C-IPL"}:
        if model == "C-IPL":
            fit = ChallengerC_IPLAnchoredRolePhase().fit(pressure, dimension, role, match_weights=weights)
        else:
            fit = ChallengerD_WorkloadDistributional(include_short_stints=model == "D-all").fit(
                resample(history), dimension, role,
            )
        values = [fit.predict_quantile(pids, workload), fit.predict_mean(pids), *fit.predict_ci_80(pids, workload)]
    elif model in {"IPL-EB", "IPL-EB-mix"}:
        values = ipl_empirical_bayes(history, profile, role, cutoff, weights, mix=model.endswith("-mix"))
    else:
        dispatch = {"DHP": "Challenger DHP", "RPP": "Challenger RPP"}
        scored = score_with_selected_model(
            profile, resample(history).reset_index(drop=True), dimension, role, dispatch[model],
            obs_df=phase, bat_cells_df=resample(cells) if cells is not None else None,
        )
        values = [scored[col].to_numpy() for col in FORECAST]
    result = profile.assign(**dict(zip(FORECAST, values)), selection_priority=values[-1] if len(values) == 5 else values[0])
    valid = np.isfinite(result[FORECAST]).all(axis=1)
    result["is_qualified"] &= valid
    q25, _, q10, q90 = (result[key][valid] for key in FORECAST)
    if not (q10.le(q25) & q25.le(q90)).all():
        raise ValueError(f"Crossed forecast quantiles in {model}")
    return result


def select(scored, market, *, balance=False, min_balls=24, min_matches=2, recent=True, pressure_guard=True):
    scored = scored.copy()
    original_qualified = scored["is_qualified"].copy()
    if recent:
        scored["is_qualified"] &= scored["latest_ipl_hp_balls"].ge(12) & scored["latest_ipl_hp_matches"].ge(2)
    latest_exclusion = set(scored.loc[original_qualified & ~scored["is_qualified"], "player_id"])
    conflicting = scored["is_qualified"] & scored["ipl_hp_rate"].lt(0) & scored["latest_ipl_hp_rate"].lt(0)
    if pressure_guard:
        scored.loc[conflicting, "is_qualified"] = False
    scored["pressure_q25"] = scored["conservative_score_q25"]
    scored["conservative_score_q25"] = scored["selection_priority"]
    ranked = select_shortlist_by_policy(
        scored, market, allow_rr_incumbents=True, policy_name="RPP_IPL_VERIFIED",
        min_ipl_hp_balls=min_balls, min_ipl_hp_matches=min_matches, require_indian_majority=balance,
    ).sort_values("submission_rank")
    ranked["conservative_score_q25"] = ranked.pop("pressure_q25")
    ranked.loc[ranked["player_id"].isin(latest_exclusion), "passed_over_reason"] = "THIN_LATEST_IPL_PRESSURE_EXPOSURE"
    if pressure_guard:
        rejected = scored.loc[conflicting, "player_id"]
        ranked.loc[ranked["player_id"].isin(rejected), "passed_over_reason"] = "NEGATIVE_IPL_PRESSURE_OVERALL_AND_LATEST"
    return ranked


def assess(ranked, realized, holdout, role, model, season):
    top = ranked.head(10).copy()
    top = top.merge(realized[["ipl_hp_balls", "ipl_hp_rate", "ipl_ordinary_rate"]], left_on="player_id", right_index=True,
                    how="left", suffixes=("", "_realized"))
    ok = top["ipl_hp_balls_realized"].ge(MIN_ASSESSED)
    top["assessed"] = ok
    top["realized_rate"] = top["ipl_hp_rate_realized"].where(ok)
    rate = top["realized_rate"].dropna()
    ordinary = top["ipl_ordinary_rate_realized"].where(ok)
    mixed = (2 * top["realized_rate"] + ordinary) / 3
    balls, impact, *_ = COLUMNS[role]
    # Evaluate Q25 and interval on approximately 12-ball stints, across the screened pool.
    comparable = holdout[holdout[balls].between(9, 15)].merge(
        ranked[["player_id", *FORECAST]], on="player_id", how="inner",
    )
    truth = 12 * comparable[impact] / comparable[balls]
    error = truth - comparable["conservative_score_q25"]
    stats = {
        "season": season, "role": role, "model": model, "selected": len(top), "assessed": int(ok.sum()),
        "mean_realized_impact": float(rate.mean()),
        "slot_score_zero_if_unassessed": float(rate.sum() / 10),
        "mixed_slot_score_zero_if_unassessed": float(mixed.sum() / 10),
        "positive_picks": int(rate.gt(0).sum()),
        "q25_pinball": float(np.maximum(.25 * error, -.75 * error).mean()),
        "q25_hit_rate": float(error.lt(0).mean()),
        "interval_coverage": float(truth.between(comparable["ci_lower_80"], comparable["ci_upper_80"]).mean()),
        "comparable_stints": len(comparable),
    }
    return stats, top.assign(season=season, role=role, model=model)


def production_slots(official, mapping):
    listed = official[official["player_id"].notna() & official["country"].ne("")]
    overseas = listed.groupby("player_id")["country"].apply(lambda s: set(s.str.upper().ne("INDIA")))
    slots = {pid: ("OS" if next(iter(values)) else "IND") for pid, values in overseas.items() if len(values) == 1}
    international = mapping[mapping["comp_name"].str.contains(r"T20I|World Cup", na=False, regex=True)]
    for pid, teams in international.groupby("player_id")["team_name"]:
        flags = teams.str.startswith("India").unique()
        if len(flags) == 1:
            slots.setdefault(pid, "IND" if flags[0] else "OS")
    return slots


def bootstrap_selection(model, profile, history, dimension, role, cutoff, phase, pressure, cells,
                        balance, original, count):
    fixture_groups = [
        g["match_id"].unique() for _, g in history.groupby(
            [history["match_date"].str[:4], "comp_tier"], sort=True,
        )
    ]
    rng = np.random.default_rng(2027)
    counts = defaultdict(int)
    for _ in range(count):
        weights = pd.Series(np.concatenate([rng.choice(g, len(g), replace=True) for g in fixture_groups])).value_counts().to_dict()
        predictions = score(model, profile, history, dimension, role, cutoff, phase, pressure, cells, weights)
        fixed_pool = original[["player_id", "slot_nationality"]].merge(
            predictions.loc[predictions["is_qualified"], ["player_id", "predicted_hp_impact", "selection_priority"]],
            on="player_id", validate="one_to_one",
        ).merge(profile[["player_id", "ipl_hp_balls"]], on="player_id", validate="one_to_one")
        fixed_pool = fixed_pool.sort_values(
            ["selection_priority", "predicted_hp_impact", "ipl_hp_balls", "player_id"],
            ascending=[False, False, False, True],
        )
        if balance:
            overseas = fixed_pool["slot_nationality"].eq("OS")
            fixed_pool = fixed_pool.loc[~overseas | overseas.cumsum().le(4)]
        for pid in fixed_pool.head(10)["player_id"]:
            counts[pid] += 1
    return {pid: counts[pid] / count for pid in original["player_id"]}


def run(raw, baseline_dir, out, bootstrap):
    official_path = Path(__file__).parent / "data" / "historical_ipl_auction.csv"
    manifest = json.loads((baseline_dir / "input_manifest.json").read_text(encoding="utf-8"))
    hashes = {name: compute_sha256(raw / name) for name in manifest["files"]}
    if any(digest != manifest["files"][name]["sha256"] for name, digest in hashes.items()):
        raise ValueError("Raw inputs differ from the validated delivery ledger's manifest")
    mapping = pd.read_csv(raw / "competition_team_player_mapping.csv")
    official = match_market(official_path, mapping)
    current_market = build_asof_market_snapshot(2027, mapping, pd.read_csv(baseline_dir / "player_dimension.csv"), raw_dir=raw)
    current_market = add_verified_roster_routes(current_market, mapping)
    registry = build_ipl_availability_registry(output_dir=None, raw_dir=raw)
    assumed_core = current_market["player_id"].isin(CORE_WATCH) & ~current_market["is_rr_incumbent"]
    market_review = current_market.copy()
    current_market.loc[assumed_core, "is_unavailable_hard"] = True
    current_market.loc[assumed_core, "market_exclusion_reason"] = "RIVAL_CORE_EXPECTED_TO_STAY"
    current_market["market_assumption"] = current_market["player_id"].map({k: v[0] for k, v in CORE_WATCH.items()})
    current_market["market_assumption_source"] = current_market["player_id"].map({k: v[1] for k, v in CORE_WATCH.items()})
    current_market.to_csv(out / "market_screen.csv", index=False)
    slots = production_slots(official, mapping)
    official.to_csv(out / "auction_identity_audit.csv", index=False)

    fixture = pd.read_csv(raw / "matches.csv", usecols=["match_id", "match_date"])
    ball = pd.read_csv(raw / "ball_by_ball.csv").merge(fixture, on="match_id", validate="many_to_one")
    p11 = pd.read_csv(raw / "playing_eleven.csv")
    dimension = {
        date: derive_player_roles(ball, p11, mapping["player_id"], mapping, set(fixture.loc[fixture["match_date"].lt(date), "match_id"]))
        for date in [*AUCTIONS.values(), MARKET_AS_OF]
    }
    del ball, p11
    ledger = pd.read_csv(baseline_dir / "delivery_impact_ledger.csv", usecols=[
        "match_id", "comp_tier", "season", "match_date", "match_phase", "innings", "fold", "striker_id", "bowler_id",
        "is_legal_ball", "is_high_pressure_20", "is_reliability_eligible", "runs", "bowler_charge_runs",
        "is_striker_dismissed", "is_bowler_wicket", "expected_bat_runs", "expected_striker_dismissal",
        "marginal_wicket_value_ws", "batting_impact", "bowling_impact", "hp_bat_impact", "hp_bowl_impact",
    ], low_memory=False)
    ledger = ledger[ledger["is_reliability_eligible"]]
    all_pressure = ledger[ledger["is_high_pressure_20"]]
    bat_cells = build_batting_delivery_cells(ledger)
    bowl_phase = build_phase_observations_from_ledger(ledger, "bowling")
    reports, picks, candidates, sensitivity = [], [], [], []
    chosen = {}

    for role, model_names in MODELS.items():
        match = pd.read_csv(baseline_dir / f"match_player_{role}_impact.csv")
        for season, cutoff in [*AUCTIONS.items(), (2027, MARKET_AS_OF)]:
            history = match[match["match_date"].lt(cutoff)]
            dim = dimension[cutoff]
            profile = baseline(history, dim, role)
            evidence = impact_stats(history, role)
            profile = profile.drop(columns="ipl_hp_balls").join(evidence, on="player_id")
            profile[["ipl_hp_balls", "ipl_hp_matches"]] = profile[["ipl_hp_balls", "ipl_hp_matches"]].fillna(0)
            profile["slot_nationality"] = profile["player_id"].map(slots).fillna("UNKNOWN")
            phase = bowl_phase[bowl_phase["match_date"].lt(cutoff)] if role == "bowling" else None
            cells = bat_cells[bat_cells["match_date"].lt(cutoff)] if role == "batting" else None
            pressure = all_pressure[all_pressure["match_date"].lt(cutoff)]

            if season in AUCTIONS:
                market = historical_market(official, season)
                profile["slot_nationality"] = profile["slot_nationality"].replace("UNKNOWN", "OS")
                holdout = match[match["match_date"].str.startswith(str(season)) & match["comp_tier"].eq("IPL")]
                realized = impact_stats(holdout, role)
                for model in model_names:
                    scored = score(model, profile, history, dim, role, cutoff, phase, pressure, cells)
                    ranked = select(scored, market, balance=True).dropna(subset=["submission_rank"])
                    report, top = assess(ranked, realized, holdout, role, model, season)
                    reports.append(report)
                    picks.append(top)
                    print(season, role, model, report["assessed"], round(report["slot_score_zero_if_unassessed"], 3), flush=True)
                continue

            summary = pd.DataFrame(reports)
            summary = summary[summary["role"].eq(role)].groupby("model").agg(
                seasons=("season", "nunique"), min_assessed=("assessed", "min"),
                pressure_slot=("slot_score_zero_if_unassessed", "mean"),
                slot_score=("mixed_slot_score_zero_if_unassessed", "mean"), pinball=("q25_pinball", "mean"),
            )
            qualified = summary.loc[
                summary["seasons"].eq(len(AUCTIONS)) & summary["min_assessed"].ge(5)
                & ~summary.index.isin(["B0", "IPL-B0"])
            ]
            if qualified.empty:
                raise ValueError(f"Insufficient replay coverage for {role}")
            model = qualified.sort_values(["slot_score", "pinball"], ascending=[False, True]).index[0]
            chosen[role] = model
            scored = score(model, profile, history, dim, role, cutoff, phase, pressure, cells)
            # Unknown slot status cannot be counted as Indian squad depth.
            scored["slot_nationality"] = scored["slot_nationality"].replace("UNKNOWN", "OS")
            ranked = select(scored, current_market, balance=True)
            ranked["role"] = role
            ranked["model"] = model
            ranked = ranked.merge(
                registry[["player_id", "fitness_clearance_status", "auction_registration_status", "source_url"]],
                on="player_id", how="left", validate="one_to_one",
            )
            ranked_pool = ranked.dropna(subset=["submission_rank"])
            if bootstrap:
                freq = bootstrap_selection(model, profile, history, dim, role, cutoff, phase, pressure, cells,
                                           True, ranked_pool, bootstrap)
                ranked["bootstrap_top10_frequency"] = ranked["player_id"].map(freq)
            for tag, test in (
                ("no_indian_majority", select(scored, current_market)),
                ("stricter_36_balls_3_matches", select(scored, current_market, balance=True, min_balls=36, min_matches=3)),
                ("without_latest_ipl_floor", select(scored, current_market, balance=True, recent=False)),
                ("without_negative_pressure_guard", select(scored, current_market, balance=True, pressure_guard=False)),
                ("additional_rival_core_released", select(scored, market_review, balance=True)),
            ):
                sensitivity.append(test.dropna(subset=["submission_rank"]).head(10).assign(role=role, scenario=tag))
            candidates.append(ranked)
            print("2027", role, "chosen", model, flush=True)

    frame = pd.concat(candidates, ignore_index=True)
    top = frame.loc[frame["submission_rank"].le(10)].sort_values(["role", "submission_rank"]).copy()
    if top.groupby("role")["player_id"].nunique().to_dict() != {"batting": 10, "bowling": 10}:
        raise ValueError("Expected exactly ten distinct players per discipline")
    if top["is_unavailable_hard"].any() or not top["role_supported"].all():
        raise ValueError("Shortlist failed market or discipline checks")
    for role, player, impact in (("batting", "striker_id", "hp_bat_impact"), ("bowling", "bowler_id", "hp_bowl_impact")):
        selected = top.loc[top["role"].eq(role), "player_id"]
        phase = all_pressure[all_pressure["comp_tier"].eq("IPL") & all_pressure[player].isin(selected)]
        phase = phase.groupby([player, "match_phase"]).agg(
            balls=("is_legal_ball", "sum"), impact=(impact, "sum"),
        ).reset_index().rename(columns={player: "player_id"})
        phase["runs_per_12"] = phase["impact"].mul(12).div(phase["balls"].replace(0, np.nan))
        phase.merge(top.loc[top["role"].eq(role), ["player_id", "player_name"]], on="player_id", validate="many_to_one").to_csv(
            out / f"{role}_ipl_phase_evidence.csv", index=False,
        )
    top["unstop_dropdown_status"] = "LIVE_SEARCH_PENDING"
    top["rr_route"] = np.where(top["is_rr_incumbent"], "Back within RR", "Confirm release and auction listing")
    frame.to_csv(out / "candidates.csv", index=False)
    top.to_csv(out / "shortlist.csv", index=False)
    pd.concat(picks, ignore_index=True).to_csv(out / "historical_shortlists.csv", index=False)
    pd.concat(sensitivity, ignore_index=True).to_csv(out / "policy_sensitivity.csv", index=False)
    pd.DataFrame(reports).to_csv(out / "model_replay.csv", index=False)
    (out / "review_manifest.json").write_text(json.dumps({
        "selected_models": chosen, "official_sources": SOURCES, "auction_cutoffs_exclusive": AUCTIONS,
        "market_snapshot_as_of": MARKET_AS_OF, "last_performance_date": str(ledger["match_date"].max()),
        "raw_sha256": hashes, "official_snapshot_sha256": compute_sha256(official_path),
        "bootstrap_replicates": bootstrap, "bootstrap_seed": 2027,
        "selection_rule": "Among pressure-aware models, highest average replay impact per slot (two thirds pressure, one third ordinary). Unassessed slots contribute zero only to model selection. Minimum five assessed each season. Q25 pinball breaks ties. Ordinary-only controls are reported.",
        "production_policy": "IPL floor 24 pressure balls and two matches, latest IPL season floor 12 pressure balls and two matches. Screen players with negative direct IPL pressure impact both overall and in the latest season. Supported role, dated market screen and Indian majority.",
        "evaluation_limit": "The peer-impact reference in the existing ledger uses cross-fit or season-start baselines. Forecast inputs and role evidence are strictly pre-auction.",
        "interval_limit": "Raw nominal forecast bands. See historical coverage. Bootstrap frequencies measure shortlist stability given fixed eligibility and model, not future success or availability.",
    }, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("raw-dir", "baseline-dir", "out-dir"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--bootstrap", type=int, default=100)
    args = parser.parse_args()
    if args.bootstrap < 0:
        parser.error("--bootstrap must be nonnegative")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    with threadpool_limits(limits=1):
        run(args.raw_dir, args.baseline_dir, args.out_dir, args.bootstrap)


if __name__ == "__main__":
    main()
