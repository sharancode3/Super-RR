# Stage 00 · Freeze the dashboard evidence

## Agent prompt

Read [START](START.md), the supplied problem statement PDF and the original report evidence. Treat archive notes as records of previous decisions. Use the source map below for current facts. Record the exact cutoff in the UI. Leave all earlier artifacts in place.

### Build a source register

| Source relative to the RR workspace | Approved use |
| --- | --- |
| `artifacts_rr_retrain_audit_20261115/recommended_rankings.csv` | Canonical `player_id`, spelling, `role`, `rank`, `deployment`, 2026 pressure and ordinary exposure and impact, uplift, predicted composite impact |
| `artifacts_rr_retrain_audit_20261115/player_evidence.csv` | Pressure-exposed fixtures, one-match omission range, route, RR fit and caveat. Join using verified discipline and rank, then assert exact name agreement |
| `artifacts_rr_scenario_review_20261115/scenario_review_rankings_with_stability.csv` | Authoritative match-resample inclusion by `player_id`, role and rank. Validate any duplicate metric in the evidence file against this file |
| `artifacts_rr_scenario_review_20261115/updated_stability.json` | 1,000 draws, medians, whole-list results and pool size |
| `artifacts_rr_scenario_review_20261115/verified_rankings.csv` | Exact Unstop option-label check. This is a name cross-check. Its impact columns come from a different summary, and some earlier stability values differ |
| `artifacts_rr_retrain_audit_20261115/retraining_comparison.csv` | Rebuilds and historical model comparisons. Preserve role, source, lane, season, cutoff, recipe and number of assessed candidates or picks whenever relevant |
| `artifacts_rr_retrain_audit_20261115/DATA_AND_TRAINING_AUDIT.md`, `retraining_audit.json` and `artifacts_rr_scenario_review_20261115/SCENARIO_REVIEW.md` | Source changes, chronology checks, model choice, interpretation and conditional market analysis |
| `scratch/rr_rebuild_recorded_20261115/input_manifest.json`, `coverage_report.json`, `eda_summary.json`, `evaluation_split_manifest.json`, `model_diagnostics.json`, `round1_progress.json` | Aggregate raw-to-derived counts, data quality and chronological splits. Use only explicit approved aggregates |
| `artifacts/round1_progress.json`, `artifacts_forecast_audit_20261111/`, dated review notes and early model checkpoints | Establish the earliest documented project work and distinguish recorded milestones from inferred dates |

### Project the data

1. Make a small build-time export with an explicit input allowlist. Use a real CSV parser. Generate a typed data bundle outside the historical folders. Store source path and hash internally, with an evaluator-readable shortened source title and date in the UI. Make output stable across two runs with equal inputs. Avoid using path names alone as evidence of time or duration. Never scan and copy an entire raw or artifact directory to public assets.
2. Create an identity record keyed by canonical player ID and a ranking record keyed by role and rank, with player ID as a foreign key. Names and historical photo affiliations never drive joins. Rank 1–10 is a contiguous ordered sequence for each role. Only player ID `152` appears twice across roles. The ID, media record and face are shared, while the two evidence records differ. Use dataset spelling in the display, including **Abishek Porel** and **Rasikh Salam**. Document aliases separately for media and portal verification.
3. Each role record carries display name, exact portal label if verified, name of the deployment, ordinal rank, dated role-scoped observed pressure and ordinary runs per 12 legal balls, both ball counts, pressure-exposed matches, signed uplift, predicted composite impact, stability fraction, resample count, RR route and evidence-backed fit or caveat. Keep model ranking priority as a named field if needed for reproduction. Preserve zero, negative values and missing values distinctly. Display missing as “Insufficient evidence” or “Unavailable” as appropriate.
4. For the modelling overview, carry the two rebuilds, five recipes, two roles, eight windows per role per source, 160 comparison rows, and 1,000 fixture resamples as separate quantities with explicit labels. Confirm them by counting source rows and unique keys. The eight windows comprise four 2024–25 forward windows, two retrospective 2026 forward windows and two auction replays. The 160 rows are comparisons, and include a historical pressure-only recipe. They cannot identify the exact number of independent model fits or the total compute time. Keep both unverified counts out of KPI cards.
5. Start the project story at the earliest verifiable record in the workspace. The current files support project work spanning **10–15 November 2026 IST**. Use exact milestone dates only with corroborating evidence. Distinguish project day, recorded run time with supporting timestamp or test duration, and model-training duration. The audit reports 232 full-suite tests and 33 targeted tests after final changes. Neither count is a model fit.
6. Build contract checks for ranks, exact ordered names, the shared Jadeja ID, numeric bounds, exact row linkage, `uplift = pressure - ordinary` within tolerance, context-scoped sample size, sanity of missing values, and the two zero whole-list counts. Make contract failures stop the data build with a useful error.

### Loop and handoff

Run the exporter twice, compare outputs and then follow five rows by hand from source to projection, including both Jadeja rows, Vaibhav, Siraj and a low-sample pick. Fix joins or citation drift and rerun the check. **Pass** when all 20 records have matched identity, rank, unit and source, both 10s exactly match the latest recommendations, and every displayed headline number has a named evidence source. Open [Stage 01](01_portrait_library.md).
