"""Reapply verified IPL market decisions to saved RR player ratings."""

import argparse
from pathlib import Path

import pandas as pd

from rr_pressure.auction_robust import candidate_order


STATUSES = {"RR_RETAINED", "RIVAL_RETAINED", "RELEASED", "REGISTERED", "WITHDRAWN"}


def refresh(candidates, current, updates):
    for field in ("player_id", "status", "source_url"):
        if field not in updates or updates[field].isna().any():
            raise ValueError(f"Missing required evidence field {field}")
    if updates["player_id"].duplicated().any() or not updates["status"].isin(STATUSES).all():
        raise ValueError("Provide one supported market status per player")
    if not updates["source_url"].str.startswith("https://").all():
        raise ValueError("Provide an official https source for every market update")
    evidence = updates.set_index("player_id")
    current = current.set_index(["role", "player_id"])
    output = []
    for role, original in candidates.groupby("role", sort=False):
        ranked = original.set_index("player_id")
        status = evidence["status"].reindex(ranked.index)
        base_eligible = ranked.get("base_eligible", pd.Series(True, index=ranked.index))
        # An official release can reopen a previously assumed rival core slot.
        reopened = status.isin({"RELEASED", "REGISTERED", "RR_RETAINED"}) & ranked.get(
            "can_reopen_on_market_evidence", pd.Series(False, index=ranked.index),
        )
        eligible = ranked.loc[(base_eligible | reopened) & ~status.isin({"RIVAL_RETAINED", "WITHDRAWN"})]
        picks = candidate_order(eligible["priority"], eligible, role)
        if len(picks) != 10:
            raise ValueError(f"Only {len(picks)} eligible {role} options have model evidence")
        selected = eligible.loc[picks, ["player_name", "deployment", "priority"]].join(evidence)
        incumbent = current.loc[role, "route"].reindex(selected.index).eq("RR squad decision")
        selected["route"] = selected["status"].map({
            "RR_RETAINED": "RR squad decision", "RELEASED": "Released, registration pending",
            "REGISTERED": "On official auction list",
        }).fillna(incumbent.map({True: "RR squad decision pending", False: "Auction status unverified"}))
        output.append(selected.assign(role=role, rank=range(1, 11)).reset_index())
    return pd.concat(output, ignore_index=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("decision-dir", "updates", "output"):
        parser.add_argument(f"--{flag}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a new output path to preserve earlier rankings")
    pool = args.decision_dir / "auction_recruitment_pool.csv"
    candidates = pd.read_csv(pool if pool.exists() else args.decision_dir / "candidate_evidence.csv")
    current = pd.read_csv(args.decision_dir / "final_shortlist.csv")
    result = refresh(candidates, current, pd.read_csv(args.updates))
    result.to_csv(args.output, index=False)


if __name__ == "__main__":
    main()
