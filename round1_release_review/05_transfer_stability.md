# I05 · Test IPL transfer and rank stability

**End goal** Show which shortlist claims survive a change in context, support or a single fixture, using the same estimator within each comparison.

```text
Open the frozen I04 protocol. Use rr_pressure/robustness.py and the shared candidate interface. Treat all transfer and stress scenarios as explicitly named comparisons with their own fit and target identities. Keep runtime under control using shared keyed feature blocks and small fixed smoke samples before the complete calculation.

Loop: lock reference -> perturb one decision -> rerun the same estimator -> measure changes -> audit uncertainty.

1. On identical later IPL match-player keys, compare an IPL-only fit with pooled and, if supported, a partially pooled league adjustment for the selected family. Use the same evaluation reference labels. Partition direct IPL evidence, common IPL history, new-to-IPL players, sparse categories and opportunity coverage. Report exact counts and paired differences with match-block uncertainty. Use only past results for opponent strength or venue effects, and label poorly supported contexts. If group support is thin, shrink effects or present the subgroup descriptively.
2. Reproduce the production baseline rankings byte-for-byte at the same cutoff, target, context, candidate and tie-break before changing a factor. Test the predeclared pressure-percentile range, strict workload floor, removal of emerging competitions, and one-match deletion. For pressure changes, rebuild the affected labels and downstream fits coherently. For venue or role scenarios, use common support and a documented historical RR/IPL mix frozen before ranking. If using a mixture of predicted distributions, derive the Q25 from the mixture CDF or pooled simulated draws. Report an average of scenario scores only as an explicitly different score. Separate domain shifts from estimator comparisons.
3. Resample whole matches or appropriate season blocks, preserve multiplicities, rerun the selected estimator and rank the eligible universe. Measure top-ten inclusion, rank range and the margin between ranks 8 through 15. Calculate fixture concentration as largest single-match pressure-ball share and optionally effective match support from match weights. Test known fragile cases, including the old Sufiyan six-match profile with 24 of 52 pressure balls from one fixture. Confirm the code recomputes fits rather than attaching B/B0 intervals to E. Disclose which upstream models were fixed versus refit. Give Monte Carlo uncertainty or increase draws until the precision is useful.
4. Build a compare-with-reserve stress table using only paired runs and verified player evidence. Separate base rank, real matches observed, IPL support, leave-one-out effect and most influential support gap. Publish scenario disagreements, even when a high-ranked player looks fragile. Choose any simpler fallback only under the predeclared I04 rule using valid earlier-window evidence. Never use a favorite player's rank as the revision rule.

Gate: independent baseline rank parity, matched IPL key sets, dated features and fair comparisons, actionable uncertainty for near-cutoff players, and an evidence-bounded domain-transfer statement. Low transfer support is a valid measured result.

PASS -> round1_release_review/06_shortlist_reality.md
FAIL -> repeat I05 for mixed estimators, weights or scenarios. Redirect a scoring-interface error to round1_release_review/03_model_evidence_parity.md. Redirect any predeclared model fallback or protocol revision to round1_release_review/04_train_select.md.
BLOCKED -> STOP_PROVISIONAL only if required stress evidence cannot be reproduced. Record the missing component and resume at round1_release_review/05_transfer_stability.md. Report sparse but valid support and continue.
```
