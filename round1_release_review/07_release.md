# I07 · Rebuild and deliver the terminal result

**End goal** Independently prove backend reproducibility and deliver terminal output whose status matches its evidence.

```text
Read the stage checkpoint and every unresolved issue. Use two clean isolated output directories with the frozen inputs, config, optional eligibility evidence and code. Keep all snapshots preserved. Exercise the normal CLI entry point from the raw RR pack.

Loop: build from raw -> independently rebuild -> verify hashes and meaning -> repair or stop.

1. Run the full tests, including critical regression cases. Execute the normal backend command twice under the recorded environment and seed. Verify original raw and historical hashes. Compare canonical content digests for stable tables, predictions, shortlist order, evidence and machine-readable metrics. Record both clean run commands, config/code fingerprints, measured runtime, excluded metadata fields and any actual nondeterminism. If paths or timestamps differ, normalize only documented metadata. No positive reproducibility claim from the test count or presence of files.
2. Independently recompute at least one match-weighted state metric, paired Q25 pinball loss and calibration per role, one top-ten backtest utility per role, two player rank positions including a tie if present, and one valid batting and bowling episode. Check that read-only public anchors and event attribution agree where claimed, and verify output IDs, schema, units, cutoff, real coverage, candidate IDs and uncertainty type. Ensure early cutoff predictions cannot change when a later event is altered. Review report-facing language for scope and status.
3. Print both ordered lists in terminal with evidence support, Q25, chosen model, year coverage, provisional or form-verified status, IPL overlap and uncertainty. Save the performance rankings, separate form-entry checklist, selection evidence, scored prediction rows for local audit, experiment ledger, cohort and cricket QA, validation metrics, robustness tables, open issues, manifest and resume instructions. The form uses dropdown selections and PDF/PPTX. The internal CSV is a convenience for checking order. Keep dashboard and report authoring for a later stage.
4. Declare BACKEND_VERIFIED only when the model evidence, contracts and two rebuilds pass. Add FORM_VERIFIED only with ten exact confirmed choices per role. Otherwise report PROVISIONAL with the reason and owner. If corrected results cannot support a winner between model families, document the simpler defensible choice or remaining predictive block. Return the exact clean-run command, changed files, observed results and what remains for the entrant. Stop after the documented outcome.

PASS -> STOP_VERIFIED when both backend and form gates pass.
PASS -> STOP_PROVISIONAL when backend gates pass and exact form options remain pending. Resume at round1_release_review/06_shortlist_reality.md on new form evidence, then revalidate output order.
FAIL -> round1_release_review/00_reproduce.md for provenance, round1_release_review/01_cricket_data.md for event accounting, round1_release_review/02_temporal_target.md for leakage, round1_release_review/03_model_evidence_parity.md for dispatch and export, round1_release_review/04_train_select.md for model evidence, round1_release_review/05_transfer_stability.md for stress evidence, or round1_release_review/06_shortlist_reality.md for eligibility and player rationale. Repeat I07 for clean-run mechanics.
BLOCKED -> STOP_BLOCKED with the failed independent check and its owning prompt. Never route a scientific failure to an eligibility-only stop.
```
