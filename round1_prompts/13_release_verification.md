# Stage 13 · Verify reproducibility and hand back

**Inputs** · Completed CLI, selected configuration, audited input pack, frozen result snapshot.

**Checkpoint records** · 00, 04, 09, 12.

**Outputs** · Verified release status, rerun command, reproducibility evidence, explicit handoff.

**Read for this stage** · [Organizer requirements](rules_contract.md#organizer-requirements).

## Release checklist

- [ ] Data scope. The RR inputs have unchanged hashes. Coverage and exclusions are explicit by tier, innings and role. External copies only corroborate the RR evidence.
- [ ] Joins preserve the intended grain and conflicting identities have audit evidence.
- [ ] Pressure definition. Both innings have a valid pre-ball route. The evidence includes a contrast between high pressure and an ordinary state.
- [ ] Scoring and transformations. Tests distinguish legal balls, team runs, batter runs, charged extras, team wickets and bowler credit. Nonstandard innings are flagged.
- [ ] Fair comparison. Both roles show usual level, pressure effect, forecast, uncertainty, and exposure. Peer contexts and the IPL versus T20I transfer check are documented.
- [ ] Reliability. Three candidates use the same reference or a missing comparison is disclosed. Measured 2025 validation selects the actual refit method. The previously inspected 2026 assessment is labeled, and coverage and sensitivity results are visible.
- [ ] Reproducibility. The clean rerun, terminal and exports agree. The manifest identifies inputs, thresholds, metrics and the selected model.
- [ ] Rank evidence. Every proposed pick has a supporting match or aggregate result, a risk or limitation, and a plausible RR role. Each verified list has ten distinct confirmed dropdown names in order.
- [ ] Submission handoff. The Unstop-order export and the later PDF or PPTX share a snapshot. The entrant has the evidence needed to own the final choices and write their own rationale. Track that review separately from backend readiness.
- [ ] Data use. Raw data and internal extracts stay local. A future public dashboard uses public or specifically approved material.

[Quantile forecast evaluation and pinball loss](https://doi.org/10.1146/annurev-statistics-032921-020240) · [ICC playing conditions](https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions) · [CatBoost ordered boosting paper](https://proceedings.neurips.cc/paper/2018/file/14491b756b3a51daac41c24863285549-Paper.pdf) · [Official competition listing](https://unstop.com/hackathons/crp-superr-selector-season-2-help-shape-rajasthan-royals-ipl-2027-auction-strategy-rajasthan-royals-1792758/amp)

## Implementation prompt

```text
Run the focused regression suite. If earlier reproducibility evidence covers the unchanged model and only eligibility changed, reuse that evidence and recheck the updated rank filter, terminal, and exports. Otherwise run the CLI from a clean output directory against the local data pack, then rerun with the same inputs, configuration, seed, and public cache. Compare stable ranking order, decision, eligibility, and normalized metrics. Allow generated run IDs and timestamps to vary. Record whether cached and clean runs agree. Verify that changing a source hash invalidates downstream results, missing files fail clearly, raw input hashes stay identical, and logs contain the correct fold boundaries.

Ensure tests read the active run or independent small fixtures instead of hard-coded legacy artifact paths. Check that output changes when inputs or selected models change and that a later outcome cannot change an earlier fit. Recompute sampled metrics from stored predictions. Verify real replay rows and sample official scorecards. Check that no test requires a specific winning model, positive pooled gain, or fixed ranking names. A passing hash or schema test alone proves neither validity nor predictive skill.

Review the recovery checkpoint and trace every audited defect to a passing check or a disclosed blocker. Confirm the selection manifest was written before the repaired 2026 assessment. Trace the selected model ID and fingerprint from measured validation through the production refit, rank rows and terminal output. Recalculate at least one reported metric and one batter and bowler example from the stored predictions and real source rows.

Inspect the terminal output as a user would. Verify that the predictions come from the chosen fits, that validation numbers have coverage and units, and that exact, proxy, exploratory and provisional results are distinguishable. Check both the model-validation and eligibility gates. A reproducible run with inconclusive predictive evidence is an exploratory or provisional handoff. A verified release needs evidence from the measured forecast gates, ten confirmed dropdown choices for each role, and the final form order cross-check.

Return the exact rerun command, release status, selected model by role, model-comparison summary, paths to both lists, the most important validation result, and any material uncertainty. Hand off a checklist for the required PDF or PPTX and the optional dashboard from the frozen exports. Record pending entrant review as pending. The entrant owns the final reasoning, choices and single submission.

PASS -> STOP_VERIFIED | Measured validation and reproducibility passed, and both lists have ten confirmed dropdown names in the correct order. Return the verified backend handoff.
FAIL -> round1_prompts/00_project_contract.md | Repair raw-input integrity, runtime pinning, or fingerprint invalidation.
FAIL -> round1_prompts/04_freeze_evaluation.md | Repair fold boundaries or evaluation leakage.
FAIL -> round1_prompts/09_model_comparison.md | Repair forecast comparison or selected-model provenance.
FAIL -> round1_prompts/11_rankings_and_eligibility.md | Repair nonreproducible ranking or dropdown order.
FAIL -> round1_prompts/12_terminal_exports.md | Repair inconsistent terminal and file exports.
FAIL -> round1_prompts/13_release_verification.md | Repair a clean-run or final verification defect that belongs to this stage.
BLOCKED -> STOP_PROVISIONAL | The terminal run is reproducible and live eligibility is unresolved. Resume at round1_prompts/11_rankings_and_eligibility.md when the dropdown pool is verified.
BLOCKED -> STOP_PROVISIONAL | The run is reproducible but model evidence is inconclusive. Report the measured limitations and resume at round1_prompts/09_model_comparison.md when the required evidence is available.
BLOCKED -> STOP_PROVISIONAL | The terminal run is reproducible and another external dependency remains. Record the exact owning prompt as resume_prompt. For insufficient player evidence, use round1_prompts/11_rankings_and_eligibility.md once new evidence is available.
BLOCKED -> STOP_BLOCKED | The terminal run cannot be reproduced and no verified fallback exists. Record the failed check and resume at round1_prompts/13_release_verification.md after the dependency is restored.
```
