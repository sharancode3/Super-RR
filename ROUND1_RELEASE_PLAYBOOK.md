# SupeRR Selector Season 2 · Round 1 backend release review

**Historical route.** The current `artifacts_release_review` run is the comparison input for the [rank validation dispatcher](ROUND1_RANK_PLAYBOOK.md). Start there for the next coding pass.

**Project root** `C:/SHARAN PROJECTS/rr`  
**Scope** Repair and validate the model first. Deliver terminal rankings and reproducible evidence for ten batters and ten bowlers. Report design, dashboard development and submission are later work.

## Run the loop

1. Read [the release audit](ROUND1_RELEASE_AUDIT.md), the [rules contract](round1_prompts/rules_contract.md) and the applicable workspace instructions once. Open only the active prompt and the references it needs. Start with [F00](round1_release_review/00_reproduce.md) even if an older checkpoint shows H07 PASS.
2. Read the stage's end goal and gates. Record a reproducer or baseline. Make the smallest relevant change, run the indicated failing and passing cases, inspect actual outputs, and rerun only the affected dependencies. Keep iterating while there is a concrete, testable correction. If retries produce no new evidence, record the blocker and the exact resume prompt.
3. Write a release review checkpoint inside the new run with stage ID, status, input and upstream artifact hashes, code/config fingerprint, command and environment, observed metrics and test results, open issues, and next prompt. Use `PASS` only when all current gates are evidenced. On a failed upstream gate, invalidate downstream results tied to its fingerprint and follow the prompt's redirect. Continue from a checkpoint only after verifying hashes and evidence.
4. Preserve the raw pack and all prior runs. Write derived tables and caches under `artifacts_release_review` and independent rebuilds under new sibling directories. No synthetic training rows, fixed player scores, manual rank edits, or post hoc changes to favor a name. Small fabricated unit fixtures are permitted for isolated rule and leakage tests. Keep public inputs local and separately attributed. Use public records for verification unless an explicitly frozen, permitted auxiliary lane passes reconciliation and evaluation.
5. Use strict match-level time cutoffs. Keep 2026 as previously inspected retrospective evidence. Freeze the metric, folds, context and decision rule before evaluating revised 2026 outputs. Fit any final 2027 forecast after the model decision, using the exact dated cutoff in the manifest. Do not use the final fit to claim retrospective performance. Leave uncertainty and form eligibility visible.

| Order | Active prompt | Pass target |
| --- | --- | --- |
| Fix F00 | [Reproduce and preserve](round1_release_review/00_reproduce.md) | F01 |
| Fix F01 | [Reconcile cricket and audit data](round1_release_review/01_cricket_data.md) | F02 |
| Fix F02 | [Enforce information and time boundaries](round1_release_review/02_temporal_target.md) | F03 |
| Fix F03 | [Unify forecasts, metrics and evidence](round1_release_review/03_model_evidence_parity.md) | I04 |
| Build I04 | [Train, compare and select by role](round1_release_review/04_train_select.md) | I05 |
| Build I05 | [Test IPL transfer and rank stability](round1_release_review/05_transfer_stability.md) | I06 |
| Build I06 | [Verify players, RR fit and form mapping](round1_release_review/06_shortlist_reality.md) | I07 |
| Build I07 | [Rebuild and deliver terminal outputs](round1_release_review/07_release.md) | STOP |

## Start prompt for the coding agent

```text
Work in C:/SHARAN PROJECTS/rr on SupeRR Selector Season 2, Round 1, Identify the Most Reliable Players Under Pressure. Take ownership of the model backend and terminal evidence through the release gates. Read ROUND1_RELEASE_PLAYBOOK.md and ROUND1_RELEASE_AUDIT.md, then begin at round1_release_review/00_reproduce.md. Follow the exact redirect at the end of each stage, one prompt at a time. Reproduce the failed gate, fix its cause, run a falsifying regression test, inspect real outputs, record the evidence, and advance only on PASS. Use a fresh output namespace and keep the seven original pack files and all old snapshots untouched. Treat artifacts_hardened as provisional history. Separate observed match performance, forecast information available before play, statistical rankings, RR squad fit and form eligibility. Compare a cricket baseline, empirical-Bayes shrinkage with and without a pressure effect, a robust partially pooled distribution and a regularized quantile booster on identical dated evaluation rows. Select separately for batting and bowling from leakage-free error, calibration and shortlist utility. Use exact match examples and a matched scenario stress test to explain both lists. Keep the 2026 retrospective label, count and disclose missing evidence, and export the two ordered lists and model evidence from the same fit identity. Stop at the documented release outcome. No dashboard, report design or submission in this run.
```
