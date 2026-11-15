# Stage 03 · Explore distributions and pressure opportunity

**Inputs** · Audited delivery ledger and dimensions.

**Checkpoint records** · 01, 02.

**Outputs** · Aggregate EDA tables and compact plots, source coverage decision, draft evidence grid, candidate feature dictionary.

**Read for this stage** · [Input data contract](data_contract.md).

## Implementation prompt

```text
Profile samples by season, competition tier, innings, phase, venue, team, batting role, bowling type, matchup, over and match status. Show distinct matches, deliveries, players, winners, scoring rates, wicket rates, role coverage, outliers and missing values. Split off-bat and team scoring. Check Impact Player-era scoring changes and compare IPL versus T20I distributions before pooling. Flag sparse emerging-team samples as a separate tier.

For full 20-over innings, define powerplay as overs 1 through 6, middle as 7 through 15, and death as 16 through 20 in one-based over labels. Keep current role and phase exposure distinct. Early successful chases have fewer late-over opportunities. Use observed opportunities for denominators and record that censoring when comparing players. Use a separate handling rule before introducing shortened matches.

Plot representative state distributions and tabulate context sparsity. Audit exact versus proxy coverage, the mismatch direction, missing match patterns, and whether missingness concentrates by competition, season, team, or player exposure. Treat the published Cricsheet withholding policy as a reason to inspect bias, and verify which specific fixture groups are absent.

Report data availability by opponent, venue, role and phase for the supported comparison, including RR's own appearances where present. Quantify distinct matches and usable ball counts behind opponent or matchup features. Use training-only priors for sparse opponents and a pooled fallback for unseen ones. Keep matchup-specific conclusions within observed support.

Use anonymized counts to compare candidate evidence floors of 24, 48 and 72 high-pressure ball equivalents and 4, 6 and 8 distinct matches, plus comparable ordinary exposure. Use phase-based counts only to gauge feasibility until Stage 06 produces pressure labels. Record prospective evaluation support and gaps by role. Document feature availability, sources, units, missing behavior, and whether fields are labels, identifiers, or forbidden predictors. Use prior, stable player profiles for batting hand, bowling style and role. Keep same-ball shot, speed, observed delivery type and realized outcomes out of pre-ball predictors. Use XI or substitution information only when its timing is established.

PASS -> round1_prompts/04_freeze_evaluation.md | Publish the EDA summary, coverage decision, and feature availability.
FAIL -> round1_prompts/01_ingest_identity.md | Repair identity or joins.
FAIL -> round1_prompts/02_scoreboard_ledgers.md | Repair invalid ledger states.
FAIL -> round1_prompts/03_exploratory_analysis.md | Repair the EDA or feature inventory.
BLOCKED -> round1_prompts/04_freeze_evaluation.md | Continue on the strongest validated route if both roles still have usable support. Record missing segments.
BLOCKED -> STOP_BLOCKED | A role has insufficient usable coverage. Resume at round1_prompts/03_exploratory_analysis.md after the data issue is resolved.
```
