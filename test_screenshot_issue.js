const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.setViewport({ width: 1200, height: 800 });
  
  await page.goto('http://127.0.0.1:8000/index.html');
  await page.evaluate(() => { localStorage.setItem('aura_user', JSON.stringify({ name: 'Admin', role: 'SuperAdmin' })); });
  await page.goto('http://127.0.0.1:8000/index.html', { waitUntil: 'networkidle0' });
  await page.screenshot({ path: 'index_ss.png' });
  
  await page.goto('http://127.0.0.1:8000/candidates.html', { waitUntil: 'networkidle0' });
  await page.screenshot({ path: 'candidates_ss.png' });

  await browser.close();
})();
