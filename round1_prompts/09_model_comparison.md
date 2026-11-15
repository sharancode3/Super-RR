# Stage 09 · Compare the three model candidates

**Inputs** · Frozen protocol, rule-based baseline, statistical fit, boosted fit, ablations and fold predictions.

**Checkpoint records** · 04, 05, 07, 08.

**Outputs** · Shared-cohort comparison by role and lane, 2025 selection decision, and previously inspected 2026 assessment.

| Candidate | Fit for comparison |
| --- | --- |
| A · Cricket baseline | Cricket pressure rules, historical phase and role expectations, empirical player-match impact with a role-level sparse-sample fallback. |
| B · Statistical default | Regularized state and context models, partial pooling for ordinary level and pressure effect. |
| C · Boosted challenger | Shallow calibrated boosted trees for state and context. Same reliability and opportunity definition as B in the controlled comparison. |

## Implementation prompt

```text
Fit A, B and C on identical dated folds. Compare player predictions on the same held-out reference pressure opportunities, realized impact target and evaluation cohort fixed at Stage 04. Hold the target and workload convention constant when fitting any calibration layer. For a secondary experiment compare each end-to-end pressure recipe and report how its candidate coverage changes. Test raw strike rate or economy as a descriptive benchmark and B without player pressure effects as an ablation. These explain what each added layer contributes.

Build an explicit common comparison table keyed by assessment window, role, RR match ID, and player ID. Require the same source lane, target and workload for every paired model. Compute coverage on the full candidate cohort separately, including which unique players or match rows were added. For IPL transfer, compare pooled and IPL-only losses on intersecting IPL keys for both roles and give a separate coverage count. Store enough row-level scored predictions to recompute every published aggregate. Resample match blocks with multiplicities. A membership filter that discards repeated draws is not a cluster bootstrap.

Report 25th-percentile pinball loss and empirical Q25 coverage by role. Report mean forecast error, realized average pressure impact among top-ten picks with observed future opportunities, rank correlation where coverage supports it, and top-ten membership stability. Use match-resampled paired uncertainty and show the denominator for each ranking metric. Exclude players with insufficient future opportunities from the observed-impact denominator and report their coverage separately. Never impute zero impact. Compare on held-out IPL as the main transfer check, including IPL-only versus pooled training. Show pooled, innings and competition results separately.

For observed impact y and forecast q, compute Q25 pinball loss as max(0.25 * (y - q), -0.75 * (y - q)). Report the fractions strictly below and at or below q when ties matter. Test the scorer on an independently calculated example. Use the predeclared decision rule on actual paired predictions. Test that selection can return a different valid winner when evidence changes and can return inconclusive when coverage or calibration fails.

Select per role from measured 2025 results using the predeclared calibration, quantile loss, ranking and uncertainty gates. B is a starting model, never a required winner. Allow the fitted no-player-pressure model to win if its evidence is stronger. Keep the simpler calibrated method if gains are fragile. Record the choice, candidate ID, fit configuration, metrics and reason in a machine-readable manifest. Generate the rationale from measured values. The 2026 assessment has already been inspected in the legacy run. Rerun it after the new decision is locked and report any disagreement or low coverage. Do not tune against it. If predictive evidence is inconclusive, report that status rather than certifying the ranking.

PASS -> round1_prompts/10_robustness_checks.md | Save the pre-holdout decision and final 2026 evaluation.
FAIL -> round1_prompts/04_freeze_evaluation.md | Repair unequal folds or a changed assessment reference.
FAIL -> round1_prompts/07_player_impact.md | Repair mismatched impact units or targets.
FAIL -> round1_prompts/08_reliability_forecast.md | Repair forecast defects.
FAIL -> round1_prompts/09_model_comparison.md | Repair the benchmark, metrics, or protocol execution and preserve the frozen selection rules.
BLOCKED -> round1_prompts/10_robustness_checks.md | A simpler candidate passed on the common cohort. Disclose the missing comparison.
BLOCKED -> STOP_BLOCKED | No valid common-cohort ranking evaluation remains. Resume at round1_prompts/09_model_comparison.md with the missing evidence.
```
