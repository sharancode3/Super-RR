# H05 · Measure IPL transfer, stability and the value of pressure

**Read** · [Robustness specification](../round1_prompts/10_robustness_checks.md), [selection contract](../round1_prompts/09_model_comparison.md).

**Inputs** · Repaired and challenger forecasts on earlier rolling assessment windows, versioned reference, chosen workload and cohort.

**Deliver** · Paired comparison, rank robustness, frozen selection per role and labeled retrospective 2026 result.

## Implementation prompt

```text
Evaluate IPL-only and pooled IPL/T20I training for each serious candidate using exactly the same held-out IPL player-match keys and reference values. Report unmatched player and match-row coverage separately. Add emerging-team data as a separate sensitivity. Compare tier offsets or hierarchical transfer against equal pooling. Fit strength or era effects on earlier matches and show where transfer is unsupported. Reject extrapolation into unobserved tactical roles. Test against recent IPL opposition or phase subsets only where support is adequate.

Assess role-specific pinball loss, Q25 calibration, mean bias, top-ten coverage and realized impact for each candidate's own historical order. Compute pinball as max(0.25*(y-q), -0.75*(y-q)), with the same weights and workload for paired models. Resample whole matches with multiplicity and use the same sampled weights on all candidates. Report paired intervals and practical differences. Use a seeded pilot and increase replicates until relevant bounds are stable. Avoid using the number of balls as the number of independent matches.

Rebuild both pressure and ordinary exposure from the same event ledger when testing 15%, 20%, and 25% cutoffs. Compare first-innings versus chase, exact versus proxy on matching fixtures, different workload floors, removal of one influential match, and unsupported opposition strata. Repeat selection or refit only where the experiment definition requires it. Label fixed-model sensitivity separately. Calculate rank bands and top-ten frequency from the selected recipe, and examine the boundary around ranks 8 to 15. Test whether personal pressure lift improves prediction beyond usual skill. If weak, retain a descriptive pressure comparison with support and uncertainty.

Lock the candidate decision by role from the earlier rolling folds and persist the manifest before computing the repaired 2026 assessment. Follow the predeclared practical margins and calibration gates. A larger model can win when it improves the target consistently. A simpler model can win when the added effect is weak. Allow an inconclusive outcome where gates are unmet. Score the frozen 2026 lists with their own rankings and clearly label the outcomes previously inspected. Report any poor shortlist evidence alongside improvements. Keep the final full-history refit and its new ranks distinct from historical predictions.

PASS -> round1_hardening/06_explanations_exports.md | The selection and retrospective assessment are coherent and traceable.
FAIL -> round1_hardening/02_temporal_reference.md | Repair opportunity masks, transfer provenance or chronology.
FAIL -> round1_hardening/03_model_parity.md | Repair candidate scoring or selection and refit mismatch.
FAIL -> round1_hardening/05_transfer_stability.md | Repair the sensitivity computation or matched comparison.
BLOCKED -> round1_hardening/06_explanations_exports.md | The run is reproducible and predictive evidence is weak. Carry an explicit exploratory status and the measured results.
```
