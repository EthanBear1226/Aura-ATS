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
        let patchStatus = 200;
        let releaseSave = null;
        const edits = [];
        const transitions = [];
        let releaseFirstRequest;
        const firstRequest = new Promise(resolve => { releaseFirstRequest = resolve; });
        let pending = true;
        await page.route('**/*', async route => {
            const url = new URL(route.request().url());
            if (url.origin !== 'http://contacts.test') return route.abort();
            if (url.pathname === '/api/candidates/902/transition') {
                assert.equal(route.request().method(), 'POST');
                const body = route.request().postDataJSON();
                transitions.push(body);
                candidate.stage = body.target_stage;
                return route.fulfill({ json: candidate });
            }
            if (url.pathname === '/api/candidates/902') {
                if (route.request().method() === 'PATCH') {
                    edits.push(route.request().postDataJSON());
                    if (releaseSave) await new Promise(resolve => { releaseSave = resolve; });
                    if (patchStatus !== 200) return route.fulfill({ status: patchStatus, json: { detail: 'Permission denied' } });
                    candidate = { ...candidate, ...edits.at(-1) };
                    candidate.logs = [{ action: '修改基本信息', details: candidate.name, operator: 'Test HR' }];
                    return route.fulfill({ json: candidate });
                }
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
        const actionCard = page.locator('.candidate-action-card');
        assert.equal(await actionCard.locator('svg, i, img').count(), 0);
        assert(!/[💬👥⚠🎉↻↩➔✕]/u.test(await actionCard.innerText()));
        await actionCard.getByRole('button', { name: '推进至部门筛选', exact: true }).click();
        assert(await page.locator('#advanceModal').isVisible());
        assert.equal(await page.locator('#advanceTargetStage').innerText(), '部门筛选');
        assert(await page.locator('#advanceModal').evaluate(el => !el.parentElement.closest('.modal-overlay')));
        await page.locator('#advanceModal').getByRole('button', { name: '取消', exact: true }).click();
        assert.equal(transitions.length, 0);
        await actionCard.getByRole('button', { name: '推进至部门筛选', exact: true }).click();
        await page.locator('#advanceNoteInput').fill('Synthetic review note');
        await page.locator('#advanceModal').getByRole('button', { name: '确认推进', exact: true }).click();
        await page.waitForFunction(() => document.querySelector('#advanceModal').style.display === 'none');
        assert.equal(transitions.length, 1);
        assert.equal(transitions[0].action, 'advance');
        assert.equal(transitions[0].target_stage, '部门筛选');
        assert.equal(transitions[0].reason, 'Synthetic review note');
        candidate.stage = '初筛';
        await page.evaluate(() => loadDetail());
        const rejectButton = actionCard.getByRole('button', { name: '淘汰', exact: true });
        await page.mouse.move(0, 0);
        assert.equal(await rejectButton.evaluate(el => getComputedStyle(el).backgroundColor), 'rgb(255, 241, 240)');
        await rejectButton.hover();
        await page.waitForFunction(() => getComputedStyle(document.querySelector('.candidate-action-danger')).backgroundColor === 'rgb(255, 228, 225)');
        await rejectButton.click();
        assert(await page.locator('#rejectModal').isVisible());
        await page.locator('#rejectModal').getByRole('button', { name: '取消', exact: true }).click();
        await actionCard.getByRole('button', { name: '添加备注', exact: true }).click();
        assert(await page.locator('#tab-pane-4').isVisible());
        await page.evaluate(() => switchNavTab(0));
        await actionCard.getByRole('button', { name: '推荐部门', exact: true }).click();
        assert(await page.locator('#detailRecommendModal').isVisible());
        await page.locator('#detailRecommendModal').getByRole('button', { name: '取消', exact: true }).click();
        candidate.stage = '面试';
        await page.evaluate(() => loadDetail());
        await actionCard.getByRole('button', { name: '撤回上步', exact: true }).click();
        assert(await page.locator('#rollbackModal').isVisible());
        await page.locator('#rollbackModal').getByRole('button', { name: '取消', exact: true }).click();
        candidate.stage = '已淘汰';
        await page.evaluate(() => loadDetail());
        await actionCard.getByRole('button', { name: '重新进入流程', exact: true }).click();
        assert(await page.locator('#reenterModal').isVisible());
        await page.locator('#reenterModal').getByRole('button', { name: '取消', exact: true }).click();
        candidate.stage = '入职';
        await page.evaluate(() => loadDetail());
        assert(await actionCard.getByText('候选人已正式入职', { exact: true }).isVisible());
        assert.equal(await actionCard.locator('.btn-blue-dropdown').count(), 0);
        candidate.stage = '初筛';
        await page.evaluate(() => loadDetail());
        for (const width of [1440, 1024, 390, 320]) {
            await page.setViewportSize({ width, height: 900 });
            const bounds = await actionCard.evaluate(el => {
                const card = el.getBoundingClientRect();
                return [...el.querySelectorAll('button')].every(button => {
                    const rect = button.getBoundingClientRect();
                    return rect.height >= 36 && rect.left >= card.left && rect.right <= card.right &&
                        button.scrollWidth <= button.clientWidth + 1;
                });
            });
            assert(bounds, `${width}px: action buttons overflow`);
        }
        await actionCard.screenshot({ path: path.join(__dirname, '.env.candidate-actions-mobile.png') });
        await page.setViewportSize({ width: 1440, height: 900 });
        await page.locator('.right-control-sidebar').screenshot({ path: path.join(__dirname, '.env.candidate-actions-desktop.png') });
        console.log('PASS candidate actions: plain text, confirmation/cancel, notes, recommendation, rollback, reenter, onboarding and responsive layout');
        await page.screenshot({ path: path.join(__dirname, '.env.candidate-contact-desktop.png'), fullPage: false });
        await page.reload();
        await page.waitForFunction(() => document.querySelector('#meta-phone').textContent === '13900001234');

        assert.equal(await page.locator('#meta-gender').innerText(), '性别未填写');
        assert.equal(await page.locator('#header-application-count').innerText(), '已申请0次');
        assert.equal(await page.getByText('Boss直聘', { exact: false }).count(), 0);
        await page.getByRole('button', { name: '编辑基本信息', exact: true }).click();
        const editor = page.getByRole('dialog', { name: '编辑基本信息', exact: true });
        assert.equal(await editor.getByLabel('姓名', { exact: true }).inputValue(), 'Contact Fixture');
        await editor.getByLabel('姓名', { exact: true }).fill('Cancelled');
        await editor.getByRole('button', { name: '取消', exact: true }).click();
        assert.equal(edits.length, 0);
        await page.getByRole('button', { name: '编辑基本信息', exact: true }).click();
        await editor.getByLabel('联系电话', { exact: true }).fill('bad-phone');
        await editor.getByRole('button', { name: '保存', exact: true }).click();
        assert.equal(edits.length, 0);
        assert.equal(await editor.locator('[role="alert"]').innerText(), '请填写有效联系电话');
        await editor.getByLabel('联系电话', { exact: true }).fill('13800005678');
        await editor.getByLabel('姓名', { exact: true }).fill(' Updated Fixture ');
        await editor.getByLabel('邮箱', { exact: true }).fill('updated@test.local');
        await editor.getByLabel('学历', { exact: true }).fill('硕士');
        patchStatus = 403;
        await editor.getByRole('button', { name: '保存', exact: true }).click();
        await page.waitForFunction(() => document.querySelector('#profile-edit-error').textContent === 'Permission denied');
        assert.equal(await editor.getByLabel('姓名', { exact: true }).inputValue(), ' Updated Fixture ');
        patchStatus = 200;
        releaseSave = true;
        await editor.getByRole('button', { name: '保存', exact: true }).click();
        await page.waitForFunction(() => document.querySelector('#profile-save').disabled);
        assert(await editor.getByLabel('姓名', { exact: true }).isDisabled());
        assert(await editor.getByRole('button', { name: '取消', exact: true }).isDisabled());
        await page.keyboard.press('Escape');
        assert(await editor.isVisible(), 'Cannot dismiss an in-flight save');
        const writes = edits.length;
        releaseSave();
        releaseSave = null;
        await page.waitForFunction(() => !document.querySelector('#profile-edit-dialog').open);
        assert.equal(edits.length, writes);
        assert.equal(candidate.name, 'Updated Fixture');
        assert.equal(candidate.exp, '硕士');
        await page.reload();
        await page.waitForFunction(() => document.querySelector('#header-cand-name').textContent === 'Updated Fixture');
        assert.equal(await page.locator('#meta-email').innerText(), 'updated@test.local');
        await page.getByRole('button', { name: '编辑基本信息', exact: true }).click();
        await editor.getByRole('button', { name: '保存', exact: true }).click();
        assert.equal(edits.length, writes, 'No-op does not write');
        candidate.raw_text = '姓名：张雪 | 学历：本科\n电话 13900001234 邮箱 original@test.local';
        await page.getByRole('button', { name: '编辑基本信息', exact: true }).click();
        for (const field of ['联系电话', '邮箱', '学历']) await editor.getByLabel(field, { exact: true }).fill('');
        await editor.getByRole('button', { name: '保存', exact: true }).click();
        await page.waitForFunction(() => !document.querySelector('#profile-edit-dialog').open);
        await page.reload();
        await page.waitForFunction(() => document.querySelector('#header-cand-name').textContent === 'Updated Fixture');
        assert.equal(await page.locator('#meta-phone').innerText(), '--');
        assert.equal(await page.locator('#meta-email').innerText(), '--');
        assert.equal(await page.locator('#meta-education').innerText(), '学历未填写');
        await page.getByRole('button', { name: '编辑基本信息', exact: true }).click();
        for (const width of [1440, 390, 320]) {
            await page.setViewportSize({ width, height: 900 });
            assert(await editor.evaluate(el => el.scrollWidth <= el.clientWidth + 1 && el.getBoundingClientRect().right <= innerWidth));
        }
        await page.screenshot({ path: path.join(__dirname, '.env.candidate-profile-mobile.png') });
        await page.setViewportSize({ width: 1440, height: 900 });
        await page.screenshot({ path: path.join(__dirname, '.env.candidate-profile-desktop.png') });
        await page.keyboard.press('Escape');
        assert(!(await editor.isVisible()));
        await page.getByRole('button', { name: '编辑基本信息', exact: true }).click();
        patchStatus = 503;
        await editor.getByLabel('姓名', { exact: true }).fill('Uncertain Fixture');
        await editor.getByRole('button', { name: '保存', exact: true }).click();
        await page.waitForFunction(() => document.querySelector('#profile-edit-error').textContent.includes('结果待确认'));
        assert(await editor.getByRole('button', { name: '保存', exact: true }).isDisabled());
        await editor.getByRole('button', { name: '取消', exact: true }).click();
        await page.getByRole('button', { name: '编辑基本信息', exact: true }).click();
        assert.equal(await editor.getByLabel('姓名', { exact: true }).inputValue(), 'Uncertain Fixture');
        assert(await editor.getByRole('button', { name: '保存', exact: true }).isDisabled());
        await page.keyboard.press('Escape');
        patchStatus = 200;
        await page.reload();
        await page.waitForFunction(() => document.querySelector('#header-cand-name').textContent === 'Updated Fixture');
        await page.getByRole('button', { name: '编辑基本信息', exact: true }).click();
        assert(await editor.getByRole('button', { name: '保存', exact: true }).isEnabled());
        await page.keyboard.press('Escape');
        candidate.name = 'legacy.pdf';
        candidate.exp = '未知';
        candidate.ai_analysis = '<img src=x onerror="window.profileXss=true">';
        candidate.skills = ['模拟', '<img src=x onerror="window.profileXss=true">'];
        candidate.raw_text += '\n<img src=x onerror="window.profileXss=true">';
        await page.evaluate(() => loadDetail());
        assert.equal(await page.locator('#header-cand-name').innerText(), '张雪');
        assert.equal(await page.locator('#meta-education').innerText(), '本科');
        const beforeNoop = edits.length;
        await page.getByRole('button', { name: '编辑基本信息', exact: true }).click();
        await editor.getByRole('button', { name: '保存', exact: true }).click();
        assert.equal(edits.length, beforeNoop, 'Extracted display alone must not create a write');
        assert.equal(await page.locator('#ai-skills img, #ai-analysis-container img, #fallback-resume-card img').count(), 0);
        assert.equal(await page.evaluate(() => window.profileXss), undefined);
        candidate.name = 'Contact Fixture';
        candidate.exp = '未知';
        candidate.raw_text = '博士项目，硕士优先';
        candidate.ai_summary = '女 博士 13812345678 fake@test.local';
        await page.evaluate(() => loadDetail());
        assert.equal(await page.locator('#meta-gender').innerText(), '性别未填写');
        assert.equal(await page.locator('#meta-education').innerText(), '学历未填写');
        console.log('PASS candidate profile: truthful fields, extracted name, edit/cancel, validation, failure retention, save lock, persistence, clearing, no-op, safe text, mobile dialog');

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
        assert(!(await page.getByRole('button', { name: '编辑基本信息', exact: true }).isVisible()));
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
