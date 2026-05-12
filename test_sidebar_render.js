const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  
  await page.goto('http://127.0.0.1:8000/candidates.html', { waitUntil: 'networkidle0' });
  await page.evaluate(() => { localStorage.setItem('aura_user', JSON.stringify({ name: 'Admin', role: 'SuperAdmin' })); });
  await page.goto('http://127.0.0.1:8000/candidates.html', { waitUntil: 'networkidle0' });

  const logoDetails = await page.evaluate(() => {
    const logo = document.querySelector('.sidebar-logo');
    if (!logo) return 'No logo found';
    const rect = logo.getBoundingClientRect();
    const svg = document.querySelector('.sidebar-logo svg');
    const svgRect = svg ? svg.getBoundingClientRect() : null;
    return {
      logoRect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
      svgRect: svgRect ? { x: svgRect.x, y: svgRect.y, width: svgRect.width, height: svgRect.height } : null,
      html: logo.outerHTML
    };
  });
  console.log('candidates logo:', JSON.stringify(logoDetails, null, 2));

  await browser.close();
})();
