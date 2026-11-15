# A02 · Repair the data, target and chronological boundary

**End goal** Build a versioned event-to-forecast dataset that measures plausible cricket pressure and uses only information available before prediction.

```text
Use the original six CSVs, the A01 defect ledger and round1_prompts/data_contract.md. Read the scoring and replay details in round1_rank_validation/01_pressure_and_time.md. Keep official scorecard fields, pack event counts, and model workload separate.

Loop: profile and reconcile -> rebuild dated features and labels -> replay -> mutate future data -> verify.

1. Write a compact EDA and transformation ledger. Verify event grain, numeric delivery order, canonical IDs, league/tier mapping, duplicated XIs, missing fixtures, joins, revisions, and exclusions. Publish counts at each step by season, innings, phase, tier, and discipline. Quantify IPL support, opponent/context overlap, pressure match concentration and missing tracking variables. Apply match-date rules for legal balls, no-balls, wides, wicket credit, revised targets and free hits. Store exact versus proxy evidence distinctly.
2. Predeclare a mixed replay set with setting-a-total stress, close and lopsided chases, and ordinary controls. Include fixtures 40759, 50943 and 50944 as documented checks. Score them with a cricket-rule baseline and a pre-ball state model using first-innings resource/par stress and chase leverage. Compare coverage and calibration across roles and contexts, not how many runs any named player receives. Learn any composite or pressure weights on earlier data. Where transitions remain approximate, show their effect in a sensitivity. Reconcile official balls faced and ledger legal balls without substituting one for the other.
3. Materialize per-block reference fits for peer expectations, wicket value, pressure state, transitions, thresholds and roles. Exclude the warm-up block's self-fit labels from forecast training or supply a documented independent prior. Build E's usual level, exposure, form, league, venue and opponent features from dates strictly before the row's match. Never merge a full-window summary into earlier labelled rows. Preserve a cold-start policy. Make date provenance auditable with row keys and the latest source timestamp. Test row-order stability and that a later fixture or the assessed match's outcomes cannot affect earlier features.
4. Freeze one target for all selectable families. Batting impact is off-bat runs above peer expectation minus the centered striker-dismissal cost. Bowling impact is runs saved against expected bowler charges plus the centered credited-wicket value. Normalize to 12 legal-ball equivalents under a stated opportunity definition. Use consistent weights in the numerator and denominator. Keep matched ordinary-versus-pressure change, current skill, actual fit support, and prospective pressure reliability as separate quantities. If testing continuous weights or public-data enrichment, version that as an experiment and rerun all relevant fits. Use dated, reconciled observations. Use whole-match resampling for uncertainty.

Gate: the event-to-opportunity ledger reconciles, pressure is tested on varied real scenarios, forward-only provenance is testable, and the common target and assessment keys are frozen.

PASS -> round1_decision_validation/03_train_for_decisions.md
FAIL -> repeat A02 for cricket, features, time or target. Send source integrity and test-isolation problems to round1_decision_validation/01_fix_and_falsify.md.
BLOCKED -> STOP_BLOCKED with the exact unsupported dependency and resume at round1_decision_validation/02_data_and_target.md. A measured proxy lane can pass with its limitation attached.
```
