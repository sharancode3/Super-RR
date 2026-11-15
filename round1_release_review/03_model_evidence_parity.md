# F03 · Unify model dispatch, metrics and evidence

**End goal** Each tested candidate can be run end to end, and every exported number points to its real fit, rows and source.

```text
Inspect rr_pressure/compare.py, forecast.py, challengers.py, robustness.py, rankings.py and exports.py. Repair integration before interpreting model performance. Use the F02 target and fixture cutoffs.

Loop: reproduce the mismatch -> centralize the contract -> force every candidate path -> replay outputs.

1. Use one explicit candidate ID and common fit/predict/rank interface across rolling assessment, shortlist tests, perturbations and production. Define one forecast record per role, player, forecast cutoff, target ID, context ID and fit ID. Use the same score and tie-break function for all rank consumers. Force every selectable model through both assessment and export, especially A and C. A model without a complete production path can remain diagnostic only. Unknown IDs or absent required fields fail loudly.
2. Define optional forecast fields by what the estimator fits. E may publish Q25 only. It may publish other quantiles from the same family, target and context after calibration and a monotonicity check. D can produce model-implied quantities under its fitted distribution. Never borrow B0 mean or interval to populate D/E fields. Store usual performance and empirical lift as dated descriptive fields. Distinguish a future outcome interval from parameter uncertainty and match-resampled rank uncertainty.
3. Freeze the comparison keys before model joins. Use transparent common cold-start priors where estimable. Otherwise publish the full base universe, exact paired intersection, missing rows by model and reason, and the loss conditioned on coverage. Check duplicate keys and unchanged target values. Use stable ID after predeclared tie-break evidence and report exact ties and near ties. Do not infer an IPL context from an absent column. Verify predictions are unchanged when only outcome-side fields in assessment input are edited.
4. Derive example numbers, counts, dates, wording, cohort, selected model and status from the actual records. Replay a scored batting and bowling event from full-precision fields before rounding, including the actual chosen wicket cost. Test excluded examples, negative evidence and missing fields. Remove fixed favorable narratives and unsupported portal status claims. Add hash-derived run, snapshot and fit IDs and a manifest that propagates these IDs into every output. Validate status and resume pointers together. A changed input, fit, scenario or rankings snapshot must have a new appropriate fingerprint.

Gate: forced A/B/B0/C/D/E branch tests for every model still selectable, joined row set checks, rank and forecast parity, no fallback to another candidate, and independent arithmetic replays with correct explanatory text. Test failures use real artifacts or purpose-built fixtures, without requiring saved success statuses.

PASS -> round1_release_review/04_train_select.md
FAIL -> repeat F03 for interface, dispatch or arithmetic mismatch. Redirect target/feature problems to round1_release_review/02_temporal_target.md and event problems to round1_release_review/01_cricket_data.md.
BLOCKED -> STOP_BLOCKED and record the unsupported candidate, contract or missing evidence. Resume at round1_release_review/03_model_evidence_parity.md.
```
