# H02 · Rebuild chronological features, pressure and the common impact target

**Read** · [Temporal protocol](../round1_prompts/04_freeze_evaluation.md), [state model](../round1_prompts/05_match_state_models.md), [pressure](../round1_prompts/06_pressure_definition.md), [impact](../round1_prompts/07_player_impact.md).

**Inputs** · Validated event populations and provenance, original reference protocol, audited issues.

**Deliver** · Versioned fold and fit manifests, pre-ball pressure, out-of-time reference impact and common player-match assessment rows.

## Implementation prompt

```text
Create expanding date cutoffs with whole match clusters. Within each outer training window, generate historical training targets from strictly earlier fits after a declared burn-in. Use pre-2026 rolling validation for candidate selection. Freeze the comparison unit, opportunity mask, objective, support and calibration gates, uncertainty and practical tie rule before scoring the new comparison. Treat all previously seen seasons as retrospective and report 2026 separately after model choice. Exclude same-day updates unless a strict timestamp is verified.

Separate static identity from performance-derived role, venue, opponent and player skill features. Learn history snapshots from preceding matches. Use support-aware pooling for bowling style, phase, venue, opposition, era and competition. Treat debutants as unknown or use a documented stable pre-match attribute. Avoid deriving role from the complete pack. Within each cutoff, test that changing a later player's performance cannot alter earlier features, peer targets, parameters, or predictions. Cache each fold with its source and configuration fingerprints.

Fit a constant and regularized logistic benchmark for chase probability and compare with shallow boosting. Use separate chronological calibration or cross-fitted probabilities with known cutoffs. Evaluate match-weighted Brier and log loss, calibration by innings and phase, and supported monotonicity. Fit a remaining-runs model for first innings and wicket value. Where first-innings win skill is weak, use a separately labeled scoring-resource pressure estimate. Fit successor outcome probabilities from earlier eligible observations and compute leverage from the expected absolute change about their weighted successor mean. Test feasible free-hit and terminal states. Keep chase stress and first-innings recovery separate from leverage.

If reporting percentage accuracy for team wins, use a declared checkpoint such as the state before over 16, one prediction per match at that checkpoint, and a matched baseline. Record matches that ended before that checkpoint. Keep that metric separate from player forecast accuracy and coverage.

Fit a transparent, common peer reference on earlier folds. For delivery state s, let w(s) be the fitted expected remaining runs at the observed wicket count minus expected remaining runs with one fewer wicket in hand, holding supported context fixed. Audit its shape. Treat the old midpoint cost as a named benchmark and leave unsupported values missing or use a predeclared pooled fallback. Score batting as actual minus expected runs minus w(s) times the dismissal residual. Score bowling as expected minus actual charged runs plus w(s) times the credited-wicket residual in the exact lane. Use the declared legal off-bat prevention target in the proxy. Test both score signs and combined events. Never reuse a peer fit on rows that estimated it.

Freeze one observed reference outcome and pressure definition per lane for the controlled model comparison. Aggregate to unique role, player, match and evaluation-window keys. Store impact, actual opportunity count, innings, peer and source IDs, fit cutoff, and training-set fingerprint. Use y12 = 12 times observed impact divided by eligible exposure and leave zero exposure missing. Keep realized exposure in assessment metadata. When evaluating predictions conditional on realized workload, explicitly label that conditioning. Use a declared fixed workload and supported role/phase mix when producing public ranks. Secondary end-to-end pressure definitions need separate evaluation.

PASS -> round1_hardening/03_model_parity.md | Every reference row has valid time provenance and supported cricket semantics.
FAIL -> round1_hardening/01_cricket_ledger.md | Repair underlying scoring, state or exposure defects.
FAIL -> round1_hardening/02_temporal_reference.md | Repair leakage, invalid support, calibration or reference accounting.
BLOCKED -> round1_hardening/03_model_parity.md | A validated simpler resource or rule-pressure reference is available and its limitations are explicit.
BLOCKED -> STOP_BLOCKED | No usable chronological target remains. Resume at round1_hardening/02_temporal_reference.md when the required evidence is available.
```
