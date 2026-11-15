# Stage 00 · Establish the project contract

**Input** · This playbook, existing workspace, local pack, Round 1 brief, form screenshots.

**Outputs** · CLI design, dependency manifest, run ledger, immutable input manifest, documented stage map.

**Read for this stage** · [Input data contract](data_contract.md) and [organizer requirements](rules_contract.md#organizer-requirements).

## Implementation prompt

```text
Inspect the workspace and any applicable agent instructions. Confirm all six CSVs and the brief are readable. Record paths, SHA-256, sizes, package versions and known constraints. Set up the smallest runnable package and CLI with clear errors for missing inputs, plus a configuration with explicit seed and artifact location. Check existing user changes before editing. Keep training, rankings, dashboards, and uploads outside this stage.

For the audited repair, extend the existing package and use artifacts_revalidated for the active run. Use separate fresh directories for tests that write outputs and for the clean verification rerun. Preserve the legacy snapshots. Include source and configuration in fingerprints along with the raw hashes. Reuse fingerprinted parsed data, typed columns and fitted fold artifacts where practical. Measure runtime before changing storage or adding a dependency. Do a targeted rerun for a localized defect.

Run a CLI help smoke check and verify the input manifest can be reproduced. The ledger must support PASS, FAIL, BLOCKED, and PROVISIONAL with evidence. Keep the raw pack, working extracts, fitted artifacts and checkpoints out of shared repositories and public services. Record separate reasons for missing public archives and an unverified dropdown pool, since neither blocks the raw audit.

PASS -> round1_prompts/01_ingest_identity.md | The CLI smoke check and input manifest are reproducible.
FAIL -> round1_prompts/00_project_contract.md | Repair the paths, command, manifest, or environment declaration.
BLOCKED -> STOP_BLOCKED | Required input or runtime is unavailable. Record the missing item and resume at round1_prompts/00_project_contract.md when it is restored.
```
