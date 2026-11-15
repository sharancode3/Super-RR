# I06 · Verify players, Rajasthan Royals fit and form mapping

Use the official brief, supplied form and any dated entrant-provided view of the live role options. [Unstop listing and rules](https://api.unstop.com/hackathons/crp-superr-selector-season-2-help-shape-rajasthan-royals-ipl-2027-auction-strategy-rajasthan-royals-1792758) · [IPL 2026 retentions](https://www.iplt20.com/news/article/tata-ipl-2026-player-retentions-announced)

**End goal** Produce two defensible, ordered model shortlists and any verified form selections from those orders, with evidence for each recommendation.

```text
Use F03 identities, I04 fits, I05 stability and the rules contract. Keep four fields separate: model order, tactical RR fit, verified form eligibility, and real 2027 auction availability. Match public sources to canonical player ID and date. Use official league, board or tournament references for critical claims.

Loop: derive ranks -> check identity and role -> replay evidence -> verify eligibility -> validate order.

1. Recompute the ranked universe and both ten-player lists from the final dated model fit. Preserve exact score, tie-break, sample size, role and scenario. Use the model-derived order and mark exact ties. For plausible reserves near the cutoff, store the same context and support fields. Do not filter current IPL players, capped players, overseas players or all-rounders without an applicable verified rule. Do not force a role quota into the two lists.
2. Audit statistical role inference and separate it from external tactical descriptions. Review why Mustafizur Rahman and Taskin Ahmed were called all-rounders by old code, and test the input rule or threshold instead of substituting name-based exceptions. Show the phases players actually cover, evidence quality, RR deployment scenario and one decision-relevant downside. Cite dated 2026 roster status where supported. Do not infer 2027 availability from past roster membership or a form dropdown.
3. Generate an evidence card for each top-ten selection and near-cutoff reserve. Include the usual baseline, context-adjusted pressure-versus-usual difference with uncertainty, conditional lower-tail score, comparable pressure exposure, IPL overlap and stability. Use comparable phase/tier contexts or mark overlap insufficient. Distinguish a player's typical pressure level from evidence of improvement under pressure. Give one model-supported sequence with event keys and attributable run/wicket components plus a real-world source when available. Include one matched alternate or a clear condition that would alter the pick. Choose a replay by a documented rule rather than automatically picking a highlight. For an optional tree explanation, attribute the actual Q25 score in its deployment context and verify additive consistency. Distinguish attribution from causal effect.
4. If entrant-provided authenticated form evidence is available, store timestamped exact label, canonical ID, role and verification status. Join one-to-one inside each role, keep eligible names in model order, and log replacements from the reserve order and verified reasons. Check ten distinct labels per role and identical order across outputs. If evidence is absent or ambiguous, generate a provisional form-entry checklist with pending labels and explicit shortfalls. No portal mutation or submission.

Gate: both statistical lists are ordered and reproducible, evidence cards replay and avoid unsupported real-world claims, exact form eligibility is either verified for each chosen role or explicitly pending, and no tactical annotation changes the statistical rank.

PASS -> round1_release_review/07_release.md with eligibility status attached, including a provisional status when the option list is unverified.
FAIL -> repeat I06 for identity, mapping or explanation faults. Redirect a ranking or formula mismatch to round1_release_review/03_model_evidence_parity.md or a stress evidence issue to round1_release_review/05_transfer_stability.md.
BLOCKED -> STOP_PROVISIONAL with the specific identity or required evidence conflict. Resume at round1_release_review/06_shortlist_reality.md after resolution. Unknown live eligibility alone passes to I07 as provisional.
```
