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
type ScopeMode = "all_rr" | "all" | "top15" | "shortlist_only";
type PoolType = "screened" | "broad";

interface ScoredRecord {
  machine_rank: number;
  forecast_only_rank: number;
  screened_priority_rank?: number | null;
  screened_forecast_rank?: number | null;
  is_screened?: boolean;
  team_2026?: string;
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
  const [scopeMode, setScopeMode] = useState<ScopeMode>("all_rr");
  const [poolType, setPoolType] = useState<PoolType>("broad");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const poolCounts = modelRankingsData.broad_candidate_pool_counts;
  const screenedCounts = (modelRankingsData as any).screened_candidate_pool_counts || { batting: 82, bowling: 95 };

  const rawList: ScoredRecord[] = useMemo(() => {
    const list =
      activeTab === "batting"
        ? (modelRankingsData.batting_rankings as ScoredRecord[])
        : (modelRankingsData.bowling_rankings as ScoredRecord[]);

    // 1. Filter by pool type (screened vs broad)
    let filtered = poolType === "screened" ? list.filter((p) => p.is_screened) : [...list];

    // 2. Filter by search query if any
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      filtered = filtered.filter((p) => p.player_name.toLowerCase().includes(q) || (p.team_2026 && p.team_2026.toLowerCase().includes(q)));
    }

    // 3. Sort deterministically
    const sorted = [...filtered].sort((a, b) => {
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

    // 4. Scope filtering / slicing
    if (searchQuery.trim()) {
      return sorted;
    }

    if (scopeMode === "shortlist_only") {
      return sorted.filter((p) => p.rr_shortlist_rank !== null);
    }

    if (scopeMode === "top15") {
      return sorted.slice(0, 15);
    }

    if (scopeMode === "all_rr") {
      // In broad pool, Bowler #10 (Archer) is at rank 25, and Batter #10 (Venkatesh) is at rank 20.
      // Slicing to 25 ensures ALL 10 RR picks are visible in both disciplines.
      // In screened pool, Bowler #10 is at rank 13, and Batter #10 is at rank 10.
      const sliceLimit = poolType === "broad" ? 25 : 15;
      return sorted.slice(0, sliceLimit);
    }

    // "all" returns the full sorted list
    return sorted;
  }, [activeTab, sortMode, scopeMode, poolType, searchQuery]);

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
            exposes both the <strong>RR-Screened Top 15</strong> (from {screenedCounts.batting} Batters &amp; {screenedCounts.bowling} Bowlers in the active recruitment pool)
            and the broad candidate population ({poolCounts.batting} Batters, {poolCounts.bowling} Bowlers)
            scored directly by the Bayesian volume-shrunk regression model. Toggle between recruitment-screened targets and the full candidate universe below.
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
            <span>
              Raw Batters Leaderboard ({poolType === "screened" ? (scopeMode === "top15" ? "Screened Top 15" : `${screenedCounts.batting} Screened`) : (scopeMode === "top15" ? "Top 15" : `${poolCounts.batting} Scored`)})
            </span>
          </button>
          <button
            type="button"
            className={`raw-subnav-btn ${activeTab === "bowling" ? "active" : ""}`}
            onClick={() => setActiveTab("bowling")}
          >
            <ChartIcon size={14} />
            <span>
              Raw Bowlers Leaderboard ({poolType === "screened" ? (scopeMode === "top15" ? "Screened Top 15" : `${screenedCounts.bowling} Screened`) : (scopeMode === "top15" ? "Top 15" : `${poolCounts.bowling} Scored`)})
            </span>
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
                <li><strong>Bowling Arsenal:</strong> At least 3 Death-over specialists (Kartik Tyagi, Lungi Ngidi, Rasikh Salam), 2 Spin containers (Krunal Pandya, Ravindra Jadeja), and New-Ball seam pressure (Mohammed Siraj, Jason Holder, Mohammed Shami, Anshul Kamboj, Jofra Archer).</li>
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
                      <strong>1 Swap (Deepak Chahar vs Ravindra Jadeja):</strong> Under score-only selection, Deepak Chahar (+0.08 r/12 priority) takes slot #10. However, that leaves RR with only 1 spinner (Krunal Pandya). Enforcing the 2-spin requirement promotes <strong>Ravindra Jadeja (#9 Bowler, -0.31)</strong> to guarantee spin control on Jaipur pitches.
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
                <strong> Anshul Kamboj (#8)</strong> was promoted over Harshit Rana after verifying Rana missed IPL 2026 and suffered an unverified injury setback.
                Similarly, <strong>Mohammed Siraj</strong> and <strong>Jason Holder</strong> are tracked as release-dependent targets pending GT's official retention announcement, while <strong>Jofra Archer (#10)</strong> is backed as an internal RR squad asset avoiding new overseas auction slot consumption.
              </p>
            </div>
          </div>
        ) : (
          <div className="raw-rankings-table-container">
            {/* Table Controls Bar */}
            <div className="raw-table-meta-bar" style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: "12px" }}>
              <div>
                <span className="table-caption-badge">
                  {poolType === "screened" ? "RR-Screened Top 15 (Active Recruitment Pool)" : "Broad Candidate Universe (Unfiltered Machine Output)"}
                </span>
                <span className="table-caption-sub" style={{ display: "block", marginTop: "4px" }}>
                  {poolType === "screened"
                    ? `Showing ${scopeMode === "top15" && !searchQuery ? "Top 15" : "all"} screened candidates (${activeTab === "batting" ? screenedCounts.batting : screenedCounts.bowling} total eligible) · Sorted by ${sortMode === "priority" ? "Evidence-Adjusted Priority Score" : "Predicted Composite Impact"}`
                    : `Showing broad candidate population (${activeTab === "batting" ? poolCounts.batting : poolCounts.bowling} scored) · Sorted by ${sortMode === "priority" ? "Evidence-Adjusted Priority Score" : "Predicted Composite Impact"}`}
                </span>
              </div>

              {/* View & Sort Toggles */}
              <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                {/* Search Box */}
                <div style={{ position: "relative", minWidth: "190px" }}>
                  <input
                    type="text"
                    placeholder="Search candidate (e.g. Archer, Boult)..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "5px 10px 5px 12px",
                      borderRadius: "9999px",
                      border: "1.5px solid #CBD5E1",
                      fontSize: "0.78rem",
                      background: "#FFF",
                      color: "#20172F",
                    }}
                  />
                  {searchQuery && (
                    <button
                      type="button"
                      onClick={() => setSearchQuery("")}
                      style={{
                        position: "absolute",
                        right: "8px",
                        top: "50%",
                        transform: "translateY(-50%)",
                        background: "none",
                        border: "none",
                        cursor: "pointer",
                        color: "#94A3B8",
                        fontSize: "12px",
                      }}
                    >
                      ✕
                    </button>
                  )}
                </div>

                {/* Pool Selector: Screened vs Broad */}
                <div style={{ display: "inline-flex", background: "#F1F5F9", padding: "3px", borderRadius: "9999px", border: "1.5px solid #CBD5E1" }}>
                  <button
                    type="button"
                    style={{
                      border: "none",
                      background: poolType === "screened" ? "#D81465" : "transparent",
                      color: poolType === "screened" ? "#FFF" : "#475569",
                      padding: "4px 12px",
                      borderRadius: "9999px",
                      fontSize: "0.78rem",
                      fontWeight: 700,
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                    }}
                    onClick={() => setPoolType("screened")}
                    title="Active RR recruitment pool after removing non-actionable rival franchise locks"
                  >
                    RR-Screened Pool ({activeTab === "batting" ? screenedCounts.batting : screenedCounts.bowling})
                  </button>
                  <button
                    type="button"
                    style={{
                      border: "none",
                      background: poolType === "broad" ? "#20172F" : "transparent",
                      color: poolType === "broad" ? "#FFF" : "#475569",
                      padding: "4px 12px",
                      borderRadius: "9999px",
                      fontSize: "0.78rem",
                      fontWeight: 700,
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                    }}
                    onClick={() => setPoolType("broad")}
                    title="Full candidate universe including contractually unavailable rival leaders"
                  >
                    Broad Pool ({activeTab === "batting" ? poolCounts.batting : poolCounts.bowling})
                  </button>
                </div>

                {/* Sort Mode: Priority vs Forecast */}
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

                {/* Scope Toggles: All 10 RR Targets vs All Scored vs Top 15 vs 10 Shortlisted */}
                <div style={{ display: "inline-flex", background: "#F1F5F9", padding: "3px", borderRadius: "9999px", border: "1.5px solid #CBD5E1", flexWrap: "wrap", gap: "2px" }}>
                  <button
                    type="button"
                    style={{
                      border: "none",
                      background: scopeMode === "all_rr" ? "#D81465" : "transparent",
                      color: scopeMode === "all_rr" ? "#FFF" : "#475569",
                      padding: "4px 12px",
                      borderRadius: "9999px",
                      fontSize: "0.78rem",
                      fontWeight: 700,
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                    }}
                    onClick={() => setScopeMode("all_rr")}
                    title={`Show through all 10 RR Shortlisted Targets (Ranks 1 to ${poolType === "broad" ? 25 : 15})`}
                  >
                    All 10 RR Targets (Top 25)
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
                      transition: "all 0.15s ease",
                    }}
                    onClick={() => setScopeMode("all")}
                    title={`Full candidate database (${activeTab === "batting" ? (poolType === "screened" ? screenedCounts.batting : poolCounts.batting) : (poolType === "screened" ? screenedCounts.bowling : poolCounts.bowling)} players)`}
                  >
                    All Scored ({activeTab === "batting" ? (poolType === "screened" ? screenedCounts.batting : poolCounts.batting) : (poolType === "screened" ? screenedCounts.bowling : poolCounts.bowling)})
                  </button>
                  <button
                    type="button"
                    style={{
                      border: "none",
                      background: scopeMode === "shortlist_only" ? "#20172F" : "transparent",
                      color: scopeMode === "shortlist_only" ? "#FFF" : "#475569",
                      padding: "4px 12px",
                      borderRadius: "9999px",
                      fontSize: "0.78rem",
                      fontWeight: 700,
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                    }}
                    onClick={() => setScopeMode("shortlist_only")}
                    title="Filter table to only show the 10 RR Shortlisted Targets"
                  >
                    RR 10 Only
                  </button>
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
                      transition: "all 0.15s ease",
                    }}
                    onClick={() => setScopeMode("top15")}
                    title="Show Top 15 candidates"
                  >
                    Top 15
                  </button>
                </div>
              </div>
            </div>

            {/* Scroll Navigation & Coverage Helper Toolbar */}
            <div
              className="raw-table-scroll-helper"
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexWrap: "wrap",
                gap: "8px",
                padding: "8px 12px",
                background: "#FFFDF9",
                border: "1px solid #E2E8F0",
                borderRadius: "6px",
                marginBottom: "8px",
                fontSize: "0.78rem",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontWeight: 700, color: "#20172F" }}>
                  {scopeMode === "all_rr"
                    ? `Showing Ranks 1 to ${poolType === "broad" ? 25 : 15} · Covers all 10 RR Shortlisted Targets`
                    : scopeMode === "all"
                    ? `Showing all ${rawList.length} scored candidates · Full Database`
                    : scopeMode === "shortlist_only"
                    ? `Showing the 10 RR Shortlisted Targets only`
                    : `Showing Top 15 Candidates`}
                </span>
                <span style={{ color: "#64748B", fontSize: "0.74rem" }}>
                  (Scroll vertically inside table)
                </span>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <button
                  type="button"
                  onClick={() => {
                    const el = document.querySelector(".raw-table-scroll-wrapper");
                    if (el) el.scrollTo({ top: 0, behavior: "smooth" });
                  }}
                  title="Scroll table to Top (Rank #1)"
                  style={{
                    background: "#FFF",
                    border: "1px solid #CBD5E1",
                    borderRadius: "4px",
                    padding: "3px 9px",
                    fontSize: "0.73rem",
                    fontWeight: 600,
                    color: "#20172F",
                    cursor: "pointer",
                  }}
                >
                  ↑ Top #1
                </button>
                <button
                  type="button"
                  onClick={() => {
                    const el = document.querySelector(".raw-table-scroll-wrapper");
                    const targetRow = document.querySelector(
                      activeTab === "batting" ? "#mr-batting-7544" : "#mr-bowling-3298"
                    );
                    if (el && targetRow) {
                      (targetRow as HTMLElement).scrollIntoView({ behavior: "smooth", block: "center" });
                    } else if (el) {
                      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
                    }
                  }}
                  title={`Scroll table down to RR #10 (${activeTab === "batting" ? "Venkatesh Iyer" : "Jofra Archer"})`}
                  style={{
                    background: "#FFF0F5",
                    border: "1px solid #FBCFE8",
                    borderRadius: "4px",
                    padding: "3px 9px",
                    fontSize: "0.73rem",
                    fontWeight: 700,
                    color: "#D81465",
                    cursor: "pointer",
                  }}
                >
                  ↓ Scroll to RR #10 ({activeTab === "batting" ? "Venkatesh" : "Archer"})
                </button>
              </div>
            </div>

            <div className="raw-table-scroll-wrapper">
              <table className="raw-comparison-table" aria-label="Model rankings before RR decisions">
                <thead>
                  <tr>
                    <th scope="col" className="th-machine-rank">Rank</th>
                    <th scope="col" className="th-player">Player &amp; Role</th>
                    <th scope="col" className="th-priority">
                      {sortMode === "priority" ? "Score" : "Forecast"}
                    </th>
                    <th scope="col" className="th-rates">Observed Rates</th>
                    <th scope="col" className="th-status">Availability</th>
                    <th scope="col" className="th-outcome">RR Outcome</th>
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

                    // Authorized rank computation
                    const displayedRank =
                      poolType === "screened"
                        ? (sortMode === "priority" ? p.screened_priority_rank : p.screened_forecast_rank) ?? (idx + 1)
                        : (sortMode === "priority" ? p.machine_rank : p.forecast_only_rank);

                    return (
                      <tr
                        key={`mr-${p.role}-${p.player_id}`}
                        id={`mr-${p.role}-${p.player_id}`}
                        className={`raw-table-row ${isRRShortlisted ? "is-shortlisted" : "is-excluded"}`}
                      >
                        <td className="td-machine-rank">
                          <span className="machine-rank-badge">
                            #{displayedRank}
                          </span>
                          <span style={{ fontSize: "10px", color: "#64748B", display: "block", marginTop: "2px" }}>
                            {poolType === "screened"
                              ? (sortMode === "priority" ? `Screened #${p.screened_priority_rank}` : `Screened #${p.screened_forecast_rank}`)
                              : (sortMode === "priority" ? `Broad #${p.machine_rank}` : `Broad #${p.forecast_only_rank}`)}
                          </span>
                        </td>
                        <td className="td-player">
                          <div className="raw-player-cell">
                            <PlayerThumbnail playerId={p.player_id} name={p.player_name} size={38} />
                            <div className="raw-player-meta">
                              <strong className="raw-player-name">{p.player_name}</strong>
                              <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap", marginTop: "2px" }}>
                                <span className="raw-deployment-tag">{p.deployment}</span>
                                {p.team_2026 && (
                                  <span style={{ fontSize: "10.5px", color: p.team_2026 === "Rajasthan Royals" ? "#D81465" : "#475569", fontWeight: 600 }}>
                                    {p.team_2026}
                                  </span>
                                )}
                              </div>
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
                        <td className="td-rates">
                          {p.observed_pressure_runs_per_12 !== null ? (
                            <div>
                              <div><strong>HP:</strong> {p.observed_pressure_runs_per_12 >= 0 ? `+${p.observed_pressure_runs_per_12.toFixed(1)}` : p.observed_pressure_runs_per_12.toFixed(1)} r/12 ({p.hp_balls}b)</div>
                              <div><strong>Uplift:</strong> {p.observed_pressure_uplift !== null && p.observed_pressure_uplift >= 0 ? `+${p.observed_pressure_uplift.toFixed(1)}` : p.observed_pressure_uplift?.toFixed(1)} r/12</div>
                            </div>
                          ) : (
                            <span style={{ color: "#94A3B8" }}>No 2026 IPL data</span>
                          )}
                        </td>
                        <td className="td-status">
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
                        <td className="td-outcome">
                          {isRRShortlisted ? (
                            <a
                              href={`#${cardAnchor}`}
                              className="rr-target-badge"
                              title={`Jump to ${p.player_name} card on the RR Shortlist`}
                              style={{ textDecoration: "none", cursor: "pointer" }}
                            >
                              <span className="target-num">
                                {poolType === "screened"
                                  ? `Screened #${p.screened_priority_rank} → RR #${p.rr_shortlist_rank}`
                                  : `Model #${p.machine_rank} → RR #${p.rr_shortlist_rank}`}
                              </span>
                              <span className="target-label">
                                {isRRRetained ? "In-Squad" : "Target"} <ExternalLinkIcon size={10} className="inline-icon" />
                              </span>
                            </a>
                          ) : (
                            <span className="rr-filtered-badge">
                              {p.player_id === 2320 ? (
                                <span style={{ color: "#1E3A8A", fontWeight: 600 }}>MI 2026 Asset (Conditional)</span>
                              ) : isOutside ? (
                                <><CrossIcon size={11} className="inline-cross" /> Non-Target</>
                              ) : (
                                <span style={{ color: "#64748B" }}>Unselected Backup</span>
                              )}
                            </span>
                          )}
                        </td>
                        <td className="td-scout-rationale">
                          <p className="rationale-text">{p.selection_or_exclusion_reason}</p>
                          {p.tactical_transition_reason && (
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
