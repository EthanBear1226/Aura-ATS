const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  await page.goto('http://127.0.0.1:8000/candidates.html', { waitUntil: 'networkidle0' });
  await page.evaluate(() => { localStorage.setItem('aura_user', JSON.stringify({ name: 'Admin', role: 'SuperAdmin' })); });
  await page.goto('http://127.0.0.1:8000/candidates.html', { waitUntil: 'networkidle0' });

  const logoStyles = await page.evaluate(() => {
    const logo = document.querySelector('.sidebar-logo');
    const svg = document.querySelector('.sidebar-logo svg');
    const text = document.querySelector('.sidebar-logo .nav-text');
    return {
      logo: logo ? { width: logo.clientWidth, display: window.getComputedStyle(logo).display, padding: window.getComputedStyle(logo).padding } : null,
      svg: svg ? { width: svg.clientWidth, display: window.getComputedStyle(svg).display, minWidth: window.getComputedStyle(svg).minWidth } : null,
      text: text ? { display: window.getComputedStyle(text).display } : null,
    };
  });
  console.log('candidates css:', logoStyles);

  await page.goto('http://127.0.0.1:8000/index.html', { waitUntil: 'networkidle0' });
  const indexStyles = await page.evaluate(() => {
    const logo = document.querySelector('.sidebar-logo');
    const svg = document.querySelector('.sidebar-logo svg');
    const text = document.querySelector('.sidebar-logo .nav-text');
    return {
      logo: logo ? { width: logo.clientWidth, display: window.getComputedStyle(logo).display, padding: window.getComputedStyle(logo).padding } : null,
      svg: svg ? { width: svg.clientWidth, display: window.getComputedStyle(svg).display, minWidth: window.getComputedStyle(svg).minWidth } : null,
      text: text ? { display: window.getComputedStyle(text).display } : null,
    };
  });
  console.log('index css:', indexStyles);

  await browser.close();
})();
