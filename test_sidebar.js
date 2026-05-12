const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  await page.goto('http://127.0.0.1:8000/candidates.html', { waitUntil: 'networkidle0' });
  await page.evaluate(() => { localStorage.setItem('aura_user', JSON.stringify({ name: 'Admin', role: 'SuperAdmin' })); });
  await page.goto('http://127.0.0.1:8000/candidates.html', { waitUntil: 'networkidle0' });

  const inner = await page.evaluate(() => {
    const sb = document.getElementById('sidebar-container');
    return sb ? sb.innerHTML : 'null';
  });
  console.log('candidates innerHTML:', inner);

  await browser.close();
})();
