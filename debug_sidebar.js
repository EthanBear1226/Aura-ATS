const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  await page.goto('http://127.0.0.1:8000/candidates.html');
  await new Promise(r => setTimeout(r, 1000));
  
  const logoInfo = await page.evaluate(() => {
    const logo = document.querySelector('.sidebar-logo');
    const svg = document.querySelector('.sidebar-logo svg');
    const text = document.querySelector('.sidebar-logo .nav-text');
    return {
      logo: logo ? { width: logo.clientWidth, display: window.getComputedStyle(logo).display } : null,
      svg: svg ? { width: svg.clientWidth, height: svg.clientHeight, display: window.getComputedStyle(svg).display, minWidth: window.getComputedStyle(svg).minWidth, flexShrink: window.getComputedStyle(svg).flexShrink } : null,
      text: text ? { display: window.getComputedStyle(text).display, opacity: window.getComputedStyle(text).opacity } : null,
    };
  });
  console.log('candidates.html logo info:', logoInfo);

  await page.goto('http://127.0.0.1:8000/index.html');
  await new Promise(r => setTimeout(r, 1000));
  const logoInfoIndex = await page.evaluate(() => {
    const logo = document.querySelector('.sidebar-logo');
    const svg = document.querySelector('.sidebar-logo svg');
    const text = document.querySelector('.sidebar-logo .nav-text');
    return {
      logo: logo ? { width: logo.clientWidth, display: window.getComputedStyle(logo).display } : null,
      svg: svg ? { width: svg.clientWidth, height: svg.clientHeight, display: window.getComputedStyle(svg).display, minWidth: window.getComputedStyle(svg).minWidth, flexShrink: window.getComputedStyle(svg).flexShrink } : null,
      text: text ? { display: window.getComputedStyle(text).display, opacity: window.getComputedStyle(text).opacity } : null,
    };
  });
  console.log('index.html logo info:', logoInfoIndex);

  await browser.close();
})();
