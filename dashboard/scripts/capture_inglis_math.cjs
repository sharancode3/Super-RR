const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 1100 });
  await page.goto('http://localhost:5173/#methodology', { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 600));

  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button, [role="tab"]'));
    const target = btns.find(b => b.textContent && (b.textContent.includes('05') || b.textContent.includes('Bayes') || b.textContent.includes('Target')));
    if (target) target.click();
  });
  await new Promise(r => setTimeout(r, 600));

  const shrinkageCard = await page.$('.shrinkage-step-card');
  if (shrinkageCard) {
    const artifactDir = 'C:\\Users\\tms10\\.gemini\\antigravity\\brain\\58919bc3-f90c-4e68-8103-3c4969f79061';
    const outPath = path.join(artifactDir, 'interim_dossier_inglis_shrinkage_math.png');
    await shrinkageCard.screenshot({ path: outPath });
    console.log('Saved Inglis shrinkage screenshot to:', outPath);
  }

  await browser.close();
})();
