"""Stage H04: Research-backed forecast challengers (Challenger D and Challenger E)."""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.stats import t as student_t
from sklearn.ensemble import HistGradientBoostingRegressor

from rr_pressure.config import PipelineConfig
from rr_pressure.impact import booster_usual_level, compute_cumulative_prematch_features
from rr_pressure.role_challenger import ChallengerRPP_RolePhaseJoint, build_phase_observations_from_ledger

# Student-t quantile for alpha=0.25 with df=5
T_25_DF5 = float(student_t.ppf(0.75, df=5))  # ~0.7267


class ChallengerD_WorkloadDistributional:
    """Robust Workload-Aware and Competition-Transfer Distributional Model with Student-t Quantiles.
    
    Models skill via Empirical Bayes hierarchical shrinkage with competition-transfer weighting
    (IPL=1.0, T20I=0.25, Emerging=0.10), transfer uncertainty widening for thin IPL experience,
    and variance via a workload-dependent floor + 1/n delivery noise term.
    """
    def __init__(self, df: int = 5, m_prior: float = 36.0, transfer_penalty_scale: float = 2.5,
                 include_short_stints: bool = False):
        self.df = df
        self.m_prior = m_prior
        self.transfer_penalty_scale = transfer_penalty_scale
        self.include_short_stints = include_short_stints
        self.role_priors: Dict[str, float] = {}
        self.global_prior: float = 0.0
        self.sigma_floor: float = 4.0
        self.sigma_noise: float = 5.5
        self.player_profiles: Dict[int, Dict[str, float]] = {}

    def fit(self, train_match_df: pd.DataFrame, p_dim: pd.DataFrame, discipline: str) -> "ChallengerD_WorkloadDistributional":
        balls_col = "hp_balls_faced" if discipline == "batting" else "hp_balls_bowled"
        impact_col = "hp_bat_impact" if discipline == "batting" else "hp_bowl_impact"
        rate_col = "hp_bat_impact_12b" if discipline == "batting" else "hp_bowl_impact_12b"
        
        if self.include_short_stints:
            observed = train_match_df[balls_col].gt(0) | train_match_df[impact_col].ne(0)
        else:
            observed = train_match_df[balls_col].ge(6)
        valid = train_match_df[observed].copy()
        if valid.empty:
            return self
            
        role_map = p_dim.set_index("player_id")["inferred_role"].to_dict()
        valid["inferred_role"] = valid["player_id"].map(role_map).fillna("Unknown")
        
        # Competition transfer weights
        comp_weights = {"IPL": 1.0, "T20I": 0.25, "INTERNATIONAL": 0.25, "EMERGING": 0.10}
        if "comp_tier" in valid.columns:
            valid["w_comp"] = valid["comp_tier"].map(comp_weights).fillna(0.20)
        else:
            valid["w_comp"] = 1.0
            
        valid["eff_balls"] = valid[balls_col] * valid["w_comp"]
        valid["eff_impact"] = valid[impact_col] * valid["w_comp"]
        
        # Calculate role-level priors prioritizing IPL context from substantial outings (>= 6b)
        ge6_subset = valid[valid[balls_col] >= 6]
        ipl_subset = ge6_subset[ge6_subset["comp_tier"].eq("IPL")] if "comp_tier" in valid else ge6_subset
        prior_ref = ipl_subset if len(ipl_subset) >= 50 else ge6_subset
        if prior_ref.empty:
            prior_ref = valid[valid[balls_col].gt(0)]
        if prior_ref.empty:
            return self
        self.role_priors = prior_ref.groupby("inferred_role")[rate_col].median().to_dict()
        self.global_prior = float(prior_ref[rate_col].median())
        
        # Estimate variance components: match-level floor and noise
        overall_std = float(prior_ref[rate_col].std())
        if np.isnan(overall_std) or overall_std < 2.0:
            overall_std = 7.0
        if discipline == "batting":
            self.sigma_floor = max(3.0, overall_std * 0.60)
            self.sigma_noise = max(3.5, overall_std * 0.80)
        else:
            self.sigma_floor = max(2.5, overall_std * 0.55)
            self.sigma_noise = max(3.0, overall_std * 0.75)
        
        # Player-level empirical Bayes estimates with effective sample size and parameter uncertainty
        ipl_balls_dict = {}
        ipl_last_date_dict = {}
        cutoff_year = 2026
        if "comp_tier" in valid.columns:
            ipl_valid = valid[valid["comp_tier"] == "IPL"]
            ipl_balls_dict = ipl_valid.groupby("player_id")[balls_col].sum().to_dict()
            if "match_date" in valid.columns:
                ipl_last_date_dict = ipl_valid.groupby("player_id")["match_date"].max().to_dict()
                cutoff_year = int(str(valid["match_date"].max())[:4])
            
        p_agg = valid.groupby("player_id").agg(
            n_opps=("match_id", "count"),
            tot_balls=(balls_col, "sum"),
            tot_impact=(impact_col, "sum"),
            eff_balls=("eff_balls", "sum"),
            eff_impact=("eff_impact", "sum"),
        )
        
        # Vectorized effective sample size computation to avoid repeated per-player table filtering
        valid["_eff_balls_sq"] = valid["eff_balls"] ** 2
        p_eff_aggs = valid.groupby("player_id").agg(
            sum_b=("eff_balls", "sum"),
            sum_b2=("_eff_balls_sq", "sum"),
        )
        sum_b_dict = p_eff_aggs["sum_b"].to_dict()
        sum_b2_dict = p_eff_aggs["sum_b2"].to_dict()
        
        m_prior_matches = max(1.0, self.m_prior / 12.0)
        
        for pid, r in p_agg.iterrows():
            role = role_map.get(pid, "Unknown")
            prior = self.role_priors.get(role, self.global_prior)
            
            eff_b = r["eff_balls"]
            eff_rate = (r["eff_impact"] / eff_b * 12.0) if eff_b > 0 else prior
            
            # Match ball weights and effective sample size from pre-aggregated lookups
            sum_b = sum_b_dict.get(pid, 0.0)
            sum_b2 = sum_b2_dict.get(pid, 1.0)
            n_eff = (sum_b ** 2) / max(1.0, sum_b2)
            
            # Shrinkage toward role prior using effective evidence
            shrunk_mean = (eff_b * eff_rate + self.m_prior * prior) / (eff_b + self.m_prior)
            
            # Parameter standard error incorporates degrees of freedom from n_eff
            se_param = self.sigma_noise / np.sqrt(n_eff + m_prior_matches)
            
            # Transfer uncertainty penalty for thin direct IPL experience
            direct_ipl_b = float(ipl_balls_dict.get(pid, 0.0))
            transfer_penalty = self.transfer_penalty_scale * max(0.0, 1.0 - direct_ipl_b / 24.0)
            
            # Recency and staleness penalty (e.g. Behrendorff last IPL bowling in 2023)
            last_ipl_d = ipl_last_date_dict.get(pid)
            if last_ipl_d is not None:
                last_ipl_y = int(str(last_ipl_d)[:4])
                years_inactive = max(0, cutoff_year - last_ipl_y - 1)
            else:
                years_inactive = 2 if direct_ipl_b == 0 else 0
            stale_penalty = 1.0 * years_inactive
            
            self.player_profiles[pid] = {
                "shrunk_mean": float(shrunk_mean),
                "tot_balls": float(r["tot_balls"]),
                "eff_balls": float(eff_b),
                "ipl_balls": direct_ipl_b,
                "direct_ipl_share": float(direct_ipl_b / max(1.0, r["tot_balls"])),
                "transferred_share": float((r["tot_balls"] - direct_ipl_b) / max(1.0, r["tot_balls"])),
                "last_ipl_date": str(last_ipl_d) if last_ipl_d else "NEVER_PLAYED_IPL",
                "is_stale_ipl": bool(years_inactive > 0),
                "n_opps": int(r["n_opps"]),
                "n_eff": float(n_eff),
                "se_param": float(se_param),
                "transfer_penalty": float(transfer_penalty),
                "stale_penalty": float(stale_penalty),
                "role": role,
            }
        return self

    def predict_quantile(self, pids: np.ndarray, workloads: np.ndarray, quantile: float = 0.25) -> np.ndarray:
        t_crit = float(student_t.ppf(1.0 - quantile, df=self.df))
        preds = np.zeros(len(pids), dtype=float)
        m_prior_matches = max(1.0, self.m_prior / 12.0)
        fallback_se = self.sigma_noise / np.sqrt(1.0 + m_prior_matches)
        
        for i, (pid, w) in enumerate(zip(pids, workloads)):
            prof = self.player_profiles.get(pid)
            if prof is not None:
                mean = prof["shrunk_mean"]
                se_i = prof.get("se_param", fallback_se)
                pen_i = prof.get("transfer_penalty", self.transfer_penalty_scale)
                stale_i = prof.get("stale_penalty", 0.0)
            else:
                mean = self.global_prior
                se_i = fallback_se
                pen_i = self.transfer_penalty_scale
                stale_i = 0.0
                
            eff_w = max(1.0, float(w) / 12.0)
            # Predictive standard deviation includes scenario variance, parameter uncertainty, transfer penalty, and stale evidence penalty
            sig_pred = np.sqrt(self.sigma_floor**2 + (self.sigma_noise**2 / eff_w) + se_i**2 + pen_i**2 + stale_i**2)
            preds[i] = mean - t_crit * sig_pred
            
        return preds

    def predict_mean(self, pids: np.ndarray) -> np.ndarray:
        preds = np.zeros(len(pids), dtype=float)
        for i, pid in enumerate(pids):
            prof = self.player_profiles.get(pid)
            preds[i] = prof["shrunk_mean"] if prof is not None else self.global_prior
        return preds

    def predict_ci_80(self, pids: np.ndarray, workloads: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        t_90 = float(student_t.ppf(0.90, df=self.df))
        q10 = np.zeros(len(pids), dtype=float)
        q90 = np.zeros(len(pids), dtype=float)
        m_prior_matches = max(1.0, self.m_prior / 12.0)
        fallback_se = self.sigma_noise / np.sqrt(1.0 + m_prior_matches)
        
        for i, (pid, w) in enumerate(zip(pids, workloads)):
            prof = self.player_profiles.get(pid)
            mean = prof["shrunk_mean"] if prof is not None else self.global_prior
            se_i = prof.get("se_param", fallback_se) if prof is not None else fallback_se
            pen_i = prof.get("transfer_penalty", self.transfer_penalty_scale) if prof is not None else self.transfer_penalty_scale
            stale_i = prof.get("stale_penalty", 0.0) if prof is not None else 0.0
            eff_w = max(1.0, float(w) / 12.0)
            sig_pred = np.sqrt(self.sigma_floor**2 + (self.sigma_noise**2 / eff_w) + se_i**2 + pen_i**2 + stale_i**2)
            q10[i] = mean - t_90 * sig_pred
            q90[i] = mean + t_90 * sig_pred
        return q10, q90


    def predict_player_forecast(self, p_stats: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Compute coherent player-level forecast from cutoff player features."""
        pids = p_stats["player_id"].values if "player_id" in p_stats.columns else p_stats.index.values
        workloads = np.full(len(pids), 12.0)
        q25 = self.predict_quantile(pids, workloads, quantile=0.25)
        mean = self.predict_mean(pids)
        q10, q90 = self.predict_ci_80(pids, workloads)
        return q25, mean, q10, q90


class ChallengerC_RolePhasePartialPooling:
    """Role- and Phase-Aware Empirical Bayes Partial Pooling Model.
    
    Estimates player impact under pressure by role and phase (Powerplay, Middle, Death),
    borrowing strength from comparable players in the same tactical role when the individual
    player-phase sample size is thin. Includes all high-pressure deliveries (including wides
    and no-balls) in numerator impact, learns empirical cross-competition transfer where overlap
    allows, and computes combined Student-t predictive mean, Q25, and 80% intervals across phases.
    """
    def __init__(
        self,
        m_phase_prior: float = 24.0,
        df: int = 5,
        transfer_penalty_scale: float = 2.5,
        ipl_anchored: bool = False,
    ):
        self.m_phase_prior = m_phase_prior
        self.df = df
        self.transfer_penalty_scale = transfer_penalty_scale
        self.ipl_anchored = ipl_anchored
        self.role_phase_priors: Dict[Tuple[str, str], float] = {}
        self.phase_global_priors: Dict[str, float] = {}
        self.global_prior: float = 0.0
        self.sigma_floor: float = 4.0
        self.sigma_noise: float = 5.5
        self.learned_transfer_offset: float = 0.0
        self.overlap_players_count: int = 0
        self.transfer_residual_sd: float = transfer_penalty_scale
        self.player_profiles: Dict[int, Dict[str, Any]] = {}

    def fit(
        self,
        hp_deliv_train: pd.DataFrame,
        p_dim: pd.DataFrame,
        discipline: str,
        match_weights: Dict[int, float] = None,
    ) -> "ChallengerC_RolePhasePartialPooling":
        impact_col = "hp_bat_impact" if discipline == "batting" else "hp_bowl_impact"
        if impact_col not in hp_deliv_train.columns:
            impact_col = "batting_impact" if discipline == "batting" else "bowling_impact"
        player_col = "striker_id" if discipline == "batting" else "bowler_id"

        role_map = p_dim.set_index("player_id")["inferred_role"].to_dict()
        # Preserve ALL deliveries (including wides & no-balls) in impact numerator; denominator uses legal balls
        if match_weights is not None and "match_id" in hp_deliv_train.columns:
            mw = hp_deliv_train["match_id"].map(match_weights).fillna(0.0)
            valid = hp_deliv_train[mw > 0].copy()
            valid["_m_mult"] = mw[mw > 0].values
        else:
            valid = hp_deliv_train.copy()
            valid["_m_mult"] = 1.0
        if valid.empty:
            return self
        valid["inferred_role"] = valid[player_col].map(role_map).fillna("Unknown")

        comp_weights = (
            {"IPL": 1.0, "T20I": 0.20, "INTERNATIONAL": 0.20, "EMERGING": 0.05}
            if self.ipl_anchored
            else {"IPL": 1.0, "T20I": 0.25, "INTERNATIONAL": 0.25, "EMERGING": 0.10}
        )
        if "comp_tier" in valid.columns:
            valid["w_comp"] = valid["comp_tier"].map(comp_weights).fillna(0.15 if self.ipl_anchored else 0.20) * valid["_m_mult"]
        else:
            valid["w_comp"] = 1.0 * valid["_m_mult"]
        legal_flag = valid["is_legal_ball"].astype(float) if "is_legal_ball" in valid.columns else 1.0
        valid["raw_legal"] = legal_flag * valid["_m_mult"]
        valid["raw_impact"] = valid[impact_col].fillna(0.0) * valid["_m_mult"]
        valid["eff_balls"] = legal_flag * valid["w_comp"]
        valid["eff_impact"] = valid[impact_col].fillna(0.0) * valid["w_comp"]

        # Learn shrunk cross-competition transfer offset & empirical residual spread from dual-tier overlap
        self.learned_transfer_offset = 0.0
        self.overlap_players_count = 0
        self.transfer_residual_sd = self.transfer_penalty_scale
        if "comp_tier" in valid.columns:
            ipl_rows = valid[valid["comp_tier"] == "IPL"].groupby(player_col).agg(
                b_ipl=("raw_legal", "sum"), imp_ipl=("raw_impact", "sum")
            )
            non_ipl_rows = valid[valid["comp_tier"] != "IPL"].groupby(player_col).agg(
                b_non=("raw_legal", "sum"), imp_non=("raw_impact", "sum")
            )
            both = ipl_rows.join(non_ipl_rows, how="inner")
            both = both[(both["b_ipl"] >= 12) & (both["b_non"] >= 12)]
            self.overlap_players_count = int(len(both))
            min_overlap_req = 1 if self.ipl_anchored else 15
            if self.overlap_players_count >= min_overlap_req:
                r_ipl = (both["imp_ipl"] / both["b_ipl"]) * 12.0
                r_non = (both["imp_non"] / both["b_non"]) * 12.0
                wt = np.minimum(both["b_ipl"], both["b_non"]) / 12.0
                shrink_k = 18.0 if self.ipl_anchored else 24.0
                raw_offset = float(np.sum(wt * (r_ipl - r_non)) / max(1.0, np.sum(wt) + shrink_k))
                self.learned_transfer_offset = float(np.clip(raw_offset, -3.5, 3.5))
                if self.ipl_anchored:
                    diffs = (r_ipl - r_non) - self.learned_transfer_offset
                    emp_tau = float(np.sqrt(np.sum(wt * (diffs**2)) / max(1.0, np.sum(wt))))
                    # Inflate transfer uncertainty smoothly when dual-setting overlap is thin
                    self.transfer_residual_sd = float(
                        np.clip(max(self.transfer_penalty_scale, emp_tau * 0.45) * np.sqrt(1.0 + 10.0 / max(1, self.overlap_players_count)), 1.5, 8.0)
                    )
                non_mask = valid["comp_tier"] != "IPL"
                valid.loc[non_mask, "eff_impact"] += self.learned_transfer_offset * (valid.loc[non_mask, "eff_balls"] / 12.0)

        # Estimate empirical match-level spread (IPL-prioritized) respecting _m_mult multiplicity
        if "match_id" in valid.columns:
            valid["_single_legal"] = legal_flag
            valid["_single_imp"] = valid[impact_col].fillna(0.0)
            match_agg = valid.groupby([player_col, "match_id"]).agg(
                b=("_single_legal", "sum"),
                imp=("_single_imp", "sum"),
                m_mult=("_m_mult", "first"),
                tier=("comp_tier", "first") if "comp_tier" in valid.columns else ("_m_mult", lambda s: "IPL"),
            ).reset_index()
            m_valid = match_agg[match_agg["b"] >= 6].copy()
            m_valid["rate"] = (m_valid["imp"] / m_valid["b"]) * 12.0
            m_ipl = m_valid[m_valid["tier"] == "IPL"]
            ref = m_ipl if m_ipl["m_mult"].sum() >= 50 else m_valid
            w_ref = ref["m_mult"].to_numpy(dtype=float)
            x_ref = ref["rate"].to_numpy(dtype=float)
            w_tot = float(w_ref.sum())
            if w_tot > 1.0:
                w_mean = float(np.sum(w_ref * x_ref) / w_tot)
                overall_std = float(np.sqrt(np.sum(w_ref * ((x_ref - w_mean) ** 2)) / max(1.0, w_tot - 1.0)))
            else:
                overall_std = 7.0
        else:
            overall_std = 7.0
        if np.isnan(overall_std) or overall_std < 2.0:
            overall_std = 7.0
        if discipline == "batting":
            self.sigma_floor = max(3.0, overall_std * 0.60)
            self.sigma_noise = max(3.5, overall_std * 0.80)
        else:
            self.sigma_floor = max(2.5, overall_std * 0.55)
            self.sigma_noise = max(3.0, overall_std * 0.75)

        # Global and Role x Phase empirical-Bayes priors (anchored on IPL only when ipl_anchored=True)
        prior_src = valid[valid["comp_tier"] == "IPL"] if (self.ipl_anchored and "comp_tier" in valid.columns and (valid["comp_tier"] == "IPL").any()) else valid
        tot_eff_b = prior_src["eff_balls"].sum()
        self.global_prior = float(prior_src["eff_impact"].sum() / max(1.0, tot_eff_b) * 12.0)

        for ph, p_df in prior_src.groupby("match_phase", observed=False):
            eb = p_df["eff_balls"].sum()
            ph_rate = float(p_df["eff_impact"].sum() / max(1.0, eb) * 12.0) if eb > 0 else self.global_prior
            self.phase_global_priors[ph] = float((eb * ph_rate + 36.0 * self.global_prior) / (eb + 36.0)) if self.ipl_anchored else ph_rate

        for (r, ph), rp_df in prior_src.groupby(["inferred_role", "match_phase"], observed=False):
            eb = rp_df["eff_balls"].sum()
            ph_fb = self.phase_global_priors.get(ph, self.global_prior)
            rp_rate = float(rp_df["eff_impact"].sum() / max(1.0, eb) * 12.0) if eb > 0 else ph_fb
            self.role_phase_priors[(r, ph)] = float((eb * rp_rate + 24.0 * ph_fb) / (eb + 24.0))

        # Vectorized player-phase aggregates and metadata lookups
        p_rp_agg = valid.groupby([player_col, "match_phase"], observed=False).agg(
            eff_b=("eff_balls", "sum"),
            eff_imp=("eff_impact", "sum"),
        ).reset_index()
        p_rp_dict = {
            (int(r[player_col]), str(r["match_phase"])): (float(r["eff_b"]), float(r["eff_imp"]))
            for _, r in p_rp_agg.iterrows()
        }

        if "match_id" in valid.columns:
            n_opps_series = valid.groupby([player_col, "match_id"])["_m_mult"].first().groupby(level=0).sum().rename("n_opps")
        else:
            n_opps_series = valid.groupby(player_col)["_m_mult"].sum().rename("n_opps")
        p_meta_agg = valid.groupby(player_col).agg(
            tot_eff_b=("eff_balls", "sum"),
            tot_balls=("raw_legal", "sum"),
        ).join(n_opps_series)

        ipl_balls_dict: Dict[int, float] = {}
        ipl_last_date_dict: Dict[int, Any] = {}
        cutoff_year = 2026
        if "comp_tier" in valid.columns:
            ipl_valid = valid[valid["comp_tier"] == "IPL"]
            ipl_balls_dict = ipl_valid.groupby(player_col)["raw_legal"].sum().to_dict()
            if "match_date" in valid.columns and not valid["match_date"].isna().all():
                ipl_last_date_dict = ipl_valid.groupby(player_col)["match_date"].max().to_dict()
                cutoff_year = int(str(valid["match_date"].max())[:4])

        m_phase_matches = max(1.0, self.m_phase_prior / 12.0)
        for pid, mr in p_meta_agg.iterrows():
            pid_int = int(pid)
            role = role_map.get(pid_int, "Unknown")
            tot_eb = float(mr["tot_eff_b"])

            phase_estimates = {}
            phase_weights = {}
            phase_se = {}
            for ph in ["POWERPLAY", "MIDDLE", "DEATH"]:
                ph_prior = self.role_phase_priors.get((role, ph), self.phase_global_priors.get(ph, self.global_prior))
                b_ik, imp_ik = p_rp_dict.get((pid_int, ph), (0.0, 0.0))
                if b_ik > 0:
                    rate_ik = (imp_ik / b_ik) * 12.0
                    shrunk_ik = (b_ik * rate_ik + self.m_phase_prior * ph_prior) / (b_ik + self.m_phase_prior)
                    w_ik = b_ik / max(1.0, tot_eb)
                    se_ik = self.sigma_noise / np.sqrt((b_ik / 12.0) + m_phase_matches)
                else:
                    shrunk_ik = ph_prior
                    w_ik = 0.0
                    se_ik = self.sigma_noise / np.sqrt(m_phase_matches)
                phase_estimates[ph] = float(shrunk_ik)
                phase_weights[ph] = float(w_ik)
                phase_se[ph] = float(se_ik)

            w_sum = sum(phase_weights.values())
            if w_sum > 0:
                norm_w = {ph: phase_weights[ph] / w_sum for ph in ["POWERPLAY", "MIDDLE", "DEATH"]}
                overall_mean = sum(phase_estimates[ph] * norm_w[ph] for ph in ["POWERPLAY", "MIDDLE", "DEATH"])
                se_comb = float(np.sqrt(sum((norm_w[ph] ** 2) * (phase_se[ph] ** 2) for ph in ["POWERPLAY", "MIDDLE", "DEATH"])))
            else:
                overall_mean = self.global_prior
                se_comb = self.sigma_noise / np.sqrt(1.0 + m_phase_matches)

            direct_ipl_b = float(ipl_balls_dict.get(pid_int, 0.0))
            non_ipl_share = float(max(0.0, mr["tot_balls"] - direct_ipl_b) / max(1.0, mr["tot_balls"]))
            if self.ipl_anchored:
                transfer_penalty = float(self.transfer_residual_sd * non_ipl_share)
            else:
                transfer_penalty = self.transfer_penalty_scale * max(0.0, 1.0 - direct_ipl_b / 24.0)
            last_ipl_d = ipl_last_date_dict.get(pid_int)
            if last_ipl_d is not None:
                last_ipl_y = int(str(last_ipl_d)[:4])
                years_inactive = max(0, cutoff_year - last_ipl_y - 1)
            else:
                years_inactive = 2 if direct_ipl_b == 0 else 0
            stale_penalty = 1.0 * years_inactive

            self.player_profiles[pid_int] = {
                "shrunk_mean": float(overall_mean),
                "phase_estimates": phase_estimates,
                "phase_weights": phase_weights,
                "phase_se": phase_se,
                "tot_eff_b": float(tot_eb),
                "tot_balls": float(mr["tot_balls"]),
                "ipl_balls": direct_ipl_b,
                "direct_ipl_share": float(direct_ipl_b / max(1.0, mr["tot_balls"])),
                "transferred_share": float((mr["tot_balls"] - direct_ipl_b) / max(1.0, mr["tot_balls"])),
                "last_ipl_date": str(last_ipl_d) if last_ipl_d else "NEVER_PLAYED_IPL",
                "is_stale_ipl": bool(years_inactive > 0),
                "n_opps": int(mr["n_opps"]),
                "se_param": float(se_comb),
                "transfer_penalty": float(transfer_penalty),
                "stale_penalty": float(stale_penalty),
            }
        return self

    def _predictive_sd(self, pid: int, w: float, fallback_se: float) -> Tuple[float, float]:
        prof = self.player_profiles.get(pid)
        if prof is not None:
            mean = prof["shrunk_mean"]
            se_i = prof["se_param"]
            pen_i = prof["transfer_penalty"]
            stale_i = prof["stale_penalty"]
        else:
            mean = self.global_prior
            se_i = fallback_se
            pen_i = self.transfer_penalty_scale
            stale_i = 0.0
        eff_w = max(1.0, float(w) / 12.0)
        sig_pred = float(np.sqrt(self.sigma_floor**2 + (self.sigma_noise**2 / eff_w) + se_i**2 + pen_i**2 + stale_i**2))
        return mean, sig_pred

    def predict_quantile(self, pids: np.ndarray, workloads: np.ndarray, quantile: float = 0.25) -> np.ndarray:
        t_crit = float(student_t.ppf(1.0 - quantile, df=self.df))
        preds = np.zeros(len(pids), dtype=float)
        fallback_se = self.sigma_noise / np.sqrt(1.0 + (self.m_phase_prior / 12.0))
        for i, (pid, w) in enumerate(zip(pids, workloads)):
            mean, sig_pred = self._predictive_sd(int(pid), float(w), fallback_se)
            preds[i] = mean - t_crit * sig_pred
        return preds

    def predict_mean(self, pids: np.ndarray) -> np.ndarray:
        preds = np.zeros(len(pids), dtype=float)
        for i, pid in enumerate(pids):
            prof = self.player_profiles.get(int(pid))
            preds[i] = prof["shrunk_mean"] if prof is not None else self.global_prior
        return preds

    def predict_ci_80(self, pids: np.ndarray, workloads: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        t_90 = float(student_t.ppf(0.90, df=self.df))
        q10 = np.zeros(len(pids), dtype=float)
        q90 = np.zeros(len(pids), dtype=float)
        fallback_se = self.sigma_noise / np.sqrt(1.0 + (self.m_phase_prior / 12.0))
        for i, (pid, w) in enumerate(zip(pids, workloads)):
            mean, sig_pred = self._predictive_sd(int(pid), float(w), fallback_se)
            q10[i] = mean - t_90 * sig_pred
            q90[i] = mean + t_90 * sig_pred
        return q10, q90

    def predict_player_forecast(self, p_stats: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Compute coherent player-level forecast from cutoff player features."""
        pids = p_stats["player_id"].values if "player_id" in p_stats.columns else p_stats.index.values
        workloads = np.full(len(pids), 12.0)
        q25 = self.predict_quantile(pids, workloads, quantile=0.25)
        mean = self.predict_mean(pids)
        q10, q90 = self.predict_ci_80(pids, workloads)
        return q25, mean, q10, q90


class ChallengerC_IPLAnchoredRolePhase(ChallengerC_RolePhasePartialPooling):
    """Targeted IPL-Anchored Role-and-Phase Variant.

    Shrinks small player-phase samples strictly toward IPL role-and-phase priors,
    estimates shrunk T20I-to-IPL offset from dual-tier overlap players, and widens
    predictive uncertainty smoothly in proportion to non-IPL share and thin overlap.
    """
    def __init__(self, m_phase_prior: float = 24.0, df: int = 5, transfer_penalty_scale: float = 2.5):
        super().__init__(
            m_phase_prior=m_phase_prior,
            df=df,
            transfer_penalty_scale=transfer_penalty_scale,
            ipl_anchored=True,
        )


class ChallengerE_DirectQuantileBoosted:
    """Direct Quantile Boosting on Pre-Match Features with Coherent Mean and Prediction Interval."""
    def __init__(self, quantile: float = 0.25, seed: int = 2027):
        self.quantile = quantile
        self.seed = seed
        self.model_q25 = HistGradientBoostingRegressor(
            loss="quantile",
            quantile=quantile,
            max_depth=3,
            min_samples_leaf=20,
            max_iter=50,
            random_state=seed,
        )
        self.model_mean = HistGradientBoostingRegressor(
            loss="squared_error",
            max_depth=3,
            min_samples_leaf=20,
            max_iter=50,
            random_state=seed,
        )
        self.model_q10 = HistGradientBoostingRegressor(
            loss="quantile",
            quantile=0.10,
            max_depth=3,
            min_samples_leaf=20,
            max_iter=50,
            random_state=seed,
        )
        self.model_q90 = HistGradientBoostingRegressor(
            loss="quantile",
            quantile=0.90,
            max_depth=3,
            min_samples_leaf=20,
            max_iter=50,
            random_state=seed,
        )
        self.fitted = False
        self.fallback_q25 = 0.0
        self.fallback_mean = 0.0
        self.fallback_q10 = -5.0
        self.fallback_q90 = 5.0

    def _extract_features(self, df: pd.DataFrame, p_stats: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        # Use the same prior for historical training rows and cutoff snapshots.
        if {"ord_impact", "ord_balls"}.issubset(p_stats.columns):
            p_stats = p_stats.assign(usual_level=booster_usual_level(p_stats["ord_impact"], p_stats["ord_balls"]))
        if {"ord_impact", "ord_balls"}.issubset(df.columns):
            df = df.assign(usual_level=booster_usual_level(df["ord_impact"], df["ord_balls"]))
        cols_to_merge = [c for c in ["usual_level", "hp_balls"] if c not in df.columns]
        if cols_to_merge:
            m = df.merge(p_stats[["player_id"] + cols_to_merge], on="player_id", how="left", validate="many_to_one")
        else:
            m = df.copy()
        usual = m["usual_level"].fillna(0.0).values
        hp_balls = m["hp_balls"].fillna(0.0).values
        
        # Pre-match context only: IPL tier indicator (target competition for auction is IPL)
        ipl = (m["comp_tier"] == "IPL").astype(float).values if "comp_tier" in m.columns else np.ones(len(m))
        
        # Standardized reference workload = 12 legal balls (strictly pre-match knowable)
        workload = np.full(len(m), 12.0)
        
        X = np.column_stack([usual, hp_balls, ipl, workload])
        return X, m["player_id"].values

    def fit(self, train_match_df: pd.DataFrame, p_stats: pd.DataFrame, discipline: str) -> "ChallengerE_DirectQuantileBoosted":
        rate_col = "hp_bat_impact_12b" if discipline == "batting" else "hp_bowl_impact_12b"
        balls_col = "hp_balls_faced" if discipline == "batting" else "hp_balls_bowled"
        history_columns = (
            {"ord_balls_faced", "ord_bat_impact", "hp_bat_impact"} if discipline == "batting"
            else {"ord_balls_bowled", "ord_bowl_impact", "hp_bowl_impact"}
        )
        if {"match_date", "match_id", *history_columns}.issubset(train_match_df.columns):
            train_match_df = compute_cumulative_prematch_features(train_match_df, discipline)
        valid = train_match_df[train_match_df[balls_col] >= 6].copy()
        if len(valid) < 50:
            return self
            
        X_tr, _ = self._extract_features(valid, p_stats)
        y_tr = valid[rate_col].values
        self.fallback_q25 = float(np.percentile(y_tr, self.quantile * 100))
        self.fallback_mean = float(np.mean(y_tr))
        self.fallback_q10 = float(np.percentile(y_tr, 10.0))
        self.fallback_q90 = float(np.percentile(y_tr, 90.0))
        
        self.model_q25.fit(X_tr, y_tr)
        self.model_mean.fit(X_tr, y_tr)
        self.model_q10.fit(X_tr, y_tr)
        self.model_q90.fit(X_tr, y_tr)
        self.fitted = True
        return self

    def predict(self, df: pd.DataFrame, p_stats: pd.DataFrame) -> np.ndarray:
        if not self.fitted:
            return np.full(len(df), self.fallback_q25)
        X, _ = self._extract_features(df, p_stats)
        return self.model_q25.predict(X)

    def predict_mean(self, df: pd.DataFrame, p_stats: pd.DataFrame) -> np.ndarray:
        if not self.fitted:
            return np.full(len(df), self.fallback_mean)
        X, _ = self._extract_features(df, p_stats)
        return self.model_mean.predict(X)

    def predict_ci_80(self, df: pd.DataFrame, p_stats: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        if not self.fitted:
            return np.full(len(df), self.fallback_q10), np.full(len(df), self.fallback_q90)
        X, _ = self._extract_features(df, p_stats)
        q10 = self.model_q10.predict(X)
        q90 = self.model_q90.predict(X)
        q90 = np.maximum(q90, q10 + 0.1)
        return q10, q90

    def predict_player_forecast(self, p_stats: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Compute coherent player-level forecast from cutoff player features."""
        q25 = self.predict(p_stats, p_stats)
        mean = self.predict_mean(p_stats, p_stats)
        q10, q90 = self.predict_ci_80(p_stats, p_stats)
        return q25, mean, q10, q90

    def predict_at_cutoff(self, observations: pd.DataFrame, p_stats: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Score known competition and player using a single historical snapshot."""
        context = observations[["player_id", "comp_tier"]]
        return self.predict(context, p_stats), self.predict_mean(context, p_stats)


def score_with_selected_model(
    fit_df: pd.DataFrame,
    match_df: pd.DataFrame,
    p_dim: pd.DataFrame,
    discipline: str,
    chosen_model: str,
    deliv_hp_df: pd.DataFrame = None,
    seed: int = 2027,
    obs_df: pd.DataFrame = None,
    cal_override: Any = None,
    bat_cells_df: pd.DataFrame = None,
) -> pd.DataFrame:
    """Single canonical dispatcher scoring all candidates strictly under chosen_model.
    
    Eliminates silent fallback to Candidate B1: supports Challenger DHP, Challenger RPP,
    Challenger E, Challenger D, Challenger C, Ablation B-0, and Candidate B explicitly,
    and raises ValueError otherwise.
    """
    df = fit_df.copy()
    qual_mask = df["is_qualified"].astype(bool)
    qual_df = df[qual_mask].copy()
    qual_pids = qual_df["player_id"].values

    if "Challenger DHP" in chosen_model or "Delivery-Hazard" in chosen_model:
        if discipline != "batting":
            raise ValueError("Challenger DHP (Delivery-Hazard Role-Phase) is batting-only.")
        if bat_cells_df is None or bat_cells_df.empty:
            raise ValueError(
                "Challenger DHP (Delivery-Hazard Role-Phase) requires bat_cells_df; silent fallback is disabled."
            )
        from rr_pressure.delivery_challenger import ChallengerDHP_BattingDeliveryHazard

        model_dhp = ChallengerDHP_BattingDeliveryHazard().fit(bat_cells_df, p_dim)
        df.loc[qual_mask, "usual_level"] = [
            model_dhp.player_profiles_[int(p)]["usual_ipl_12b"] if int(p) in model_dhp.player_profiles_ else np.nan
            for p in qual_pids
        ]
        df.loc[qual_mask, "conservative_score_q25"] = model_dhp.predict_quantile(qual_pids)
        df.loc[qual_mask, "predicted_hp_impact"] = model_dhp.predict_mean(qual_pids)
        df.loc[qual_mask, "ci_lower_80"] = [
            model_dhp.player_profiles_[int(p)]["q10_12b"] if int(p) in model_dhp.player_profiles_ else np.nan
            for p in qual_pids
        ]
        df.loc[qual_mask, "ci_upper_80"] = [
            model_dhp.player_profiles_[int(p)]["q90_12b"] if int(p) in model_dhp.player_profiles_ else np.nan
            for p in qual_pids
        ]
        df.loc[qual_mask, "param_se"] = np.nan
        df["model_fit_matches"] = df["player_id"].map(
            {pid: prof["ipl_hp_matches"] for pid, prof in model_dhp.player_profiles_.items()}
        ).fillna(0).astype(int)
        df["model_fit_hp_balls"] = df["player_id"].map(
            {pid: prof["ipl_hp_balls"] for pid, prof in model_dhp.player_profiles_.items()}
        ).fillna(0).astype(int)
    elif "Challenger RPP" in chosen_model or "Role-Phase Regularized" in chosen_model:
        if obs_df is None or obs_df.empty:
            raise ValueError(
                "Challenger RPP (Role-Phase Regularized Partial-Pooling) requires obs_df (ordinary + HP observations); silent fallback is disabled."
            )
        mid_mult = None
        if "match_id" in match_df.columns and "player_id" in match_df.columns and not match_df.empty:
            mid_mult = match_df.groupby(["match_id", "player_id"]).size().groupby("match_id").first().to_dict()
        model_rpp = ChallengerRPP_RolePhaseJoint().fit(obs_df, p_dim, discipline, match_weights=mid_mult, cal_override=cal_override)
        workloads = np.full(len(qual_pids), 12.0)
        df.loc[qual_mask, "usual_level"] = model_rpp.predict_usual(qual_pids)
        df.loc[qual_mask, "conservative_score_q25"] = model_rpp.predict_quantile(qual_pids, workloads)
        df.loc[qual_mask, "predicted_hp_impact"] = model_rpp.predict_mean(qual_pids)
        q10, q90 = model_rpp.predict_ci_80(qual_pids, workloads)
        df.loc[qual_mask, "ci_lower_80"] = q10
        df.loc[qual_mask, "ci_upper_80"] = q90
        df.loc[qual_mask, "param_se"] = df.loc[qual_mask, "player_id"].map(
            {pid: prof["se_param"] for pid, prof in model_rpp.player_profiles_.items()}
        ).fillna(np.nan)
        df["model_fit_matches"] = df["player_id"].map(
            {pid: prof["ipl_hp_matches"] for pid, prof in model_rpp.player_profiles_.items()}
        ).fillna(0).astype(int)
        df["model_fit_hp_balls"] = df["player_id"].map(
            {pid: prof["ipl_hp_balls"] for pid, prof in model_rpp.player_profiles_.items()}
        ).fillna(0).astype(int)
    elif "Challenger E" in chosen_model:
        model_e = ChallengerE_DirectQuantileBoosted(seed=seed).fit(match_df, df, discipline)
        df.loc[qual_mask, "conservative_score_q25"] = model_e.predict(qual_df, df)
        df.loc[qual_mask, "predicted_hp_impact"] = model_e.predict_mean(qual_df, df)
        q10, q90 = model_e.predict_ci_80(qual_df, df)
        df.loc[qual_mask, "ci_lower_80"] = q10
        df.loc[qual_mask, "ci_upper_80"] = q90
        df.loc[qual_mask, "param_se"] = np.nan
    elif "Challenger D" in chosen_model:
        model_d = ChallengerD_WorkloadDistributional().fit(match_df, p_dim, discipline)
        workloads = np.full(len(qual_pids), 12.0)
        df.loc[qual_mask, "conservative_score_q25"] = model_d.predict_quantile(qual_pids, workloads)
        df.loc[qual_mask, "predicted_hp_impact"] = model_d.predict_mean(qual_pids)
        q10, q90 = model_d.predict_ci_80(qual_pids, workloads)
        df.loc[qual_mask, "ci_lower_80"] = q10
        df.loc[qual_mask, "ci_upper_80"] = q90
        df.loc[qual_mask, "param_se"] = np.nan
        df["model_fit_matches"] = df["player_id"].map(
            {pid: prof["n_opps"] for pid, prof in model_d.player_profiles.items()}
        ).fillna(0).astype(int)
        df["model_fit_hp_balls"] = df["player_id"].map(
            {pid: prof["tot_balls"] for pid, prof in model_d.player_profiles.items()}
        ).fillna(0).astype(int)
    elif "Challenger C-IPL" in chosen_model or "IPL-Anchored" in chosen_model:
        if deliv_hp_df is None:
            raise ValueError(
                "Challenger C-IPL (IPL-Anchored Role-and-Phase) requires deliv_hp_df; silent fallback is disabled."
            )
        mid_mult = None
        if "match_id" in match_df.columns and "player_id" in match_df.columns and not match_df.empty:
            mid_mult = match_df.groupby(["match_id", "player_id"]).size().groupby("match_id").first().to_dict()
        model_c_ipl = ChallengerC_IPLAnchoredRolePhase().fit(deliv_hp_df, p_dim, discipline, match_weights=mid_mult)
        workloads = np.full(len(qual_pids), 12.0)
        df.loc[qual_mask, "conservative_score_q25"] = model_c_ipl.predict_quantile(qual_pids, workloads)
        df.loc[qual_mask, "predicted_hp_impact"] = model_c_ipl.predict_mean(qual_pids)
        q10, q90 = model_c_ipl.predict_ci_80(qual_pids, workloads)
        df.loc[qual_mask, "ci_lower_80"] = q10
        df.loc[qual_mask, "ci_upper_80"] = q90
        df.loc[qual_mask, "param_se"] = df.loc[qual_mask, "player_id"].map(
            {pid: prof["se_param"] for pid, prof in model_c_ipl.player_profiles.items()}
        ).fillna(np.nan)
        df["model_fit_matches"] = df["player_id"].map(
            {pid: prof["n_opps"] for pid, prof in model_c_ipl.player_profiles.items()}
        ).fillna(0).astype(int)
        df["model_fit_hp_balls"] = df["player_id"].map(
            {pid: prof["tot_balls"] for pid, prof in model_c_ipl.player_profiles.items()}
        ).fillna(0).astype(int)
    elif "Challenger C" in chosen_model:
        if deliv_hp_df is None:
            raise ValueError(
                "Challenger C (Role-and-Phase Partial-Pooling) requires deliv_hp_df; silent fallback is disabled."
            )
        # Preserve match-level bootstrap multiplicity or LOMO exclusion identically from match_df
        mid_mult = None
        if "match_id" in match_df.columns and "player_id" in match_df.columns and not match_df.empty:
            mid_mult = match_df.groupby(["match_id", "player_id"]).size().groupby("match_id").first().to_dict()
        model_c = ChallengerC_RolePhasePartialPooling().fit(deliv_hp_df, p_dim, discipline, match_weights=mid_mult)
        workloads = np.full(len(qual_pids), 12.0)
        df.loc[qual_mask, "conservative_score_q25"] = model_c.predict_quantile(qual_pids, workloads)
        df.loc[qual_mask, "predicted_hp_impact"] = model_c.predict_mean(qual_pids)
        q10, q90 = model_c.predict_ci_80(qual_pids, workloads)
        df.loc[qual_mask, "ci_lower_80"] = q10
        df.loc[qual_mask, "ci_upper_80"] = q90
        df.loc[qual_mask, "param_se"] = df.loc[qual_mask, "player_id"].map(
            {pid: prof["se_param"] for pid, prof in model_c.player_profiles.items()}
        ).fillna(np.nan)
        df["model_fit_matches"] = df["player_id"].map(
            {pid: prof["n_opps"] for pid, prof in model_c.player_profiles.items()}
        ).fillna(0).astype(int)
        df["model_fit_hp_balls"] = df["player_id"].map(
            {pid: prof["tot_balls"] for pid, prof in model_c.player_profiles.items()}
        ).fillna(0).astype(int)
    elif "Ablation" in chosen_model or "B0" in chosen_model or "B-0" in chosen_model:
        df["conservative_score_q25"] = df["b0_q25"]
        df["predicted_hp_impact"] = df["b0_mean"]
        if "b0_ci_lower_80" in df.columns:
            df["ci_lower_80"] = df["b0_ci_lower_80"]
            df["ci_upper_80"] = df["b0_ci_upper_80"]
    elif "Candidate B" in chosen_model or "Statistical Default" in chosen_model:
        df["conservative_score_q25"] = df["b1_q25"]
        df["predicted_hp_impact"] = df["b1_mean"]
        if "b1_ci_lower_80" in df.columns:
            df["ci_lower_80"] = df["b1_ci_lower_80"]
            df["ci_upper_80"] = df["b1_ci_upper_80"]
    else:
        raise ValueError(f"Unsupported model selection string '{chosen_model}': silent fallback is disabled.")

    # Preserve B1 empirical Bayes lift explicitly and compute model-specific pressure change cleanly
    df["b1_historical_pressure_lift"] = df["pressure_lift"] if "pressure_lift" in df.columns else 0.0
    if "Ablation" in chosen_model or "B0" in chosen_model or "B-0" in chosen_model:
        df["modeled_pressure_lift"] = 0.0
        df["pressure_lift_estimator"] = "ZERO_BY_CONSTRUCTION_B0"
    elif "Candidate B" in chosen_model or "Statistical Default" in chosen_model:
        df["modeled_pressure_lift"] = df["b1_historical_pressure_lift"]
        df["pressure_lift_estimator"] = "B1_EMPIRICAL_BAYES"
    else:
        df["modeled_pressure_lift"] = df["predicted_hp_impact"] - df["usual_level"]
        df["pressure_lift_estimator"] = "MODEL_IMPLIED_MINUS_USUAL"

    df = df.sort_values(
        ["is_qualified", "conservative_score_q25", "predicted_hp_impact", "hp_matches", "player_id"],
        ascending=[False, False, False, False, True],
    ).reset_index(drop=True)
    df["performance_rank"] = np.nan
    df.loc[df["is_qualified"], "performance_rank"] = np.arange(1, int(df["is_qualified"].sum()) + 1)
    return df
