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
      logo: logo ? { 
        width: logo.clientWidth, 
        padding: window.getComputedStyle(logo).padding,
        display: window.getComputedStyle(logo).display,
        whiteSpace: window.getComputedStyle(logo).whiteSpace,
        overflow: window.getComputedStyle(logo).overflow
      } : null,
      svg: svg ? { 
        width: svg.clientWidth, 
        minWidth: window.getComputedStyle(svg).minWidth,
        flexShrink: window.getComputedStyle(svg).flexShrink,
        display: window.getComputedStyle(svg).display
      } : null,
      text: text ? { 
        display: window.getComputedStyle(text).display,
        opacity: window.getComputedStyle(text).opacity,
        width: text.clientWidth
      } : null,
    };
  });
  console.log('candidates css:', logoStyles);
  await browser.close();
})();
