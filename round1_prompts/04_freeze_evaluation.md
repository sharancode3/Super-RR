# Stage 04 · Freeze folds, reference outcomes, and selection rules

**Inputs** · EDA, evidence grid, ledgers, current plan.

**Checkpoint records** · 02, 03.

**Outputs** · Dated split manifest, train/calibration/validation strategy, leakage tests, predeclared model selection criteria.

## Implementation prompt

```text
Assign whole matches by date. Keep same-date matches together unless reliable pre-match timestamps establish strict ordering. Use 2022 to 2024 for initial training, expanding earlier windows for out-of-time training features, and rolling 2025 validation for model choice. Prior runs have exposed 2026 player outcomes. Lock the repair protocol and choice using earlier data, then use 2026 as a previously inspected chronological assessment. An untouched future check requires newly available match data. Use the same assessment matches and eligible players for paired comparisons.

Within each outer fold, fit mappings derived from performance, role history, preprocessing, venue and competition priors, peer expectations, thresholds, models and probability calibration on earlier data. Reserve later training folds for calibration or use chronological out-of-fold predictions. Cache predictions with match ID, date, model, train-end date and feature snapshot. Keep every record whose provenance cannot pass the date assertions out of evaluation.

Test that permuting a holdout's outcome values leaves all earlier features and fitted artifacts unchanged. Test that the same match never appears in both sides of a fold, that same-day results cannot update other fixtures' pre-match features, and that changing a full-history aggregate cannot alter an as-of-date feature. Treat any failed leakage test as a hard gate.

Write row-level fit provenance for role features, probability calibration, pressure thresholds, peer estimates and the training residuals consumed by the player model. Each scored match must have a fit cutoff before its date. Require a minimum burn-in period, and document excluded early matches or the validated prior used for them. Add a complementary controlled check that a material change to an earlier training outcome changes a fitted estimate or prediction, while an unchanged rerun reproduces it. Never feed a test fixture into training.

Predeclare one common reference for the ranking comparison, learned entirely inside the training boundary. Use a fixed cricket-state reference for pressure opportunities and a smoothed runs-and-wickets reference for realized impact. Choose its exact or proxy lane without looking at candidate names. Freeze that reference for all candidate evaluations. Separately compare each candidate's own pressure labels, scores and coverage to see where the reference is restrictive. Use the same holdout workload and target for all three ranking models.

Freeze one statistical candidate cohort per role using historical evidence available at the assessment cutoff. Use observed future exposures to score forecasts and report the candidates and picks lost from each comparison. IPL is the primary transfer assessment. Compare IPL-only training and appropriately pooled IPL/T20I training on the same held-out IPL rows before crediting international results with better forecasts. Keep emerging-team evidence separate in the sensitivity analysis.

Write the candidate selection rule before scoring the repair's validation folds. Declare the primary forecast metric, minimum usable exposure, calibration check, uncertainty and practical tie rule. Declare how a conflicting ranking metric is reported. Require role-specific support for the selected forecast. Do not choose thresholds to make a particular player or algorithm pass. Version the protocol if a correction changes the estimand and keep the original for the audit.

Choose the evidence floor from 2025 support and stability by role before reviewing ranked names. Use 48 opportunities and six matches as the initial comparison point and justify any lower or higher floor with count and uncertainty results. Define how ordinary exposure is handled and keep a provisional watchlist for players whose lift is poorly identified. Record the tiebreak as conservative score, mean pressure impact, distinct pressure matches, then stable player ID. Freeze model choice on 2025 evidence and run the final player comparison once. Keep a record of any later data repair or required evaluation rerun.

PASS -> round1_prompts/05_match_state_models.md | The chronological protocol and common comparison target are frozen.
FAIL -> round1_prompts/03_exploratory_analysis.md | Repair the coverage or evidence grid.
FAIL -> round1_prompts/04_freeze_evaluation.md | Repair fold assignment, fit boundaries, or comparison definitions.
BLOCKED -> round1_prompts/04_freeze_evaluation.md | A simpler predeclared split still supports honest forward evaluation. Record the new split and rerun the gate.
BLOCKED -> STOP_BLOCKED | No credible chronological assessment is supported. Resume at round1_prompts/04_freeze_evaluation.md after new evidence.
```
