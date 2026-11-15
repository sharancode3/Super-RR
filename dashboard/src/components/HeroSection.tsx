import React from "react";

export const HeroSection: React.FC = () => {
  return (
    <section className="hero-section" aria-labelledby="hero-title">
      <div className="hero-container">
        <div className="hero-badge-row">
          <span className="hero-pill-primary">
            Rajasthan Royals Scouting Board
          </span>
          <span className="hero-pill-scope">
            15 November 2026 IST · 160 Model Fits · 1,000 Resamples · 19 Unique Identities
          </span>
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
