# H01 · Repair the cricket ledger and modeling populations

**Read** · [Cricket rules contract](../round1_prompts/rules_contract.md#cricket-scoring-rules), [Stage 02 scoreboard spec](../round1_prompts/02_scoreboard_ledgers.md).

**Inputs** · Verified raw hashes, score and delivery tables, optional local public records for the same RR matches.

**Deliver** · Audited event ledger and separate verified/proxy views, cohort keys, reconciliation report and edge-case tests.

## Implementation prompt

```text
Keep team score, off-bat runs, charged runs, team wickets, bowler wickets and legal opportunity flags as different columns. Assign source and certainty to each field. Preserve all events in order and filter only when creating the declared modeling views. Track confirmed free hits, unknown illegal events, retirement and official over miscounts without inventing transitions. Base standard-match exclusion on structured results, innings quotas and verified metadata. Keep ties, revised targets and Super Overs outside v1 unless explicitly modeled and tested as a separate lane.

Implement or repair the public-dir path only for exact verification. Join the same fixtures on normalized competition, teams and date, then align events on order, participants and outcomes. Require unique mappings, reconciled innings totals, wickets, legal count and target. Preserve original RR IDs. Test fixture 50140 against the official 201/8 and target 202, and fixture 13511 against official totals 103 and 104/1 when complete matching public rows are present. If only scorecards are available, use them as verification anchors and keep unverified ball states marked as proxy.

For the proxy, leave exact charges and targets unavailable. Fit batting and bowling on a consistent legal-delivery execution population with known off-bat runs and attributable outcomes. Keep wide and no-ball event counts and wide stumpings in an auditable separate profile when their exact impact is unavailable. In the exact lane, include verified charged extras and correctly attributed wickets according to the scorecard convention. Track legitimate events with zero legal exposure separately. Never convert unknown extras into precise run values or extrapolate terminal win from an off-bat gap.

Test real wide-stumping and run-out rows, winning extra, no-ball and byes, free-hit carryover, innings ending before 20 overs and missing sequence. Test that editing delivery t changes the next state and leaves pre(t) unchanged. Compare coverage and divergence by IPL, T20I, emerging teams, season, role and opponent. Require a meaningful supported cohort for both roles before comparing models.

PASS -> round1_hardening/02_temporal_reference.md | Valid ledger, eligible populations and provenance checks pass.
FAIL -> round1_hardening/01_cricket_ledger.md | Repair event semantics, cohort membership or fixture and delivery joins.
BLOCKED -> round1_hardening/02_temporal_reference.md | Public matching is incomplete and the separately labeled proxy passes. Record exact-lane omissions.
BLOCKED -> STOP_BLOCKED | No defensible event lane remains for a required role. Resume at round1_hardening/01_cricket_ledger.md when the source issue is resolved.
```
