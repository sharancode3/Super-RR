import React from "react";
import type { RankingRecord, RoleType } from "../data/types";
import {
  formatSignedRun,
  formatLOORange,
  formatStability,
  getCrossDisciplineLink,
} from "../data/formatters";
import { getPortraitCredit } from "../data/portraits";
import { ChartIcon, ChevronDownIcon } from "./Icons";

interface EvidenceDisclosureProps {
  player: RankingRecord;
  role: RoleType;
  defaultExpanded?: boolean;
}

export const EvidenceDisclosure: React.FC<EvidenceDisclosureProps> = ({
  player,
  role,
  defaultExpanded = false,
}) => {
  const m = player.metrics;
  const s = player.stability;
  const isBatting = role === "batting";
  const crossLink = getCrossDisciplineLink(role, player.player_id);
  const loo = formatLOORange(m.loo_omission_min, m.loo_omission_max);
  const stab = formatStability(s.selection_frequency);
  const credit = getPortraitCredit(player.player_id);

  // Common visual domain for comparative impact bars
  // Batting: [-4 to +20] (total range 24, zero baseline at 16.67%)
  // Bowling: [-8 to +10] (total range 18, zero baseline at 44.44%)
  const domainMin = isBatting ? -4.0 : -8.0;
  const domainMax = isBatting ? 20.0 : 10.0;
  const domainRange = domainMax - domainMin;
  const zeroPct = ((0 - domainMin) / domainRange) * 100;

  const calcBarStyles = (val: number) => {
    const clamped = Math.max(domainMin, Math.min(domainMax, val));
    if (clamped >= 0) {
      const widthPct = (clamped / domainRange) * 100;
      return {
        left: `${zeroPct}%`,
        width: `${Math.max(widthPct, 1.5)}%`,
        isNegative: false,
      };
    } else {
      const widthPct = (Math.abs(clamped) / domainRange) * 100;
      return {
        left: `${zeroPct - widthPct}%`,
        width: `${Math.max(widthPct, 1.5)}%`,
        isNegative: true,
      };
    }
  };

  const ordinaryBar = calcBarStyles(m.observed_ordinary_runs_per_12);
  const pressureBar = calcBarStyles(m.observed_pressure_runs_per_12);

  return (
    <details
      className="player-evidence-disclosure"
      open={defaultExpanded}
      id={`disclosure-${role}-${player.player_id}`}
    >
      <summary
        className="evidence-summary-btn"
        aria-label={`Player evidence and audit breakdown for ${player.player_name}`}
      >
        <span className="summary-left">
          <span className="summary-icon" aria-hidden="true">
            <ChartIcon size={15} />
          </span>
          <span className="summary-title">Player evidence</span>
        </span>
        <span className="summary-meta">
          <span className="summary-badge">Audit record</span>
          <span className="summary-chevron" aria-hidden="true">
            <ChevronDownIcon size={13} />
          </span>
        </span>
      </summary>

      <div className="evidence-content-panel">
        {/* =========================================================================
            1. COMPARATIVE IMPACT VISUALIZATION (ZERO-BASELINE)
            ========================================================================= */}
        <div className="evidence-group">
          <div className="evidence-group-header">
            <h5 className="group-heading">Observed Impact Comparison</h5>
            <span className="unit-tag">run equivalents per 12 legal balls</span>
          </div>

          <div className="impact-comparison-box">
            {/* Ordinary Rate Row */}
            <div className="rate-row">
              <div className="rate-meta">
                <span className="rate-name">Ordinary Rate:</span>
                <span className="rate-exposure">
                  {m.ordinary_balls} legal balls
                </span>
              </div>
              <div className="chart-track-wrapper">
                <div
                  className="chart-zero-line"
                  style={{ left: `${zeroPct}%` }}
                  title="Zero baseline (0.00 runs/12)"
                  aria-hidden="true"
                >
                  <span className="zero-label">0.00</span>
                </div>
                <div
                  className={`chart-bar ${ordinaryBar.isNegative ? "bar-negative" : "bar-positive"} bar-ordinary`}
                  style={{
                    left: ordinaryBar.left,
                    width: ordinaryBar.width,
                  }}
                  title={`Ordinary: ${formatSignedRun(m.observed_ordinary_runs_per_12)} runs/12`}
                />
              </div>
              <div className="rate-value-col">
                <span
                  className={`rate-num tabular-nums ${m.observed_ordinary_runs_per_12 >= 0 ? "val-pos" : "val-neg"}`}
                >
                  {formatSignedRun(m.observed_ordinary_runs_per_12)}
                </span>
                <span className="rate-unit"> r/12</span>
              </div>
            </div>

            {/* Pressure Rate Row */}
            <div className="rate-row">
              <div className="rate-meta">
                <span className="rate-name">Pressure Rate:</span>
                <span className="rate-exposure">
                  {m.hp_balls} balls ({m.pressure_fixtures_count} matches)
                </span>
              </div>
              <div className="chart-track-wrapper">
                <div
                  className="chart-zero-line"
                  style={{ left: `${zeroPct}%` }}
                  aria-hidden="true"
                />
                <div
                  className={`chart-bar ${pressureBar.isNegative ? "bar-negative" : "bar-positive"} bar-pressure`}
                  style={{
                    left: pressureBar.left,
                    width: pressureBar.width,
                  }}
                  title={`Pressure: ${formatSignedRun(m.observed_pressure_runs_per_12)} runs/12`}
                />
              </div>
              <div className="rate-value-col">
                <span
                  className={`rate-num tabular-nums ${m.observed_pressure_runs_per_12 >= 0 ? "val-pos" : "val-neg"}`}
                >
                  {formatSignedRun(m.observed_pressure_runs_per_12)}
                </span>
                <span className="rate-unit"> r/12</span>
              </div>
            </div>

            {/* Signed Uplift Highlight */}
            <div className="uplift-summary-strip">
              <span className="uplift-strip-label">
                Signed Pressure Uplift (Pressure − Ordinary):
              </span>
              <span
                className={`uplift-strip-value tabular-nums ${m.signed_uplift_runs_per_12 >= 0 ? "uplift-pos" : "uplift-neg"}`}
              >
                {formatSignedRun(m.signed_uplift_runs_per_12)} runs/12
              </span>
            </div>
          </div>
        </div>

        {/* =========================================================================
            2. FORECAST, STABILITY & SENSITIVITY GRID
            ========================================================================= */}
        <div className="evidence-grid-details">
          <div className="detail-card">
            <span className="detail-card-label">Forecast Impact</span>
            <span className="detail-card-val tabular-nums val-pos">
              {formatSignedRun(m.predicted_composite_impact)} r/12
            </span>
            <span className="detail-card-sub">
              Priority: {m.model_ranking_priority.toFixed(4)}
            </span>
          </div>

          <div className="detail-card">
            <span className="detail-card-label">Top-10 Stability</span>
            <span className="detail-card-val tabular-nums">
              {stab.percentage}
            </span>
            <span className="detail-card-sub">{stab.ratio}</span>
          </div>

          <div className="detail-card">
            <span className="detail-card-label">LOO Omission Bounds</span>
            <span
              className={`detail-card-val tabular-nums ${loo.isAvailable ? "" : "val-muted"}`}
            >
              {loo.display}
            </span>
            <span className="detail-card-sub" title={loo.tooltip}>
              {loo.isAvailable ? "Sensitivity range" : "1 fixture recorded"}
            </span>
          </div>

          <div className="detail-card">
            <span className="detail-card-label">Pressure Workload</span>
            <span className="detail-card-val tabular-nums">
              {m.hp_balls} balls
            </span>
            <span className="detail-card-sub">
              Across {m.pressure_fixtures_count} fixtures
            </span>
          </div>
        </div>

        {/* =========================================================================
            3. SCOUTING CONTEXT, CAVEATS & CROSS-ROLE LINKING
            ========================================================================= */}
        <div className="scouting-context-block">
          <p className="scouting-text">
            <strong className="scouting-lead">RR Fit & Context:</strong>{" "}
            {player.rr_fit_and_risk}
          </p>

          {/* Kamboj Special Role Note */}
          {player.player_id === 27964 && (
            <p className="role-note-callout">
              <strong>Tactical Note:</strong> Model classifies deployment under
              New-ball bowling with recorded death-over evidence (42 recent
              pressure balls at the death).
            </p>
          )}

          {/* Ravindra Jadeja Cross-Discipline Link */}
          {crossLink && (
            <div className="jadeja-crosslink-box">
              <span className="crosslink-tag">Dual Role Qualification</span>
              <a
                href={crossLink.targetAnchor}
                className="jadeja-crosslink-anchor"
              >
                {crossLink.linkText}
              </a>
            </div>
          )}
        </div>

        {/* =========================================================================
            4. DIRECTION GUIDE & ATTRIBUTION FOOTNOTE
            ========================================================================= */}
        <div className="evidence-footnote">
          <p className="direction-guide">
            <strong>Direction guide:</strong> Positive impact represents
            favourable performance relative to similar match contexts. Uplift is
            observed pressure impact minus ordinary impact. Match-omission
            bounds test sensitivity by omitting individual fixtures.
          </p>
          <div className="photo-context-line">
            <span>
              <strong>Photo:</strong> Official BCCI / IPL 2026 Media Day ({credit}).
              Historic club kit reflects photo context, not 2027 squad status.
            </span>
          </div>
        </div>
      </div>
    </details>
  );
};
