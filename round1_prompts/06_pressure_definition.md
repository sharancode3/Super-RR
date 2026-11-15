# Stage 06 · Identify pressure before the delivery

**Inputs** · Validated state forecasts, pre-ball data, earlier outcome frequencies and the frozen assessment reference.

**Checkpoint records** · 02, 04, 05.

**Outputs** · Pressure scores by delivery, opportunity tags, threshold and plausibility audits, small replay examples.

## Implementation prompt

```text
Define leverage as the expected absolute spread of the next state's win probability around its outcome-weighted mean. For a pre-ball state s, build plausible hypothetical outcomes o, learn their probabilities p(o|s) from earlier data, predict win probability q(o) for each successor, and calculate sum[p(o|s) * abs(q(o) - sum[p(j|s) * q(j)])]. Centering on successor mean prevents ordinary model drift from becoming leverage. Report drift against the current-state prediction separately. Start with common legal delivery outcomes and a wicket state. Include other outcomes only if transition rules and frequency estimates are reliable. State that this is legal-delivery leverage when that restriction applies. Choose no hypothetical state using the actual current delivery's result.

Condition hypothetical outcomes on verified free-hit status when it changes possible dismissals. Check that allowed outcome probabilities sum to one. For exact regulation chases, use deterministic terminal values for wins and losses. Treat a hypothetical tie at completion separately, with a declared neutral value of 0.5 for leverage only. Keep observed tied matches outside the v1 training cohort. Never apply terminal overrides from an off-bat proxy.

Replace the legacy constant outcome arrays with counts and smoothed probabilities fitted on earlier real deliveries. Store the counts, context bins, cutoff and fallback hierarchy. Prefer a small supported outcome vocabulary with a pooled prior for sparse states. Record whether free-hit outcomes and combined runs with wickets have enough support. Use the labeled cricket-rule fallback when leverage cannot be verified. Compare plausible pressure contrasts from real fixtures and independently check their pre-ball ledger rows.

Use a role-independent match situation for leverage. Track the burden on each side separately with a directional stress score based on pursuit demand relative to resources or position against historical par. Show recovery ability as a distinct evidence slice. For first innings with an unskilled win model, use forecast total relative to a pre-match historical benchmark plus the remaining wicket and ball resources. Call this first-innings resource pressure and show its behavior separately from win leverage.

Learn high-pressure cutoffs from training data within each innings and competition tier. Start with the top 20 percent of supported states and test 15 and 25 percent without selecting thresholds for favorite names. Preserve continuous scores for diagnostics. Check a tight late chase, a virtually lost chase, an easy chase, and a first-innings collapse. Record phase coverage and ordinary-versus-pressure overlap. Show leverage and stress separately in examples so a desperate chase is not automatically the biggest swing opportunity.

Prove invariance when the actual outcome fields of the current delivery are altered. Inspect improbable tags by state group, check terminal behavior and log uncomputable opportunities. Compare exact and proxy pressure tags on aligned matches to quantify agreement and bias by player group.

PASS -> round1_prompts/07_player_impact.md | Pressure labels pass pre-ball invariance and plausibility checks.
FAIL -> round1_prompts/02_scoreboard_ledgers.md | Repair ledger or legal-ball semantics.
FAIL -> round1_prompts/05_match_state_models.md | Repair implausible calibrated probabilities.
FAIL -> round1_prompts/06_pressure_definition.md | Repair successor-state logic, thresholds, or label invariance.
BLOCKED -> round1_prompts/07_player_impact.md | The predeclared rule or resource proxy is valid for supported segments. Keep method labels.
BLOCKED -> STOP_BLOCKED | Required segments have no supported pressure measure. Resume at round1_prompts/06_pressure_definition.md when the evidence changes.
```
