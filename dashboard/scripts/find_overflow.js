import puppeteer from 'puppeteer';

const browser = await puppeteer.launch({ headless: true });
const page = await browser.newPage();
await page.setViewport({ width: 320, height: 568 });
await page.goto('http://localhost:5174/', { waitUntil: 'networkidle0' });

const offenders = await page.evaluate(() => {
  const elements = Array.from(document.querySelectorAll('*'));
  return elements
    .filter(el => el.getBoundingClientRect().right > 320.5 || el.scrollWidth > 320.5)
    .map(el => ({
      tag: el.tagName,
      className: typeof el.className === 'string' ? el.className : '',
      id: el.id,
      scrollWidth: el.scrollWidth,
      right: Math.round(el.getBoundingClientRect().right),
      width: Math.round(el.getBoundingClientRect().width)
    }))
    .slice(0, 15);
});

console.log('Offenders at 320px:', offenders);
await browser.close();
