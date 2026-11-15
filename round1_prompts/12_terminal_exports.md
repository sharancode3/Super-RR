# Stage 12 · Print the results and export the evidence

**Inputs** · Frozen model choice, rankings, evidence, selection and validation snapshots.

**Checkpoint records** · 02, 09, 10, 11.

**Outputs** · Terminal views and machine-readable exports from a single result snapshot.

**Read for this stage** · [Organizer requirements](rules_contract.md#organizer-requirements).

| Export | Required contents |
| --- | --- |
| `player_rankings.csv` | Snapshot ID, role, rank, player ID, display name, verified dropdown label if available, eligibility status, role profile, ordinary impact, pressure lift, expected pressure impact, Q25, predictive interval bounds, opportunities, matches, rank interval and support flags. |
| `unstop_rank_order.csv` | Snapshot ID, role, rank, RR player ID, exact dropdown label, and verification status. Verified release has exactly 20 ordered rows. Label provisional rows and leave unverified form labels blank. |
| `model_validation.json` | Cohort, source lanes, data cutoff, folded metrics, selected method, selection rationale, all candidate results, calibration, observed exposure, sensitivity and limitations. |
| `data_quality.csv` | Fixture and inning IDs, source lane, match and delivery reconciliation, exclusions and reasons. Include aggregate counts in the terminal. |
| `player_evidence.csv` | Match-level aggregate contribution and opportunity counts plus phase and innings summaries. Keep private match evidence local. |
| `match_examples.json` | Small reproducible examples for a pressure contrast, a supported pick, and a downside or borderline case. Include pre-ball state, outcome, peer expectation and calculation provenance. |
| `rr_shortlist.csv` | Candidate role, supporting evidence, main uncertainty, verified availability and roster evidence when known, with a place for the entrant's own judgment. Keep this separate from ranking order. |
| `run_manifest.json` | Run ID, input and configuration hashes, train and assessment windows, dependencies, seed, selected model, output hashes, release status, entrant-review status, and prior snapshot if a repair was required. |

### Terminal layout for the implementation

```text
SupeRR Selector Season 2 | Round 1 | <snapshot ID> | <VERIFIED or PROVISIONAL>
Coverage   <fixture and delivery totals by tier, exact and proxy counts>
Evaluation <chronological windows and held-out pressure opportunities>
Models     <A, B and C by role, pinball loss, Q25 coverage, top-ten outcome, selection reason>

TOP BATTERS  |  rank  player  role  pressure balls/matches  usual  lift  mean  Q25  support
<generated rows from this run>

TOP BOWLERS  |  rank  player  role  pressure balls/matches  usual  lift  mean  Q25  support
<generated rows from this run>

Limitations <coverage gaps, uncertainty, or unverified dropdown labels>
Exports     <paths for this snapshot>
```

## Implementation prompt

```text
Print one compact terminal run in this order. Show snapshot and eligibility status first, then source coverage and exclusions, model comparison and recommendation, batter top ten, bowler top ten, limitations and output paths. For each rank show player, role, pressure opportunities and matches, ordinary level, pressure lift, mean pressure impact, conservative score and any important support flag. Include enough precision for interpretation and use unrounded values for sorting. Print N/A for unavailable metrics and preserve units in the headings.

Create the listed CSV and JSON files from the same snapshot used for console tables. Keep evaluation metrics from the pre-refit backtest clearly separated from final-fit rankings. For the replay examples, show one pressure contrast and one selection rationale with the full calculation. Include a weaker match or a borderline reserve so the later report can show both evidence and uncertainty. Keep proprietary data and internal evidence files local. Public-facing materials need separately sourced public evidence or explicit approval.

Derive counts, model names, skill figures, limitations, and snapshot identity from actual run artifacts. Treat a missing metric as missing. Select replay examples from the ledger and store match_id, innings and innings_ball_num. Rejoin each example to exactly one RR row and independently recompute score state, pressure tag, peer inputs and impact. Add a regression that catches the legacy fixture 15407 replay mismatch and a test that changed upstream diagnostics change the output. Keep dropdown labels blank until verified and distinguish provisional ranks from official selections. Use dated external sources for any retained scouting claim beyond the supplied evidence.

Test that terminal, ranking CSV and Unstop-order CSV agree on order and snapshot. For a verified release, assert ranks 1 through 10 once per role, unique players per list and a confirmed exact dropdown label for every row. Check finite or explicitly missing values and traceability to genuine evidence for every pick. Validate output files against their contract and verify that the manifest points to the files generated. Render the tables in PowerShell without requiring notebook or dashboard software.

PASS -> round1_prompts/13_release_verification.md | Console, exports, and manifest agree.
FAIL -> round1_prompts/09_model_comparison.md | Repair evaluation output or metric provenance.
FAIL -> round1_prompts/11_rankings_and_eligibility.md | Repair ranks or eligibility evidence.
FAIL -> round1_prompts/12_terminal_exports.md | Repair output serialization, terminal display, or file hashes.
BLOCKED -> round1_prompts/13_release_verification.md | A coherent PROVISIONAL snapshot exists and its blocker is explicit.
BLOCKED -> STOP_BLOCKED | Terminal or exports cannot be produced coherently. Resume at round1_prompts/12_terminal_exports.md after fixing the output dependency.
```
