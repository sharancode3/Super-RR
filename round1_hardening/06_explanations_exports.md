# H06 · Generate the explainable rankings and entrant evidence

**Read** · [Organizer rules](../round1_prompts/rules_contract.md#organizer-requirements), [rankings](../round1_prompts/11_rankings_and_eligibility.md), [exports](../round1_prompts/12_terminal_exports.md).

**Inputs** · Frozen role-specific selections, assessment and sensitivity tables, final fit, source ledgers, any verified role-specific dropdown evidence.

**Deliver** · Terminal tables, full candidate and top-ten files, computed player evidence, private review material and release manifest.

## Implementation prompt

```text
Refit the actually selected candidate per role with the frozen feature and target recipe through the observed data cutoff. Use one result record for mean, Q25, interval and selected rank. Emit descriptive pressure lift as its own observed-context statistic. Include role, exact/proxy scope, exposure, rank band, IPL/T20I support, predictive validation status and input snapshot. Export the full candidate population, including insufficient evidence or missing role support, with explicit statuses. Create the provisional or verified top tens by filtering the same ordered predictions. Use deterministic documented tiebreaks. Keep unsupported or unknown players visible without adding invented precision.

Build one Why this pick record per proposed player. Show a real pre-ball state, pressure score and method, the observed delivery, expected peer outcome, the wicket and run contribution, and the player's history in similar opportunities. Include a downside or uncertainty and a supported squad role. Use a predeclared rule for representative examples so a single standout is not presented as typical. Store the exact delivery key and source. Recompute each example independently from the ledger. For the chosen tree candidate, optional local SHAP can explain the selected stage's output with an earlier-data background. Verify its scale and keep those attributions distinct from the final ranking decomposition. For pooled or linear models, show the fitted context, partial pooling and uncertainty directly.

Generate terminal, rankings, validation, data quality, replay evidence and Unstop-order exports from one run snapshot. Use source-derived counts and exact prediction columns. Generate a content-based snapshot ID from input, configuration and code/model fingerprints. Include measured coverage and known unknowns. Keep Unstop form labels blank until verified and rank names only within their correct dropdown pool. Treat the two ordered dropdown lists and the required PDF or PPTX as the later submission. Keep eligibility, auction availability and fit separate from modeled impact. State whether any tactical claim comes from RR outcomes, verified public evidence, or entrant judgment.

Test that changing the selected model or a fitted input changes the relevant output, that a replay resolves to one real event, and that a score and interval reproduce from the same model. Confirm the terminal order equals the Unstop checklist and the later report will use the same verified snapshot. Leave final insights and recommendations for entrant review and keep proprietary evidence local.

PASS -> round1_hardening/07_release.md | Exports, forecasts, ranks and evidence agree.
FAIL -> round1_hardening/03_model_parity.md | Repair mismatch between assessed and deployed models.
FAIL -> round1_hardening/05_transfer_stability.md | Repair incompatible evidence or retrospective claims.
FAIL -> round1_hardening/06_explanations_exports.md | Repair ranks, provenance, eligibility filtering or export coherence.
BLOCKED -> round1_hardening/07_release.md | Verification or predictive evidence is incomplete. Export a clearly marked provisional snapshot and report the exact blocker.
```
