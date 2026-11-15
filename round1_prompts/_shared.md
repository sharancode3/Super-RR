# Shared execution contract

Read once per coding-agent context. Use with the active stage prompt and current checkpoint. After a context reset, reload this file, the checkpoint, and the active prompt.

## Execute and redirect

1. Resolve prompt paths from the project root. Check only the active stage's declared inputs and prior evidence. Read the data contract when the stage links to it.
2. Make the smallest in-scope change. Run focused checks, inspect results, and save output paths and evidence. Keep the supplied RR files read-only and local.
3. Update the checkpoint before following a redirect. Use the outcome matching the evidence and choose the earliest owning stage when multiple failures apply. Finish independent work where possible. Honor named fallbacks only after checking their conditions.
4. A repair invalidates only stages that consumed changed outputs or configuration. Reuse completed stages with matching fingerprints and evidence. Follow the normal forward sequence through affected stages until reaching the stage that requested the repair.
5. Retry a failed check only after a specific change or new evidence. After two unchanged failures with the same signature, use the documented BLOCKED fallback or record STOP_BLOCKED. A stopped run resumes when its blocker changes. Avoid re-running an expensive fit for eligibility-only changes.

## Checkpoint and status

Keep `round1_progress.json` inside the active output directory. Use the active dispatcher's output directory and preserve historical checkpoints. The current [hardening dispatcher](../ROUND1_HARDENING_PLAYBOOK.md) uses `artifacts_hardened`. Include next_prompt, resume_prompt if stopped, release_status, repair_origin when returning to an earlier stage, and stage records. Each record includes status, input, source/config and output fingerprints, output paths, command, verification evidence, open issues and retry signature when relevant. Keep detailed logs in the run directory. Update the checkpoint atomically after checks and verify fingerprints before reuse.

PASS means the stage's checks succeeded. FAIL means a specific repair is needed. BLOCKED means follow a validated fallback or use the named stop. A provisional release may have a fully reproducible backend and outstanding eligibility or data limitations. STOP_VERIFIED, STOP_PROVISIONAL, and STOP_BLOCKED are terminal outcomes for the current run.

## Model and evidence gates

- Favor the simplest implementation that passes the cricket, statistical and reproducibility checks. Judge work by the evidence it produces. Reuse existing code and cache matching folds. Add complexity only for a measured deficiency, with a comparison that could show the change made results worse.
- A reproducible seed and predeclared constants such as the forecast quantile are part of the protocol. Learn model parameters, peer expectations and fitted probabilities from the eligible training rows. Generate model choice, reported metrics, player ranks, replay evidence and gate status from the run. Keep genuine missing values visible. A literal expected value belongs in a test only when it follows from known arithmetic or verified source evidence.
- Before marking a stage PASS, record each applicable acceptance check and its observed result, with the command or artifact path. Record the sample scope, unit, source lane and fit cutoff where relevant. A file existing, matching a schema or hashing consistently is insufficient evidence for scientific validity. Record why a check is inapplicable. If a required check is unavailable, follow the stage's BLOCKED route.
- Make tests discriminate. Show that the check rejects the known defect or fails under a targeted perturbation, then passes on the repaired behavior. Later outcomes must leave earlier fits unchanged. A meaningful change to earlier training data or a selected fit must propagate to the affected prediction and report. Isolate perturbation tests from the raw files and release outputs.

## Fixed definitions

| Decision | Specification |
| --- | --- |
| Official output | Ten ordered batter selections and ten ordered bowler selections, each distinct within its list. The required PDF or PPTX and Unstop selections agree with the release snapshot. See the [organizer requirements](rules_contract.md#organizer-requirements) for entrant ownership and data restrictions. |
| Prediction target | Future context-adjusted impact conditional on a player receiving high-pressure opportunities in a supported role. It is a forecast of execution, with auction eligibility and squad fit tracked separately. |
| Match state | The scoreboard and information known immediately before the delivery. State may include balls and wickets remaining, score, chase target where verified, venue, tier, and earlier history. |
| High pressure | Primarily high pre-ball leverage in competitive states. Track a side's recovery difficulty separately. A first-innings scoring-resource proxy is allowed if first-innings win probabilities fail validation. |
| Player quality | Net run-equivalent impact above a comparable peer. A wicket's value varies with state. Use separate batting and bowling attribution. Positive always benefits the player. |
| Player lift | The estimated change from a player's ordinary level in comparable contexts. Standardize ordinary and pressure samples on common role and phase support. Mark weak overlap. |
| Reliability | The 25th percentile of future match-level pressure impact, expressed per 12 legal-ball equivalents and standardized to a declared role workload. Export the mean and uncertainty separately. |
| Scope | Fit and evaluate on supplied RR matches. Use verified public sources to cross-check the same fixtures or enrich their observed state, with distinct provenance. Keep synthetic unit-test records out of all model data. Preserve the entrant's review before any final submission. |
| Eligibility | Keep statistical eligibility separate from the live batting and bowling dropdowns. An all-rounder may appear in both lists only if both live pools and the organizer rules allow it. Keep unverified names provisional. |

## Build layout

```text
Read-only RR pack + optional verified public match snapshots
 -> raw contract and identity audit
 -> exact scoreboard ledger + independent RR-only ledger
 -> exploratory summaries + locked date folds and reference tasks
 -> pre-ball pressure + held-out peer expectations
 -> batter and bowler match-level impact
 -> reliability model + three-candidate backtest
 -> frozen rankings, evidence, terminal output, and release manifest
```

Use one Python package named `rr_pressure`, one documented configuration, and a single CLI. Keep source code, generated outputs, public caches, and raw proprietary inputs separate. Prefer the existing Python, pandas, NumPy, SciPy, and scikit-learn installation for the core. Use pytest for the specific data, leakage and ranking regressions below. CatBoost is optional until the approved environment can install it. If unavailable, benchmark scikit-learn histogram gradient boosting on the same features and record the substitution. Use CSV and JSON for the user-facing exports. Add a local columnar cache only if profiling shows the CSV pipeline benefits.

Proposed entry point for the hardening pass after implementation

```powershell
python -m rr_pressure run --raw-dir .\6af3166e7b922_data_pack --out-dir .\artifacts_hardened --seed 2027
```

Support an audit-only run and a fresh run with optional `--public-dir`. Record input hashes, public download source and date, code version or source fingerprint, configuration hash, model library versions, seed, and date bounds. Make a run resumable from verified artifacts, invalidating downstream steps when upstream inputs or configuration change. Write each run into a new run directory and publish a release manifest only after acceptance. Do not depend on notebook execution order or remote services for a rerun with cached inputs.
