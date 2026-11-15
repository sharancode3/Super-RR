import puppeteer from 'puppeteer';
import fs from 'fs';
import path from 'path';

const VIEWPORTS = [
  { name: '1440', width: 1440, height: 900, label: 'Desktop initial viewport' },
  { name: '1024', width: 1024, height: 768, label: 'Small desktop / tablet landscape' },
  { name: '768', width: 768, height: 1024, label: 'Tablet portrait' },
  { name: '390', width: 390, height: 844, label: 'Mobile (iPhone 14/15)' },
  { name: '320', width: 320, height: 568, label: 'Constrained mobile (iPhone SE)' }
];

async function capture() {
  const outDir = path.resolve('scratch', 'screenshots_stage02');
  fs.mkdirSync(outDir, { recursive: true });

  console.log('Launching headless browser via Puppeteer...');
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();

  for (const vp of VIEWPORTS) {
    console.log(`Setting viewport ${vp.width}x${vp.height} (${vp.label})...`);
    await page.setViewport({ width: vp.width, height: vp.height, deviceScaleFactor: 2 });
    await page.goto('http://localhost:5173/', { waitUntil: 'networkidle0' });

    // Verify horizontal overflow
    const overflowCheck = await page.evaluate(() => {
      const scrollW = document.documentElement.scrollWidth;
      const innerW = window.innerWidth;
      return {
        scrollWidth: scrollW,
        innerWidth: innerW,
        hasOverflow: scrollW > innerW
      };
    });

    console.log(`  [${vp.name}px] scrollWidth=${overflowCheck.scrollWidth}, innerWidth=${overflowCheck.innerWidth}, hasOverflow=${overflowCheck.hasOverflow}`);

    // Check visibility of leaders at 1440
    if (vp.name === '1440') {
      const visibility = await page.evaluate(() => {
        const hTitle = document.getElementById('hero-title')?.getBoundingClientRect();
        const bCol = document.getElementById('batters')?.getBoundingClientRect();
        const bwCol = document.getElementById('bowlers')?.getBoundingClientRect();
        const vLead = document.querySelector('.board-batters .leader-card')?.getBoundingClientRect();
        const sLead = document.querySelector('.board-bowlers .leader-card')?.getBoundingClientRect();
        return {
          heroTitleTop: hTitle?.top,
          battersColTop: bCol?.top,
          bowlersColTop: bwCol?.top,
          vaibhavBottom: vLead?.bottom,
          sirajBottom: sLead?.bottom,
          windowHeight: window.innerHeight,
          bothLeadersInInitialView: (vLead?.bottom < 900) && (sLead?.bottom < 900)
        };
      });
      console.log('  1440 Viewport Geometry Check:', visibility);
    }

    // Viewport screenshot
    const vpPath = path.join(outDir, `viewport_${vp.name}x${vp.height}.png`);
    await page.screenshot({ path: vpPath, fullPage: false });
    console.log(`  Saved viewport screenshot -> ${vpPath}`);

    // Full page screenshot for 1440 and 390
    if (vp.name === '1440' || vp.name === '390') {
      const fpPath = path.join(outDir, `fullpage_${vp.name}.png`);
      await page.screenshot({ path: fpPath, fullPage: true });
      console.log(`  Saved fullpage screenshot -> ${fpPath}`);
    }
  }

  await browser.close();
  console.log('All responsive verification screenshots captured successfully!');
}

capture().catch((err) => {
  console.error('Error capturing screenshots:', err);
  process.exit(1);
});
