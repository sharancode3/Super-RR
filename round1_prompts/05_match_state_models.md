# Stage 05 · Train and calibrate match-state models

**Inputs** · Split manifest, pre-ball ledger, feature dictionary.

**Checkpoint records** · 02, 03, 04.

**Outputs** · Fold-wise probability predictions, calibration tables, first-innings projected-score model, model diagnostics.

## Implementation prompt

```text
Fit a constant benchmark and a regularized logistic benchmark for batting-side win, separately for first innings and chases. Start with a small feature set and nonlinear terms for balls, wickets and score. In verified chases add required runs and rate. In RR-only chases use the off-bat scoring gap with its provenance flag. Keep exact and proxy predictions in distinct runs. In the first innings use pre-ball score, balls, wickets and historical scoring expectations. Train a separate remaining-runs model for a scoring-resource fallback and wicket values. Use observed final innings score only to form training targets.

Fit the boosted challenger with the same information boundary. Start with shallow trees, CPU training, a small grid and early stopping on an earlier validation window. Set a fixed seed and a time budget. If CatBoost is unavailable, use the recorded histogram gradient boosting substitution with equivalent inputs. Exclude candidate names, current-ball outcome fields and final outcomes from the predictor matrix. Add venue or team-strength priors only from earlier matches with a pooled fallback for sparse venues or unfamiliar teams.

Weight each match equally within innings for win-model evaluation so long chases do not dominate. Measure Brier score, log loss and reliability by innings, phase, competition and predefined close-state subsets. Check chronological calibration, probability bounds and cricket monotonicity over supported states. At the same number of balls and wickets, needing more runs should rarely make a chase more likely to succeed. Handle verified terminal chase states directly. Record effect of calibration before and after it. For projected remaining runs, report MAE and residuals by phase and innings support.

Compute a float training prior from equally weighted matches and preserve its dtype in the baseline predictions. Regression-test that an integer outcome column does not turn a prior near 0.5 into zero and that the stored score reproduces independently. Generate metrics and gate status from the scored predictions. Keep fitted parameters, calibration objects, fit cutoff and scoring input fingerprint together. Use the resource or rule fallback where the measured win forecasts fail, even when the original prototype reported PASS.

For a match-weighted Brier score, average `(observed_win - predicted_probability)^2` within each match and then average across matches. Validate the probabilities used for leverage with reliability bins and counts. Fit any calibration on disjoint earlier matches or chronological out-of-fold predictions. Keep the outer assessment out of fitting, preprocessing, calibration and early stopping.

Require stable improvement over the constant and comparable cricket benchmarks plus credible calibration in the slices used for pressure. If first-innings win probabilities fail, route first innings through the scoring-resource model. If chase probabilities fail in a lane, use the rule-based chase label as a separately identified fallback. The earlier proxy pilot is context for this gate, with no promotion based on that pilot alone.

PASS -> round1_prompts/06_pressure_definition.md | Each innings and source lane has a validated pressure route.
FAIL -> round1_prompts/02_scoreboard_ledgers.md | Repair corrupted match states.
FAIL -> round1_prompts/04_freeze_evaluation.md | Repair leakage or a fold boundary.
FAIL -> round1_prompts/05_match_state_models.md | Repair the model or calibration defect within the frozen protocol.
BLOCKED -> round1_prompts/06_pressure_definition.md | A rule-based chase or first-innings resource fallback passes its checks. Record which segments use it.
BLOCKED -> STOP_BLOCKED | No credible state forecast or fallback exists. Record the evidence and resume at round1_prompts/02_scoreboard_ledgers.md if more state data becomes available.
```
