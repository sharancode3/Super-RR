const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 1100 });
  await page.goto('http://localhost:5173/#methodology', { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 600));

  // Click Module 04 tab
  await page.evaluate(() => {
    const tab4 = document.querySelector('#tab-04-pressure-definition, button[data-module="04-pressure-definition"]');
    if (tab4) {
      tab4.click();
    } else {
      // Find button containing "Pressure" or "04"
      const btns = Array.from(document.querySelectorAll('button, [role="tab"]'));
      const target = btns.find(b => b.textContent && (b.textContent.includes('04') || b.textContent.includes('Pressure Definition')));
      if (target) target.click();
    }
  });
  await new Promise(r => setTimeout(r, 600));

  // Find formula box and screenshot it
  const formulaBox = await page.$('.formula-callout-box');
  const artifactDir = 'C:\\Users\\tms10\\.gemini\\antigravity\\brain\\58919bc3-f90c-4e68-8103-3c4969f79061';
  if (formulaBox) {
    const outPath = path.join(artifactDir, 'interim_dossier_methodology_formulas.png');
    await formulaBox.screenshot({ path: outPath });
    console.log('Saved formula callout screenshot to:', outPath);
  } else {
    console.log('Could not find .formula-callout-box, taking full section screenshot');
    const outPath = path.join(artifactDir, 'interim_dossier_methodology_formulas.png');
    await page.screenshot({ path: outPath, fullPage: false });
  }

  // Also check Module 05 for Target Formulation & Volume Shrinkage formulas
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button, [role="tab"]'));
    const target = btns.find(b => b.textContent && (b.textContent.includes('05') || b.textContent.includes('Bayes') || b.textContent.includes('Target')));
    if (target) target.click();
  });
  await new Promise(r => setTimeout(r, 600));

  const ensembleGrid = await page.$('.ensemble-spec-grid');
  if (ensembleGrid) {
    const outPath2 = path.join(artifactDir, 'interim_dossier_methodology_ensemble_math.png');
    await ensembleGrid.screenshot({ path: outPath2 });
    console.log('Saved ensemble math screenshot to:', outPath2);
  }

  await browser.close();
})();
