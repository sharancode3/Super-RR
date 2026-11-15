import React, { useState, useEffect } from "react";
import {
  BatIcon,
  TargetIcon,
  SlidersIcon,
  LayersIcon,
  PhotoIcon,
  MenuIcon,
  CloseIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from "./Icons";

interface SidebarProps {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isCollapsed,
  onToggleCollapse,
}) => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [activeSection, setActiveSection] = useState<string>("batters");

  // Track active anchor section on scroll
  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY;
      const methodology = document.getElementById("methodology");
      const modelRankings = document.getElementById("model-rankings");
      const bowlers = document.getElementById("bowlers");
      const batters = document.getElementById("batters");

      if (methodology && scrollY >= methodology.offsetTop - 200) {
        setActiveSection("methodology");
      } else if (modelRankings && scrollY >= modelRankings.offsetTop - 200) {
        setActiveSection("model-rankings");
      } else if (bowlers && scrollY >= bowlers.offsetTop - 200) {
        setActiveSection("bowlers");
      } else if (batters) {
        setActiveSection("batters");
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const navItems = [
    {
      id: "batters",
      href: "#batters",
      label: "Batters Shortlist",
      shortLabel: "Batters",
      icon: <BatIcon size={18} />,
      tag: "10 picks",
      badgeClass: "badge-batters",
    },
    {
      id: "bowlers",
      href: "#bowlers",
      label: "Bowlers Shortlist",
      shortLabel: "Bowlers",
      icon: <TargetIcon size={18} />,
      tag: "10 picks",
      badgeClass: "badge-bowlers",
    },
    {
      id: "model-rankings",
      href: "#model-rankings",
      label: "Model Rankings",
      shortLabel: "Model",
      icon: <SlidersIcon size={18} />,
      tag: "248 pool",
      badgeClass: "badge-model",
    },
    {
      id: "methodology",
      href: "#methodology",
      label: "Methodology",
      shortLabel: "Methods",
      icon: <LayersIcon size={18} />,
      tag: "7 chapters",
      badgeClass: "badge-method",
    },
  ];

  const handleLinkClick = () => {
    if (mobileOpen) {
      setMobileOpen(false);
    }
  };

  return (
    <>
      {/* Mobile Floating Menu Button (Visible on screens < 1024px) */}
      <button
        type="button"
        className="mobile-sidebar-toggle-btn"
        onClick={() => setMobileOpen(!mobileOpen)}
        aria-label={mobileOpen ? "Close navigation menu" : "Open navigation menu"}
        aria-expanded={mobileOpen}
        title="Toggle Rajasthan Royals Menu"
      >
        {mobileOpen ? <CloseIcon size={20} /> : <MenuIcon size={20} />}
        <span className="mobile-toggle-label">RR Menu</span>
      </button>

      {/* Mobile Backdrop Overlay */}
      {mobileOpen && (
        <div
          className="mobile-sidebar-backdrop"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Main Sidebar (Desktop Dock / Mobile Off-canvas Drawer) */}
      <aside
        id="site-sidebar"
        className={`site-sidebar ${isCollapsed ? "is-collapsed" : "is-expanded"} ${
          mobileOpen ? "mobile-drawer-open" : ""
        }`}
        aria-label="Rajasthan Royals Navigation Sidebar"
      >
        <div className="sidebar-inner">
          {/* Header & Branding */}
          <div className="sidebar-header">
            <a href="#batters" className="sidebar-brand" onClick={handleLinkClick}>
              <div className="sidebar-crest" aria-hidden="true">
                <span className="crest-rr">RR</span>
              </div>
              {!isCollapsed && (
                <div className="sidebar-titles">
                  <span className="sidebar-brand-title">SupeRR Selector</span>
                  <span className="sidebar-brand-sub">Rajasthan Royals · 2027</span>
                </div>
              )}
            </a>

            {/* Desktop Collapse / Expand Toggle Button */}
            <button
              type="button"
              className="desktop-collapse-btn"
              onClick={onToggleCollapse}
              aria-label={isCollapsed ? "Expand sidebar navigation" : "Collapse sidebar navigation"}
              title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              {isCollapsed ? <ChevronRightIcon size={16} /> : <ChevronLeftIcon size={16} />}
            </button>

            {/* Mobile Close Button inside drawer */}
            <button
              type="button"
              className="mobile-drawer-close-btn"
              onClick={() => setMobileOpen(false)}
              aria-label="Close navigation drawer"
            >
              <CloseIcon size={20} />
            </button>
          </div>

          {/* Primary Navigation List */}
          <nav className="sidebar-nav" aria-label="Main Navigation">
            <ul className="sidebar-nav-list">
              {navItems.map((item) => {
                const isActive = activeSection === item.id;
                return (
                  <li key={item.id} className="sidebar-nav-item">
                    <a
                      href={item.href}
                      className={`sidebar-nav-link ${isActive ? "is-active" : ""}`}
                      onClick={handleLinkClick}
                      title={item.label}
                    >
                      <span className="sidebar-icon" aria-hidden="true">
                        {item.icon}
                      </span>
                      {!isCollapsed && (
                        <>
                          <span className="sidebar-link-text">{item.label}</span>
                          <span className={`sidebar-badge ${item.badgeClass}`}>{item.tag}</span>
                        </>
                      )}
                      {isCollapsed && isActive && (
                        <span className="collapsed-active-indicator" aria-hidden="true" />
                      )}
                    </a>
                  </li>
                );
              })}

              {/* In-App Media Section */}
              <li className="sidebar-nav-item">
                <a
                  href="#media"
                  className="sidebar-nav-link"
                  title="View all 19 official player cutouts and cards"
                  onClick={handleLinkClick}
                >
                  <span className="sidebar-icon" aria-hidden="true">
                    <PhotoIcon size={18} />
                  </span>
                  {!isCollapsed && (
                    <>
                      <span className="sidebar-link-text">Media Section</span>
                      <span className="sidebar-badge">19 cards</span>
                    </>
                  )}
                </a>
              </li>
            </ul>
          </nav>

          {/* Footer Metadata */}
          {!isCollapsed && (
            <div className="sidebar-footer">
              <div className="sidebar-status-card">
                <div className="status-dot-pulse" aria-hidden="true" />
                <div className="status-text">
                  <span className="status-title">Decision Snapshot</span>
                  <span className="status-desc">IPL 2027 Strategy · 160 Fits</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  );
};
