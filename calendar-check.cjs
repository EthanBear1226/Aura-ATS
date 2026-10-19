const { chromium } = require('playwright');
const assert = require('assert');
const fs = require('fs');
const http = require('http');
const path = require('path');

(async () => {
  let mode = 'local', bookingStatus = 200, submitted = [], peopleEmpty = false;
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://localhost');
    const json = (data, status = 200) => {
      res.writeHead(status, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(data));
    };
    if (url.pathname === '/api/settings/interviewers') {
      return json(peopleEmpty ? [] : [{ id: 7, name: '真实面试官 <安全文本>' }]);
    }
    if (url.pathname === '/api/calendar/freebusy') {
      if (mode === 'error') return json({}, 500);
      const selectedMode = mode, day = url.searchParams.get('date');
      const message = selectedMode === 'local' ? `飞书日历未接入；仅检查 Aura 内部排期 ${day}` :
        (selectedMode === 'unbound' ? '面试官尚未绑定飞书身份' : '飞书日历暂不可用');
      setTimeout(() => json({ external_status: selectedMode === 'local' ? 'not_connected' : selectedMode, message,
        slots: ['09:00', '10:00', '11:00'].map((time, index) => ({time,
          isFree: selectedMode === 'local' && index > 0,
          label: index === 0 ? 'Aura 已占用' : (selectedMode === 'local' ? 'Aura 无冲突 · 飞书未检查' : '档期待确认') })) }), day === '2026-11-02' ? 180 : 10);
      return;
    }
    if (url.pathname === '/api/interviews' && req.method === 'POST') {
      let body = '';
      req.on('data', chunk => body += chunk);
      req.on('end', () => {
        submitted.push(JSON.parse(body));
        json(bookingStatus === 200 ? {id: 55} : {detail: '该面试官已有重叠排期'}, bookingStatus);
      });
      return;
    }
    if (url.pathname === '/') {
      res.setHeader('Content-Type', 'text/html; charset=utf-8');
      res.end('<!doctype html><html><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/assets/css/styles.css"><body><script src="/assets/js/app.js"></script></body></html>');
      return;
    }
    if (url.pathname.startsWith('/assets/')) {
      const file = path.join(__dirname, url.pathname);
      if (!fs.existsSync(file)) { res.writeHead(404); res.end(); return; }
      res.setHeader('Content-Type', file.endsWith('.js') ? 'text/javascript' : 'text/css');
      res.end(fs.readFileSync(file));
      return;
    }
    res.writeHead(404); res.end();
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  let browser;
  try {
    browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
    const page = await browser.newPage({ viewport: {width: 1440, height: 1000} });
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.addInitScript(() => {
      localStorage.setItem('aura_user', JSON.stringify({role: 'Admin', name: 'HR'}));
      localStorage.setItem('aura_token', 'test.' + btoa(JSON.stringify({exp: 4102444800})) + '.test');
    });
    await page.goto(`http://127.0.0.1:${server.address().port}/`);
    await page.evaluate(() => {
      window.toasts = [];
      window.showToast = text => window.toasts.push(text);
      openScheduleDrawer('测试候选人', 'candidate@example.com', '前端工程师', 101);
    });
    const button = page.locator('#drawerInterviewerOptions button');
    await button.waitFor();
    assert.equal(await button.innerText(), '真实面试官 <安全文本>');
    assert.equal(await page.locator('#drawerInterviewerOptions select').count(), 0);
    await button.click();
    await page.locator('#drawerInterviewDate').fill('2026-11-02');
    await page.locator('#drawerInterviewDate').fill('2026-11-03');
    await page.waitForFunction(() => document.getElementById('drawerAvailabilityStatus').textContent.includes('2026-11-03'));
    await page.waitForTimeout(230);
    assert((await page.locator('#drawerAvailabilityStatus').innerText()).includes('2026-11-03'));
    assert.equal(await page.locator('[name="drawerTimeSlot"][value="09:00"]').isDisabled(), true);
    await page.locator('[name="drawerTimeSlot"][value="10:00"]').check();
    await page.locator('#drawerInterviewDate').fill('');
    assert.equal(await page.locator('[name="drawerTimeSlot"]').count(), 0);
    mode = 'error';
    await page.locator('#drawerInterviewDate').fill('2026-11-03');
    await page.getByRole('button', {name: '重试查询'}).waitFor();
    assert.equal(await page.locator('[name="drawerTimeSlot"]').count(), 0);
    mode = 'unbound';
    await page.getByRole('button', {name: '重试查询'}).click();
    await page.waitForFunction(() => document.getElementById('drawerAvailabilityStatus').textContent.includes('未绑定'));
    assert.equal(await page.locator('[name="drawerTimeSlot"]:enabled').count(), 0);
    mode = 'unavailable';
    await page.evaluate(() => loadDrawerAvailability());
    assert.equal(await page.locator('[name="drawerTimeSlot"]:enabled').count(), 0);
    mode = 'local';
    await page.evaluate(() => loadDrawerAvailability());
    await page.locator('[name="drawerTimeSlot"][value="10:00"]').check();
    await page.locator('#drawerLocation').fill('会议室 B');
    bookingStatus = 409;
    await page.locator('#drawerSubmitBtn').click();
    await page.waitForFunction(() => window.toasts.some(text => text.includes('重叠排期')));
    await page.waitForFunction(() => !document.getElementById('drawerSubmitBtn').disabled);
    assert.equal(await page.locator('[name="drawerTimeSlot"]:checked').count(), 0);
    assert.equal(submitted[0].interviewer_id, 7);
    assert.equal(submitted[0].interviewer_name, '真实面试官 <安全文本>');
    assert.equal(submitted[0].location, '会议室 B');
    await page.screenshot({path: 'calendar-desktop.png'});
    await page.setViewportSize({width: 390, height: 844});
    await page.screenshot({path: 'calendar-mobile.png'});
    assert(await page.locator('#globalScheduleDrawer').evaluate(el => el.scrollWidth <= el.clientWidth + 1));
    assert(await page.locator('.drawer-body').evaluate(el => el.scrollWidth <= el.clientWidth + 1));
    bookingStatus = 200;
    await page.locator('[name="drawerTimeSlot"][value="11:00"]').check();
    await page.locator('#drawerSubmitBtn').click();
    await page.waitForFunction(() => window.toasts.some(text => text.includes('尚未同步飞书')));
    await page.waitForFunction(() => !document.getElementById('globalScheduleDrawer'));
    peopleEmpty = true;
    await page.evaluate(() => openScheduleDrawer('测试候选人', '', '前端工程师', 101));
    await page.waitForFunction(() => document.getElementById('drawerInterviewerOptions').textContent.includes('暂无面试官'));
    assert.deepEqual(errors, []);
    console.log('PASS calendar drawer: local-only, real people, stale responses, reset, unavailable, retry, conflict, submit and mobile layout');
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
