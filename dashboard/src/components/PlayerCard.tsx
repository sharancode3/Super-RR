import React from "react";
import type { RankingRecord, RoleType } from "../data/types";
import { getPortraitCredit } from "../data/portraits";
import {
  getDeploymentLabel,
  getRouteInfo,
  formatSignedRun,
  formatStability,
  formatLOORange,
} from "../data/formatters";
import { EvidenceDisclosure } from "./EvidenceDisclosure";
import { InfoIcon } from "./Icons";

interface PlayerCardProps {
  player: RankingRecord;
  role: RoleType;
  isLeader?: boolean;
  isActive?: boolean;
  onPreview?: (player: RankingRecord) => void;
}

export const PlayerCard: React.FC<PlayerCardProps> = ({
  player,
  role,
  isLeader = player.rank === 1,
  isActive = false,
  onPreview,
}) => {
  const isBatting = role === "batting";
  const roleThemeClass = isBatting ? "leader-batters" : "leader-bowlers";
  const pid = player.player_id;
  const credit = getPortraitCredit(pid);
  const deployment = getDeploymentLabel(role, player.deployment, pid);
  const routeInfo = getRouteInfo(player.route_category);
  const stab = formatStability(player.stability.selection_frequency);
  const loo = formatLOORange(
    player.metrics.loo_omission_min,
    player.metrics.loo_omission_max
  );

  return (
    <article
      className={`leader-card player-card downwise-dossier-card rect-player-card ${roleThemeClass} ${isLeader ? "is-leader" : ""} ${isActive ? "is-active-target" : ""} rank-mod-${player.rank % 2}`}
      data-reveal={player.rank <= 2 ? "revealed" : "pending"}
      aria-labelledby={`player-${role}-${player.player_id}-name`}
      id={`card-${role}-${player.player_id}`}
    >
      {/* Mobile/Compact Header (visible on < 900px) */}
      <div className="card-mobile-header">
        <div className="leader-rank-badge">
          <span className="rank-num">#{player.rank}</span>
          <span className="rank-label">{isLeader ? "TOP PICK" : `RANK ${player.rank}`}</span>
        </div>
        <div className="mobile-tags-row">
          <span className="phase-pill" title={deployment.primary}>
            {deployment.primary}
          </span>
          <span className={`route-pill ${routeInfo.pillClass}`} title={routeInfo.longExplanation}>
            {routeInfo.label}
          </span>
        </div>
        <span className="stability-header-pill" title="Top-10 bootstrap stability">
          {stab.percentage}
        </span>
      </div>

      {/* Main Rectangular Grid Body (Horizontal 3-Zone on Desktop, Auto-adjusting on Mobile) */}
      <div className="dossier-grid-body rect-card-body">
        {/* =========================================================================
            ZONE 1: Visual Arched Well & Pop-Out Animated Portrait Cutout
            ========================================================================= */}
        <div className="dossier-visual-pane rect-visual-col">
          <div className="leader-visual-well player-visual-well rect-visual-well popout-visual-well">
            <div className="geometric-shape-bg" aria-hidden="true" />
            <div className="geometric-accent-block" aria-hidden="true" />

            <button
              type="button"
              onClick={() => onPreview?.(player)}
              className="portrait-click-target"
              title={`Preview ${player.player_name} card & verified IPL stats`}
              aria-label={`Preview ${player.player_name} card & verified IPL stats`}
            >
              <picture className="portrait-picture">
                <source
                  type="image/webp"
                  srcSet={`/portraits/${pid}_640w.webp 640w, /portraits/${pid}_320w.webp 320w`}
                  sizes="(max-width: 640px) 160px, 240px"
                />
                <source
                  type="image/png"
                  srcSet={`/portraits/${pid}_640w.png 640w, /portraits/${pid}_320w.png 320w`}
                  sizes="(max-width: 640px) 160px, 240px"
                />
                <img
                  src={`/portraits/${pid}_640w.webp`}
                  alt={player.player_name}
                  className="leader-portrait-img player-portrait-img rect-portrait-img popout-portrait-img"
                  loading="eager"
                  decoding="async"
                  width={640}
                  height={640}
                />
              </picture>
            </button>

            <span className="portrait-credit" title={`Image credit: ${credit}`}>
              {credit}
            </span>
          </div>
        </div>

        {/* =========================================================================
            ZONE 2: Identity & Primary Forecast Impact (Middle Column)
            ========================================================================= */}
        <div className="rect-identity-col">
          {/* Desktop Badges Row - Cleanly houses the rank badge away from the player's head */}
          <div className="desktop-tags-row">
            <div className="card-desktop-rank-badge">
              <span className="rank-num">#{player.rank}</span>
              <span className="rank-label">{isLeader ? "TOP PICK" : `RANK ${player.rank}`}</span>
            </div>
            <span className="phase-pill" title={deployment.primary}>
              {deployment.primary}
            </span>
            {deployment.secondaryBadge && (
              <span className="phase-pill-secondary">
                {deployment.secondaryBadge}
              </span>
            )}
            <span
              className={`route-pill ${routeInfo.pillClass}`}
              title={routeInfo.longExplanation}
            >
              {routeInfo.label}
            </span>
          </div>

          <div className="dossier-identity-block rect-identity-block">
            <h3 id={`player-${role}-${player.player_id}-name`} className="leader-name rect-player-name">
              {player.player_name}
            </h3>
            <div className="dossier-source-tag">
              <span className="source-label">2026 Reference: </span>
              <span className="source-val">{credit}</span>
            </div>
          </div>

          {/* Compact Headline Impact Strip (Preserves .dossier-headline-impact contract while eliminating duplicate bulky boxes) */}
          <div className="dossier-headline-impact rect-headline-impact compact-headline-strip">
            <span className="impact-tag-label">Forecast Impact:</span>
            <span className="impact-tag-val val-pos tabular-nums">
              {formatSignedRun(player.metrics.predicted_composite_impact)} r/12
            </span>
            <span className="impact-tag-sep">·</span>
            <span className="impact-tag-label">Uplift vs Ordinary:</span>
            <span
              className={`impact-tag-val tabular-nums ${
                player.metrics.signed_uplift_runs_per_12 >= 0 ? "uplift-pos" : "uplift-neg"
              }`}
            >
              {formatSignedRun(player.metrics.signed_uplift_runs_per_12)} r/12
            </span>
          </div>

          {/* RR Tactical Strategy in Identity Column */}
          <p className="leader-fit-summary rect-fit-summary">
            <strong>RR Strategy:</strong> {player.rr_fit_and_risk}
          </p>
        </div>

        {/* =========================================================================
            ZONE 3: Core Metrics, Tactical Fit & Expandable Evidence (Right Column)
            ========================================================================= */}
        <div className="dossier-data-pane rect-data-col">
          {/* 4-Box Metrics Grid */}
          <div className="leader-metrics-grid rect-metrics-grid">
            <div className="metric-box metric-primary">
              <span className="metric-label">Forecast Impact</span>
              <span className="metric-value tabular-nums val-pos">
                {formatSignedRun(player.metrics.predicted_composite_impact)}
                <span className="metric-unit"> r/12</span>
              </span>
              <span className="metric-footnote">Audited composite</span>
            </div>

            <div className="metric-box">
              <span className="metric-label">Observed Pressure</span>
              <span
                className={`metric-value tabular-nums ${
                  player.metrics.observed_pressure_runs_per_12 >= 0 ? "val-pos" : "val-neg"
                }`}
              >
                {formatSignedRun(player.metrics.observed_pressure_runs_per_12)}
                <span className="metric-unit"> r/12</span>
              </span>
              <span className="metric-footnote">
                {player.metrics.hp_balls}b ({player.metrics.pressure_fixtures_count}m)
              </span>
            </div>

            <div className="metric-box">
              <span className="metric-label">Pressure Uplift</span>
              <span
                className={`metric-value tabular-nums ${
                  player.metrics.signed_uplift_runs_per_12 >= 0 ? "uplift-pos" : "uplift-neg"
                }`}
              >
                {formatSignedRun(player.metrics.signed_uplift_runs_per_12)}
                <span className="metric-unit"> r/12</span>
              </span>
              <span className="metric-footnote">vs ordinary level</span>
            </div>

            <div className="metric-box">
              <span className="metric-label">Top-10 Stability</span>
              <span className="metric-value tabular-nums">
                {stab.percentage}
              </span>
              <span
                className="metric-footnote"
                title="Inclusion across 1,000 whole-match cluster bootstrap resamples"
              >
                {stab.ratio} draws
              </span>
            </div>
          </div>

          {/* Meta Bar: Stability Note + LOO bounds */}
          <div className="rect-meta-bar">
            <p className="stability-plain-note rect-stability-note">
              <span className="note-icon" aria-hidden="true"><InfoIcon size={14} /></span>
              Top-10 stability: included in <strong>{stab.percentage}</strong> of 1,000 resamples.
            </p>

            {loo.isAvailable ? (
              <div className="loo-range-bar" title="Leave-one-out pressure exposure omission range">
                <span className="loo-label">LOO Range:</span>
                <span className="loo-value tabular-nums">{loo.display}</span>
              </div>
            ) : (
              <div className="loo-range-bar loo-bar-na">
                <span className="loo-label">LOO Range:</span>
                <span className="loo-value tabular-nums">n/a (1 match)</span>
              </div>
            )}
          </div>

          {/* Expandable Player Evidence Audit Panel */}
          <EvidenceDisclosure player={player} role={role} />
        </div>
      </div>
    </article>
  );
};
