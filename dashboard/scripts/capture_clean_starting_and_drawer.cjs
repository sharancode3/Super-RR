const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle0' });

  const artifactDir = 'C:\\Users\\tms10\\.gemini\\antigravity\\brain\\58919bc3-f90c-4e68-8103-3c4969f79061';

  // 1. Capture Starting Screen at scrollY = 0
  await page.evaluate(() => window.scrollTo(0, 0));
  await new Promise(r => setTimeout(r, 400));
  const startPath = path.join(artifactDir, 'interim_dossier_starting_screen_fixed.png');
  await page.screenshot({ path: startPath, fullPage: false });
  console.log('Saved starting screen screenshot to:', startPath);

  // 2. Capture Dossier Section scrolled down
  await page.evaluate(() => {
    const el = document.querySelector('#batting-vaibhav-sooryavanshi');
    if (el) el.scrollIntoView({ behavior: 'instant', block: 'start' });
  });
  await new Promise(r => setTimeout(r, 400));
  const cardPath = path.join(artifactDir, 'interim_dossier_player_cards_unblocked.png');
  await page.screenshot({ path: cardPath, fullPage: false });
  console.log('Saved player cards screenshot to:', cardPath);

  // 3. Open Executive Drawer and Capture
  await page.evaluate(() => {
    const trigger = document.querySelector('.rr-floating-nav-trigger');
    if (trigger) trigger.click();
  });
  await new Promise(r => setTimeout(r, 400));
  const drawerPath = path.join(artifactDir, 'interim_dossier_executive_drawer_open.png');
  await page.screenshot({ path: drawerPath, fullPage: false });
  console.log('Saved executive drawer screenshot to:', drawerPath);

  await browser.close();
})();
