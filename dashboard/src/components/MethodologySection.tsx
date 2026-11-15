import React, { useState } from "react";
import type { EvidenceBundle } from "../data/types";
import bowlingBacktestData from "../data/bowling_backtest_results.json";
import { MathFormula } from "./MathFormula";
import { PlayerThumbnail } from "./PlayerThumbnail";
import {
  TIMELINE_MILESTONES,
  WORKED_CHASE_EXAMPLE,
  MODEL_RECIPE_COMPARISON,
  AUCTION_SCENARIOS,
  RAW_MODEL_BATTERS,
  RAW_MODEL_BOWLERS,
  TIER_AGGREGATE_COMPARISON,
  STEPPED_SELECTION_PIPELINE,
  WORKED_PLAYER_TRANSFORMATIONS,
  type ScenarioContingency,
} from "../data/methodologyData";
import {
  CheckIcon,
  CrossIcon,
  ChartIcon,
  FilterIcon,
  ShieldCheckIcon,
  ExternalLinkIcon,
} from "./Icons";

interface MethodologySectionProps {
  evidence: EvidenceBundle;
}

export const MethodologySection: React.FC<MethodologySectionProps> = ({
  evidence,
}) => {
  const [activeModule, setActiveModule] = useState<string>("01-what-rr-asked");
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>("reference");
  const [rawCategory, setRawCategory] = useState<"batting" | "bowling" | "filters">("batting");

  const selectedScenario: ScenarioContingency =
    AUCTION_SCENARIOS.find((s) => s.id === selectedScenarioId) ||
    AUCTION_SCENARIOS[0];

  const { data_funnel, verified_quantities, project_story } =
    evidence.modelling_overview;

  return (
    <section
      id="methodology"
      className="methodology-section"
      aria-labelledby="methodology-title"
    >
      <div className="methodology-container">
        {/* Navigation Return Bar */}
        <div className="section-return-bar" id="methodology-return-bar">
          <a href="#batters" className="btn-return-shortlist">
            ← Back to RR Shortlist
          </a>
          <div className="section-quick-links">
            <span className="quick-label">Jump to:</span>
            <a href="#batters" className="quick-link-pill">Batters</a>
            <a href="#bowlers" className="quick-link-pill">Bowlers</a>
            <a href="#model-rankings" className="quick-link-pill">Model Rankings</a>
          </div>
        </div>

        {/* =========================================================================
            HEADER & 60-SECOND SUMMARY (TWO-SPEED READ)
            ========================================================================= */}
        <div className="methodology-header">
          <span className="section-pill">Research & Verification Audit</span>
          <h2 id="methodology-title" className="section-heading">
            How I trained the model: Backtest, Calibration & Scenario Audit
          </h2>
          <p className="section-intro">
            A two-speed audit for Rajasthan Royals’ SupeRR Selector Season 2. Read
            the 60-second summary below to grasp the end-to-end pipeline, or
            inspect any of the eight detailed modules covering cricket logic,
            formulas, 160 model evaluations, and auction contingencies.
          </p>
        </div>

        {/* 60-Second Pipeline Stepper */}
        <div className="fast-read-card" aria-label="60-second pipeline overview">
          <div className="fast-read-header">
            <span className="fast-read-badge">The 60-Second Fast Read</span>
            <span className="fast-read-sub">From 200,999 Balls to 20 RR Picks</span>
          </div>

          <div className="pipeline-stepper-grid">
            <div className="step-card">
              <span className="step-num">01</span>
              <h4 className="step-title">Raw Data Ingestion</h4>
              <p className="step-desc">
                200,999 balls across 806 regulation fixtures. Ingested recorded
                extras, quarantined aliases, and verified 6 of 6 scorecard chase
                targets before overrides.
              </p>
            </div>

            <div className="step-card">
              <span className="step-num">02</span>
              <h4 className="step-title">Objective Pressure</h4>
              <p className="step-desc">
                Estimated pre-ball win probability swings via logistic regression.
                Pressure deliveries are strictly the historical top 20%
                (≥ 80th-percentile leverage) within match context.
              </p>
            </div>

            <div className="step-card">
              <span className="step-num">03</span>
              <h4 className="step-title">Player Impact Accounting</h4>
              <p className="step-desc">
                Measured relative run equivalents per 12 legal balls versus
                phase expectation, separating high-pressure deliveries from
                ordinary play to compute signed uplift.
              </p>
            </div>

            <div className="step-card">
              <span className="step-num">04</span>
              <h4 className="step-title">Ensemble Forecasting</h4>
              <p className="step-desc">
                Composite target blends 75% pressure impact + 25% ordinary impact
                via Bayesian shrinkage, Ridge regression, and shallow HistGBR
                with regularized bowling adjustments.
              </p>
            </div>

            <div className="step-card">
              <span className="step-num">05</span>
              <h4 className="step-title">Rigorous Verification</h4>
              <p className="step-desc">
                Audited across 160 model configurations, 1,000 whole-match
                cluster-bootstrap resamples, and 232+33 automated test assertions
                with zero synthetic data.
              </p>
            </div>
          </div>
        </div>

        {/* =========================================================================
            9 MODULE INTERACTIVE TAB NAVIGATION
            ========================================================================= */}
        <div className="module-nav-container">
          <h3 className="module-nav-heading">Deep-Dive Inspection Modules</h3>
          <div
            className="module-tab-bar"
            role="tablist"
            aria-label="Methodology Content Modules"
          >
            {[
              { id: "01-what-rr-asked", label: "01. What RR Asked" },
              { id: "02-timeline", label: "02. Project Timeline (10–15 Nov)" },
              { id: "03-data-transformations", label: "03. Data & Transformations" },
              { id: "04-pressure-definition", label: "04. Pressure Definition" },
              { id: "05-player-forecast", label: "05. Player Forecasting" },
              { id: "06-model-matrix", label: "06. How I Trained the Model" },
              { id: "07-confidence-stability", label: "07. Reading Confidence" },
              { id: "08-auction-contingencies", label: "08. Auction Scenarios" },
              { id: "09-raw-model-ranks", label: "09. Raw Model vs RR Shortlist" },
            ].map((tab) => (
              <button
                key={tab.id}
                role="tab"
                id={`tab-${tab.id}`}
                aria-selected={activeModule === tab.id}
                aria-controls={`panel-${tab.id}`}
                className={`module-tab-btn ${activeModule === tab.id ? "active" : ""}`}
                onClick={() => setActiveModule(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* =========================================================================
            MODULE 01: WHAT RR ASKED
            ========================================================================= */}
        {activeModule === "01-what-rr-asked" && (
          <div
            id="panel-01-what-rr-asked"
            role="tabpanel"
            aria-labelledby="tab-01-what-rr-asked"
            className="module-content-card"
          >
            <div className="module-header-block">
              <span className="module-eyebrow">Module 01</span>
              <h3 className="module-title">What Rajasthan Royals Asked</h3>
              <p className="module-summary">
                Problem statement scope, official challenge terms, and analytical evaluation boundaries.
              </p>
            </div>

            <div className="prose-content">
              <p>
                <strong>We compared how players perform in high-pressure situations with their usual performance and shortlisted roles RR could back.</strong>
              </p>
              <p>
                The Rajasthan Royals SupeRR Selector Season 2 (Round 1) brief
                tasks entrants with identifying and ranking <strong>10 batters</strong>{" "}
                and <strong>10 bowlers</strong> whom the franchise can reliably back
                under match pressure during the IPL 2027 campaign.
              </p>

              <div className="key-takeaways-box">
                <h4>Core Competition Directives:</h4>
                <ul>
                  <li>
                    <strong>Two Ranked Lists for RR Strategy:</strong> Exactly 10 batters and 10 bowlers shortlisted and ranked to shape Rajasthan Royals' IPL 2027 recruitment and squad assembly, distinguishing verified in-squad retentions from high-leverage conditional auction targets.
                  </li>
                  <li>
                    <strong>Freedom to Define Pressure:</strong> Entrants are
                    expressly granted methodological autonomy to formulate, justify,
                    and quantify what constitutes match pressure in T20 cricket.
                  </li>
                  <li>
                    <strong>Performance Relative to Usual Level:</strong> Entrants
                    must explain how recommended players perform under pressure
                    relative to their own ordinary baseline (signed uplift).
                  </li>
                  <li>
                    <strong>2027 Auction Strategy:</strong> The output serves as an
                    evidence-backed recommendation for Rajasthan Royals’ upcoming
                    squad assembly, distinguishing existing franchise assets from
                    conditional external auction targets.
                  </li>
                  <li>
                    <strong>Strict Temporal Boundary:</strong> All model fits,
                    evidence evaluations, and rankings are calibrated across 806 regulation fixtures up to the 2026 IPL season.
                  </li>
                </ul>
              </div>

              <p>
                Official Challenge Reference:{" "}
                <a
                  href="https://api.unstop.com/hackathons/crp-superr-selector-season-2-help-shape-rajasthan-royals-ipl-2027-auction-strategy-rajasthan-royals-1792758"
                  target="_blank"
                  rel="noreferrer"
                  className="external-audit-link"
                >
                  Unstop Challenge Portal · Rajasthan Royals SupeRR Selector S2 <ExternalLinkIcon size={12} className="inline-icon" />
                </a>
              </p>
            </div>
          </div>
        )}

        {/* =========================================================================
            MODULE 02: RESEARCH TIMELINE (10–15 NOV IST)
            ========================================================================= */}
        {activeModule === "02-timeline" && (
          <div
            id="panel-02-timeline"
            role="tabpanel"
            aria-labelledby="tab-02-timeline"
            className="module-content-card"
          >
            <div className="module-header-block">
              <span className="module-eyebrow">Module 02</span>
              <h3 className="module-title">
                Research Progression & Turning Points (10–15 Nov 2026 IST)
              </h3>
              <p className="module-summary">
                A verified chronological audit of data discoveries, model
                decisions, and repair milestones. Total compute hours and unique
                fits were unrecorded and are excluded from claims.
              </p>
            </div>

            <div className="timeline-flow-list">
              {TIMELINE_MILESTONES.map((m, idx) => (
                <div key={idx} className="timeline-entry">
                  <div className="timeline-marker">
                    <span className="marker-dot"></span>
                    <span className="marker-date">{m.date}</span>
                  </div>
                  <div className="timeline-details">
                    <span className="timeline-phase-tag">{m.phase}</span>
                    <h4 className="timeline-headline">{m.headline}</h4>
                    <p className="timeline-problem">
                      <strong>Problem Encountered:</strong> {m.problemEncountered}
                    </p>
                    <p className="timeline-decision">
                      <strong>Decision Taken:</strong> {m.decisionTaken}
                    </p>
                    {m.testsRun && (
                      <span className="timeline-test-badge">
                        Verified by: {m.testsRun}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <div className="audit-disclaimer-strip">
              <span>
                <strong>Audit Note:</strong> Project verification collected{" "}
                <strong>{project_story.verification_milestone.full_suite_tests} automated tests</strong>{" "}
                across the entire pipeline, followed by a focused rerun of{" "}
                <strong>{project_story.verification_milestone.targeted_post_repair_tests} contract tests</strong>{" "}
                confirming source preference, candidate selection, and scorekeeping.
              </span>
            </div>
          </div>
        )}

        {/* =========================================================================
            MODULE 03: DATA, EDA & TRANSFORMATIONS
            ========================================================================= */}
        {activeModule === "03-data-transformations" && (
          <div
            id="panel-03-data-transformations"
            role="tabpanel"
            aria-labelledby="tab-03-data-transformations"
            className="module-content-card"
          >
            <div className="module-header-block">
              <span className="module-eyebrow">Module 03</span>
              <h3 className="module-title">Data Funnel, Scorecards & Transformations</h3>
              <p className="module-summary">
                Filtering populations, resolving grain ambiguities, and
                validating scorecard targets.
              </p>
            </div>

            <div className="funnel-metrics-grid">
              <div className="funnel-box">
                <span className="funnel-number tabular-nums">
                  {data_funnel.raw_deliveries.toLocaleString()}
                </span>
                <span className="funnel-label">Raw Supplied Deliveries</span>
                <span className="funnel-sub">Across 883 match files</span>
              </div>
              <div className="funnel-box">
                <span className="funnel-number tabular-nums">
                  {data_funnel.eligible_fixtures}
                </span>
                <span className="funnel-label">Regulation Fixtures</span>
                <span className="funnel-sub">Excluding 77 abandonments/walkovers</span>
              </div>
              <div className="funnel-box">
                <span className="funnel-number tabular-nums">
                  {data_funnel.ranking_eligible_deliveries.toLocaleString()}
                </span>
                <span className="funnel-label">Rank-Eligible Deliveries</span>
                <span className="funnel-sub">Over 708 verified fixtures</span>
              </div>
            </div>

            <div className="prose-content">
              <h4>Table Grains & Pipeline Transformations:</h4>
              <p>
                The modeling pipeline enforces strict grain transitions: from raw{" "}
                <code>delivery</code> rows (indexed by match ID, innings, over, ball),
                to derived <code>match_state_snapshot</code> (pre-ball context), to{" "}
                <code>player_match_phase</code> aggregates, and finally to candidate
                selection profiles.
              </p>

              <div className="scorecard-comparison-card">
                <h4>Scorecard Repair: 6 of 6 Verified Chase Targets</h4>
                <p>
                  Before applying verified scorecard overrides, the legacy
                  reconstruction missed three of six chase targets (by 3, 4, and 1
                  runs) due to unparsed extra-run categories. The revised
                  reconstruction matched all six chase targets exactly:
                </p>
                <ul>
                  <li>
                    <strong>4,793 delivery pressure flags</strong> changed at the
                    80th-percentile threshold, including 1,888 IPL flags.
                  </li>
                  <li>
                    <strong>264 ambiguous no-ball events</strong> resolved through
                    documented standard cricket interpretations.
                  </li>
                  <li>
                    <strong>Rigorous Integrity Rules:</strong> Illegal deliveries do not advance legal-ball state (verified by pre-ball cumsum check); run-outs are strictly not credited to bowlers; free hits receive specific frequency adjustments.
                  </li>
                  <li>
                    Zero synthetic matches or interpolated deliveries were introduced
                    into training at any stage.
                  </li>
                </ul>
              </div>

              {/* IPL vs T20I Verified Aggregate Comparison */}
              <h4>Competition Tier Analysis: IPL vs T20I Benchmark Comparison</h4>
              <p>
                Pressure thresholds and baseline expectations are stratified strictly by competition tier to prevent cross-tournament distortion:
              </p>
              <div className="matrix-table-wrapper" style={{ marginTop: "10px" }}>
                <table className="method-comparison-table">
                  <thead>
                    <tr>
                      <th>Competition Tier</th>
                      <th>Tournament Name</th>
                      <th>Eligible Balls</th>
                      <th>Fixtures</th>
                      <th>Pressure Balls</th>
                      <th>Pressure %</th>
                      <th>Boundary Rate</th>
                      <th>Wicket Rate</th>
                      <th>80th Cutoff</th>
                    </tr>
                  </thead>
                  <tbody>
                    {TIER_AGGREGATE_COMPARISON.map((row, idx) => (
                      <tr key={idx} className={row.tier.startsWith("IPL") ? "row-retained" : ""}>
                        <td><strong>{row.tier}</strong></td>
                        <td>{row.name}</td>
                        <td className="tabular-nums font-bold">{row.deliveries.toLocaleString()}</td>
                        <td className="tabular-nums">{row.fixtures}</td>
                        <td className="tabular-nums">{row.hpDeliveries.toLocaleString()}</td>
                        <td className="tabular-nums font-bold">{row.hpPct.toFixed(2)}%</td>
                        <td className="tabular-nums">{row.boundaryPct.toFixed(2)}%</td>
                        <td className="tabular-nums">{row.wicketPct.toFixed(2)}%</td>
                        <td style={{ fontSize: "11px" }}>{row.cutoff80th}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* =========================================================================
            MODULE 04: WHAT COUNTS AS PRESSURE
            ========================================================================= */}
        {activeModule === "04-pressure-definition" && (
          <div
            id="panel-04-pressure-definition"
            role="tabpanel"
            aria-labelledby="tab-04-pressure-definition"
            className="module-content-card"
          >
            <div className="module-header-block">
              <span className="module-eyebrow">Module 04</span>
              <h3 className="module-title">
                What Counts as Pressure: Pre-Ball Leverage & Worked Example
              </h3>
              <p className="module-summary">
                Objective match-state win-probability swings versus subjective post-hoc
                narratives.
              </p>
            </div>

            <div className="prose-content">
              <p>
                <strong>Before the ball, we estimate how much realistic next-ball outcomes could move the match.</strong>
              </p>
              <p>
                Pressure is defined strictly from the state of the match{" "}
                <strong>before the ball is bowled</strong>, linking mathematical formulation directly to the codebase at{" "}
                <code style={{ fontSize: "11px", padding: "2px 6px", background: "#F1EBE4", borderRadius: "4px" }}>rr_pressure/pressure.py</code>.
                It evaluates how much plausible next-ball outcomes can shift the match outcome without any post-hoc lookahead bias:
              </p>

              <div className="formula-callout-box">
                <div className="formula-header">
                  <div className="formula-eyebrow">
                    <span className="eyebrow-dot" aria-hidden="true" />
                    <span>Mathematical Definition · rr_pressure/pressure.py</span>
                  </div>
                  <code className="formula-code-link">Pre-Ball Leverage Metric</code>
                </div>

                <h4 className="formula-title-main">
                  Pre-Ball Win-Probability Leverage (<MathFormula math="L_t" />)
                </h4>
                <p className="formula-subtitle">
                  Quantifies the expected variation in match win probability across all plausible legal outcomes <em>before</em> the delivery is bowled.
                </p>

                {/* Plain-Language Formula Explanations */}
                <div className="plain-formula-explainer" style={{ background: "#FFFFFF", padding: "12px 14px", borderRadius: "8px", border: "1px solid var(--color-ui-edge)", marginBottom: "16px" }}>
                  <p style={{ margin: "0 0 8px 0", fontSize: "13px", lineHeight: 1.5, color: "var(--color-navy)" }}>
                    <strong>Plain-Language Mechanics &amp; Units:</strong>
                  </p>
                  <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "12px", lineHeight: 1.55, color: "var(--color-ink)" }}>
                    <li>
                      <strong>1. Weighted Average (<MathFormula math="\mu_t" />):</strong> Calculates the expected successor win probability across all 6 plausible legal outcomes (dot, 1, 2, 4, 6, wicket), weighted by their empirical transition frequency in that match context (<MathFormula math="p_o" />). <em>Units: Probability [0.0, 1.0].</em>
                    </li>
                    <li>
                      <strong>2. Weighted Deviation / Leverage (<MathFormula math="L_t" />):</strong> Computes the mean absolute deviation between each outcome's win probability and the weighted average (<MathFormula math="\sum p_o |q_o - \mu_t|" />). Measures how violently the match hangs on the next delivery. <em>Units: Probability swing points [0.0, 1.0], where 0.01 = 1% match swing.</em>
                    </li>
                    <li>
                      <strong>3. Cutoff by Phase &amp; Tier (<MathFormula math="Q_{80}" />):</strong> Pressure cutoffs are calibrated strictly on historical data prior to the delivery. In Tier-1 IPL 2nd-innings chases, the 80th-percentile cutoff is <MathFormula math="Q_{80} = 0.025364" /> (displayed as <strong>0.0254</strong>). In first-innings setting phases, cutoffs range around <strong>0.0141–0.0144</strong> because 20 overs buffer individual ball variance.
                    </li>
                  </ul>
                </div>

                {/* Structured Mathematical Equations */}
                <div className="equations-showcase-grid">
                  <div className="equation-card">
                    <span className="equation-tag">Step 1 · Expected Successor Win Probability</span>
                    <MathFormula
                      displayMode={true}
                      math="\mu_t = \sum_{o \in \Omega} \bigl(p_o \cdot q_o\bigr)"
                      ariaLabel="Expected successor win probability equals sum over outcomes o in Omega of p_o times q_o"
                    />
                  </div>

                  <div className="equation-card">
                    <span className="equation-tag">Step 2 · Pre-Ball Win-Probability Leverage</span>
                    <MathFormula
                      displayMode={true}
                      math="L_t = \sum_{o \in \Omega} p_o \cdot \Bigl|\, q_o - \mu_t \,\Bigr|"
                      ariaLabel="Leverage L_t equals sum over outcomes o in Omega of p_o times absolute value of q_o minus mu_t"
                    />
                  </div>

                  <div className="equation-card full-width">
                    <span className="equation-tag">Step 3 · High-Pressure Binary Classification</span>
                    <MathFormula
                      displayMode={true}
                      math="\text{IsHighPressure}(t) = \mathbf{1}\Bigl[\, L_t \ge Q_{80}(\text{phase}_t, \text{tier}_t) \,\Bigr]"
                      ariaLabel="Delivery is high pressure if leverage L_t is greater than or equal to the 80th percentile cutoff for that match phase and tier"
                    />
                  </div>
                </div>

                {/* Structured Mathematical Glossary Grid */}
                <div className="parameters-glossary-grid">
                  <div className="param-item">
                    <span className="param-symbol">
                      <MathFormula math="S_t" /> (Match State)
                    </span>
                    <p className="param-desc">
                      Pre-ball state vector: balls remaining (<MathFormula math="b_t" />), runs required (<MathFormula math="r_t" />), wickets in hand (<MathFormula math="w_t" />), innings (<MathFormula math="i_t" />), and competition tier (<MathFormula math="\tau" />).
                    </p>
                  </div>

                  <div className="param-item">
                    <span className="param-symbol">
                      <MathFormula math="o \in \Omega" /> (Outcome Space)
                    </span>
                    <p className="param-desc">
                      Discrete set of mutually exclusive legal outcomes: <MathFormula math="\Omega = \{\text{dot}, 1, 2, 4, 6, \text{wicket}\}" />.
                    </p>
                  </div>

                  <div className="param-item">
                    <span className="param-symbol">
                      <MathFormula math="q_o = P(\text{Win} \mid S_t, o)" />
                    </span>
                    <p className="param-desc">
                      Successor win probability predicted by the chronological win-probability model if outcome <MathFormula math="o" /> occurs.
                    </p>
                  </div>

                  <div className="param-item">
                    <span className="param-symbol">
                      <MathFormula math="p_o" /> (Transition Prior)
                    </span>
                    <p className="param-desc">
                      Empirical transition frequency conditioned on venue scoring tier and phase, with free-hit overrides and resource-stress term.
                    </p>
                  </div>
                </div>

                <div className="cutoff-highlight-banner">
                  <strong>High-Pressure Classification Rule:</strong> Deliveries with pre-ball leverage <MathFormula math="L_t \ge Q_{80}(\text{phase}_t, \text{tier}_t)" /> (the historical 80th percentile for that match phase and competition tier) are classified as <strong>High Pressure</strong>. In IPL run chases, the 80th-percentile cutoff is <MathFormula math="L_{80} = 0.025364" /> (displayed as <strong>0.0254</strong>). In the Match 54 worked example below, pre-ball leverage reached <MathFormula math="L_t = 0.335582" /> (33.56 percentage points of expected variation), exceeding the threshold by more than 13x.
                </div>
              </div>

              <h4>Documented Sourced Chase Example:</h4>
              <div className="worked-example-card">
                <div className="we-header">
                  <span className="we-match">{WORKED_CHASE_EXAMPLE.fixture}</span>
                  <a
                    href={WORKED_CHASE_EXAMPLE.anchorUrl}
                    target="_blank"
                    rel="noreferrer"
                    style={{ fontSize: "11px", color: "var(--color-navy)", fontWeight: "bold", textDecoration: "underline" }}
                  >
                    Official BCCI Match 54 Report <ExternalLinkIcon size={11} className="inline-icon" />
                  </a>
                  <span className="we-context">{WORKED_CHASE_EXAMPLE.context}</span>
                </div>
                <div className="we-state-row">
                  <div>
                    <strong>Snapshot:</strong> {WORKED_CHASE_EXAMPLE.ballSnapshot}
                  </div>
                  <div>
                    <strong>Score:</strong> {WORKED_CHASE_EXAMPLE.scoreState}
                  </div>
                  <div>
                    <strong>Match Date:</strong> {WORKED_CHASE_EXAMPLE.matchDate}
                  </div>
                </div>

                {/* Sourced Delivery Ledger Parameters (Strictly from recorded evidence) */}
                <div style={{ background: "#FFFFFF", border: "1px solid var(--color-ui-edge)", borderRadius: "6px", padding: "12px 14px", margin: "12px 0" }}>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px" }}>
                    <div>
                      <span style={{ fontSize: "11px", color: "var(--color-secondary-text)", textTransform: "uppercase", display: "block" }}>
                        Saved Pre-Ball Leverage
                      </span>
                      <strong style={{ fontSize: "18px", color: "var(--color-navy)", fontFamily: "monospace" }}>
                        {WORKED_CHASE_EXAMPLE.savedPreBallLeverageDisplay}
                      </strong>
                      <span style={{ fontSize: "11px", color: "var(--color-ink)", display: "block", marginTop: "2px" }}>
                        (33.56% win-probability swing)
                      </span>
                    </div>

                    <div>
                      <span style={{ fontSize: "11px", color: "var(--color-secondary-text)", textTransform: "uppercase", display: "block" }}>
                        Historical IPL Chase Cutoff
                      </span>
                      <strong style={{ fontSize: "18px", color: "var(--color-ink)", fontFamily: "monospace" }}>
                        {WORKED_CHASE_EXAMPLE.historicalCutoffDisplay}
                      </strong>
                      <span style={{ fontSize: "11px", color: "var(--color-secondary-text)", display: "block", marginTop: "2px" }}>
                        (Exact: 0.025364 · Tier-1 Chase)
                      </span>
                    </div>

                    <div>
                      <span style={{ fontSize: "11px", color: "var(--color-secondary-text)", textTransform: "uppercase", display: "block" }}>
                        Classification Result
                      </span>
                      <span className="status-pill status-pass" style={{ fontSize: "12px", fontWeight: 800, padding: "4px 8px", display: "inline-block", marginTop: "2px" }}>
                        HIGH PRESSURE (True)
                      </span>
                      <span style={{ fontSize: "11px", color: "var(--color-accent-green)", display: "block", marginTop: "2px", fontWeight: 600 }}>
                        0.335582 ≥ 0.0254 (&gt;13x threshold)
                      </span>
                    </div>
                  </div>

                  <p style={{ margin: "10px 0 0 0", fontSize: "11.5px", lineHeight: 1.5, color: "var(--color-secondary-text)", borderTop: "1px solid #F1F5F9", paddingTop: "8px" }}>
                    <strong>Audit Integrity Notice:</strong> All intermediate win-probability or run-impact figures not present in official delivery records have been omitted. Pressure classification relies strictly on the pre-ball state in <code>scratch/rr_rebuild_recorded_20261115/delivery_impact_ledger.csv</code> and <code>pressure_thresholds.json</code>.
                  </p>
                </div>

                <div className="we-footer">
                  <div>
                    <strong>Ledger Provenance:</strong> {WORKED_CHASE_EXAMPLE.attributionRule}
                  </div>
                  <div className="we-status-badge">
                    {WORKED_CHASE_EXAMPLE.flagResult}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* =========================================================================
            MODULE 05: FROM EVENTS TO PLAYER FORECAST
            ========================================================================= */}
        {activeModule === "05-player-forecast" && (
          <div
            id="panel-05-player-forecast"
            role="tabpanel"
            aria-labelledby="tab-05-player-forecast"
            className="module-content-card"
          >
            <div className="module-header-block">
              <span className="module-eyebrow">Module 05</span>
              <h3 className="module-title">
                From Pressure Events to a Player Forecast
              </h3>
              <p className="module-summary">
                Impact accounting, Bayesian shrinkage, signed uplift, and role
                quotas.
              </p>
            </div>

            <div className="prose-content">
              <p>
                Individual player evaluation normalizes raw runs and dismissals
                against the contextual expectation for comparable deliveries, expressed
                as <strong>run equivalents per 12 legal balls</strong>.
              </p>

              <div className="ensemble-spec-grid">
                <div className="spec-card">
                  <h4>Target Formulation</h4>
                  <MathFormula
                    displayMode={true}
                    math="\text{Target}_i = 0.75 \cdot \widehat{\text{Impact}}_{\text{Pressure}, i} + 0.25 \cdot \widehat{\text{Impact}}_{\text{Ordinary}, i}"
                    ariaLabel="Target equals 75 percent pressure impact plus 25 percent ordinary impact"
                  />
                  <span className="spec-sub">
                    Prioritizes high-leverage execution (75%) while preserving baseline competence (25%).
                  </span>
                </div>
                <div className="spec-card">
                  <h4>Volume Shrinkage Penalty</h4>
                  <MathFormula
                    displayMode={true}
                    math="\widehat{\text{Impact}}_i = \frac{n_i}{n_i + \nu} \cdot \bar{y}_i + \frac{\nu}{n_i + \nu} \cdot \mu_0"
                    ariaLabel="Shrunk impact equals weight times observed performance plus weight times prior"
                  />
                  <span className="spec-sub">
                    Empirical Bayes: small samples (<MathFormula math="n_i" />) shrink aggressively toward population prior <MathFormula math="\mu_0 = 0.00" /> (<MathFormula math="\nu = 30" /> batting, <MathFormula math="24" /> bowling).
                  </span>
                </div>
                <div className="spec-card">
                  <h4>Signed Pressure Uplift</h4>
                  <MathFormula
                    displayMode={true}
                    math="\text{Uplift}_i = \text{Rate}_{\text{Pressure}, i} - \text{Rate}_{\text{Ordinary}, i}"
                    ariaLabel="Uplift equals pressure rate minus ordinary rate"
                  />
                  <span className="spec-sub">
                    Direct differential: isolates true clutch performance above the player's own ordinary rate.
                  </span>
                </div>
                <div className="spec-card">
                  <h4>Scouting Role Quotas</h4>
                  <p className="spec-quotas-text" style={{ fontSize: "12px", lineHeight: "1.5", margin: "6px 0" }}>
                    <strong>Batting:</strong> ≥ 2 Finishers, ≥ 2 Middle Order.<br />
                    <strong>Bowling:</strong> ≥ 3 Death, ≥ 2 Spin, ≥ 2 Powerplay.
                  </p>
                  <span className="spec-sub">
                    Ensures balanced XI squad construction aligned with Rajasthan Royals tactical constraints.
                  </span>
                </div>
              </div>

              <h4>Comparative Rate Example: Josh Inglis (Batters #2)</h4>
              <div className="rate-example-box">
                <div className="re-col">
                  <span className="re-label">Ordinary Baseline (118 balls)</span>
                  <span className="re-val tabular-nums val-pos">+4.92 r/12</span>
                </div>
                <div className="re-col">
                  <span className="re-label">Pressure Workload (24 balls)</span>
                  <span className="re-val tabular-nums val-pos">+13.49 r/12</span>
                </div>
                <div className="re-col">
                  <span className="re-label">Signed Uplift (Observed)</span>
                  <span className="re-val tabular-nums val-pos">+8.57 r/12</span>
                </div>
                <div className="re-col">
                  <span className="re-label">Shrunk Forecast Impact</span>
                  <span className="re-val tabular-nums font-bold">+4.70 r/12</span>
                </div>
              </div>

              <div className="shrinkage-step-card" style={{ marginTop: "12px", background: "#FFFFFF", border: "1px solid var(--color-ui-edge)", borderRadius: "8px", padding: "12px 16px" }}>
                <span style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", color: "var(--color-navy)", display: "block", marginBottom: "4px" }}>
                  Empirical Bayes Shrinkage Arithmetic:
                </span>
                <MathFormula
                  displayMode={true}
                  math="\widehat{\text{Impact}}_{\text{Inglis}} = \frac{24}{24 + 30} \times (+13.49) + \frac{30}{24 + 30} \times (0.00) = \frac{323.76}{54} \approx +4.70\text{ runs/12}"
                  ariaLabel="Josh Inglis shrinkage calculation"
                />
              </div>
              <p className="example-caption">
                *Inglis’s raw +13.49 r/12 pressure rate is discounted to +4.70
                runs/12 due to the 24-ball volume constraint, correctly keeping
                Vaibhav Sooryavanshi (+4.94 runs/12 over 63 pressure balls across 11
                matches) in the #1 position.
              </p>
            </div>
          </div>
        )}

        {/* =========================================================================
            MODULE 06: MODEL MATRIX & REPLAY AUDIT
            ========================================================================= */}
        {activeModule === "06-model-matrix" && (
          <div
            id="panel-06-model-matrix"
            role="tabpanel"
            aria-labelledby="tab-06-model-matrix"
            className="module-content-card"
          >
            <div className="module-header-block">
              <span className="module-eyebrow">Module 06</span>
              <h3 className="module-title">
                How I trained the model & checked it: Model Matrix & Retrospective Replays (160 Evaluations)
              </h3>
              <p className="module-summary">
                How I trained the model across 482 matches (2022–24) for match-state training, 191 in 2025 for validation, and 133 in 2026 replay, comparing the retained controls against 4 competing recipes across chronological forward windows and auction replays.
              </p>
            </div>

            <div className="prose-content">
              <div className="funnel-metrics-grid" style={{ marginBottom: "14px" }}>
                <div className="funnel-box">
                  <span className="funnel-number tabular-nums">
                    {verified_quantities.comparison_rows_total}
                  </span>
                  <span className="funnel-label">Total Matrix Rows</span>
                  <span className="funnel-sub">2 sources × 2 roles × 5 recipes × 8 windows</span>
                </div>
                <div className="funnel-box">
                  <span className="funnel-number tabular-nums">
                    {verified_quantities.recipes_count}
                  </span>
                  <span className="funnel-label">Model Recipes Tested</span>
                  <span className="funnel-sub">Incumbent vs 4 alternatives</span>
                </div>
                <div className="funnel-box">
                  <span className="funnel-number tabular-nums">
                    {verified_quantities.windows_per_role_per_source}
                  </span>
                  <span className="funnel-label">Evaluation Windows</span>
                  <span className="funnel-sub">Forward, auction replays, retrospective</span>
                </div>
              </div>

              <p>
                Exactly <strong>{verified_quantities.comparison_rows_total} comparison rows</strong> were evaluated across 2
                rebuild sources × 2 roles × 5 recipes × 8 evaluation windows. The
                retained models (Challenger D for batting and Ablation B0 for bowling)
                defeated all four alternatives:
              </p>

              <div className="matrix-table-wrapper">
                <table className="method-comparison-table">
                  <thead>
                    <tr>
                      <th>Test Benchmark</th>
                      <th>Recipe Name</th>
                      <th>Role</th>
                      <th>Status</th>
                      <th>Forward MAE (r/12)</th>
                      <th>Impact / Slot</th>
                      <th>Assessable Picks</th>
                      <th>Audit & Promotion Rationale</th>
                    </tr>
                  </thead>
                  <tbody>
                    {MODEL_RECIPE_COMPARISON.map((row, idx) => (
                      <tr
                        key={idx}
                        className={row.status === "retained" ? "row-retained" : ""}
                      >
                        <td style={{ fontSize: "11px", fontWeight: 700, color: "var(--color-navy)", whiteSpace: "nowrap" }}>
                          {row.testType}
                        </td>
                        <td>
                          <strong>{row.recipeLabel}</strong>
                        </td>
                        <td>{row.role}</td>
                        <td>
                          <span
                            className={`status-pill ${row.status === "retained" ? "status-pass" : "status-fail"}`}
                          >
                            {row.status.toUpperCase()}
                          </span>
                        </td>
                        <td className="tabular-nums font-bold">
                          {row.forwardMae.toFixed(2)}
                        </td>
                        <td className="tabular-nums">
                          {row.perSlotImpact >= 0 ? "+" : ""}
                          {row.perSlotImpact.toFixed(2)}
                        </td>
                        <td className="tabular-nums" style={{ fontSize: "11.5px", fontWeight: 600 }}>
                          {row.assessedPicks}
                        </td>
                        <td className="table-note">{row.evaluationNote}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div style={{ marginTop: "12px", padding: "10px 14px", background: "rgba(33, 150, 83, 0.08)", border: "1px solid rgba(33, 150, 83, 0.25)", borderRadius: "6px", display: "flex", alignItems: "center", gap: "10px" }}>
                <CheckIcon size={16} className="inline-check" />
                <span style={{ fontSize: "12px", color: "#1B5E20", fontWeight: 600 }}>
                  <strong>Formal Backtest Conclusion:</strong> The bowling baseline (Ablation B0 / Incumbent) was firmly <strong>retained</strong> across all gates. None of the challenger recipes met the promotion gate criteria (+0.25 r/12 impact gain without inflating MAE by &gt;0.15).
                </span>
              </div>

              {/* STAGE 02: BOWLING EXPERIMENT & DECISION GATE */}
              <div
                className="bowling-experiment-card"
                style={{
                  marginTop: "20px",
                  background: "#FFFDF9",
                  border: "1.5px solid var(--color-border-subtle)",
                  borderRadius: "8px",
                  padding: "16px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    flexWrap: "wrap",
                    gap: "8px",
                    marginBottom: "12px",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                    }}
                  >
                    <ShieldCheckIcon
                      width={18}
                      height={18}
                      color="var(--color-navy)"
                    />
                    <h4
                      style={{
                        margin: 0,
                        fontSize: "14px",
                        color: "var(--color-navy)",
                      }}
                    >
                      Stage 02 Bowling Experiment: Challenging the Baseline
                    </h4>
                  </div>
                  <span
                    className="status-pill status-pass"
                    style={{ fontSize: "11px", fontWeight: "bold" }}
                  >
                    DECISION GATE: RETAIN BASELINE
                  </span>
                </div>

                <p
                  style={{
                    fontSize: "12px",
                    lineHeight: 1.45,
                    color: "var(--color-ink)",
                    margin: "0 0 12px 0",
                  }}
                >
                  {bowlingBacktestData.decision_gate_summary.justification}
                </p>

                {/* DECISION MATRIX GRID */}
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                    gap: "10px",
                    marginBottom: "16px",
                  }}
                >
                  <div
                    style={{
                      padding: "10px",
                      background: "#FFFFFF",
                      border: "1px solid var(--color-ui-edge)",
                      borderRadius: "6px",
                    }}
                  >
                    <div
                      style={{
                        fontSize: "10px",
                        color: "var(--color-secondary-text)",
                        textTransform: "uppercase",
                      }}
                    >
                      Incumbent Baseline (B0)
                    </div>
                    <div
                      style={{
                        fontSize: "14px",
                        fontWeight: "bold",
                        color: "var(--color-rr-pink)",
                        marginTop: "2px",
                      }}
                    >
                      +1.26 r/12
                    </div>
                    <div
                      style={{
                        fontSize: "11px",
                        color: "var(--color-ink)",
                        marginTop: "2px",
                      }}
                    >
                      MAE 3.94 · 6.50 assessed
                    </div>
                    <div
                      style={{
                        fontSize: "10px",
                        color: "var(--color-accent-green)",
                        marginTop: "4px",
                        fontWeight: "600",
                      }}
                    >
                      Control Retained
                    </div>
                  </div>

                  <div
                    style={{
                      padding: "10px",
                      background: "#FFFFFF",
                      border: "1px solid var(--color-ui-edge)",
                      borderRadius: "6px",
                    }}
                  >
                    <div
                      style={{
                        fontSize: "10px",
                        color: "var(--color-secondary-text)",
                        textTransform: "uppercase",
                      }}
                    >
                      Challenger 1 (Recency IPL)
                    </div>
                    <div
                      style={{
                        fontSize: "14px",
                        fontWeight: "bold",
                        color: "var(--color-ink)",
                        marginTop: "2px",
                      }}
                    >
                      +0.75 r/12
                    </div>
                    <div
                      style={{
                        fontSize: "11px",
                        color: "var(--color-ink)",
                        marginTop: "2px",
                      }}
                    >
                      MAE 4.57 (+0.63) · 5.25 assessed
                    </div>
                    <div
                      style={{
                        fontSize: "10px",
                        color: "var(--color-accent-coral)",
                        marginTop: "4px",
                        fontWeight: "600",
                      }}
                    >
                      Failed MAE & Impact Gates
                    </div>
                  </div>

                  <div
                    style={{
                      padding: "10px",
                      background: "#FFFFFF",
                      border: "1px solid var(--color-ui-edge)",
                      borderRadius: "6px",
                    }}
                  >
                    <div
                      style={{
                        fontSize: "10px",
                        color: "var(--color-secondary-text)",
                        textTransform: "uppercase",
                      }}
                    >
                      Challenger 2 (Shrunk Uplift)
                    </div>
                    <div
                      style={{
                        fontSize: "14px",
                        fontWeight: "bold",
                        color: "var(--color-ink)",
                        marginTop: "2px",
                      }}
                    >
                      +1.00 r/12
                    </div>
                    <div
                      style={{
                        fontSize: "11px",
                        color: "var(--color-ink)",
                        marginTop: "2px",
                      }}
                    >
                      MAE 4.46 (+0.52) · 4.50 assessed
                    </div>
                    <div
                      style={{
                        fontSize: "10px",
                        color: "var(--color-accent-coral)",
                        marginTop: "4px",
                        fontWeight: "600",
                      }}
                    >
                      Failed Coverage (-2.00 picks)
                    </div>
                  </div>

                  <div
                    style={{
                      padding: "10px",
                      background: "#FFFFFF",
                      border: "1px solid var(--color-ui-edge)",
                      borderRadius: "6px",
                    }}
                  >
                    <div
                      style={{
                        fontSize: "10px",
                        color: "var(--color-secondary-text)",
                        textTransform: "uppercase",
                      }}
                    >
                      Split-Target Benchmark
                    </div>
                    <div
                      style={{
                        fontSize: "14px",
                        fontWeight: "bold",
                        color: "var(--color-ink)",
                        marginTop: "2px",
                      }}
                    >
                      +0.54 r/12
                    </div>
                    <div
                      style={{
                        fontSize: "11px",
                        color: "var(--color-ink)",
                        marginTop: "2px",
                      }}
                    >
                      MAE 4.50 (+0.55) · 5.75 assessed
                    </div>
                    <div
                      style={{
                        fontSize: "10px",
                        color: "var(--color-accent-coral)",
                        marginTop: "4px",
                        fontWeight: "600",
                      }}
                    >
                      Regressed in 2026 (-1.10)
                    </div>
                  </div>
                </div>

                {/* THREE CHOICE PAIR CASE STUDIES */}
                <h5
                  style={{
                    fontSize: "13px",
                    color: "var(--color-navy)",
                    margin: "12px 0 8px 0",
                  }}
                >
                  Candidate Choice Pairs & Tactical Allocation Analysis
                </h5>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "10px",
                  }}
                >
                  {bowlingBacktestData.choice_pair_diagnostics.pairs.map(
                    (pair, pIdx) => (
                      <div
                        key={pIdx}
                        style={{
                          background: "#FFFFFF",
                          border: "1px solid var(--color-ui-edge)",
                          borderRadius: "6px",
                          padding: "10px 12px",
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            flexWrap: "wrap",
                            gap: "6px",
                            marginBottom: "4px",
                          }}
                        >
                          <span
                            style={{
                              fontSize: "12px",
                              fontWeight: "bold",
                              color: "var(--color-navy)",
                            }}
                          >
                            {pair.pair_name}
                          </span>
                          <span
                            style={{
                              fontSize: "10px",
                              padding: "2px 6px",
                              background: "rgba(235, 13, 94, 0.08)",
                              color: "var(--color-rr-pink)",
                              borderRadius: "4px",
                              fontWeight: "600",
                            }}
                          >
                            {pair.role_slot}
                          </span>
                        </div>
                        <p
                          style={{
                            fontSize: "11px",
                            lineHeight: 1.4,
                            color: "var(--color-secondary-text)",
                            margin: 0,
                          }}
                        >
                          {pair.reasoning}
                        </p>
                      </div>
                    )
                  )}
                </div>
              </div>

              <div className="limitation-callout-card">
                <h4>Material Limitation Disclosed: Bowling Auction Replay</h4>
                <p>
                  The 2026 bowling auction replay returned{" "}
                  <strong>−0.89 observed composite impact per offered slot</strong>,
                  with subsequent evidence sufficient to assess only four of ten
                  picks. While the broader 2026 forward replay achieved +0.77 runs/12
                  per slot, this auction divergence is transparently documented as a
                  methodological limitation.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* =========================================================================
            MODULE 07: HOW TO READ CONFIDENCE
            ========================================================================= */}
        {activeModule === "07-confidence-stability" && (
          <div
            id="panel-07-confidence-stability"
            role="tabpanel"
            aria-labelledby="tab-07-confidence-stability"
            className="module-content-card"
          >
            <div className="module-header-block">
              <span className="module-eyebrow">Module 07</span>
              <h3 className="module-title">
                How to Read Confidence: Three Distinct Uncertainty Layers
              </h3>
              <p className="module-summary">
                Distinguishing player inclusion, exact slate concordance, and
                forecast error.
              </p>
            </div>

            <div className="three-layers-grid">
              <div className="layer-card">
                <span className="layer-badge">Layer 01</span>
                <h4>Individual Top-10 Stability</h4>
                <p className="layer-stat">
                  Vaibhav: 95.8% · Parag: 42.5% · Siraj: 89.4%
                </p>
                <p className="layer-desc">
                  Fraction of 1,000 whole-match cluster bootstrap resamples in which a player appears anywhere in Rajasthan Royals’ top 10. In everyday language: <strong>Riyan Parag’s 42.5% stability means 425 of 1,000 match resamples included him in the batting top 10</strong> under simulated fixture and schedule perturbations. Median stability is <strong>47.3%</strong> for batting and <strong>55.3%</strong> for bowling.
                </p>
              </div>

              <div className="layer-card">
                <span className="layer-badge">Layer 02</span>
                <h4>Exact-List Concordance</h4>
                <p className="layer-stat">0 of 1,000 Repeats</p>
                <p className="layer-desc">
                  The probability of reproducing the exact 10-man slate in identical
                  order is <strong>0.0%</strong>. However, 8+ of the recommended 10
                  names co-occur in 3.4% of batting draws and 4.1% of bowling draws.
                </p>
              </div>

              <div className="layer-card">
                <span className="layer-badge">Layer 03</span>
                <h4>Forecast Error (MAE)</h4>
                <p className="layer-stat">
                  Bat: ~4.20 · Bowl: ~4.34 r/12
                </p>
                <p className="layer-desc">
                  Mean absolute error of forward-chaining predictions on held-out
                  windows (lower is better). Indicates realistic bounds on
                  per-match scoring variation.
                </p>
              </div>
            </div>

            <div className="prose-content">
              <h4>Audited Close Calls:</h4>
              <ul>
                <li>
                  <strong>Trent Boult (#7) vs Mitchell Starc:</strong> Boult recorded
                  negative 2026 pressure impact (-6.06 runs/12). Starc performed better
                  in 2026, but Boult led Starc in powerplay impact and ball volume
                  across 2024–25 and retained the lead in the full model. Starc remains
                  the direct backup for overseas left-arm pace.
                </li>
                <li>
                  <strong>Prabhsimran Singh (#8) vs KL Rahul:</strong> Prabhsimran
                  achieved +3.57 runs/12 across 41 pressure balls and remained positive
                  under all single-match omissions, whereas Rahul recorded -1.82
                  runs/12 across 84 balls.
                </li>
              </ul>
              <p className="caveat-italic">
                *Statistical stability and backtest errors describe historical model
                behavior and cannot guarantee 2027 auction availability or live match
                outcomes.
              </p>
            </div>
          </div>
        )}

        {/* =========================================================================
            MODULE 08: AUCTION SCENARIOS & WHAT-IF CONTINGENCIES
            ========================================================================= */}
        {activeModule === "08-auction-contingencies" && (
          <div
            id="panel-08-auction-contingencies"
            role="tabpanel"
            aria-labelledby="tab-08-auction-contingencies"
            className="module-content-card"
          >
            <div className="module-header-block">
              <span className="module-eyebrow">Module 08</span>
              <h3 className="module-title">
                Auction Actionability: What-If Contingency Planner
              </h3>
              <p className="module-summary">
                Explore verified backup slates across 170 tested availability and
                purse scenarios.
              </p>
            </div>

            {/* Interactive Scenario Buttons */}
            <div className="scenario-selector-row">
              <span className="selector-label">Select Contingency Scenario:</span>
              <div className="scenario-btn-group">
                {AUCTION_SCENARIOS.map((sc) => (
                  <button
                    key={sc.id}
                    type="button"
                    className={`scenario-btn ${selectedScenarioId === sc.id ? "active" : ""}`}
                    onClick={() => setSelectedScenarioId(sc.id)}
                  >
                    {sc.name.split(":")[0]}
                  </button>
                ))}
              </div>
            </div>

            {/* Selected Scenario Dynamic Card */}
            <div className="scenario-dynamic-display">
              <div className="scenario-display-header">
                <h4 className="scenario-headline">{selectedScenario.name}</h4>
                <p className="scenario-desc">{selectedScenario.description}</p>
              </div>

              {selectedScenario.replacements.length > 0 ? (
                <div className="scenario-replacements-grid">
                  {selectedScenario.replacements.map((rep, idx) => (
                    <div key={idx} className="replacement-card">
                      <span className="rep-role-tag">{rep.role.toUpperCase()} ADJUSTMENTS</span>
                      <div className="dropped-list">
                        <strong>Dropped from Top 10:</strong>
                        <ul>
                          {rep.dropped.map((d, i) => (
                            <li key={i} className="dropped-item">
                              <CrossIcon size={12} className="inline-cross" /> {d}
                            </li>
                          ))}
                        </ul>
                      </div>
                      <div className="added-list">
                        <strong>Replacement Candidates:</strong>
                        <ul>
                          {rep.added.map((a, i) => (
                            <li key={i} className="added-item">
                              <span className="added-name">
                                <CheckIcon size={12} className="inline-check" /> {a.name}
                              </span>
                              <span className="added-type">({a.type})</span>
                              <span className="added-reason">— {a.reason}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="scenario-baseline-note">
                  <p>
                    <strong>Baseline Slate Active:</strong> Showing the canonical 10
                    Batters and 10 Bowlers recommended in the main boards above. All
                    squad decisions and conditional auction targets are fully eligible.
                  </p>
                </div>
              )}

              <div className="scenario-implication-strip">
                <span className="implication-label">Strategic Implication for RR:</span>
                <span className="implication-text">
                  {selectedScenario.strategicImplication}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* =========================================================================
            MODULE 09: RAW MODEL RESULTS VS RAJASTHAN ROYALS ACTIONABLE SHORTLIST
            ========================================================================= */}
        {activeModule === "09-raw-model-ranks" && (
          <div
            id="panel-09-raw-model-ranks"
            role="tabpanel"
            aria-labelledby="tab-09-raw-model-ranks"
            className="module-content-card"
          >
            <div className="module-header-block">
              <span className="module-eyebrow">Module 09 · Direct Algorithmic Output</span>
              <h3 className="module-title">
                Raw Model Results vs. Rajasthan Royals Actionable Shortlist
              </h3>
              <p className="module-summary">
                Before applying franchise retention locks and Rajasthan Royals squad balance rules,
                what did the raw mathematical model predict? This audit reveals the unfiltered
                algorithmic leaderboard, demonstrating why statistical superstars like Jasprit Bumrah
                (+3.16) and Sunil Narine (+3.02) topped the machine ranking, and how our 3-stage
                operational filter transformed them into Rajasthan Royals' actionable 2027 auction slate.
              </p>
            </div>

            {/* Stepped Selection Transformation Pipeline */}
            <div style={{ marginBottom: "16px" }}>
              <h4 style={{ fontSize: "13px", color: "var(--color-navy)", margin: "0 0 8px 0" }}>
                Stepped Selection Pipeline: From Machine Scores to RR Shortlist
              </h4>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "10px" }}>
                {STEPPED_SELECTION_PIPELINE.map((st, sIdx) => (
                  <div
                    key={sIdx}
                    style={{
                      background: "#FFFFFF",
                      border: "1.5px solid var(--color-border-subtle)",
                      borderRadius: "6px",
                      padding: "10px 12px",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                      <span style={{ fontSize: "11px", fontWeight: "bold", color: "var(--color-rr-pink)" }}>
                        Step {st.stepNum}
                      </span>
                      <code style={{ fontSize: "9px", padding: "1px 4px", background: "#F1EBE4", borderRadius: "3px" }}>
                        {st.ruleId}
                      </code>
                    </div>
                    <div style={{ fontSize: "12px", fontWeight: "bold", color: "var(--color-navy)", marginBottom: "2px" }}>
                      {st.title}
                    </div>
                    <div style={{ fontSize: "11px", fontWeight: "600", color: "var(--color-ink)", marginBottom: "4px" }}>
                      {st.populationCount}
                    </div>
                    <p style={{ fontSize: "10.5px", lineHeight: "1.35", color: "var(--color-secondary-text)", margin: 0 }}>
                      {st.description}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Two Verified Worked Player Movement Case Studies */}
            <div style={{ marginBottom: "20px" }}>
              <h4 style={{ fontSize: "13px", color: "var(--color-navy)", margin: "0 0 8px 0" }}>
                Verified Player Movement Case Studies: Machine Rank vs RR Decision
              </h4>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "12px" }}>
                {WORKED_PLAYER_TRANSFORMATIONS.map((c, cIdx) => (
                  <div
                    key={cIdx}
                    style={{
                      background: "#FFFFFF",
                      border: "1.5px solid var(--color-ui-edge)",
                      borderRadius: "8px",
                      padding: "12px 14px",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                      <span style={{ fontSize: "13px", fontWeight: "bold", color: "var(--color-navy)" }}>
                        {c.playerName} ({c.role})
                      </span>
                      <span
                        className={`status-pill ${c.finalRROutcome.startsWith("PROMOTED") ? "status-pass" : "status-fail"}`}
                        style={{ fontSize: "10px" }}
                      >
                        {c.finalRROutcome}
                      </span>
                    </div>
                    <div style={{ display: "flex", gap: "12px", fontSize: "11px", marginBottom: "6px" }}>
                      <span><strong>Raw Rank:</strong> {c.rawModelRank} ({c.rawPriority})</span>
                      <span><strong>RR Board:</strong> {c.actionableRank}</span>
                    </div>
                    <p style={{ fontSize: "11px", lineHeight: "1.4", color: "var(--color-ink)", margin: "0 0 6px 0" }}>
                      {c.selectionPathExplanation}
                    </p>
                    <div style={{ fontSize: "10px", color: "var(--color-secondary-text)", fontStyle: "italic" }}>
                      {c.evidenceContrast}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Sub-navigation Controls */}
            <div className="raw-subnav-row" role="tablist" aria-label="Raw model viewing subcategory">
              <button
                type="button"
                className={`raw-subnav-btn ${rawCategory === "batting" ? "active" : ""}`}
                onClick={() => setRawCategory("batting")}
              >
                <ChartIcon size={14} />
                <span>Raw Batters Leaderboard (Top 15)</span>
              </button>
              <button
                type="button"
                className={`raw-subnav-btn ${rawCategory === "bowling" ? "active" : ""}`}
                onClick={() => setRawCategory("bowling")}
              >
                <ChartIcon size={14} />
                <span>Raw Bowlers Leaderboard (Top 15)</span>
              </button>
              <button
                type="button"
                className={`raw-subnav-btn ${rawCategory === "filters" ? "active" : ""}`}
                onClick={() => setRawCategory("filters")}
              >
                <FilterIcon size={14} />
                <span>The 3 RR Tactical Filters Explained</span>
              </button>
            </div>

            {rawCategory === "filters" ? (
              <div className="raw-filters-explanation-panel">
                <div className="filter-pillar-card">
                  <div className="filter-pillar-header">
                    <span className="pillar-num">Filter 01</span>
                    <h4 className="pillar-title">Recruitment Screen &amp; Shortlist Assumptions</h4>
                  </div>
                  <p className="pillar-desc">
                    Raw machine models evaluate every player in the dataset regardless of legal availability.
                    However, world-class performers like <strong>Jasprit Bumrah (Raw Bowling #1, +3.16 priority)</strong>,{" "}
                    <strong>Sunil Narine (Raw Bowling #3, +3.02)</strong>, <strong>Shreyas Iyer (Raw Batting #3, +2.05)</strong>, and{" "}
                    <strong>Tilak Varma (Raw Batting #6, +1.50)</strong> fall <strong>outside current shortlist assumptions</strong> because core rival franchise retention assumptions remove them from the actionable recruitment pool.
                    Recommending unavailable players to Rajasthan Royals for an auction strategy is actionable malpractice.
                    Filter 01 screens out non-target assumptions while preserving internal RR squad decisions.
                  </p>
                </div>

                <div className="filter-pillar-card">
                  <div className="filter-pillar-header">
                    <span className="pillar-num">Filter 02</span>
                    <h4 className="pillar-title">Rajasthan Royals Tactical Role Blueprint</h4>
                  </div>
                  <p className="pillar-desc">
                    A raw model simply takes the top 10 scores, which would create fatal structural imbalances
                    (e.g., selecting 7 powerplay batters and zero death bowlers). RR's verified squad construction requires:
                  </p>
                  <ul className="pillar-specs-list">
                    <li><strong>Batting Coverage:</strong> At least 2 Finishers (Donovan Ferreira, Ravindra Jadeja), 2 Middle-Order anchors (Sameer Rizvi, Cooper Connolly, Riyan Parag, Venkatesh Iyer), and explosive Powerplay cover (Vaibhav Sooryavanshi, Josh Inglis, Abishek Porel, Prabhsimran Singh).</li>
                    <li><strong>Bowling Arsenal:</strong> At least 3 Death-over specialists (Kartik Tyagi, Lungi Ngidi, Rasikh Salam), 2 Spin containers (Krunal Pandya, Ravindra Jadeja), and New-Ball seam pressure (Mohammed Siraj, Jason Holder, Trent Boult, Mohammed Shami, Anshul Kamboj).</li>
                  </ul>
                </div>

                <div className="filter-pillar-card">
                  <div className="filter-pillar-header">
                    <span className="pillar-num">Filter 03</span>
                    <h4 className="pillar-title">Real-World Scouting Overrides & Health Status</h4>
                  </div>
                  <p className="pillar-desc">
                    Machine forecasts are calibrated with real-world intelligence:
                    <strong> Anshul Kamboj</strong> was promoted over Harshit Rana after verifying Rana missed IPL 2026 and suffered an unverified injury setback.
                    Similarly, <strong>Mohammed Siraj</strong> and <strong>Jason Holder</strong> are tagged as conditional release targets pending Gujarat Titans' official retention announcement.
                  </p>
                </div>
              </div>
            ) : (
              <div className="raw-rankings-table-container">
                <div className="raw-table-meta-bar">
                  <span className="table-caption-badge">
                    {rawCategory === "batting" ? "Unfiltered Batting Model Predictions" : "Unfiltered Bowling Model Predictions"}
                  </span>
                  <span className="table-caption-sub">
                    Direct Bayesian regression outputs across 806 matches before franchise exclusion
                  </span>
                </div>

                <div className="raw-table-scroll-wrapper">
                  <table className="raw-comparison-table" aria-label="Raw model rankings vs RR shortlist table">
                    <thead>
                      <tr>
                        <th scope="col" className="th-machine-rank">Machine Rank</th>
                        <th scope="col" className="th-player">Player &amp; Role</th>
                        <th scope="col" className="th-priority">Raw Model Priority</th>
                        <th scope="col" className="th-market-status">Franchise / Market Status</th>
                        <th scope="col" className="th-rr-outcome">RR 2027 Outcome</th>
                        <th scope="col" className="th-scout-rationale">Scouting &amp; Tactical Rationale</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(rawCategory === "batting" ? RAW_MODEL_BATTERS : RAW_MODEL_BOWLERS).map((p, idx) => {
                        const isRRShortlisted = p.actionableRank !== undefined;
                        const isOutside = p.status === "outside_shortlist_assumptions";
                        const isRRRetained = p.status === "rr_squad_decision";

                        return (
                          <tr
                            key={`raw-${p.role}-${p.id}`}
                            className={`raw-table-row ${isRRShortlisted ? "is-shortlisted" : "is-excluded"}`}
                          >
                            <td className="td-machine-rank">
                              <span className="machine-rank-badge">#{idx + 1}</span>
                            </td>
                            <td className="td-player">
                              <div className="raw-player-cell">
                                <PlayerThumbnail playerId={p.id} name={p.name} size={42} />
                                <div className="raw-player-meta">
                                  <strong className="raw-player-name">{p.name}</strong>
                                  <span className="raw-deployment-tag">{p.deployment}</span>
                                </div>
                              </div>
                            </td>
                            <td className="td-priority tabular-nums">
                              <span className={`priority-val ${p.priorityScore >= 0 ? "val-pos" : "val-neg"}`}>
                                {p.priorityScore >= 0 ? `+${p.priorityScore.toFixed(2)}` : p.priorityScore.toFixed(2)}
                              </span>
                              <span className="priority-sub">runs/12</span>
                            </td>
                            <td className="td-market-status">
                              <span
                                className={`market-status-pill ${
                                  isOutside
                                    ? "status-outside"
                                    : isRRRetained
                                    ? "status-rr"
                                    : "status-auction"
                                }`}
                              >
                                {isOutside && <CrossIcon size={12} className="inline-cross" />}
                                {isRRShortlisted && <CheckIcon size={12} className="inline-check" />}
                                {p.statusLabel}
                              </span>
                            </td>
                            <td className="td-rr-outcome">
                              {isRRShortlisted ? (
                                <div className="rr-target-badge">
                                  <span className="target-num">RR #{p.actionableRank}</span>
                                  <span className="target-label">{isRRRetained ? "In-Squad" : "Auction"}</span>
                                </div>
                              ) : (
                                <span className="rr-filtered-badge">
                                  <CrossIcon size={11} className="inline-cross" /> Non-Target
                                </span>
                              )}
                            </td>
                            <td className="td-scout-rationale">
                              <p className="rationale-text">{p.franchiseOrMarketContext}</p>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                <div className="raw-table-legend-footer">
                  <div className="legend-item">
                    <span className="legend-indicator status-auction" />
                    <span><strong>Conditional auction target:</strong> External target shortlisted by RR; auction entry pending official franchise release lists.</span>
                  </div>
                  <div className="legend-item">
                    <span className="legend-indicator status-rr" />
                    <span><strong>RR squad decision:</strong> Internal Rajasthan Royals squad asset certified by model metrics and franchise control.</span>
                  </div>
                  <div className="legend-item">
                    <span className="legend-indicator status-outside" />
                    <span><strong>Outside current shortlist assumptions:</strong> Highly rated by algorithm but core rival franchise retention assumptions remove player from recruitment pool.</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
};
