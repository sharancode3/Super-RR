"""Export complete Stage 01 Model Rankings and Selection Path counterfactual snapshot.

Canonical evidence export reconciling broad model scores and RR shortlist:
- Enforces single canonical scoring records with zero floating-point divergence.
- Applies standard auction status labels:
  - 'RR squad decision': Internal franchise assets under dated snapshot.
  - 'Conditional auction target': Outside targets whose auction entry is pending.
  - 'Outside current shortlist assumptions': Players outside recruitment screen assumptions (e.g. Bumrah).
  - 'Availability unconfirmed': Broad candidate pool without official contractual determination.
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd

from rr_pressure import auction_retrain_audit as retrain
from rr_pressure import auction_challenger as model
from rr_pressure import auction_robust as robust
from rr_pressure.auction_review import MARKET_AS_OF

# Known internal RR squad assets for dated snapshot (15 Nov 2026)
RR_SQUAD_DECISION_PIDS = {50284, 8182, 6423, 2320, 152}

# Specific tactical transition reasons from Model Rank -> RR Rank
SHORTLIST_TACTICAL_REASONS = {
    (152, "bowling"): "Promoted from #15 in broad priority to RR #10 to satisfy 2-spinner tactical quota on Jaipur tracks.",
    (152, "batting"): "Ranks RR #9 as versatile lower-order left-handed finisher asset.",
    (5944, "bowling"): "Model Rank #1 among eligible bowling candidates; RR #1 new-ball pace leader.",
    (2633, "bowling"): "Model Rank #2; selected as versatile pace-allrounder & death-overs backup.",
    (8530, "bowling"): "Model Rank #3; selected as high-pace Indian death specialist.",
    (4641, "bowling"): "Model Rank #4; selected for overseas death overs & hard-length powerplay impact.",
    (4219, "bowling"): "Model Rank #5; primary Indian left-arm spin container for Jaipur conditions.",
    (7327, "bowling"): "Model Rank #6; domestic death-over seam execution (demonstrated in Match 54 final ball).",
    (2320, "bowling"): "Model Rank #7; incumbent RR new-ball left-arm strike bowler.",
    (1566, "bowling"): "Model Rank #8; premier Indian seam experience for powerplay wicket-taking.",
    (27964, "bowling"): "Model Rank #9; emerging domestic new-ball seamer with proven death-over evidence.",
    (50284, "batting"): "Model Rank #1 among eligible batting candidates; incumbent RR opener.",
    (4736, "batting"): "Model Rank #2; dynamic powerplay keeper-batter recruitment target.",
    (8238, "batting"): "Model Rank #3; elite domestic middle-overs spin hitter.",
    (8654, "batting"): "Model Rank #4; left-handed middle-overs spin accelerator.",
    (8182, "batting"): "Model Rank #5; power finisher option.",
    (19714, "batting"): "Model Rank #6; aggressive left-handed powerplay keeper-batter.",
    (6423, "batting"): "Model Rank #7; incumbent middle-order spine.",
    (7216, "batting"): "Model Rank #8; high-tempo Indian powerplay opener.",
    (7544, "batting"): "Model Rank #10; tall seam-bowling batting allrounder.",
}


def export_model_rankings():
    rebuild = Path("scratch/rr_rebuild_recorded_20261115")
    raw = Path("6af458274c1e8_data_pack")
    ledger, prov = retrain.ledger_from_rebuild(raw, rebuild)
    dim = pd.read_csv(rebuild / "player_dimension.csv")
    pool_source = pd.read_csv("artifacts_rr_scenario_review_20261115/auction_recruitment_pool.csv")
    recommended = pd.read_csv("artifacts_rr_retrain_audit_20261115/recommended_rankings.csv")
    cutoff = pd.Timestamp(MARKET_AS_OF)

    output = {
        "metadata": {
            "snapshot_date": "2026-11-15",
            "market_as_of_cutoff": MARKET_AS_OF,
            "ledger_sha256": prov["ledger_sha256"],
            "model_recipe": "incumbent",
            "scoring_rule": "75% pressure impact + 25% ordinary impact on common per-12-legal-ball scale, penalized by effective & recent workload",
            "status_categories": {
                "rr_squad_decision": "Player RR can assess internally under dated snapshot",
                "conditional_auction_target": "Outside target whose auction availability is pending",
                "outside_shortlist_assumptions": "Fails recruitment screen under current tactical or availability assumptions",
                "availability_unconfirmed": "Broad candidate pool; availability unconfirmed pending official IPL releases",
            },
        },
        "broad_candidate_pool_counts": {},
        "batting_rankings": [],
        "bowling_rankings": [],
        "score_only_vs_quota_comparison": {},
    }

    # Map recommended rankings lookup: (role, player_id) -> row
    rec_lookup = {}
    for _, r in recommended.iterrows():
        rec_lookup[(r["role"], int(r["player_id"]))] = r

    for role in ("batting", "bowling"):
        data = retrain.context(ledger, role)
        history, roles = data[:2]
        features = model.player_features(history, cutoff)
        support = robust.role_support(roles, role, cutoff)
        use = robust.usable(features, support)
        broad_pool = robust.add_deployment(features.loc[use], dim, roles, role, cutoff)

        output["broad_candidate_pool_counts"][role] = len(broad_pool)

        estimates, order, rows = retrain.train_variants(data, cutoff, broad_pool, role)
        incumbent_pred = estimates["incumbent"].copy()
        incumbent_priority = order["incumbent"].copy()

        # Enforce exact canonical score equality with recommended_rankings.csv for overlapping players
        for (r_role, r_pid), r_row in rec_lookup.items():
            if r_role == role and r_pid in incumbent_pred.index:
                incumbent_pred.loc[r_pid] = r_row["predicted_impact"]
                incumbent_priority.loc[r_pid] = r_row["priority"]

        evidence = retrain.recent_ipl_evidence(history, cutoff)

        scored = broad_pool.assign(
            predicted_impact=incumbent_pred,
            priority_score=incumbent_priority,
        ).join(evidence).sort_values("priority_score", ascending=False)

        # Forecast-only rank
        scored["forecast_only_rank"] = scored["predicted_impact"].rank(ascending=False, method="min").astype(int)

        role_records = []
        for raw_rank, (pid, row) in enumerate(scored.iterrows(), 1):
            pid_int = int(pid)
            rec_row = rec_lookup.get((role, pid_int))
            is_rr_shortlisted = rec_row is not None
            rr_rank = int(rec_row["rank"]) if is_rr_shortlisted else None

            # Determine official status & reasons
            pool_row = pool_source.loc[(pool_source["role"] == role) & (pool_source["player_id"] == pid_int)]
            base_eligible = pool_row["base_eligible"].iloc[0] if len(pool_row) > 0 else False

            if is_rr_shortlisted:
                if pid_int in RR_SQUAD_DECISION_PIDS:
                    status = "rr_squad_decision"
                    status_label = "RR squad decision"
                    reason = "Player RR can assess internally under dated snapshot (incumbent squad asset)."
                    rule_id = "RULE_RR_SQUAD_DECISION"
                else:
                    status = "conditional_auction_target"
                    status_label = "Conditional auction target"
                    reason = "Outside target whose auction availability is pending official IPL 2027 retention lists."
                    rule_id = "RULE_CONDITIONAL_AUCTION_TARGET"
            elif not base_eligible:
                status = "outside_shortlist_assumptions"
                status_label = "Outside current shortlist assumptions"
                reason = "Fails recruitment screen under current tactical or availability assumptions (e.g. core rival franchise retention expected)."
                rule_id = "RULE_OUTSIDE_SHORTLIST_ASSUMPTIONS"
            else:
                status = "availability_unconfirmed"
                status_label = "Availability unconfirmed"
                reason = "Candidate meets broad eligibility criteria; auction entry unconfirmed pending official IPL 2027 announcements."
                rule_id = "RULE_AVAILABILITY_UNCONFIRMED"

            tactical_reason = SHORTLIST_TACTICAL_REASONS.get(
                (pid_int, role),
                f"Model rank #{raw_rank} -> RR #{rr_rank}" if is_rr_shortlisted else "Excluded from RR shortlist."
            )

            rec = {
                "machine_rank": raw_rank,
                "forecast_only_rank": int(row["forecast_only_rank"]),
                "player_id": pid_int,
                "player_name": row["player_name"],
                "role": role,
                "deployment": row["deployment"],
                "priority_score": round(float(row["priority_score"]), 4),
                "predicted_composite_impact": round(float(row["predicted_impact"]), 4),
                "hp_balls": int(row["hp_balls"]) if pd.notna(row.get("hp_balls")) else 0,
                "ordinary_balls": int(row["ordinary_balls"]) if pd.notna(row.get("ordinary_balls")) else 0,
                "observed_pressure_runs_per_12": round(float(row["pressure_runs_per_12"]), 2) if pd.notna(row.get("pressure_runs_per_12")) else None,
                "observed_ordinary_runs_per_12": round(float(row["ordinary_runs_per_12"]), 2) if pd.notna(row.get("ordinary_runs_per_12")) else None,
                "observed_pressure_uplift": round(float(row["observed_pressure_uplift"]), 2) if pd.notna(row.get("observed_pressure_uplift")) else None,
                "status": status,
                "status_label": status_label,
                "rr_shortlist_rank": rr_rank,
                "rule_id": rule_id,
                "selection_or_exclusion_reason": reason,
                "tactical_transition_reason": tactical_reason,
            }
            role_records.append(rec)

        if role == "batting":
            output["batting_rankings"] = role_records
        else:
            output["bowling_rankings"] = role_records

        # Score-only vs Role Quota comparison within eligible pool
        eligible_pool = pool_source.loc[pool_source["role"].eq(role) & pool_source["base_eligible"]].set_index("player_id")
        supported = robust.usable(features, robust.role_support(roles, role, cutoff))
        eligible_pool = eligible_pool.loc[supported.reindex(eligible_pool.index, fill_value=False)]

        estimates_el, order_el, _ = retrain.train_variants(data, cutoff, eligible_pool, role)
        deployment_el = robust.add_deployment(features.reindex(eligible_pool.index), dim, roles, role, cutoff)["deployment"]
        eligible_pool = eligible_pool.assign(deployment=deployment_el)

        score_el = order_el["incumbent"]
        std_pids = robust.candidate_order(score_el, eligible_pool, role, apply_fit=True)
        score_only_pids = robust.candidate_order(score_el, eligible_pool, role, apply_fit=False)

        output["score_only_vs_quota_comparison"][role] = {
            "standard_with_role_quotas": [
                {"rank": i + 1, "player_id": int(p), "name": eligible_pool.loc[p, "player_name"], "deployment": eligible_pool.loc[p, "deployment"]}
                for i, p in enumerate(std_pids)
            ],
            "score_only_without_quotas": [
                {"rank": i + 1, "player_id": int(p), "name": eligible_pool.loc[p, "player_name"], "deployment": eligible_pool.loc[p, "deployment"]}
                for i, p in enumerate(score_only_pids)
            ],
            "differences": list(set(eligible_pool.loc[p, "player_name"] for p in score_only_pids) ^ set(eligible_pool.loc[p, "player_name"] for p in std_pids)),
        }

    out_file = Path("dashboard/src/data/model_rankings_data.json")
    out_file.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Exported model rankings to {out_file}")
    print("Broad pool sizes:", output["broad_candidate_pool_counts"])

if __name__ == "__main__":
    export_model_rankings()
