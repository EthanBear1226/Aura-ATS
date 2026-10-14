const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const http = require('http');
const assert = require('assert');

(async () => {
  let candidates = [{ id: 101, name: '张测试', job: '前端工程师', stage: '初筛', created_at: '2026-10-14', gender: '男', degree: '本科' }];
  const server = http.createServer((req, res) => {
    const route = req.url.split('?')[0];
    if (route === '/api/candidates') {
      res.setHeader('Content-Type', 'application/json');
      res.end(JSON.stringify(candidates));
      return;
    }
    if (route === '/api/jobs' || route === '/api/settings/interviewers') {
      res.setHeader('Content-Type', 'application/json');
      res.end('[]');
      return;
    }
    const file = path.join(__dirname, route === '/' ? 'candidates.html' : route);
    if (!fs.existsSync(file)) { res.writeHead(404); res.end(); return; }
    res.setHeader('Content-Type', file.endsWith('.js') ? 'text/javascript' : file.endsWith('.css') ? 'text/css' : 'text/html');
    res.end(fs.readFileSync(file));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  let browser;
  try {
    browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    await context.addInitScript(() => {
      localStorage.setItem('aura_user', JSON.stringify({ role: 'Admin', name: '测试 HR' }));
      localStorage.setItem('aura_token', 'test.' + btoa(JSON.stringify({ exp: 4102444800 })) + '.test');
    });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => console.log('BROWSER', message.type(), message.text()));
    await page.goto(`http://127.0.0.1:${server.address().port}/candidates.html`);
    await page.waitForTimeout(1000);
    if (!await page.locator('.moka-cand-card').count()) {
      console.log('DEBUG errors=', errors);
      console.log('DEBUG body=', (await page.locator('body').innerText()).slice(0, 1200));
    }
    await page.waitForFunction(() => document.querySelectorAll('.moka-cand-card').length === 1);
    assert.equal(await page.locator('.cand-name').first().innerText(), '张测试');
    assert.equal(await page.locator('#job-total-count-badge').innerText(), '共 1 个');
    assert.equal(await page.locator('#moka-cand-cards-container .aura-empty-box').count(), 0);
    assert.equal(errors.length, 0, errors.join('\n'));

    candidates = [];
    await page.reload();
    await page.waitForFunction(() => document.querySelector('#moka-cand-cards-container')?.innerText.includes('当前筛选下暂无候选人'));
    assert.equal(await page.locator('.moka-cand-card').count(), 0);
    assert.equal(await page.locator('#moka-cand-cards-container .aura-empty-box').count(), 1);
    assert.equal(errors.length, 0, errors.join('\n'));
    console.log('PASS: uploaded candidate API data renders; no legacy variable error; empty API state is honest; no demo candidates');
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
