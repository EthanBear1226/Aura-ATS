(() => {
    'use strict';
    let data = null;
    let revision = 0;
    let pending = false;
    let dialog;
    const byId = id => document.getElementById(id);
    const isAdmin = () => {
        try { return ['Admin', 'SuperAdmin'].includes(JSON.parse(localStorage.getItem('aura_user'))?.role); }
        catch (_) { return false; }
    };
    function node(tag, text, className) {
        const element = document.createElement(tag);
        if (text !== undefined) element.textContent = text;
        if (className) element.className = className;
        return element;
    }
    function button(text, action) {
        const element = node('button', text, 'btn');
        element.type = 'button';
        element.onclick = action;
        return element;
    }
    function status(message, retry = false) {
        const box = byId('accountListStatus');
        box.replaceChildren();
        box.className = message ? 'account-list-message' : '';
        if (message) box.append(document.createTextNode(message));
        if (retry) box.append(button('重试', load));
    }
    function render() {
        const rows = byId('accountRows');
        rows.replaceChildren();
        if (!data) return;
        const query = byId('accountSearch').value.trim().toLocaleLowerCase();
        const people = data.interviewers.filter(person =>
            [person.name, person.department, person.account?.email, person.account?.name]
                .some(value => String(value || '').toLocaleLowerCase().includes(query)));
        byId('accountCount').textContent = `${people.length} / ${data.interviewers.length} 人`;
        status(people.length ? '' : (query ? '没有匹配的人员' : '暂无面试官'));
        people.forEach(person => {
            const row = node('tr');
            const identity = node('td', person.name);
            identity.append(node('span', `${person.department || '未分配部门'} · ID ${person.id}`, 'account-secondary'));
            const account = node('td', person.account?.name || '未绑定');
            if (person.account) account.append(node('span', person.account.email, 'account-secondary'));
            const state = node('td', person.account ? (person.account.role === 'Interviewer' ? '已绑定' : '账号角色已变更') : '待绑定');
            const action = node('td');
            action.append(button(person.account ? '查看' : '绑定账号', () => open(person)));
            row.append(identity, account, state, action);
            rows.append(row);
        });
    }
    async function load() {
        if (pending) return;
        const request = ++revision;
        data = null;
        byId('accountRows').replaceChildren();
        byId('accountCount').textContent = '';
        if (!isAdmin()) {
            status('仅管理员可管理面试官账号绑定');
            byId('accountAddPerson').disabled = true;
            return;
        }
        status('正在读取账号绑定...');
        byId('accountRefresh').disabled = true;
        try {
            const response = await fetch('/api/settings/interviewer-accounts', {signal: AbortSignal.timeout(15000)});
            if (!response.ok) throw new Error(response.status === 403 ? '仅管理员可管理面试官账号绑定' : '账号绑定加载失败');
            const result = await response.json();
            if (request !== revision) return;
            data = result;
            render();
        } catch (error) {
            if (request === revision) status(error.message || '网络异常，账号绑定尚未读取', true);
        } finally {
            if (request === revision) byId('accountRefresh').disabled = false;
        }
    }
    function close() {
        if (!pending) dialog?.close();
    }
    function open(person) {
        if (pending || !isAdmin()) return;
        dialog?.remove();
        dialog = node('dialog', undefined, 'account-dialog');
        dialog.setAttribute('aria-labelledby', 'accountDialogTitle');
        const form = node('form');
        form.onsubmit = event => event.preventDefault();
        const title = node('h3', person.account ? '已绑定账号' : '绑定面试官账号');
        title.id = 'accountDialogTitle';
        const identity = node('p', `${person.name} · ID ${person.id}`);
        const footer = node('footer');
        const cancel = button('取消', close);
        form.append(title, identity);
        dialog.append(form);
        dialog.addEventListener('cancel', event => { if (pending) event.preventDefault(); });
        document.body.append(dialog);
        if (person.account) {
            form.append(node('p', `${person.account.name} · ${person.account.email}`));
            form.append(node('p', person.account.role === 'Interviewer' ? '已关联历史面试记录，不能直接转移给其他账号。' : '该账号已不是面试官角色，请联系管理员核对权限。'));
            footer.append(button('关闭', close));
            form.append(footer);
            dialog.showModal();
            return;
        }
        let selected = null;
        const search = node('input');
        search.type = 'search';
        search.placeholder = '搜索姓名或工作邮箱';
        search.setAttribute('aria-label', '搜索面试官账号');
        const options = node('div', undefined, 'account-options');
        const confirm = node('label', undefined, 'account-confirm');
        const checkbox = node('input');
        checkbox.type = 'checkbox';
        confirm.append(checkbox, document.createTextNode('确认账号归属无误；绑定后可访问该面试官的历史面试和相关简历。'));
        const error = node('p', '', 'account-dialog-error');
        error.setAttribute('role', 'alert');
        const save = button('确认绑定', saveBinding);
        save.classList.add('btn-primary');
        save.disabled = true;
        const sync = () => { save.disabled = !selected || !checkbox.checked || pending; };
        checkbox.onchange = sync;
        const renderOptions = () => {
            options.replaceChildren();
            const query = search.value.trim().toLocaleLowerCase();
            const accounts = data.accounts.filter(account => `${account.name} ${account.email}`.toLocaleLowerCase().includes(query));
            if (!accounts.length) options.append(node('p', query ? '没有匹配的账号' : '暂无已注册的面试官账号', 'account-list-message'));
            accounts.forEach(account => {
                const label = node('label', undefined, 'account-option');
                const input = node('input');
                input.type = 'radio';
                input.name = 'interviewerAccount';
                input.value = account.id;
                input.disabled = account.interviewer_id !== null;
                input.checked = account.id === selected;
                const text = node('span', account.name);
                text.append(node('span', `${account.email}${input.disabled ? ' · 已绑定其他面试官' : ''}`, 'account-secondary'));
                input.onchange = () => { selected = account.id; checkbox.checked = false; error.textContent = ''; sync(); };
                label.append(input, text);
                options.append(label);
            });
        };
        search.oninput = () => {
            // Filter changes require an explicit, visible selection again.
            selected = null;
            checkbox.checked = false;
            renderOptions();
            sync();
        };
        footer.append(cancel, save);
        form.append(search, options, confirm, error, footer);
        renderOptions();
        dialog.showModal();
        search.focus();
        async function saveBinding() {
            if (pending || !selected || !checkbox.checked) return;
            pending = true;
            const controls = [...form.querySelectorAll('input, button')];
            const states = controls.map(control => control.disabled);
            controls.forEach(control => control.disabled = true);
            save.textContent = '绑定中...';
            error.textContent = '';
            try {
                const response = await fetch(`/api/settings/interviewers/${person.id}/account`, {
                    method: 'PATCH', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({user_id: selected}), signal: AbortSignal.timeout(15000),
                });
                if (!response.ok) {
                    const result = await response.json();
                    error.textContent = typeof result.detail === 'string' ? result.detail : '绑定失败，请检查账号状态';
                    if (response.status === 409 || response.status === 403) {
                        selected = null;
                        checkbox.checked = false;
                        controls.forEach(control => control.disabled = true);
                        cancel.disabled = false;
                        cancel.textContent = '关闭并刷新';
                        cancel.onclick = () => { close(); load(); };
                    }
                    return;
                }
                const result = await response.json();
                if (result.user_id !== selected || result.interviewer_id !== person.id) throw new Error('Unexpected response');
                pending = false;
                dialog.close();
                window.showToast?.('账号绑定已保存', 'success');
                await load();
            } catch (_) {
                // A dropped response may follow a successful commit. Refresh before another write.
                pending = false;
                dialog.close();
                await load();
                window.showToast?.('绑定结果待确认，请核对刷新后的账号状态', 'error');
            } finally {
                pending = false;
                save.textContent = '确认绑定';
                if (selected !== null) controls.forEach((control, index) => control.disabled = states[index]);
                sync();
            }
        }
    }
    window.auraInterviewerAccounts = { load };
    document.addEventListener('DOMContentLoaded', () => {
        byId('accountRefresh').onclick = load;
        byId('accountSearch').oninput = render;
        byId('accountAddPerson').onclick = () => { if (isAdmin()) openDictModal('interviewers', '新增面试官'); };
        if (!isAdmin()) byId('accountAddPerson').disabled = true;
        const modal = byId('dictModal');
        new MutationObserver(() => {
            if (!modal.classList.contains('active') && byId('sec-interviewer-accounts').classList.contains('active')) load();
        }).observe(modal, {attributes: true, attributeFilter: ['class']});
        if (location.hash === '#interviewer-accounts') {
            byId('sec-departments').classList.remove('active');
            document.querySelectorAll('.settings-nav-item').forEach(item => item.classList.remove('active'));
            document.querySelector('[data-setting="interviewer-accounts"]').classList.add('active');
            byId('sec-interviewer-accounts').classList.add('active');
            load();
        }
    });
})();
