const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  await page.goto('http://127.0.0.1:8000/candidates.html', { waitUntil: 'networkidle0' });
  await page.evaluate(() => { localStorage.setItem('aura_user', JSON.stringify({ name: 'Admin', role: 'SuperAdmin' })); });
  await page.goto('http://127.0.0.1:8000/candidates.html', { waitUntil: 'networkidle0' });

  const layout = await page.evaluate(() => {
    const sidebar = document.querySelector('.sidebar');
    const secSidebar = document.querySelector('.secondary-sidebar');
    const logo = document.querySelector('.sidebar-logo');
    const svg = document.querySelector('.sidebar-logo svg');
    const text = document.querySelector('.sidebar-logo .nav-text');
    
    const getRect = (el) => {
        if(!el) return null;
        const r = el.getBoundingClientRect();
        return {x: r.x, y: r.y, w: r.width, h: r.height, zIndex: window.getComputedStyle(el).zIndex};
    };
    
    return {
      sidebar: getRect(sidebar),
      secSidebar: getRect(secSidebar),
      logo: getRect(logo),
      svg: getRect(svg),
      text: getRect(text)
    };
  });
  console.log('candidates.html layout:', JSON.stringify(layout, null, 2));

  await browser.close();
})();
