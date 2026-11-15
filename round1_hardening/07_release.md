# H07 · Verify the hardened run and return the evidence

**Read** · [Release checklist](../round1_prompts/13_release_verification.md), [audit](../ROUND1_HARDENING_AUDIT.md).

**Inputs** · Active run, source code and config, validation records, official or provisional top-ten exports.

**Deliver** · Release status, independent clean-run checks, rerun command and concise model evidence by role.

## Implementation prompt

```text
Run focused regression tests and a full clean CLI run in an isolated directory. Compare deterministic core outputs with the active run under identical source, config, input fingerprints and seed. Allow deliberate run IDs and timing metadata to vary. Check that an intentional source or config change invalidates the affected artifacts and that unchanged inputs reuse cached work. Keep old snapshots intact. Tie test inputs to the active run or independently verified fixtures so a previous artifact cannot pass a new release.

Close each audit defect with the exact observed test or mark it open and route to its owner. Independently recompute at least one match-weighted Brier value, one paired forecast-loss value, the evaluated top-ten selection for both roles, and one real impact replay per role. Confirm the assessed candidate and production fit identities agree and that the score, mean and interval come from one prediction record. Verify raw hashes, match and player sample scope, source lanes, eligibility, 2026 assessment labeling, and absence of any fixed favorable statement. Report the numbers of assessable picks alongside their outcomes.

Return the exact clean-run command, per-role candidate decision, measured comparison, output paths, status, and any unresolved data or form evidence. Verified requires predictive evidence under the frozen protocol, reproducibility and both lists having ten distinct confirmed dropdown choices in the right order. A reproducible exploratory result is provisional. If only dropdown evidence changes later, reuse the validated fit and regenerate the filtered exports. The entrant owns the final reasoning, report and submission.

PASS -> STOP_VERIFIED | All scientific, reproducibility and form checks passed.
FAIL -> round1_hardening/00_recovery.md | Repair input isolation, fingerprints or run reuse.
FAIL -> round1_hardening/01_cricket_ledger.md | Repair state or attribution evidence.
FAIL -> round1_hardening/02_temporal_reference.md | Repair a temporal or reference defect.
FAIL -> round1_hardening/03_model_parity.md | Repair forecast, scoring or model-dispatch parity.
FAIL -> round1_hardening/05_transfer_stability.md | Repair transfer, ranking assessment or sensitivity evidence.
FAIL -> round1_hardening/06_explanations_exports.md | Repair identity, output order or evidence references.
FAIL -> round1_hardening/07_release.md | Repair a verification issue owned by the release stage.
BLOCKED -> STOP_PROVISIONAL | Run reproduced and eligibility is unresolved. Resume at round1_hardening/06_explanations_exports.md after obtaining form evidence.
BLOCKED -> STOP_PROVISIONAL | Predictive evidence is inconclusive. Resume at round1_hardening/05_transfer_stability.md only when new valid evidence or a documented correction is available.
BLOCKED -> STOP_BLOCKED | No defensible, reproducible output exists. Record the failed check and its exact owning prompt.
```
