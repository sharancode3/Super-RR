# Stage 01 · Freeze the baseline and evaluation protocol

Use [START](START.md) for scope, immutable input, and the shared loop. Establish exactly what the existing run does and what evidence will support a change.

## Inspect and record

1. Verify all seven raw hashes against the locked input manifest and the manifest-listed baseline outputs. Compare the locked order with the reviewed order. Verify the recorded batting and bowling model selections and distinguish them from the policy that constructs the 20. Capture the current 20 and their original scores, both bowling model ranks, sample by league and phase, and acquisition status.
2. Trace the normal path through `rr_pressure.ingest`, `rr_pressure.pressure`, `rr_pressure.impact`, `rr_pressure.forecast`, `rr_pressure.challengers`, `rr_pressure.compare`, `rr_pressure.rankings`, and `rr_pressure.exports`. Locate where D drops player-match opportunities with fewer than six pressure balls. Locate where the bowling rule gives priority to C-IPL ranks and fills later slots from B0. Check which of those rules are exercised in a historical replay.
3. Reproduce a small data-backed baseline table. Start with the locked audit cases from [START](START.md). For both disciplines record ordinary and pressure impact by phase, recent IPL sample, match count, and the change when the strongest match is removed. Verify the current score and rank provenance for the examples. Use these checks to identify likely failure modes. Preserve the baseline for later comparison.

## Freeze what the model predicts

- Predict wicket-adjusted contribution in a stated IPL role under pressure, normalized to runs per 12 legal balls. Positive values should favor the player for each discipline. Estimate an ordinary-performance baseline for that player in comparable contexts and the difference under pressure. Use downside and repeatability to distinguish players with similar means. A player can be very good under pressure even if their own ordinary baseline is higher. The primary ordering needs evidence of reliable absolute performance as well as the ordinary comparison required by the brief.
- Use a shared, documented IPL reference for a role, with a standard workload and a phase/innings distribution set from earlier data. Document the common reporting scale across roles. Report the intended role, expected pressure impact, Q25 or another predeclared lower quantile, ordinary impact, pressure change, and uncertainty. Treat RR roster value and the acquisition route as decision evidence alongside the forecast. Specify in advance how they affect eligibility, role assignment, or near-ties.
- Keep the source match together. Derive and freeze each cutoff's candidate pool and features from history available at that cutoff. Reproduce 2024 from pre-2024 history, 2025 from pre-2025 history, and 2026 from pre-2026 history. Earlier windows may be used for model development where support permits. Treat 2025 as the original validation window and 2026 as a previously inspected retrospective. Record any fresh policy tuning on past windows as such. Preserve a future evaluation window if one becomes available.
- Predeclare the candidates, tuning budget, target, pressure and workload reference, eligibility logic, fit and evaluation cohorts, ranking rule, metric priority, acceptable degradation, and tie handling. Include forecast Q25 loss and calibration on identical opportunities, and realized player-weighted pressure impact and coverage of the ten. Record what must improve for a model change. Use earlier evidence and operational relevance to set any tolerance. Record the choice before rerunning the challenger comparisons. Preserve the original selection rule as a reference.

## Loop and exit

Reproduce → inspect → freeze → verify. If baseline figures fail, trace the relevant artifact and fix or record the discrepancy before using it as a control. If a required dated source is unavailable, record what evidence the replay can actually evaluate. Save the protocol and baseline checks in the new run directory, and record their paths in `review_progress.md`.

**Pass when** raw and baseline inputs are identified, the final ranking objective and comparison rule are written, and every evaluation cutoff is tied to its available history. **Next → [Stage 02](02_data_and_roles.md).**
