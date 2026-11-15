# R03 · Compare and select models by role

**End goal** Choose a reproducible batting and bowling model using calibrated, date-safe performance and actual shortlist utility.

```text
Use the frozen R01 and R02 target, folds and forecast interface. Work from the RR pack and key predictions to the same observations across models. Open round1_release_review/04_train_select.md for metric definitions and the original benchmark plan.

Loop: register experiment -> fit earlier windows -> score on common later rows -> compare uncertainty -> freeze.

1. Compare three core model families: cricket phase/tier benchmark plus B0/B1 shrinkage, robust support-aware distributional challenger D, and regularized quantile boosting E. Train each role separately. For E start with shallow histogram boosting using prior-only ability, pressure history, support and validated role, phase, tier, venue or opposition context. Any unknown scenario field gets a documented prior or is excluded before fitting. Bound depth, minimum leaf support, learning rate and iterations using earlier folds. Train the Q25 objective with loss max(0.25*u, -0.75*u) for u = actual impact minus predicted Q25. Add other quantiles only if their ordering and coverage can be verified. Preserve other candidates only if their target and dispatch pass R02. Add CatBoost or a hierarchical challenger only if a diagnosed residual pattern justifies the trial and earlier folds support it.
2. Use expanding date-block folds and a strictly earlier tuning/calibration window. Freeze exact assessment keys, the IPL focus, practical improvement threshold, coverage bounds and tie-break when models disagree. Report aggregate and separate IPL assessment rows, batting/bowling subroles, thin-support groups and new players. Report Q25 pinball loss, empirical coverage against 25%, predictive interval coverage if supported, and paired match-cluster uncertainty intervals for the actual candidate choices. Keep legitimate cold starts and identify any unscoreable rows before prediction joins.
3. Backtest the decision the contest needs. Rank players as of each cutoff and measure later pressure performance of those exact ten IDs against equally sized B0 and cricket baseline lists. Report pressure-ball weighted impact, per-player summaries, fit eligibility, assessable picks, and missing opportunities. Distinguish list utility from prediction loss on all players. Compare ordinary and pressure performance in like-for-like contexts and show which IPL deployment roles have sufficient support. Repeat evidence checks for sparse and established players without using individual ranks as a tuning objective.
4. Select independently by role using the frozen rule. If small gains or sparse support cannot separate two models, use the simpler adequate baseline or record that the evidence is inconclusive. Keep the already-inspected 2026 period retrospective. Export the decision, fitted metadata, exact assessed keys, commands and cutoffs before any full-history refit. Do not tune choices using 2026 outcomes or expected player names.

Gate: decisions and uncertainty are supported on earlier forward folds, predictions reflect the declared IPL context, shortlist metrics trace to the selected fit, and provisional cases have an explicit reason. B0 remains a valid winner when incremental pressure features lack demonstrated value, with pressure-versus-usual evidence reported separately.

PASS -> round1_rank_validation/04_rank_evidence.md
FAIL -> repeat R03 for evaluation, missing benchmarks or unsupported model selection. Send fit/dispatch failures to round1_rank_validation/02_fit_contract.md and chronology defects to round1_rank_validation/01_pressure_and_time.md.
BLOCKED -> STOP_PROVISIONAL with the measured baseline and missing evidence. Resume at round1_rank_validation/03_select_models.md.
```
