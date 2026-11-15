import React, { useState } from "react";
import portraitsManifest from "../data/portraits_manifest.json";
import playerIplStats from "../data/player_ipl_stats.json";
import { evidence } from "../data";
import type { RankingRecord } from "../data/types";
import {
  PhotoIcon,
  SearchIcon,
  ExternalLinkIcon,
  BatIcon,
  CricketBallIcon,
} from "./Icons";

interface MediaSectionProps {
  onPreviewPlayer: (player: RankingRecord) => void;
}

type MediaFilter = "all" | "batters" | "bowlers";

interface PlayerStatRecord {
  id: number;
  name: string;
  role: string;
  matches: number;
  is_batter: boolean;
  is_bowler: boolean;
  batting: {
    runs: number;
    strike_rate: number;
    average: number;
    highest_score: number | string;
    fifties: number;
    hundreds: number;
    hp_balls: number;
  };
  bowling: {
    wickets: number;
    overs: number;
    economy: number;
    average: number;
    best_bowling: string;
    four_w: number;
    five_w: number;
    hp_balls: number;
  };
}

export const MediaSection: React.FC<MediaSectionProps> = ({ onPreviewPlayer }) => {
  const [filter, setFilter] = useState<MediaFilter>("all");

  const statsMap = playerIplStats as unknown as Record<string, PlayerStatRecord>;

  const filteredPlayers = portraitsManifest.filter((p) => {
    if (filter === "batters") return p.role === "BATTER" || p.player_id === 152;
    if (filter === "bowlers") return p.role === "BOWLER" || p.role === "DUAL_ROLE";
    return true;
  });

  const handleCardClick = (pid: number) => {
    // Find matching RankingRecord in evidence.rankings
    const match =
      evidence.rankings.find((r) => r.player_id === pid) ||
      evidence.rankings[0];
    onPreviewPlayer(match);
  };

  return (
    <section id="media" className="media-section" aria-labelledby="media-section-title">
      <div className="media-container">
        {/* Section Header */}
        <div className="media-header">
          <div className="media-header-badge">
            <PhotoIcon size={14} />
            <span>OFFICIAL IPL MEDIA ASSETS &amp; STUDIO CARDS</span>
          </div>
          <h2 id="media-section-title" className="media-title">
            Media Section: Official Player Cards &amp; IPL Performance
          </h2>
          <p className="media-subtitle">
            19 Identity-Verified Official Master Portraits with #FFF8ED Paper Stroke &amp; 2022–2026 IPL Ball-by-Ball Records
          </p>

          <div className="media-interactive-notice">
            <span className="notice-icon"><SearchIcon size={16} /></span>
            <span className="notice-text">
              <strong>Interactive Studio:</strong> Click any card tile or the <em>&quot;Preview Card &amp; Official IPL Stats&quot;</em> button to inspect high-resolution cutouts, customize studio canvas tones, and view verified IPL career performance.
            </span>
          </div>

          {/* Discipline Filters */}
          <div className="media-filter-bar" role="tablist" aria-label="Media filter tabs">
            <button
              type="button"
              role="tab"
              aria-selected={filter === "all"}
              className={`media-filter-btn ${filter === "all" ? "active" : ""}`}
              onClick={() => setFilter("all")}
            >
              All Players (19)
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={filter === "batters"}
              className={`media-filter-btn ${filter === "batters" ? "active" : ""}`}
              onClick={() => setFilter("batters")}
            >
              <BatIcon size={14} />
              <span>Batters (10)</span>
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={filter === "bowlers"}
              className={`media-filter-btn ${filter === "bowlers" ? "active" : ""}`}
              onClick={() => setFilter("bowlers")}
            >
              <CricketBallIcon size={14} />
              <span>Bowlers (9 + Dual)</span>
            </button>
          </div>
        </div>

        {/* Players Grid */}
        <div className="media-players-grid">
          {filteredPlayers.map((p) => {
            const stats = statsMap[String(p.player_id)];
            const isBatter = p.role === "BATTER" || p.role === "DUAL_ROLE";
            const isBowler = p.role === "BOWLER" || p.role === "DUAL_ROLE";

            return (
              <div
                key={`media-player-${p.player_id}`}
                className={`media-player-card ${p.is_leader ? "is-leader" : ""}`}
                id={`media-card-${p.player_id}`}
              >
                {/* 4-Tone Preview Tiles */}
                <div
                  className="media-tiles-col"
                  onClick={() => handleCardClick(p.player_id)}
                  title={`Click to preview ${p.name}'s card and official IPL stats`}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      handleCardClick(p.player_id);
                    }
                  }}
                >
                  <div className="media-preview-tiles">
                    <div className="media-tile tile-pink">
                      <img
                        src={`/portraits/${p.player_id}_320w.webp`}
                        alt=""
                        loading="lazy"
                        width={90}
                        height={90}
                      />
                      <span className="tile-label">Pink Tile</span>
                    </div>
                    <div className="media-tile tile-blue">
                      <img
                        src={`/portraits/${p.player_id}_320w.webp`}
                        alt=""
                        loading="lazy"
                        width={90}
                        height={90}
                      />
                      <span className="tile-label">Blue Tile</span>
                    </div>
                    <div className="media-tile tile-paper">
                      <img
                        src={`/portraits/${p.player_id}_320w.webp`}
                        alt=""
                        loading="lazy"
                        width={90}
                        height={90}
                      />
                      <span className="tile-label">Paper Tile</span>
                    </div>
                    <div className="media-tile tile-dark">
                      <img
                        src={`/portraits/${p.player_id}_320w.webp`}
                        alt=""
                        loading="lazy"
                        width={90}
                        height={90}
                      />
                      <span className="tile-label">Dark Tile</span>
                    </div>
                  </div>
                </div>

                {/* Player Meta & Verified Stats */}
                <div className="media-info-col">
                  <div className="media-card-header">
                    <div className="media-title-row">
                      <h3 className="media-card-name">{p.name}</h3>
                      {p.is_leader ? (
                        <span className="media-leader-badge">LEADER #1</span>
                      ) : (
                        <span className="media-rank-badge">RANK #{p.rank}</span>
                      )}
                    </div>
                    <div className="media-card-meta">
                      <span>ID: {p.player_id}</span>
                      <span>·</span>
                      <span>Discipline: {p.role}</span>
                      <span>·</span>
                      <span>2026 Reference: {p.squad_2026}</span>
                      <span>·</span>
                      <span>Sizes: 320w / 640w HD Master</span>
                      <span>·</span>
                      <span>Credit: {p.credit}</span>
                    </div>
                  </div>

                  {/* Verified IPL Performance Stats */}
                  {stats && (
                    <div className="media-ipl-stats-row">
                      <div className="media-stat-pill">
                        <span className="stat-label">IPL Matches:</span>
                        <strong className="stat-value">{stats.matches}</strong>
                      </div>

                      {isBatter && (
                        <>
                          <div className="media-stat-pill">
                            <span className="stat-label">Runs:</span>
                            <strong className="stat-value">{stats.batting.runs}</strong>
                          </div>
                          <div className="media-stat-pill">
                            <span className="stat-label">SR:</span>
                            <strong className="stat-value">{stats.batting.strike_rate}</strong>
                          </div>
                          <div className="media-stat-pill">
                            <span className="stat-label">Avg:</span>
                            <strong className="stat-value">{stats.batting.average}</strong>
                          </div>
                          <div className="media-stat-pill">
                            <span className="stat-label">HS:</span>
                            <strong className="stat-value">{stats.batting.highest_score}</strong>
                          </div>
                          <div className="media-stat-pill">
                            <span className="stat-label">50s/100s:</span>
                            <strong className="stat-value">
                              {stats.batting.fifties}/{stats.batting.hundreds}
                            </strong>
                          </div>
                          <div className="media-stat-pill">
                            <span className="stat-label">HP Balls:</span>
                            <strong className="stat-value">{stats.batting.hp_balls}</strong>
                          </div>
                        </>
                      )}

                      {isBowler && !isBatter && (
                        <>
                          <div className="media-stat-pill">
                            <span className="stat-label">Wickets:</span>
                            <strong className="stat-value">{stats.bowling.wickets}</strong>
                          </div>
                          <div className="media-stat-pill">
                            <span className="stat-label">Econ:</span>
                            <strong className="stat-value">{stats.bowling.economy}</strong>
                          </div>
                          <div className="media-stat-pill">
                            <span className="stat-label">Avg:</span>
                            <strong className="stat-value">{stats.bowling.average}</strong>
                          </div>
                          <div className="media-stat-pill">
                            <span className="stat-label">Best:</span>
                            <strong className="stat-value">{stats.bowling.best_bowling}</strong>
                          </div>
                          <div className="media-stat-pill">
                            <span className="stat-label">4w/5w:</span>
                            <strong className="stat-value">
                              {stats.bowling.four_w}/{stats.bowling.five_w}
                            </strong>
                          </div>
                          <div className="media-stat-pill">
                            <span className="stat-label">HP Balls:</span>
                            <strong className="stat-value">{stats.bowling.hp_balls}</strong>
                          </div>
                        </>
                      )}

                      {p.role === "DUAL_ROLE" && (
                        <div className="media-stat-pill" style={{ background: "#EEF2FF" }}>
                          <span className="stat-label">Bowling:</span>
                          <strong className="stat-value">
                            {stats.bowling.wickets} wkts @ {stats.bowling.economy} econ
                          </strong>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="media-card-actions">
                    <button
                      type="button"
                      className="btn-media-preview"
                      onClick={() => handleCardClick(p.player_id)}
                    >
                      <SearchIcon size={14} />
                      <span>Preview Card &amp; Official IPL Stats</span>
                    </button>
                    <a
                      href={`/portraits/${p.player_id}_640w.png`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-media-view-png"
                    >
                      <span>View 640w PNG</span>
                      <ExternalLinkIcon size={13} />
                    </a>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
