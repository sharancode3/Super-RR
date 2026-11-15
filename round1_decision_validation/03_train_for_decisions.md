# A03 · Train for prediction and shortlist decisions

**End goal** Select batting and bowling models that perform well on dated IPL evidence and produce defensible lists.

```text
Use the versioned A02 data, target and feature provenance. Before running comparisons, freeze expanding match-date folds, an earlier tuning/calibration window, common assessment keys, the IPL context, practical error and calibration limits, and a shortlist decision rule. Keep the already inspected 2026 period retrospective.

Loop: fit baseline -> train bounded challengers -> score identical rows -> replay selected lists -> freeze or revise within earlier folds.

1. Fit a simple phase/tier cricket baseline and B0/B1 shrinkage. B0 models usual ability and B1 adds a partially pooled pressure effect learned from comparable situations. For a distributional challenger, estimate role/league priors, robust location, player-estimation uncertainty and match variability with training-only data. Use Student-t if tails support it. Keep independent match evidence and weight concentration visible. Test whether an IPL-specific partial-pooling model learns better than one fixed domestic transfer.
2. Refit E with the A02 earlier-date features. Start with a shallow histogram quantile model and a small earlier-fold grid for depth, minimum leaf support, iterations and regularization. At Q25 minimize max(0.25*u, -0.75*u), where u is realized impact minus predicted quantile. Add a constrained CatBoost trial only for a specific residual pattern or meaningful categorical context. If publishing other quantiles, verify ordering and calibration. Use the same forecast fields and allowed context at validation, 2026 assessment, and release. Any candidate with no faithful dispatch remains diagnostic.
3. Compare pooled and IPL-target performance separately on exact paired keys, with cold-start cases and eligible coverage visible. Report Q25 loss and calibration, matched uncertainty by resampling whole matches, and slices by phase, role and support. Record the effective number of independent matches. Score actual historical top tens as they stood at the date of selection, against equally sized cricket and shrinkage benchmark lists. Compare on the same later fixture windows and standardized supported roles where possible. Show per-pick outcomes, ball-weighted and player-weighted summaries, unassessable picks, and the uncertainty of the difference. Missing exposure stays missing. The old E versus B list result is a reason to make this check, not a target to reproduce.
4. Select separately by role. Require adequate calibration, IPL support and list utility under the frozen rule. If a challenger improves row loss but harms shortlist performance beyond the predeclared tolerance, record the trade-off and use the justified baseline or mark the choice inconclusive. Freeze fitted IDs, cutoffs, scenario, candidate eligibility, and rank tie-break. Persist scored rows. Run 2026 once for this frozen version as retrospective evidence and keep the final full-history refit separate.

Gate: comparisons share keys and units, each family can reproduce its own output, list utility has matched evidence and counts, and the decision rule selects the result without favoring a named player or model.

PASS -> round1_decision_validation/04_stress_and_auction.md
FAIL -> repeat A03 for fit, scoring, calibration or selection. Send a temporal, cohort or label issue to round1_decision_validation/02_data_and_target.md.
BLOCKED -> STOP_PROVISIONAL with the best measured baseline and the missing evaluation evidence. Resume at round1_decision_validation/03_train_for_decisions.md.
```
