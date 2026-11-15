# R01 · Repair pressure coverage and chronology

**End goal** Verify that pressure labels represent difficult cricket situations and that every feature and reference is available at the time claimed.

```text
Read round1_release_review/01_cricket_data.md and round1_release_review/02_temporal_target.md for the prior rules and contracts. Work from the RR event ledger and verified match conditions. Keep exact, approximate and excluded evidence lanes separate.

Loop: define the cricket situation -> rebuild time-safe features -> replay anchor and contrast cases -> falsify.

1. Build a reproducible EDA and transformation ledger from all six CSVs. Check schemas, grains, aliases, team/season/tier keys, date coverage, event order, missing deliveries, duplicate XIs, identity conflicts and join cardinality. Use canonical IDs, numeric event order and documented exclusions. Preserve unknowns, derive legal-ball, score, wicket and phase state into a new table, and keep raw-to-derived row keys. Quantify how many fixtures, events, players and fit opportunities survive each step by year, tier, innings, phase, role and venue support. Show ordinary versus pressure coverage and concentration, with a named audit column for any denominator or proxy change.
2. Freeze an anchor set across seasons, leagues, innings and phases before recomputing ranks. Include a difficult first-innings recovery, a close chase, a low-stress chase and strong/weak spells from multiple players. Reconcile fixture 40759 and the official 73-run innings, preserving any discrepancy in balls faced. Reconcile Sooryavanshi's 776 IPL 2026 runs, the 39 excluded for a revised fixture, and his two playoff anchors 50943 and 50944. Show state, threshold, flags and runs/legal-ball coverage for each anchor. Use the replays as coverage checks under a common rule. Verify extras and wicket accounting, including fixtures 13511 and 14101.
3. Compare a transparent cricket benchmark with calibrated leverage. Cover first-innings resource stress against a past-only par and chase leverage with the known target or labelled off-bat proxy. Test continuous leverage weights as a sensitivity to the cliff at the current percentile. Calibrate on earlier dates. Measure match-weighted Brier/log loss, scenario coverage and score sensitivity to missing extras by innings, phase and tier. Keep excluded fixtures out of active pressure labels and examples. When using hypothetical state changes, ensure legal balls, illegal balls, free hits, terminal states and wickets evolve consistently.
4. Replace match-modulo reference construction with strict time blocks. For each block, only earlier matches may fit context priors, player roles, opponent/venue strength, run and wicket reference values, pressure models and cutoffs. Shift player history by date before merging it into E's training rows. Verify no future or same-match contribution to history. Use a documented warm-up prior or explicit exclusion and record support. Supply required context columns explicitly. Treat missing dated sources as errors or documented unknowns.
5. Freeze the common forecast target and keys. Keep the observed pressure outcome and model features separate. Test that changing a match outcome or workload cannot change inputs to its forecast, and that changing any later block cannot change earlier pressure labels or historical features. Track when each source and feature first becomes available. Emit dated data and feature manifests so all later stages know the exact tables to use.

Gate: the raw-to-derived counts reconcile, the transformations and denominators replay, match anchors and ordinary contrasts reconcile within documented limits, the proxy lane is explicit, and temporal mutation tests pass. A player's resulting rank cannot determine a pass.

PASS -> round1_rank_validation/02_fit_contract.md
FAIL -> repeat R01 for event, pressure or timing issues. Route source corruption to round1_rank_validation/00_reproduce.md.
BLOCKED -> STOP_BLOCKED with the unsupported target or evidence lane. Resume at round1_rank_validation/01_pressure_and_time.md. Continue on a validated proxy lane if the gate can be met with that limitation disclosed.
```
