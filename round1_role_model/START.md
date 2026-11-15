# SupeRR Selector Season 2 Round 1

Open this file from `C:/SHARAN PROJECTS/rr`. Execute the six stage prompts in order. Build and validate the backend through entrant review. Use the normal CLI, and let the measured results determine who moves. The entrant owns the final picks and submission.

## Read the current state

- Read the [official case PDF](../6af3166e7b922_data_pack/Round%201%20Problem%20Statement%20_%20SupeRR%20Selector%20Season%202.docx.pdf) and [Unstop Round 1 description](https://api.unstop.com/hackathons/crp-superr-selector-season-2-help-shape-rajasthan-royals-ipl-2027-auction-strategy-rajasthan-royals-1792758). The expected output is two ordered lists of ten and evidence for how the players deliver under pressure and how they could help RR. The downloaded case and form are the working submission contract. Follow any newer written organizer clarification.
- Use `C:/SHARAN PROJECTS/rr/6af3166e7b922_data_pack` as read-only input. Keep all six CSVs and the case PDF available. Write transformations to a fresh run directory. Preserve the existing runs and keep the proprietary data local.
- Use [the latest saved run](../artifacts_locked_20261112/run_manifest.json), snapshot `RR_SUPE_RR_S2_657c0bd6218fd4c93839`, as the baseline to beat. Read its [comparison](../artifacts_locked_20261112/model_comparison.json), [shortlist](../artifacts_locked_20261112/rr_shortlist.csv), and [changes](../artifacts_locked_20261112/shortlist_review_changelog.csv). Its fitted batting model is D and bowling baseline is B0. The saved bowling list applies a later B0/C-IPL scouting rule, which needs its own backtest. The last polish pass kept the same 20 names.
- Treat Aniket–Porel, Salt's pressure vs ordinary powerplay, Shahrukh's older evidence, and Coetzee/Tyagi/Hazlewood/Wood/Muzarabani/Vyshak as audit cases. These names are useful tests of the pipeline. Their ranks and membership must come from measured evidence and the declared shortlist policy.

## Work loop

Create one `review_progress.md` in the new run directory. Record the input and baseline fingerprints, seed, current stage, commands and outputs, decisions, and open items. Read only the active stage and the artifacts it requires. Reuse verified computations when their inputs, code, and configuration still match. Use seed `2027` for the reproduction run.

At the end of each stage, check its exit criteria. Fix a failure at its source, rerun the smallest affected checks, then check the exit criteria again. Return to the earliest invalidated stage if a change invalidates upstream evidence. Document a measured tradeoff or a genuinely unavailable source and continue with work that the evidence supports. A weak challenger is a valid result. Avoid tuning repeatedly to obtain a preferred player or a better-looking historical metric. Advance immediately once the stage criteria pass.

1. [Freeze the baseline and evaluation protocol](01_baseline_and_protocol.md).
2. [Build and verify the role and context data](02_data_and_roles.md).
3. [Fit and calibrate the candidate models](03_fit_and_calibrate.md).
4. [Backtest the complete shortlist rule](04_replay_and_select.md).
5. [Build the current RR auction shortlist](05_rr_shortlist.md).
6. [Verify the clean run and hand off](06_verify_and_handoff.md).

Begin with **[Stage 01](01_baseline_and_protocol.md)** now. End after Stage 06 at `BACKEND_REVIEW`. The handoff is the terminal lists, evidence, report-ready tables, and pending entrant checks.
