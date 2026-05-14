# 面试安排与协作反馈深度化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将面试安排升级为真实的业务模块，包含飞书日历接口预留、真实的邮件邀约发送以及独立的面试评价体系。

**Architecture:** 后端增加 `Interview`, `EmailTemplate`, `FeedbackTemplate` 模型及对应的 CRUD API。抽象 `services.py` 处理邮件发送和飞书 API 交互。前端重构 `interviews.html` 和 `candidate-detail.html` 的面试安排抽屉与看板，对接真实数据。

**Tech Stack:** Python (FastAPI, SQLAlchemy), HTML, CSS, Vanilla JS

---

### Task 1: 数据库模型与 Schema 扩展

**Files:**
- Modify: `models.py`
- Modify: `schemas.py`
- Modify: `seed_data.py`

- [ ] **Step 1: 在 `models.py` 中新增模型**
添加 `EmailTemplate`, `FeedbackTemplate` 和 `Interview` 模型。

```python
class EmailTemplate(Base):
    __tablename__ = "email_templates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    subject = Column(String(200))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class FeedbackTemplate(Base):
    __tablename__ = "feedback_templates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Interview(Base):
    __tablename__ = "interviews"
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"))
    interviewer_name = Column(String(100))
    job_title = Column(String(100))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    location = Column(String(100))
    status = Column(String(50), default="已安排") # 已安排, 已完成, 已取消
    feedback_result = Column(String(50), nullable=True) # 满意, 待定, 不满意
    feedback_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    candidate = relationship("Candidate")
```

- [ ] **Step 2: 在 `schemas.py` 中新增 Schema**
为上述模型创建对应的 Pydantic schemas。

```python
class EmailTemplateCreate(BaseModel):
    name: str
    subject: str
    content: str
class EmailTemplate(EmailTemplateCreate):
    id: int
    class Config: from_attributes = True

class FeedbackTemplateCreate(BaseModel):
    name: str
    content: str
class FeedbackTemplate(FeedbackTemplateCreate):
    id: int
    class Config: from_attributes = True

class InterviewCreate(BaseModel):
    candidate_id: int
    interviewer_name: str
    job_title: str
    start_time: datetime
    end_time: datetime
    location: str

class InterviewUpdateFeedback(BaseModel):
    feedback_result: str
    feedback_text: str

class Interview(InterviewCreate):
    id: int
    status: str
    feedback_result: Optional[str] = None
    feedback_text: Optional[str] = None
    created_at: datetime
    candidate: Optional[CandidateBase] = None
    class Config: from_attributes = True
```

- [ ] **Step 3: 修改 `seed_data.py`**
在 `seed_dicts()` 中增加初始化默认的邮件模板和评价模板。

```python
    if db.query(models.EmailTemplate).count() == 0:
        db.add(models.EmailTemplate(name="默认面试邀约", subject="Aura ATS 面试邀请 - {job_title}", content="您好 {candidate_name}，\n\n诚挚邀请您参加 {job_title} 的面试。\n时间：{interview_time}\n地点：{location}\n\n期待您的回复！"))
        db.commit()

    if db.query(models.FeedbackTemplate).count() == 0:
        db.add(models.FeedbackTemplate(name="标准评价表", content="1. 专业技能匹配度：\n2. 沟通表达能力：\n3. 综合潜质评估：\n"))
        db.commit()
```

- [ ] **Step 4: Commit**
```bash
git add models.py schemas.py seed_data.py
git commit -m "feat: add models and schemas for interviews, email and feedback templates"
```

---

### Task 2: 后端协作服务与 API 实现

**Files:**
- Create: `services.py`
- Modify: `main.py`

- [ ] **Step 1: 创建 `services.py` 预留接口**
创建 `services.py`，封装飞书日历和邮件发送的逻辑。

```python
from datetime import datetime, timedelta

class FeishuCalendarService:
    @staticmethod
    def get_freebusy(interviewer_email: str, date: str):
        # TODO: 接入真实飞书 OpenAPI 获取忙闲
        # 目前返回 Mock 的空闲时间段 (9:00, 10:00, 14:00, 15:00, 16:00 等)
        return [
            {"time": "09:00", "isFree": True},
            {"time": "10:00", "isFree": False},
            {"time": "11:00", "isFree": True},
            {"time": "14:00", "isFree": True},
            {"time": "15:00", "isFree": True},
            {"time": "16:00", "isFree": False},
        ]
        
    @staticmethod
    def create_event(interviewer_email: str, start_time: datetime, end_time: datetime, summary: str, description: str):
        # TODO: 调用飞书 API 锁定日程
        print(f"[Feishu Mock] Created event for {interviewer_email} at {start_time}")
        return True

class EmailService:
    @staticmethod
    def send_interview_invitation(to_email: str, subject: str, content: str):
        # TODO: 使用 smtplib 或第三方服务真实发送邮件
        print(f"[Email Mock] Sending to: {to_email}")
        print(f"[Email Mock] Subject: {subject}")
        print(f"[Email Mock] Content:\n{content}")
        return True
```

- [ ] **Step 2: 在 `main.py` 增加 API 接口**
在 `main.py` 中引入 `services`，并新增以下接口：
- `GET /api/settings/email-templates`
- `GET /api/settings/feedback-templates`
- `GET /api/calendar/freebusy` (传入 interviewer 和 date)
- `POST /api/interviews` (创建面试，同时触发发邮件和飞书建日程)
- `GET /api/interviews`
- `PATCH /api/interviews/{interview_id}/feedback`

*注意：`POST /api/interviews` 的逻辑中需要查询 `EmailTemplate` 替换 `{candidate_name}` 等变量，并调用 `EmailService.send_interview_invitation` 和 `FeishuCalendarService.create_event`。*

- [ ] **Step 3: Commit**
```bash
git add services.py main.py
git commit -m "feat: implement interview APIs, email and feishu service stubs"
```

---

### Task 3: 系统设置页面 UI 扩充

**Files:**
- Modify: `settings.html`

- [ ] **Step 1: 增加邮件和评价模板的侧边栏菜单**
在 `.settings-nav` 中追加：
```html
<div class="settings-nav-item" onclick="switchSetting('email-templates', event)">📧 邮件模板</div>
<div class="settings-nav-item" onclick="switchSetting('feedback-templates', event)">📝 评价模板</div>
```

- [ ] **Step 2: 增加对应的内容区域**
添加 `id="sec-email-templates"` 和 `id="sec-feedback-templates"`。

- [ ] **Step 3: 完善 `loadAllDicts` 和渲染逻辑**
由于模板包含大量文本，表格列除了 `名称`，可以加一列 `操作`。点击“查看/编辑”时，可以通过扩展 `DictModal` 或新模态框展示大文本输入框。为简单起见，初始可只支持查看和删除。

- [ ] **Step 4: Commit**
```bash
git add settings.html
git commit -m "feat: add email and feedback templates to system settings"
```

---

### Task 4: 候选人详情页：真实安排面试抽屉集成

**Files:**
- Modify: `candidate-detail.html`

- [ ] **Step 1: 动态渲染飞书档期**
在 `drawerInterviewerSelect` 或 `drawerInterviewDate` 改变时，调用 `/api/calendar/freebusy`。

```javascript
        async function loadDrawerAvailability() {
            const date = document.getElementById('drawerInterviewDate').value;
            const interviewer = document.getElementById('drawerInterviewerSelect').value;
            if (!date || !interviewer) return;
            
            try {
                const response = await fetch(`/api/calendar/freebusy?interviewer=${interviewer}&date=${date}`);
                const slots = await response.json();
                
                const container = document.getElementById('drawerAvailabilityBlocks');
                container.innerHTML = slots.map((slot, index) => {
                    const isFree = slot.isFree;
                    // 生成之前的单选框 HTML
                    return `...`; // 保持原有的渲染逻辑，但基于接口返回的 slot.time 和 slot.isFree
                }).join('');
            } catch(e) {}
        }
```

- [ ] **Step 2: 提交面试表单**
修改 `submitDrawerSchedule()`，向 `POST /api/interviews` 提交数据。包括 `candidate_id`，选中的 `start_time` 等。
提交成功后，提示“邀约已发送，日程已锁定”。

- [ ] **Step 3: Commit**
```bash
git add candidate-detail.html
git commit -m "feat: integrate real interview scheduling drawer with backend APIs"
```

---

### Task 5: 面试日程看板：真实数据加载与评价反馈

**Files:**
- Modify: `interviews.html`

- [ ] **Step 1: 加载真实的 Interviews 数据**
在 `interviews.html` 中，调用 `GET /api/interviews`。按 `status` 分类渲染到不同的 Kanban Column 中（如“今日面试”、“待评价”、“已完成”）。

- [ ] **Step 2: 实现【填写评价】模态框**
添加一个隐藏的 Modal：
```html
<div class="modal-overlay" id="feedbackModal">
    <div class="modal-card">
        <h2>面试评价反馈</h2>
        <div class="form-group">
            <label>面试结论</label>
            <select id="feedbackResult" class="form-control"><option>满意</option><option>待定</option><option>不满意</option></select>
        </div>
        <div class="form-group">
            <label>详细评价</label>
            <textarea id="feedbackText" class="form-control" style="height:150px;"></textarea>
        </div>
        <button class="btn btn-primary" onclick="submitFeedback()">提交评价</button>
    </div>
</div>
```
当点击某卡片的【填写评价】时，先请求 `/api/settings/feedback-templates` 拿默认模板填入 `feedbackText`，打开 Modal。

- [ ] **Step 3: 提交评价逻辑**
调用 `PATCH /api/interviews/{id}/feedback`，提交后刷新看板。

- [ ] **Step 4: Commit**
```bash
git add interviews.html
git commit -m "feat: render real interviews kanban and add interview feedback modal"
```
