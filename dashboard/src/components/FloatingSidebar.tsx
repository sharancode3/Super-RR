import React, { useState, useEffect } from "react";
import {
  RajasthanRoyalsLogo,
  BatIcon,
  CricketBallIcon,
  SlidersIcon,
  MethodologyIcon,
  PhotoIcon,
  YouTubeIcon,
} from "./Icons";

interface FloatingSidebarProps {
  onOpenVideo?: () => void;
}

export const FloatingSidebar: React.FC<FloatingSidebarProps> = ({ onOpenVideo }) => {
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

      const media = document.getElementById("media");
      const methodology = document.getElementById("methodology");
      const modelRankings = document.getElementById("model-rankings");
      const bowlers = document.getElementById("bowlers");
      const batters = document.getElementById("batters");

      if (media && scrollY >= media.offsetTop - 220) {
        setActiveSection("media");
      } else if (methodology && scrollY >= methodology.offsetTop - 220) {
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

            {/* Media & Portraits Section */}
            <li className="floating-nav-item">
              <a
                href="#media"
                className={`floating-nav-link ${activeSection === "media" ? "is-active" : ""}`}
                aria-label="Media Section · Official Player Cards & IPL Stats"
                title="Media Section · 19 Official Cards"
              >
                <span className="floating-nav-icon" aria-hidden="true">
                  <PhotoIcon size={20} />
                </span>
                <span className="floating-tooltip" role="tooltip">
                  Media Section (19 Cards)
                </span>
              </a>
            </li>

            {onOpenVideo && (
              <>
                <div className="sidebar-divider" aria-hidden="true" />
                {/* Video Walkthrough Modal Trigger */}
                <li className="floating-nav-item">
                  <button
                    type="button"
                    onClick={onOpenVideo}
                    className="floating-nav-link floating-yt-btn"
                    aria-label="Watch Walkthrough Video (Popup)"
                    title="Watch Walkthrough Video (Popup)"
                  >
                    <span className="floating-nav-icon floating-yt-icon" aria-hidden="true">
                      <YouTubeIcon size={20} />
                    </span>
                    <span className="floating-tooltip" role="tooltip">
                      Watch Video (60s)
                    </span>
                  </button>
                </li>
              </>
            )}
          </ul>
        </nav>
      </div>
    </aside>
  );
};
