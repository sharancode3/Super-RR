# Stage 10 · Challenge the shortlist before freezing names

**Inputs** · Frozen model decision, 2025 validation and 2026 assessment, candidate support tables.

**Checkpoint records** · 02, 06, 08, 09.

**Outputs** · Sensitivity grid, rank intervals, weak spots by role and cohort, robustness decision.

## Implementation prompt

```text
Evaluate robustness to pressure percentiles, alternative recovery thresholds, IPL-only versus pooled evidence, exact versus proxy states on the same fixtures, with and without emerging-team evidence, and narrower or wider workload rules. Use prespecified ranges and report all cases. Check recent versus earlier seasons, exclusion of one standout match, and whether ranks depend disproportionately on one format or tournament. Use match-level resampling to estimate rank intervals and top-ten inclusion frequency. If runtime is limited, time a smaller seeded run first, then increase replicates until intervals are reasonably stable and record the number used.

Test that sampling a match twice gives it twice the weight, and distinguish a missing match from a zero-impact outcome. Compute every sensitivity from its refit or labeled fixed-model comparison. Record unavailable lanes as unavailable. Make sure a `rank interval` uses ranks across replicates rather than standard deviation of unranked impact rates.

Review both cutoff regions around ranks 8 to 15, ordinary-versus-pressure overlap, skill versus exposure, and the risk of rewarding tiny samples or compressing all picks into one phase. Examine aggregate residuals by competition, innings and role. Test alternative pressure schemes for role balance without forcing quota-based rankings. Publish differences as sensitivity findings. Keep official performance order on the frozen method.

Record any substantial sensitivity as a limitation or a provisional flag. Fix reproducible data or math bugs at the originating stage. Keep exploratory improvements separate from final holdout evidence. Never rerank because a favored name moved.

PASS -> round1_prompts/11_rankings_and_eligibility.md | Publish sensitivity, uncertainty, and borderline rank evidence.
FAIL -> round1_prompts/02_scoreboard_ledgers.md | Repair invalid exact or proxy states.
FAIL -> round1_prompts/06_pressure_definition.md | Repair pressure definition or cutoff implementation.
FAIL -> round1_prompts/07_player_impact.md | Repair impact scoring.
FAIL -> round1_prompts/08_reliability_forecast.md | Repair reliability estimation.
FAIL -> round1_prompts/09_model_comparison.md | Repair evaluation integrity.
FAIL -> round1_prompts/10_robustness_checks.md | Repair the sensitivity or rank-interval calculation.
BLOCKED -> round1_prompts/11_rankings_and_eligibility.md | The evaluation is sound and unstable or unsupported cases are marked provisional.
BLOCKED -> STOP_BLOCKED | A core evaluation defect remains without a validated fallback. Resume at round1_prompts/10_robustness_checks.md once its owner is repaired.
```
