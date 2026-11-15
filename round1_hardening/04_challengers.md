# H04 · Train research-backed forecast challengers

**Read** · [Research and priorities](../ROUND1_HARDENING_AUDIT.md#research-and-modeling-priorities), [reliability specification](../round1_prompts/08_reliability_forecast.md).

**Inputs** · Corrected A/B0/B1/C benchmark, identical reference rows, frozen historical folds and evaluation gates.

**Deliver** · Workload-aware distributional challenger, direct quantile challenger, candidate comparison rows and fit diagnostics. Document any unavailable or rejected experiment.

## Implementation prompt

```text
Keep the repaired baseline, with empirical priors and consistent uncertainty, as the control. Hold the reference target, folds, role workload and opportunity definitions fixed. Record train rows, match counts, feature availability, seed and fit time for each candidate. Fit and compare on earlier rolling folds. Leave 2026 outside model and hyperparameter choice.

Challenger D is a robust partially pooled player model. Use y12 as the outcome and fit a Student-t predictive distribution or an independently calibrated residual distribution. Start with role and competition intercepts, shrunk player skill, phase and innings effects, and support-aware opposition/venue context. Add a shrunk player pressure slope as an ablation against the no-personal-slope variant. Use a workload-dependent spread with a match-level floor plus a delivery-noise term proportional to 1/n. Pool variance parameters when player support is sparse. If using Student-t, distinguish scale from standard deviation and use the inverse CDF for Q25. Fit shrinkage and spread using earlier matches or inner time folds. Check convergence, baseline recovery, cold starts and whether robust tails improve calibration. Generate role predictions standardized at the declared workload, and score conditional workload forecasts separately where appropriate.

Challenger E is direct quantile boosting at the player-match level. Use shallow CatBoost with its quantile objective when available locally, or histogram gradient boosting with quantile loss. Train on as-of features such as shrunk usual level, supported pressure history, opposition strength, era, role and phase. Exclude future match aggregates and raw player ID memorization from the first comparison. Use identical folds, small grids and chronological stopping. Fit a conditional mean separately if needed and keep interval and quantile crossings visible. Compare its Q25 coverage and paired pinball loss against D and B0. Record the effect of any calibration using earlier data only. Treat no-skill or sparse fits as measured results.

Only run optional candidates against a diagnosed gap. If one conditional spread is inadequate, try distributional boosting such as NGBoost. If calibration drifts, test a rolling residual correction or conformal interval as a separate earlier-data experiment and measure coverage under actual shift. If exact chase coverage and probability calibration justify a sequential challenger, fit a smoothed legal-ball transition distribution and evaluate V(s) = sum over outcomes of P(o|s) times V(next state). Test terminal states, probability mass, extras assumptions and short-run dependence. Compare the resulting pressure tags and rank quality to the repaired reference. Simulated outcomes are never training or assessment rows. A foundation model is an optional local player-match benchmark only after the direct quantile comparison. Document privacy, sample-size and compute constraints before using it.

Use matched prediction rows, Q25 loss, uncertainty, coverage, and top-ten observed results. Keep both families if each helps a distinct role. Stop expanding the search when further candidates lack a specific failure to address. Save all attempts, including negative results, and carry the measured candidate set forward.

PASS -> round1_hardening/05_transfer_stability.md | Available challengers were assessed on the frozen comparison with traceable fits.
FAIL -> round1_hardening/02_temporal_reference.md | A target, cutoff or feature leaks or differs across models.
FAIL -> round1_hardening/03_model_parity.md | A candidate's fit, prediction and ranking recipe diverge.
FAIL -> round1_hardening/04_challengers.md | Repair a reproducible challenger fitting, support or metric defect.
BLOCKED -> round1_hardening/05_transfer_stability.md | A challenger lacks data, dependency or fit support. Keep the coherent measured candidates and report the gap.
```
