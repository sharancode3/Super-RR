# Start here · SupeRR Selector Season 2 dashboard

## Prompt to give the coding agent

Work in `C:/SHARAN PROJECTS/rr`. Build the local, evaluator-facing dashboard for Rajasthan Royals' SupeRR Selector Season 2, Round 1. The research and ranked recommendations are already complete. Your job is to present them faithfully, explain how they were produced, and make the experience fast, accessible and visually distinct. Start with `round1_dashboard_prompts/00_evidence_contract.md` and follow one stage file at a time.

The dashboard opens with both leaders visible side by side on desktop. It has two ordered sections, **Batters** and **Bowlers**, and a third section, **How we chose**, that documents the audit from raw files through the final recommendation. Show all 20 ranking entries and exactly 19 distinct real player portraits. Ravindra Jadeja shares one image across his two role cards. No other player appears twice in the ranked display. Treat the rankings as an evidence-backed recommendation for RR as of 15 November 2026. Current outside targets have an auction availability condition. RR players have an RR squad decision. Present the submission order exactly as recorded.

Design it as a playful geometric sports editorial. Use real transparent portrait cutouts with a continuous warm-white paper stroke, two colour families with clear text labels, strong type hierarchy and restrained entrance motion. Build geometry in CSS. Use no SVG art, emojis, generic player silhouettes or generated portraits. Make both leader panels and the opening heading readable before any animation or interaction. Follow Stage 02 for the exact palette, font sizes, grid and button dimensions.

### Work rules

- Inspect local instructions and reuse a working frontend if one exists. The planning audit found no existing JS application at the workspace root. If that is still true, keep the app isolated in a `dashboard/` directory. Prefer a static, typed React build with Vite, TypeScript and CSS. Use the installed supported Node version and the repo's existing tooling where applicable. Use native browser features for basic controls and animation.
- Begin in Stage 00. Freeze the ranking inputs by ID, role and rank. Keep the backend, historical evidence, raw data and existing outputs intact. Fit no new models for this dashboard. Make any data transformation for the dashboard a reproducible build-time projection into small approved aggregates. Keep raw proprietary data and internal source files outside the delivered client bundle. The dashboard shows analysis derived from the competition pack.
- Record the source of every metric, assertion, supplied date and photo. Preserve precision in data and round in display. Check the 2026 replay is described as retrospective. Show player confidence as match-resample selection frequency with its denominator. Use the saved source for the exact per-player figure. The full-list result is 0 of 1,000 for each discipline. The total number of historical fits and continuous training duration are unverified. Show dated evidence and specifically labelled run counts.
- Use actual, identity-verified photographs. Preserve the original team jersey and explain the photo's season in credits. Source images with a usable reuse basis for the intended audience. Keep rights review separate from identity review. Keep assets and the preview local during this task.
- Loop at every stage. Read its inputs, make a small coherent change, run its checks, inspect the actual browser or generated output, fix failures and recheck. Keep a short checkpoint at `dashboard/BUILD_CHECKPOINT.md` with stage, evidence, tests, decisions and any blocker. A stage passes when its named checks pass. If a check fails, return to the earliest stage responsible. Continue independent work while resolving a missing dependency. Record what blocked any unresolved requirement and the exact stage to resume. Avoid repeatedly rerunning a check with the same inputs.
- Finish both role sections, the full methodology, motion and keyboard support, the local production build and the release review. A preview need not wait on an individual image rights question. A complete final preview needs all 19 verified photos. Return the local preview command, screenshot locations, build and test results and any unresolved rights or verification item. Publishing, uploading to Unstop and creating the PDF/PPT are separate actions outside this dashboard implementation.

### Stage order

| Stage | Prompt | Gate |
| --- | --- | --- |
| 00 | [Evidence contract](00_evidence_contract.md) | Exactly 20 ranked rows, 19 identities, sourced metrics and timeline |
| 01 | [Portrait library](01_portrait_library.md) | 19 identity-verified photographs with a credit and rights record, ready for the selected review audience |
| 02 | [Visual system and page structure](02_visual_system.md) | Approved responsive structure, components, tokens and two-leader first screen |
| 03 | [Rankings and player evidence](03_rankings_and_player_evidence.md) | Two exact lists, 20 correctly scoped cards and accessible player details |
| 04 | [Methodology and project story](04_methodology_and_project_story.md) | All claimed transformations, results, limits and timelines trace to evidence |
| 05 | [Motion, accessibility and performance](05_motion_accessibility_performance.md) | All 20 portraits reveal safely and the complete page works without motion |
| 06 | [Final review and handoff](06_final_review_and_handoff.md) | Two verification passes, production preview and review status |
