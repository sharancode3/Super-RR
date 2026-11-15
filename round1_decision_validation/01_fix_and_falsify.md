# A01 · Fix the acceptance gates

**End goal** Replace checks that reward a preferred result with checks that detect real faults. Reopen the issues the saved R run missed.

```text
Read ROUND1_DECISION_AUDIT.md, ROUND1_DECISION_PLAYBOOK.md and round1_prompts/rules_contract.md. Preserve the raw pack, artifacts_rank_validation, and test_artifacts_rank_validation. Use the existing rr_pressure pipeline and a fresh artifacts_decision_validation directory.

Loop: fingerprint -> reproduce -> fix the failing acceptance check -> run a negative and positive control -> record.

1. Hash all raw files and the saved outputs. Capture current code and environment versions. Reproduce selected loss, retrospective shortlist support, the E history join, the R04 preferred-name assertions, the robustness baseline discrepancy and the missing auction context. Separate the parts that genuinely improved from the defects still open. Keep the existing R output and its recorded decisions as the historical comparison.
2. Repair the live acceptance tests. A historical replay may verify immutable snapshot bytes or numbers. The current gate must allow any valid model and any data-derived ordering. Replace tests that require E/B0, Sooryavanshi first, Suryakumar in, Rajapaksa out, or a minimum amount of a named player's pressure runs. Check score-to-order consistency, correct IDs, common keys, source provenance, calibration evidence and behavior when earlier or later data changes. Ensure tests write only to scratch outputs.
3. Register falsifiers and owners. A02 owns time boundaries, label and feature provenance, and cricket coverage. A03 owns model and list evaluation parity. A04 owns same-fit stability, genuine IPL transfer, and supported auction claims. A05 owns fit IDs and rebuild proof. Prevent a previous R05 PASS from certifying this run. Set the working status to provisional, record the evidence required for each downstream gate, and block final claims on open critical faults.

Gate: historical hashes match, current tests are model/name neutral, at least one adversarial test distinguishes faulty from valid behavior, and the checkpoint lists exact owners for all open defects.

PASS -> round1_decision_validation/02_data_and_target.md
FAIL -> repeat A01 after isolating the bad test, missing control, or fingerprint mismatch.
BLOCKED -> STOP_BLOCKED with the specific source, runtime, or evidence required. Resume at round1_decision_validation/01_fix_and_falsify.md.
```
