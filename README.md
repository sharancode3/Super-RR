# Super-RR Selector Season 2: Rajasthan Royals IPL 2027 Auction & Scouting Intelligence Dashboard

[![Vercel Deployment](https://img.shields.io/badge/Deploy-Vercel-black?style=flat&logo=vercel)](https://vercel.com)
[![React 19](https://img.shields.io/badge/React-19.1.0-blue?style=flat&logo=react)](https://react.dev/)
[![Vite 6](https://img.shields.io/badge/Vite-6.2.0-646CFF?style=flat&logo=vite)](https://vitejs.dev/)
[![TypeScript 5.8](https://img.shields.io/badge/TypeScript-5.8.2-3178C6?style=flat&logo=typescript)](https://www.typescriptlang.org/)
[![IPL 2027 Ready](https://img.shields.io/badge/IPL-2027_Ready-EC1C24?style=flat)](https://www.iplt20.com/)

A high-performance scouting intelligence dashboard engineered for the **Rajasthan Royals (RR)** recruitment team ahead of the **IPL 2027 Auction**. Built on pre-ball win-probability leverage modeling ($L_t$), Bayesian shrinkage, forward-chaining backtests, and 1,000-resample cluster-bootstrap stability bounds.

---

## 👑 Features & Architecture

- **Official Rajasthan Royals Visual Identity**: Authentic RR Crest SVG with `#FFFFFF` crisp framing, RR Royal Pink (`#E0006C`), and Midnight Navy (`#0C2340`) aesthetics.
- **Zero-Emoji Architecture**: Strictly zero emojis across the entire codebase; 100% powered by crisp, scalable, high-contrast inline SVGs.
- **In-App Interactive Player Preview Modal**:
  - Master high-resolution player portraits with dynamic 4-tone studio canvas background switcher (Pink `#FDE8EF`, Blue `#EBF2FF`, Paper `#FFFDF8`, Dark `#0C1829`).
  - Verified 2022–2026 IPL career numbers, strike rate speedometer gauge, bowling economy efficiency gauge, and High-Pressure vs Career performance comparisons.
  - Interactive discipline switcher for dual-role stars (e.g. Ravindra Jadeja `#152` toggles between Batting Rank #9 and Bowling Rank #10).
- **Verified 20-Player Shortlist**:
  - **10 Batters**: Vaibhav Sooryavanshi (#1), Josh Inglis (#2), Sameer Rizvi (#3), Oliver Davies Connolly (#4), Donovan Ferreira (#5), Abishek Porel (#6), Riyan Parag (#7), Shashank Singh (#8), Ravindra Jadeja (#9), Venkatesh Iyer (#10).
  - **10 Bowlers**: Jasprit Bumrah (Benchmark Leader), Mohammed Siraj (#1), Noor Ahmad (#2), Josh Hazlewood (#3), Prasidh Krishna (#4), Matheesha Pathirana (#5), Gerald Coetzee (#6), Kuldeep Yadav (#7), Sandeep Sharma (#8), T Natarajan (#9), Ravindra Jadeja (#10).
- **Rigorous Mathematical Methodology**:
  - Live KaTeX rendered formulations for Pre-Ball Leverage $L_t = \sum_o p_o |q_o - \bar{q}|$, Bayesian Empirical Shrinkage, and Historical Cutoff ($L_t \ge 0.0254$ for Tier-1 IPL Chase).
  - Reproducible case study: IPL 2026 Match 54 RCB vs MI (pre-ball leverage `0.335582`, cutoff `0.025364`).
- **Device Screen Auto-Stabilization**:
  - Responsive layouts calibrated for Mobile (390px), Tablet (768px), Laptop (1100px), and Desktop (1440px+).
  - Body scroll-locking, escape key listeners, and accessibility standards (`role="dialog"`, `aria-modal="true"`).

---

## 🚀 Instant Deployment on Vercel

This repository is pre-configured for **turnkey deployment on Vercel** with zero backend infrastructure required:

### Option A: 1-Click Import via Vercel Dashboard
1. Go to [Vercel](https://vercel.com/) and click **"Add New..." > "Project"**.
2. Select and import the repository: `https://github.com/sharancode3/Super-RR.git`.
3. Vercel automatically detects the root [`vercel.json`](./vercel.json):
   - **Framework Preset**: Vite
   - **Build Command**: `npm --prefix dashboard run build`
   - **Output Directory**: `dashboard/dist`
4. Click **Deploy**. Your dashboard will be live within ~40 seconds!

### Option B: Deploy from Subdirectory
If configuring Vercel with **Root Directory** set to `dashboard`:
- Vercel uses [`dashboard/vercel.json`](./dashboard/vercel.json):
  - **Build Command**: `npm run build`
  - **Output Directory**: `dist`

---

## 💻 Local Development

### Prerequisites
- Node.js 18+ or 20+
- npm 9+

### Setup
```bash
# Clone the repository
git clone https://github.com/sharancode3/Super-RR.git
cd Super-RR

# Install dashboard dependencies
npm --prefix dashboard install

# Start local development server
npm run dev

# Or run from dashboard directory directly
cd dashboard
npm run dev
```

### Build & Preview
```bash
# Production build
npm run build

# Preview production build locally
npm run preview
```

### End-to-End Test Suite
Run the automated verification suite (verifies zero emojis, in-app modal mechanics, multi-screen responsive bounds, KaTeX formulas, and score parity):
```bash
node dashboard/scripts/verify_in_app_modal_and_zero_emojis.cjs
node dashboard/scripts/verify_evidence_corrections.cjs
node dashboard/scripts/verify_timeline_media_floating.cjs
```

---

## 📁 Repository Structure

```
.
├── dashboard/                  # React + Vite Frontend Application
│   ├── public/                 # Static assets, fonts, official logos
│   │   ├── portraits/          # 640w master portraits & contact sheet
│   │   ├── rajasthan_royals_official_logo.svg  # Official RR Crest
│   │   └── favicon.svg         # Official RR Crest Favicon
│   ├── src/                    # Application source code
│   │   ├── components/         # React components (Modal, Cards, Boards, Header)
│   │   ├── data/               # Verified ranking records, metrics, manifests
│   │   ├── App.tsx             # Root application orchestrator
│   │   └── App.css             # High-contrast CSS & responsive rules
│   ├── scripts/                # Verification test suites & data generators
│   └── vercel.json             # Subdirectory Vercel deployment configuration
├── rr_pressure/                # Python win-probability leverage & scoring models
├── tests/                      # Python pytest regression suites
├── package.json                # Root npm workspace configuration
├── vercel.json                 # Root Vercel deployment configuration
├── .gitignore                  # Optimized Git filter excluding >100MB datasets
└── README.md                   # Project documentation
```

---

## 🛡️ License & Trademarks

All Rajasthan Royals logos, team crests, and BCCI/IPL statistical references belong to their respective copyright holders. Developed for analytical evaluation and recruitment modeling.
