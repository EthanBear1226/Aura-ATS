# 人才库深度重构与系统设置UI精装 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重塑人才库逻辑（移除无关操作、加入“重新激活”功能）及精装系统设置页面（引入高保真模态框）。同时确保移动端侧边栏的 Logo 始终可见。

**Architecture:** 前端页面重构与 JavaScript 交互修改。

**Tech Stack:** HTML, CSS, Vanilla JS

---

### Task 1: 确保移动端侧边栏 Logo 始终可见

**Files:**
- Modify: `assets/css/styles.css`

- [ ] **Step 1: 更新 CSS 媒体查询中的 `.sidebar-logo`**
找到 `assets/css/styles.css` 文件底部的 `@media (max-width: 768px)` 块。将其中的 `.sidebar-logo { display: none; }` 修改为使其在底部导航栏中作为品牌图标居中展示，或者在顶部始终保留一个导航条。
*由于现在的移动端策略是将 sidebar 变成了 fixed at bottom 的 row 布局，我们可以将 logo 显示在最左侧或单独处理。*

```css
  /* 替换掉原来的 .sidebar-logo { display: none; } */
  .sidebar-logo {
    display: flex;
    padding: 0 16px;
    align-items: center;
    justify-content: center;
  }
  .sidebar-logo .nav-text {
    display: none; /* 在移动端只显示图标，隐藏 "Aura" 文字，或者可以显示 */
  }
  /* 更好的做法：让文字也显示，但缩小字号 */
  .sidebar-logo .nav-text {
    display: block;
    font-size: 14px;
    margin-left: 4px;
  }
```

- [ ] **Step 2: Commit**
```bash
git add assets/css/styles.css
git commit -m "style: keep Aura logo visible on mobile sidebar navigation"
```

---

### Task 2: 人才库列表页逻辑净化与复捞机制

**Files:**
- Modify: `talent-pool.html`

- [ ] **Step 1: 移除不合理的操作按钮，添加“重新激活”按钮**
在 `talent-pool.html` 的 `loadCandidates` 渲染循环中，将 `<td>` 里的“推荐”、“面试”和“删除”全部清空，只保留一个“重新激活”按钮。同时将表格 header 的最后一列对齐。

```javascript
                let dateStr = c.created_at ? new Date(c.created_at).toISOString().split('T')[0] : '--';
                
                // 替换 actions 列
                let actionsHtml = `<button class="btn btn-primary" onclick="event.stopPropagation(); reactivateCandidate('${c.id}')" style="padding:4px 12px; font-size:12px; background: var(--primary-color); color: white; border: none;">重新激活</button>`;
                
                tbody.innerHTML += `
                    <tr onclick="viewDetail('${c.id}')" style="cursor: pointer; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#f4f8ff'" onmouseout="this.style.backgroundColor=''">
                        <td style="font-weight:500;">${c.name}</td>
                        <td>${c.job}</td>
                        <td><span class="tag tag-gray">${c.stage}</span></td>
                        <td style="color:var(--text-secondary);">${c.exp}</td>
                        <td style="color:var(--text-secondary);">${dateStr}</td>
                        <td style="white-space: nowrap;">
                            ${actionsHtml}
                        </td>
                    </tr>
                `;
```

- [ ] **Step 2: 移除原有的 Checkbox 逻辑**
在 `talent-pool.html` 中移除 header 中的 `<th style="width: 40px;"><input type="checkbox"...></th>` 以及 tbody 生成代码中的 checkbox td。确保表格现在只有 6 列。

- [ ] **Step 3: 添加 `reactivateCandidate` 函数**
在 `talent-pool.html` 的 `<script>` 块中，加入发送 `PATCH` 请求的逻辑。

```javascript
        async function reactivateCandidate(id) {
            showConfirm('确定要重新激活该候选人吗？TA 将回到初筛节点。', async () => {
                try {
                    const user = JSON.parse(localStorage.getItem('aura_user') || '{}');
                    const operatorName = user.name || '系统';
                    
                    const response = await fetch(`/api/candidates/${id}`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ stage: '初筛', operator: operatorName, details: '从人才库重新激活' })
                    });
                    
                    if(response.ok) {
                        showToast('已重新激活，移入工作台', 'success');
                        loadCandidates(); // Refresh
                    } else {
                        const data = await response.json();
                        showToast(`操作失败: ${data.detail || '未知错误'}`, 'error');
                    }
                } catch (error) {
                    console.error(error);
                    showToast('操作失败，请检查网络', 'error');
                }
            });
        }
```

- [ ] **Step 4: Commit**
```bash
git add talent-pool.html
git commit -m "feat: refactor talent pool list to only allow reactivate action"
```

---

### Task 3: 人才库详情页只读化与复捞机制

**Files:**
- Modify: `candidate-detail.html`

- [ ] **Step 1: 详情页只读判定与 UI 渲染**
在 `loadDetail` 函数中，获取到 candidate 数据后，判断如果 `candidate.stage === '已淘汰'`，则隐藏掉所有常规的操作按钮（推进流程、安排面试、淘汰），只显示一个蓝色的“重新激活”按钮。

```javascript
                // Update Actions Container
                const actionsContainer = document.getElementById('cand-actions-container'); // Need to wrap buttons in this ID
                
                if (candidate.stage === '已淘汰') {
                    // 只读模式 / 人才库模式
                    actionsContainer.innerHTML = `
                        <button class="btn btn-primary" style="width:100%; justify-content:center;" onclick="reactivateCurrentCandidate()">重新激活</button>
                    `;
                } else {
                    // 正常活跃模式
                    let nextBtnHtml = '';
                    const currentIndex = STAGES.indexOf(candidate.stage);
                    if (currentIndex >= 0 && currentIndex < STAGES.length - 1) {
                        const nextStage = STAGES[currentIndex + 1];
                        if (nextStage === '用人部门筛选') {
                            nextBtnHtml = `<button class="btn btn-primary" id="btn-next-stage" style="width:100%; justify-content:center;" onclick="openRecommendModal(${candidate.id})">推荐给用人部门</button>`;
                        } else {
                            nextBtnHtml = `<button class="btn btn-primary" id="btn-next-stage" style="width:100%; justify-content:center;" onclick="moveToNextStage()">推进至「${nextStage}」</button>`;
                        }
                    }
                    
                    actionsContainer.innerHTML = `
                        ${nextBtnHtml}
                        <div style="display:flex; gap:8px; width:100%; margin-top:8px;">
                            <button class="btn" style="flex:1;" onclick="openScheduleDrawer('${candidate.name}', '${candidate.email || ''}', '${candidate.job}')">安排面试</button>
                            <button class="btn" style="flex:1; color:#FF3B30;" onclick="eliminateCurrentCandidate()">淘汰</button>
                        </div>
                    `;
                }
```
**注意**: 你需要在 `candidate-detail.html` 的 HTML 结构中，给包含这些按钮的 `div` 加上 `id="cand-actions-container"`。

- [ ] **Step 2: 添加 `reactivateCurrentCandidate` 函数**
在 `candidate-detail.html` 的 `<script>` 块中：

```javascript
        async function reactivateCurrentCandidate() {
            if(!currentCandidate) return;
            showConfirm('确定要重新激活该候选人吗？TA 将回到初筛节点。', async () => {
                try {
                    const user = JSON.parse(localStorage.getItem('aura_user') || '{}');
                    const operatorName = user.name || '系统';
                    
                    const response = await fetch(`/api/candidates/${currentCandidate.id}`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ stage: '初筛', operator: operatorName, details: '从人才库重新激活' })
                    });
                    
                    if(response.ok) {
                        showToast('已重新激活', 'success');
                        setTimeout(() => {
                            window.location.href = 'candidates.html';
                        }, 1000);
                    } else {
                        const data = await response.json();
                        showToast(`操作失败: ${data.detail || '未知错误'}`, 'error');
                    }
                } catch (error) {
                    console.error(error);
                    showToast('操作失败，请检查网络', 'error');
                }
            });
        }
```

- [ ] **Step 3: Commit**
```bash
git add candidate-detail.html
git commit -m "feat: make eliminated candidate details read-only and provide reactivate action"
```

---

### Task 4: 系统设置页精装 - 引入高保真模态框与空状态

**Files:**
- Modify: `settings.html`
- Modify: `assets/css/styles.css` (可选，如需增加模态框样式，但 `styles.css` 里已有 `.modal-overlay` 和 `.modal-card`)

- [ ] **Step 1: HTML 增加统一的高保真模态框**
在 `settings.html` 的 `<body>` 标签内，增加一个通用的 `DictModal`。

```html
    <!-- 通用字典操作弹窗 -->
    <div class="modal-overlay" id="dictModal">
        <div class="modal-card" style="width: 400px;">
            <h2 id="dictModalTitle" style="margin-top:0;">新增条目</h2>
            <div class="form-group">
                <label>名称<span class="required-mark">*</span></label>
                <input type="text" id="dictItemName" placeholder="请输入名称">
            </div>
            <!-- 动态注入额外字段 -->
            <div id="dictExtraFields"></div>
            
            <div style="display:flex; gap:12px; margin-top:24px;">
                <button class="btn" style="flex:1; justify-content:center;" onclick="closeDictModal()">取消</button>
                <button class="btn btn-primary" style="flex:1; justify-content:center;" onclick="submitDictItem()">保存</button>
            </div>
        </div>
    </div>
```

- [ ] **Step 2: 重写 `addDict` 和相关 JS 逻辑**
在 `settings.html` 中移除原来用 `prompt` 的粗糙实现，改为弹出 Modal。

```javascript
        let currentDictType = '';

        function openDictModal(type, title) {
            currentDictType = type;
            document.getElementById('dictModalTitle').innerText = title;
            document.getElementById('dictItemName').value = '';
            
            const extraFields = document.getElementById('dictExtraFields');
            extraFields.innerHTML = '';
            
            if (type === 'interviewers') {
                extraFields.innerHTML = `
                    <div class="form-group" style="margin-top: 16px;">
                        <label>角色</label>
                        <select id="dictItemRole" class="form-control" style="width: 100%; padding: 12px; border-radius: 8px; border: 1px solid var(--border-color);">
                            <option value="Manager">用人经理 (Manager)</option>
                            <option value="Interviewer">面试官 (Interviewer)</option>
                            <option value="HR">人事 (HR)</option>
                        </select>
                    </div>
                `;
            } else if (type === 'locations') {
                extraFields.innerHTML = `
                    <div class="form-group" style="margin-top: 16px;">
                        <label>类型</label>
                        <select id="dictItemType" class="form-control" style="width: 100%; padding: 12px; border-radius: 8px; border: 1px solid var(--border-color);">
                            <option value="线下">线下</option>
                            <option value="线上">线上</option>
                        </select>
                    </div>
                `;
            } else if (type === 'interview-processes') {
                extraFields.innerHTML = `
                    <div class="form-group" style="margin-top: 16px;">
                        <label>流转节点 (用逗号分隔)</label>
                        <input type="text" id="dictItemStages" placeholder="如: 初筛,一面,二面,HR面" value="初筛,一面,HR面">
                    </div>
                `;
            }
            
            document.getElementById('dictModal').classList.add('active');
        }

        function closeDictModal() {
            document.getElementById('dictModal').classList.remove('active');
        }

        async function submitDictItem() {
            const name = document.getElementById('dictItemName').value.trim();
            if (!name) { alert('请输入名称'); return; }
            
            let payload = { name };
            if (currentDictType === 'interviewers') {
                payload.role_type = document.getElementById('dictItemRole').value;
            } else if (currentDictType === 'locations') {
                payload.type = document.getElementById('dictItemType').value;
            } else if (currentDictType === 'interview-processes') {
                payload.stages = document.getElementById('dictItemStages').value;
            }
            
            try {
                await fetch(`/api/settings/${currentDictType}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                closeDictModal();
                loadAllDicts();
            } catch (e) { console.error(e); }
        }
```

- [ ] **Step 3: 修改 HTML 按钮的调用**
在 `settings.html` 的五块 `settings-section` 中，将 `addDict('...')` 改为 `openDictModal('...', '新增...')`。

```html
<button class="btn btn-primary" onclick="openDictModal('departments', '新增部门')">新增部门</button>
<button class="btn btn-primary" onclick="openDictModal('interviewers', '新增人员')">新增人员</button>
<button class="btn btn-primary" onclick="openDictModal('locations', '新增地点')">新增地点</button>
<button class="btn btn-primary" onclick="openDictModal('interview-processes', '新增面试流程')">新增流程</button>
<button class="btn btn-primary" onclick="openDictModal('categories', '新增职位类别')">新增类别</button>
```

- [ ] **Step 4: 添加空状态 (Empty State)**
在 `loadAllDicts` 中处理空数组的返回。

```javascript
        function renderTableRows(tbodyId, data, cols, type) {
            const tbody = document.getElementById(tbodyId);
            if (!data || data.length === 0) {
                tbody.innerHTML = `<tr><td colspan="${cols}" style="text-align:center; padding:40px; color:var(--text-secondary);">暂无数据，请点击上方按钮新增</td></tr>`;
                return;
            }
            // Generate rows
            tbody.innerHTML = data.map(d => {
                let extra = '';
                if (type === 'interviewers') extra = `<td>${d.role_type}</td>`;
                if (type === 'locations') extra = `<td><span class="tag tag-gray">${d.type}</span></td>`;
                if (type === 'interview-processes') extra = `<td><span class="tag tag-blue">${d.stages}</span></td>`;
                
                return `<tr>
                    <td style="font-weight:500;">${d.name}</td>
                    ${extra}
                    <td style="width:80px;"><button class="btn" style="color:#FF3B30; padding:4px 12px;" onclick="deleteDict('${type}', ${d.id})">删除</button></td>
                </tr>`;
            }).join('');
        }

        async function loadAllDicts() {
            fetch('/api/settings/departments').then(r=>r.json()).then(d => renderTableRows('tb-departments', d, 2, 'departments'));
            fetch('/api/settings/interviewers').then(r=>r.json()).then(d => renderTableRows('tb-interviewers', d, 3, 'interviewers'));
            fetch('/api/settings/locations').then(r=>r.json()).then(d => renderTableRows('tb-locations', d, 3, 'locations'));
            fetch('/api/settings/interview-processes').then(r=>r.json()).then(d => renderTableRows('tb-processes', d, 3, 'interview-processes'));
            fetch('/api/settings/categories').then(r=>r.json()).then(d => renderTableRows('tb-categories', d, 2, 'categories'));
        }
```

- [ ] **Step 5: 平滑删除确认**
如果你全局有 `showConfirm` (应该在 `assets/js/app.js` 或其他地方有定义)，将 `deleteDict` 里的 `confirm` 替换为 `showConfirm`。

```javascript
        async function deleteDict(type, id) {
            if(window.showConfirm) {
                showConfirm("确认要删除该条目吗？删除后相关业务数据可能无法匹配。", async () => {
                    await fetch(`/api/settings/${type}/${id}`, { method: 'DELETE' });
                    loadAllDicts();
                });
            } else {
                if(!confirm("确认删除？")) return;
                await fetch(`/api/settings/${type}/${id}`, { method: 'DELETE' });
                loadAllDicts();
            }
        }
```

- [ ] **Step 6: Commit**
```bash
git add settings.html
git commit -m "style: revamp system settings with high-fidelity modals and empty states"
```
