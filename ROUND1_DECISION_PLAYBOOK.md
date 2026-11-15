# SupeRR Selector Season 2 · Model and auction decision review

Read [the latest audit](ROUND1_DECISION_AUDIT.md), the [original brief](<6af3166e7b922_data_pack/Round 1 Problem Statement _ SupeRR Selector Season 2.docx.pdf>) and the [rules contract](round1_prompts/rules_contract.md). Start at [A01](round1_decision_validation/01_fix_and_falsify.md). The saved R run is the comparison baseline. Use the original six CSVs and the existing Python pipeline. Keep past runs and the raw pack intact. Write to a new `artifacts_decision_validation` directory.

| Stage | Prompt | PASS redirect |
| --- | --- | --- |
| Fix A01 | [Reopen false passes and repair acceptance](round1_decision_validation/01_fix_and_falsify.md) | A02 |
| Improve A02 | [Repair and measure the data and pressure target](round1_decision_validation/02_data_and_target.md) | A03 |
| Improve A03 | [Train and compare forecasts and top-ten decisions](round1_decision_validation/03_train_for_decisions.md) | A04 |
| Improve A04 | [Stress test rankings and evaluate RR options](round1_decision_validation/04_stress_and_auction.md) | A05 |
| Improve A05 | [Rebuild and stop for review](round1_decision_validation/05_review.md) | STOP |

Execute one stage at a time. Reproduce the failure, make the smallest relevant change, run a falsifying check, inspect real outputs and record the evidence. Advance on PASS, route a failure to the owning stage, and stop with the exact missing input or evidence on BLOCKED. Continue scientific work with explicit unknown auction fields where the official inputs are missing. Keep assessment cutoffs, fits, predictions and public evidence dated and separate. Report design, dashboard work and submission are later.

## Start prompt for the agent

```text
Work in C:/SHARAN PROJECTS/rr on SupeRR Selector Season 2, Round 1. Read ROUND1_DECISION_AUDIT.md, ROUND1_DECISION_PLAYBOOK.md, the original brief and the rules contract. Start at round1_decision_validation/01_fix_and_falsify.md even if R05 shows PASS. Preserve the six raw CSVs, brief and earlier runs. Write new results to artifacts_decision_validation.

Execute A01 through A05 one file at a time. In every stage reproduce the issue, correct it, run the original failing check and a passing contrast, inspect actual results, and log the command, evidence and next route. Never make a particular player's rank, model family or successful result a test requirement. Follow the exact redirect on PASS, FAIL or BLOCKED.

Repair chronological data provenance and measure how the pressure definition changes real coverage. Compare a cricket baseline, B0/B1, a support-aware distributional challenger and a time-safe quantile booster on identical dated rows. Select by role using forecast and actual top-ten utility, with IPL-specific evidence and uncertainty. Keep 2026 retrospective. Keep statistical ranks, verified role-specific form eligibility and RR auction options separate. Support every numeric, roster, and tactical claim with measured or dated official evidence. Use conditional scenarios for unverified costs or slots and unknown statuses for unverified availability. Finish with two audited terminal shortlists, auction decision cards, metrics, uncertainty and reproduction commands. Stop at backend review.
```
