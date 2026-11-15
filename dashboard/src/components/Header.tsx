import React from "react";
import {
  RajasthanRoyalsLogo,
  BatIcon,
  CricketBallIcon,
  SlidersIcon,
  MethodologyIcon,
  PhotoIcon,
} from "./Icons";

export const Header: React.FC = () => {
  return (
    <>
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <header role="banner" className="site-header">
        <div className="header-container">
          <div className="brand-group">
            <a
              href="#batters"
              className="rr-crest"
              title="Rajasthan Royals · Official Crest · Return to top"
              aria-label="Rajasthan Royals · Official Crest · Return to top"
            >
              <RajasthanRoyalsLogo size={32} />
            </a>
            <div className="brand-titles">
              <span className="brand-title">SupeRR Selector Season 2</span>
              <span className="brand-subtitle">Rajasthan Royals · IPL 2027</span>
            </div>
          </div>

          <nav role="navigation" aria-label="Primary Anchor Navigation" className="primary-nav">
            <ul className="nav-list">
              <li>
                <a href="#batters" className="nav-link nav-batters">
                  <span className="nav-icon" aria-hidden="true"><BatIcon size={14} /></span>
                  Batters
                </a>
              </li>
              <li>
                <a href="#bowlers" className="nav-link nav-bowlers">
                  <span className="nav-icon" aria-hidden="true"><CricketBallIcon size={14} /></span>
                  Bowlers
                </a>
              </li>
              <li>
                <a href="#model-rankings" className="nav-link nav-model-rankings">
                  <span className="nav-icon" aria-hidden="true"><SlidersIcon size={14} /></span>
                  Model Rankings
                </a>
              </li>
              <li>
                <a href="#methodology" className="nav-link nav-methodology">
                  <span className="nav-icon" aria-hidden="true"><MethodologyIcon size={14} /></span>
                  Methodology
                </a>
              </li>
              <li>
                <a
                  href="/portraits/contact_sheet.html"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="nav-link nav-sheet"
                  title="View all 19 official player cutouts contact sheet"
                >
                  <span className="nav-icon" aria-hidden="true"><PhotoIcon size={14} /></span>
                  Portraits Sheet ↗
                </a>
              </li>
            </ul>
          </nav>
        </div>
      </header>
    </>
  );
};
