# Stage 01 · Ingest and reconcile identity

**Inputs** · Six supplied CSVs, input manifest.

**Checkpoint records** · 00.

**Outputs** · Schema audit, fixture and player dimensions, alias table, XI conflicts and join evidence.

**Read for this stage** · [Input data contract](data_contract.md).

## Implementation prompt

```text
Load each table at its actual grain. Validate required columns, numeric IDs, booleans, nullable fields, date parsing and numeric sequence sorting. Treat literal None and missing tokens deliberately. Inventory duplicate, orphan, missing and conflicting records. Check the expected many-to-one or one-to-one cardinality before each join and verify row count after joining. Fail on unintended row multiplication.

Screen for the same physical fixture under multiple IDs using date, teams, competition context and sequence fingerprints. Keep legitimate same-day fixtures distinct. Resolve verified copies before splitting so they cannot duplicate training or assessment evidence.

Use RR player IDs across seasons. Preserve original display names and aliases. Derive actual roles from earlier observed batting order and phase usage. Resolve XI duplicate groups only when fields agree. Keep the 35 conflicting batting-order groups in an audit table and avoid borrowing future appearance information. Track captain, keeper and Impact Player fields separately from inferred role. Keep a one-to-one alias crosswalk for any public IDs added later.

Separate identity/display metadata from learned profile features. Full-pack totals can support a final dated profile or an audit, while every historical model needs role, style, workload, venue and opponent inputs based on prior available matches. Provide a pooled unknown-role fallback for debuts. Test with a real player's earlier appearance that adding or changing later appearances leaves the historical profile unchanged.

Compare measured counts against the starting audit and explain differences rather than forcing counts to match. Assert delivery and fixture keys are unique. List all fixtures without deliveries and join failures. Build an independent regression fixture that would fail if an XI join multiplied a player's balls.

PASS -> round1_prompts/02_scoreboard_ledgers.md | Required joins preserve grain and quarantined optional identities are documented.
FAIL -> round1_prompts/01_ingest_identity.md | Repair schema, join, or identity logic and repeat the audit.
BLOCKED -> STOP_BLOCKED | A required input is missing. Record it and resume at round1_prompts/00_project_contract.md when supplied.
```
