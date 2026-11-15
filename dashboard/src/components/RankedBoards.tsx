import React, { useState, useEffect } from "react";
import type { RankingRecord } from "../data/types";
import { getAnchorId } from "../data/formatters";
import { PlayerCard } from "./PlayerCard";
import { PinIcon, ChevronDownIcon, ChevronUpIcon } from "./Icons";

interface RankedBoardsProps {
  batters: RankingRecord[];
  bowlers: RankingRecord[];
  onPreviewPlayer?: (player: RankingRecord) => void;
}

export const RankedBoards: React.FC<RankedBoardsProps> = ({
  batters,
  bowlers,
  onPreviewPlayer,
}) => {
  const sortedBatters = [...batters].sort((a, b) => a.rank - b.rank);
  const sortedBowlers = [...bowlers].sort((a, b) => a.rank - b.rank);

  const [activeDiscipline, setActiveDiscipline] = useState<"batting" | "bowling">("batting");
  const [activeBatterRank, setActiveBatterRank] = useState<number>(1);
  const [activeBowlerRank, setActiveBowlerRank] = useState<number>(1);

  // Scroll spy to track currently viewed player & discipline as user scrolls down
  useEffect(() => {
    const handleScroll = () => {
      const bowlersSection = document.getElementById("bowlers");
      if (bowlersSection) {
        const bRect = bowlersSection.getBoundingClientRect();
        if (bRect.top <= 240) {
          setActiveDiscipline("bowling");
        } else {
          setActiveDiscipline("batting");
        }
      }

      sortedBatters.forEach((p) => {
        const el = document.getElementById(getAnchorId("batting", p.player_name));
        if (el) {
          const rect = el.getBoundingClientRect();
          if (rect.top <= 320 && rect.bottom >= 120) {
            setActiveBatterRank(p.rank);
          }
        }
      });

      sortedBowlers.forEach((p) => {
        const el = document.getElementById(getAnchorId("bowling", p.player_name));
        if (el) {
          const rect = el.getBoundingClientRect();
          if (rect.top <= 320 && rect.bottom >= 120) {
            setActiveBowlerRank(p.rank);
          }
        }
      });
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, [sortedBatters, sortedBowlers]);

  // Jump smoothly to a specific player card
  const scrollToPlayer = (
    role: "batting" | "bowling",
    playerName: string,
    rank: number
  ) => {
    setActiveDiscipline(role);
    const el = document.getElementById(getAnchorId(role, playerName));
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      if (role === "batting") setActiveBatterRank(rank);
      else setActiveBowlerRank(rank);

      const card = el.querySelector("[data-reveal]");
      if (card) card.setAttribute("data-reveal", "revealed");
    }
  };

  // Step down or up by rank
  const stepRank = (
    role: "batting" | "bowling",
    currentRank: number,
    delta: number
  ) => {
    const list = role === "batting" ? sortedBatters : sortedBowlers;
    const newRank = Math.max(1, Math.min(10, currentRank + delta));
    const target = list[newRank - 1];
    if (target) {
      scrollToPlayer(role, target.player_name, newRank);
    }
  };

  // Listen to hash changes for deep linking (e.g. Jadeja cross-links)
  useEffect(() => {
    const handleHash = () => {
      const hash = window.location.hash.replace("#", "");
      if (!hash) return;

      if (hash.startsWith("bowling-") || hash === "bowlers") {
        setActiveDiscipline("bowling");
      } else if (hash.startsWith("batting-") || hash === "batters") {
        setActiveDiscipline("batting");
      }

      const targetEl = document.getElementById(hash);
      if (targetEl) {
        targetEl.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    };

    window.addEventListener("hashchange", handleHash);
    return () => window.removeEventListener("hashchange", handleHash);
  }, []);

  const isBatting = activeDiscipline === "batting";
  const currentList = isBatting ? sortedBatters : sortedBowlers;
  const activeRank = isBatting ? activeBatterRank : activeBowlerRank;
  const currentPlayer = currentList[activeRank - 1] || currentList[0];

  const activeBatter = sortedBatters[activeBatterRank - 1] || sortedBatters[0];
  const activeBowler = sortedBowlers[activeBowlerRank - 1] || sortedBowlers[0];

  return (
    <div id="ranked-boards" className="ranked-boards-wrapper" aria-label="Rajasthan Royals Ranked Boards">
      {/* =========================================================================
          PERSISTENT STICKY SCOUTING COMMAND BAR (Always docked at top while scrolling)
          ========================================================================= */}
      <nav
        className="persistent-sticky-command-bar sticky-rank-bar"
        aria-label="Rajasthan Royals Scouting Command Bar"
        id="scouting-command-bar"
      >
        <div className="command-bar-container">
          {/* Discipline Switcher: Batters vs Bowlers */}
          <div className="command-bar-disciplines">
            <button
              type="button"
              className={`disc-switch-btn btn-disc-batters ${isBatting ? "is-active" : ""}`}
              onClick={() => {
                setActiveDiscipline("batting");
                scrollToPlayer("batting", activeBatter.player_name, activeBatterRank);
              }}
              title="Jump to Batters Roster"
            >
              <span className="disc-dot dot-batters" aria-hidden="true" />
              <span className="disc-name">Batters</span>
              <span className="disc-count">(10)</span>
            </button>
            <button
              type="button"
              className={`disc-switch-btn btn-disc-bowlers ${!isBatting ? "is-active" : ""}`}
              onClick={() => {
                setActiveDiscipline("bowling");
                scrollToPlayer("bowling", activeBowler.player_name, activeBowlerRank);
              }}
              title="Jump to Bowlers Roster"
            >
              <span className="disc-dot dot-bowlers" aria-hidden="true" />
              <span className="disc-name">Bowlers</span>
              <span className="disc-count">(10)</span>
            </button>
          </div>

          {/* Stepper Controls & Current Player Label */}
          <div className="command-bar-stepper">
            <div className="step-btn-group">
              <button
                type="button"
                className="step-arrow-btn btn-prev"
                onClick={() => stepRank(activeDiscipline, activeRank, -1)}
                disabled={activeRank === 1}
                aria-label={`Previous ${isBatting ? "batter" : "bowler"} card`}
                title="Scroll up to previous player"
              >
                <ChevronUpIcon size={14} />
              </button>
              <button
                type="button"
                className="step-arrow-btn btn-next"
                onClick={() => stepRank(activeDiscipline, activeRank, 1)}
                disabled={activeRank === 10}
                aria-label={`Next ${isBatting ? "batter" : "bowler"} card`}
                title="Scroll down to next player"
              >
                <ChevronDownIcon size={14} />
              </button>
            </div>

            <div className="live-rank-counter">
              <span className="counter-badge">#{currentPlayer.rank}</span>
              <span className="counter-name">{currentPlayer.player_name}</span>
              <span className="counter-total">(Rank {currentPlayer.rank} of 10)</span>
            </div>
          </div>

          {/* Quick Jump Rank Pills for Active Discipline */}
          <div
            className="rank-pills-bar"
            role="tablist"
            aria-label={`${isBatting ? "Batters" : "Bowlers"} quick rank navigation`}
          >
            {currentList.map((p) => {
              const surname = p.player_name.split(" ").slice(-1)[0];
              const isActive = activeRank === p.rank;
              return (
                <button
                  key={`${activeDiscipline}-pill-${p.rank}`}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  className={`rank-pill-item ${isActive ? "active-pill" : ""}`}
                  onClick={() => scrollToPlayer(activeDiscipline, p.player_name, p.rank)}
                  title={`Scroll to #${p.rank} ${p.player_name}`}
                >
                  <span className="pill-num">#{p.rank}</span>
                  <span className="pill-surname">{surname}</span>
                </button>
              );
            })}
          </div>

          {/* Quick Jump Link to Methodology */}
          <div className="command-bar-extras">
            <a href="#methodology" className="quick-jump-link" title="Jump to model training & research journey">
              How I trained the model <ChevronDownIcon size={11} className="inline-chevron" />
            </a>
          </div>
        </div>
      </nav>

      {/* =========================================================================
          BATTERS BOARD (Discipline 01) · DOWN-WISE CARDS STREAM
          ========================================================================= */}
      <section
        id="batters"
        className="discipline-showcase-section showcase-batters"
        aria-labelledby="batters-board-title"
      >
        <div className="showcase-container">
          <div className="showcase-header">
            <div className="showcase-title-row">
              <div className="showcase-title-group">
                <span className="board-discipline-tag tag-batters">
                  Discipline 01
                </span>
                <h2 id="batters-board-title" className="showcase-title">
                  Batters · 10 Ranked Targets
                </h2>
              </div>
              <div className="showcase-badge-pill pill-batters">
                <span>Powerplay, Middle &amp; Finishers · Pressure Backtested</span>
              </div>
            </div>

            <div className="board-direction-legend">
              <span className="legend-icon" aria-hidden="true">
                <PinIcon size={13} />
              </span>
              <span>
                <strong>Direction guide:</strong> Positive impact represents favourable scoring vs context.
                Uplift is pressure minus ordinary level. All 10 batters verified by Bayesian volume shrinkage.
              </span>
            </div>
          </div>

          {/* Semantic Ordered List with exactly 10 down-wise cards */}
          <ol
            className="board-players-ol downwise-cards-ol"
            aria-label="Batters ranked 1 through 10 in recommended order"
          >
            {sortedBatters.map((player) => (
              <li
                key={`batter-${player.player_id}-${player.rank}`}
                id={getAnchorId("batting", player.player_name)}
                className={`player-list-item downwise-item ${player.rank === 1 ? "item-leader" : "item-standard"}`}
                tabIndex={-1}
              >
                <PlayerCard
                  player={player}
                  role="batting"
                  isLeader={player.rank === 1}
                  isActive={isBatting && activeBatterRank === player.rank}
                  onPreview={onPreviewPlayer}
                />
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* =========================================================================
          BOWLERS BOARD (Discipline 02) · DOWN-WISE CARDS STREAM
          ========================================================================= */}
      <section
        id="bowlers"
        className="discipline-showcase-section showcase-bowlers"
        aria-labelledby="bowlers-board-title"
      >
        <div className="showcase-container">
          <div className="showcase-header">
            <div className="showcase-title-row">
              <div className="showcase-title-group">
                <span className="board-discipline-tag tag-bowlers">
                  Discipline 02
                </span>
                <h2 id="bowlers-board-title" className="showcase-title">
                  Bowlers · 10 Ranked Arsenal
                </h2>
              </div>
              <div className="showcase-badge-pill pill-bowlers">
                <span>Powerplay, Death Overs &amp; Spin · Runs Saved vs Context</span>
              </div>
            </div>

            <div className="board-direction-legend">
              <span className="legend-icon" aria-hidden="true">
                <PinIcon size={13} />
              </span>
              <span>
                <strong>Direction guide:</strong> Positive impact represents runs saved / prevention vs expectation.
                Uplift is pressure minus ordinary economy. All 10 bowlers backtested across 1,000 resamples.
              </span>
            </div>
          </div>

          {/* Semantic Ordered List with exactly 10 down-wise cards */}
          <ol
            className="board-players-ol downwise-cards-ol"
            aria-label="Bowlers ranked 1 through 10 in recommended order"
          >
            {sortedBowlers.map((player) => (
              <li
                key={`bowler-${player.player_id}-${player.rank}`}
                id={getAnchorId("bowling", player.player_name)}
                className={`player-list-item downwise-item ${player.rank === 1 ? "item-leader" : "item-standard"}`}
                tabIndex={-1}
              >
                <PlayerCard
                  player={player}
                  role="bowling"
                  isLeader={player.rank === 1}
                  isActive={!isBatting && activeBowlerRank === player.rank}
                  onPreview={onPreviewPlayer}
                />
              </li>
            ))}
          </ol>
        </div>
      </section>
    </div>
  );
};
