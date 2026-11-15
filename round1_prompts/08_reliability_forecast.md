# Stage 08 · Fit the reliability forecast

**Inputs** · Chronological match impact observations and standardized role workloads.

**Checkpoint records** · 04, 07.

**Outputs** · Role-specific player fits, prediction distributions, ordinary baselines, pressure lifts, uncertainty and opportunity diagnostics.

## Implementation prompt

```text
Train separate batting and bowling models. Fit a partially pooled player intercept for usual level and a partially pooled pressure effect, controlling for competition and role support. Use empirical Bayes with regularized variance components or an equivalent transparent mixed-effects estimate. Treat a match as a correlated unit. Let more opportunities reduce sampling error with a variance floor for match-to-match variability. Pool variation within roles by default. Estimate player-specific variability only when the sample supports it and it improves 2025 calibration.

Fit the simplest usable hierarchy first. One implementable specification uses player-match-pressure bands with outcome 12 times the impact sum divided by legal opportunities. Give ordinary level and pressure change separate group priors and fit both effects jointly. Use residual variance of the form match variance plus delivery variance divided by opportunity count. Fit variance and shrinkage strengths on earlier folds, with pooled role values when a role slice is sparse. If the full hierarchy is unstable, use exposure-weighted regularized player effects as the declared fallback and estimate predictive spread from earlier held-out match residuals. Document the exact estimator actually used.

Retain missing ordinary or pressure exposure as missing when fitting group priors. Count distinct matches by ID and use the actual eligible denominator. Use role profiles as of each fit cutoff. Keep the plain partially pooled pressure forecast and a fitted variant with no player-specific pressure effect. Train and validate both on matched opportunities. If the interaction has weak signal, retain measured descriptive pressure lift and allow the simpler fitted forecast to win. Record which statistics are descriptive and which were validated as predictions.

Choose representative role and phase weights from earlier IPL opportunities with shared support. Pool T20I information through competition adjustments and verify its transfer separately. Keep emerging-team evidence as a separate sensitivity tier. Use high-pressure and ordinary observations in comparable contexts to estimate lift, and mark weak overlap rather than inventing what a player would do in an unsupported phase. Define a role-supported workload normalized to 12 legal-ball equivalents for reporting. Treat it as a standardized impact rate, with the forecast conditional on opportunity. Use each observed match's exposure when calibrating predictive distributions, or a matched workload subset where available. Avoid evaluating a 12-ball forecast on one-ball outcomes as though the uncertainty were identical.

Export the estimated ordinary level, pressure lift, expected impact under pressure, Q25, prediction interval, evidence counts and support flags. The conservative score is Q25, the 25th percentile of future standardized match impact. A normal predictive approximation may use mean minus 0.67449 times predictive standard deviation after validating residuals and calibration. Keep parameter uncertainty separate from future performance spread. Use cluster resampling by match to quantify ranking instability. Apply a role prior for sparse players and make the watchlist status visible.

Fit an ablation with the player pressure effect removed and a second sensitivity with recency weights tested using 2025 only. Keep recency only if the improvement is consistent and coverage holds. Verify that adding a tiny hot streak does not cause an unsupported jump, that stable performance is distinguishable from isolated impact, and that the model handles new players and unsupported contexts explicitly.

PASS -> round1_prompts/09_model_comparison.md | Both roles have auditable match-level forecasts, uncertainty, and exposure.
FAIL -> round1_prompts/04_freeze_evaluation.md | Repair temporal leakage.
FAIL -> round1_prompts/07_player_impact.md | Repair impact residuals or denominators.
FAIL -> round1_prompts/08_reliability_forecast.md | Repair pooling, workload normalization, or forecast calibration.
BLOCKED -> round1_prompts/09_model_comparison.md | A simpler pooled forecast passes the audit. Flag unsupported players or role slices as provisional.
BLOCKED -> STOP_BLOCKED | No auditable forecast covers both roles. Resume at round1_prompts/08_reliability_forecast.md when the blocker is resolved.
```
