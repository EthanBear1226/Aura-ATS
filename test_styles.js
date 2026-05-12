const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  await page.goto('http://127.0.0.1:8000/index.html');
  await page.evaluate(() => { localStorage.setItem('aura_user', JSON.stringify({ name: 'Admin', role: 'SuperAdmin' })); });
  await page.goto('http://127.0.0.1:8000/index.html', { waitUntil: 'networkidle0' });
  const indexHtml = await page.evaluate(() => document.getElementById('sidebar-container').innerHTML);
  console.log('index html length:', indexHtml.length);

  await page.goto('http://127.0.0.1:8000/candidates.html', { waitUntil: 'networkidle0' });
  const candidatesHtml = await page.evaluate(() => document.getElementById('sidebar-container').innerHTML);
  console.log('candidates html length:', candidatesHtml.length);

  await browser.close();
})();
