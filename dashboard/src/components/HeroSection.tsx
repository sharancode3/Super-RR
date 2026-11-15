import React from "react";
import { YouTubeIcon } from "./Icons";

interface HeroSectionProps {
  onOpenVideo?: () => void;
}

export const HeroSection: React.FC<HeroSectionProps> = ({ onOpenVideo }) => {
  return (
    <section className="hero-section" aria-labelledby="hero-title">
      <div className="hero-container">
        <div className="hero-badge-row">
          <span className="hero-pill-primary">
            Rajasthan Royals Scouting Board
          </span>
          <span className="hero-pill-scope">
            160 Model Fits · 1,000 Resamples · 19 Shortlisted Targets
          </span>
          {onOpenVideo && (
            <button
              type="button"
              onClick={onOpenVideo}
              className="hero-pill-video"
              title="Watch 60-second video walkthrough on YouTube (Popup)"
              aria-label="Watch 60-second video walkthrough on YouTube"
            >
              <YouTubeIcon size={16} className="hero-yt-icon" />
              <span>Watch Walkthrough (60s)</span>
            </button>
          )}
        </div>

        <h1 id="hero-title" className="hero-headline">
          Players Rajasthan Royals can back under pressure
        </h1>

        <p className="hero-scope">
          Two ranked top tens built for Rajasthan Royals’ 2027 squad strategy.
          Each pick is verified by real match leverage, forward-chaining backtests,
          and cluster-bootstrap stability bounds.
        </p>
      </div>
    </section>
  );
};
