# 系统设置与组织架构动态化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 开发“系统设置”模块，将硬编码的部门、面试官、地点、面试流程等变更为数据库驱动的动态字典。

**Architecture:** 后端新增 5 张字典表及 RESTful API。前端新增 `settings.html` 进行维护，并在原有业务线页面替换硬编码选项，改为 `fetch` 加载。

**Tech Stack:** Python (FastAPI, SQLAlchemy), HTML, CSS, Vanilla JS

---

### Task 1: 建立后端数据模型及预置数据

**Files:**
- Modify: `models.py`
- Modify: `schemas.py`
- Modify: `main.py`
- Modify: `seed_data.py`

- [ ] **Step 1: 新增数据库模型**
在 `models.py` 底部添加五张新表：

```python
class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True)
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Interviewer(Base):
    __tablename__ = "interviewers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    role_type = Column(String(50)) # HR, Manager, Interviewer
    department_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Location(Base):
    __tablename__ = "locations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    type = Column(String(50), default="线下") # 线上, 线下
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class InterviewProcess(Base):
    __tablename__ = "interview_processes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    stages = Column(String(200))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class JobCategory(Base):
    __tablename__ = "job_categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
```

- [ ] **Step 2: 新增 Pydantic Schemas**
在 `schemas.py` 底部添加：

```python
class DictItemBase(BaseModel):
    name: str

class DepartmentCreate(DictItemBase):
    pass
class Department(DictItemBase):
    id: int
    status: str
    class Config: from_attributes = True

class InterviewerCreate(DictItemBase):
    role_type: str
    department_id: Optional[int] = None
class Interviewer(InterviewerCreate):
    id: int
    class Config: from_attributes = True

class LocationCreate(DictItemBase):
    type: str = "线下"
class Location(LocationCreate):
    id: int
    class Config: from_attributes = True

class InterviewProcessCreate(DictItemBase):
    stages: str
class InterviewProcess(InterviewProcessCreate):
    id: int
    class Config: from_attributes = True

class JobCategoryCreate(DictItemBase):
    pass
class JobCategory(DictItemBase):
    id: int
    class Config: from_attributes = True
```

- [ ] **Step 3: 修改数据库自动迁移**
在 `main.py` 中，`models.Base.metadata.create_all(bind=engine)` 已经会创建新表。不需要改动 `upgrade_db`。但在 `main.py` 的顶部，需要确认模型导入有效。

- [ ] **Step 4: 修改 seed_data.py**
在 `seed_data.py` 中增加初始字典数据：

```python
# 写入字典数据
def seed_dicts():
    if db.query(models.Department).count() == 0:
        for d in ["研发部", "产品部", "设计部", "市场部", "销售部", "人力资源部"]:
            db.add(models.Department(name=d))
        db.commit()
        
    if db.query(models.Location).count() == 0:
        db.add(models.Location(name="北京总部", type="线下"))
        db.add(models.Location(name="腾讯会议", type="线上"))
        db.commit()

    if db.query(models.JobCategory).count() == 0:
        for c in ["技术/研发", "产品/设计", "运营/市场", "职能/支持"]:
            db.add(models.JobCategory(name=c))
        db.commit()
        
    if db.query(models.InterviewProcess).count() == 0:
        db.add(models.InterviewProcess(name="标准技术面试", stages="初筛,一面,二面,HR面"))
        db.add(models.InterviewProcess(name="简易面试", stages="初筛,直属leader面"))
        db.commit()

    if db.query(models.Interviewer).count() == 0:
        db.add(models.Interviewer(name="研发总监", role_type="Manager"))
        db.add(models.Interviewer(name="产品总监", role_type="Manager"))
        db.add(models.Interviewer(name="HR 李", role_type="HR"))
        db.commit()

seed_dicts()
```

- [ ] **Step 5: Commit**
```bash
git add models.py schemas.py main.py seed_data.py
git commit -m "feat: add database models and schemas for system settings and seed initial data"
```

---

### Task 2: 后端字典 API 接口实现

**Files:**
- Modify: `main.py`

- [ ] **Step 1: 编写 API 接口**
在 `main.py` 中增加这 5 个实体的 CRUD 接口 (GET 列表，POST 创建，DELETE 删除)。放在文件下部。

```python
# --- System Settings APIs ---

@app.get("/api/settings/departments", response_model=list[schemas.Department])
def get_departments(db: Session = Depends(get_db)):
    return db.query(models.Department).all()

@app.post("/api/settings/departments", response_model=schemas.Department)
def create_department(item: schemas.DepartmentCreate, db: Session = Depends(get_db)):
    db_item = models.Department(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/api/settings/departments/{item_id}")
def delete_department(item_id: int, db: Session = Depends(get_db)):
    db.query(models.Department).filter(models.Department.id == item_id).delete()
    db.commit()
    return {"ok": True}

@app.get("/api/settings/interviewers", response_model=list[schemas.Interviewer])
def get_interviewers(db: Session = Depends(get_db)):
    return db.query(models.Interviewer).all()

@app.post("/api/settings/interviewers", response_model=schemas.Interviewer)
def create_interviewer(item: schemas.InterviewerCreate, db: Session = Depends(get_db)):
    db_item = models.Interviewer(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/api/settings/interviewers/{item_id}")
def delete_interviewer(item_id: int, db: Session = Depends(get_db)):
    db.query(models.Interviewer).filter(models.Interviewer.id == item_id).delete()
    db.commit()
    return {"ok": True}

@app.get("/api/settings/locations", response_model=list[schemas.Location])
def get_locations(db: Session = Depends(get_db)):
    return db.query(models.Location).all()

@app.post("/api/settings/locations", response_model=schemas.Location)
def create_location(item: schemas.LocationCreate, db: Session = Depends(get_db)):
    db_item = models.Location(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/api/settings/locations/{item_id}")
def delete_location(item_id: int, db: Session = Depends(get_db)):
    db.query(models.Location).filter(models.Location.id == item_id).delete()
    db.commit()
    return {"ok": True}

@app.get("/api/settings/interview-processes", response_model=list[schemas.InterviewProcess])
def get_interview_processes(db: Session = Depends(get_db)):
    return db.query(models.InterviewProcess).all()

@app.post("/api/settings/interview-processes", response_model=schemas.InterviewProcess)
def create_interview_process(item: schemas.InterviewProcessCreate, db: Session = Depends(get_db)):
    db_item = models.InterviewProcess(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/api/settings/interview-processes/{item_id}")
def delete_interview_process(item_id: int, db: Session = Depends(get_db)):
    db.query(models.InterviewProcess).filter(models.InterviewProcess.id == item_id).delete()
    db.commit()
    return {"ok": True}

@app.get("/api/settings/categories", response_model=list[schemas.JobCategory])
def get_categories(db: Session = Depends(get_db)):
    return db.query(models.JobCategory).all()

@app.post("/api/settings/categories", response_model=schemas.JobCategory)
def create_category(item: schemas.JobCategoryCreate, db: Session = Depends(get_db)):
    db_item = models.JobCategory(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/api/settings/categories/{item_id}")
def delete_category(item_id: int, db: Session = Depends(get_db)):
    db.query(models.JobCategory).filter(models.JobCategory.id == item_id).delete()
    db.commit()
    return {"ok": True}
```

- [ ] **Step 2: Commit**
```bash
git add main.py
git commit -m "feat: add RESTful APIs for system settings dictionaries"
```

---

### Task 3: 系统设置页面框架与权限

**Files:**
- Modify: `assets/js/app.js`
- Modify: `main.py`
- Create: `settings.html`

- [ ] **Step 1: 前端导航栏权限控制与入口**
修改 `assets/js/app.js`。获取 localStorage `aura_user` 角色。如果是 `SuperAdmin` 或 `Admin`，则在 `navItems` 中额外追加 `settings`。

```javascript
    const user = JSON.parse(localStorage.getItem('aura_user') || '{}');
    const role = user.role || 'HR';
    
    if (role === 'SuperAdmin' || role === 'Admin') {
        navItems.push({ id: 'settings', name: '系统设置', icon: '<svg viewBox="0 0 24 24"><path d="M19.14,12.94c0.04-0.3,0.06-0.61,0.06-0.94c0-0.32-0.02-0.64-0.06-0.94l2.03-1.58c0.18-0.14,0.23-0.41,0.12-0.61 l-1.92-3.32c-0.12-0.22-0.37-0.29-0.59-0.22l-2.39,0.96c-0.5-0.38-1.03-0.7-1.62-0.94L14.4,2.81c-0.04-0.24-0.24-0.41-0.48-0.41 h-3.84c-0.24,0-0.43,0.17-0.47,0.41L9.25,5.35C8.66,5.59,8.12,5.92,7.63,6.29L5.24,5.33c-0.22-0.08-0.47,0-0.59,0.22L2.73,8.87 C2.62,9.08,2.66,9.34,2.86,9.48l2.03,1.58C4.84,11.36,4.8,11.69,4.8,12s0.02,0.64,0.06,0.94l-2.03,1.58 c-0.18,0.14-0.23,0.41-0.12,0.61l1.92,3.32c0.12,0.22,0.37,0.29,0.59,0.22l2.39-0.96c0.5,0.38,1.03,0.7,1.62,0.94l0.36,2.54 c0.05,0.24,0.24,0.41,0.48,0.41h3.84c0.24,0,0.43-0.17,0.47-0.41l0.36-2.54c0.59-0.24,1.13-0.56,1.62-0.94l2.39,0.96 c0.22,0.08,0.47,0,0.59-0.22l1.92-3.32c0.12-0.22,0.07-0.49-0.12-0.61L19.14,12.94z M12,15.6c-1.98,0-3.6-1.62-3.6-3.6 s1.62-3.6,3.6-3.6s3.6,1.62,3.6,3.6S13.98,15.6,12,15.6z"/></svg>', link: 'settings.html' });
    }
```

- [ ] **Step 2: 后端路由**
在 `main.py` 添加 `settings.html` 的路由。

```python
@app.get("/settings.html")
async def read_settings():
    return FileResponse('settings.html')
```

- [ ] **Step 3: 创建 `settings.html` (基础框架)**
创建新文件 `settings.html`，包含侧边栏、右侧区域，定义一个简单的选项卡结构来切换不同字典的显示。

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>系统设置 | Aura</title>
    <link rel="stylesheet" href="assets/css/styles.css?v=6">
    <style>
        .settings-layout { display: flex; height: calc(100vh - 64px); background: #fff; }
        .settings-nav { width: 240px; border-right: 1px solid var(--border-color); background: #fafafa; padding: 20px 0; }
        .settings-nav-item { padding: 12px 24px; cursor: pointer; color: var(--text-primary); font-weight: 500; }
        .settings-nav-item:hover { background: #f0f0f0; }
        .settings-nav-item.active { background: #e8f4fd; color: var(--primary-color); border-right: 3px solid var(--primary-color); }
        .settings-content { flex: 1; padding: 32px; overflow-y: auto; }
        .settings-section { display: none; }
        .settings-section.active { display: block; }
    </style>
</head>
<body>
    <div class="app-container">
        <aside class="sidebar" id="sidebar-container"></aside>
        <main class="main-content">
            <header class="header" id="header-container"></header>
            <div class="settings-layout">
                <div class="settings-nav">
                    <div class="settings-nav-item active" onclick="switchSetting('departments')">部门管理</div>
                    <div class="settings-nav-item" onclick="switchSetting('interviewers')">人员管理</div>
                    <div class="settings-nav-item" onclick="switchSetting('locations')">面试地点</div>
                    <div class="settings-nav-item" onclick="switchSetting('processes')">面试流程</div>
                    <div class="settings-nav-item" onclick="switchSetting('categories')">职位类别</div>
                </div>
                <div class="settings-content">
                    <div id="sec-departments" class="settings-section active">
                        <h2>部门管理</h2>
                        <button class="btn btn-primary" onclick="addDict('departments')">新增部门</button>
                        <table class="table-container" style="margin-top: 16px;">
                            <thead><tr><th>名称</th><th>操作</th></tr></thead>
                            <tbody id="tb-departments"></tbody>
                        </table>
                    </div>
                    <!-- 其他占位 -->
                    <div id="sec-interviewers" class="settings-section">
                        <h2>人员管理</h2>
                        <button class="btn btn-primary" onclick="addDict('interviewers')">新增人员</button>
                        <table class="table-container" style="margin-top: 16px;">
                            <thead><tr><th>名称</th><th>角色</th><th>操作</th></tr></thead>
                            <tbody id="tb-interviewers"></tbody>
                        </table>
                    </div>
                    <div id="sec-locations" class="settings-section">
                        <h2>面试地点</h2>
                        <button class="btn btn-primary" onclick="addDict('locations')">新增地点</button>
                        <table class="table-container" style="margin-top: 16px;">
                            <thead><tr><th>名称</th><th>类型</th><th>操作</th></tr></thead>
                            <tbody id="tb-locations"></tbody>
                        </table>
                    </div>
                    <div id="sec-processes" class="settings-section">
                        <h2>面试流程</h2>
                        <button class="btn btn-primary" onclick="addDict('interview-processes')">新增流程</button>
                        <table class="table-container" style="margin-top: 16px;">
                            <thead><tr><th>名称</th><th>流转节点</th><th>操作</th></tr></thead>
                            <tbody id="tb-processes"></tbody>
                        </table>
                    </div>
                    <div id="sec-categories" class="settings-section">
                        <h2>职位类别</h2>
                        <button class="btn btn-primary" onclick="addDict('categories')">新增类别</button>
                        <table class="table-container" style="margin-top: 16px;">
                            <thead><tr><th>名称</th><th>操作</th></tr></thead>
                            <tbody id="tb-categories"></tbody>
                        </table>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <script src="assets/js/app.js?v=7"></script>
    <script>
        document.addEventListener("DOMContentLoaded", () => {
            renderSidebar('settings');
            renderHeader();
            loadAllDicts();
        });

        function switchSetting(type) {
            document.querySelectorAll('.settings-nav-item').forEach(el => el.classList.remove('active'));
            event.target.classList.add('active');
            document.querySelectorAll('.settings-section').forEach(el => el.classList.remove('active'));
            document.getElementById('sec-' + type).classList.add('active');
        }

        async function loadAllDicts() {
            // Fetch and render Departments
            fetch('/api/settings/departments').then(r => r.json()).then(data => {
                document.getElementById('tb-departments').innerHTML = data.map(d => `<tr><td>${d.name}</td><td><button class="btn" style="color:red;" onclick="deleteDict('departments', ${d.id})">删除</button></td></tr>`).join('');
            });
            // Fetch Interviewers
            fetch('/api/settings/interviewers').then(r => r.json()).then(data => {
                document.getElementById('tb-interviewers').innerHTML = data.map(d => `<tr><td>${d.name}</td><td>${d.role_type}</td><td><button class="btn" style="color:red;" onclick="deleteDict('interviewers', ${d.id})">删除</button></td></tr>`).join('');
            });
            // Fetch Locations
            fetch('/api/settings/locations').then(r => r.json()).then(data => {
                document.getElementById('tb-locations').innerHTML = data.map(d => `<tr><td>${d.name}</td><td>${d.type}</td><td><button class="btn" style="color:red;" onclick="deleteDict('locations', ${d.id})">删除</button></td></tr>`).join('');
            });
            // Fetch Processes
            fetch('/api/settings/interview-processes').then(r => r.json()).then(data => {
                document.getElementById('tb-processes').innerHTML = data.map(d => `<tr><td>${d.name}</td><td>${d.stages}</td><td><button class="btn" style="color:red;" onclick="deleteDict('interview-processes', ${d.id})">删除</button></td></tr>`).join('');
            });
            // Fetch Categories
            fetch('/api/settings/categories').then(r => r.json()).then(data => {
                document.getElementById('tb-categories').innerHTML = data.map(d => `<tr><td>${d.name}</td><td><button class="btn" style="color:red;" onclick="deleteDict('categories', ${d.id})">删除</button></td></tr>`).join('');
            });
        }

        async function addDict(type) {
            let name = prompt("请输入名称:");
            if (!name) return;
            let payload = { name };
            if (type === 'interviewers') {
                payload.role_type = prompt("请输入角色 (Manager, HR, Interviewer):", "Manager");
            } else if (type === 'locations') {
                payload.type = prompt("请输入类型 (线上, 线下):", "线下");
            } else if (type === 'interview-processes') {
                payload.stages = prompt("请输入流转节点 (逗号分隔):", "初筛,一面,HR面");
            }
            
            await fetch(`/api/settings/${type}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            loadAllDicts();
        }

        async function deleteDict(type, id) {
            if(!confirm("确认删除？")) return;
            await fetch(`/api/settings/${type}/${id}`, { method: 'DELETE' });
            loadAllDicts();
        }
    </script>
</body>
</html>
```

- [ ] **Step 4: Commit**
```bash
git add assets/js/app.js main.py settings.html
git commit -m "feat: implement settings page with basic UI and sidebar navigation"
```

---

### Task 4: 动态加载：修改 add-job.html 选项

**Files:**
- Modify: `add-job.html`

- [ ] **Step 1: 移除 HTML 中的硬编码选项**
在 `add-job.html`，找到 `jobDepartment`, `jobLocation`, `jobHrName` 这几个下拉框，只保留默认的 disabled option，移除所有硬编码 `<option>`。
找到 Segmented Control 对应的 `jobCategory` 和 `jobInterviewProcess` (注：之前设计中将 category 变为了 segmented_control，为了兼容 API 拉取的动态数量，我们需要在 JS 里清空并动态重构，或改回下拉框。为保持极简，将 `jobCategory` 改为从 API 渲染 Segmented Item)。

```html
<!-- 对于 jobDepartment -->
                                <select id="jobDepartment" required>
                                    <option value="" disabled selected>加载中...</option>
                                </select>
<!-- 对于 jobLocation -->
                                <select id="jobLocation" required>
                                    <option value="" disabled selected>加载中...</option>
                                </select>
<!-- 对于 jobHrName -->
                                <select id="jobHrName" required>
                                    <option value="" disabled selected>加载中...</option>
                                </select>
```

- [ ] **Step 2: 在 `DOMContentLoaded` 中动态拉取并渲染**
在 `add-job.html` 的 script 区域中添加逻辑：

```javascript
        document.addEventListener("DOMContentLoaded", async () => {
            renderSidebar('jobs');
            renderHeader();
            
            // 动态加载字典
            await loadDictionaries();

            // 在字典加载完成后，再渲染自定义样式
            setupCustomSelects();
            setupSegmentedControls();
            
            quill = new Quill('#editor-container', { theme: 'snow', placeholder: '...' });
        });

        async function loadDictionaries() {
            // 部门
            const deps = await fetch('/api/settings/departments').then(r=>r.json());
            const depSelect = document.getElementById('jobDepartment');
            depSelect.innerHTML = '<option value="" disabled selected>请选择所属部门</option>' + deps.map(d => `<option value="${d.name}">${d.name}</option>`).join('');

            // 地点
            const locs = await fetch('/api/settings/locations').then(r=>r.json());
            const locSelect = document.getElementById('jobLocation');
            locSelect.innerHTML = '<option value="" disabled selected>请选择工作地点</option>' + locs.map(d => `<option value="${d.name}">${d.name}</option>`).join('');

            // 面试官(HR)
            const hrs = await fetch('/api/settings/interviewers').then(r=>r.json());
            const hrSelect = document.getElementById('jobHrName');
            hrSelect.innerHTML = '<option value="" disabled selected>请选择负责人</option>' + hrs.map(d => `<option value="${d.name}">${d.name}</option>`).join('');

            // 职位类别 (Segmented Control)
            const cats = await fetch('/api/settings/categories').then(r=>r.json());
            const catContainer = document.querySelector('.segmented-control[data-target="jobCategory"]');
            catContainer.innerHTML = cats.map(c => `<div class="segmented-item" data-value="${c.name}">${c.name}</div>`).join('');
            
            // 面试流程 (若界面上有) -> 当前是在前端写死的吗？若没有可略。
        }
```

- [ ] **Step 3: 调整 Segmented Controls 初始化问题**
因为我们在 JS 里重写了 `.segmented-control[data-target="jobCategory"]` 的 innerHTML，所以确保 `setupSegmentedControls()` 能够正常挂载事件（因为我们在 `loadDictionaries` await 之后才调用的，所以没问题）。

- [ ] **Step 4: Commit**
```bash
git add add-job.html
git commit -m "feat: dynamically load dictionary data for job creation form"
```

---

### Task 5: 动态加载：修改 candidates 和 details 页面弹窗选项

**Files:**
- Modify: `candidate-detail.html`
- Modify: `candidates.html`

- [ ] **Step 1: 修改 Detail 推荐和安排面试**
在 `candidate-detail.html` 中找到 `recommend-manager-select` 的内容。将其清空并在页面加载时从 `/api/settings/interviewers` 获取 `Manager` 角色的数据填充。
（注意由于在两个页面都会用到 schedule 抽屉，如果有的话也动态更新 `drawerInterviewerSelect`）。

```javascript
        async function loadDictionariesForDetail() {
            try {
                const interviewers = await fetch('/api/settings/interviewers').then(r=>r.json());
                const managers = interviewers.filter(i => i.role_type === 'Manager');
                
                const recSelect = document.getElementById('recommend-manager-select');
                if (recSelect) {
                    recSelect.innerHTML = managers.map(m => `<option value="${m.name}">${m.name}</option>`).join('');
                }
                
                // 如果存在抽屉相关的选项
                const drawSelect = document.getElementById('drawerInterviewerSelect');
                if (drawSelect) {
                    drawSelect.innerHTML = '<option value="" disabled selected>请选择面试官</option>' + interviewers.map(i => `<option value="${i.name}">${i.name}</option>`).join('');
                }
            } catch(e) { console.error('Failed to load dicts', e); }
        }
        
        document.addEventListener("DOMContentLoaded", () => {
            renderSidebar('candidates');
            renderHeader();
            loadDictionariesForDetail();
            loadDetail();
        });
```

- [ ] **Step 2: 修改 Candidates 安排面试**
在 `candidates.html` 同样补充 `loadDictionariesForList`。

```javascript
        async function loadDictionariesForList() {
            try {
                const interviewers = await fetch('/api/settings/interviewers').then(r=>r.json());
                const drawSelect = document.getElementById('drawerInterviewerSelect');
                if (drawSelect) {
                    drawSelect.innerHTML = '<option value="" disabled selected>请选择面试官</option>' + interviewers.map(i => `<option value="${i.name}">${i.name}</option>`).join('');
                }
            } catch(e) {}
        }
        // Call this in DOMContentLoaded
```

- [ ] **Step 3: Commit**
```bash
git add candidate-detail.html candidates.html
git commit -m "feat: dynamically load interviewers for recommendation and scheduling flows"
```
