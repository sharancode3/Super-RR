# SupeRR Selector Season 2 Round 1 — final model review

Work from C:/SHARAN PROJECTS/rr. Produce two ordered ten-player review lists with evidence of pressure performance, repeatability, intended RR role and retention or acquisition route. The submitted data pack and its case PDF are the evidence base. Preserve the original data and each existing snapshot. Work through the normal Python CLI in a fresh output directory, with seed 2027 for the control.

## Read first

- [Audit and research](00_audit_and_sources.md) records the observed defects, comparison results, rules and evidence as of 12 November 2026 IST.
- Baseline C:/SHARAN PROJECTS/rr/artifacts_s2_blend_20261112, snapshot RR_SUPE_RR_S2_0c2fb1645f3e524579d9. Earlier comparison C:/SHARAN PROJECTS/rr/artifacts_reval_final_20261112.
- Read the case PDF in C:/SHARAN PROJECTS/rr/6af3166e7b922_data_pack and the current Unstop Round 1 description. Use the downloaded case and entrant-provided form evidence to specify deliverables. Recheck official updates as of the review timestamp.

## Loop and handoff

Create one progress log in the fresh run with the active stage, input and baseline fingerprints, config, commands, measured results, failed checks and next stage. In each stage, follow its implementation and loop. Reproduce a problem before changing it. Fix the earliest failing dependency, rerun the smallest checks that establish the fix, then run the stage exit checks. If a later failure invalidates an upstream output, return to that stage and regenerate dependent files. Use a documented experiment budget, and end a model trial when the evidence reaches its declared decision gate. Record a tie, a failed candidate, or limited evidence as a valid measured result. Independent acceptance criteria cover correctness, forecast quality, ranking stability and RR feasibility. A passing test, a coverage percentage and a chance of making the top ten each describe different things.

Keep the entrant's current review choice explicit. Evaluate RR incumbents as retention options in an RR review scenario, starting with Vaibhav Sooryavanshi and applying the same criteria to every incumbent. The user prefers more Indian players when building the shortlist. Compare a documented Indian-majority scenario using role-matched alternatives. Apply official slot rules only at the squad or XI level they govern. Preserve the pure model rank and the evidence behind any RR recommendation. Use named player cases as checks, with ranks produced by the declared rule.

1. [Reproduce and freeze the contract](01_reproduce_and_freeze.md).
2. [Repair match state, pressure and impact](02_cricket_state_and_pressure.md).
3. [Repair the replay and evaluation](03_replay_and_evaluation.md).
4. [Train and calibrate the candidate models](04_fit_and_calibrate.md).
5. [Measure shortlist uncertainty and stability](05_shortlist_uncertainty.md).
6. [Build the RR recommendations](06_rr_decisions.md).
7. [Verify and hand off](07_clean_handoff.md).

Start at Stage 01. Finish at BACKEND_REVIEW with report-ready evidence and an entrant decision sheet. The entrant owns the final recommendations and Unstop submission.
