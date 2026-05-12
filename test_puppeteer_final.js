const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', error => console.log('PAGE ERROR:', error.message));
  page.on('requestfailed', request => console.log('FAILED:', request.url(), request.failure().errorText));
  
  await page.goto('file://' + path.resolve('add-job.html'), { waitUntil: 'networkidle0' });
  
  const hasCustomSelect = await page.evaluate(() => document.querySelectorAll('.custom-select-wrapper').length);
  console.log('Custom selects count:', hasCustomSelect);
  
  await browser.close();
})();
