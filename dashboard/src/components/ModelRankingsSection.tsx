import React, { useState, useMemo } from "react";
import modelRankingsData from "../data/model_rankings_data.json";
import { getAnchorId } from "../data/formatters";
import type { RoleType } from "../data/types";
import { PlayerThumbnail } from "./PlayerThumbnail";
import {
  ChartIcon,
  FilterIcon,
  CheckIcon,
  CrossIcon,
  SlidersIcon,
  ExternalLinkIcon,
} from "./Icons";

type TabType = "batting" | "bowling" | "filters";
type SortMode = "priority" | "forecast";
type ScopeMode = "top15" | "all";

interface ScoredRecord {
  machine_rank: number;
  forecast_only_rank: number;
  player_id: number;
  player_name: string;
  role: string;
  deployment: string;
  priority_score: number;
  predicted_composite_impact: number;
  hp_balls: number;
  ordinary_balls: number;
  observed_pressure_runs_per_12: number | null;
  observed_ordinary_runs_per_12: number | null;
  observed_pressure_uplift: number | null;
  status: string;
  status_label: string;
  rr_shortlist_rank: number | null;
  rule_id: string;
  selection_or_exclusion_reason: string;
  tactical_transition_reason?: string;
}

export const ModelRankingsSection: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>("batting");
  const [sortMode, setSortMode] = useState<SortMode>("priority");
  const [scopeMode, setScopeMode] = useState<ScopeMode>("top15");

  const rawList: ScoredRecord[] = useMemo(() => {
    const list =
      activeTab === "batting"
        ? (modelRankingsData.batting_rankings as ScoredRecord[])
        : (modelRankingsData.bowling_rankings as ScoredRecord[]);

    const sorted = [...list].sort((a, b) => {
      if (sortMode === "priority") {
        if (b.priority_score !== a.priority_score) {
          return b.priority_score - a.priority_score;
        }
        return a.player_id - b.player_id; // deterministic canonical ID tie-breaker
      } else {
        if (b.predicted_composite_impact !== a.predicted_composite_impact) {
          return b.predicted_composite_impact - a.predicted_composite_impact;
        }
        return a.player_id - b.player_id;
      }
    });

    return scopeMode === "top15" ? sorted.slice(0, 15) : sorted;
  }, [activeTab, sortMode, scopeMode]);

  const poolCounts = modelRankingsData.broad_candidate_pool_counts;

  return (
    <section
      id="model-rankings"
      className="model-rankings-section"
      aria-labelledby="model-rankings-title"
    >
      <div className="model-rankings-container">
        {/* Navigation Return Bar */}
        <div className="section-return-bar" id="model-rankings-return-bar">
          <a href="#batters" className="btn-return-shortlist">
            ← Back to RR Shortlist
          </a>
          <div className="section-quick-links">
            <span className="quick-label">Jump to:</span>
            <a href="#batters" className="quick-link-pill">Batters</a>
            <a href="#bowlers" className="quick-link-pill">Bowlers</a>
            <a href="#methodology" className="quick-link-pill">Methodology</a>
          </div>
        </div>

        {/* Section Header */}
        <div className="model-rankings-header">
          <span className="section-pill">Destination 02 · Unfiltered Machine Output</span>
          <h2 id="model-rankings-title" className="section-heading">
            Model Rankings: Pure Performance Before RR Decisions
          </h2>
          <p className="section-intro">
            <strong>What does the model rank before RR-specific decisions?</strong> This view
            exposes the broad, cricket-only candidate population ({poolCounts.batting} Batters, {poolCounts.bowling} Bowlers)
            scored directly by the retained Bayesian volume-shrunk regression model. No franchise retention
            locks, role-balance requirements, or auction availability assumptions have been applied.
          </p>
        </div>

        {/* Sub-navigation Controls */}
        <div className="raw-subnav-row" role="tablist" aria-label="Model rankings category">
          <button
            type="button"
            className={`raw-subnav-btn ${activeTab === "batting" ? "active" : ""}`}
            onClick={() => setActiveTab("batting")}
          >
            <ChartIcon size={14} />
            <span>Raw Batters Leaderboard ({scopeMode === "top15" ? "Top 15" : `${poolCounts.batting} Scored`})</span>
          </button>
          <button
            type="button"
            className={`raw-subnav-btn ${activeTab === "bowling" ? "active" : ""}`}
            onClick={() => setActiveTab("bowling")}
          >
            <ChartIcon size={14} />
            <span>Raw Bowlers Leaderboard ({scopeMode === "top15" ? "Top 15" : `${poolCounts.bowling} Scored`})</span>
          </button>
          <button
            type="button"
            className={`raw-subnav-btn ${activeTab === "filters" ? "active" : ""}`}
            onClick={() => setActiveTab("filters")}
          >
            <FilterIcon size={14} />
            <span>How Model Ranks Lead to RR Shortlist</span>
          </button>
        </div>

        {activeTab === "filters" ? (
          <div className="raw-filters-explanation-panel">
            <div className="filter-pillar-card">
              <div className="filter-pillar-header">
                <span className="pillar-num">Pillar 01</span>
                <h4 className="pillar-title">Recruitment Screen &amp; Shortlist Assumptions</h4>
              </div>
              <p className="pillar-desc">
                The empirical model ranks <strong>Jasprit Bumrah (#1 Bowler, +3.16 priority, +4.34 forecast)</strong>,{" "}
                <strong>Sunil Narine (#3 Bowler, +3.02 priority)</strong>, <strong>Shreyas Iyer (#3 Batter, +2.05 priority)</strong>, and{" "}
                <strong>Tilak Varma (#6 Batter, +1.50 priority)</strong> at the very top of pressure performance.
                However, these players fall <strong>Outside current shortlist assumptions</strong> because core rival franchise
                retention assumptions (MI, KKR, PBKS) remove them from the actionable recruitment pool. Recommending contractually
                unavailable players for Rajasthan Royals’ auction strategy is non-actionable.
                Pillar 01 screens out non-target assumptions while preserving internal RR squad decisions.
              </p>
            </div>

            <div className="filter-pillar-card">
              <div className="filter-pillar-header">
                <span className="pillar-num">Pillar 02</span>
                <h4 className="pillar-title">Rajasthan Royals Tactical Role Blueprint &amp; Quota Trade-Off</h4>
              </div>
              <p className="pillar-desc">
                Taking the raw top 10 would create fatal roster gaps (e.g. 7 top-order batters and 0 death specialists).
                RR's verified tactical strategy requires:
              </p>
              <ul className="pillar-specs-list">
                <li><strong>Batting Coverage:</strong> At least 2 Finishers (Donovan Ferreira, Ravindra Jadeja), 2 Middle-Order anchors (Sameer Rizvi, Cooper Connolly, Riyan Parag, Venkatesh Iyer), and explosive Powerplay cover (Vaibhav Sooryavanshi, Josh Inglis, Abishek Porel, Prabhsimran Singh).</li>
                <li><strong>Bowling Arsenal:</strong> At least 3 Death-over specialists (Kartik Tyagi, Lungi Ngidi, Rasikh Salam), 2 Spin containers (Krunal Pandya, Ravindra Jadeja), and New-Ball seam pressure (Mohammed Siraj, Jason Holder, Trent Boult, Mohammed Shami, Anshul Kamboj).</li>
              </ul>

              {/* Counterfactual Score-only vs Role Quota comparison */}
              <div className="quota-tradeoff-box" style={{ marginTop: "16px", padding: "16px", background: "#FFFDF9", border: "1.5px solid #20172F", borderRadius: "12px" }}>
                <h5 style={{ margin: "0 0 8px 0", fontSize: "0.95rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "8px" }}>
                  <SlidersIcon size={16} />
                  <span>Empirical Counterfactual: Score-Only vs Role-Quota Slate</span>
                </h5>
                <p style={{ margin: "0 0 12px 0", fontSize: "0.85rem", color: "#475569", lineHeight: 1.5 }}>
                  What happens if we remove role balance rules and pick strictly by priority score within the eligible pool?
                </p>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px" }}>
                  <div style={{ padding: "12px", background: "#F8FAFC", borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                    <strong style={{ fontSize: "0.85rem", color: "#E03A3E" }}>Batting Discipline</strong>
                    <p style={{ margin: "6px 0 0 0", fontSize: "0.82rem", color: "#334155" }}>
                      <strong>Zero Changes (10 of 10 match):</strong> The score-only order naturally satisfies both the 2-finisher and 2-middle-order quotas without requiring any intervention.
                    </p>
                  </div>
                  <div style={{ padding: "12px", background: "#F8FAFC", borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                    <strong style={{ fontSize: "0.85rem", color: "#1B5E8A" }}>Bowling Discipline (The 2-Spinner Decision)</strong>
                    <p style={{ margin: "6px 0 0 0", fontSize: "0.82rem", color: "#334155" }}>
                      <strong>1 Swap (Deepak Chahar vs Ravindra Jadeja):</strong> Under score-only selection, Deepak Chahar (+0.08 r/12 priority) takes slot #10. However, that leaves RR with only 1 spinner (Krunal Pandya). Enforcing the 2-spin requirement promotes <strong>Ravindra Jadeja (#10, -0.31)</strong> to guarantee spin control on Jaipur pitches.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="filter-pillar-card">
              <div className="filter-pillar-header">
                <span className="pillar-num">Pillar 03</span>
                <h4 className="pillar-title">Scouting Overrides &amp; Health Validation</h4>
              </div>
              <p className="pillar-desc">
                Model outputs are checked against real-world cricket availability:
                <strong> Anshul Kamboj</strong> was promoted over Harshit Rana after verifying Rana missed IPL 2026 and suffered an unverified injury setback.
                Similarly, <strong>Mohammed Siraj</strong> and <strong>Jason Holder</strong> are tracked as release-dependent targets pending GT's official retention announcement.
              </p>
            </div>
          </div>
        ) : (
          <div className="raw-rankings-table-container">
            {/* Table Controls Bar */}
            <div className="raw-table-meta-bar" style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: "12px" }}>
              <div>
                <span className="table-caption-badge">
                  {activeTab === "batting" ? "Unfiltered Batting Model Predictions" : "Unfiltered Bowling Model Predictions"}
                </span>
                <span className="table-caption-sub" style={{ display: "block", marginTop: "4px" }}>
                  {sortMode === "priority"
                    ? "Sorted by Evidence-Adjusted Priority Score (Penalized for sparse sample size)"
                    : "Sorted by Unadjusted Predicted Composite Impact (Raw point forecast)"}
                </span>
              </div>

              {/* View & Sort Toggles */}
              <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
                <div style={{ display: "inline-flex", background: "#F1F5F9", padding: "3px", borderRadius: "9999px", border: "1px solid #CBD5E1" }}>
                  <button
                    type="button"
                    style={{
                      border: "none",
                      background: sortMode === "priority" ? "#20172F" : "transparent",
                      color: sortMode === "priority" ? "#FFF" : "#475569",
                      padding: "4px 12px",
                      borderRadius: "9999px",
                      fontSize: "0.78rem",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                    onClick={() => setSortMode("priority")}
                  >
                    Priority Score (Primary)
                  </button>
                  <button
                    type="button"
                    style={{
                      border: "none",
                      background: sortMode === "forecast" ? "#20172F" : "transparent",
                      color: sortMode === "forecast" ? "#FFF" : "#475569",
                      padding: "4px 12px",
                      borderRadius: "9999px",
                      fontSize: "0.78rem",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                    onClick={() => setSortMode("forecast")}
                  >
                    Forecast Only
                  </button>
                </div>

                <div style={{ display: "inline-flex", background: "#F1F5F9", padding: "3px", borderRadius: "9999px", border: "1px solid #CBD5E1" }}>
                  <button
                    type="button"
                    style={{
                      border: "none",
                      background: scopeMode === "top15" ? "#20172F" : "transparent",
                      color: scopeMode === "top15" ? "#FFF" : "#475569",
                      padding: "4px 12px",
                      borderRadius: "9999px",
                      fontSize: "0.78rem",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                    onClick={() => setScopeMode("top15")}
                  >
                    Top 15
                  </button>
                  <button
                    type="button"
                    style={{
                      border: "none",
                      background: scopeMode === "all" ? "#20172F" : "transparent",
                      color: scopeMode === "all" ? "#FFF" : "#475569",
                      padding: "4px 12px",
                      borderRadius: "9999px",
                      fontSize: "0.78rem",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                    onClick={() => setScopeMode("all")}
                  >
                    All Scored ({activeTab === "batting" ? poolCounts.batting : poolCounts.bowling})
                  </button>
                </div>
              </div>
            </div>

            <div className="raw-table-scroll-wrapper">
              <table className="raw-comparison-table" aria-label="Model rankings before RR decisions">
                <thead>
                  <tr>
                    <th scope="col" className="th-machine-rank">
                      {sortMode === "priority" ? "Machine Rank" : "Forecast Rank"}
                    </th>
                    <th scope="col" className="th-player">Player &amp; Role</th>
                    <th scope="col" className="th-priority">
                      {sortMode === "priority" ? "Priority Score" : "Forecast Impact"}
                    </th>
                    <th scope="col" className="th-market-status">Observed Rates</th>
                    <th scope="col" className="th-market-status">Franchise Availability</th>
                    <th scope="col" className="th-rr-outcome">RR 2027 Outcome</th>
                    <th scope="col" className="th-scout-rationale">Tactical Rationale</th>
                  </tr>
                </thead>
                <tbody>
                  {rawList.map((p, idx) => {
                    const isRRShortlisted = p.rr_shortlist_rank !== null;
                    const isOutside = p.status === "outside_shortlist_assumptions";
                    const isUnconfirmed = p.status === "availability_unconfirmed";
                    const isRRRetained = p.status === "rr_squad_decision";
                    const cardAnchor = getAnchorId(p.role as RoleType, p.player_name);

                    return (
                      <tr
                        key={`mr-${p.role}-${p.player_id}`}
                        className={`raw-table-row ${isRRShortlisted ? "is-shortlisted" : "is-excluded"}`}
                      >
                        <td className="td-machine-rank">
                          <span className="machine-rank-badge">
                            #{sortMode === "priority" ? idx + 1 : p.forecast_only_rank}
                          </span>
                        </td>
                        <td className="td-player">
                          <div className="raw-player-cell">
                            <PlayerThumbnail playerId={p.player_id} name={p.player_name} size={42} />
                            <div className="raw-player-meta">
                              <strong className="raw-player-name">{p.player_name}</strong>
                              <span className="raw-deployment-tag">{p.deployment}</span>
                            </div>
                          </div>
                        </td>
                        <td className="td-priority tabular-nums">
                          <span className={`priority-val ${p.priority_score >= 0 ? "val-pos" : "val-neg"}`}>
                            {sortMode === "priority"
                              ? (p.priority_score >= 0 ? `+${p.priority_score.toFixed(2)}` : p.priority_score.toFixed(2))
                              : (p.predicted_composite_impact >= 0 ? `+${p.predicted_composite_impact.toFixed(2)}` : p.predicted_composite_impact.toFixed(2))}
                          </span>
                          <span className="priority-sub">
                            {sortMode === "priority" ? "score" : "runs/12"}
                          </span>
                        </td>
                        <td className="td-market-status" style={{ fontSize: "0.80rem" }}>
                          {p.observed_pressure_runs_per_12 !== null ? (
                            <div>
                              <div><strong>HP:</strong> {p.observed_pressure_runs_per_12 >= 0 ? `+${p.observed_pressure_runs_per_12.toFixed(1)}` : p.observed_pressure_runs_per_12.toFixed(1)} r/12 ({p.hp_balls}b)</div>
                              <div><strong>Uplift:</strong> {p.observed_pressure_uplift !== null && p.observed_pressure_uplift >= 0 ? `+${p.observed_pressure_uplift.toFixed(1)}` : p.observed_pressure_uplift?.toFixed(1)} r/12</div>
                            </div>
                          ) : (
                            <span style={{ color: "#94A3B8" }}>No 2026 IPL data</span>
                          )}
                        </td>
                        <td className="td-market-status">
                          <span
                            className={`market-status-pill ${
                              isOutside
                                ? "status-outside"
                                : isUnconfirmed
                                ? "status-unconfirmed"
                                : isRRRetained
                                ? "status-rr"
                                : "status-auction"
                            }`}
                          >
                            {isOutside && <CrossIcon size={12} className="inline-cross" />}
                            {isRRShortlisted && <CheckIcon size={12} className="inline-check" />}
                            {p.status_label}
                          </span>
                        </td>
                        <td className="td-rr-outcome">
                          {isRRShortlisted ? (
                            <a
                              href={`#${cardAnchor}`}
                              className="rr-target-badge"
                              title={`Jump to ${p.player_name} card on the RR Shortlist`}
                              style={{ textDecoration: "none", cursor: "pointer" }}
                            >
                              <span className="target-num">Model #{idx + 1} → RR #{p.rr_shortlist_rank}</span>
                              <span className="target-label">{isRRRetained ? "In-Squad" : "Target"} <ExternalLinkIcon size={10} className="inline-icon" /></span>
                            </a>
                          ) : (
                            <span className="rr-filtered-badge">
                              {isOutside ? (
                                <><CrossIcon size={11} className="inline-cross" /> Non-Target</>
                              ) : (
                                <span style={{ color: "#64748B" }}>Unselected Backup</span>
                              )}
                            </span>
                          )}
                        </td>
                        <td className="td-scout-rationale">
                          <p className="rationale-text">{p.selection_or_exclusion_reason}</p>
                          {p.tactical_transition_reason && isRRShortlisted && (
                            <div className="tactical-transition-note" style={{ fontSize: "11px", color: "var(--color-navy)", marginTop: "4px", fontWeight: 600 }}>
                              {p.tactical_transition_reason}
                            </div>
                          )}
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
                <span><strong>Conditional auction target:</strong> External target shortlisted by RR whose 2027 auction entry is pending official franchise release lists.</span>
              </div>
              <div className="legend-item">
                <span className="legend-indicator status-rr" />
                <span><strong>RR squad decision:</strong> Internal Rajasthan Royals squad asset assessed under franchise control.</span>
              </div>
              <div className="legend-item">
                <span className="legend-indicator status-outside" />
                <span><strong>Outside current shortlist assumptions:</strong> Algorithmic leader whose rival franchise retention assumptions remove them from recruitment pool (e.g. Jasprit Bumrah #1).</span>
              </div>
              <div className="legend-item">
                <span className="legend-indicator status-unconfirmed" />
                <span><strong>Availability unconfirmed:</strong> Candidate meets broad statistical eligibility; franchise contract status unconfirmed pending official IPL releases.</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
};
