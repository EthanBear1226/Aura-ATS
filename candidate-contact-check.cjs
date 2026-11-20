const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

// All requests use synthetic fixtures; never connect to the user's test database.
(async () => {
    const browser = await chromium.launch({
        executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true,
    });
    try {
        const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
        await context.addInitScript(() => {
            localStorage.setItem('aura_user', JSON.stringify({ role: 'Admin', name: 'Test HR' }));
            localStorage.setItem('aura_token', 'test.' + btoa(JSON.stringify({ exp: 4102444800 })) + '.test');
        });
        const page = await context.newPage();
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        let candidate = {
            id: 902, name: 'Contact Fixture', job: 'Engineer', stage: '初筛', exp: '本科',
            phone: '13900001234', email: 'contact.fixture@test.local',
            raw_text: 'Synthetic resume', ai_summary: 'Synthetic summary',
            ai_analysis: 'Synthetic analysis', skills: [], applications: [], interviews: [], logs: [],
        };
        let status = 200;
        let releaseFirstRequest;
        const firstRequest = new Promise(resolve => { releaseFirstRequest = resolve; });
        let pending = true;
        await page.route('**/*', async route => {
            const url = new URL(route.request().url());
            if (url.origin !== 'http://contacts.test') return route.abort();
            if (url.pathname === '/api/candidates/902') {
                assert.equal(url.searchParams.get('reveal_sensitive'), 'true');
                assert(route.request().headers().authorization?.startsWith('Bearer '));
                if (pending) { pending = false; await firstRequest; }
                return route.fulfill({ status, json: status === 200 ? candidate : { detail: 'Unavailable' } });
            }
            if (url.pathname.startsWith('/api/')) return route.fulfill({ json: [] });
            const relative = url.pathname === '/candidate-detail.html' ? 'candidate-detail.html' : url.pathname.slice(1);
            const file = path.resolve(__dirname, relative);
            if (!file.startsWith(__dirname + path.sep) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
                return route.fulfill({ status: 404, body: '' });
            }
            return route.fulfill({
                contentType: file.endsWith('.js') ? 'text/javascript' : file.endsWith('.css') ? 'text/css' : 'text/html',
                body: fs.readFileSync(file),
            });
        });
        await page.goto('http://contacts.test/candidate-detail.html?id=902');
        assert.equal(await page.locator('#meta-phone').innerText(), '--', 'No demo phone while loading');
        assert.equal(await page.locator('#meta-email').innerText(), '--', 'No demo email while loading');
        releaseFirstRequest();
        await page.waitForFunction(() => document.querySelector('#header-cand-name').textContent === 'Contact Fixture');
        assert.equal(await page.locator('#meta-phone').innerText(), candidate.phone);
        assert.equal(await page.locator('#meta-email').innerText(), candidate.email);
        assert.equal(await page.locator('[id^="eye-btn-"], #meta-idcard').count(), 0);
        await page.screenshot({ path: path.join(__dirname, '.env.candidate-contact-desktop.png'), fullPage: false });
        await page.reload();
        await page.waitForFunction(() => document.querySelector('#meta-phone').textContent === '13900001234');

        candidate.phone = '暂无';
        candidate.email = '未知';
        candidate.raw_text = 'Phone: 186-0000-1234 Email: original@test.local';
        await page.reload();
        await page.waitForFunction(() => document.querySelector('#meta-phone').textContent === '186-0000-1234');
        assert.equal(await page.locator('#meta-email').innerText(), 'original@test.local');

        candidate.raw_text = 'No contact information. Legacy reference: 310104199508122345';
        candidate.ai_summary = 'Do not trust AI contacts: 13812345678 ai@test.local';
        await page.reload();
        await page.waitForFunction(() => document.querySelector('#header-cand-name').textContent === 'Contact Fixture');
        assert.equal(await page.locator('#meta-phone').innerText(), '--');
        assert.equal(await page.locator('#meta-email').innerText(), '--');

        candidate.phone = '139********34';
        candidate.email = 'c********';
        candidate.raw_text = 'Phone: 13900001234 Email: private@test.local';
        await page.evaluate(() => localStorage.setItem('aura_user', JSON.stringify({ role: 'Interviewer' })));
        await page.evaluate(() => loadDetail());
        assert.equal(await page.locator('#meta-phone').innerText(), candidate.phone);
        assert.equal(await page.locator('#meta-email').innerText(), candidate.email);
        candidate.phone = null;
        candidate.email = null;
        await page.evaluate(() => loadDetail());
        assert.equal(await page.locator('#meta-phone').innerText(), '--');
        assert.equal(await page.locator('#meta-email').innerText(), '--');
        await page.evaluate(() => localStorage.setItem('aura_user', '{invalid'));
        await page.evaluate(() => loadDetail());
        assert.equal(await page.locator('#meta-phone').innerText(), '--');
        assert.equal(await page.locator('#meta-email').innerText(), '--');

        await page.evaluate(() => localStorage.setItem('aura_user', JSON.stringify({ role: 'Admin' })));
        candidate.phone = '13900001234';
        candidate.email = 'a.very.long.contact.address.for.layout.verification@example.test';
        await page.evaluate(() => loadDetail());
        for (const width of [1440, 1024, 390, 320]) {
            await page.setViewportSize({ width, height: 900 });
            const layout = await page.evaluate(() => {
                const header = document.querySelector('.header-meta-line').getBoundingClientRect();
                const phone = document.querySelector('#meta-phone').getBoundingClientRect();
                const email = document.querySelector('#meta-email').getBoundingClientRect();
                return {
                    contained: [phone, email].every(rect => rect.left >= header.left - 1 && rect.right <= header.right + 1),
                    overlapping: !(phone.right <= email.left || email.right <= phone.left || phone.bottom <= email.top || email.bottom <= phone.top),
                };
            });
            assert(layout.contained, `${width}px: contact outside header`);
            assert(!layout.overlapping, `${width}px: contacts overlap`);
        }
        await page.screenshot({ path: path.join(__dirname, '.env.candidate-contact-mobile.png'), fullPage: false });
        status = 503;
        await page.reload();
        await page.waitForFunction(() => document.querySelector('#header-cand-name').textContent === '档案加载失败');
        assert.equal(await page.locator('#meta-phone').innerText(), '--');
        assert.equal(await page.locator('#meta-email').innerText(), '--');
        assert.deepEqual(errors, []);
        console.log('PASS candidate contacts: direct display, original-text recovery, missing values, restricted roles, refresh, failure and responsive layout');
    } finally {
        await browser.close();
    }
})().catch(error => { console.error(error); process.exitCode = 1; });
