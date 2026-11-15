# Stage 03 · Fit and calibrate the candidate models

Read the frozen protocol and Stage 02 feature specification. Keep the fit small enough to explain, reproduce, and compare in the current repo. Use the same target and evaluation opportunities across models.

## Controls and proposed challenger

- Reuse the selected batting **D** and bowling **B0** as the locked controls. Reuse **B1** as the simple ordinary level plus shrunk pressure-change model. Keep **C-IPL** as the bowling comparison for role/phase pooling and cross-tier uncertainty. Preserve the saved baseline metrics and replay each relevant control from the same cutoff and evaluation universe as the challenger. Clearly label a control that only models ordinary performance or that learns from pressure-only history.
- Implement one principal challenger using **regularized partial pooling of ordinary skill and pressure response by role and phase**. A practical fit is a weighted ridge model on the existing context-adjusted impact, with role/phase effects, player ordinary effects, and player-by-pressure interactions. Use the role or role-by-phase mean as the shrinkage prior when player support is thin. A useful specification is

  `impact_12 = role_phase_level + player_ordinary_effect + pressure × (role_phase_pressure_effect + player_pressure_effect) + context_terms + error`

  Use legal exposure for fitting weights on match-phase groups, with any weighting cap or recency decay declared in the protocol. Keep shrinkage stronger for the sparse player pressure terms than for the ordinary terms, unless earlier development supports a different choice. Fit separate batting and bowling parameters. Pool to broader role/phase estimates for new players and show the resulting uncertainty. Include a simple no-interaction ablation if needed to test whether the pressure term adds value.
- Use the existing residual target initially. If expected runs and wickets are reworked, evaluate the new target and the locked target on the same rows, record how meaning changes, and keep the principal comparison on a common target. A context change is a separate experiment from the candidate model. Established T20 work motivates context-adjusted runs, wicket cost, and shrinkage. It does not pick a winner for this pack. [Context-adjusted T20 evaluation preprint](https://arxiv.org/abs/2608.18020v2), [T20I pressure index](https://journals.sagepub.com/doi/full/10.3233/JSA-240792)

## Training and inference

1. Fit each candidate on history strictly before the forecast cutoff. Fit encoders, role priors, transfer offsets or tier weights, and uncertainty using only that history. Use earlier IPL evidence as the target domain. If learning a T20I-to-IPL adjustment, use dual-competition players at the same cutoff and shrink unstable adjustments. Give thin transferred profiles wider uncertainty. Use the same documented fallback when direct IPL evidence is missing.
2. Use a small, frozen search over regularization and any recency or transfer setting selected in Stage 01. Log runtime, fit counts, settings, and exclusions. Reuse earlier out-of-fold residuals to estimate predictive spread by role and workload, with fallback pooling. Estimate Q25 at the reference workload from a calibrated predictive distribution. Keep parameter uncertainty distinct from match-to-match variation where the data supports it. Use fixed or known-at-prediction workload inputs. Actual later workloads may describe evaluation groups.
3. For a candidate's intended IPL role, predict ordinary and pressured scenarios against common supported contexts. Aggregate means with the declared reference weights. If using a mixture of scenarios, estimate its Q25 from the combined predictive distribution. Export the scenario weights and both predicted levels. Report the pressure difference as an estimate under those contexts. Avoid extrapolating a pressure comparison when one side has little comparable support.
4. Use the same scoring functions for historical comparison, robustness, and final ranking. Keep one canonical implementation through the CLI. Record the fit cutoff and model ID with every prediction. Check predictions for empty or thin roles, finite values and ordered quantiles, and matching baseline/pressure units. Test that inserting a later match leaves earlier predictions and model settings intact. Verify whole-match resampling uses the same weights for impact and exposure.

## Loop and exit

Fit → inspect → correct → rerun on the same chronological protocol. Fix implementation issues as needed. Keep the search within the frozen budget. Reuse the previous comparisons when their dependencies match. Write candidate forecasts, calibration provenance, and a short fit summary with the exact model and settings in `review_progress.md`.

**Pass when** each model returns comparable predictions by cutoff, role, and pressure state and the challenger includes both ordinary and short pressure observations. A challenger may underperform. **Next → [Stage 04](04_replay_and_select.md).**
