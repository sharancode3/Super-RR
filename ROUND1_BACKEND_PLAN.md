# SupeRR Selector Round 1

Start implementation from the [Round 1 dispatcher](ROUND1_AGENT_PLAYBOOK.md). The [validation audit](ROUND1_VALIDATION_AUDIT.md) supersedes claims from the first built snapshot. This earlier note records the model rationale and exploratory results.

Build a reproducible local Python pipeline that ranks batters and bowlers by their predicted performance in future high-pressure situations. Use the supplied RR deliveries as the evidence for both rankings. Feed the report, Unstop selections and eventual dashboard from the same frozen results.

## Submission contract

- Enter ten batters and ten bowlers in rank order in Unstop. Verify the exact dropdown label for each selected player and check that each list contains ten unique players.
- Upload the methodology report as a PDF or PPTX. The form marks this upload required and provides a separate optional dashboard link field.
- Keep the performance ranking distinct from the auction shortlist. Verify each candidate's role fit and availability using dated sources. Keep unconfirmed availability visible. The screenshots show closed dropdowns, so the eligible pool and any capped-player restriction still need verification.

## Model decision

Use a partially pooled, context-adjusted player forecast as the default. Predict future net impact given high-pressure opportunities, separately for batting and bowling. Use 12 legal-ball equivalents as the reporting unit and compare players against peers in roles and situations they actually play. A prediction is conditional on receiving that workload. The forecast does not estimate auction availability or selection probability.

| Candidate | Pressure and peer models | Player forecast |
| --- | --- | --- |
| A. Cricket baseline | Fixed rules for tight late chases and first-innings resource stress. Historical role, phase and competition averages for runs and wickets. | Empirical distribution of high-pressure match impact, with a role-level estimate where individual evidence is sparse. |
| B. Statistical model | Regularized logistic win model with nonlinear terms. Smoothed historical run and dismissal models. Use the first-innings resource rule if the win model fails calibration. | Empirical-Bayes player baseline and pressure effect, with match-level variance. This is the default to beat. |
| C. Boosted challenger | Shallow calibrated CatBoost win model and CatBoost run and wicket expectation models. Use the same score-state inputs as B. | Same player model and reporting unit as B, so the comparison isolates the value of boosted context models. |

Give all three candidates the same frozen evaluation cohort, opportunity definitions, pressure labels and realized net-impact target for the ranking test. Estimate that reference target and its wicket values using earlier data. Also compare the candidates' own pressure classifications separately. Removing the player-specific pressure effect from B provides a direct test of whether estimating that effect improves prediction.

Choose using rolling validation through 2025, then compare once against the 2026 player outcomes. For the conservative score, use 25th-percentile pinball loss and check whether roughly one in four observed outcomes falls below the predicted bound. For the selection decision, report future average pressure impact of each top ten against the same eligible pool, by role, with paired match-bootstrap intervals. Report how many candidates actually had enough future exposure and exclude unobserved outcomes from scoring. Prefer the simpler candidate when the booster's improvement is within the uncertainty across folds. A gain in match-win Brier score alone does not promote a player ranking model.

An exposure audit using the last five overs found 178 batters and 170 bowlers with at least 48 approximate legal deliveries across six pre-2026 matches in the pooled data. Of those, only 73 batters and 80 bowlers appeared in at least three comparable 2026 matches. In the IPL-only audit the corresponding counts were 82 and 79 historically, and 45 and 39 with comparable future exposure. Late overs are an exposure check. Learn the true pressure threshold from earlier data and check whether enough eligible players survive it before locking minimum evidence rules.

### Research behind the decision

- [Davis, Perera and Swartz's T20 simulator](https://www.sfu.ca/~tswartz/papers/t20sim.pdf) uses hierarchical empirical Bayes to estimate ball outcomes across batter, bowler and game states. [CAMP](https://arxiv.org/abs/2307.13700) compares actual scoring with expected runs in context. [CricViz](https://cricviz.com/data-science/) documents separate win and context-adjusted player impact models in commercial use.
- Two 2026 preprints inform the design. [Runs Above Expected and Wicket Effect](https://arxiv.org/abs/2608.18020) centers run and wicket value against expectations in comparable states. [The Calibration-Leverage Tradeoff](https://arxiv.org/abs/2608.14696) shows that an internally coherent chase simulator can still miscalibrate win probabilities. Dynamic simulation is a follow-on experiment once the verified ball transitions and the ranking benchmarks are in place.
- [Rajasthan Royals' 2025 recap](https://www.rajasthanroyals.com/latest-news/superr-selector-hackathon-7500-participants-1500-submissions) names the winners and highlights analytical depth, clarity and originality. [Winner Sainath Reddy's account](https://www.linkedin.com/posts/sainathreddy-sankepally_from-college-mock-auctions-to-pitching-strategy-activity-7410354137478959104-W9Pl) describes statistical and ML work alongside player roles, price bands and squad balance. These sources do not specify the exact winning estimator or publish its validation results.
- [Mann Sutariya's public 2025 entry](https://github.com/PureGenius369/RajasthanRoyals-IPL-Auction-Strategy) documents integer programming for auction construction and calibrated random forest and gradient boosting for predicting an India cap. It provides a precedent for phase-aware features and a reproducible comparison. That prediction target differs from Round 1 pressure reliability.

## 1. Build and audit the match state

- Preserve the original six CSVs. Use the RR player IDs and match IDs as internal keys. Resolve name aliases, duplicate names and public IDs in a crosswalk. Keep competition and season attached to every observation.
- Read rows in match, innings and delivery sequence. Reconstruct all fields from the state **before** the current delivery. Track legal deliveries, wickets, runs off the bat and team runs separately. A wide or no-ball does not consume a legal delivery. Byes and leg-byes affect the scoreboard and are excluded from runs charged to the bowler.
- Recover exact extras and legal-ball flags where the RR rows can be aligned to public [Cricsheet records](https://cricsheet.org/downloads/). Match the fixture first by competition, date and normalized team pair. Verify the delivery sequence with over, striker, non-striker, bowler, batter runs and dismissals. Use official scorecards to reconcile innings totals, wickets and legal-ball counts. Send ambiguous sequences to an audit table with a reason.
- Track coverage by competition, season, role and candidate as well as overall. Report exact-state coverage and the player exposure it retains. If coverage is adequate across the candidate pool, use verified matches for the main exact-score analysis and use the broader RR-only model for sensitivity. If exact coverage is too selective, use the RR-only pressure proxy as the main model and compare it against exact states where available. Document the decision before opening the final player rankings.
- For the RR-only path, use cumulative runs off the bat, wickets and reconstructed legal balls. In a chase, the difference from the first innings' bat-run total is a proxy feature. Display it as such. Keep exact and approximate score features in separate model runs. Exclude unreconciled innings where the legal-ball sequence is uncertain. Exclude ties, no-results, Super Overs and rain-adjusted targets from the first win-model build and count exclusions by reason.

The pack has 200,999 delivery rows and 867 matches with deliveries. The raw `extras1_runs` field repeats a category code for each extras type. A local check found that adding one run per labeled extra plus `extras_2_runs` reproduced only 124 of 390 recorded win-by-runs margins in the sample with no revision fields and two innings. That heuristic is unsuitable for reconstructing exact targets. Treating `other` as a possible illegal delivery reconciles many over lengths, but verify it against public sequences or explicit over checks before using those states.

## 2. Model pressure before the ball

**Target.** Predict whether the batting side wins the match. Fit separate models for setting a total and chasing. Start with a regularized logistic model with nonlinear terms. Test a calibrated, shallow CatBoost model against it using identical folds and features. Select on match-weighted Brier score, log loss and calibration in close states. Keep the simpler model when the improvement is unstable.

**Features.** Use balls and wickets remaining, score or score proxy, league and season context, and historical scoring expectations available on the match date. For a chase use runs required where verified. For the first innings use the score relative to a historical scoring curve and the resources remaining. Team strength, if used, must be dated. Exclude current-ball outcomes, shot type, speed, final result fields and first-innings totals that had yet to occur.

**Pressure measure.** Estimate the expected absolute change in win probability across plausible next-delivery outcomes. Weight hypothetical outcomes using frequencies from earlier matches for the same context, with pooling for sparse states. The actual delivery outcome is never used to decide whether it was high pressure. Begin with the highest-leverage 20% of states within each innings and competition tier, with thresholds learned on training folds. Check 15% and 25% for sensitivity. Track difficult recovery situations separately using a shortfall against the historical scoring curve or chase demand relative to resources.

**First-innings fallback.** If win-probability skill or calibration is inadequate, use a transparent first-innings pressure rule based on wickets in hand and the gap between the projected total and a historical venue or competition benchmark. Learn the projection and cutoffs on earlier matches. Score and validate first-innings and chase performance separately before combining their player estimates. Label first-innings pressure as a scoring-resource proxy when using this path.

**Pilot from the supplied files.** A regularized logistic model using runs off the bat, wickets and reconstructed legal balls trained on 461 matches through 2024. With equal total weight per match, its Brier scores were 0.217 for the first innings and 0.128 for chases in 2025 (190 matches). In 2026 (131 matches), the scores were 0.254 and 0.134, against 0.254 for the constant baseline. Lower is better. This exploratory check supports keeping the chase proxy in contention and requiring a separate first-innings validation gate. It did not evaluate calibration in pressure states or test any player rankings.

## 3. Estimate player impact and reliability

**Peer expectation.** Fit expected runs and wicket probabilities from earlier deliveries. Condition on innings, phase, role, competition and bowler style where samples support them. Estimate wicket cost from expected runs remaining before and after a wicket in comparable states. Evaluate each delivery against the peer expectation on its held-out match.

**Attribution.** For batting, use runs off the bat and the cost of the striker's attributable dismissal. For bowling, use runs charged to the bowler and credit only bowler-attributable wickets. Handle run-outs separately so a non-striker dismissal does not become the striker's or bowler's wicket credit. In the proxy analysis, label any bowling measure based on runs off the bat accordingly. Disclose the exclusions and compare results on the exact-state subset.

Calculate batting impact as `actual batter runs - expected batter runs - wicket cost * (actual attributable dismissal - expected dismissal probability)`. Calculate bowling impact as `expected charged runs - actual charged runs + wicket cost * (actual credited wicket - expected credited wicket probability)`. Learn the relevant expectations independently for each target and score both with the same sign convention, where positive means better for the player. Aggregate with the correct role-specific denominators. Include conceded wides and no-balls in verified bowling runs while counting legal balls separately. Freeze the impact definition before backtesting rankings.

**Player baseline and pressure lift.** Fit a partially pooled player model to the impact above peer expectation. Give each player a usual level and an incremental effect under pressure. Estimate match-to-match variability from matches, with pooling for sparse players. Keep IPL and T20I effects distinguishable and test transfer to held-out IPL matches. Use the emerging-team events as a separate evidence tier in sensitivity analysis.

**Prediction and rank.** Predict context-adjusted impact for a future high-pressure match at a standardized workload within the player's observed role. Rank by the 25th percentile of that predictive distribution, so the order rewards both expected impact and repeatability. Export the mean, the ordinary baseline, the pressure lift, the predictive interval, pressure opportunities and distinct matches. Agree minimum evidence rules from exposure counts and stability before reviewing ranked names. Publish rank bands from match-level resampling. Show the absolute high-pressure estimate alongside lift to distinguish dependable high performers from large improvers.

## 4. Backtest and freeze the result

1. Train through 2024, use 2025 for feature and model choices and calibration, and hold 2026 player outcomes for the final chronological ranking test. The exploratory pressure pilot has already inspected aggregate 2026 win scores. Record that exposure and avoid tuning to the 2026 player test. Keep entire matches together. Fit historical benchmarks and preprocessing inside each fold. Generate earlier out-of-sample impact scores through rolling folds for the player model. Preserve the final holdout metrics before any full-history refit.
2. Compare the player ranking with raw strike rate and economy, a phase-based rule and a context model without player pressure effects. At the same cutoff, test how well each historical ranking predicts future high-pressure impact among players with observable future exposure. Report coverage and rank correlation or top-10 lift with match-resampled intervals.
3. Audit score calibration by innings, competition and match phase. Compare ranking stability across pressure thresholds, seasons, IPL-only versus pooled data and verified versus proxy match states. Investigate large rank movements and carry material uncertainty into the report.
4. Refit the chosen pipeline at the documented submission cutoff after evaluation. Verify the live role-specific dropdown pool before freezing the final lists. Generate the report tables and Unstop checklist from the same snapshot.

## 5. Outputs for the report and dashboard

| Output | Contents |
| --- | --- |
| `player_rankings.csv` | Snapshot ID, role, rank, player ID, dropdown label, usual impact, pressure lift, predicted high-pressure impact, conservative score, interval, pressure opportunities and matches |
| `model_validation.json` | Data window, temporal folds, model comparisons, calibration, holdout metrics and sensitivity summaries |
| `data_quality.csv` | Join and scoreboard reconciliation coverage, exclusions and reasons by match |
| `rr_shortlist.csv` | Player ID, proposed role, scouting evidence, roster fit, verified or pending availability and dated sources |
| `match_examples.json` | Selected replay states, with enough detail to show how pre-ball pressure and player impact were measured |

Run training and ranking locally as a batch job. The dashboard can read versioned, precomputed exports, so it can share the PDF's numbers without a live prediction service. A hosted dashboard should use cleared summaries and replay examples sourced from public records. The proprietary raw pack stays local.
