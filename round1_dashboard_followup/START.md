# Next prompt · SupeRR Selector Season 2

## Give this to the coding agent after its current pass

Continue in `C:/SHARAN PROJECTS/rr` after finishing the dashboard prompt you are already executing. Preserve and inspect the current implementation, including its SVG icons, methodology, rankings navigation, portrait changes and local preview. Use what works. This is a continuation with a data audit and a targeted model test. Start at [Stage 00](00_reconcile_current_build.md).

The goal is a dashboard an evaluator can understand and verify. It must answer three questions. **Who should RR back? What does the model rank before RR-specific decisions? How did the data, model tests and auction constraints lead from one to the other?** Give these questions clearly labelled destinations, with Methodology as a standalone section. The RR shortlist remains the main entry point. Preserve both role orders from the latest verified recommendation as the baseline. Promote a different model or recommendation only through Stage 02, with a full, separately verified successor snapshot.

### Rules while building

- Keep both organizer data packs, historic artifacts and current recommendation available. Use the revised recorded-extras pack for the baseline. Use source hashes and versioned, allowlisted derived data. Retain only the aggregates needed by the client. Reuse the existing model, data and dashboard paths through their normal entry points.
- Define **Model rankings** before any RR roster, role-balance, nationality, retention, recruitment or auction availability decisions. Preserve match integrity, identity, role and historical evidence requirements. An earlier “performance-only” view or a sorted RR candidate pool may already have applied market filters. Read the code and prove the population before adding the label.
- Present different kinds of evidence under their proper names. Give the forecast and its unit. Show historical performance and exposure. Label top-ten selection as “Picked in X of Y match resamples.” Describe RR fit using role evidence and dated availability assumptions. Give forecast error only for the cohort that produced it. Use a probability of future success only if a precisely defined historical event has genuinely been calibrated and evaluated. The current artifacts do not supply a probability that a player is the best fit for RR. The currently observed 30–50% inclusion counts are valid results.
- Use no emojis on any application surface. Use restrained custom SVGs where an icon communicates something. Reuse the existing icon components if they pass review. Align photo scale and framing using actual portrait bounds and a shared composition system. Keep real images and credits, paper edges, the existing playful palette and comfortable reduced-motion defaults.
- Fix the methodology at the evidence source. Verify every public-facing figure, formula, recipe name and match example against the actual computation and source. Start each subsection with plain language. Layer the detailed math, sample definitions and reproducibility notes beneath it. Keep prior experimental models visible in a dated development history when verified, with their own outcomes.
- Loop each stage: inspect the current version, reproduce the issue, change only the necessary source, run the listed checks, inspect the result, record what changed and advance only when the gate passes. Return to the earliest failing stage when a later check finds a discrepancy. Keep a short append-only follow-up checkpoint with exact artifacts, tested output, decisions and reason for any open item.
- Finish with a production build on a local preview and a short verification summary. Report whether the bowling comparison justified a change and what the strongest limitations are. This implementation covers the local app and evidence. The existing Unstop entry and public deployment are outside this phase.

| Stage | Open next | Gate |
| --- | --- | --- |
| 00 | [Reconcile the active build](00_reconcile_current_build.md) | Baseline frozen and verified source-of-truth map |
| 01 | [Export model rankings and RR decisions](01_model_rankings_to_rr.md) | Same-model comparison with evidenced changes |
| 02 | [Run the focused bowling experiment](02_bowling_backtest_and_confidence.md) | Reproducible comparison and an evidence-based decision |
| 03 | [Rebuild Methodology](03_methodology_and_evidence.md) | Exact facts, plain-language explanations and a verified example |
| 04 | [Balance UI, SVGs and portraits](04_ui_portraits_and_motion.md) | Accessible and consistent three-destination experience |
| 05 | [Verify and hand off](05_verify_and_handoff.md) | Data and browser passes on the actual served build |
