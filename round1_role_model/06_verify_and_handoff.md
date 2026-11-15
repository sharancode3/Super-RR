# Stage 06 · Verify the clean run and hand off

Finish through the feature's normal entry point. Use the Stage 04 decision and Stage 05 shortlist evidence. The acceptance check covers reproducibility, cricket logic, and the actual outputs the entrant will use.

## Run the checks

1. From `C:/SHARAN PROJECTS/rr`, run the end-to-end CLI with the approved configuration, seed `2027`, and a fresh output directory. For the existing entry point the command is `python -m rr_pressure.cli run --raw-dir "C:/SHARAN PROJECTS/rr/6af3166e7b922_data_pack" --out-dir "C:/SHARAN PROJECTS/rr/artifacts_role_model_review" --seed 2027`. Choose a new directory name if that one exists. Record the exact effective command and settings if a new configuration switch is added. During iteration use the applicable existing subcommands such as `compare`, `rank`, and `export` with the same explicit directories. Rebuild affected dependencies when they change.
2. Run `python -m pytest tests/ -q`. Verify all seven raw hashes against the initial manifest and check the archived baseline's recorded hashes. Compare output identities, ranks, and deterministic fields on a repeat using identical inputs. Verify that metrics and worked examples recalculate from their referenced rows. Ensure tests that generate artifacts use temporary output directories.
3. Check the specific regression risks. Later appearances must leave earlier features and rankings intact. One- to five-ball pressure stints must enter the new fit when usable. Role eligibility and whole-match weights must agree with the declared rules. A dated availability change must reach the shortlist, terminal, Unstop order, and report table. Each view must use the same 20 player IDs and the same order. Check score provenance against the actual selection rule, including whether a rank is a model rank or a submission rank.

## Hand off the evidence

- Print the two lists and role-matched reserves. Include usual and pressure performance, downside, recent direct IPL and transferred evidence, and role and acquisition status. Attach the chronological model comparison, the shortlist replay and its limitations, and before-and-after reasons for important movements. Show two real worked examples with correct arithmetic and source flags.
- Leave one report-ready table in form order plus the selection rationale, dated auction assumptions, test summary, raw and output fingerprints, and reproduction command. State whether the challenger earned adoption, whether the reported model and policy were both replayed, and which comparisons were limited by coverage. Distinguish the audited scorecard evidence from proxies.
- Keep a short entrant checklist for the exact dropdowns, current retain/release and registration checks, and any borderline choice where evidence supports multiple plausible picks. Record the deliverable paths and remaining conditions in `review_progress.md`.

## Loop and exit

Rebuild → test → reconcile → hand off. If a check fails, return to the stage that owns the cause and rerun only the affected work before the final verification. Finish with the strongest measured option and clear limitations if a challenger did not improve on the baseline. Record the actual run status.

**Pass when** the clean build and regression checks complete, inputs and archives verify, and the report and Unstop tables can be reviewed together. **Next → `BACKEND_REVIEW` for the entrant. End execution here.**
