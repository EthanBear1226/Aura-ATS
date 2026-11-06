const {chromium} = require('playwright');
const assert = require('assert');

(async () => {
    const base = process.env.AURA_PREVIEW_URL || 'http://127.0.0.1:8127';
    assert(['127.0.0.1', 'localhost'].includes(new URL(base).hostname), 'Use an isolated local preview only');
    const browser = await chromium.launch({executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true});
    let personId;
    let api;
    try {
        const context = await browser.newContext({viewport: {width: 1440, height: 960}});
        const page = await context.newPage();
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        const login = await context.request.post(`${base}/api/auth/login`, {
            data: {email: 'hr.preview@aura.local', password: 'AuraPreview2026!'},
        });
        assert(login.ok(), await login.text());
        const session = await login.json();
        api = async (method, path, data) => context.request.fetch(`${base}${path}`, {
            method, headers: {Authorization: `Bearer ${session.access_token}`}, data,
        });
        const created = await api('POST', '/api/settings/interviewers', {name: '绑定验收 <安全文本>', role_type: 'Interviewer'});
        assert(created.ok(), await created.text());
        personId = (await created.json()).id;
        await context.addInitScript(session => {
            localStorage.setItem('aura_token', session.access_token);
            localStorage.setItem('aura_user', JSON.stringify(session.user));
        }, session);
        await page.goto(`${base}/settings.html#interviewer-accounts`);
        await page.waitForFunction(() => document.querySelectorAll('#accountRows tr').length >= 4);
        await page.locator('#accountSearch').fill('没有这个人员');
        assert.equal(await page.locator('#accountRows tr').count(), 0);
        await page.locator('#accountSearch').fill('绑定验收');
        const row = page.locator('#accountRows tr');
        assert((await row.innerText()).includes('<安全文本>'));
        assert.equal(await page.locator('#accountRows script').count(), 0);
        await row.getByRole('button', {name: '绑定账号'}).click();
        const dialog = page.locator('dialog[open]');
        const save = dialog.getByRole('button', {name: '确认绑定'});
        assert(await save.isDisabled());
        assert(await dialog.locator('input[type=radio]').first().isDisabled());
        await dialog.getByRole('searchbox').fill('chen.preview');
        await dialog.locator('input[type=radio]').check();
        assert(await save.isDisabled());
        await dialog.locator('input[type=checkbox]').check();
        assert(!(await save.isDisabled()));
        await dialog.getByRole('searchbox').fill('zhou.preview');
        assert(await save.isDisabled());
        await dialog.getByRole('searchbox').fill('chen.preview');
        await dialog.locator('input[type=radio]').check();
        await dialog.locator('input[type=checkbox]').check();
        await page.screenshot({path: 'accounts-desktop.png', animations: 'disabled'});
        await page.route('**/api/settings/interviewers/*/account', route => route.fulfill({status: 409,
            contentType: 'application/json', body: JSON.stringify({detail: '该账号已绑定其他面试官'})}));
        await save.click();
        await page.getByRole('alert').filter({hasText: '已绑定其他面试官'}).waitFor();
        assert(await save.isDisabled());
        await dialog.getByRole('button', {name: '关闭并刷新'}).click();
        await page.unroute('**/api/settings/interviewers/*/account');
        await page.locator('#accountRows tr').getByRole('button', {name: '绑定账号'}).click();
        await dialog.getByRole('searchbox').fill('chen.preview');
        await dialog.locator('input[type=radio]').check();
        await dialog.locator('input[type=checkbox]').check();
        await dialog.getByRole('button', {name: '确认绑定'}).click();
        await page.waitForFunction(() => document.querySelector('#accountRows').textContent.includes('chen.preview@aura.local'));
        await page.reload();
        await page.waitForFunction(() => document.querySelector('#accountRows').textContent.includes('chen.preview@aura.local'));
        await page.locator('#accountSearch').fill('绑定验收');
        await page.locator('#accountRows').getByRole('button', {name: '查看'}).click();
        assert((await dialog.innerText()).includes('不能直接转移'));
        assert.equal(await dialog.locator('input[type=radio]').count(), 0);
        await page.keyboard.press('Escape');
        await page.route('**/api/settings/interviewer-accounts', route => route.fulfill({status: 503, body: '{}'}), {times: 1});
        await page.locator('#accountRefresh').click();
        await page.locator('#accountListStatus').getByRole('button', {name: '重试', exact: true}).waitFor();
        assert.equal(await page.locator('#accountRows tr').count(), 0);
        await page.locator('#accountListStatus').getByRole('button', {name: '重试', exact: true}).click();
        await page.waitForFunction(() => document.querySelectorAll('#accountRows tr').length === 1);
        await page.locator('#accountSearch').fill('');
        await page.setViewportSize({width: 390, height: 844});
        await page.screenshot({path: 'accounts-mobile.png', animations: 'disabled'});
        assert(await page.locator('.settings-content').evaluate(el => el.scrollWidth <= el.clientWidth + 1));
        assert(await page.locator('#sec-interviewer-accounts').evaluate(el => el.scrollWidth <= el.clientWidth + 1));
        await page.locator('#accountSearch').fill('陈思宁');
        await page.locator('#accountRows').getByRole('button', {name: '绑定账号'}).click();
        await page.screenshot({path: 'accounts-mobile-dialog.png', animations: 'disabled'});
        assert(await dialog.evaluate(el => el.scrollWidth <= el.clientWidth + 1));
        await page.keyboard.press('Escape');
        await page.evaluate(() => {
            const user = JSON.parse(localStorage.getItem('aura_user'));
            user.role = 'Interviewer';
            localStorage.setItem('aura_user', JSON.stringify(user));
            window.auraInterviewerAccounts.load();
        });
        assert((await page.locator('#accountListStatus').innerText()).includes('仅管理员'));
        assert.equal(await page.locator('#accountRows tr').count(), 0);
        assert.deepEqual(errors, []);
        console.log('PASS real local API: search, XSS text, occupied account, explicit confirmation, conflict, save, reload, read-only, retry, mobile and role gate');
    } finally {
        if (personId && api) await api('DELETE', `/api/settings/interviewers/${personId}`);
        await browser.close();
    }
})().catch(error => {console.error(error); process.exitCode = 1;});
