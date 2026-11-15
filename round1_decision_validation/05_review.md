# A05 · Rebuild and stop for review

**End goal** Prove the ranks and auction notes can be rebuilt and checked before handing them to the entrant.

```text
Use the A01–A04 checkpoints and two fresh output directories. Run the normal backend command from the raw pack with a pinned environment and frozen inputs. Keep all comparison runs untouched.

Loop: rebuild from raw -> verify hashes and meaning -> fix or stop.

1. Run model-neutral tests with scratch output. Run two independent clean builds. Generate versioned input, code/config, fit and snapshot identities from their contents. Hash the required machine-readable outputs. Explain and normalize only path or environment metadata that is expected to differ. Verify raw and historical artifact hashes.
2. Independently replay a batter and bowler example, Q25 loss and coverage, the top-ten assessment including actual assessable counts, and a same-fit rank perturbation. Check rankings and role-specific form mapping by canonical ID and order. Ensure each public or tactical claim is tied to a documented source or measured rows, and verify changing a bid or availability assumption leaves statistical rank unchanged.
3. Deliver the two ordered terminal rankings, a separate Unstop checklist, dated RR decision cards and the assessment and sensitivity results. Include exact fit date, target and evidence limits, historical benchmark, risk, and scenario triggers. Mark incomplete mappings provisional and unsigned auction candidates conditional. Record exact reproducible commands and the owning stage for any unresolved item. Stop for entrant review before report production or submission.

Gate: both clean builds agree on model identity, scores, order and meaning. All claims trace to sources. Unknown auction facts cannot certify an auction option.

PASS -> STOP_BACKEND_REVIEW with measured results, provisional statuses and reproduction commands.
FAIL -> route integrity to round1_decision_validation/01_fix_and_falsify.md, data and chronology to round1_decision_validation/02_data_and_target.md, selection or metrics to round1_decision_validation/03_train_for_decisions.md, or stress and evidence to round1_decision_validation/04_stress_and_auction.md. Repeat A05 for rebuild issues.
BLOCKED -> STOP_BLOCKED with the specific failed gate and exact resume file.
```
