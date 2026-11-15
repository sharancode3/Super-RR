"""Stage 03 Principal Challenger: Role-and-Phase Regularized Partial-Pooling Model (RPP).

Jointly fits ordinary and high-pressure observations (including <6b short pressure stints)
using weighted Ridge partial pooling by tactical role and phase:

    impact_12 = role_phase_level + player_ordinary_effect
              + pressure * (role_phase_pressure_effect + player_pressure_effect)
              + context_terms + error

All role priors, competition-transfer weights, recency decay, scenario weights,
and Student-t Q25 uncertainty calibration are learned strictly prior to the forecast cutoff.
"""

from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.stats import t as student_t


VALID_ROLES = (
    "WK_BATTER",
    "TOP_ORDER_BATTER",
    "MIDDLE_ORDER_BATTER",
    "FINISHER_BATTER",
    "SPIN_ALLROUNDER",
    "PACE_ALLROUNDER",
    "PACE_BOWLER",
    "SPIN_BOWLER",
)
PHASES = ("POWERPLAY", "MIDDLE", "DEATH")


def infer_role_family(inferred_role: Any, bowler_type: Any = "Unknown") -> str:
    """Map canonical player_dimension role into a compact tactical role family."""
    r = str(inferred_role) if pd.notna(inferred_role) else "Unknown"
    if r in VALID_ROLES:
        return r
    bt = str(bowler_type) if pd.notna(bowler_type) else "Unknown"
    if bt == "Spin":
        return "SPIN_BOWLER"
    if bt == "Pace":
        return "PACE_BOWLER"
    return "OTHER"


def build_phase_observations_from_ledger(
    deliv_df: pd.DataFrame,
    discipline: str,
    max_date: Optional[str] = None,
) -> pd.DataFrame:
    """Aggregate reliability-eligible deliveries by player, match, phase, innings, and pressure state.

    Includes ordinary balls, short (<6b) pressure stints, and extras-only (0-legal-ball) cells.
    """
    mask = pd.Series(True, index=deliv_df.index)
    if "is_reliability_eligible" in deliv_df.columns:
        mask &= deliv_df["is_reliability_eligible"].astype(bool)
    elif "is_cohort_eligible" in deliv_df.columns:
        mask &= deliv_df["is_cohort_eligible"].astype(bool)
    if max_date is not None and "match_date" in deliv_df.columns:
        mask &= deliv_df["match_date"].astype(str) <= str(max_date)

    sub = deliv_df.loc[mask].copy()
    if sub.empty:
        return pd.DataFrame()
    if "season" not in sub.columns:
        sub["season"] = sub["match_date"].astype(str).str[:4].astype(int)
    else:
        sub["season"] = pd.to_numeric(sub["match_date"].astype(str).str[:4], errors="coerce").fillna(2024).astype(int)

    pcol = "striker_id" if discipline == "batting" else "bowler_id"
    icol = "batting_impact" if discipline == "batting" else "bowling_impact"
    rcol = "runs" if discipline == "batting" else "bowler_charge_runs"
    wcol = "is_striker_dismissed" if discipline == "batting" else "is_bowler_wicket"
    hp_col = "is_high_pressure_20" if "is_high_pressure_20" in sub.columns else "is_high_pressure"
    fold_col = "fold" if "fold" in sub.columns else None

    grp_cols = ["match_id", pcol, "match_phase", "innings", hp_col, "comp_tier", "match_date", "season"]
    if fold_col:
        grp_cols.append(fold_col)

    obs = (
        sub.groupby(grp_cols, observed=False)
        .agg(
            raw_deliveries=("is_legal_ball", "count"),
            legal_balls=("is_legal_ball", "sum"),
            outcome_runs=(rcol, "sum"),
            outcome_wickets=(wcol, "sum"),
            total_impact=(icol, "sum"),
        )
        .reset_index()
        .rename(columns={pcol: "player_id", hp_col: "is_high_pressure"})
    )
    obs["impact_12b"] = np.where(obs["legal_balls"] > 0, (obs["total_impact"] / obs["legal_balls"]) * 12.0, np.nan)
    return obs


class ChallengerRPP_RolePhaseJoint:
    """Regularized Role-and-Phase Partial-Pooling Model over Ordinary + Pressure Exposure."""

    def __init__(
        self,
        lam_ord: float = 10.0,
        lam_hp: float = 30.0,
        half_life_seasons: float = 2.5,
        w_t20i: float = 0.15,
        w_emerging: float = 0.0375,
        df: int = 5,
        transfer_penalty_scale: float = 2.5,
        include_pressure_interaction: bool = True,
        cutoff_label: str = "UNSPECIFIED",
    ):
        self.lam_ord = lam_ord
        self.lam_hp = lam_hp
        self.half_life_seasons = half_life_seasons
        self.w_t20i = w_t20i
        self.w_emerging = w_emerging
        self.df = df
        self.transfer_penalty_scale = transfer_penalty_scale
        self.include_pressure_interaction = include_pressure_interaction
        self.cutoff_label = cutoff_label

        self.theta_: Optional[np.ndarray] = None
        self.H_inv_: Optional[np.ndarray] = None
        self.pid_to_idx_: Dict[int, int] = {}
        self.rp_to_idx_: Dict[Tuple[str, str], int] = {}
        self.ph_to_idx_: Dict[str, int] = {ph: i for i, ph in enumerate(PHASES)}
        self.offsets_: Dict[str, int] = {}
        self.n_cols_: int = 0
        self.global_prior_: float = 0.0
        self.sig_cal_ge6_: float = 6.5
        self.sig_noise_comp_: float = 4.0
        self.sig_floor_comp_: float = 4.5
        self.role_sig_: Dict[str, float] = {}
        self.role_phase_weights_: Dict[str, Dict[Tuple[str, int], float]] = {}
        self.global_ipl_phase_weights_: Dict[Tuple[str, int], float] = {("DEATH", 2): 0.4, ("MIDDLE", 1): 0.3, ("POWERPLAY", 1): 0.3}
        self.player_profiles_: Dict[int, Dict[str, Any]] = {}
        self.player_phase_weights_: Dict[int, Dict[Tuple[str, int], float]] = {}
        self.fit_meta_: Dict[str, Any] = {}

    def _fit_ridge_core(
        self,
        df_fit: pd.DataFrame,
        role_fam_map: Dict[int, str],
        match_weights: Optional[Dict[int, float]] = None,
        compute_cov: bool = True,
    ) -> Tuple[np.ndarray, Optional[np.ndarray], Any, Dict[int, int]]:
        work = df_fit[df_fit["legal_balls"] > 0].copy()
        work["role_fam"] = work["player_id"].map(role_fam_map).fillna("OTHER")
        if match_weights is not None:
            work["_m_mult"] = work["match_id"].map(match_weights).fillna(0.0)
            work = work[work["_m_mult"] > 0].copy()
        else:
            work["_m_mult"] = 1.0

        cutoff_yr = int(str(work["match_date"].max())[:4])
        seasons = pd.to_numeric(work["season"], errors="coerce").fillna(cutoff_yr).astype(float)
        comp_w = {
            "IPL": 1.0,
            "T20I": self.w_t20i,
            "INTERNATIONAL": self.w_t20i,
            "EMERGING": self.w_emerging,
        }
        w_comp = work["comp_tier"].map(comp_w).fillna(self.w_emerging).values
        w_rec = 0.5 ** (np.maximum(0.0, cutoff_yr - seasons.values) / self.half_life_seasons)
        w_exp = np.minimum(work["legal_balls"].astype(float).values, 36.0) / 12.0
        w_tr = w_comp * w_rec * w_exp * work["_m_mult"].values

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
        n_cols = off_p_hp + (len(pids) if self.include_pressure_interaction else 0)

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
                np.full(n, off_hp, dtype=int),
            ]
            vals = [
                np.ones(n),
                (df_in["innings"].values == 2).astype(float),
                nipl,
                np.ones(n),
                np.ones(n),
                hp,
            ]
            mask_hp = hp > 0
            if np.any(mask_hp):
                rows_i.append(r_idx[mask_hp])
                cols_j.append(off_rp_hp + rp_arr[mask_hp])
                vals.append(hp[mask_hp])

            p_mapped = df_in["player_id"].map(pid_to_idx)
            known = p_mapped.notna().values
            if np.any(known):
                rows_i.append(r_idx[known])
                cols_j.append(off_p_ord + p_mapped[known].astype(int).values)
                vals.append(np.ones(np.sum(known)))
                if self.include_pressure_interaction:
                    k_hp = known & mask_hp
                    if np.any(k_hp):
                        rows_i.append(r_idx[k_hp])
                        cols_j.append(off_p_hp + p_mapped[k_hp].astype(int).values)
                        vals.append(hp[k_hp])

            return sparse.csr_matrix(
                (np.concatenate(vals), (np.concatenate(rows_i), np.concatenate(cols_j))),
                shape=(n, n_cols),
            )

        X_tr = build_X(work)
        pen = np.zeros(n_cols)
        pen[0] = 1e-4
        pen[1] = 8.0
        pen[2] = 12.0
        pen[off_ph:off_rp_ord] = 4.0
        pen[off_rp_ord:off_hp] = 6.0
        pen[off_hp] = 4.0
        pen[off_rp_hp:off_p_ord] = 8.0
        pen[off_p_ord:off_p_hp] = self.lam_ord
        if self.include_pressure_interaction:
            pen[off_p_hp:] = self.lam_hp

        WX = X_tr.multiply(w_tr[:, None])
        H = (X_tr.T @ WX).toarray()
        H[np.diag_indices_from(H)] += pen
        theta = np.linalg.solve(H, X_tr.T @ (w_tr * work["impact_12b"].values))
        H_inv = np.linalg.inv(H) if compute_cov else None
        return theta, H_inv, build_X, pid_to_idx

    @staticmethod
    def _compute_phase_weights(df_sub: pd.DataFrame) -> Tuple[Dict[Tuple[str, int], float], Dict[str, Dict[Tuple[str, int], float]], Dict[int, Dict[Tuple[str, int], float]]]:
        ipl_all = df_sub[df_sub["comp_tier"] == "IPL"]
        fallback_glob = {("DEATH", 2): 0.4, ("MIDDLE", 1): 0.3, ("POWERPLAY", 1): 0.3}
        if ipl_all.empty:
            return fallback_glob, {}, {}
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
        return glob_w, role_w, player_w

    @staticmethod
    def _build_scenario_frame(
        pids: Iterable[int],
        role_fam_map: Dict[int, str],
        glob_w: Dict[Tuple[str, int], float],
        role_w: Dict[str, Dict[Tuple[str, int], float]],
        player_w: Dict[int, Dict[Tuple[str, int], float]],
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
            for (ph, inn), w_val in mix.items():
                if w_val > 0:
                    sc_rows.append({
                        "player_id": int(pid),
                        "role_fam": rf,
                        "match_phase": ph,
                        "innings": int(inn),
                        "sc_wt": float(w_val / tot_w),
                        "comp_tier": "IPL",
                    })
        return pd.DataFrame(sc_rows)

    def fit(
        self,
        obs_df: pd.DataFrame,
        p_dim: pd.DataFrame,
        discipline: str,
        match_weights: Optional[Dict[int, float]] = None,
        cal_override: Optional[Tuple[float, Dict[str, float]]] = None,
    ) -> "ChallengerRPP_RolePhaseJoint":
        """Fit joint ordinary + pressure partial-pooling model & calibrate Student-t Q25 scale on expanding chronological blocks."""
        if obs_df is None or obs_df.empty:
            return self
        df_pos = obs_df[obs_df["legal_balls"] > 0].copy()
        if match_weights is not None:
            mw = df_pos["match_id"].map(match_weights).fillna(0.0)
            df_pos = df_pos[mw > 0].copy()
        if df_pos.empty:
            return self

        p_map = p_dim.set_index("player_id")
        all_pids = set(df_pos["player_id"].astype(int)) | set(int(x) for x in p_map.index)
        role_fam_map = {
            pid: infer_role_family(p_map.loc[pid, "inferred_role"], p_map.loc[pid].get("bowler_type", "Unknown"))
            if pid in p_map.index
            else "OTHER"
            for pid in all_pids
        }
        df_pos["role_fam"] = df_pos["player_id"].map(role_fam_map).fillna("OTHER")

        t_crit = float(student_t.ppf(0.75, df=self.df))
        if cal_override is not None:
            self.sig_cal_ge6_, self.role_sig_ = float(cal_override[0]), dict(cal_override[1])
        else:
            # 1. Strictly chronological expanding-window OOF residual calibration (zero future match leakage)
            m_dates = df_pos[["match_id", "match_date"]].drop_duplicates().sort_values(["match_date", "match_id"])
            ordered_mids = m_dates["match_id"].tolist()
            n_m = len(ordered_mids)
            oof_rows = []
            if n_m >= 6:
                warmup_n = max(3, int(round(0.35 * n_m)))
                rem_mids = ordered_mids[warmup_n:]
                n_blocks = min(4, max(1, len(rem_mids)))
                chunks = np.array_split(np.array(rem_mids, dtype=int), n_blocks)
                prior_mids = set(int(x) for x in ordered_mids[:warmup_n])
                for ch in chunks:
                    val_mids = set(int(x) for x in ch.tolist())
                    if not val_mids:
                        continue
                    tr_k = df_pos[df_pos["match_id"].isin(prior_mids)]
                    va_k = df_pos[
                        df_pos["match_id"].isin(val_mids)
                        & (df_pos["comp_tier"] == "IPL")
                        & (df_pos["is_high_pressure"] == True)
                    ].copy()
                    if not tr_k.empty and not va_k.empty:
                        th_k, _, bx_k, _ = self._fit_ridge_core(tr_k, role_fam_map, match_weights=match_weights, compute_cov=False)
                        gw_k, rw_k, pw_k = self._compute_phase_weights(tr_k)
                        m_k = va_k.groupby(["match_id", "player_id"], as_index=False).agg(
                            b=("legal_balls", "sum"),
                            imp=("total_impact", "sum"),
                            role_fam=("role_fam", "first"),
                        )
                        sc_k = self._build_scenario_frame(m_k["player_id"].unique(), role_fam_map, gw_k, rw_k, pw_k)
                        if not sc_k.empty:
                            sc_k["mu_hp"] = (bx_k(sc_k, force_hp=1.0, force_non_ipl=0.0) @ th_k) * sc_k["sc_wt"]
                            mu_map = sc_k.groupby("player_id")["mu_hp"].sum().to_dict()
                            m_k["mu"] = m_k["player_id"].astype(int).map(mu_map).fillna(float(th_k[0]))
                            m_k["y"] = 12.0 * m_k["imp"] / m_k["b"]
                            m_k["err"] = m_k["y"] - m_k["mu"]
                            oof_rows.append(m_k)
                    prior_mids.update(val_mids)

            if oof_rows:
                oof_df = pd.concat(oof_rows, ignore_index=True)
                oof_ge6 = oof_df[oof_df["b"] >= 6]
                ref_oof = oof_ge6 if len(oof_ge6) >= 30 else oof_df
                q25_neg = max(2.5, -float(np.quantile(ref_oof["err"].values, 0.25)))
                sig_total_oof = max(3.5, q25_neg / t_crit)
                self.sig_cal_ge6_ = sig_total_oof
                self.role_sig_ = {}
                for r, grp in ref_oof.groupby("role_fam"):
                    if len(grp) >= 25:
                        r_sig = max(3.5, -float(np.quantile(grp["err"].values, 0.25)) / t_crit)
                        self.role_sig_[r] = float(0.5 * sig_total_oof + 0.5 * r_sig)
                    else:
                        self.role_sig_[r] = float(sig_total_oof)
            else:
                self.sig_cal_ge6_ = 6.5
                self.role_sig_ = {}

        # 2. Full pre-cutoff Ridge fit
        theta, H_inv, build_X, pid_to_idx = self._fit_ridge_core(df_pos, role_fam_map, match_weights=match_weights)
        self.theta_ = theta
        self.H_inv_ = H_inv
        self._build_X_fn_ = build_X
        self.pid_to_idx_ = pid_to_idx
        self.global_prior_ = float(theta[0])

        # Subtract average parameter variance seen on OOF (~10-15%) so adding exact per-player var_param doesn't double-count
        ipl_hp_rows = df_pos[(df_pos["comp_tier"] == "IPL") & (df_pos["is_high_pressure"] == True)].copy()
        if not ipl_hp_rows.empty:
            Xa_ref = build_X(ipl_hp_rows, force_hp=1.0, force_non_ipl=0.0).toarray()
            mean_diag_var = float(np.mean(np.sum((Xa_ref @ H_inv) * Xa_ref, axis=1) * (self.sig_cal_ge6_ ** 2)))
        else:
            mean_diag_var = 0.0
        base_resid_var = max(12.25, self.sig_cal_ge6_**2 - mean_diag_var)
        self.sig_floor_comp_ = float(np.sqrt(0.55 * base_resid_var))
        self.sig_noise_comp_ = float(np.sqrt(0.45 * base_resid_var))

        # 3. Pre-cutoff IPL role & player phase/innings distributions (target deployment domain)
        self.global_ipl_phase_weights_, self.role_phase_weights_, self.player_phase_weights_ = self._compute_phase_weights(df_pos)

        # 4. Pre-cutoff player evidence & repeatability profiles + scenario predictions
        cutoff_yr = int(str(df_pos["match_date"].max())[:4])
        recent_years = {cutoff_yr, cutoff_yr - 1}
        hp_only = df_pos[df_pos["is_high_pressure"] == True]
        ord_only = df_pos[df_pos["is_high_pressure"] == False]
        ipl_hp = hp_only[hp_only["comp_tier"] == "IPL"]
        ipl_ord = ord_only[ord_only["comp_tier"] == "IPL"]

        hp_tot_b = hp_only.groupby("player_id")["legal_balls"].sum().to_dict()
        hp_ipl_b = ipl_hp.groupby("player_id")["legal_balls"].sum().to_dict()
        hp_ipl_m = ipl_hp.groupby("player_id")["match_id"].nunique().to_dict()
        hp_ipl_rec_b = ipl_hp[ipl_hp["season"].isin(recent_years)].groupby("player_id")["legal_balls"].sum().to_dict()
        ord_ipl_b = ipl_ord.groupby("player_id")["legal_balls"].sum().to_dict()

        # Match-level IPL HP repeatability (leave-best-match-out)
        ipl_match_agg = (
            ipl_hp.groupby(["player_id", "match_id"], as_index=False)
            .agg(b=("legal_balls", "sum"), imp=("total_impact", "sum"))
        )
        lo_best_map: Dict[int, float] = {}
        match_sd_map: Dict[int, float] = {}
        for pid, grp in ipl_match_agg.groupby("player_id"):
            if len(grp) >= 2:
                best_i = grp["imp"].idxmax()
                rem = grp.drop(best_i)
                if rem["b"].sum() > 0:
                    lo_best_map[int(pid)] = float(12.0 * rem["imp"].sum() / rem["b"].sum())
                match_sd_map[int(pid)] = float(np.std(12.0 * grp["imp"] / np.maximum(1, grp["b"]), ddof=1))

        # Vectorized scenario scoring across all players in all_pids using strictly pre-cutoff role/player mixes
        sc_df = self._build_scenario_frame(
            all_pids, role_fam_map, self.global_ipl_phase_weights_, self.role_phase_weights_, self.player_phase_weights_
        )
        X_ord = build_X(sc_df, force_hp=0.0, force_non_ipl=0.0).toarray()
        X_hp = build_X(sc_df, force_hp=1.0, force_non_ipl=0.0).toarray()
        sc_df["mu_ord"] = X_ord @ theta
        sc_df["mu_hp"] = X_hp @ theta
        sc_df["wt"] = sc_df["sc_wt"]

        # Aggregate player scenario design vector x_hp = sum wt * X_hp for coherent covariance
        pids_sorted = sc_df["player_id"].unique()
        self.player_profiles_ = {}
        t_80 = float(student_t.ppf(0.90, df=self.df))

        # Grouped fast vectorized dot products
        idx_groups = sc_df.groupby("player_id").indices
        for pid, idxs in idx_groups.items():
            wts = sc_df["wt"].values[idxs]
            mu_ord = float(np.sum(wts * sc_df["mu_ord"].values[idxs]))
            mu_hp = float(np.sum(wts * sc_df["mu_hp"].values[idxs]))
            x_bar_hp = np.sum(wts[:, None] * X_hp[idxs], axis=0)
            var_param = float((x_bar_hp @ H_inv @ x_bar_hp) * (self.sig_cal_ge6_ ** 2))

            rf = role_fam_map.get(int(pid), "OTHER")
            role_sig = self.role_sig_.get(rf, self.sig_cal_ge6_)
            scale_ratio = role_sig / max(1e-6, self.sig_cal_ge6_)
            floor_i = self.sig_floor_comp_ * scale_ratio
            noise_i = self.sig_noise_comp_ * scale_ratio

            tot_hp = float(hp_tot_b.get(int(pid), 0))
            ipl_hp_cnt = float(hp_ipl_b.get(int(pid), 0))
            ipl_share = ipl_hp_cnt / tot_hp if tot_hp > 0 else 0.0
            rec_hp_cnt = float(hp_ipl_rec_b.get(int(pid), 0))
            m_ipl = int(hp_ipl_m.get(int(pid), 0))

            pen_transfer = self.transfer_penalty_scale * (1.0 - ipl_share)
            pen_stale = 1.5 if (ipl_hp_cnt > 0 and rec_hp_cnt == 0) else (0.75 if (ipl_hp_cnt > 0 and m_ipl <= 1) else 0.0)
            sig_tot = float(np.sqrt(floor_i**2 + noise_i**2 + var_param + pen_transfer**2 + pen_stale**2))

            self.player_profiles_[int(pid)] = {
                "player_id": int(pid),
                "role_fam": rf,
                "usual_ipl_12b": mu_ord,
                "predicted_hp_12b": mu_hp,
                "pressure_delta_12b": mu_hp - mu_ord,
                "se_param": float(np.sqrt(max(0.0, var_param))),
                "sig_floor": float(floor_i),
                "sig_noise": float(noise_i),
                "transfer_penalty": float(pen_transfer),
                "stale_penalty": float(pen_stale),
                "predictive_sigma": sig_tot,
                "q25_12b": float(mu_hp - t_crit * sig_tot),
                "q10_12b": float(mu_hp - t_80 * sig_tot),
                "q90_12b": float(mu_hp + t_80 * sig_tot),
                "ipl_hp_balls": int(ipl_hp_cnt),
                "ipl_recent_2yr_hp_balls": int(rec_hp_cnt),
                "ipl_ord_balls": int(ord_ipl_b.get(int(pid), 0)),
                "ipl_hp_matches": m_ipl,
                "ipl_hp_share": float(ipl_share),
                "ipl_hp_excl_best_m_12b": lo_best_map.get(int(pid), np.nan),
                "ipl_hp_match_sd": match_sd_map.get(int(pid), np.nan),
            }

        self.fit_meta_ = {
            "discipline": discipline,
            "cutoff_label": self.cutoff_label,
            "calibration_mode": "expanding_chronological_ex_ante",
            "n_obs_cells": int(len(df_pos)),
            "n_short_hp_cells_lt6": int(((df_pos["is_high_pressure"] == True) & (df_pos["legal_balls"] < 6)).sum()),
            "n_ord_cells": int((df_pos["is_high_pressure"] == False).sum()),
            "n_players": int(len(pid_to_idx)),
            "sig_cal_oof_ge6": float(self.sig_cal_ge6_),
            "sig_floor_comp": float(self.sig_floor_comp_),
            "sig_noise_comp": float(self.sig_noise_comp_),
            "lam_ord": self.lam_ord,
            "lam_hp": self.lam_hp,
            "half_life_seasons": self.half_life_seasons,
            "w_t20i": self.w_t20i,
            "include_pressure_interaction": self.include_pressure_interaction,
        }
        return self

    def predict_opportunities(self, eval_obs: pd.DataFrame, p_dim: pd.DataFrame) -> pd.DataFrame:
        """Predict match-level IPL high-pressure mean and Q25 on exact evaluation opportunities (preserving <6b)."""
        if eval_obs is None or eval_obs.empty or self.theta_ is None:
            return pd.DataFrame()
        ev = eval_obs[eval_obs["legal_balls"] > 0].copy()
        p_map = p_dim.set_index("player_id")
        ev["role_fam"] = [
            infer_role_family(p_map.loc[int(pid), "inferred_role"], p_map.loc[int(pid)].get("bowler_type", "Unknown"))
            if int(pid) in p_map.index
            else "OTHER"
            for pid in ev["player_id"]
        ]
        X_ev = self._build_X_fn_(ev, force_hp=1.0, force_non_ipl=0.0)
        Xa = X_ev.toarray()
        ev["cell_mu"] = Xa @ self.theta_
        ev["wt_mu"] = ev["cell_mu"] * ev["legal_balls"]
        ev["cell_vp"] = np.sum((Xa @ self.H_inv_) * Xa, axis=1) * (self.sig_cal_ge6_ ** 2) * ev["legal_balls"]

        ev_m = ev.groupby(["match_id", "player_id"], as_index=False).agg(
            hp_balls=("legal_balls", "sum"),
            hp_impact=("total_impact", "sum"),
            wt_mu=("wt_mu", "sum"),
            wt_vp=("cell_vp", "sum"),
            role_fam=("role_fam", "first"),
        )
        ev_m["y_12b"] = 12.0 * ev_m["hp_impact"] / ev_m["hp_balls"]
        ev_m["pred_mean"] = ev_m["wt_mu"] / ev_m["hp_balls"]
        ev_m["var_param"] = ev_m["wt_vp"] / np.maximum(1, ev_m["hp_balls"])

        t_crit = float(student_t.ppf(0.75, df=self.df))
        q25_arr = np.zeros(len(ev_m), dtype=float)
        for i, row in enumerate(ev_m.itertuples(index=False)):
            pid = int(row.player_id)
            prof = self.player_profiles_.get(pid)
            if prof is not None:
                floor_i = prof["sig_floor"]
                noise_i = prof["sig_noise"]
                pen_t = prof["transfer_penalty"]
                pen_s = prof["stale_penalty"]
            else:
                role_sig = self.role_sig_.get(row.role_fam, self.sig_cal_ge6_)
                scale_ratio = role_sig / max(1e-6, self.sig_cal_ge6_)
                floor_i = self.sig_floor_comp_ * scale_ratio
                noise_i = self.sig_noise_comp_ * scale_ratio
                pen_t = self.transfer_penalty_scale
                pen_s = 0.0
            # Standardized 12b noise variance scales cleanly at known 12b benchmark (avoid peeking at match workload)
            sig = float(np.sqrt(floor_i**2 + noise_i**2 + row.var_param + pen_t**2 + pen_s**2))
            q25_arr[i] = float(row.pred_mean - t_crit * sig)
        ev_m["pred_q25"] = q25_arr
        return ev_m

    def predict_quantile(self, pids: Iterable[int], workloads: Optional[np.ndarray] = None, quantile: float = 0.25) -> np.ndarray:
        t_crit = float(student_t.ppf(1.0 - quantile, df=self.df))
        out = []
        fallback_sig = self.sig_cal_ge6_
        for pid in pids:
            prof = self.player_profiles_.get(int(pid))
            if prof is not None:
                if abs(quantile - 0.25) < 1e-6:
                    out.append(prof["q25_12b"])
                else:
                    out.append(prof["predicted_hp_12b"] - t_crit * prof["predictive_sigma"])
            else:
                out.append(self.global_prior_ - t_crit * np.sqrt(fallback_sig**2 + self.transfer_penalty_scale**2))
        return np.array(out, dtype=float)

    def predict_mean(self, pids: Iterable[int]) -> np.ndarray:
        return np.array(
            [self.player_profiles_[int(p)]["predicted_hp_12b"] if int(p) in self.player_profiles_ else self.global_prior_ for p in pids],
            dtype=float,
        )

    def predict_usual(self, pids: Iterable[int]) -> np.ndarray:
        return np.array(
            [self.player_profiles_[int(p)]["usual_ipl_12b"] if int(p) in self.player_profiles_ else self.global_prior_ for p in pids],
            dtype=float,
        )

    def predict_ci_80(self, pids: Iterable[int], workloads: Optional[np.ndarray] = None) -> Tuple[np.ndarray, np.ndarray]:
        t_80 = float(student_t.ppf(0.90, df=self.df))
        q10, q90 = [], []
        for pid in pids:
            prof = self.player_profiles_.get(int(pid))
            if prof is not None:
                q10.append(prof["q10_12b"])
                q90.append(prof["q90_12b"])
            else:
                sig = float(np.sqrt(self.sig_cal_ge6_**2 + self.transfer_penalty_scale**2))
                q10.append(self.global_prior_ - t_80 * sig)
                q90.append(self.global_prior_ + t_80 * sig)
        return np.array(q10, dtype=float), np.array(q90, dtype=float)
