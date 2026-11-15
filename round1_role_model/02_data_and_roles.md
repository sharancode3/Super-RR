# Stage 02 · Build and verify the role and context data

Read the frozen protocol and baseline evidence from Stage 01. Reuse the ledger and prior pipeline logic where their fingerprints and invariants hold. Build the minimum feature view needed to compare ordinary and pressure performance in the same job.

## Audit the inputs and construct the observations

1. Join by canonical player ID and validated fixture and delivery keys. Check join cardinality, alias collisions, missing IDs, duplicate playing-XI records, season boundaries, and excluded fixtures. Report raw and eligible rows separately. A missing value means unknown. A player without observed pressure exposure in a window has no measured pressure outcome for that window.
2. Preserve pre-ball state, legal-ball counts, role, pressure definition, match date, competition tier, target source, and both batting and bowling impact. Validate wides, no-balls, byes, leg-byes, and wicket credit against the existing ledger rules. Include applicable extra-delivery contribution in the numerator and use the documented legal-ball denominator. Carry extras-only cells forward where applicable without dividing by zero or attributing evidence to a player with zero legal-ball exposure. Recompute worked examples from their ledger rows.
3. Freeze pressure labels using references fitted at each cutoff. Use only pre-delivery game state, including phase, wickets, balls remaining, and chase demand or leverage when available. Reuse the existing pressure definition for the main comparison. Use the existing percentile sensitivity as a check. The locked run has one verified target and 805 proxies. Keep that distinction visible. Bring in public scorecard values only after reliable fixture and state reconciliation. Publish coverage and impact of verified corrections when made.
4. Reuse the existing contextual impact outcome for the first controlled comparison. For each player, fixture, phase, innings, and pressure state, preserve additive impact, legal exposure, and enough provenance to recover the source deliveries. Include ordinary balls and every short pressure stint with usable exposure. Separate the exposure count from performance. Keep per-delivery context if a later model needs it. Do not use a minimum-six-pressure-ball rule to define the new training universe. Measure what the old threshold omitted, including short finishing and death-bowling appearances.

## Build as-of role evidence

- Use actual batting position and exposure to distinguish openers, middle-order batters, and finishers. Keep wicketkeeping as a separate capability. For bowlers use phase usage, legal workload, and bowling style for powerplay seam, middle-overs spin or pace, and death bowling. An all-rounder can qualify in both disciplines from independent evidence. Handle role changes and sparse cases explicitly.
- Derive prior-only role deployment and ordinary performance, recent season and career evidence, competition tier, and match-to-match variation. Add context like opposition strength or matchup style only if identities, coverage, and time cutoffs support it. Freeze form windows and any recency weighting before comparison. Keep players with sparse direct IPL data as uncertain when there is usable transfer evidence.
- Make a compact EDA showing IPL vs T20I counts, ordinary vs pressure sample by phase, role coverage, short-stint exclusions from the old fit, and how much evidence depends on older seasons or one match. Check useful examples from the audit. Compare pressure and ordinary within the same role and phase. Report shared-support limitations when the situations are very different.

## Loop and exit

Build → audit → correct → rebuild only the affected stages. Run checks for valid join counts, consistent scoring signs, fixture isolation, and strict feature cutoffs. Verify that a future appearance cannot change an earlier role, feature, or qualification. Track scorecard uncertainty where the pack remains approximate. Update `review_progress.md` with the feature definition, counts, and artifact paths.

**Pass when** the training view has both pressure and ordinary observations, valid short stints are retained, role evidence is as-of each cutoff, and the ledger and aggregate totals reconcile under the documented conventions. **Next → [Stage 03](03_fit_and_calibrate.md).**
