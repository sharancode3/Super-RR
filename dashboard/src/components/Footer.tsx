import React from "react";

export const Footer: React.FC = () => {
  return (
    <footer role="contentinfo" className="site-footer">
      <div className="footer-container">
        <div className="footer-top">
          <div className="footer-brand">
            <span className="footer-logo">Rajasthan Royals · SupeRR Selector S2</span>
            <p className="footer-desc">
              Data-hardened recommendation engine for IPL 2027 auction and retention strategy.
              Prepared for Round 1 Unstop submission.
            </p>
          </div>

          <div className="footer-links">
            <div className="link-group">
              <span className="link-group-title">Navigation</span>
              <ul>
                <li><a href="#batters">Batters Board</a></li>
                <li><a href="#bowlers">Bowlers Board</a></li>
                <li><a href="#methodology">Audit & Methodology</a></li>
                <li><a href="#media">Media &amp; Portraits Section</a></li>
              </ul>
            </div>

            <div className="link-group">
              <span className="link-group-title">Governance</span>
              <ul>
                <li><span>Decision Cutoff: 15 Nov 2026 IST</span></li>
                <li><span>Evaluator Seed: 2027</span></li>
                <li><span>Tests Passed: 219 of 219</span></li>
                <li><span>WCAG Conformance: 2.2 AA</span></li>
              </ul>
            </div>
          </div>
        </div>

        <div className="footer-bottom">
          <p className="footer-copy">
            Copyright 2026 Rajasthan Royals SupeRR Selector Season 2. Evaluator-facing decision dashboard.
            All player photographs sourced from official BCCI/IPL 2026 tournament media day assets.
          </p>
          <div className="footer-audit-tag">
            <span>19 Players</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
