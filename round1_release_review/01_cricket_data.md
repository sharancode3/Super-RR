# F01 · Reconcile cricket events and audit the data

Use match-date versions of the playing conditions. [IPL playing conditions](https://www.iplt20.com/playing-conditions) · [ICC playing conditions](https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions) · [MCC laws and editions](https://www.lords.org/mcc/about-the-laws-of-cricket)

**End goal** Produce auditable, uniquely keyed event and opportunity data with an honest scoreboard source and complete denominator definitions.

```text
Open round1_prompts/data_contract.md and round1_prompts/rules_contract.md. Inspect ingestion, ledger, pressure and impact aggregation. Use the RR pack as the training and evaluation source. Store clean copies, exclusions and audit evidence in the new run.

Loop: profile -> transform -> reconcile -> falsify.

1. Inventory per file and season, tier, innings and phase. Audit schema and categories, candidate player and team IDs, aliases, playing-XI cardinality and substitutions, missing fixtures, conflicting results, duplicate keys and chronology. Separate observations from imputed values. Audit field availability by date and competition, especially extras and optional tracking fields. Verify join cardinality and row count at every merge. Treat an unknown venue or bowler style as unknown.
2. Verify chronological event order independently of over notation and wall-clock timestamp. Keep pre- and post-event state, team wicket, striker dismissal and bowler credit, legal workload and delivery count separate. Cover run-out of either batter, wide stumping, no-ball plus bat runs, free hit carried across another illegal ball, retired hurt/out, byes, leg-byes, penalties, umpire miscounts, innings end, tie, super over and revised chase cases. Follow the applicable competition rules. Never compute a player's denominator from a delivery class that differs silently from the numerator's class. Document rates when illegal-delivery outcomes contribute and distinguish them from conventional strike rate and economy.
3. Confirm extras1_runs behaves as a category code. Validate extras_2_runs and each accounting assumption before using it. Compare raw and derived state to official anchors 50140 and 13511 and at least one wicket/extras edge case. Keep separate exact and off-bat proxy sources. Permit exact state only where complete pre/post runs, wicket/ball counts, target and an auditable delivery alignment reconcile. Record every mismatch and the policy decision. Keep the competition cohort exclusions visible. Never promote a scorecard-only anchor to exact ball-by-ball evidence or silently splice states.
4. Show retained and excluded opportunity counts, role/phase/tier support, pressure event concentration, missingness, and IPL overlap. Emit compact machine-readable tables and a readable summary. Estimate plausible pressure-label sensitivity to unknown extras on any reconciled paired sample. Use explicit unknowns for unscored rows, and make excluded or unscored rows ineligible for report examples. Regression-test fixture 13612's exclusion. Validate actual wicket/ball states by hand on two small real sequences.

Gate: raw hashes unchanged, event keys unique, rule and replay tests pass, coverage reconciles, aggregation denominators are explicit, and all released examples must come from scorable rows with a known evidence lane. Keep proxy limitations in downstream artifacts even if the gate passes.

PASS -> round1_release_review/02_temporal_target.md
FAIL -> repeat F01 for ledger, eligibility or cohort mismatches. If raw or historical hashes differ unexpectedly, redirect to round1_release_review/00_reproduce.md.
BLOCKED -> STOP_BLOCKED with the affected source lane and resume at round1_release_review/01_cricket_data.md. If exact data are missing but the documented proxy passes, continue with explicit proxy scope.
```
