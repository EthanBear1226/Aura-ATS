# 人才库模块与淘汰机制 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 增加“人才库”模块，将删除简历功能变更为将简历“淘汰”并归档入人才库，提升历史数据的管理和沉淀。

**Architecture:** 前端通过过滤 `stage` 字段区分活跃候选人和淘汰候选人。后端通过现有的 `PATCH` 接口将候选人 `stage` 设置为 `已淘汰` 来实现逻辑归档，不改变现有数据库表结构。

**Tech Stack:** HTML, CSS, Vanilla JS, FastAPI

---

### Task 1: 侧边栏导航和路由增加“人才库”

**Files:**
- Modify: `assets/js/app.js`
- Modify: `main.py`

- [ ] **Step 1: 在前端导航增加人才库入口**
修改 `assets/js/app.js` 中 `renderSidebar` 函数的 `navItems` 数组，在 `candidates` 后方插入 `talent-pool`。

```javascript
        { id: 'candidates', name: '候选人管理', icon: '<svg viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>', link: 'candidates.html' },
        { id: 'talent-pool', name: '人才库', icon: '<svg viewBox="0 0 24 24"><path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H8V4h12v12z"/></svg>', link: 'talent-pool.html' },
```

- [ ] **Step 2: 在后端增加路由**
修改 `main.py`，在 `@app.get("/candidates.html")` 下方添加路由。

```python
@app.get("/talent-pool.html")
async def read_talent_pool():
    return FileResponse('talent-pool.html')
```

- [ ] **Step 3: Commit**
```bash
git add assets/js/app.js main.py
git commit -m "feat: add talent pool to sidebar navigation and backend router"
```

---

### Task 2: 建立人才库页面

**Files:**
- Create: `talent-pool.html` (可以复制自 `candidates.html`，然后修改)

- [ ] **Step 1: 复制 `candidates.html` 到 `talent-pool.html`**
复制 `candidates.html` 并作以下几处主要修改：
1. `<title>` 更改为 `人才库 | Aura`。
2. `<h1 class="page-title">` 更改为 `人才库`。
3. 移除页面的“上传简历”和“批量操作”按钮及对应逻辑（只需要显示归档列表即可）。
4. 在 `DOMContentLoaded` 中调用 `renderSidebar('talent-pool')`。
5. 在 `loadCandidates()` 函数的过滤逻辑中，只显示 `c.stage === '已淘汰'` 的候选人。

```javascript
        async function loadCandidates() {
            try {
                const response = await fetch('/api/candidates');
                const data = await response.json();
                
                // 仅显示已淘汰的候选人
                let displayData = data.filter(c => c.stage === '已淘汰');

                const tbody = document.getElementById('candidateTbody');
                tbody.innerHTML = '';
```
6. 移除列表表格中的 `checkbox` 列，以及 `删除` 或 `淘汰` 按钮。
7. （可选）隐藏阶段筛选下拉框。

- [ ] **Step 2: Commit**
```bash
git add talent-pool.html
git commit -m "feat: create talent pool page to view archived candidates"
```

---

### Task 3: 修改候选人列表页的“删除”为“淘汰”

**Files:**
- Modify: `candidates.html`

- [ ] **Step 1: 过滤已淘汰候选人**
在 `loadCandidates()` 函数中，过滤掉已淘汰的候选人，使其不在正常列表里显示。

```javascript
                let displayData = data.filter(c => c.stage !== '已淘汰');
                
                if (currentStageFilter !== '全部阶段') {
```

- [ ] **Step 2: 修改按钮文本和调用函数**
将 `deleteCandidate` 替换为 `eliminateCandidate`，将显示文本“删除”替换为“淘汰”。

```javascript
                let deleteBtnHtml = perms.canDelete
                    ? `<button class="btn" onclick="event.stopPropagation(); eliminateCandidate('${c.id}')" style="padding:4px 12px; font-size:12px; color: #FF3B30; border-color: #FF3B30; background: #fff;">淘汰</button>`
                    : '';
```

- [ ] **Step 3: 实现 `eliminateCandidate` 函数**
用 `eliminateCandidate` 函数替换掉原来的 `deleteCandidate` 函数。修改 API 调用为 `PATCH`，将 stage 设置为 `已淘汰`。

```javascript
        async function eliminateCandidate(id) {
            showConfirm('确定要淘汰该候选人并归档到人才库吗？', async () => {
                try {
                    const user = JSON.parse(localStorage.getItem('aura_user') || '{}');
                    const operatorName = user.name || '系统';
                    
                    const response = await fetch(`/api/candidates/${id}`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ stage: '已淘汰', operator: operatorName, details: '淘汰至人才库' })
                    });

                    if(response.ok) {
                        showToast('已淘汰并归档', 'success');
                        loadCandidates(); // Refresh the list
                    } else {
                        const data = await response.json();
                        showToast(`操作失败: ${data.detail || '未知错误'}`, 'error');
                    }
                } catch (error) {
                    console.error(error);
                    showToast('操作失败，请检查网络或后端服务', 'error');
                }
            });
        }
```

- [ ] **Step 4: Commit**
```bash
git add candidates.html
git commit -m "feat: change delete action to eliminate and archive candidates in list view"
```

---

### Task 4: 修改候选人详情页的“删除”为“淘汰”

**Files:**
- Modify: `candidate-detail.html`

- [ ] **Step 1: 修改按钮显示**
找到详情页左侧的删除按钮，将其文本修改为 `淘汰`，并调用 `eliminateCurrentCandidate()`。

```html
                                    <button class="btn" style="flex:1; color:#FF3B30;" onclick="eliminateCurrentCandidate()">淘汰</button>
```

- [ ] **Step 2: 实现 `eliminateCurrentCandidate` 函数**
用 `eliminateCurrentCandidate` 替换原有的 `deleteCurrentCandidate` 函数。

```javascript
        async function eliminateCurrentCandidate() {
            if(!currentCandidate) return;
            showConfirm('确定要淘汰该候选人并归档到人才库吗？', async () => {
                try {
                    const user = JSON.parse(localStorage.getItem('aura_user') || '{}');
                    const operatorName = user.name || '系统';
                    
                    const response = await fetch(`/api/candidates/${currentCandidate.id}`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ stage: '已淘汰', operator: operatorName, details: '淘汰至人才库' })
                    });
                    
                    if(response.ok) {
                        showToast('已淘汰并归档', 'success');
                        setTimeout(() => {
                            window.location.href = 'candidates.html';
                        }, 1000);
                    } else {
                        const data = await response.json();
                        showToast(`操作失败: ${data.detail || '未知错误'}`, 'error');
                    }
                } catch (error) {
                    console.error(error);
                    showToast('操作失败，请检查网络或后端服务', 'error');
                }
            });
        }
```

- [ ] **Step 3: Update Mock Data Stage (Optional but recommended)**
确保 mockCandidates 不受影响或不受阻碍。

- [ ] **Step 4: Commit**
```bash
git add candidate-detail.html
git commit -m "feat: change delete action to eliminate and archive candidates in detail view"
```
