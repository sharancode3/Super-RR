# Recovery gate · Revalidate the existing model run

**Inputs** · Existing source and tests, `artifacts`, `test_artifacts`, supplied RR pack, [validation audit](../ROUND1_VALIDATION_AUDIT.md).

**Outputs** · Isolated repair checkpoint and an ordered set of invalidated stages.

## Implementation prompt

```text
Treat the prior STOP_PROVISIONAL snapshot as historical audit evidence. Its remaining blocker is broader than dropdown eligibility. Read the validation audit and inspect the referenced source and files. Verify the seven input hashes against the original manifest. Preserve raw data and both old output directories as read-only evidence. Use artifacts_revalidated as the default new output directory and keep its checkpoint there. Resume that directory if its source, input and configuration fingerprints agree. Keep the raw pack as the canonical source and write derived tables separately.

Mark old role, ledger, model comparison and export evidence stale for release. Reuse the existing source package, CLI and useful tests. Record the previously inspected 2026 outcomes. Lock the corrective validation protocol before viewing new 2026 results and use earlier rolling folds to choose models. Confirm no test prescribes a winning candidate or a favorable metric. Leave legacy snapshots available for a before-and-after comparison.

Run the smallest diagnostic that can reproduce each relevant audit defect. Avoid a full model run before the accounting and split checks are sound. Start at Stage 00 for the fresh manifest and then follow the stage files. Use verified fingerprints to reuse only unaffected work. Resolve public-scorecard gaps with the documented proxy where valid. Use the supplied RR data for all official training and evaluation evidence.

Map each known defect to its owning stage and a check that can fail. Include the float Brier baseline, as-of role features, legal-ball workload, paired candidate comparison, model dispatch, and the replay mismatch. Record the checks and the status of each defect in the recovery checkpoint. Clear a defect only with new observed evidence from its owning stage.

PASS -> round1_prompts/00_project_contract.md | Inputs and legacy outputs are preserved, and the new recovery path is established.
FAIL -> round1_prompts/recovery_gate.md | Repair the input path, fingerprint comparison, or output isolation before training.
BLOCKED -> STOP_BLOCKED | Required original inputs are unavailable or cannot be confirmed. Record the exact source issue and resume at round1_prompts/recovery_gate.md when resolved.
```
