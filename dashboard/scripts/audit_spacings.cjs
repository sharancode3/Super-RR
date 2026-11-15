const puppeteer = require('../node_modules/puppeteer');
const fs = require('fs');
const path = require('path');

const ARTIFACT_DIR = path.resolve('C:/Users/tms10/.gemini/antigravity/brain/58919bc3-f90c-4e68-8103-3c4969f79061');
const BASE_URL = 'http://localhost:5173';

const VIEWPORTS = [
  { name: 'desktop_1440', width: 1440, height: 900 },
  { name: 'tablet_768', width: 768, height: 1024 },
  { name: 'mobile_390', width: 390, height: 844 },
  { name: 'compact_320', width: 320, height: 568 }
];

async function auditSpacings() {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();

  for (const vp of VIEWPORTS) {
    await page.setViewport({ width: vp.width, height: vp.height });
    await page.goto(BASE_URL, { waitUntil: 'networkidle0' });

    console.log(`\n=================== VIEWPORT: ${vp.name} (${vp.width}x${vp.height}) ===================`);

    const data = await page.evaluate(() => {
      const getMetrics = (sel) => {
        const el = document.querySelector(sel);
        if (!el) return null;
        const s = window.getComputedStyle(el);
        const r = el.getBoundingClientRect();
        return {
          padding: `${s.paddingTop} ${s.paddingRight} ${s.paddingBottom} ${s.paddingLeft}`,
          margin: `${s.marginTop} ${s.marginRight} ${s.marginBottom} ${s.marginLeft}`,
          gap: s.gap || 'none',
          height: Math.round(r.height),
          width: Math.round(r.width),
          top: Math.round(r.top),
          bottom: Math.round(r.bottom)
        };
      };

      // Check card internal elements
      const card = document.querySelector('.player-card');
      let cardInternals = null;
      if (card) {
        const well = card.querySelector('.player-visual-well');
        const img = card.querySelector('.player-portrait-img');
        const identity = card.querySelector('.rect-identity-col');
        const dataCol = card.querySelector('.rect-data-col');
        const metricsGrid = card.querySelector('.rect-metrics-grid');
        const fit = card.querySelector('.leader-fit-summary');
        const name = card.querySelector('.leader-name');
        
        cardInternals = {
          well: well ? { h: well.clientHeight, w: well.clientWidth } : null,
          img: img ? { h: img.clientHeight, w: img.clientWidth, natH: img.naturalHeight, natW: img.naturalWidth } : null,
          identity: identity ? { h: identity.clientHeight, w: identity.clientWidth } : null,
          dataCol: dataCol ? { h: dataCol.clientHeight, w: dataCol.clientWidth } : null,
          metricsGrid: metricsGrid ? { h: metricsGrid.clientHeight, w: metricsGrid.clientWidth } : null,
          name: name ? { h: name.clientHeight, fs: window.getComputedStyle(name).fontSize } : null,
          fit: fit ? { h: fit.clientHeight, fs: window.getComputedStyle(fit).fontSize } : null
        };
      }

      // Check vertical gaps between major landmarks
      const hero = document.querySelector('.hero-section')?.getBoundingClientRect();
      const commandBar = document.querySelector('.sticky-rank-bar')?.getBoundingClientRect();
      const batters = document.querySelector('#batters')?.getBoundingClientRect();
      const bowlers = document.querySelector('#bowlers')?.getBoundingClientRect();
      const modelRankings = document.querySelector('#model-rankings')?.getBoundingClientRect();
      const methodology = document.querySelector('#methodology')?.getBoundingClientRect();
      const footer = document.querySelector('.site-footer')?.getBoundingClientRect();

      const gaps = {
        heroToCommandBar: commandBar && hero ? commandBar.top - hero.bottom : null,
        commandBarToBatters: batters && commandBar ? batters.top - commandBar.bottom : null,
        battersToBowlers: bowlers && batters ? bowlers.top - batters.bottom : null,
        bowlersToModel: modelRankings && bowlers ? modelRankings.top - bowlers.bottom : null,
        modelToMethodology: methodology && modelRankings ? methodology.top - modelRankings.bottom : null,
        methodologyToFooter: footer && methodology ? footer.top - methodology.bottom : null
      };

      return {
        cardInternals,
        gaps,
        hero: getMetrics('.hero-section'),
        commandBar: getMetrics('.sticky-rank-bar'),
        firstCard: getMetrics('.player-card'),
        cardBody: getMetrics('.rect-card-body'),
        modelRankings: getMetrics('#model-rankings'),
        methodology: getMetrics('#methodology')
      };
    });

    console.log('Landmark Gaps:', JSON.stringify(data.gaps, null, 2));
    console.log('Card Internals:', JSON.stringify(data.cardInternals, null, 2));
    console.log('Hero Metrics:', JSON.stringify(data.hero, null, 2));
    console.log('Command Bar Metrics:', JSON.stringify(data.commandBar, null, 2));
    console.log('First Card Metrics:', JSON.stringify(data.firstCard, null, 2));
    console.log('Card Body Metrics:', JSON.stringify(data.cardBody, null, 2));
  }

  await browser.close();
}

auditSpacings().catch(console.error);
