"""Test bowling challengers on recorded_extras data across all windows."""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from rr_pressure import auction_challenger as model
from rr_pressure import auction_retrain_audit as audit


def compute_recency_weighted_ipl(history, cutoff, pool_index):
    """365-day half-life recency-weighted IPL rates."""
    ipl = history.loc[history["comp_tier"].eq("IPL") & history["match_date"].lt(cutoff)].copy()
    if ipl.empty:
        return pd.Series(0.0, index=pool_index)
    days = (cutoff - ipl["match_date"]).dt.total_seconds() / (24 * 3600)
    weights = np.exp2(-days / 365.0)

    ipl["w_hp_balls"] = ipl["hp_balls"] * weights
    ipl["w_hp_impact"] = ipl["hp_impact"] * weights
    ipl["w_ord_balls"] = ipl["ordinary_balls"] * weights
    ipl["w_ord_impact"] = ipl["ordinary_impact"] * weights

    agg = ipl.groupby("player_id")[["w_hp_balls", "w_hp_impact", "w_ord_balls", "w_ord_impact"]].sum()

    tot_hp_balls = agg["w_hp_balls"].sum()
    tot_hp_impact = agg["w_hp_impact"].sum()
    tot_ord_balls = agg["w_ord_balls"].sum()
    tot_ord_impact = agg["w_ord_impact"].sum()
    peer_hp_rate = 12.0 * tot_hp_impact / tot_hp_balls if tot_hp_balls > 0 else 0.0
    peer_ord_rate = 12.0 * tot_ord_impact / tot_ord_balls if tot_ord_balls > 0 else 0.0
    peer_target = 0.75 * peer_hp_rate + 0.25 * peer_ord_rate

    hp_rate = (12.0 * agg["w_hp_impact"] / agg["w_hp_balls"]).where(agg["w_hp_balls"].gt(0), peer_hp_rate)
    ord_rate = (12.0 * agg["w_ord_impact"] / agg["w_ord_balls"]).where(agg["w_ord_balls"].gt(0), peer_ord_rate)
    target = 0.75 * hp_rate + 0.25 * ord_rate

    return target.reindex(pool_index).fillna(peer_target)


def fit_shrunk_pressure_uplift(training, features, history, cutoff, pool_index, k=48.0):
    """Fit regularized ordinary forecast and shrink observed uplift toward training peer prior."""
    x = training[model.FEATURE_SET]
    predict_x = features[model.FEATURE_SET]
    ord_support = training["ordinary_balls"]

    # 1. Regularized ordinary forecast
    ord_fit = make_pipeline(model.HistoricalBounds(), StandardScaler(), Ridge(alpha=60))
    ord_fit.fit(x, training["actual_ordinary"], ridge__sample_weight=np.sqrt(ord_support.clip(upper=72)))
    pred_ord = ord_fit.predict(predict_x)

    # 2. Prior uplift from training set
    u_train = training["actual_pressure"] - training["actual_ordinary"]
    h_train = 2.0 * training["ordinary_balls"] * training["hp_balls"] / (training["ordinary_balls"] + training["hp_balls"]).clip(lower=1e-6)
    valid = training["ordinary_balls"].gt(0) & training["hp_balls"].gt(0)
    prior_uplift = (u_train[valid] * h_train[valid]).sum() / h_train[valid].sum() if valid.any() else 0.0

    # 3. Prospect observed uplift from pre-cutoff history
    before = history.loc[history["match_date"].lt(cutoff)]
    agg = before.groupby("player_id")[["hp_balls", "hp_impact", "ordinary_balls", "ordinary_impact"]].sum().reindex(pool_index).fillna(0)
    hp_rate = np.where(agg["hp_balls"] > 0, 12.0 * agg["hp_impact"] / agg["hp_balls"], 0.0)
    ord_rate = np.where(agg["ordinary_balls"] > 0, 12.0 * agg["ordinary_impact"] / agg["ordinary_balls"], 0.0)
    raw_uplift = hp_rate - ord_rate

    n_eff = 2.0 * agg["hp_balls"] * agg["ordinary_balls"] / (agg["hp_balls"] + agg["ordinary_balls"]).clip(lower=1e-6)
    has_both = (agg["hp_balls"] > 0) & (agg["ordinary_balls"] > 0)
    shrunk_u = np.where(has_both, (n_eff * raw_uplift + k * prior_uplift) / (n_eff + k), prior_uplift)

    # 4. Composite impact
    return pd.Series(pred_ord + 0.75 * shrunk_u, index=pool_index)


def run_experiment():
    raw = Path("6af458274c1e8_data_pack")
    rebuild = Path("scratch/rr_rebuild_recorded_20261115")
    ledger, prov = audit.ledger_from_rebuild(raw, rebuild)
    dim = pd.read_csv(rebuild / "player_dimension.csv")
    mapping = pd.read_csv(raw / "competition_team_player_mapping.csv")
    market = model.match_market(Path("rr_pressure/data/historical_ipl_auction.csv"), mapping)

    data = audit.context(ledger, "bowling")
    history, roles, local, ends, old, local_old, dense, matchups = data

    windows = [(y, s, e, "forward") for y, s, e in model.rolling_windows(ledger) if y >= 2024]
    windows += [(y, pd.Timestamp(s), pd.Timestamp(y+1, 1, 1), "auction") for y, s in model.AUCTIONS.items()]

    results = []
    recipes = ["incumbent", "recency_weighted_ipl", "shrunk_pressure_uplift", "split_targets", "pressure_only"]

    for year, start, end, lane in windows:
        base_features = model.player_features(history, start)
        sufficient = model.usable(base_features, model.role_support(roles, "bowling", start))
        pool = model.add_deployment(base_features.loc[sufficient], dim, roles, "bowling", start)
        if lane == "auction":
            mkt = model.historical_market(market, year)
            pool = pool.loc[pool.index.isin(mkt.loc[~mkt["is_unavailable_hard"], "player_id"])]

        train = dense.loc[dense["assessable"] & dense["end"].le(start)]
        features = model.enrich(history, start).reindex(pool.index)

        # 1. Incumbent
        orig_fit = model.fit_models(audit.completed_ipl_labels(old, start, ends))
        inc_base = model.predict(features, orig_fit)["ensemble"]
        adj = model.adjust_for_opposition(matchups, start, pool.index)
        incumbent = 0.60 * inc_base + 0.40 * (0.80 * adj + 0.20 * features["transfer_skill"])

        # 2. Recency weighted IPL
        recency = compute_recency_weighted_ipl(history, start, pool.index)

        # 3. Shrunk pressure uplift
        shrunk = fit_shrunk_pressure_uplift(train, features, history, start, pool.index)

        # 4. Split targets
        split = audit.fit_split_targets(train, features)

        # 5. Pressure only
        pressure = features["pressure"]

        estimates = pd.DataFrame({
            "incumbent": incumbent,
            "recency_weighted_ipl": recency,
            "shrunk_pressure_uplift": shrunk,
            "split_targets": split,
            "pressure_only": pressure,
        })

        feat_pool = features.reindex(pool.index)
        order = estimates.apply(lambda pred: model.penalize_sparse_evidence(pred, feat_pool))

        actual = model.realized_ipl(history, start, end)
        same = actual.reindex(pool.index)

        for rec in recipes:
            # Policy 1: Standard Role Quota (apply_fit=True)
            sel_quota = model.candidate_order(order[rec], pool, "bowling", apply_fit=True)
            act_quota = same.reindex(sel_quota)
            errors = (same["target"] - estimates[rec]).abs()

            # Policy 2: Score-Only (apply_fit=False)
            sel_score = model.candidate_order(order[rec], pool, "bowling", apply_fit=False)
            act_score = same.reindex(sel_score)

            results.append({
                "season": year, "lane": lane, "cutoff": start.date().isoformat(), "recipe": rec,
                "training_rows": len(train), "candidate_count": len(pool), "mae": errors.mean(),
                # Role quota metrics
                "quota_assessed": act_quota["target"].count(),
                "quota_impact": act_quota["target"].sum() / 10.0,
                "quota_pressure": act_quota["actual_pressure"].sum() / 10.0,
                "quota_avg_assessed": act_quota["target"].mean() if act_quota["target"].count() > 0 else np.nan,
                # Score only metrics
                "score_assessed": act_score["target"].count(),
                "score_impact": act_score["target"].sum() / 10.0,
                "score_pressure": act_score["actual_pressure"].sum() / 10.0,
                "score_avg_assessed": act_score["target"].mean() if act_score["target"].count() > 0 else np.nan,
            })

    df = pd.DataFrame(results)
    print("\n--- FORWARD VALIDATION (2024-2025) ---")
    fwd = df.loc[df["lane"].eq("forward") & df["season"].lt(2026)]
    fwd_summary = fwd.groupby("recipe")[["mae", "quota_assessed", "quota_impact", "quota_pressure"]].mean()
    print(fwd_summary.to_string())

    print("\n--- 2026 RETROSPECTIVE CHECK ---")
    retro = df.loc[df["lane"].eq("forward") & df["season"].eq(2026)]
    retro_summary = retro.groupby("recipe")[["mae", "quota_assessed", "quota_impact", "quota_pressure"]].mean()
    print(retro_summary.to_string())

    print("\n--- AUCTION POOLS (2025 & 2026) ---")
    auc = df.loc[df["lane"].eq("auction")]
    auc_summary = auc.pivot(index="recipe", columns="season", values=["quota_assessed", "quota_impact", "quota_pressure", "mae"])
    print(auc_summary.to_string())

    df.to_csv("dashboard/scripts/bowling_experiment_results.csv", index=False)
    print("\nSaved results to dashboard/scripts/bowling_experiment_results.csv")


if __name__ == "__main__":
    with threadpool_limits(limits=1):
        run_experiment()
