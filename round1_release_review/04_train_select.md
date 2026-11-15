# I04 · Train, compare and select by role

Technical references for the fit and metrics. [T20 empirical Bayes simulator](https://www.sfu.ca/~tswartz/papers/t20sim.pdf) · [Context-adjusted T20 player evaluation](https://arxiv.org/abs/2608.18020v2) · [CatBoost regression objectives](https://catboost.ai/docs/en/concepts/loss-functions-regression)

**End goal** Select a production model independently for batting and bowling from leakage-free results, including a baseline if challengers offer weak evidence.

```text
Use the frozen F02 target and F03 interface. Publish the experiment protocol and feature definitions before model scores. Put all trials in a bounded experiment ledger. Reuse the existing implementation when it meets the same feature and target contract.

Loop: fit baselines -> fit bounded challengers -> independently score -> compare -> freeze.

1. Fit A as a phase/tier cricket benchmark on the same target and data as all candidates. Fit B0 with shrinkage toward a past-only role/league prior and no individual pressure effect. Fit B with a player pressure term shrunk toward role-average lift. Use effective support, accounting for repeated observations in the same match, and choose prior strengths on earlier folds. Preserve B0/B to test incremental value of individual pressure history. Keep C as a boosted peer-model sensitivity if it changes the impact target, or give it a documented feature-only implementation so the target stays common.
2. Fit D as a robust partially pooled location/scale model. Use a Student-t distribution for match rate if justified by residual tails. Estimate location from past player baseline and pressure observations with role priors. Estimate scale from past observed residuals, with a regularized floor and known historical/scenario support if available. Never inject realized workload. Estimate or predeclare degrees of freedom with training-only evidence. Compute Q25 from the fitted distribution.
3. Fit E with shallow regularized histogram gradient boosting under the Q25 objective, using only F02 predictors and a small train-only search of tree depth, minimum leaf support, shrinkage and iterations. Test separate chronological feature ablations for pressure history, era, opponent strength and tier when support permits. Keep CatBoost quantile or a more expressive hierarchical model as a bounded optional challenger if a specific residual pattern justifies it. Avoid direct player IDs in a categorical booster unless an explicit time-safe cold-start protocol passes. Persist actual settings, seeds, fitted objects or deterministic reconstruction details.
4. Run expanding whole-match folds with tuning and calibration confined to earlier windows. On identical forecast/label keys, report mean pinball loss, Q25 coverage with a match-block interval, group coverage, and cohort exclusions. For residual u = observed minus forecast, Q25 loss is max(0.25*u, -0.75*u). For a model with a fitted mean or extra quantiles, report those metrics only where available. Build the top ten from the training cutoff and independently measure later impact and assessment coverage for those exact IDs. Publish paired match-block confidence intervals against B0 and a transparent baseline. Retain weights and multiplicities in paired bootstrap.
5. Use a predeclared practical improvement and calibration/support gate. Prefer the simpler adequate family when a claimed gain is smaller than the threshold or uncertain. Freeze model ID, context, features, training cutoffs and tie-break rule per role. Compare the frozen decisions against 2026 only as retrospective evidence. Changes after inspecting revised 2026 scores require a recorded new experiment version and carry the same retrospective label. Never select model, threshold or names because the result looks good.

Gate: every candidate and calibration uses earlier rows, comparable key sets and target, independent metric checks pass, and each role has a traceable frozen decision or an explicit inconclusive status.

PASS -> round1_release_review/05_transfer_stability.md
FAIL -> repeat I04 for training and selection errors. Redirect shared-dispatch errors to round1_release_review/03_model_evidence_parity.md or temporal failures to round1_release_review/02_temporal_target.md.
BLOCKED -> STOP_PROVISIONAL with evaluated baselines and the limiting evidence. Resume at round1_release_review/04_train_select.md after a documented correction or new valid evidence.
```
