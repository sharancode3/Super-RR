# SupeRR Selector Season 2 · Model hardening dispatcher

**Historical route.** The current `artifacts_hardened` run is the input to the [release review dispatcher](ROUND1_RELEASE_PLAYBOOK.md). Start there for further implementation.

Use this dispatcher for the existing `artifacts_revalidated` run. Start with the [audit](ROUND1_HARDENING_AUDIT.md), then open [H00](round1_hardening/00_recovery.md). Treat both completed run directories as historical evidence. The implementation stays in `rr_pressure` and uses the original data pack as the sole training and evaluation population. Write a new run to `artifacts_hardened`.

## Execution contract

Read [the shared execution contract](round1_prompts/_shared.md) once. Use `artifacts_hardened/round1_progress.json` for this pass. Read the active stage and only its named references. Check the recorded fingerprints before reusing upstream work. Maintain one checkpoint that records defect ID, required check, command, observed outcome, output artifact, dependencies, next prompt and any resume condition. Use source, configuration and input hashes to identify a run. Keep actual metrics with the run that produced them.

Complete H00–H03 before considering model upgrades. H04–H05 compare candidates and stress the best supported approach. H06–H07 produce and verify evidence. At each stage, run the smallest check that can falsify the change, then record the result. A measured failure of an optional challenger is a valid result. Follow the file's exact route for fixes or blockers. Retry only after a specific change or new evidence. Stop with the strongest honest output when a dependency or lack of validation prevents release.

| Stage | Prompt | Main gate |
| --- | --- | --- |
| H00 | [Preserve and reproduce](round1_hardening/00_recovery.md) | Isolated output and regression evidence |
| H01 | [Repair the cricket ledger](round1_hardening/01_cricket_ledger.md) | Verified score lane or honest proxy |
| H02 | [Rebuild historical features and the reference](round1_hardening/02_temporal_reference.md) | Fit cutoff, shared target, valid pressure and wicket value |
| H03 | [Fix candidate and export parity](round1_hardening/03_model_parity.md) | The evaluated, refitted and exported model agree |
| H04 | [Train research-backed challengers](round1_hardening/04_challengers.md) | Paired comparison of uncertainty and ranking quality |
| H05 | [Test IPL transfer and stability](round1_hardening/05_transfer_stability.md) | Selection on evidence and a frozen chronological assessment |
| H06 | [Produce reviewable rankings](round1_hardening/06_explanations_exports.md) | Every number and claim traces to its source |
| H07 | [Verify and hand off](round1_hardening/07_release.md) | Reproducible run and accurate release status |

## Start prompt

```text
Implement the Round 1 model hardening pass in C:\SHARAN PROJECTS\rr. Read ROUND1_HARDENING_AUDIT.md, this dispatcher and round1_prompts/_shared.md. Start at round1_hardening/00_recovery.md or the earliest invalidated stage in a verified artifacts_hardened checkpoint. Repair the audited defects before training challengers. Fit and evaluate on the supplied RR matches. Use public records only to corroborate or enrich those matches. Keep raw files and previous outputs intact. At each stage run the acceptance checks, record actual evidence, and follow its exact PASS, FAIL or BLOCKED redirect. Finish with the verified or provisional terminal and ranked evidence exports, the model choice by role and the reproducible CLI command.
```
