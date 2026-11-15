# SupeRR Selector Season 2

## Round 1 · Identify the Most Reliable Players Under Pressure

This dispatcher starts or resumes the terminal-first model build in the RR workspace. The target is two ordered top-10 lists, a chronological model comparison, and evidence for every pick. The report, dashboard, and submission follow as separate work.

**Current workspace entry** · Read the [decision audit](ROUND1_DECISION_AUDIT.md) and follow the [decision validation dispatcher](ROUND1_DECISION_PLAYBOOK.md) from [A01](round1_decision_validation/01_fix_and_falsify.md). Preserve `artifacts_rank_validation` as the comparison snapshot. The route below is the original rebuild reference.

## Original rebuild only

1. Read the [shared execution contract](round1_prompts/_shared.md) once.
2. For a replay of the original repair, open the [original recovery gate](round1_prompts/recovery_gate.md). The existing `artifacts_revalidated/round1_progress.json` documents that run.
3. For a genuinely fresh workspace with no audited legacy outputs, open [Stage 00](round1_prompts/00_project_contract.md).
4. Read the active prompt and only the references it names. Run it, record the gate result, and open the exact file named by its redirect. Repeat until a STOP outcome.

## Master prompt for the coding agent

```text
Implement SupeRR Selector Season 2, Round 1, in the current RR workspace. Use this dispatcher, the shared contract, and one stage prompt at a time. Keep the supplied data read-only and local. Use actual acceptance evidence to advance and the checkpoint to resume. Deliver the reproducible terminal rankings, comparison, and evidence before any presentation work.

START -> ROUND1_DECISION_PLAYBOOK.md, then round1_decision_validation/01_fix_and_falsify.md for the current workspace. The original rebuild below is a historical reference.
```

## Prompt map

| Stage | Open |
| --- | --- |
| 00 | [Establish the project contract](round1_prompts/00_project_contract.md) |
| 01 | [Ingest and reconcile identity](round1_prompts/01_ingest_identity.md) |
| 02 | [Establish exact and proxy ball ledgers](round1_prompts/02_scoreboard_ledgers.md) |
| 03 | [Explore distributions and pressure opportunity](round1_prompts/03_exploratory_analysis.md) |
| 04 | [Freeze folds, reference outcomes, and selection rules](round1_prompts/04_freeze_evaluation.md) |
| 05 | [Train and calibrate match-state models](round1_prompts/05_match_state_models.md) |
| 06 | [Identify pressure before the delivery](round1_prompts/06_pressure_definition.md) |
| 07 | [Convert runs and wickets into player impact](round1_prompts/07_player_impact.md) |
| 08 | [Fit the reliability forecast](round1_prompts/08_reliability_forecast.md) |
| 09 | [Compare the three model candidates](round1_prompts/09_model_comparison.md) |
| 10 | [Challenge the shortlist before freezing names](round1_prompts/10_robustness_checks.md) |
| 11 | [Produce rankings and separate eligibility](round1_prompts/11_rankings_and_eligibility.md) |
| 12 | [Print the results and export the evidence](round1_prompts/12_terminal_exports.md) |
| 13 | [Verify reproducibility and hand back](round1_prompts/13_release_verification.md) |

Open the [input data contract](round1_prompts/data_contract.md) and [rules contract](round1_prompts/rules_contract.md) only when the active stage calls for them. [Stage 13](round1_prompts/13_release_verification.md) contains the evaluator-facing release checklist. [Earlier model research and pilot findings](ROUND1_BACKEND_PLAN.md) are available for reference. Use the stage prompts as the implementation authority.
