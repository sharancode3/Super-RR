# Dashboard Build Checkpoint

## Stage 00 · Freeze the dashboard evidence (PASS)

- **Execution Date:** 15 November 2026, IST
- **Status:** **STAGE_00_PASSED**
- **Target App Directory:** `dashboard/`
- **Output Bundle:** [`dashboard/src/data/evidence.json`](src/data/evidence.json)

### 1. Evidence Source Register

| Source File | Date | Evaluator Description | SHA-256 Hash |
| :--- | :---: | :--- | :--- |
| `recommended_rankings.csv` | 2026-11-15 | Retrain Audit Recommended Rankings (2026-11-15) | `632fba31caa1b971...` |
| `player_evidence.csv` | 2026-11-15 | Player Evidence & RR Scouting Context (2026-11-15) | `d8e4748302a64ddb...` |
| `scenario_review_rankings_with_stability.csv` | 2026-11-15 | Scenario Review Rankings with Stability (2026-11-15) | `6a97e8e9a5528dbc...` |
| `updated_stability.json` | 2026-11-15 | Updated Cluster Bootstrap Stability Report (2026-11-15) | `9d8efcb9c5ce099c...` |
| `verified_rankings.csv` | 2026-11-15 | Unstop Verified Rankings Cross-Check (2026-11-15) | `c0a88f46ab322ff5...` |
| `retraining_comparison.csv` | 2026-11-15 | Retraining Comparison Matrix across 160 Evaluations (2026-11-15) | `424d41520b4108b1...` |
| `retraining_audit.json` | 2026-11-15 | Retraining Audit Technical Manifest (2026-11-15) | `d6cfe0b001bcc2dd...` |
| `coverage_report.json` | 2026-11-15 | Rebuild Coverage & Data Quality Report (2026-11-15) | `06c09698390d006b...` |
| `evaluation_split_manifest.json` | 2026-11-15 | Chronological Evaluation Split Manifest (2026-11-15) | `d26df84fa7cfbb92...` |

### 2. Contract Verification Results

- [x] **Exact Row & Identity Counts:** Exactly 20 ranking records (10 Batters, 10 Bowlers) across exactly 19 distinct player identities.
- [x] **Dual-Role Verification:** Player ID `152` (Ravindra Jadeja) is the sole identity appearing twice (Batters #9, Bowlers #10). The identity record, media key, and portrait are shared, while role evidence, impact, and stability differ.
- [x] **Name Agreement:** Exact name matches between `recommended_rankings.csv`, `player_evidence.csv`, and `verified_rankings.csv` verified across all 20 rows.
- [x] **Spelling Integrity:** Dataset spelling strictly preserved in display (`Abishek Porel`, `Rasikh Salam`).
- [x] **Arithmetic Check:** `signed_uplift = pressure_runs_per_12 - ordinary_runs_per_12` satisfies exact tolerance (< 1e-5) across all 20 rows.
- [x] **Stability Concordance:** Selection frequency matches between `player_evidence.csv` and `scenario_review_rankings_with_stability.csv` across all rows; whole-list concordance is exactly `0 of 1,000` for both disciplines.
- [x] **Missing Value Sanity:** `loo_omission_min`/`loo_omission_max` are null strictly when `fixtures <= 1` (Riyan Parag #7, Krunal Pandya #5), and strictly non-null for all 18 multi-fixture players.
- [x] **Modelling Matrix Integrity:** Exactly 160 comparison rows representing 2 rebuild sources × 2 roles × 5 recipes × 8 evaluation windows.
- [x] **Data Segregation:** Raw proprietary files and full historical directories are excluded from client bundles; only the build-time projection (`evidence.json`) is delivered.

### 3. Frozen Recommendations (As of 15 November 2026 IST)

- **Batters (10):**
    - #1 Vaibhav Sooryavanshi (POWERPLAY)
  - #2 Josh Inglis (POWERPLAY)
  - #3 Sameer Rizvi (MIDDLE)
  - #4 Cooper Connolly (MIDDLE)
  - #5 Donovan Ferreira (FINISHER)
  - #6 Abishek Porel (POWERPLAY)
  - #7 Riyan Parag (MIDDLE)
  - #8 Prabhsimran Singh (POWERPLAY)
  - #9 Ravindra Jadeja (FINISHER)
  - #10 Venkatesh Iyer (MIDDLE)
- **Bowlers (10):**
    - #1 Mohammed Siraj (POWERPLAY)
  - #2 Jason Holder (MIDDLE)
  - #3 Kartik Tyagi (DEATH)
  - #4 Lungi Ngidi (DEATH)
  - #5 Krunal Pandya (SPIN)
  - #6 Rasikh Salam (DEATH)
  - #7 Mohammed Shami (POWERPLAY)
  - #8 Anshul Kamboj (POWERPLAY)
  - #9 Ravindra Jadeja (SPIN)
  - #10 Jofra Archer (POWERPLAY)

### 4. 5-Row Manual Audit Trace

1. **Vaibhav Sooryavanshi (Batters #1, ID 50284):**
   - Source: `recommended_rankings.csv` (priority 3.5069, predicted impact 4.9401, pressure 11.0172, ordinary 10.0593, uplift +0.9578).
   - Evidence: `player_evidence.csv` (63 balls, 11 fixtures, LOO range [8.2898, 12.9793], stability 0.958, route: "RR squad decision").
   - Trace status: **VERIFIED_EXACT**.
2. **Josh Inglis (Batters #2, ID 4736):**
   - Source: `recommended_rankings.csv` (priority 2.8001, predicted impact 4.7039, pressure 13.4868, ordinary 4.9194, uplift +8.5674).
   - Evidence: `player_evidence.csv` (24 balls, 5 fixtures, LOO range [9.6351, 18.0956], stability 0.875, route: "If available at auction").
   - Trace status: **VERIFIED_EXACT**.
3. **Ravindra Jadeja (Batting #9, ID 152):**
   - Source: `recommended_rankings.csv` (priority 1.4883, predicted impact 3.4116, pressure 10.6698, ordinary 9.5242, uplift +1.1456).
   - Evidence: `player_evidence.csv` (38 balls, 4 fixtures, LOO range [7.9866, 12.2782], stability 0.350, route: "RR squad decision").
   - Trace status: **VERIFIED_EXACT**.
4. **Mohammed Siraj (Bowlers #1, ID 5944):**
   - Source: `recommended_rankings.csv` (priority 3.3289, predicted impact 5.2346, pressure 15.3402, ordinary 12.6074, uplift +2.7328).
   - Evidence: `player_evidence.csv` (130 balls, 14 fixtures, LOO range [13.2751, 16.5492], stability 0.894, route: "If available at auction").
   - Trace status: **VERIFIED_EXACT**.
5. **Ravindra Jadeja (Bowling #10, ID 152):**
   - Source: `recommended_rankings.csv` (priority 0.9991, predicted impact 3.3005, pressure 13.9168, ordinary 11.2701, uplift +2.6467).
   - Evidence: `player_evidence.csv` (34 balls, 5 fixtures, LOO range [10.2798, 17.1587], stability 0.428, route: "RR squad decision").
   - Trace status: **VERIFIED_EXACT**.
6. **Low-Sample Pick — Sameer Rizvi (Batters #3, ID 8238):**
   - Source: `recommended_rankings.csv` (priority 2.5029, predicted impact 4.2981, pressure 18.0841, ordinary 4.0397, uplift +14.0444).
   - Evidence: `player_evidence.csv` (8 balls, 4 fixtures, LOO range [13.4326, 23.4735], stability 0.630, route: "If available at auction").
   - Trace status: **VERIFIED_EXACT** (Caveat: thin sample of 8 balls correctly flagged).

### 5. Gate Handoff
- Stage 00 is complete and verified. Ready for **Stage 01 (Portrait Library)**.
