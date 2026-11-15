"""Stage 3 Targeted Batting Challenger: Delivery-Level Runs & Striker Dismissal Hazard Partial Pooling.

Learns separate context-adjusted models from ordinary + high-pressure legal deliveries:
  1. Excess net runs per legal ball: runs - expected_bat_runs
  2. Excess striker dismissal probability per legal ball: is_striker_dismissed - expected_striker_dismissal

Retains genuine 1-to-5-ball pressure outings cleanly alongside >=6b and ordinary deliveries,
classifies short outings by observable cause (DISMISSED, INNINGS_END_NOT_OUT, OTHER_NOT_OUT),
and accounts for dismissal terminating a batter's 12-ball opportunity alongside expanding-window
chronological uncertainty calibration.
"""

from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.stats import t as student_t

from rr_pressure.role_challenger import PHASES, VALID_ROLES, infer_role_family


def build_batting_stint_cause_audit(
    deliv_df: pd.DataFrame,
    max_date: Optional[str] = None,
) -> pd.DataFrame:
    """Summarize HP batting stints with short-outing cause classification (DISMISSED / INNINGS_END_NOT_OUT / OTHER_NOT_OUT)."""
    mask = (deliv_df["is_legal_ball"] == 1)
    if "is_reliability_eligible" in deliv_df.columns:
        mask &= deliv_df["is_reliability_eligible"].astype(bool)
    elif "is_cohort_eligible" in deliv_df.columns:
        mask &= deliv_df["is_cohort_eligible"].astype(bool)
    if max_date is not None and "match_date" in deliv_df.columns:
        mask &= deliv_df["match_date"].astype(str) <= str(max_date)

    rel = deliv_df.loc[mask].copy()
    if rel.empty:
        return pd.DataFrame()
    hp_col = "is_high_pressure_20" if "is_high_pressure_20" in rel.columns else "is_high_pressure"
    inn_last = rel.groupby(["match_id", "innings"])["innings_ball_num"].max().rename("inn_last_ball")
    hp = rel[rel[hp_col].astype(bool)].merge(inn_last, on=["match_id", "innings"], how="left")
    if hp.empty:
        return pd.DataFrame()

    grp = hp.groupby(["match_id", "striker_id", "comp_tier", "match_date"], observed=False).agg(
        hp_balls=("is_legal_ball", "sum"),
        dismissed=("is_striker_dismissed", "max"),
        max_ball=("innings_ball_num", "max"),
        inn_last=("inn_last_ball", "first"),
        hp_impact=("batting_impact", "sum"),
        fold=("fold", "first") if "fold" in hp.columns else ("match_date", "first"),
    ).reset_index().rename(columns={"striker_id": "player_id"})
    grp["is_short_1_to_5b"] = grp["hp_balls"].between(1, 5)
    grp["short_cause"] = np.where(
        grp["hp_balls"] >= 6,
        "GE6_BALLS",
        np.where(
            grp["dismissed"] == 1,
            "DISMISSED",
            np.where(grp["max_ball"] == grp["inn_last"], "INNINGS_END_NOT_OUT", "OTHER_NOT_OUT"),
        ),
    )
    grp["hp_impact_12b"] = np.where(grp["hp_balls"] > 0, 12.0 * grp["hp_impact"] / grp["hp_balls"], np.nan)
    return grp


def build_batting_delivery_cells(
    deliv_df: pd.DataFrame,
    max_date: Optional[str] = None,
) -> pd.DataFrame:
    """Aggregate legal ordinary + HP batting deliveries to sufficient cell counts for exact Ridge fitting."""
    mask = (deliv_df["is_legal_ball"] == 1)
    if "is_reliability_eligible" in deliv_df.columns:
        mask &= deliv_df["is_reliability_eligible"].astype(bool)
    elif "is_cohort_eligible" in deliv_df.columns:
        mask &= deliv_df["is_cohort_eligible"].astype(bool)
    if max_date is not None and "match_date" in deliv_df.columns:
        mask &= deliv_df["match_date"].astype(str) <= str(max_date)

    sub = deliv_df.loc[mask].copy()
    if sub.empty:
        return pd.DataFrame()
    sub["season"] = pd.to_numeric(sub["match_date"].astype(str).str[:4], errors="coerce").fillna(2024).astype(int)
    hp_col = "is_high_pressure_20" if "is_high_pressure_20" in sub.columns else "is_high_pressure"
    sub["excess_runs"] = sub["runs"].astype(float) - sub["expected_bat_runs"].astype(float)
    sub["excess_dismissal"] = sub["is_striker_dismissed"].astype(float) - sub["expected_striker_dismissal"].astype(float)
    sub["w_s_col"] = sub["marginal_wicket_value_ws"].astype(float) if "marginal_wicket_value_ws" in sub.columns else 7.0

    grp_cols = ["match_id", "striker_id", "match_phase", "innings", hp_col, "comp_tier", "match_date", "season"]
    if "fold" in sub.columns:
        grp_cols.append("fold")
    cells = (
        sub.groupby(grp_cols, observed=False)
        .agg(
            legal_balls=("is_legal_ball", "sum"),
            excess_runs_sum=("excess_runs", "sum"),
            excess_dismissal_sum=("excess_dismissal", "sum"),
            exp_dismissal_sum=("expected_striker_dismissal", "sum"),
            w_s_mean=("w_s_col", "mean"),
            impact_sum=("batting_impact", "sum"),
            dismissed=("is_striker_dismissed", "max"),
        )
        .reset_index()
        .rename(columns={grp_col_p: "player_id" for grp_col_p in ["striker_id"]} | {hp_col: "is_high_pressure"})
    )
    cells["excess_runs_rate"] = cells["excess_runs_sum"] / np.maximum(1, cells["legal_balls"])
    cells["excess_dismissal_rate"] = cells["excess_dismissal_sum"] / np.maximum(1, cells["legal_balls"])
    return cells


class ChallengerDHP_BattingDeliveryHazard:
    """Delivery-Level Context-Adjusted Runs & Dismissal Hazard Partial-Pooling Model."""

    def __init__(
        self,
        lam_runs_ord: float = 120.0,
        lam_runs_hp: float = 180.0,
        lam_dism_ord: float = 240.0,
        lam_dism_hp: float = 360.0,
        half_life_seasons: float = 2.5,
        w_t20i: float = 0.20,
        w_emerging: float = 0.05,
        df: int = 5,
        transfer_penalty_scale: float = 2.5,
        cutoff_label: str = "UNSPECIFIED",
    ):
        self.lam_runs_ord = lam_runs_ord
        self.lam_runs_hp = lam_runs_hp
        self.lam_dism_ord = lam_dism_ord
        self.lam_dism_hp = lam_dism_hp
        self.half_life_seasons = half_life_seasons
        self.w_t20i = w_t20i
        self.w_emerging = w_emerging
        self.df = df
        self.transfer_penalty_scale = transfer_penalty_scale
        self.cutoff_label = cutoff_label

        self.theta_r_: Optional[np.ndarray] = None
        self.theta_d_: Optional[np.ndarray] = None
        self.player_profiles_: Dict[int, Dict[str, Any]] = {}
        self.sig_cal_ge6_: float = 7.0
        self.sig_cal_all_: float = 12.0
        self.role_sig_ge6_: Dict[str, float] = {}
        self.global_prior_: float = 0.0
        self.fit_meta_: Dict[str, Any] = {}

    @staticmethod
    def _compute_phase_weights_and_baselines(df_sub: pd.DataFrame) -> Tuple[Any, Any, Any, Dict[Tuple[str, int], Tuple[float, float]]]:
        ipl_all = df_sub[df_sub["comp_tier"] == "IPL"]
        fallback_glob = {("DEATH", 2): 0.35, ("MIDDLE", 1): 0.35, ("POWERPLAY", 1): 0.30}
        if ipl_all.empty:
            return fallback_glob, {}, {}, {k: (0.05, 7.0) for k in fallback_glob}
        gw = ipl_all.groupby(["match_phase", "innings"])["legal_balls"].sum()
        g_sum = float(gw.sum())
        glob_w = (gw / g_sum).to_dict() if g_sum > 0 else fallback_glob
        rw_tab = ipl_all.groupby(["role_fam", "match_phase", "innings"])["legal_balls"].sum()
        role_w: Dict[str, Dict[Tuple[str, int], float]] = {}
        r_lvl = rw_tab.index.get_level_values(0)
        for rf in set(df_sub["role_fam"].unique()) | set(VALID_ROLES) | {"OTHER"}:
            if rf in r_lvl:
                sub_w = rw_tab.xs(rf, level="role_fam")
                role_w[rf] = (sub_w / sub_w.sum()).to_dict() if float(sub_w.sum()) >= 24 else glob_w
            else:
                role_w[rf] = glob_w
        pw_tab = ipl_all.groupby(["player_id", "match_phase", "innings"])["legal_balls"].sum()
        player_w: Dict[int, Dict[Tuple[str, int], float]] = {}
        for pid in ipl_all["player_id"].unique():
            sub_pw = pw_tab.xs(pid, level="player_id")
            if float(sub_pw.sum()) >= 24:
                player_w[int(pid)] = (sub_pw / sub_pw.sum()).to_dict()

        ipl_hp = ipl_all[ipl_all["is_high_pressure"] == True]
        base_src = ipl_hp if not ipl_hp.empty else ipl_all
        glob_d = float(base_src["exp_dismissal_sum"].sum() / max(1.0, base_src["legal_balls"].sum()))
        glob_wval = float(np.average(base_src["w_s_mean"], weights=np.maximum(1, base_src["legal_balls"])))
        base_stats: Dict[Tuple[str, int], Tuple[float, float]] = {}
        for (ph, inn), grp in base_src.groupby(["match_phase", "innings"]):
            b = float(grp["legal_balls"].sum())
            d_base = float(grp["exp_dismissal_sum"].sum() / max(1.0, b))
            w_base = float(np.average(grp["w_s_mean"], weights=np.maximum(1, grp["legal_balls"])))
            base_stats[(str(ph), int(inn))] = (d_base, w_base)
        base_stats[("_DEFAULT", 0)] = (glob_d, glob_wval)
        return glob_w, role_w, player_w, base_stats

    def _fit_two_head_core(
        self,
        df_fit: pd.DataFrame,
        role_fam_map: Dict[int, str],
    ) -> Tuple[np.ndarray, np.ndarray, Any, Dict[int, int]]:
        work = df_fit[df_fit["legal_balls"] > 0].copy()
        work["role_fam"] = work["player_id"].map(role_fam_map).fillna("OTHER")

        cutoff_yr = int(str(work["match_date"].max())[:4])
        seasons = pd.to_numeric(work["season"], errors="coerce").fillna(cutoff_yr).astype(float)
        comp_w = {"IPL": 1.0, "T20I": self.w_t20i, "INTERNATIONAL": self.w_t20i, "EMERGING": self.w_emerging}
        w_comp = work["comp_tier"].map(comp_w).fillna(self.w_emerging).values
        w_rec = 0.5 ** (np.maximum(0.0, cutoff_yr - seasons.values) / self.half_life_seasons)
        # Delivery-level sufficient count weights: weight strictly by legal balls * tier * recency (no <6 exclusion)
        w_tr = w_comp * w_rec * work["legal_balls"].astype(float).values

        roles = sorted(set(work["role_fam"].unique()) | set(VALID_ROLES) | {"OTHER"})
        rp_list = [(r, ph) for r in roles for ph in PHASES]
        pids = sorted(int(p) for p in work["player_id"].unique())
        pid_to_idx = {pid: i for i, pid in enumerate(pids)}
        rp_to_idx = {rp: i for i, rp in enumerate(rp_list)}
        ph_to_idx = {ph: i for i, ph in enumerate(PHASES)}

        off_ph = 3
        off_rp_ord = off_ph + len(PHASES)
        off_hp = off_rp_ord + len(rp_list)
        off_rp_hp = off_hp + 1
        off_p_ord = off_rp_hp + len(rp_list)
        off_p_hp = off_p_ord + len(pids)
        n_cols = off_p_hp + len(pids)

        def build_X(df_in: pd.DataFrame, force_hp: Optional[float] = None, force_non_ipl: Optional[float] = None) -> sparse.csr_matrix:
            n = len(df_in)
            if n == 0:
                return sparse.csr_matrix((0, n_cols))
            r_idx = np.arange(n)
            nipl = np.full(n, float(force_non_ipl)) if force_non_ipl is not None else (df_in["comp_tier"].values != "IPL").astype(float)
            ph_arr = df_in["match_phase"].map(ph_to_idx).fillna(1).astype(int).values
            rf_vals = df_in["role_fam"].values if "role_fam" in df_in.columns else df_in["player_id"].map(role_fam_map).fillna("OTHER").values
            rp_arr = np.array([rp_to_idx.get((rf, ph), 0) for rf, ph in zip(rf_vals, df_in["match_phase"].values)], dtype=int)
            hp = np.full(n, float(force_hp)) if force_hp is not None else df_in["is_high_pressure"].astype(float).values

            rows_i = [r_idx, r_idx, r_idx, r_idx, r_idx, r_idx]
            cols_j = [
                np.zeros(n, dtype=int),
                np.full(n, 1, dtype=int),
                np.full(n, 2, dtype=int),
                off_ph + ph_arr,
                off_rp_ord + rp_arr,
                off_hp + np.zeros(n, dtype=int),
            ]
            vals = [np.ones(n), nipl, nipl * hp, np.ones(n), np.ones(n), hp]
            rows_i.append(r_idx)
            cols_j.append(off_rp_hp + rp_arr)
            vals.append(hp)

            p_arr = np.array([pid_to_idx.get(int(p), -1) for p in df_in["player_id"].values], dtype=int)
            pmask = p_arr >= 0
            if pmask.any():
                rows_i.append(r_idx[pmask])
                cols_j.append(off_p_ord + p_arr[pmask])
                vals.append(np.ones(pmask.sum()))
                rows_i.append(r_idx[pmask])
                cols_j.append(off_p_hp + p_arr[pmask])
                vals.append(hp[pmask])

            return sparse.csr_matrix(
                (np.concatenate(vals), (np.concatenate(rows_i), np.concatenate(cols_j))),
                shape=(n, n_cols),
            )

        X_tr = build_X(work)
        WX = X_tr.multiply(w_tr[:, None])
        XtWX = (X_tr.T @ WX).toarray()

        pen_r = np.zeros(n_cols, dtype=float)
        pen_r[0] = 1e-4
        pen_r[1:3] = 20.0
        pen_r[off_ph:off_rp_ord] = 30.0
        pen_r[off_rp_ord:off_hp] = 60.0
        pen_r[off_hp] = 30.0
        pen_r[off_rp_hp:off_p_ord] = 80.0
        pen_r[off_p_ord:off_p_hp] = self.lam_runs_ord
        pen_r[off_p_hp:] = self.lam_runs_hp

        pen_d = np.zeros(n_cols, dtype=float)
        pen_d[0] = 1e-4
        pen_d[1:3] = 50.0
        pen_d[off_ph:off_rp_ord] = 80.0
        pen_d[off_rp_ord:off_hp] = 160.0
        pen_d[off_hp] = 80.0
        pen_d[off_rp_hp:off_p_ord] = 200.0
        pen_d[off_p_ord:off_p_hp] = self.lam_dism_ord
        pen_d[off_p_hp:] = self.lam_dism_hp

        Hr = XtWX.copy()
        Hr[np.diag_indices_from(Hr)] += pen_r
        Hd = XtWX.copy()
        Hd[np.diag_indices_from(Hd)] += pen_d

        theta_r = np.linalg.solve(Hr, X_tr.T @ (w_tr * work["excess_runs_rate"].values))
        theta_d = np.linalg.solve(Hd, X_tr.T @ (w_tr * work["excess_dismissal_rate"].values))
        return theta_r, theta_d, build_X, pid_to_idx

    @staticmethod
    def _score_players_from_heads(
        pids: Iterable[int],
        role_fam_map: Dict[int, str],
        theta_r: np.ndarray,
        theta_d: np.ndarray,
        build_X: Any,
        glob_w: Dict[Tuple[str, int], float],
        role_w: Dict[str, Dict[Tuple[str, int], float]],
        player_w: Dict[int, Dict[Tuple[str, int], float]],
        base_stats: Dict[Tuple[str, int], Tuple[float, float]],
    ) -> pd.DataFrame:
        sc_rows: List[Dict[str, Any]] = []
        for pid in sorted({int(p) for p in pids}):
            rf = role_fam_map.get(pid, "OTHER")
            r_mix = role_w.get(rf, glob_w)
            p_mix = player_w.get(pid)
            if p_mix is not None:
                keys = set(r_mix) | set(p_mix)
                mix = {k: 0.70 * p_mix.get(k, 0.0) + 0.30 * r_mix.get(k, 0.0) for k in keys}
            else:
                mix = r_mix
            tot_w = sum(mix.values()) or 1.0
            d_def, w_def = base_stats.get(("_DEFAULT", 0), (0.05, 7.0))
            for (ph, inn), w_val in mix.items():
                if w_val > 0:
                    d0, ws0 = base_stats.get((ph, int(inn)), (d_def, w_def))
                    sc_rows.append({
                        "player_id": int(pid),
                        "role_fam": rf,
                        "match_phase": ph,
                        "innings": int(inn),
                        "sc_wt": float(w_val / tot_w),
                        "comp_tier": "IPL",
                        "base_d": d0,
                        "base_ws": ws0,
                    })
        sc_df = pd.DataFrame(sc_rows)
        X_ord = build_X(sc_df, force_hp=0.0, force_non_ipl=0.0).toarray()
        X_hp = build_X(sc_df, force_hp=1.0, force_non_ipl=0.0).toarray()

        dr_ord = X_ord @ theta_r
        dd_ord = X_ord @ theta_d
        dr_hp = X_hp @ theta_r
        dd_hp = X_hp @ theta_d

        # Per-ball expected net impact & 12-ball dismissal-stopping expected survival balls L(p)
        p_ord = np.clip(sc_df["base_d"].values + dd_ord, 0.005, 0.45)
        p_hp = np.clip(sc_df["base_d"].values + dd_hp, 0.005, 0.45)
        l_ord = (1.0 - (1.0 - p_ord) ** 12) / p_ord
        l_hp = (1.0 - (1.0 - p_hp) ** 12) / p_hp

        ws = sc_df["base_ws"].values
        sc_df["mu_ord_12b"] = 12.0 * (dr_ord - ws * dd_ord)
        sc_df["mu_hp_12b"] = 12.0 * (dr_hp - ws * dd_hp)
        sc_df["runs_hp_12b"] = 12.0 * dr_hp
        sc_df["dism_hp_prob"] = p_hp
        sc_df["expected_survived_balls_12"] = l_hp
        sc_df["hazard_hp_12b_stint"] = l_hp * (dr_hp - ws * dd_hp)

        for c in ("mu_ord_12b", "mu_hp_12b", "runs_hp_12b", "dism_hp_prob", "expected_survived_balls_12", "hazard_hp_12b_stint"):
            sc_df[c] = sc_df[c] * sc_df["sc_wt"]
        agg = sc_df.groupby("player_id", as_index=False)[
            ["mu_ord_12b", "mu_hp_12b", "runs_hp_12b", "dism_hp_prob", "expected_survived_balls_12", "hazard_hp_12b_stint"]
        ].sum()
        return agg

    def fit(
        self,
        cells_df: pd.DataFrame,
        p_dim: pd.DataFrame,
    ) -> "ChallengerDHP_BattingDeliveryHazard":
        if cells_df is None or cells_df.empty:
            return self
        df_pos = cells_df[cells_df["legal_balls"] > 0].copy()
        p_map = p_dim.set_index("player_id")
        all_pids = set(df_pos["player_id"].astype(int)) | set(int(x) for x in p_map.index)
        role_fam_map = {
            pid: infer_role_family(p_map.loc[pid, "inferred_role"], p_map.loc[pid].get("bowler_type", "Unknown"))
            if pid in p_map.index
            else "OTHER"
            for pid in all_pids
        }
        df_pos["role_fam"] = df_pos["player_id"].map(role_fam_map).fillna("OTHER")

        # 1. Expanding-window chronological OOF calibration separately on ge6 and all>0b
        m_dates = df_pos[["match_id", "match_date"]].drop_duplicates().sort_values(["match_date", "match_id"])
        ordered_mids = m_dates["match_id"].tolist()
        oof_rows = []
        if len(ordered_mids) >= 6:
            warmup_n = max(3, int(round(0.35 * len(ordered_mids))))
            rem = ordered_mids[warmup_n:]
            chunks = np.array_split(np.array(rem, dtype=int), min(4, max(1, len(rem))))
            prior_mids = set(int(x) for x in ordered_mids[:warmup_n])
            for ch in chunks:
                val_mids = set(int(x) for x in ch.tolist())
                if not val_mids:
                    continue
                tr_k = df_pos[df_pos["match_id"].isin(prior_mids)]
                va_k = df_pos[df_pos["match_id"].isin(val_mids) & (df_pos["comp_tier"] == "IPL") & (df_pos["is_high_pressure"] == True)]
                if not tr_k.empty and not va_k.empty:
                    th_r, th_d, bx_k, _ = self._fit_two_head_core(tr_k, role_fam_map)
                    gw, rw, pw, bs = self._compute_phase_weights_and_baselines(tr_k)
                    m_k = va_k.groupby(["match_id", "player_id"], as_index=False).agg(b=("legal_balls", "sum"), imp=("impact_sum", "sum"))
                    prof_k = self._score_players_from_heads(m_k["player_id"].unique(), role_fam_map, th_r, th_d, bx_k, gw, rw, pw, bs)
                    m_k = m_k.merge(prof_k[["player_id", "mu_hp_12b"]], on="player_id", how="left")
                    m_k["mu"] = m_k["mu_hp_12b"].fillna(0.0)
                    m_k["y"] = 12.0 * m_k["imp"] / m_k["b"]
                    m_k["err"] = m_k["y"] - m_k["mu"]
                    oof_rows.append(m_k)
                prior_mids.update(val_mids)

        t_crit = float(student_t.ppf(0.75, df=self.df))
        if oof_rows:
            oof_df = pd.concat(oof_rows, ignore_index=True)
            oof_ge6 = oof_df[oof_df["b"] >= 6]
            ref = oof_ge6 if len(oof_ge6) >= 30 else oof_df
            self.sig_cal_ge6_ = max(3.5, -float(np.quantile(ref["err"].values, 0.25)) / t_crit)
            self.sig_cal_all_ = max(3.5, -float(np.quantile(oof_df["err"].values, 0.25)) / t_crit)
        else:
            self.sig_cal_ge6_ = 7.0
            self.sig_cal_all_ = 12.0

        # 2. Full pre-cutoff fit
        th_r, th_d, bx, pid_to_idx = self._fit_two_head_core(df_pos, role_fam_map)
        self.theta_r_ = th_r
        self.theta_d_ = th_d
        gw, rw, pw, bs = self._compute_phase_weights_and_baselines(df_pos)
        prof_df = self._score_players_from_heads(all_pids, role_fam_map, th_r, th_d, bx, gw, rw, pw, bs)

        hp_only = df_pos[df_pos["is_high_pressure"] == True]
        ipl_hp = hp_only[hp_only["comp_tier"] == "IPL"]
        tot_hp_b = hp_only.groupby("player_id")["legal_balls"].sum().to_dict()
        ipl_hp_b = ipl_hp.groupby("player_id")["legal_balls"].sum().to_dict()
        ipl_hp_m = ipl_hp.groupby("player_id")["match_id"].nunique().to_dict()
        cutoff_yr = int(str(df_pos["match_date"].max())[:4])
        rec_ipl_b = ipl_hp[ipl_hp["season"].isin({cutoff_yr, cutoff_yr - 1})].groupby("player_id")["legal_balls"].sum().to_dict()

        eff_hp_b_map = (
            hp_only.assign(_wb=hp_only["legal_balls"] * hp_only["comp_tier"].map({"IPL": 1.0, "T20I": self.w_t20i, "INTERNATIONAL": self.w_t20i, "EMERGING": self.w_emerging}).fillna(0.05))
            .groupby("player_id")["_wb"].sum().to_dict()
        )
        t_80 = float(student_t.ppf(0.90, df=self.df))
        self.player_profiles_ = {}
        for _, r in prof_df.iterrows():
            pid = int(r["player_id"])
            tot_b = float(tot_hp_b.get(pid, 0.0))
            ipl_b = float(ipl_hp_b.get(pid, 0.0))
            eb = float(eff_hp_b_map.get(pid, 0.0))
            ipl_share = ipl_b / tot_b if tot_b > 0 else 0.0
            pen_t = self.transfer_penalty_scale * (1.0 - ipl_share)
            rec_b = float(rec_ipl_b.get(pid, 0.0))
            m_ipl = int(ipl_hp_m.get(pid, 0))
            pen_s = 1.5 if (ipl_b > 0 and rec_b == 0) else (0.75 if (ipl_b > 0 and m_ipl <= 1) else 0.0)
            se_p = float(self.sig_cal_ge6_ * 0.65 / np.sqrt(1.0 + eb / 24.0))
            sig = float(np.sqrt(self.sig_cal_ge6_**2 + se_p**2 + pen_t**2 + pen_s**2))
            mu_hp = float(r["mu_hp_12b"])
            mu_ord = float(r["mu_ord_12b"])
            self.player_profiles_[pid] = {
                "player_id": pid,
                "usual_ipl_12b": mu_ord,
                "predicted_hp_12b": mu_hp,
                "pressure_delta_12b": mu_hp - mu_ord,
                "runs_hp_12b": float(r["runs_hp_12b"]),
                "dism_hp_prob": float(r["dism_hp_prob"]),
                "expected_survived_balls_12": float(r["expected_survived_balls_12"]),
                "hazard_hp_12b_stint": float(r["hazard_hp_12b_stint"]),
                "q25_12b": float(mu_hp - t_crit * sig),
                "q10_12b": float(mu_hp - t_80 * sig),
                "q90_12b": float(mu_hp + t_80 * sig),
                "ipl_hp_balls": int(ipl_b),
                "ipl_hp_matches": m_ipl,
            }
        self.global_prior_ = float(prof_df["mu_hp_12b"].median()) if not prof_df.empty else 0.0
        self.fit_meta_ = {
            "cutoff_label": self.cutoff_label,
            "n_cells": int(len(df_pos)),
            "n_short_hp_cells_lt6": int(((df_pos["is_high_pressure"] == True) & (df_pos["legal_balls"] < 6)).sum()),
            "sig_cal_ge6": float(self.sig_cal_ge6_),
            "sig_cal_all_pos": float(self.sig_cal_all_),
        }
        return self

    def predict_quantile(self, pids: Iterable[int], use_all_pos_cal: bool = False) -> np.ndarray:
        t_crit = float(student_t.ppf(0.75, df=self.df))
        out = []
        for pid in pids:
            prof = self.player_profiles_.get(int(pid))
            if prof is not None:
                if use_all_pos_cal:
                    out.append(prof["predicted_hp_12b"] - t_crit * self.sig_cal_all_)
                else:
                    out.append(prof["q25_12b"])
            else:
                out.append(self.global_prior_ - t_crit * (self.sig_cal_all_ if use_all_pos_cal else self.sig_cal_ge6_))
        return np.array(out, dtype=float)

    def predict_mean(self, pids: Iterable[int]) -> np.ndarray:
        return np.array(
            [self.player_profiles_[int(p)]["predicted_hp_12b"] if int(p) in self.player_profiles_ else self.global_prior_ for p in pids],
            dtype=float,
        )
