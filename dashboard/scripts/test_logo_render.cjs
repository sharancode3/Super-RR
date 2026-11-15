const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  await page.setContent(`
    <!DOCTYPE html>
    <html>
      <body style="background: #FFF8ED; padding: 40px; display: flex; gap: 30px; align-items: center;">
        <div style="background: #0B1426; padding: 16px; border-radius: 12px; display: flex; align-items: center; gap: 12px;">
          <img src="http://localhost:5173/rajasthan_royals_official_logo.svg" width="40" height="40" style="object-fit: contain;" />
          <span style="color: white; font-family: sans-serif; font-weight: bold; font-size: 16px;">Rajasthan Royals Official Logo (Dark BG)</span>
        </div>
        <div style="background: #FFFFFF; border: 1px solid #20172F; padding: 16px; border-radius: 12px; display: flex; align-items: center; gap: 12px;">
          <img src="http://localhost:5173/rajasthan_royals_official_logo.svg" width="40" height="40" style="object-fit: contain;" />
          <span style="color: #20172F; font-family: sans-serif; font-weight: bold; font-size: 16px;">Rajasthan Royals Official Logo (Light BG)</span>
        </div>
      </body>
    </html>
  `);
  const artifactDir = 'C:\\Users\\tms10\\.gemini\\antigravity\\brain\\58919bc3-f90c-4e68-8103-3c4969f79061';
  const outPath = path.join(artifactDir, 'test_official_rr_logo_render.png');
  await page.screenshot({ path: outPath });
  console.log('Saved test official logo screenshot to:', outPath);
  await browser.close();
})();
