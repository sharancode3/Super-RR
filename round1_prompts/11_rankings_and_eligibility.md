# Stage 11 · Produce rankings and separate eligibility

**Inputs** · Frozen model and protocol, passed audits, supplied data through a declared cutoff, any verified form options.

**Checkpoint records** · 04, 09, 10.

**Outputs** · Ordered full candidate lists, top tens where supported, role watchlists, verified or provisional eligibility records.

**Read for this stage** · [Organizer requirements](rules_contract.md#organizer-requirements).

## Implementation prompt

```text
Preserve all pre-refit validation outputs. If the final fit still matches the model, data, and cutoff fingerprints, reuse it. Otherwise refit the chosen pipeline through the recorded submission cutoff using the frozen procedure. Compute pressure and ordinary evidence from earlier-fit predictions where required. Build separate batting and bowling candidate pools. Verify that statistical eligibility is assessed with data available at the cutoff. Apply the declared evidence floor and pressure/ordinary support rules. Sort by descending conservative impact score, then descending mean pressure impact, descending distinct pressure matches, and stable player ID.

Load the measured selection manifest and dispatch the actual chosen estimator and feature recipe for each role. Verify that a different valid selected model changes the refit path. Keep historically evaluated picks separate from the full-data refit. Remove the fixed player scouting dictionaries and derive order reasons and examples from the evidence for the current snapshot. Treat retention, current roster, availability and tactical claims as unverified unless supported by a dated source or a computed observed statistic. Eligibility cannot promote a weakly validated model to verified status.

Map exact live dropdown labels to RR IDs and keep verification evidence and date. Separate confirmed eligible, confirmed ineligible, and unverified. Apply a capped-player or other categorical restriction only when it is established by the organizer or form. Use the order produced by the model when applying the live pool. Keep reserves in order for later review. Record availability, role fit and any squad overlap as separate scouting fields. Preserve all-rounder distinctions and exact player aliases.

Prepare ranked candidates and evidence for the entrant to review. Give them the measured reason for the order, one representative pressure performance, a downside or uncertainty, and the supported squad role for each pick. Preserve any entrant-approved correction, its rationale, and the resulting regenerated snapshot. Keep the audited ranking rule intact unless a justified methodology or data correction is revalidated. Record the entrant's final ownership of the recommendations separately from model rank and dropdown verification.

Require ten unique verified names in each official list and deterministic order. When the form pool is unknown or an evidence floor leaves fewer than ten, export the ranked evidence as PROVISIONAL. Report the shortfall and reserve pool. Keep the evidence floor fixed unless the predeclared 2025 validation process already supports a different one. Do not fabricate missing names or replace unsupported predictions with reputation.

PASS -> round1_prompts/12_terminal_exports.md | The selected forecasts passed the evaluation gates and both lists contain ten verified dropdown names.
FAIL -> round1_prompts/01_ingest_identity.md | Repair canonical identities or aliases.
FAIL -> round1_prompts/08_reliability_forecast.md | Repair scores or exposure inputs.
FAIL -> round1_prompts/09_model_comparison.md | Repair a missing or inconsistent model selection manifest.
FAIL -> round1_prompts/11_rankings_and_eligibility.md | Repair ranking order, tie handling, or eligibility mapping.
BLOCKED -> round1_prompts/12_terminal_exports.md | The ranking model produced evidence but verification or support is incomplete. Export PROVISIONAL, record the shortfall, and preserve the model fit.
```
