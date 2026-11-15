# H03 · Repair selection, refit and reporting parity

**Read** · [Audit](../ROUND1_HARDENING_AUDIT.md), [comparison contract](../round1_prompts/09_model_comparison.md).

**Inputs** · Chronological reference rows, predeclared gates, existing candidate implementations.

**Deliver** · Repaired A/B0/B1/C comparisons, shared prediction/ranking path, candidate manifests, fail-closed tests.

## Implementation prompt

```text
Give every selectable candidate a stable ID, role, feature and target recipe, cutoff, estimator config, and fingerprint. Use a common forecast and ranking path in validation, replay, robustness and production. Candidate A is the role/phase benchmark with a fitted empirical quantile. B0 partially pools usual skill and forecasts pressure performance without a personal pressure slope. B1 adds a fitted shrunk personal pressure effect. C uses shallow boosted context or outcome features and the same forecast target. If a candidate is selectable, implement its own real refit. Missing and unsupported candidate IDs must fail clearly. A display label must never choose an estimator.

Use the same predictive center, spread and quantile rule for a candidate during validation and deployment. Remove the fixed B0 validation widths and use the fitted or calibrated forecast for that fold. Store chosen forecast mean, Q25, interval and exposure together. When B0 is selected, keep the B1 pressure estimate as a separate descriptive statistic. Derive each assessed top ten by sorting its own candidate score from prior data. Verify the list passed to scoring against the expected candidate IDs and selected-player IDs. Add tests where B0 and B1 order differs and where C or the baseline can win. Test a clear inconclusive result and missing manifest handling.

Join candidate predictions by role, player, match and assessment cutoff and require matching target, lane and exposure keys. Score common rows for all candidates. Report differences in ability to predict additional players as coverage. Use the fixed historical candidate pool and report how many top-ten picks had enough later observed exposure. Define top-ten impact as a realized rate for those observed picks and include a comparable benchmark plus uncertainty. Write prediction rows with model, source, units and cutoff so every aggregate can be recomputed independently. Test match resampling with repeated match weights.

Replace literal cohort totals, performance claims, fixed winner language and snapshot IDs with source-derived results. Keep a typed run manifest for scores, evidence and refit choice. Rerun the legacy B versus B0 ranking replay as a regression for the defect, then produce fresh repaired results. Store the corrected comparison as a baseline for H04. A computationally correct but inconclusive model can be a valid baseline for research and is not a verified submission model.

PASS -> round1_hardening/04_challengers.md | Every scored forecast and reported shortlist comes from the same candidate and the repaired baseline can be reproduced.
FAIL -> round1_hardening/02_temporal_reference.md | Repair reference keys, provenance, support or target mismatches.
FAIL -> round1_hardening/03_model_parity.md | Repair candidate dispatch, scoring, selection or reporting.
BLOCKED -> STOP_BLOCKED | No coherent candidate can be evaluated and refitted. Resume at round1_hardening/03_model_parity.md once the fit or data blocker is resolved.
```
