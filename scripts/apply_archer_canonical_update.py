"""Apply the agreed one-player revision to canonical evidence files:
- Replace Trent Boult (2320) with Jofra Archer (3298) at No. 10 on the final RR bowling shortlist.
- Shift Mohammed Shami (1566) -> rank 7.
- Shift Anshul Kamboj (27964) -> rank 8.
- Shift Ravindra Jadeja (152) -> rank 9.
- Add Jofra Archer (3298) -> rank 10.
- Batting slate (10 players) remains 100% untouched.
"""

import pandas as pd
import json
from pathlib import Path

WORKSPACE = Path("C:/SHARAN PROJECTS/rr")

# 1. Update recommended_rankings.csv
rec_path = WORKSPACE / "artifacts_rr_retrain_audit_20261115/recommended_rankings.csv"
rec_df = pd.read_csv(rec_path)

# Separate batting and bowling
bat_rec = rec_df[rec_df["role"] == "batting"].copy()
bowl_rec = rec_df[rec_df["role"] == "bowling"].copy()

# Remove Boult (2320)
bowl_rec = bowl_rec[bowl_rec["player_id"] != 2320].copy()

# Update ranks for Shami, Kamboj, Jadeja
bowl_rec.loc[bowl_rec["player_id"] == 1566, "rank"] = 7
bowl_rec.loc[bowl_rec["player_id"] == 27964, "rank"] = 8
bowl_rec.loc[bowl_rec["player_id"] == 152, "rank"] = 9

# Add Jofra Archer (3298) as rank 10
archer_rec_row = {
    "player_id": 3298,
    "player_name": "Jofra Archer",
    "deployment": "POWERPLAY",
    "hp_balls": 106.0,
    "ordinary_balls": 242.0,
    "pressure_runs_per_12": -1.9832927237090333,
    "ordinary_runs_per_12": 3.031782294119859,
    "observed_pressure_uplift": -5.015075017828892,
    "source": "recorded_extras",
    "role": "bowling",
    "recipe": "incumbent",
    "rank": 10,
    "priority": -0.42743859468032225,
    "predicted_impact": 0.6437885387299954,
}
bowl_rec = pd.concat([bowl_rec, pd.DataFrame([archer_rec_row])], ignore_index=True)
bowl_rec = bowl_rec.sort_values("rank").reset_index(drop=True)

new_rec_df = pd.concat([bat_rec, bowl_rec], ignore_index=True)
new_rec_df.to_csv(rec_path, index=False)
print("Updated recommended_rankings.csv successfully.")


# 2. Update player_evidence.csv
ev_path = WORKSPACE / "artifacts_rr_retrain_audit_20261115/player_evidence.csv"
ev_df = pd.read_csv(ev_path)

bat_ev = ev_df[ev_df["role"] == "batting"].copy()
bowl_ev = ev_df[ev_df["role"] == "bowling"].copy()

# Remove Boult (rank 7)
bowl_ev = bowl_ev[bowl_ev["player_name"] != "Trent Boult"].copy()

# Shift ranks
bowl_ev.loc[bowl_ev["player_name"] == "Mohammed Shami", "rank"] = 7
bowl_ev.loc[bowl_ev["player_name"] == "Anshul Kamboj", "rank"] = 8
bowl_ev.loc[bowl_ev["player_name"] == "Ravindra Jadeja", "rank"] = 9

# Add Archer
archer_ev_row = {
    "role": "bowling",
    "rank": 10,
    "player_name": "Jofra Archer",
    "deployment": "POWERPLAY",
    "predicted_impact": 0.6437885387299954,
    "balls": 106.0,
    "fixtures": 13.0,
    "pressure_per_12": -1.9832927237090333,
    "loo_min": -3.753449797242161,
    "loo_max": -0.6926178100186396,
    "stability": 0.258,
    "route": "RR squad decision",
    "rr_fit_and_risk": "RR right-arm new-ball pace. 106 recent pressure balls (-1.98 r/12). Backed under internal franchise squad decision to partner Siraj; trades away Boult's left-arm angle.",
}
bowl_ev = pd.concat([bowl_ev, pd.DataFrame([archer_ev_row])], ignore_index=True)
bowl_ev = bowl_ev.sort_values("rank").reset_index(drop=True)

new_ev_df = pd.concat([bat_ev, bowl_ev], ignore_index=True)
new_ev_df.to_csv(ev_path, index=False)
print("Updated player_evidence.csv successfully.")


# 3. Update verified_rankings.csv
ver_path = WORKSPACE / "artifacts_rr_scenario_review_20261115/verified_rankings.csv"
ver_df = pd.read_csv(ver_path)

bat_ver = ver_df[ver_df["role"] == "batting"].copy()
bowl_ver = ver_df[ver_df["role"] == "bowling"].copy()

# Remove Boult
bowl_ver = bowl_ver[bowl_ver["verified_unstop_label"] != "Trent Boult"].copy()

# Shift ranks
bowl_ver.loc[bowl_ver["verified_unstop_label"] == "Mohammed Shami", "rank"] = 7
bowl_ver.loc[bowl_ver["verified_unstop_label"] == "Anshul Kamboj", "rank"] = 8
bowl_ver.loc[bowl_ver["verified_unstop_label"] == "Ravindra Jadeja", "rank"] = 9

archer_ver_row = {
    "role": "bowling",
    "rank": 10,
    "verified_unstop_label": "Jofra Archer",
    "deployment": "POWERPLAY",
    "route": "RR squad decision",
    "top10_stability": 0.258,
    "recent_balls": 106,
    "ipl_pressure_observed": 0.212049224378012,
    "ipl_ordinary_observed": -0.0735075793284452,
}
bowl_ver = pd.concat([bowl_ver, pd.DataFrame([archer_ver_row])], ignore_index=True)
bowl_ver = bowl_ver.sort_values("rank").reset_index(drop=True)

new_ver_df = pd.concat([bat_ver, bowl_ver], ignore_index=True)
new_ver_df.to_csv(ver_path, index=False)
print("Updated verified_rankings.csv successfully.")


# 4. Update scenario_review_rankings_with_stability.csv
stab_path = WORKSPACE / "artifacts_rr_scenario_review_20261115/scenario_review_rankings_with_stability.csv"
stab_df = pd.read_csv(stab_path)

bat_stab = stab_df[stab_df["role"] == "batting"].copy()
bowl_stab = stab_df[stab_df["role"] == "bowling"].copy()

# Remove Boult (2320)
bowl_stab = bowl_stab[bowl_stab["player_id"] != 2320].copy()

# Shift ranks
bowl_stab.loc[bowl_stab["player_id"] == 1566, "rank"] = 7
bowl_stab.loc[bowl_stab["player_id"] == 27964, "rank"] = 8
bowl_stab.loc[bowl_stab["player_id"] == 152, "rank"] = 9

archer_stab_row = {
    "player_id": 3298,
    "player_name": "Jofra Archer",
    "deployment": "POWERPLAY",
    "route": "RR squad decision",
    "recipe": "incumbent",
    "scenario": "current_market",
    "rank": 10,
    "priority": -0.42743859468032225,
    "role": "bowling",
    "stability": 0.258,
}
bowl_stab = pd.concat([bowl_stab, pd.DataFrame([archer_stab_row])], ignore_index=True)
bowl_stab = bowl_stab.sort_values("rank").reset_index(drop=True)

new_stab_df = pd.concat([bat_stab, bowl_stab], ignore_index=True)
new_stab_df.to_csv(stab_path, index=False)
print("Updated scenario_review_rankings_with_stability.csv successfully.")
