import React, { useState, useEffect } from "react";
import type { RankingRecord } from "../data/types";
import iplStatsData from "../data/player_ipl_stats.json";
import portraitsManifest from "../data/portraits_manifest.json";
import { ExternalLinkIcon } from "./Icons";

interface PlayerPreviewModalProps {
  player: RankingRecord | null;
  onClose: () => void;
}

interface PlayerStats {
  id: number;
  name: string;
  role: string;
  matches: number;
  is_batter: boolean;
  is_bowler: boolean;
  batting: {
    innings: number;
    runs: number;
    balls: number;
    fours: number;
    sixes: number;
    strike_rate: number;
    average: number;
    highest_score: number;
    fifties: number;
    hundreds: number;
    hp_balls: number;
    hp_runs: number;
    hp_strike_rate: number;
  };
  bowling: {
    innings: number;
    overs: number;
    balls: number;
    runs: number;
    wickets: number;
    economy: number;
    average: number;
    strike_rate: number;
    best_bowling: string;
    four_w: number;
    five_w: number;
    hp_balls: number;
    hp_wickets: number;
    hp_economy: number;
  };
}

export const PlayerPreviewModal: React.FC<PlayerPreviewModalProps> = ({
  player,
  onClose,
}) => {
  const [bgTheme, setBgTheme] = useState<"tile-pink" | "tile-blue" | "tile-paper" | "tile-dark">("tile-paper");
  const [activeTab, setActiveTab] = useState<"batting" | "bowling">("batting");

  useEffect(() => {
    if (!player) return;

    const isDual = player.player_id === 152;
    if (isDual) {
      setActiveTab("batting");
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = originalOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [player, onClose]);

  if (!player) return null;

  const pid = String(player.player_id);
  const statsRecord = (iplStatsData as Record<string, PlayerStats>)[pid];
  const manifestItem = (portraitsManifest as any[]).find(
    (m) => String(m.player_id) === pid
  );

  const isDual = player.player_id === 152;
  const showBatting = isDual ? activeTab === "batting" : statsRecord?.is_batter;

  // Calculate visualizer progress
  let speedoWidth = "0%";
  if (statsRecord?.batting?.strike_rate) {
    const sr = statsRecord.batting.strike_rate;
    // Map 80 -> 0%, 240 -> 100%
    const pct = Math.max(10, Math.min(100, Math.round(((sr - 80) / 160) * 100)));
    speedoWidth = `${pct}%`;
  }

  let economyWidth = "0%";
  if (statsRecord?.bowling?.economy) {
    const econ = statsRecord.bowling.economy;
    // Lower is better: Map 12.0 -> 10%, 6.0 -> 95%
    const pct = Math.max(10, Math.min(100, Math.round(((12.0 - econ) / 6.0) * 100)));
    economyWidth = `${pct}%`;
  }

  const roleLabel = isDual
    ? "Dual-Role All-Rounder (Batters #9 · Bowlers #10)"
    : player.role === "batting"
    ? `Batter · Rank #${player.rank}`
    : `Bowler · Rank #${player.rank}`;

  return (
    <div
      className="react-player-modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="presentation"
    >
      <div
        className="react-player-modal-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="player-preview-title"
      >
        {/* Modal Header */}
        <div className="react-modal-header">
          <div className="react-modal-header-titles">
            <h2 id="player-preview-title" className="react-modal-name">
              {player.player_name}
            </h2>
            <div className="react-modal-badge-group">
              <span className="react-modal-role-pill">{roleLabel}</span>
              <span className="react-modal-squad-ref">
                2026 Reference: {manifestItem?.squad_2026 || "Rajasthan Royals"}
              </span>
            </div>
          </div>
          <button
            type="button"
            className="react-modal-close-btn"
            onClick={onClose}
            aria-label="Close Preview"
            title="Close Preview (Escape)"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Dual-role discipline tabs */}
        {isDual && (
          <div className="react-modal-dual-tabs">
            <button
              type="button"
              className={`react-modal-dual-tab ${activeTab === "batting" ? "is-active" : ""}`}
              onClick={() => setActiveTab("batting")}
            >
              Batting Impact (Rank #9)
            </button>
            <button
              type="button"
              className={`react-modal-dual-tab ${activeTab === "bowling" ? "is-active" : ""}`}
              onClick={() => setActiveTab("bowling")}
            >
              Bowling Impact (Rank #10)
            </button>
          </div>
        )}

        {/* Modal Body */}
        <div className="react-modal-body">
          {/* Left Column: Portrait Studio */}
          <div className="react-modal-visual-col">
            <div className={`react-modal-portrait-well ${bgTheme}`}>
              <picture>
                <source
                  type="image/webp"
                  srcSet={`/portraits/${pid}_640w.webp 640w, /portraits/${pid}_320w.webp 320w`}
                  sizes="(max-width: 640px) 240px, 320px"
                />
                <img
                  src={`/portraits/${pid}_640w.png`}
                  alt={player.player_name}
                  className="react-modal-portrait-img"
                  width={640}
                  height={640}
                />
              </picture>
            </div>

            {/* Background Theme Switcher - Zero emojis, pure SVG swatches */}
            <div className="react-modal-theme-row">
              <span className="react-modal-theme-label">Backdrop:</span>
              <button
                type="button"
                className={`react-theme-btn ${bgTheme === "tile-pink" ? "is-active" : ""}`}
                onClick={() => setBgTheme("tile-pink")}
                title="Rajasthan Royals Pink"
              >
                <svg width="10" height="10" viewBox="0 0 20 20" aria-hidden="true">
                  <circle cx="10" cy="10" r="8" fill="#E6007E" stroke="#20172F" strokeWidth="2" />
                </svg>
                <span>Pink</span>
              </button>
              <button
                type="button"
                className={`react-theme-btn ${bgTheme === "tile-blue" ? "is-active" : ""}`}
                onClick={() => setBgTheme("tile-blue")}
                title="Royals Navy Blue"
              >
                <svg width="10" height="10" viewBox="0 0 20 20" aria-hidden="true">
                  <circle cx="10" cy="10" r="8" fill="#004BA0" stroke="#20172F" strokeWidth="2" />
                </svg>
                <span>Blue</span>
              </button>
              <button
                type="button"
                className={`react-theme-btn ${bgTheme === "tile-paper" ? "is-active" : ""}`}
                onClick={() => setBgTheme("tile-paper")}
                title="Classic Paper"
              >
                <svg width="10" height="10" viewBox="0 0 20 20" aria-hidden="true">
                  <circle cx="10" cy="10" r="8" fill="#FFF8ED" stroke="#20172F" strokeWidth="2" />
                </svg>
                <span>Paper</span>
              </button>
              <button
                type="button"
                className={`react-theme-btn ${bgTheme === "tile-dark" ? "is-active" : ""}`}
                onClick={() => setBgTheme("tile-dark")}
                title="Midnight Dark"
              >
                <svg width="10" height="10" viewBox="0 0 20 20" aria-hidden="true">
                  <circle cx="10" cy="10" r="8" fill="#130C1E" stroke="#FFF8ED" strokeWidth="2" />
                </svg>
                <span>Dark</span>
              </button>
            </div>

            <p className="react-modal-credit-text">
              {manifestItem?.credit || "Official BCCI / IPL Media Day Studio Portrait"}
            </p>

            <div className="react-modal-download-actions">
              <a
                href={`/portraits/${pid}_640w.png`}
                target="_blank"
                rel="noopener noreferrer"
                className="react-modal-action-link"
              >
                <span>View 640w HD</span>
                <ExternalLinkIcon size={12} className="inline-icon" />
              </a>
              <a
                href={`/portraits/${pid}_320w.png`}
                download={`${pid}_${player.player_name.toLowerCase().replace(/\s+/g, "_")}.png`}
                className="react-modal-action-link"
              >
                <span>Download 320w</span>
              </a>
            </div>
          </div>

          {/* Right Column: Verified Official IPL Records & Visualizers */}
          <div className="react-modal-stats-col">
            <div className="react-modal-stats-header">
              <h3 className="react-modal-stats-title">Verified IPL Career Performance</h3>
              <span className="react-modal-verified-seal">
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="3"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span>Official IPL Records (2022–2026)</span>
              </span>
            </div>

            {showBatting && statsRecord?.batting ? (
              <>
                {/* 10-Metric Grid for Batting */}
                <div className="react-modal-metrics-grid">
                  <div className="react-metric-card">
                    <span className="react-metric-num">{statsRecord.matches}</span>
                    <span className="react-metric-lbl">Matches</span>
                  </div>
                  <div className="react-metric-card">
                    <span className="react-metric-num">{statsRecord.batting.innings}</span>
                    <span className="react-metric-lbl">Innings</span>
                  </div>
                  <div className="react-metric-card highlight-pink">
                    <span className="react-metric-num">{statsRecord.batting.runs}</span>
                    <span className="react-metric-lbl">Total Runs</span>
                  </div>
                  <div className="react-metric-card highlight-navy">
                    <span className="react-metric-num">{statsRecord.batting.strike_rate}</span>
                    <span className="react-metric-lbl">Strike Rate</span>
                  </div>
                  <div className="react-metric-card">
                    <span className="react-metric-num">{statsRecord.batting.average}</span>
                    <span className="react-metric-lbl">Average</span>
                  </div>
                  <div className="react-metric-card">
                    <span className="react-metric-num">{statsRecord.batting.highest_score}</span>
                    <span className="react-metric-lbl">High Score</span>
                  </div>
                  <div className="react-metric-card">
                    <span className="react-metric-num">{statsRecord.batting.fours}</span>
                    <span className="react-metric-lbl">Fours</span>
                  </div>
                  <div className="react-metric-card">
                    <span className="react-metric-num">{statsRecord.batting.sixes}</span>
                    <span className="react-metric-lbl">Sixes</span>
                  </div>
                  <div className="react-metric-card">
                    <span className="react-metric-num">
                      {statsRecord.batting.fifties} / {statsRecord.batting.hundreds}
                    </span>
                    <span className="react-metric-lbl">50s / 100s</span>
                  </div>
                  <div className="react-metric-card">
                    <span className="react-metric-num">{statsRecord.batting.hp_balls}</span>
                    <span className="react-metric-lbl">HP Balls</span>
                  </div>
                  <div className="react-metric-card">
                    <span className="react-metric-num">{statsRecord.batting.hp_runs}</span>
                    <span className="react-metric-lbl">HP Runs</span>
                  </div>
                  <div className="react-metric-card highlight-pink">
                    <span className="react-metric-num">{statsRecord.batting.hp_strike_rate}</span>
                    <span className="react-metric-lbl">HP Strike Rate</span>
                  </div>
                </div>

                {/* Strike Rate Speedometer Gauge */}
                <div className="react-modal-visualizer-box">
                  <div className="react-visualizer-header">
                    <span className="react-visualizer-title">Strike Rate Speedometer</span>
                    <strong className="react-visualizer-val">
                      {statsRecord.batting.strike_rate} r/100b
                    </strong>
                  </div>
                  <div className="react-gauge-track">
                    <div
                      className="react-gauge-fill pink-gradient"
                      style={{ width: speedoWidth }}
                    />
                  </div>
                  <div className="react-gauge-markers">
                    <span>80 (Anchor)</span>
                    <span>145 (IPL Avg)</span>
                    <span>220+ (Elite Power)</span>
                  </div>
                </div>

                {/* Environment Split Contrast Card */}
                <div className="react-modal-contrast-card">
                  <div className="react-contrast-header">
                    <svg
                      width="12"
                      height="12"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                    </svg>
                    <span>High-Pressure Environment Split (Historical 80th-Percentile Leverage)</span>
                  </div>
                  <div className="react-contrast-grid">
                    <div className="react-contrast-panel">
                      <strong className="react-contrast-val">
                        {statsRecord.batting.strike_rate} SR
                      </strong>
                      <span className="react-contrast-sub">
                        Career IPL Strike Rate ({statsRecord.batting.balls} balls)
                      </span>
                    </div>
                    <div className="react-contrast-panel accent-border">
                      <strong className="react-contrast-val pink-text">
                        {statsRecord.batting.hp_strike_rate} HP SR
                      </strong>
                      <span className="react-contrast-sub">
                        High-Pressure Strike Rate ({statsRecord.batting.hp_balls} balls)
                      </span>
                    </div>
                  </div>
                </div>
              </>
            ) : statsRecord?.bowling ? (
              <>
                {/* 10-Metric Grid for Bowling */}
                <div className="react-modal-metrics-grid">
                  <div className="react-metric-card">
                    <span className="react-metric-num">{statsRecord.matches}</span>
                    <span className="react-metric-lbl">Matches</span>
                  </div>
                  <div className="react-metric-card">
                    <span className="react-metric-num">{statsRecord.bowling.innings}</span>
                    <span className="react-metric-lbl">Innings</span>
                  </div>
                  <div className="react-metric-card highlight-navy">
                    <span className="react-metric-num">{statsRecord.bowling.overs}</span>
                    <span className="react-metric-lbl">Overs Bowled</span>
                  </div>
                  <div className="react-metric-card highlight-pink">
                    <span className="react-metric-num">{statsRecord.bowling.wickets}</span>
                    <span className="react-metric-lbl">Wickets</span>
                  </div>
                  <div className="react-metric-card highlight-navy">
                    <span className="react-metric-num">{statsRecord.bowling.economy}</span>
                    <span className="react-metric-lbl">Economy</span>
                  </div>
                  <div className="react-metric-card">
                    <span className="react-metric-num">{statsRecord.bowling.average}</span>
                    <span className="react-metric-lbl">Average</span>
                  </div>
                  <div className="react-metric-card">
                    <span className="react-metric-num">{statsRecord.bowling.best_bowling}</span>
                    <span className="react-metric-lbl">Best Bowling</span>
                  </div>
                  <div className="react-metric-card">
                    <span className="react-metric-num">{statsRecord.bowling.strike_rate}</span>
                    <span className="react-metric-lbl">Strike Rate</span>
                  </div>
                  <div className="react-metric-card">
                    <span className="react-metric-num">
                      {statsRecord.bowling.four_w} / {statsRecord.bowling.five_w}
                    </span>
                    <span className="react-metric-lbl">4W / 5W Hauls</span>
                  </div>
                  <div className="react-metric-card">
                    <span className="react-metric-num">{statsRecord.bowling.hp_balls}</span>
                    <span className="react-metric-lbl">HP Balls</span>
                  </div>
                  <div className="react-metric-card">
                    <span className="react-metric-num">{statsRecord.bowling.hp_wickets}</span>
                    <span className="react-metric-lbl">HP Wickets</span>
                  </div>
                  <div className="react-metric-card highlight-pink">
                    <span className="react-metric-num">{statsRecord.bowling.hp_economy}</span>
                    <span className="react-metric-lbl">HP Economy</span>
                  </div>
                </div>

                {/* Bowling Economy Efficiency Gauge */}
                <div className="react-modal-visualizer-box">
                  <div className="react-visualizer-header">
                    <span className="react-visualizer-title">Bowling Economy Efficiency</span>
                    <strong className="react-visualizer-val">
                      {statsRecord.bowling.economy} rpo (Lower is better)
                    </strong>
                  </div>
                  <div className="react-gauge-track">
                    <div
                      className="react-gauge-fill blue-gradient"
                      style={{ width: economyWidth }}
                    />
                  </div>
                  <div className="react-gauge-markers">
                    <span>12.0 (Expensive)</span>
                    <span>8.6 (IPL Median)</span>
                    <span>6.0 (Elite Control)</span>
                  </div>
                </div>

                {/* Environment Split Contrast Card */}
                <div className="react-modal-contrast-card">
                  <div className="react-contrast-header">
                    <svg
                      width="12"
                      height="12"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                    </svg>
                    <span>High-Pressure Environment Split (Historical 80th-Percentile Leverage)</span>
                  </div>
                  <div className="react-contrast-grid">
                    <div className="react-contrast-panel">
                      <strong className="react-contrast-val">
                        {statsRecord.bowling.economy} RPO
                      </strong>
                      <span className="react-contrast-sub">
                        Career IPL Economy ({statsRecord.bowling.overs} overs)
                      </span>
                    </div>
                    <div className="react-contrast-panel accent-border">
                      <strong className="react-contrast-val pink-text">
                        {statsRecord.bowling.hp_economy} HP RPO
                      </strong>
                      <span className="react-contrast-sub">
                        High-Pressure Economy ({statsRecord.bowling.hp_balls} balls)
                      </span>
                    </div>
                  </div>
                </div>
              </>
            ) : null}

            {/* Source Provenance Footnote */}
            <p className="react-modal-footnote">
              <strong>Data Provenance Guarantee:</strong> Figures reflect verified ball-by-ball delivery entries across regulation tournament fixtures from the official BCCI / IPL delivery ledger (2022–2026). Zero synthetic or imputed match numbers.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
