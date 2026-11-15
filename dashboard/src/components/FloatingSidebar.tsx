import React, { useState, useEffect } from "react";
import {
  RajasthanRoyalsLogo,
  BatIcon,
  CricketBallIcon,
  SlidersIcon,
  MethodologyIcon,
  PhotoIcon,
} from "./Icons";

export const FloatingSidebar: React.FC = () => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [activeSection, setActiveSection] = useState<string>("batters");

  useEffect(() => {
    const updatePositionAndSection = () => {
      const scrollY = window.scrollY;
      setIsScrolled(scrollY > 120);

      // Dynamically measure sticky command bar bottom to prevent ANY overlap across all screen widths & wrapping states
      const stickyBar = document.querySelector(".sticky-rank-bar");
      if (stickyBar) {
        const rect = stickyBar.getBoundingClientRect();
        if (rect.bottom > 0) {
          const safeTop = Math.max(185, Math.round(rect.bottom + 18));
          document.documentElement.style.setProperty("--floating-sidebar-top", `${safeTop}px`);
        } else {
          document.documentElement.style.setProperty("--floating-sidebar-top", "185px");
        }
      } else {
        document.documentElement.style.setProperty("--floating-sidebar-top", "185px");
      }

      const methodology = document.getElementById("methodology");
      const modelRankings = document.getElementById("model-rankings");
      const bowlers = document.getElementById("bowlers");
      const batters = document.getElementById("batters");

      if (methodology && scrollY >= methodology.offsetTop - 220) {
        setActiveSection("methodology");
      } else if (modelRankings && scrollY >= modelRankings.offsetTop - 220) {
        setActiveSection("model-rankings");
      } else if (bowlers && scrollY >= bowlers.offsetTop - 220) {
        setActiveSection("bowlers");
      } else if (batters) {
        setActiveSection("batters");
      }
    };

    updatePositionAndSection();
    window.addEventListener("scroll", updatePositionAndSection, { passive: true });
    window.addEventListener("resize", updatePositionAndSection, { passive: true });
    return () => {
      window.removeEventListener("scroll", updatePositionAndSection);
      window.removeEventListener("resize", updatePositionAndSection);
    };
  }, []);

  const navItems = [
    {
      id: "batters",
      href: "#batters",
      tooltip: "Batters (10 picks)",
      icon: <BatIcon size={20} />,
    },
    {
      id: "bowlers",
      href: "#bowlers",
      tooltip: "Bowlers (10 picks)",
      icon: <CricketBallIcon size={20} />,
    },
    {
      id: "model-rankings",
      href: "#model-rankings",
      tooltip: "Model Rankings (248 candidates)",
      icon: <SlidersIcon size={20} />,
    },
    {
      id: "methodology",
      href: "#methodology",
      tooltip: "Methodology (7 chapters)",
      icon: <MethodologyIcon size={20} />,
    },
  ];

  return (
    <aside
      id="floating-sidebar"
      className={`floating-sidebar ${isScrolled ? "is-visible" : "is-hidden"}`}
      aria-label="Rajasthan Royals Quick Navigation"
    >
      <div className="floating-sidebar-inner">
        {/* Official Rajasthan Royals Logo */}
        <div className="floating-sidebar-brand">
          <a
            href="#batters"
            className="floating-brand-link"
            title="Rajasthan Royals · Official Crest · Back to Top"
            aria-label="Rajasthan Royals · Official Crest · Back to Top"
          >
            <RajasthanRoyalsLogo size={34} className="sidebar-rr-logo-img" />
          </a>
        </div>

        <div className="sidebar-divider" aria-hidden="true" />

        {/* Navigation Options with Proper SVGs */}
        <nav className="floating-sidebar-nav" aria-label="Quick Section Navigation">
          <ul className="floating-nav-list">
            {navItems.map((item) => {
              const isActive = activeSection === item.id;
              return (
                <li key={item.id} className="floating-nav-item">
                  <a
                    href={item.href}
                    className={`floating-nav-link ${isActive ? "is-active" : ""}`}
                    aria-label={item.tooltip}
                    title={item.tooltip}
                  >
                    <span className="floating-nav-icon" aria-hidden="true">
                      {item.icon}
                    </span>
                    {/* Hover flyout tooltip */}
                    <span className="floating-tooltip" role="tooltip">
                      {item.tooltip}
                    </span>
                  </a>
                </li>
              );
            })}

            <div className="sidebar-divider" aria-hidden="true" />

            {/* Portraits Contact Sheet */}
            <li className="floating-nav-item">
              <a
                href="/portraits/contact_sheet.html"
                target="_blank"
                rel="noopener noreferrer"
                className="floating-nav-link external-sheet-link"
                aria-label="Portraits Contact Sheet · 19 Cutouts (Opens in new tab)"
                title="Portraits Contact Sheet · 19 Cutouts ↗"
              >
                <span className="floating-nav-icon" aria-hidden="true">
                  <PhotoIcon size={20} />
                </span>
                <span className="floating-tooltip" role="tooltip">
                  Portraits Contact Sheet ↗
                </span>
              </a>
            </li>
          </ul>
        </nav>
      </div>
    </aside>
  );
};
