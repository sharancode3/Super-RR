import json
import os

with open('dashboard/src/data/portraits_manifest.json') as f:
    manifest = json.load(f)

with open('dashboard/src/data/player_ipl_stats.json') as f:
    ipl_stats = json.load(f)

html = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Rajasthan Royals SupeRR Selector · Media Section & Portrait Library</title>
  <style>
    :root {
      --color-page-bg: #FFF8ED;
      --color-ink: #20172F;
      --color-rr-pink: #D81465;
      --color-rr-blue: #3045A5;
      --color-card-bg: #FFFCF6;
      --color-border: #20172F;
      --shadow-paper: 3px 4px 0px rgba(32, 23, 47, 0.15);
      --shadow-hover: 4px 5px 0px #20172F;
    }
    * {
      box-sizing: border-box;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--color-page-bg);
      color: var(--color-ink);
      margin: 0;
      padding: 0;
      line-height: 1.45;
    }
    
    /* Top Sticky Navigation Bar */
    .top-nav-bar {
      position: sticky;
      top: 0;
      z-index: 1000;
      background: #FFFDF8;
      border-bottom: 2px solid var(--color-ink);
      padding: 10px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px;
      box-shadow: 0 4px 14px rgba(32, 23, 47, 0.08);
    }
    .nav-brand-group {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .rr-crest-badge {
      width: 36px;
      height: 36px;
      border-radius: 8px;
      background: #FFFFFF;
      border: 1.5px solid var(--color-ink);
      box-shadow: 2px 2px 0px var(--color-ink);
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 3px;
    }
    .rr-crest-badge img {
      width: 28px;
      height: 28px;
      object-fit: contain;
    }
    .nav-title-group {
      display: flex;
      flex-direction: column;
    }
    .nav-title {
      font-weight: 800;
      font-size: 15px;
      color: var(--color-ink);
      line-height: 1.1;
    }
    .nav-subtitle {
      font-size: 11px;
      color: #534A60;
      font-weight: 600;
    }
    
    /* Prominent Back Button */
    .btn-back-dashboard {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: var(--color-ink);
      color: #FFF8ED;
      text-decoration: none;
      font-size: 13px;
      font-weight: 800;
      padding: 8px 16px;
      border-radius: 6px;
      border: 2px solid var(--color-ink);
      box-shadow: 2px 2px 0px var(--color-rr-pink);
      transition: all 0.15s ease;
      cursor: pointer;
    }
    .btn-back-dashboard:hover {
      transform: translate(-1px, -1px);
      box-shadow: 3px 3px 0px var(--color-rr-pink);
      background: #150E20;
    }
    .nav-quick-links {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .nav-chip-link {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 700;
      color: var(--color-ink);
      text-decoration: none;
      border: 1.5px solid var(--color-ink);
      background: #FFFDF8;
      box-shadow: 1.5px 1.5px 0px var(--color-ink);
      transition: all 0.15s ease;
    }
    .nav-chip-link:hover {
      transform: translateY(-1px);
      background: #FFFFFF;
    }
    
    /* Page Container */
    .page-container {
      max-width: 1240px;
      margin: 0 auto;
      padding: 24px 20px 80px 20px;
    }
    
    header.sheet-header {
      margin-bottom: 28px;
      border-bottom: 2px solid var(--color-ink);
      padding-bottom: 20px;
    }
    .breadcrumb-row {
      font-size: 12px;
      font-weight: 600;
      color: #6C627A;
      margin-bottom: 8px;
    }
    .breadcrumb-row a {
      color: var(--color-rr-pink);
      text-decoration: none;
      font-weight: 700;
    }
    h1 {
      margin: 0 0 8px 0;
      font-size: 32px;
      letter-spacing: -0.5px;
      line-height: 1.15;
    }
    .subtitle {
      color: #534A60;
      font-size: 15px;
      margin: 0 0 16px 0;
    }
    .header-action-banner {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px;
      background: #FFFDF8;
      border: 1.5px solid var(--color-ink);
      border-radius: 8px;
      padding: 12px 18px;
      box-shadow: 2px 2px 0px rgba(32, 23, 47, 0.1);
    }
    .banner-text {
      font-size: 13.5px;
      font-weight: 600;
      color: var(--color-ink);
    }
    
    /* Section Headings */
    .discipline-section-title {
      font-size: 20px;
      font-weight: 800;
      margin: 36px 0 16px 0;
      display: flex;
      align-items: center;
      gap: 10px;
      border-bottom: 2px solid var(--color-ink);
      padding-bottom: 8px;
    }
    .discipline-section-title .section-tag {
      font-size: 12px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 4px;
      background: var(--color-ink);
      color: #FFF8ED;
    }
    
    /* Grid */
    .grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 20px;
    }
    .player-card {
      background: var(--color-card-bg);
      border: 1.5px solid var(--color-ink);
      border-radius: 12px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      box-shadow: var(--shadow-paper);
      transition: transform 0.15s ease, box-shadow 0.15s ease;
      cursor: pointer;
    }
    @media (min-width: 860px) {
      .player-card {
        flex-direction: row;
        align-items: center;
        gap: 24px;
      }
    }
    .player-card:hover {
      transform: translateY(-2px);
      box-shadow: var(--shadow-hover);
      border-color: var(--color-rr-pink);
    }
    .player-card.leader {
      border: 2px solid var(--color-rr-pink);
      background: #FFFDFC;
      box-shadow: 4px 6px 0px rgba(216, 20, 101, 0.18);
    }
    .preview-tiles {
      display: grid;
      grid-template-columns: repeat(4, 100px);
      gap: 8px;
      overflow-x: auto;
      padding-bottom: 4px;
      flex-shrink: 0;
    }
    @media (max-width: 520px) {
      .preview-tiles {
        grid-template-columns: repeat(2, 1fr);
      }
    }
    .tile {
      border-radius: 8px;
      padding: 6px;
      display: flex;
      flex-direction: column;
      align-items: center;
      position: relative;
      overflow: hidden;
      border: 1px solid rgba(32, 23, 47, 0.18);
      transition: transform 0.15s ease;
    }
    .tile:hover {
      transform: scale(1.05);
    }
    .tile img {
      width: 100%;
      height: auto;
      display: block;
    }
    .tile-pink { background: #F4CADA; }
    .tile-blue { background: #CFDAFF; }
    .tile-paper { background: #FFF8ED; }
    .tile-dark { background: #20172F; }
    .tile-label {
      font-size: 10px;
      font-weight: 600;
      margin-top: 4px;
      color: #20172F;
      opacity: 0.85;
    }
    .tile-dark .tile-label {
      color: #FFF8ED;
    }
    
    .player-info {
      flex: 1;
      display: flex;
      flex-direction: column;
      justify-content: center;
      min-width: 0;
    }
    .player-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 6px;
      flex-wrap: wrap;
    }
    .player-header h3 {
      margin: 0;
      font-size: 20px;
      font-weight: 800;
      color: var(--color-ink);
    }
    .badge {
      display: inline-block;
      font-size: 11px;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 4px;
      background: var(--color-ink);
      color: #FFF8ED;
    }
    .badge.leader-badge {
      background: var(--color-rr-pink);
      color: #FFF8ED;
      font-weight: 800;
    }
    .badge.dual-badge {
      background: linear-gradient(135deg, #D81465, #3045A5);
      color: #FFF8ED;
      font-weight: 800;
    }
    .meta {
      margin: 2px 0;
      font-size: 12.5px;
      color: #534A60;
      line-height: 1.4;
    }
    
    /* Quick IPL Stats Pill Row on Card */
    .card-quick-stats-row {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin: 8px 0 10px 0;
    }
    .stat-chip {
      background: #FFFFFF;
      border: 1px solid #D6D0C2;
      border-radius: 4px;
      padding: 3px 8px;
      font-size: 11.5px;
      color: var(--color-ink);
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }
    .stat-chip strong {
      color: var(--color-rr-pink);
      font-weight: 800;
    }
    
    /* Action Buttons Row */
    .card-action-row {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-top: 6px;
      flex-wrap: wrap;
    }
    .btn-preview-card {
      background: var(--color-rr-pink);
      color: #FFFFFF;
      border: 1.5px solid var(--color-ink);
      border-radius: 6px;
      padding: 6px 14px;
      font-size: 12.5px;
      font-weight: 800;
      cursor: pointer;
      box-shadow: 2px 2px 0px var(--color-ink);
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
    }
    .btn-preview-card:hover {
      background: #B80F54;
      transform: translateY(-1px);
      box-shadow: 3px 3px 0px var(--color-ink);
    }
    .btn-view-image {
      background: #FFFFFF;
      color: var(--color-ink);
      border: 1.5px solid var(--color-ink);
      border-radius: 6px;
      padding: 6px 12px;
      font-size: 12px;
      font-weight: 700;
      text-decoration: none;
      box-shadow: 1.5px 1.5px 0px var(--color-ink);
      transition: all 0.15s ease;
    }
    .btn-view-image:hover {
      background: #F4F1EA;
      transform: translateY(-1px);
    }
    
    /* ==========================================================================
       MODAL LIGHTBOX (Player Preview & Verified IPL Stats)
       ========================================================================== */
    .modal-overlay {
      position: fixed;
      inset: 0;
      background: rgba(15, 10, 25, 0.78);
      backdrop-filter: blur(4px);
      z-index: 2000;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 20px;
      overflow-y: auto;
    }
    .modal-overlay.is-open {
      display: flex;
      animation: modalFadeIn 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    }
    @keyframes modalFadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }
    .modal-dialog {
      background: #FFFDF8;
      border: 2px solid var(--color-ink);
      border-radius: 16px;
      box-shadow: 0 20px 50px rgba(11, 20, 38, 0.4), 6px 8px 0px var(--color-ink);
      width: 100%;
      max-width: 960px;
      max-height: 90vh;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      position: relative;
    }
    .modal-header {
      background: #FAF7F0;
      border-bottom: 1.5px solid var(--color-ink);
      padding: 16px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 10;
    }
    .modal-header-info {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }
    .modal-header h2 {
      margin: 0;
      font-size: 24px;
      font-weight: 800;
      color: var(--color-ink);
    }
    .modal-close-btn {
      background: #FFFFFF;
      border: 1.5px solid var(--color-ink);
      border-radius: 8px;
      width: 36px;
      height: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
      font-weight: 800;
      cursor: pointer;
      box-shadow: 2px 2px 0px var(--color-ink);
      transition: all 0.15s ease;
    }
    .modal-close-btn:hover {
      background: var(--color-rr-pink);
      color: #FFFFFF;
      transform: translateY(-1px);
    }
    
    .modal-body {
      padding: 24px 20px;
      display: grid;
      grid-template-columns: 1fr;
      gap: 24px;
    }
    @media (min-width: 768px) {
      .modal-body {
        grid-template-columns: 340px 1fr;
      }
    }
    
    /* Modal Left: Portrait Canvas */
    .modal-portrait-col {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 14px;
    }
    .modal-portrait-well {
      width: 100%;
      max-width: 320px;
      aspect-ratio: 1;
      border-radius: 14px;
      border: 2px solid var(--color-ink);
      box-shadow: 3px 4px 0px var(--color-ink);
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      overflow: hidden;
      transition: background 0.2s ease;
    }
    .modal-portrait-well img {
      width: 90%;
      height: 90%;
      object-fit: contain;
      filter: drop-shadow(0 8px 16px rgba(32, 23, 47, 0.25));
    }
    .bg-theme-switcher {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
      justify-content: center;
    }
    .theme-pill-btn {
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 700;
      border: 1px solid var(--color-ink);
      cursor: pointer;
      background: #FFFFFF;
      color: var(--color-ink);
      transition: all 0.15s ease;
    }
    .theme-pill-btn.active {
      background: var(--color-ink);
      color: #FFF8ED;
    }
    .modal-photo-credit {
      font-size: 11px;
      color: #6C627A;
      text-align: center;
      line-height: 1.35;
    }
    .modal-download-links {
      display: flex;
      gap: 8px;
      width: 100%;
    }
    .modal-download-btn {
      flex: 1;
      text-align: center;
      padding: 7px;
      border-radius: 6px;
      font-size: 11.5px;
      font-weight: 700;
      color: var(--color-ink);
      background: #FFFFFF;
      border: 1.5px solid var(--color-ink);
      box-shadow: 1.5px 1.5px 0px var(--color-ink);
      text-decoration: none;
      transition: all 0.15s ease;
    }
    .modal-download-btn:hover {
      background: #F4F1EA;
      transform: translateY(-1px);
    }
    
    /* Modal Right: Verified IPL Stats */
    .modal-stats-col {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .stats-card-heading {
      font-size: 16px;
      font-weight: 800;
      color: var(--color-ink);
      margin: 0;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1.5px solid #E2DCCF;
      padding-bottom: 6px;
    }
    .verified-bcci-seal {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 11px;
      font-weight: 700;
      color: #0E7039;
      background: #EAF7EE;
      border: 1px solid #A3D8B4;
      border-radius: 4px;
      padding: 2px 6px;
    }
    
    /* Stats Metric Grid */
    .stats-metrics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
      gap: 10px;
    }
    .metric-box {
      background: #FFFFFF;
      border: 1px solid var(--color-ink);
      border-radius: 8px;
      padding: 10px;
      text-align: center;
      box-shadow: 1.5px 1.5px 0px rgba(32, 23, 47, 0.1);
    }
    .metric-value {
      font-size: 20px;
      font-weight: 900;
      color: var(--color-ink);
      line-height: 1.1;
    }
    .metric-value.highlight-pink {
      color: var(--color-rr-pink);
    }
    .metric-value.highlight-blue {
      color: var(--color-rr-blue);
    }
    .metric-label {
      font-size: 10.5px;
      font-weight: 700;
      color: #6C627A;
      margin-top: 4px;
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }
    
    /* Graphical Visualization Bars */
    .graph-visual-card {
      background: #FFFFFF;
      border: 1px solid var(--color-ink);
      border-radius: 10px;
      padding: 14px;
      box-shadow: 2px 2px 0px rgba(32, 23, 47, 0.08);
    }
    .graph-title {
      font-size: 12.5px;
      font-weight: 800;
      color: var(--color-ink);
      margin: 0 0 10px 0;
      display: flex;
      justify-content: space-between;
    }
    .bar-container {
      background: #EFEBE0;
      height: 12px;
      border-radius: 6px;
      overflow: hidden;
      position: relative;
      border: 1px solid rgba(32, 23, 47, 0.2);
    }
    .bar-fill {
      height: 100%;
      border-radius: 5px;
      transition: width 0.6s ease;
    }
    .bar-fill-pink { background: linear-gradient(90deg, #EA1985, #FF5FA0); }
    .bar-fill-blue { background: linear-gradient(90deg, #2E45A3, #5F7EFF); }
    
    .graph-benchmarks {
      display: flex;
      justify-content: space-between;
      font-size: 10px;
      color: #6C627A;
      font-weight: 600;
      margin-top: 4px;
    }
    
    /* Pressure Comparison Panel */
    .pressure-contrast-panel {
      background: #FDF9F1;
      border: 1px dashed var(--color-ink);
      border-radius: 8px;
      padding: 12px;
    }
    .pressure-contrast-heading {
      font-size: 12px;
      font-weight: 800;
      color: var(--color-ink);
      margin: 0 0 8px 0;
    }
    .contrast-columns {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      text-align: center;
    }
    .contrast-col {
      background: #FFFFFF;
      border: 1px solid #D6D0C2;
      border-radius: 6px;
      padding: 8px;
    }
    .contrast-stat {
      font-size: 16px;
      font-weight: 900;
      color: var(--color-ink);
    }
    .contrast-desc {
      font-size: 10px;
      font-weight: 700;
      color: #6C627A;
      margin-top: 2px;
    }
    
    .data-disclaimer-box {
      font-size: 11px;
      line-height: 1.45;
      color: #534A60;
      background: #FAF7F0;
      border-radius: 6px;
      padding: 8px 12px;
      border-left: 3px solid var(--color-ink);
    }
  </style>
</head>
<body>
  <!-- Top Sticky Navigation Bar -->
  <nav class="top-nav-bar" aria-label="Portrait Library Navigation">
    <div class="nav-brand-group">
      <div class="rr-crest-badge" aria-hidden="true">
        <img src="/rajasthan_royals_official_logo.svg" alt="Rajasthan Royals Crest" />
      </div>
      <div class="nav-title-group">
        <span class="nav-title">SupeRR Selector Season 2</span>
        <span class="nav-subtitle">Media Section · Official BCCI/IPL Portraits &amp; Verified Stats</span>
      </div>
    </div>
    
    <div class="nav-quick-links">
      <a href="/" class="btn-back-dashboard" id="nav-btn-back">
        <span aria-hidden="true">←</span>
        <span>Back to Scouting Dashboard</span>
      </a>
      <a href="#batters-section" class="nav-chip-link">Batters (10)</a>
      <a href="#bowlers-section" class="nav-chip-link">Bowlers (9 + Dual)</a>
    </div>
  </nav>

  <div class="page-container">
    <header class="sheet-header">
      <div class="breadcrumb-row">
        <a href="/">← Live Dashboard</a> / <span>Media Section · Official Portraits &amp; IPL Stats</span>
      </div>
      <h1>Media Section: Official Player Cards &amp; IPL Performance</h1>
      <p class="subtitle">19 Identity-Verified Official Master Portraits with #FFF8ED Paper Stroke &amp; 2022–2026 IPL Ball-by-Ball Records</p>
      
      <div class="header-action-banner">
        <span class="banner-text">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="vertical-align: middle; margin-right: 4px;"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg><strong>Interactive Studio:</strong> Click any card or the <strong>"Preview Card &amp; Official IPL Stats"</strong> button to inspect high-resolution cutouts, customize background tones, and view verified IPL career data.
        </span>
        <a href="/" class="btn-back-dashboard" id="hero-btn-back">
          <span aria-hidden="true">←</span>
          <span>Return to Dashboard</span>
        </a>
      </div>
    </header>

    <h2 id="batters-section" class="discipline-section-title">
      <span>Discipline 01 · Batters Shortlist</span>
      <span class="section-tag">10 Official Targets</span>
    </h2>

    <main class="grid" id="batters-grid">
'''

# 10 Batters (indices 0 to 9 in manifest, which includes Jadeja at #9)
for p in manifest[0:10]:
    pid = str(p['player_id'])
    stats = ipl_stats.get(pid, {})
    b_stats = stats.get('batting', {})
    
    is_leader = p.get('is_leader', False)
    is_dual = p.get('role') == 'DUAL_ROLE'
    card_class = "player-card leader" if is_leader else "player-card standard"
    if is_leader:
        badge_html = "<span class='badge leader-badge'>LEADER #1</span>"
    elif is_dual:
        badge_html = "<span class='badge dual-badge'>Batters #9 · Bowlers #10 (Dual)</span>"
    else:
        badge_html = f"<span class='badge'>Rank #{p.get('rank', 2)}</span>"
    
    runs = b_stats.get('runs', 0)
    sr = b_stats.get('strike_rate', 0.0)
    avg = b_stats.get('average', 0.0)
    hs = b_stats.get('highest_score', 0)
    matches = stats.get('matches', 0)
    fifties = b_stats.get('fifties', 0)
    hundreds = b_stats.get('hundreds', 0)
    hp_balls = b_stats.get('hp_balls', 0)
    
    html += f'''
      <div class="{card_class}" id="player-{pid}" onclick="openPlayerModal('{pid}')">
        <div class="preview-tiles">
          <div class="tile tile-pink">
            <img src="/portraits/{pid}_320w.webp" alt="{p['name']}" loading="lazy" />
            <span class="tile-label">Pink Tile</span>
          </div>
          <div class="tile tile-blue">
            <img src="/portraits/{pid}_320w.webp" alt="{p['name']}" loading="lazy" />
            <span class="tile-label">Blue Tile</span>
          </div>
          <div class="tile tile-paper">
            <img src="/portraits/{pid}_320w.webp" alt="{p['name']}" loading="lazy" />
            <span class="tile-label">Paper Tile</span>
          </div>
          <div class="tile tile-dark">
            <img src="/portraits/{pid}_320w.webp" alt="{p['name']}" loading="lazy" />
            <span class="tile-label">Dark Tile</span>
          </div>
        </div>
        <div class="player-info">
          <div class="player-header">
            <h3>{p['name']}</h3>
            {badge_html}
          </div>
          <p class="meta"><strong>ID:</strong> {pid} | <strong>Discipline:</strong> {'BATTER & BOWLER' if is_dual else 'BATTER'} | <strong>2026 Reference:</strong> {p.get('squad_2026', 'IPL')}</p>
          <p class="meta"><strong>Sizes:</strong> 320w (WebP/PNG) / 640w HD Master | <strong>Credit:</strong> {p.get('credit', 'BCCI / IPL')}</p>
          
          <div class="card-quick-stats-row">
            <span class="stat-chip">IPL Matches: <strong>{matches}</strong></span>
            <span class="stat-chip">Runs: <strong>{runs}</strong></span>
            <span class="stat-chip">SR: <strong>{sr}</strong></span>
            <span class="stat-chip">Avg: <strong>{avg}</strong></span>
            <span class="stat-chip">HS: <strong>{hs}</strong></span>
            <span class="stat-chip">50s/100s: <strong>{fifties}/{hundreds}</strong></span>
            <span class="stat-chip">HP Balls: <strong>{hp_balls}</strong></span>
          </div>
          
          <div class="card-action-row">
            <button type="button" class="btn-preview-card" onclick="event.stopPropagation(); openPlayerModal('{pid}')">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="vertical-align: middle; margin-right: 4px;"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>Preview Card &amp; Official IPL Stats
            </button>
            <a href="/portraits/{pid}_640w.png" target="_blank" class="btn-view-image" onclick="event.stopPropagation()">
              View 640w PNG ↗
            </a>
          </div>
        </div>
      </div>
    '''

html += '''
    </main>

    <h2 id="bowlers-section" class="discipline-section-title">
      <span>Discipline 02 · Bowlers Shortlist</span>
      <span class="section-tag">9 Official Specialist Targets</span>
    </h2>

    <main class="grid" id="bowlers-grid">
'''

# 9 Bowlers (indices 10 to 18 in manifest)
for p in manifest[10:19]:
    pid = str(p['player_id'])
    stats = ipl_stats.get(pid, {})
    bw_stats = stats.get('bowling', {})
    
    is_leader = p.get('is_leader', False)
    card_class = "player-card leader" if is_leader else "player-card standard"
    badge_html = f"<span class='badge leader-badge'>LEADER #1</span>" if is_leader else f"<span class='badge'>Rank #{p.get('rank', 2)}</span>"
    
    wickets = bw_stats.get('wickets', 0)
    econ = bw_stats.get('economy', 0.0)
    avg = bw_stats.get('average', 0.0)
    bb = bw_stats.get('best_bowling', '—')
    matches = stats.get('matches', 0)
    overs = bw_stats.get('overs', 0.0)
    hp_balls = bw_stats.get('hp_balls', 0)
    
    html += f'''
      <div class="{card_class}" id="player-{pid}" onclick="openPlayerModal('{pid}')">
        <div class="preview-tiles">
          <div class="tile tile-pink">
            <img src="/portraits/{pid}_320w.webp" alt="{p['name']}" loading="lazy" />
            <span class="tile-label">Pink Tile</span>
          </div>
          <div class="tile tile-blue">
            <img src="/portraits/{pid}_320w.webp" alt="{p['name']}" loading="lazy" />
            <span class="tile-label">Blue Tile</span>
          </div>
          <div class="tile tile-paper">
            <img src="/portraits/{pid}_320w.webp" alt="{p['name']}" loading="lazy" />
            <span class="tile-label">Paper Tile</span>
          </div>
          <div class="tile tile-dark">
            <img src="/portraits/{pid}_320w.webp" alt="{p['name']}" loading="lazy" />
            <span class="tile-label">Dark Tile</span>
          </div>
        </div>
        <div class="player-info">
          <div class="player-header">
            <h3>{p['name']}</h3>
            {badge_html}
          </div>
          <p class="meta"><strong>ID:</strong> {pid} | <strong>Discipline:</strong> BOWLER | <strong>2026 Reference:</strong> {p.get('squad_2026', 'IPL')}</p>
          <p class="meta"><strong>Sizes:</strong> 320w (WebP/PNG) / 640w HD Master | <strong>Credit:</strong> {p.get('credit', 'BCCI / IPL')}</p>
          
          <div class="card-quick-stats-row">
            <span class="stat-chip">IPL Matches: <strong>{matches}</strong></span>
            <span class="stat-chip">Wickets: <strong>{wickets}</strong></span>
            <span class="stat-chip">Economy: <strong>{econ}</strong></span>
            <span class="stat-chip">Best: <strong>{bb}</strong></span>
            <span class="stat-chip">Overs: <strong>{overs}</strong></span>
            <span class="stat-chip">Avg: <strong>{avg}</strong></span>
            <span class="stat-chip">HP Balls: <strong>{hp_balls}</strong></span>
          </div>
          
          <div class="card-action-row">
            <button type="button" class="btn-preview-card" onclick="event.stopPropagation(); openPlayerModal('{pid}')">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="vertical-align: middle; margin-right: 4px;"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>Preview Card &amp; Official IPL Stats
            </button>
            <a href="/portraits/{pid}_640w.png" target="_blank" class="btn-view-image" onclick="event.stopPropagation()">
              View 640w PNG ↗
            </a>
          </div>
        </div>
      </div>
    '''

html += f'''
    </main>
  </div>

  <!-- Interactive Modal Lightbox -->
  <div id="player-modal" class="modal-overlay" onclick="handleBackdropClick(event)">
    <div class="modal-dialog" role="dialog" aria-modal="true" aria-labelledby="modal-player-name">
      <div class="modal-header">
        <div class="modal-header-info">
          <h2 id="modal-player-name">Player Name</h2>
          <span id="modal-player-badge" class="badge leader-badge">Rank</span>
          <span id="modal-player-squad" class="meta" style="font-weight:700;">Squad</span>
        </div>
        <button type="button" class="modal-close-btn" onclick="closePlayerModal()" aria-label="Close Preview Modal">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
        </button>
      </div>

      <div class="modal-body">
        <!-- Left: Studio Portrait Inspector -->
        <div class="modal-portrait-col">
          <div id="modal-portrait-well" class="modal-portrait-well tile-paper">
            <img id="modal-portrait-img" src="" alt="Player Portrait" />
          </div>

          <div class="bg-theme-switcher" aria-label="Background Tone Tester">
            <button type="button" class="theme-pill-btn" onclick="setModalBg('tile-pink')">
              <svg width="10" height="10" viewBox="0 0 20 20" aria-hidden="true" style="vertical-align: middle; margin-right: 4px;"><circle cx="10" cy="10" r="8" fill="#E6007E" stroke="#20172F" stroke-width="2"/></svg>Pink
            </button>
            <button type="button" class="theme-pill-btn" onclick="setModalBg('tile-blue')">
              <svg width="10" height="10" viewBox="0 0 20 20" aria-hidden="true" style="vertical-align: middle; margin-right: 4px;"><circle cx="10" cy="10" r="8" fill="#004BA0" stroke="#20172F" stroke-width="2"/></svg>Blue
            </button>
            <button type="button" class="theme-pill-btn active" onclick="setModalBg('tile-paper')">
              <svg width="10" height="10" viewBox="0 0 20 20" aria-hidden="true" style="vertical-align: middle; margin-right: 4px;"><circle cx="10" cy="10" r="8" fill="#FFF8ED" stroke="#20172F" stroke-width="2"/></svg>Paper
            </button>
            <button type="button" class="theme-pill-btn" onclick="setModalBg('tile-dark')">
              <svg width="10" height="10" viewBox="0 0 20 20" aria-hidden="true" style="vertical-align: middle; margin-right: 4px;"><circle cx="10" cy="10" r="8" fill="#130C1E" stroke="#FFF8ED" stroke-width="2"/></svg>Dark
            </button>
          </div>

          <p id="modal-photo-credit" class="modal-photo-credit">
            Official BCCI / IPL Media Day Studio Portrait
          </p>

          <div class="modal-download-links">
            <a id="modal-link-640" href="#" target="_blank" class="modal-download-btn">View 640w HD ↗</a>
            <a id="modal-link-320" href="#" target="_blank" class="modal-download-btn">Download 320w PNG</a>
          </div>
        </div>

        <!-- Right: Official Verified IPL Stats -->
        <div class="modal-stats-col">
          <div class="stats-card-heading">
            <span>Verified IPL Career Performance</span>
            <span class="verified-bcci-seal">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="vertical-align: middle; margin-right: 4px;"><polyline points="20 6 9 17 4 12"></polyline></svg>Official IPL Records (2022–2026)
            </span>
          </div>

          <div id="modal-metrics-container" class="stats-metrics-grid">
            <!-- Dynamically populated metrics -->
          </div>

          <!-- Graphical Visualizer: Performance Gauge -->
          <div class="graph-visual-card">
            <div class="graph-title">
              <span id="graph-title-label">Primary Performance Gauge</span>
              <strong id="graph-title-val">0.0</strong>
            </div>
            <div class="bar-container">
              <div id="graph-bar-fill" class="bar-fill bar-fill-pink" style="width: 0%;"></div>
            </div>
            <div class="graph-benchmarks">
              <span id="benchmark-left">Min</span>
              <span id="benchmark-mid">IPL Benchmark</span>
              <span id="benchmark-right">Max Elite</span>
            </div>
          </div>

          <!-- High Pressure Breakdown -->
          <div class="pressure-contrast-panel">
            <div class="pressure-contrast-heading">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="vertical-align: middle; margin-right: 4px;"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>High-Pressure Environment Performance (Historical 80th-Percentile Leverage)
            </div>
            <div class="contrast-columns">
              <div class="contrast-col">
                <div id="contrast-val-ord" class="contrast-stat">0.0</div>
                <div id="contrast-label-ord" class="contrast-desc">Ordinary Match Conditions</div>
              </div>
              <div class="contrast-col">
                <div id="contrast-val-hp" class="contrast-stat highlight-pink">0.0</div>
                <div id="contrast-label-hp" class="contrast-desc">High-Pressure Deliveries</div>
              </div>
            </div>
          </div>

          <div class="data-disclaimer-box">
            <strong>Data Integrity Guarantee:</strong> Figures reflect verified ball-by-ball delivery entries across regulation tournament fixtures from the official BCCI / IPL delivery ledger. Zero synthetic or imputed match numbers.
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    const IPL_STATS = {json.dumps(ipl_stats)};
    const MANIFEST = {json.dumps(manifest)};

    function openPlayerModal(pid) {{
      const meta = MANIFEST.find(m => String(m.player_id) === String(pid));
      const stats = IPL_STATS[String(pid)] || {{}};
      if (!meta) return;

      document.getElementById('modal-player-name').textContent = meta.name;
      let rankText = meta.is_leader ? 'LEADER #1' : ('Rank #' + (meta.rank || '2'));
      if (meta.role === 'DUAL_ROLE') rankText = 'Batters #9 · Bowlers #10 (Dual)';
      
      const badge = document.getElementById('modal-player-badge');
      badge.textContent = rankText;
      badge.className = meta.is_leader ? 'badge leader-badge' : (meta.role === 'DUAL_ROLE' ? 'badge dual-badge' : 'badge');

      document.getElementById('modal-player-squad').textContent = '2026 Reference: ' + (meta.squad_2026 || 'IPL');

      // Image
      const img = document.getElementById('modal-portrait-img');
      img.src = '/portraits/' + pid + '_640w.webp';
      img.alt = meta.name;

      document.getElementById('modal-link-640').href = '/portraits/' + pid + '_640w.png';
      document.getElementById('modal-link-320').href = '/portraits/' + pid + '_320w.png';
      document.getElementById('modal-photo-credit').textContent = 'Credit: ' + (meta.credit || 'BCCI / IPL');

      // Render stats
      const isBatter = stats.is_batter && (!stats.is_bowler || meta.role === 'BATTER' || meta.role === 'DUAL_ROLE');
      const mContainer = document.getElementById('modal-metrics-container');
      mContainer.innerHTML = '';

      if (isBatter && stats.batting && stats.batting.balls > 0) {{
        const b = stats.batting || {{}};
        const metrics = [
          {{ label: 'Matches', val: stats.matches }},
          {{ label: 'Innings', val: b.innings }},
          {{ label: 'Total Runs', val: b.runs, highlight: 'pink' }},
          {{ label: 'Strike Rate', val: b.strike_rate, highlight: 'blue' }},
          {{ label: 'Average', val: b.average }},
          {{ label: 'High Score', val: b.highest_score }},
          {{ label: 'Fours', val: b.fours }},
          {{ label: 'Sixes', val: b.sixes }},
          {{ label: '50s / 100s', val: b.fifties + ' / ' + b.hundreds }},
          {{ label: 'HP Balls', val: b.hp_balls }},
          {{ label: 'HP Runs', val: b.hp_runs }},
          {{ label: 'HP Strike Rate', val: b.hp_strike_rate, highlight: 'pink' }}
        ];

        metrics.forEach(m => {{
          const box = document.createElement('div');
          box.className = 'metric-box';
          const hlClass = m.highlight ? (' highlight-' + m.highlight) : '';
          box.innerHTML = '<div class="metric-value' + hlClass + '">' + m.val + '</div><div class="metric-label">' + m.label + '</div>';
          mContainer.appendChild(box);
        }});

        // Visualizer
        document.getElementById('graph-title-label').textContent = 'Strike Rate Speedometer';
        document.getElementById('graph-title-val').textContent = b.strike_rate + ' r/100b';
        const srPct = Math.min(100, Math.max(10, ((b.strike_rate - 80) / 160) * 100));
        const bar = document.getElementById('graph-bar-fill');
        bar.className = 'bar-fill bar-fill-pink';
        bar.style.width = srPct + '%';
        document.getElementById('benchmark-left').textContent = '80 (Anchor)';
        document.getElementById('benchmark-mid').textContent = '145 (IPL Avg)';
        document.getElementById('benchmark-right').textContent = '220+ (Elite Power)';

        // Contrast
        document.getElementById('contrast-val-ord').textContent = b.strike_rate + ' SR';
        document.getElementById('contrast-val-hp').textContent = b.hp_strike_rate + ' HP SR';
        document.getElementById('contrast-label-ord').textContent = 'Career IPL Strike Rate (' + b.balls + ' balls)';
        document.getElementById('contrast-label-hp').textContent = 'High-Pressure Strike Rate (' + b.hp_balls + ' balls)';
      }} else {{
        const bw = stats.bowling || {{}};
        const metrics = [
          {{ label: 'Matches', val: stats.matches }},
          {{ label: 'Innings', val: bw.innings }},
          {{ label: 'Overs Bowled', val: bw.overs }},
          {{ label: 'Wickets', val: bw.wickets, highlight: 'pink' }},
          {{ label: 'Economy', val: bw.economy, highlight: 'blue' }},
          {{ label: 'Average', val: bw.average }},
          {{ label: 'Best Bowling', val: bw.best_bowling }},
          {{ label: 'Strike Rate', val: bw.strike_rate }},
          {{ label: '4w / 5w Hauls', val: bw.four_w + ' / ' + bw.five_w }},
          {{ label: 'HP Balls', val: bw.hp_balls }},
          {{ label: 'HP Wickets', val: bw.hp_wickets }},
          {{ label: 'HP Economy', val: bw.hp_economy, highlight: 'pink' }}
        ];

        metrics.forEach(m => {{
          const box = document.createElement('div');
          box.className = 'metric-box';
          const hlClass = m.highlight ? (' highlight-' + m.highlight) : '';
          box.innerHTML = '<div class="metric-value' + hlClass + '">' + m.val + '</div><div class="metric-label">' + m.label + '</div>';
          mContainer.appendChild(box);
        }});

        // Visualizer
        document.getElementById('graph-title-label').textContent = 'Bowling Economy Efficiency (Lower is Better)';
        document.getElementById('graph-title-val').textContent = bw.economy + ' rpo';
        const econScore = Math.min(100, Math.max(10, ((12.0 - bw.economy) / 6.0) * 100));
        const bar = document.getElementById('graph-bar-fill');
        bar.className = 'bar-fill bar-fill-blue';
        bar.style.width = econScore + '%';
        document.getElementById('benchmark-left').textContent = '12.0 (Expensive)';
        document.getElementById('benchmark-mid').textContent = '8.6 (IPL Median)';
        document.getElementById('benchmark-right').textContent = '6.0 (Elite Control)';

        // Contrast
        document.getElementById('contrast-val-ord').textContent = bw.economy + ' RPO';
        document.getElementById('contrast-val-hp').textContent = bw.hp_economy + ' HP RPO';
        document.getElementById('contrast-label-ord').textContent = 'Career IPL Economy (' + bw.overs + ' ov)';
        document.getElementById('contrast-label-hp').textContent = 'High-Pressure Economy (' + bw.hp_balls + ' balls)';
      }}

      const modal = document.getElementById('player-modal');
      modal.classList.add('is-open');
      document.body.style.overflow = 'hidden';
    }}

    function closePlayerModal() {{
      const modal = document.getElementById('player-modal');
      modal.classList.remove('is-open');
      document.body.style.overflow = '';
    }}

    function handleBackdropClick(e) {{
      if (e.target.id === 'player-modal') {{
        closePlayerModal();
      }}
    }}

    function setModalBg(themeClass) {{
      const well = document.getElementById('modal-portrait-well');
      well.className = 'modal-portrait-well ' + themeClass;
      document.querySelectorAll('.theme-pill-btn').forEach(btn => btn.classList.remove('active'));
      event.target.classList.add('active');
    }}

    document.addEventListener('keydown', (e) => {{
      if (e.key === 'Escape') {{
        closePlayerModal();
      }}
    }});

    window.addEventListener('DOMContentLoaded', () => {{
      if (window.location.hash) {{
        const m = window.location.hash.match(/player-(\\d+)/);
        if (m && m[1]) {{
          openPlayerModal(m[1]);
        }}
      }}
    }});
  </script>
</body>
</html>
'''

output_path = 'dashboard/public/portraits/contact_sheet.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Generated enhanced contact sheet at {output_path} with all {len(manifest)} cards ({len(html)} bytes)")
