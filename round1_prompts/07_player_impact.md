# Stage 07 · Convert runs and wickets into player impact

**Inputs** · Pre-ball ledger, pressure tags, fold-wise context features.

**Checkpoint records** · 02, 04, 06.

**Outputs** · Held-out peer expectations, attributable ball residuals, match-level observations for batting and bowling.

## Implementation prompt

```text
Fit separate peer expectations for batting runs, bowler-charged runs, striker dismissal probability and bowler-credited wicket probability. Use historical phase, innings, resources, role, competition, bowling style and supported opponent priors. Start with smoothed empirical or regularized models, and run a boosted context variant on the same inputs. Keep the focal player's identity and the current outcome out of the peer predictors. Generate scores for each historical match using a model fit on strictly earlier data. Track cold-start cases and sparse-context fallback.

For a minimal statistical implementation, use a smoothed phase and role table as the fallback, a regularized count mean for runs, and regularized logistic regression for wicket events. Use fixed folds and small regularization grids. Score expected runs with mean error and residual calibration as well as MAE. Score rare wicket probabilities with log loss and calibration. Do not rebalance or oversample wicket outcomes without evaluating the effect on predicted probabilities. The player model needs calibrated expectations to interpret its residuals.

Price a wicket as the difference in expected future runs between two otherwise comparable states with one fewer wicket in hand. Start with a regularized first-innings resource surface and validate its cricket shape. Use its run-equivalent price consistently where supported. Treat a separate chase wicket price as a sensitivity experiment with an explicit solution for chases stopping early. Learn wicket costs and expected dismissal risks inside each fold. Check support before using rare end states.

Use the persisted fold-specific resource fit in scoring. A fixed wicket value may be a labeled, predeclared sensitivity benchmark and must not be presented as a fitted delivery-specific price. Fit each peer expectation on prior rows, including for training targets later consumed by the player model. Unit-check that widening, narrowing or changing the observed opportunity mask changes the denominator as intended. Verify total and pressure legal counts on real RR rows that include a wide or no-ball. Treat unknown proxy charges as unknown rather than assuming each extra is exactly one.

Use these formulas with expected values fitted on the same eligible event population as actual outcomes.

Batting = (off_bat_runs - expected_off_bat_runs) - wicket_price * (attributable_striker_dismissal - expected_dismissal_probability)
Bowling = (expected_charged_runs - charged_runs) + wicket_price * (credited_wicket - expected_credited_wicket_probability)

In exact batting, credit runs hit off no-balls and keep wides out of the batter execution numerator. In exact bowling, include charged wides and no-balls and supported wickets such as ordinary wide stumpings. Exclude penalty-only team events from player execution. Use the event's pre-ball state for pressure and count legal-ball workload separately. Keep team-only dismissals out of bowler credit and avoid charging individual run-out responsibility without evidence. Preserve those events on the team ledger. When charges are unknown, use the named legal-delivery off-bat prevention proxy and report observed wide/no-ball events separately. Compare proxy versus exact rankings on matched fixtures.

Treat player impact as contextual performance under scorecard attribution. A catch or stumping still depends partly on fielding. Document that limitation when interpreting bowler credit.

Aggregate to player, match, role, innings, phase and pressure band. Store impact sums, numerator components, legal opportunities, extras events, and distinct matches. Carry zero-legal-ball segments in the event audit. Aggregate their attributable impact with supported exposure at the declared scoring grain or flag the rate as unavailable. Never divide by zero or silently discard their events. Test a run-out, wide stumping, no-ball plus bat runs, and a combined run-and-wicket event. Check that peer residuals center reasonably by innings and phase on held-out matches.

PASS -> round1_prompts/08_reliability_forecast.md | Impact is correctly attributed and scored on earlier-fit peer expectations.
FAIL -> round1_prompts/02_scoreboard_ledgers.md | Repair event attribution inputs or totals.
FAIL -> round1_prompts/04_freeze_evaluation.md | Repair temporal leakage.
FAIL -> round1_prompts/07_player_impact.md | Repair peer expectations, signs, denominators, or aggregation.
BLOCKED -> round1_prompts/08_reliability_forecast.md | Validated proxy impact still covers both roles. Record unavailable components.
BLOCKED -> STOP_BLOCKED | A role lacks a usable impact target. Resume at round1_prompts/07_player_impact.md with new evidence.
```
