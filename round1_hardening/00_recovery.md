# H00 · Preserve the previous run and reproduce defects

**Read** · [Audit](../ROUND1_HARDENING_AUDIT.md), [shared execution contract](../round1_prompts/_shared.md), [data contract](../round1_prompts/data_contract.md).

**Inputs** · Existing package and tests, raw pack, `artifacts_revalidated`, `test_artifacts_revalidated`.

**Deliver** · `artifacts_hardened` checkpoint, preserved input fingerprints, defect-to-check table and benchmark plan.

## Implementation prompt

```text
Treat the prior STOP_PROVISIONAL as historical evidence. Verify all seven raw-pack fingerprints against the recorded manifest. Preserve the raw files and prior output directories. Use artifacts_hardened for the active run and a separate temporary directory for tests that write outputs. Record source, config, input and output fingerprints so the new run cannot silently reuse stale results.

Reproduce the material audit failures from the saved artifacts before editing. Confirm the candidate that generated each evaluated top ten, B0's scored versus deployed width, the mismatch between Q25 and mean/interval, the use of full-pack roles in comparison, A's differing assessment keys and the absence of exact score rows. Reproduce one case with a tiny read-only diagnostic rather than rerunning the whole pipeline. Record expected behavior independently from the current code. Every defect needs an owning stage and a check that would reject the old result. Do not require any named player, model or sign of improvement in a test.

Lock the modeling target as future net pressure impact conditional on a supported workload, with separate batting and bowling scores. Record the already inspected 2025 and 2026 results. Define a fresh protocol version before comparing repaired or new models. Use one package and the existing CLI. Measure time spent reading data, building features and fitting before optimizing. Reuse fingerprinted data and model artifacts between compatible experiments. Preserve the entrant's control of final choices.

PASS -> round1_hardening/01_cricket_ledger.md | The raw pack, prior output and baseline defect evidence are preserved and the new checkpoint is isolated.
FAIL -> round1_hardening/00_recovery.md | Repair reproducible input, isolation or audit-record defects.
BLOCKED -> STOP_BLOCKED | Required inputs or evidence are unavailable. Record them and resume at round1_hardening/00_recovery.md when available.
```
