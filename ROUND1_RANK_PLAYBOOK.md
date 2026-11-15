# SupeRR Selector Season 2 · Rank validation and correction

**Historical route.** The completed R run is the comparison input for the [decision validation dispatcher](ROUND1_DECISION_PLAYBOOK.md). Start there to address the defects found after R05.

Work in `C:/SHARAN PROJECTS/rr`. Read the [rank audit](ROUND1_RANK_AUDIT.md), the [Round 1 brief](<6af3166e7b922_data_pack/Round 1 Problem Statement _ SupeRR Selector Season 2.docx.pdf>) and the [rules and output contract](round1_prompts/rules_contract.md). Start at [R00](round1_rank_validation/00_reproduce.md). Prior F00–I07 reports are historical evidence. Use the six supplied CSVs, the existing Python pipeline, and new local outputs under `artifacts_rank_validation`. The audit rebuild `artifacts_forecast_audit_20261111` records the limited code corrections already made.

Deliver two ordered pressure-performance rankings, a separate Unstop form-entry checklist, and RR auction decision notes. The review outputs must explain a player's usual performance, matched performance under pressure, reliability, evidence strength and concrete RR deployment. Statistical rank, form eligibility, dated roster membership and 2027 auction availability are separate facts. Require canonical data keys or a dated official source for every material claim.

| Order | Prompt | Gate after PASS |
| --- | --- | --- |
| Fix R00 | [Freeze and reproduce](round1_rank_validation/00_reproduce.md) | R01 |
| Fix R01 | [Transform and audit cricket data, then repair pressure coverage and chronology](round1_rank_validation/01_pressure_and_time.md) | R02 |
| Fix R02 | [Specify batting and bowling impact, and repair reliability and fit parity](round1_rank_validation/02_fit_contract.md) | R03 |
| Build R03 | [Compare and select models by role](round1_rank_validation/03_select_models.md) | R04 |
| Build R04 | [Stress test ranks, verify evidence and build RR decision notes](round1_rank_validation/04_rank_evidence.md) | R05 |
| Build R05 | [Rebuild and deliver review outputs](round1_rank_validation/05_review_gate.md) | STOP |

Use one prompt file at a time. Follow its exact redirect after a gate is evidenced. Reproduce the issue, fix its cause, run the smallest falsifying check, inspect the output, and record commands, dependencies, hashes, measured values, open issues, and the exact next prompt. Cache by input, code, configuration and cutoff, and invalidate downstream work after an upstream fix. Keep the raw pack and previous snapshots intact. An old pass cannot close a newly observed defect. A blocked dependency must name the required evidence and its owning stage.

## Start prompt for the agent

```text
Work in C:/SHARAN PROJECTS/rr on SupeRR Selector Season 2, Round 1. Read ROUND1_RANK_AUDIT.md, ROUND1_RANK_PLAYBOOK.md, the original brief in 6af3166e7b922_data_pack and round1_prompts/rules_contract.md. Execute round1_rank_validation/00_reproduce.md first. Use the original six CSVs and existing rr_pressure code. Preserve the raw pack and earlier outputs. Write derived data, fitted evidence and checkpoints to artifacts_rank_validation. Keep proprietary data local.

Follow R00 -> R01 -> R02 -> R03 -> R04 -> R05. Open only the current stage and its required references. In R00, reproduce the existing results and freeze the evidence. In R01, profile each table and reconcile identity, chronology, scoring and exclusions. Build separate pre-ball pressure and past-only player histories. In R02, freeze the batting and bowling targets, usual-performance comparisons, actual fit support, uncertainty and ranking contract. In R03, compare the cricket baseline, B0/B1 shrinkage, support-aware D and regularized quantile booster E on identical dated rows. Choose separately by role using calibration, paired forecast error, actual later top-ten outcomes and supported IPL context. Keep the already-inspected 2026 results retrospective.

In R04, rerun the selected fit for stress tests. Trace every example by player and fixture IDs. Use Sooryavanshi, Suryakumar and Rajapaksa to test data coverage, chronology and sample sensitivity. Apply the same rules to all players and let the models determine the order. For the auction notes, compare each pick with a dated RR incumbent or an explicitly conditional role need. Store roster season, verified 2027 availability and role-specific dropdown evidence separately. Unknown availability stays unknown. Use only verified form options for a verified form list, and keep any unresolved mapping provisional.

In R05, rebuild twice in fresh output directories and reproduce the arithmetic, model identities and ranks. Return the two terminal top tens, the separate form checklist, dated RR auction decision notes, the supporting evaluation and exact commands.

For each stage, reproduce the defect, implement the smallest complete correction, run the failing and passing cases, inspect real outputs and log commands, fingerprints, observed evidence and the next prompt. Follow the exact stage redirect on PASS, FAIL or BLOCKED. A claim with no traceable source is unknown. Never invent a match, ID, roster decision, metric or player rank. Stop for entrant review at the backend gate. Report design, dashboard and submission follow in a separate run.
```
