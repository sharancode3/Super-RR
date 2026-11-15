# R05 · Rebuild and deliver the review outputs

**End goal** Verify that fresh runs and independently calculated evidence agree, then stop for entrant review.

```text
Use the R00–R04 checkpoints and two new output directories. Run the normal backend entry point from the seven-file data pack in the same recorded environment. Keep previous snapshots protected. Use the same frozen configuration and optional verified form mapping in both runs.

Loop: rebuild from raw -> verify artifact identity and meaning -> repair or stop.

1. Run the full test suite with output isolation. Replace tests that merely demand a predetermined winner with tests of the frozen decision rule, input timing, exact assessed keys, candidate dispatch, and outcome arithmetic. Make replay fixtures exercise the original failures. Check original and historical hashes again.
2. Rebuild twice. Create a content-based run and snapshot identity from input, code, cutoff, configuration and output contract. Record the complete set of required output hashes. Verify equivalent scored rows, Q25, ordered IDs, and evidence under deterministic seeds and stable ordering. Document only genuine differences such as machine-specific metadata. Forecasts should come from training on real observations. Reproducibility means the same evidence and configuration reproduce the same result.
3. Recompute a pressure label, a batting and bowling match impact, a selected candidate's loss and coverage, and the backtested top-ten metric per role from their actual rows. Confirm the historical and final fit identities differ when their dates differ. Report diagnostic versus verified status from the evidence, and show the exact prompt to resume for unresolved issues.
4. Return two ordered performance lists in the terminal with model used, matched usual-versus-pressure comparison, fit support and uncertainty. Export the form checklist and the dated RR auction decision notes as separate evidence tables. Include match replays, model comparison, IPL transfer and rank sensitivity tables, exact CLI commands and open issues. Verify that any reported rank, date, auction status or tactical claim traces to its declared source. If form options or auction availability are unknown, show that status and proceed only to backend review. The entrant decides the final selections. Stop here for review.

Gate: both independent rebuilds and meaning checks pass, test writes stay isolated, the three outputs agree on IDs without conflating their purposes, and every factual claim comes from scored data or a verified dated source.

PASS -> STOP_BACKEND_REVIEW. Keep the two lists provisional until entrant review and form eligibility checks.
FAIL -> follow the owning prompt. Use round1_rank_validation/00_reproduce.md for integrity, round1_rank_validation/01_pressure_and_time.md for cricket or leakage, round1_rank_validation/02_fit_contract.md for scoring, round1_rank_validation/03_select_models.md for selection, or round1_rank_validation/04_rank_evidence.md for robustness and evidence. Repeat R05 for rebuild mechanics.
BLOCKED -> STOP_BLOCKED with the failed verification and exact owning prompt. Pending eligibility cannot mask an unresolved model defect.
```
