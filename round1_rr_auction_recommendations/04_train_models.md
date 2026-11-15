# Stage 04 — Fit the model candidates

## Fit the controls first

Run Candidate B and Challenger D for batting, and B0, RPP and C-IPL for bowling. Keep the saved blend, prior positive-IPL policy, and IPL-only versus pooled data as named controls. If Stage 02 changes the target or pressure labels, refit the controls on the same corrected labels for a fair comparison. Reuse rr_pressure/forecast.py, challengers.py, role_challenger.py and delivery_challenger.py. Inspect their normal fit and scoring paths, including forecast defaults for thin or new players.

## Primary candidate

1. Fit an IPL-anchored, partially pooled role-and-phase model per discipline. Use player-match-phase records or delivery aggregates whose numerator and exposure match the target. Include role-by-phase, innings, supported prior opposition or matchup factors, a shrunk player ordinary effect and a smooth pressure response. Include the role-by-phase pressure effect and a shrunk player pressure interaction. Start with a small number of spline basis terms or predeclared pressure bins and a sparse penalized regression. An individual player-by-phase effect requires sufficient support and stronger pooling. A weak matchup cell falls back to a wider role group with more uncertainty.
2. Use all observed eligible legal opportunities. Give each fit a declared exposure and match contribution so a long innings or a heavily sampled series cannot dominate. Assess robust or capped weighting using the common target. Choose an IPL transfer treatment on earlier rolling IPL validation. Compare IPL-only, the current transfer weights and one lower non-IPL weight or hierarchical competition offset. Record domain counts, recency, opposition variation and weighted support. Include strictly prior ordinary observations and pressure observations in the fit so the model can learn the player's own baseline.
3. Score each player over the same declared IPL deployment for their intended role. Estimate ordinary mean, pressure mean, pressure-minus-usual difference, and the lower-quarter pressure forecast. Form a distribution over predeclared plausible contexts or matched residuals. A weighted mean of context quantiles needs its own calibration before use as a predictive quantile. Report role-conditioned impact and comparison to the role benchmark. Record exactly where the forecast relies on transferred or pooled evidence.

## Targeted comparators

4. For batting, test the existing DHP approach on the short-stint issue. Its run component estimates scoring from pre-ball state and its hazard component estimates striker dismissal. Respect early dismissal, no-ball rules, nonstriker dismissal, and censoring when the innings ends. If predicting cumulative impact over a simulated assignment, stop the simulation on the correct terminal state and validate against that quantity. If predicting impact per 12 legal balls conditional on actual exposure, keep that target distinct. Evaluate one-to-five-ball and longer outcomes. Report a diagnostic under a different estimand separately.
5. Run one small nonlinear comparator using the installed and tested tree implementation, starting with the existing quantile challenger. Use the same pre-cutoff features and forecast target. Fit lower-tail quantiles and mean with shallow trees, minimum leaf sizes and a small fixed grid. Handle unknown categories and enforce or repair ordered quantiles with calibration. Use grouped time folds for any player or role encoding. If a more complex model improves only a narrow or tiny sample, record the effect and retain the more reliable one.
6. Keep the experiment budget bounded. Start with the controls, the primary model with a small earlier-window grid, and at most one targeted additional trial per question. A convex blend is eligible only if fixed earlier, evaluated on common rows and calibrated as its own forecast. A previously tried model is an existing control. Log model, source inputs, target, feature set, weights, tuning dates, fit diagnostics, CPU time and memory. Fit once per immutable cutoff/feature/parameter key and reuse its output across RR policies.

## Loop

Fit a simple baseline, then add one block at a time. Measure differences for pressure, role/phase, transfer, recent form and any matchup features. Diagnose a loss by coverage, sample size, role or temporal slice. A feature or label failure sends work to Stage 02, a dated roster or role evidence issue to Stage 03. Retain the model family with the strongest repeatable evidence under the declared trial budget.

## Exit and redirect

Export comparable pre-cutoff predictions from each candidate with consistent outcome units, assumptions, phase exposures and reproducible fit settings. Continue to [Stage 05](05_backtest_and_confidence.md).
