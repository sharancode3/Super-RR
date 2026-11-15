# Stage 02 · Establish exact and proxy ball ledgers

**Inputs** · Audited RR dimensions, deliveries, fixtures, optional local public JSON archives.

**Checkpoint records** · 00, 01.

**Outputs** · Delivery ledger by route, matchup crosswalk, exact-match and proxy coverage, discrepancy records, exclusions and scoreboard fixtures.

**Read for this stage** · [Input data contract](data_contract.md) and [cricket scoring rules](rules_contract.md#cricket-scoring-rules).

## Implementation prompt

```text
Start from RR delivery order. Build the state ledger before filtering to a modeling cohort. Store pre/post team score, off-bat runs, bowler charges, wickets, event index, official over position, legal balls and resources, match date, verified target, free-hit status where known, attribution and provenance. Apply the linked rules contract. A non-wicket with a populated dismissed ID stays a non-wicket unless independently reconciled. Preserve unusual events and quarantine ambiguous states.

For the exact route, match Cricsheet fixtures using competition, date and normalized team pair. Allow a date shift only where an unambiguous venue or sequence corroborates it. Align using over and within-over event sequence, participants, off-bat runs and normalized wickets. Repeated displayed ball numbers are possible. Keep match IDs and archive hash in the crosswalk. Accept an innings as exact only if sequence, score, wickets, legal balls, target and terminal outcome reconcile to independent official evidence where available. Record whether verification used a complete matched public ledger, a scorecard, or both. A chase is exact only when its own states and target are verified.

Start with the IPL and men's T20I public archives rather than the full database. Cache by source hash. Keep external matches outside the official player evidence cohort and avoid counting a public copy of an RR delivery as a second observation.

Test the exact lane against two independent real anchors when source rows are available. In fixture 50140 RCB's raw batter total is 188, while the official total is 201/8 and the target is 202. In fixture 13511 raw batter totals of 100 and 99 differ from the official 103 and 104/1. If only the RR ledger is available, the expected behavior is to preserve the off-bat figures and withhold exact scores, targets and charged extras. A rain delay alone does not imply a shortened innings. Use verified playing conditions and scheduled resources. Record a route as exact only when the implemented source path actually verified it.

For the RR-only route, reconstruct from runs off the bat and validated sequence information. Use first-innings off-bat total minus chase off-bat runs as a labelled proxy. Never use that gap to infer a terminal win or a true runs requirement. Check complete overs, innings bounds and paired public examples. Use structured revision flags, innings, result text and public metadata together to exclude nonstandard v1 fixtures. Log exclusions and never force an over to six or guess revised targets.

Test wide stumping, a no-ball with off-bat runs or byes, free-hit carryover, a non-striker run-out, retirement, pre/post penalties, a chase won on an extra, a tie at completion, an umpire miscount, a missing event and a rain result with blank revision fields. Test that changing delivery t's result changes post(t) and subsequent rows but leaves pre(t) unchanged. Use RR vs RCB on 10 April 2026 as a regression case when public data for it is present.

Publish coverage by season, tier, innings, phase and player role. For the verified route, require every included inning to reconcile. Use the verified route as the official candidate only if the frozen coverage decision shows adequate representative support. Keep the RR-only route as a sensitivity comparison. If public archives are missing or coverage is materially selective, train the validated RR-only route and label its metrics. Put exact-route gaps and reasons in the run ledger.

PASS -> round1_prompts/03_exploratory_analysis.md | Publish the validated lanes with coverage evidence and reasons for any omissions.
FAIL -> round1_prompts/01_ingest_identity.md | Repair a fixture, player, or join defect.
FAIL -> round1_prompts/02_scoreboard_ledgers.md | Repair event, sequence, or scoreboard logic.
BLOCKED -> round1_prompts/03_exploratory_analysis.md | Public retrieval or overlap is inadequate and the validated proxy is available. Record the exact-lane gap.
BLOCKED -> STOP_BLOCKED | Neither lane has valid chronology. Resume at round1_prompts/02_scoreboard_ledgers.md after new source evidence arrives.
```
