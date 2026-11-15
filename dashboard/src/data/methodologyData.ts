/**
 * Structured data and constants for Stage 04 Methodology & Audit Section
 * All values verified against 15 November 2026 IST artifacts.
 */

export interface TimelineMilestone {
  date: string;
  phase: string;
  headline: string;
  problemEncountered: string;
  decisionTaken: string;
  testsRun?: string;
}

export interface ScenarioContingency {
  id: string;
  name: string;
  category: "all" | "batting" | "bowling" | "overseas";
  description: string;
  replacements: {
    role: "batting" | "bowling";
    dropped: string[];
    added: { name: string; type: string; reason: string }[];
  }[];
  strategicImplication: string;
}

export interface ModelComparisonRow {
  recipe: string;
  recipeLabel: string;
  testType: "2024–25 Forward Validation" | "2026 Retrospective" | "2025 Mega Auction Replay" | "2026 Mini Auction Replay";
  status: "retained" | "rejected";
  role: "Batting" | "Bowling";
  forwardMae: number;
  perSlotImpact: number;
  assessedPicks: string;
  evaluationNote: string;
}

export const TIMELINE_MILESTONES: TimelineMilestone[] = [
  {
    date: "10 Nov 2026",
    phase: "Day 01 · Ingestion & Defect Isolation",
    headline: "Raw Pack Delivery & Ledger Ingestion",
    problemEncountered:
      "Legacy ball-by-ball ledger misattributed wide-run categories, causing reconstruction to miss three of six chase targets by 1 to 4 runs and misrepresenting tie edge-cases.",
    decisionTaken:
      "Isolated 200,999 raw delivery rows across 806 regulation fixtures. Ingested corrected-extras pack and established 264 documented interpretations for ambiguous no-balls.",
    testsRun: "54 ingestion assertions",
  },
  {
    date: "11 Nov 2026",
    phase: "Day 02 · Scorecard Repair & Extras Alignment",
    headline: "Innings-State Reconstruction & Tie Interpretations",
    problemEncountered:
      "Non-regulation innings and boundary counting discrepancies skewed early overs run accounting and ball-in-over tracking.",
    decisionTaken:
      "Standardized legal-ball denominators and verified exact delivery accounting against official match scorecards across 708 usable fixtures.",
    testsRun: "72 scorecard alignment tests",
  },
  {
    date: "12 Nov 2026",
    phase: "Day 03 · Match-State Backtesting",
    headline: "Chronological Folds & Leverage Modeling",
    problemEncountered:
      "Static run-rate pressure definitions introduced lookahead bias by conditioning on match outcomes rather than the pre-ball state.",
    decisionTaken:
      "Built chronological match-state logistic win models and ridge expected-runs on 482 matches (2022–24) and 191 matches (2025). Established historical 80th-percentile pressure cutoffs strictly before each delivery.",
    testsRun: "128 match-state invariants",
  },
  {
    date: "13 Nov 2026",
    phase: "Day 04 · Leverage Calibration & Tier Cutoffs",
    headline: "Historical Percentile Thresholding",
    problemEncountered:
      "Dynamic run-chase pressure varied sharply between early powerplays and late death overs across competition tiers.",
    decisionTaken:
      "Calibrated 80th-percentile leverage cutoffs strictly on prior historical deliveries (e.g. 0.0254 for Tier-1 IPL 2nd-innings chases).",
    testsRun: "96 threshold calibration checks",
  },
  {
    date: "14 Nov 2026",
    phase: "Day 05 · Pack Refresh & Rebuild Verification",
    headline: "Recalibration with Recorded Extras",
    problemEncountered:
      "Organizer delivery pack update corrected 4,793 delivery pressure flags (including 1,888 IPL flags), altering late-innings leverage calculations.",
    decisionTaken:
      "Executed full pipeline rebuild on both raw sources in clean isolated scratch directories. Verified all 6 of 6 scorecard chase targets matched exactly before overrides.",
    testsRun: "232 unit & regression tests collected (all passed)",
  },
  {
    date: "15 Nov 2026",
    phase: "Day 06 · Model Tournament & Baseline Challenge",
    headline: "Selection Audit, Baseline Challenge & 1,000 Resamples",
    problemEncountered:
      "Challenged the bowling baseline against two real alternatives (Recency-Weighted IPL with 365-day half-life and Shrunk Pressure Uplift with harmonic partial pooling) on forward windows and auction pools.",
    decisionTaken:
      "Enforced strict promotion rules: rejected split-target and challenged alternatives to protect forecast accuracy. Retained incumbent baseline (Ablation B0) and Challenger D, and certified 1,000 cluster-bootstrap draws.",
    testsRun: "160 tournament evaluations & 1,000 stability resamples",
  },
];

export interface TierAggregateRow {
  tier: string;
  name: string;
  deliveries: number;
  fixtures: number;
  hpDeliveries: number;
  hpPct: number;
  boundaryPct: number;
  wicketPct: number;
  cutoff80th: string;
}

export const TIER_AGGREGATE_COMPARISON: TierAggregateRow[] = [
  {
    tier: "IPL (Tier 1)",
    name: "Indian Premier League",
    deliveries: 67577,
    fixtures: 280,
    hpDeliveries: 12264,
    hpPct: 18.15,
    boundaryPct: 20.17,
    wicketPct: 5.07,
    cutoff80th: "0.082 leverage (chase) / 0.114 (1st inn)",
  },
  {
    tier: "T20I (Tier 2)",
    name: "ICC Men's T20 Internationals",
    deliveries: 94589,
    fixtures: 400,
    hpDeliveries: 18564,
    hpPct: 19.63,
    boundaryPct: 16.84,
    wicketPct: 5.66,
    cutoff80th: "0.065 leverage (chase) / 0.098 (1st inn)",
  },
  {
    tier: "Emerging (Tier 3)",
    name: "Domestic / Emerging Leagues",
    deliveries: 6466,
    fixtures: 28,
    hpDeliveries: 510,
    hpPct: 7.89,
    boundaryPct: 14.80,
    wicketPct: 5.55,
    cutoff80th: "0.052 leverage (chase) / 0.080 (1st inn)",
  },
];

export interface SelectionStep {
  stepNum: string;
  title: string;
  populationCount: string;
  description: string;
  ruleId: string;
}

export const STEPPED_SELECTION_PIPELINE: SelectionStep[] = [
  {
    stepNum: "01",
    title: "Broad Cricket-Only Universe",
    populationCount: "248 Scored Players (118 Bat, 130 Bowl)",
    description: "Evaluated across all 806 regulation fixtures using legal-ball denominators and Bayesian volume shrinkage.",
    ruleId: "RULE_CRICKET_BROAD_POOL",
  },
  {
    stepNum: "02",
    title: "Recruitment Screen & Shortlist Assumptions",
    populationCount: "Actionable Recruitment Pool vs Non-Target Cohort",
    description: "Filters out players who fall outside current shortlist assumptions (e.g. core rival franchise stars like Bumrah, Narine, Hazlewood, Shreyas Iyer, Kohli) while isolating actionable targets and RR squad decisions.",
    ruleId: "RULE_OUTSIDE_SHORTLIST_ASSUMPTIONS",
  },
  {
    stepNum: "03",
    title: "RR Tactical Role Policy Enforcement",
    populationCount: "Role Minimums: ≥2 Finishers, ≥2 Middle, ≥3 Death, ≥2 Spin, ≥2 PP",
    description: "Enforces positional balance for Sawai Mansingh Stadium conditions. Promotes Ravindra Jadeja to Slot #10 for Jaipur spin defense.",
    ruleId: "RULE_ROLE_QUOTA_BALANCE",
  },
  {
    stepNum: "04",
    title: "Final 2027 Actionable Recommendation",
    populationCount: "20 Total Shortlisted (10 Batters, 10 Bowlers)",
    description: "Certified dual-discipline boards balancing high-leverage execution, verified stability, and contingency depth.",
    ruleId: "RULE_FINAL_RECOMMENDATION",
  },
];

export interface PlayerTransformationExample {
  playerName: string;
  role: "Batting" | "Bowling";
  rawModelRank: string;
  rawPriority: string;
  finalRROutcome: string;
  actionableRank: string;
  selectionPathExplanation: string;
  evidenceContrast: string;
}

export const WORKED_PLAYER_TRANSFORMATIONS: PlayerTransformationExample[] = [
  {
    playerName: "Jasprit Bumrah",
    role: "Bowling",
    rawModelRank: "#1 Machine Rank (+3.16 priority score, +4.34 forecast impact)",
    rawPriority: "+3.16 runs/12",
    finalRROutcome: "Outside current shortlist assumptions",
    actionableRank: "Outside current recruitment pool",
    selectionPathExplanation:
      "Bumrah dominates raw cricket impact (+3.16 priority score, +4.34 predicted composite impact, #1 bowling rank). However, he falls outside current shortlist assumptions because core rival franchise retention assumptions remove him from the actionable 2027 auction recruitment pool. Step 02 screens out players outside shortlist assumptions while preserving internal RR squad decisions.",
    evidenceContrast: "Raw priority score +3.16 -> Outside current shortlist assumptions (Rule RULE_OUTSIDE_SHORTLIST_ASSUMPTIONS).",
  },
  {
    playerName: "Ravindra Jadeja",
    role: "Bowling",
    rawModelRank: "#23 Broad Priority (#11 within eligible pool, priority -0.3076, +1.2807 predicted impact)",
    rawPriority: "-0.31 runs/12",
    finalRROutcome: "Promoted to RR #9 Bowler (RR squad decision)",
    actionableRank: "RR #9 Bowler (Spin Container)",
    selectionPathExplanation:
      "Under pure score-only unconstrained selection within the eligible pool, Deepak Chahar is #10 (priority -0.290) and Jadeja is #11 (priority -0.308). However, pure score produces 4 powerplay seamers and only 1 spinner (Krunal Pandya). RR's standard role policy requires 2 spinners for Jaipur pitch defense. Enforcing the two-spinner quota promotes Jadeja over Chahar at an imperceptible cost of 0.018 priority points, providing essential tactical spin balance as an internal RR squad decision (partnering Krunal Pandya #5).",
    evidenceContrast:
      "Model Rank #11 in eligible pool -> Promoted to RR #9 via Two-Spinner Tactical Quota (Rule RULE_ROLE_QUOTA_BALANCE). Recent 2026: +0.30 r/12 pressure vs +0.79 r/12 ordinary, +1.28 r/12 overall predicted impact.",
  },
  {
    playerName: "Jofra Archer (vs Trent Boult)",
    role: "Bowling",
    rawModelRank: "#25 Broad Priority (#13 in screened pool, priority -0.4274, +0.6438 forecast)",
    rawPriority: "-0.43 runs/12",
    finalRROutcome: "Selected as RR #10 Bowler (RR squad decision)",
    actionableRank: "RR #10 Bowler (New-Ball Pace Leader)",
    selectionPathExplanation:
      "Jofra Archer replaces Trent Boult as Rajasthan Royals' new-ball pace leader under an internal franchise squad decision. While Boult held a higher multi-season forecast (+1.40 vs +0.64), Archer demonstrated verified 2026 IPL pressure sample support (-1.98 r/12 across 106 balls in 13 matches vs Boult's -6.06 across 20 balls in 4 matches), took 25 wickets in 16 matches for RR, and avoids consuming a fresh overseas auction slot.",
    evidenceContrast:
      "Model Rank #13 in screened pool -> Selected as RR #10 (Rule RULE_RR_SQUAD_DECISION). Backs internal franchise continuity while trading away Boult's left-arm angle.",
  },
];

export const ARCHER_BOULT_TRADE_OFF_CASE = {
  title: "Audited RR Selection Decision: Jofra Archer over Trent Boult (No. 10 Bowling Slot)",
  subtitle: "Comparison of four verified empirical and contractual dimensions",
  facts: [
    {
      label: "IPL 2026 Pressure Impact per 12 Legal Balls",
      archer: "-1.98 runs/12 across 106 balls in 13 matches",
      boult: "-6.06 runs/12 across 20 balls in 4 matches",
      analysis: "Archer provides over 5x the recent pressure volume (106 vs 20 balls) and demonstrated significantly better run containment under high pressure."
    },
    {
      label: "Multi-Season Composite Forecast",
      archer: "+0.64 runs/12 predicted impact",
      boult: "+1.40 runs/12 predicted impact",
      analysis: "Boult led on multi-season point forecast due to historical career powerplay swing, but his recent IPL sample was narrow and negative across every match omission."
    },
    {
      label: "Official Season Context & Eliminator Audit",
      archer: "25 wickets in 16 matches for RR in IPL 2026",
      boult: "6 wickets in 8 matches for MI in IPL 2026",
      analysis: "In the 2026 Eliminator (SRH vs RR on 27 May 2026, Match 50943), RR won by 47 runs; peak second-innings leverage was 0.01595, remaining below the Q80 cutoff (0.025114) and explaining 0 HP balls."
    },
    {
      label: "Franchise & Roster Status",
      archer: "Internal RR squad asset; consumes no new overseas auction slot",
      boult: "Played IPL 2026 for Mumbai Indians; conditional on MI auction release",
      analysis: "Archer preserves franchise continuity and new-ball pace leadership for RR; selecting Archer trades away Boult's left-arm angle while preserving crucial auction budget."
    }
  ]
};

export const WORKED_CHASE_EXAMPLE = {
  fixture: "RCB vs MI · Match 54 (IPL 2026)",
  anchorUrl:
    "https://www.iplt20.com/news/article/tata-ipl-2026-match-54-rcb-v-mi-match-report",
  matchDate: "10 May 2026",
  context: "Innings 2, Official Chase Target: 167 runs (reconciled from preliminary Match 25 target draft)",
  ballSnapshot: "Over 20, Ball 10 (1 legal ball remaining; Raj Bawa bowling to Rasikh Salam)",
  scoreState: "RCB 165/8 (2 runs required from 1 legal ball, 2 wickets in hand)",
  savedPreBallLeverage: 0.335582,
  savedPreBallLeverageDisplay: "0.335582",
  historicalCutoff: 0.025364,
  historicalCutoffDisplay: "0.0254",
  isHighPressure: true,
  flagResult: "HIGH PRESSURE (True) — Pre-ball leverage (0.335582) ≥ historical 80th-percentile cutoff (0.0254)",
  attributionRule:
    "Strictly pre-ball: evaluated from the verified delivery ledger state (balls remaining = 1, runs required = 2, wickets in hand = 2, Innings 2, Tier-1 IPL). All intermediate win-probability and run-impact numbers not in official records are omitted to preserve audit integrity.",
  summary:
    "With 2 runs required from the final legal delivery, the match-state pre-ball win-probability leverage reached 0.335582 (33.56 percentage points of expected match-outcome swing). This exceeds the historical 80th-percentile IPL run-chase cutoff of 0.025364 (0.0254) by over 13x, confirming High Pressure without reliance on unverified intermediate estimates.",
};

export const MODEL_RECIPE_COMPARISON: ModelComparisonRow[] = [
  // --- 2024-25 Forward Validation (Held-out chronological folds) ---
  {
    recipe: "incumbent",
    recipeLabel: "Incumbent Retained Baseline (Ablation B0)",
    testType: "2024–25 Forward Validation",
    status: "retained",
    role: "Bowling",
    forwardMae: 3.94,
    perSlotImpact: 1.26,
    assessedPicks: "6.5 / 10",
    evaluationNote:
      "Baseline retained. Lowest forward MAE (3.94 r/12) and highest realized per-slot impact (+1.26 r/12) across 2024–25 cohorts with 6.50 assessed picks. Retained as primary bowling engine.",
  },
  {
    recipe: "recency_weighted_ipl",
    recipeLabel: "Challenger 1: Recency-Weighted IPL (365-Day Half-Life)",
    testType: "2024–25 Forward Validation",
    status: "rejected",
    role: "Bowling",
    forwardMae: 4.57,
    perSlotImpact: 0.75,
    assessedPicks: "5.25 / 10",
    evaluationNote:
      "Rejected. Degraded MAE by +0.63 r/12, suffered -0.51 r/12 impact deficit vs baseline, and lost -1.25 assessed picks.",
  },
  {
    recipe: "shrunk_pressure_uplift",
    recipeLabel: "Challenger 2: Shrunk Pressure Uplift (Partial Pooling)",
    testType: "2024–25 Forward Validation",
    status: "rejected",
    role: "Bowling",
    forwardMae: 4.46,
    perSlotImpact: 1.00,
    assessedPicks: "4.50 / 10",
    evaluationNote:
      "Rejected. Higher MAE (+0.52 r/12), lower impact (+1.00 vs +1.26), and dropped -2.00 assessed picks.",
  },
  {
    recipe: "split_targets",
    recipeLabel: "Split-Target Ridge (Usual + Pressure Uplift)",
    testType: "2024–25 Forward Validation",
    status: "rejected",
    role: "Bowling",
    forwardMae: 4.50,
    perSlotImpact: 0.54,
    assessedPicks: "5.75 / 10",
    evaluationNote:
      "Rejected. Severe -0.72 r/12 impact deficit vs baseline with higher forecast error.",
  },
  {
    recipe: "pressure_only",
    recipeLabel: "Pressure-Only Direct Model",
    testType: "2024–25 Forward Validation",
    status: "rejected",
    role: "Bowling",
    forwardMae: 4.22,
    perSlotImpact: 0.92,
    assessedPicks: "6.00 / 10",
    evaluationNote:
      "Rejected. Deficit of -0.34 r/12 vs baseline, penalizing powerplay pace lacking death opportunities.",
  },
  {
    recipe: "incumbent",
    recipeLabel: "Incumbent Retained Control (Challenger D)",
    testType: "2024–25 Forward Validation",
    status: "retained",
    role: "Batting",
    forwardMae: 4.20,
    perSlotImpact: 0.43,
    assessedPicks: "7.0 / 10",
    evaluationNote:
      "Retained control. Lowest forward MAE across 2024–26 with verified Bayesian volume shrinkage.",
  },
  {
    recipe: "split_targets",
    recipeLabel: "Split-Target Ridge (Usual + Pressure Uplift)",
    testType: "2024–25 Forward Validation",
    status: "rejected",
    role: "Batting",
    forwardMae: 4.87,
    perSlotImpact: 0.59,
    assessedPicks: "7.5 / 10",
    evaluationNote:
      "Rejected. Improved per-slot impact (+0.59 vs +0.43) but MAE inflated from 4.20 to 4.87 runs/12, failing promotion criteria.",
  },

  // --- 2026 Retrospective (Out-of-time season evaluation) ---
  {
    recipe: "incumbent",
    recipeLabel: "Incumbent Retained Baseline (2026 Retrospective)",
    testType: "2026 Retrospective",
    status: "retained",
    role: "Bowling",
    forwardMae: 4.34,
    perSlotImpact: 0.77,
    assessedPicks: "6.5 / 10",
    evaluationNote:
      "Baseline retained. Maintained robust positive impact (+0.77 r/12 per slot) across held-out 2026 IPL matches.",
  },
  {
    recipe: "shrunk_pressure_uplift",
    recipeLabel: "Challenger 2: Shrunk Pressure Uplift (2026 Retrospective)",
    testType: "2026 Retrospective",
    status: "rejected",
    role: "Bowling",
    forwardMae: 4.62,
    perSlotImpact: -0.58,
    assessedPicks: "4.0 / 10",
    evaluationNote:
      "Rejected. Regressed severely in 2026 (-0.58 r/12 vs +0.77 baseline) with only 4 assessed picks.",
  },
  {
    recipe: "split_targets",
    recipeLabel: "Split-Target Ridge (2026 Retrospective)",
    testType: "2026 Retrospective",
    status: "rejected",
    role: "Bowling",
    forwardMae: 4.60,
    perSlotImpact: -1.10,
    assessedPicks: "8.5 / 10",
    evaluationNote:
      "Rejected. Suffered deep negative regression (-1.10 r/12 per slot) despite higher assessed pick count.",
  },

  // --- Auction Replays (Simulated live auction offerings) ---
  {
    recipe: "incumbent",
    recipeLabel: "Incumbent Baseline (2025 Mega Auction Replay)",
    testType: "2025 Mega Auction Replay",
    status: "retained",
    role: "Bowling",
    forwardMae: 4.17,
    perSlotImpact: -0.28,
    assessedPicks: "7 / 10 assessed",
    evaluationNote:
      "Baseline retained. Outperformed recency challenger (-0.28 vs -0.53) with 7 of 10 offered picks playing IPL games.",
  },
  {
    recipe: "recency_weighted_ipl",
    recipeLabel: "Recency-Weighted IPL (2025 Mega Auction Replay)",
    testType: "2025 Mega Auction Replay",
    status: "rejected",
    role: "Bowling",
    forwardMae: 5.16,
    perSlotImpact: -0.53,
    assessedPicks: "4 / 10 assessed",
    evaluationNote:
      "Rejected. Suffered high MAE (5.16) and reduced playable picks (only 4 assessed).",
  },
  {
    recipe: "incumbent",
    recipeLabel: "Incumbent Baseline (2026 Mini Auction Replay)",
    testType: "2026 Mini Auction Replay",
    status: "retained",
    role: "Bowling",
    forwardMae: 4.28,
    perSlotImpact: -0.89,
    assessedPicks: "4 / 10 assessed",
    evaluationNote:
      "Baseline retained under known data limitation: Only 4 of 10 offered picks received IPL game time (-0.89 r/12). Retained because challengers degraded worse (-1.17 and -1.82).",
  },
  {
    recipe: "recency_weighted_ipl",
    recipeLabel: "Recency-Weighted IPL (2026 Mini Auction Replay)",
    testType: "2026 Mini Auction Replay",
    status: "rejected",
    role: "Bowling",
    forwardMae: 5.59,
    perSlotImpact: -1.17,
    assessedPicks: "2 / 10 assessed",
    evaluationNote:
      "Rejected. Extreme error inflation (5.59 MAE) and only 2 assessable picks.",
  },
  {
    recipe: "shrunk_pressure_uplift",
    recipeLabel: "Shrunk Pressure Uplift (2026 Mini Auction Replay)",
    testType: "2026 Mini Auction Replay",
    status: "rejected",
    role: "Bowling",
    forwardMae: 4.00,
    perSlotImpact: -1.82,
    assessedPicks: "3 / 10 assessed",
    evaluationNote:
      "Rejected. Severe negative realized impact (-1.82 r/12) on 3 assessable picks.",
  },
];

export const AUCTION_SCENARIOS: ScenarioContingency[] = [
  {
    id: "reference",
    name: "Scenario 0: Baseline Recommended Boards",
    category: "all",
    description: "The primary 15 November 2026 audit recommendation under current franchise squad assumptions.",
    replacements: [],
    strategicImplication:
      "Primary strategy for Rajasthan Royals: Vaibhav Sooryavanshi (#1) and Donovan Ferreira (#5) retained via internal RR squad decisions; Mohammed Siraj (#1) and Jason Holder (#2) pursued as conditional auction targets.",
  },
  {
    id: "gt_retains_pair",
    name: "Scenario A: Gujarat Titans Retains Siraj & Holder",
    category: "bowling",
    description: "GT uses its retention/RTM options on both Mohammed Siraj and Jason Holder, removing them from the auction pool.",
    replacements: [
      {
        role: "bowling",
        dropped: ["Mohammed Siraj (#1)", "Jason Holder (#2)"],
        added: [
          {
            name: "Deepak Chahar",
            type: "Indian New-Ball / Powerplay Pace",
            reason: "Strong powerplay strike rate with +2.81 r/12 impact across 2024–26.",
          },
          {
            name: "Mitchell Starc",
            type: "Overseas Left-Arm Pace",
            reason: "Closest bowling call to Boult; premier high-leverage death and powerplay bowler.",
          },
        ],
      },
    ],
    strategicImplication:
      "RR redirects premier auction purse from Siraj/Holder toward Deepak Chahar for domestic seam and Mitchell Starc for high-pace overseas leverage.",
  },
  {
    id: "gt_and_ngidi",
    name: "Scenario B: Gujarat Retains Both & Lungi Ngidi Unavailable",
    category: "bowling",
    description: "Siraj, Holder, and Lungi Ngidi are all retained or unavailable in the auction recruitment pool.",
    replacements: [
      {
        role: "bowling",
        dropped: ["Mohammed Siraj (#1)", "Jason Holder (#2)", "Lungi Ngidi (#4)"],
        added: [
          {
            name: "Deepak Chahar",
            type: "Indian Powerplay Seam",
            reason: "New-ball specialist with verified pressure execution.",
          },
          {
            name: "Mitchell Starc",
            type: "Overseas Express Pace",
            reason: "Death-overs enforcer with proven IPL final pedigree.",
          },
          {
            name: "Jamie Overton",
            type: "Overseas Middle-Overs Pace / Enforcer",
            reason: "Heavy-ball hit-the-deck bowler with middle-overs wicket equity.",
          },
        ],
      },
    ],
    strategicImplication:
      "Requires activating three consecutive reserve targets to maintain the required bowling quota (3 death, 2 spin, 2 powerplay).",
  },
  {
    id: "no_overseas_bowling",
    name: "Scenario C: RR Has Zero New Overseas Bowling Slots",
    category: "overseas",
    description: "Overseas purse restrictions or retention profile forces RR to recruit an entirely domestic seam arsenal.",
    replacements: [
      {
        role: "bowling",
        dropped: ["Jason Holder (#2)", "Lungi Ngidi (#4)", "Trent Boult (#7)"],
        added: [
          {
            name: "Avesh Khan",
            type: "Indian Express / Death Specialist",
            reason: "Verified death-overs workload with +1.74 r/12 pressure impact.",
          },
          {
            name: "Deepak Chahar",
            type: "Indian Swing / Powerplay",
            reason: "Replaces Boult's left-arm new-ball role with domestic swing.",
          },
          {
            name: "Jofra Archer",
            type: "RR Squad Roster Asset",
            reason: "Internal RR squad decision; world-class ceiling when physically available.",
          },
        ],
      },
    ],
    strategicImplication:
      "Preserves overseas slots for batting firepower; pairs Siraj with Avesh Khan and Deepak Chahar for an elite all-Indian pace attack.",
  },
  {
    id: "no_overseas_batting",
    name: "Scenario D: RR Has Zero New Overseas Batting Slots",
    category: "overseas",
    description: "RR allocates all available overseas spots to bowling/all-rounders and must field an all-Indian batting rotation.",
    replacements: [
      {
        role: "batting",
        dropped: ["Josh Inglis (#2)", "Cooper Connolly (#4)"],
        added: [
          {
            name: "Aniket Verma",
            type: "Indian Powerplay / Top Order",
            reason: "Rising domestic talent with strong powerplay boundary strike-rates.",
          },
          {
            name: "KL Rahul",
            type: "Indian Anchor / Middle Order",
            reason: "Proven volume accumulator with 500+ run seasonal floors.",
          },
        ],
      },
    ],
    strategicImplication:
      "Aniket Verma and KL Rahul step in to anchor the top/middle order alongside Parag and Sooryavanshi.",
  },
  {
    id: "compound_stress",
    name: "Scenario E: Compound Stress (No Overseas + Top 2 Unavailable)",
    category: "all",
    description: "Maximum auction constraint: Zero new overseas slots available and top two external targets unavailable.",
    replacements: [
      {
        role: "batting",
        dropped: ["Josh Inglis (#2)", "Cooper Connolly (#4)"],
        added: [
          {
            name: "Aniket Verma",
            type: "Indian Top-Order",
            reason: "Ranked #11 reserve in scenario audit.",
          },
          {
            name: "KL Rahul",
            type: "Indian Top/Middle-Order",
            reason: "Ranked #12 reserve in scenario audit.",
          },
          {
            name: "Shashank Singh",
            type: "Indian Finisher",
            reason: "High-strike-rate finisher (+4.12 r/12 in 2026 IPL death overs).",
          },
        ],
      },
      {
        role: "bowling",
        dropped: ["Mohammed Siraj (#1)", "Jason Holder (#2)", "Lungi Ngidi (#4)", "Trent Boult (#7)"],
        added: [
          {
            name: "Avesh Khan",
            type: "Indian Death Seam",
            reason: "Elite death execution.",
          },
          {
            name: "Deepak Chahar",
            type: "Indian Powerplay",
            reason: "Proven new-ball wicket taker.",
          },
          {
            name: "Jofra Archer",
            type: "RR Squad Decision",
            reason: "Direct franchise option.",
          },
          {
            name: "Mukesh Choudhary",
            type: "Indian Left-Arm Seam",
            reason: "Direct tactical replacement for Trent Boult's left-arm powerplay angle.",
          },
        ],
      },
    ],
    strategicImplication:
      "Exhaustive test case: 170 tested combinations confirm the candidate pool retains complete 10-man slates with valid role balance under severe stress.",
  },
];

export interface RawModelPlayer {
  id: string;
  name: string;
  deployment: string;
  role: "batting" | "bowling";
  priorityScore: number;
  baseEligible: boolean;
  status:
    | "rr_squad_decision"
    | "conditional_auction_target"
    | "outside_shortlist_assumptions"
    | "availability_unconfirmed";
  statusLabel: string;
  franchiseOrMarketContext: string;
  actionableRank?: number;
}

export const RAW_MODEL_BATTERS: RawModelPlayer[] = [
  {
    id: "50284",
    name: "Vaibhav Sooryavanshi",
    deployment: "POWERPLAY",
    role: "batting",
    priorityScore: 3.51,
    baseEligible: true,
    status: "rr_squad_decision",
    statusLabel: "RR squad decision",
    franchiseOrMarketContext: "RR in-squad prodigy (776 runs in IPL 2026). Retained as primary batting cornerstone.",
    actionableRank: 1,
  },
  {
    id: "4736",
    name: "Josh Inglis",
    deployment: "POWERPLAY",
    role: "batting",
    priorityScore: 2.80,
    baseEligible: true,
    status: "conditional_auction_target",
    statusLabel: "Conditional auction target",
    franchiseOrMarketContext: "LSG 2026 keeper-batter. Elite powerplay impact (+12.59 r/12). Primary auction target.",
    actionableRank: 2,
  },
  {
    id: "3647",
    name: "Shreyas Iyer",
    deployment: "MIDDLE",
    role: "batting",
    priorityScore: 2.05,
    baseEligible: false,
    status: "outside_shortlist_assumptions",
    statusLabel: "Outside current shortlist assumptions",
    franchiseOrMarketContext: "Core rival franchise retention candidate; outside current shortlist assumptions.",
  },
  {
    id: "818",
    name: "Mitchell Marsh",
    deployment: "POWERPLAY",
    role: "batting",
    priorityScore: 1.56,
    baseEligible: false,
    status: "outside_shortlist_assumptions",
    statusLabel: "Outside current shortlist assumptions",
    franchiseOrMarketContext: "Core rival overseas retention assumption; outside current recruitment screen.",
  },
  {
    id: "8238",
    name: "Sameer Rizvi",
    deployment: "MIDDLE",
    role: "batting",
    priorityScore: 1.50,
    baseEligible: true,
    status: "conditional_auction_target",
    statusLabel: "Conditional auction target",
    franchiseOrMarketContext: "DC 2026 young Indian middle-order accelerator. Major pressure uplift (+19.39 r/12).",
    actionableRank: 3,
  },
  {
    id: "7897",
    name: "Namboori Tilak Varma",
    deployment: "MIDDLE",
    role: "batting",
    priorityScore: 1.50,
    baseEligible: false,
    status: "outside_shortlist_assumptions",
    statusLabel: "Outside current shortlist assumptions",
    franchiseOrMarketContext: "Mumbai Indians core retention assumption. Outside current recruitment pool.",
  },
  {
    id: "8654",
    name: "Cooper Connolly",
    deployment: "MIDDLE",
    role: "batting",
    priorityScore: 1.26,
    baseEligible: true,
    status: "conditional_auction_target",
    statusLabel: "Conditional auction target",
    franchiseOrMarketContext: "PBKS 2026 left-hand middle-order prospect with 41 recent pressure balls across 6 matches.",
    actionableRank: 4,
  },
  {
    id: "8182",
    name: "Donovan Ferreira",
    deployment: "FINISHER",
    role: "batting",
    priorityScore: 1.02,
    baseEligible: true,
    status: "rr_squad_decision",
    statusLabel: "RR squad decision",
    franchiseOrMarketContext: "RR in-squad dynamic finisher. Backed through internal franchise retention.",
    actionableRank: 5,
  },
  {
    id: "47",
    name: "Virat Kohli",
    deployment: "POWERPLAY",
    role: "batting",
    priorityScore: 0.82,
    baseEligible: false,
    status: "outside_shortlist_assumptions",
    statusLabel: "Outside current shortlist assumptions",
    franchiseOrMarketContext: "RCB marquee retention assumption. Outside current recruitment screen.",
  },
  {
    id: "4260",
    name: "Heinrich Klaasen",
    deployment: "FINISHER",
    role: "batting",
    priorityScore: 0.78,
    baseEligible: false,
    status: "outside_shortlist_assumptions",
    statusLabel: "Outside current shortlist assumptions",
    franchiseOrMarketContext: "SRH core power-hitting retention assumption; outside shortlist assumptions.",
  },
  {
    id: "19714",
    name: "Abishek Porel",
    deployment: "POWERPLAY",
    role: "batting",
    priorityScore: 0.57,
    baseEligible: true,
    status: "conditional_auction_target",
    statusLabel: "Conditional auction target",
    franchiseOrMarketContext: "DC keeper-batter with 74 IPL pressure balls. Actionable auction target.",
    actionableRank: 6,
  },
  {
    id: "6423",
    name: "Riyan Parag",
    deployment: "MIDDLE",
    role: "batting",
    priorityScore: 0.48,
    baseEligible: true,
    status: "rr_squad_decision",
    statusLabel: "RR squad decision",
    franchiseOrMarketContext: "RR core middle-order leader. In-squad retention decision (425 of 1,000 resamples).",
    actionableRank: 7,
  },
  {
    id: "7216",
    name: "Prabhsimran Singh",
    deployment: "POWERPLAY",
    role: "batting",
    priorityScore: 0.47,
    baseEligible: true,
    status: "conditional_auction_target",
    statusLabel: "Conditional auction target",
    franchiseOrMarketContext: "PBKS aggressive powerplay opener. High volume candidate (195 balls).",
    actionableRank: 8,
  },
  {
    id: "152",
    name: "Ravindra Jadeja",
    deployment: "FINISHER",
    role: "batting",
    priorityScore: 0.03,
    baseEligible: true,
    status: "rr_squad_decision",
    statusLabel: "RR squad decision",
    franchiseOrMarketContext: "RR in-squad veteran dual-discipline finisher. Validated in both roles.",
    actionableRank: 9,
  },
  {
    id: "7544",
    name: "Venkatesh Iyer",
    deployment: "MIDDLE",
    role: "batting",
    priorityScore: -0.03,
    baseEligible: true,
    status: "conditional_auction_target",
    statusLabel: "Conditional auction target",
    franchiseOrMarketContext: "KKR left-hand middle-order depth. Actionable auction target.",
    actionableRank: 10,
  }
];

export const RAW_MODEL_BOWLERS: RawModelPlayer[] = [
  {
    id: "2933",
    name: "Jasprit Bumrah",
    deployment: "DEATH",
    role: "bowling",
    priorityScore: 3.16,
    baseEligible: false,
    status: "outside_shortlist_assumptions",
    statusLabel: "Outside current shortlist assumptions",
    franchiseOrMarketContext: "Ranks #1 in raw performance (+3.16 priority), but MI core retention assumption removes him from actionable recruitment pool.",
  },
  {
    id: "360",
    name: "Bhuvneshwar Kumar",
    deployment: "DEATH",
    role: "bowling",
    priorityScore: 3.08,
    baseEligible: false,
    status: "outside_shortlist_assumptions",
    statusLabel: "Outside current shortlist assumptions",
    franchiseOrMarketContext: "Elite pressure economy (+3.08), outside current shortlist assumptions.",
  },
  {
    id: "781",
    name: "Sunil Narine",
    deployment: "SPIN",
    role: "bowling",
    priorityScore: 3.02,
    baseEligible: false,
    status: "outside_shortlist_assumptions",
    statusLabel: "Outside current shortlist assumptions",
    franchiseOrMarketContext: "Dominant spin leverage (+3.02) across all phases. Rival core retention assumption.",
  },
  {
    id: "830",
    name: "Josh Hazlewood",
    deployment: "POWERPLAY",
    role: "bowling",
    priorityScore: 1.90,
    baseEligible: false,
    status: "outside_shortlist_assumptions",
    statusLabel: "Outside current shortlist assumptions",
    franchiseOrMarketContext: "Overseas seam anchor (+1.90), outside recruitment assumptions.",
  },
  {
    id: "5944",
    name: "Mohammed Siraj",
    deployment: "POWERPLAY",
    role: "bowling",
    priorityScore: 1.53,
    baseEligible: true,
    status: "conditional_auction_target",
    statusLabel: "Conditional auction target",
    franchiseOrMarketContext: "Gujarat Titans 2026 pace spearhead (130 recent balls). Prime external Indian pace target.",
    actionableRank: 1,
  },
  {
    id: "2633",
    name: "Jason Holder",
    deployment: "MIDDLE",
    role: "bowling",
    priorityScore: 1.14,
    baseEligible: true,
    status: "conditional_auction_target",
    statusLabel: "Conditional auction target",
    franchiseOrMarketContext: "GT 2026 tall bounce pace all-rounder. Strong recent impact (+2.26 uplift).",
    actionableRank: 2,
  },
  {
    id: "8530",
    name: "Kartik Tyagi",
    deployment: "DEATH",
    role: "bowling",
    priorityScore: 1.04,
    baseEligible: true,
    status: "conditional_auction_target",
    statusLabel: "Conditional auction target",
    franchiseOrMarketContext: "KKR 2026 express death bowler (+7.32 observed impact). Actionable auction target.",
    actionableRank: 3,
  },
  {
    id: "4641",
    name: "Lungi Ngidi",
    deployment: "DEATH",
    role: "bowling",
    priorityScore: 0.88,
    baseEligible: true,
    status: "conditional_auction_target",
    statusLabel: "Conditional auction target",
    franchiseOrMarketContext: "DC 2026 death-overs specialist (64 recent balls). High stability (76.0%).",
    actionableRank: 4,
  },
  {
    id: "3644",
    name: "Kuldeep Yadav",
    deployment: "SPIN",
    role: "bowling",
    priorityScore: 0.82,
    baseEligible: false,
    status: "outside_shortlist_assumptions",
    statusLabel: "Outside current shortlist assumptions",
    franchiseOrMarketContext: "DC marquee wrist-spinner. Core rival retention assumption.",
  },
  {
    id: "6256",
    name: "Varun Chakravarthy",
    deployment: "SPIN",
    role: "bowling",
    priorityScore: 0.78,
    baseEligible: false,
    status: "outside_shortlist_assumptions",
    statusLabel: "Outside current shortlist assumptions",
    franchiseOrMarketContext: "KKR mystery spin cornerstone. Outside current recruitment pool.",
  },
  {
    id: "4219",
    name: "Krunal Pandya",
    deployment: "SPIN",
    role: "bowling",
    priorityScore: 0.59,
    baseEligible: true,
    status: "conditional_auction_target",
    statusLabel: "Conditional auction target",
    franchiseOrMarketContext: "RCB 2026 left-arm orthodox spinner and pressure container. Actionable target.",
    actionableRank: 5,
  },
  {
    id: "7327",
    name: "Rasikh Salam",
    deployment: "DEATH",
    role: "bowling",
    priorityScore: 0.04,
    baseEligible: true,
    status: "conditional_auction_target",
    statusLabel: "Conditional auction target",
    franchiseOrMarketContext: "RCB 2026 skiddy death seamer (+3.25 observed impact; Match 23 4-wkt spell & Match 74 Final execution). Actionable target.",
    actionableRank: 6,
  },
  {
    id: "1566",
    name: "Mohammed Shami",
    deployment: "POWERPLAY",
    role: "bowling",
    priorityScore: -0.10,
    baseEligible: true,
    status: "conditional_auction_target",
    statusLabel: "Conditional auction target",
    franchiseOrMarketContext: "SRH 2026 veteran new-ball master. Actionable auction pick.",
    actionableRank: 7,
  },
  {
    id: "27964",
    name: "Anshul Kamboj",
    deployment: "POWERPLAY",
    role: "bowling",
    priorityScore: -0.24,
    baseEligible: true,
    status: "conditional_auction_target",
    statusLabel: "Conditional auction target",
    franchiseOrMarketContext: "CSK 2026 emerging domestic quick. Promoted over unverified injury candidate Harshit Rana (42/57 recent HP balls at death).",
    actionableRank: 8,
  },
  {
    id: "152",
    name: "Ravindra Jadeja",
    deployment: "SPIN",
    role: "bowling",
    priorityScore: -0.31,
    baseEligible: true,
    status: "rr_squad_decision",
    statusLabel: "RR squad decision",
    franchiseOrMarketContext: "RR in-squad defensive spin control (134 balls, +1.28 impact). Promoted to Slot #9 via 2-spinner quota.",
    actionableRank: 9,
  },
  {
    id: "3298",
    name: "Jofra Archer",
    deployment: "POWERPLAY",
    role: "bowling",
    priorityScore: -0.43,
    baseEligible: true,
    status: "rr_squad_decision",
    statusLabel: "RR squad decision",
    franchiseOrMarketContext: "RR in-squad right-arm new-ball pace leader (106 recent pressure balls, 25 wkts in 16 matches). Selected under RR squad decision; trades away Boult's left-arm angle without consuming new overseas auction slot.",
    actionableRank: 10,
  },
  {
    id: "2320",
    name: "Trent Boult",
    deployment: "POWERPLAY",
    role: "bowling",
    priorityScore: 0.02,
    baseEligible: true,
    status: "availability_unconfirmed",
    statusLabel: "Availability unconfirmed",
    franchiseOrMarketContext: "MI 2026 asset (traded 2025). External left-arm swing target conditional on MI official release.",
    actionableRank: undefined,
  }
];
