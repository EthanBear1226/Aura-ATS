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
      res.end(JSON.stringify(route === '/api/jobs' ? [{id: 7, title: '前端工程师', status: '热招中'}] : []));
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
    assert.equal(await page.locator('select').count(), 0);
    await page.locator('#selectAll').check();
    assert.equal(await page.locator('#selected-count-badge').innerText(), '已选择 1 项');
    assert.equal(await page.locator('#bulkActionTrigger').isDisabled(), false);
    await page.locator('#bulkActionTrigger').click();
    assert.equal(await page.locator('#bulkActionMenu').getAttribute('class'), 'bulk-action-menu open');
    await page.keyboard.press('ArrowDown');
    assert.equal(await page.locator('[data-stage="初筛"]').evaluate(el=>el===document.activeElement), true);
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#bulkActionTrigger').getAttribute('aria-expanded'), 'false');
    await page.locator('#bulkActionTrigger').click();
    await page.locator('[data-stage="面试"]').click();
    assert.equal(await page.locator('#bulkActionMenu').getAttribute('class'), 'bulk-action-menu');
    await page.locator('.danger-modal-overlay button', { hasText: '取消' }).click();
    await page.locator('[data-sort="score_desc"]').click();
    assert.equal(await page.locator('[data-sort="score_desc"]').getAttribute('aria-pressed'), 'true');
    assert.equal(await page.locator('#selected-count-badge').isHidden(), true);
    await page.locator('#selectAll').check();
    await page.locator('#clearSelection').click();
    assert.equal(await page.locator('#bulkActionTrigger').isDisabled(), true);
    assert.equal(errors.length, 0, errors.join('\n'));

    await page.locator('#btnAddCandidate').click();
    await page.waitForURL('**/add-candidate.html');
    await page.waitForFunction(() => document.querySelector('#modal-job-select option[value="7"]'));
    await page.evaluate(() => { document.querySelector('#modal-job-select').value = '7'; });
    await page.route('**/api/parse-resumes', route => {
      assert(route.request().headers().authorization?.startsWith('Bearer '));
      assert(route.request().postData().includes('name="job_id"'));
      return route.fulfill({json: {succeeded: 1, failed: 0, results: [{status: 'success', filename: 'test.pdf', candidate: candidates[0]}]}});
    });
    await page.locator('#resume-file').setInputFiles({name: 'test.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4 test')});
    await page.locator('#view-uploaded-candidates').waitFor({state: 'visible'});
    assert.equal(await page.locator('#upload-results a').getAttribute('href'), 'candidate-detail.html?id=101');
    await page.locator('#view-uploaded-candidates').click();
    await page.waitForFunction(() => document.querySelectorAll('.moka-cand-card').length === 1);

    candidates.push({id:102,name:'第二位测试',job:'前端工程师',stage:'初筛',created_at:'2026-10-15'});
    await page.locator('#refreshCandidates').click();
    await page.waitForFunction(() => document.querySelectorAll('.moka-cand-card').length === 2);
    await page.locator('.cand-checkbox').first().check();
    assert(await page.locator('#selectAll').evaluate(el=>el.indeterminate));
    await page.locator('#selectAll').check();
    let requests = 0;
    await page.route('**/api/candidates/*/transition', async route => {
      requests++;
      const id=Number(route.request().url().split('/').at(-2));
      assert.equal(route.request().postDataJSON().target_stage,'部门筛选');
      if(id===101){candidates[0].stage='部门筛选';await route.fulfill({json:candidates[0]});}
      else await route.fulfill({status:400,json:{detail:'测试流转失败'}});
    });
    await page.locator('#bulkActionTrigger').click();
    await page.locator('[data-stage="部门筛选"]').click();
    assert.equal(requests,0,'Requests must wait for confirmation');
    await page.locator('#dangerModalConfirmBtn').click();
    await page.waitForFunction(()=>document.querySelector('#bulkResult').textContent.includes('失败 1 位'));
    assert.equal(requests,2);
    assert((await page.locator('#bulkResult').innerText()).includes('测试流转失败'));
    assert.equal(await page.locator('.moka-cand-card').count(),1);
    await page.locator('.moka-stage-tab-item').filter({hasText:'部门筛选'}).click();
    assert.equal(await page.locator('.cand-name').innerText(),'张测试');
    await page.setViewportSize({width:390,height:844});
    await page.mouse.move(350,100);
    await page.waitForTimeout(400);
    await page.screenshot({path:path.join(__dirname,'candidates-mobile.png')});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.setViewportSize({width:1440,height:900});
    await page.mouse.move(1300,100);
    await page.waitForTimeout(400);
    await page.screenshot({path:path.join(__dirname,'candidates-desktop.png')});
    await page.locator('.moka-stage-tab-item').filter({hasText:'已归档'}).click();
    assert.equal(await page.locator('.moka-cand-card').count(),0);

    candidates = [];
    await page.locator('#refreshCandidates').click();
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
