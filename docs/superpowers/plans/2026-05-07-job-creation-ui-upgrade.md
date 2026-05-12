# 职位发布页 UI 重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重新设计 `add-job.html` 表单，去除原生系统控件痕迹，引入 Apple 风格的胶囊分段控制器和极简下拉框，解决“双箭头”视觉 Bug。

**Architecture:** 完全采用 Vanilla JS 和 CSS。通过 CSS 隐藏原生 Select 并渲染 Segmented Control，利用 JS 处理点击事件与原生数据绑定。保留当前的极简下拉框。

**Tech Stack:** HTML, CSS, Vanilla JS

---

### Task 1: 修复自定义下拉框“双箭头” Bug

**Files:**
- Modify: `add-job.html`

- [ ] **Step 1: 移除原生的下拉框背景**
打开 `add-job.html`，找到 `<style>` 标签内的 `.form-group select` 样式，移除原有的 `background-image` 相关属性，并添加 `appearance: none;`。

```html
<!-- 替换这段 CSS 代码 -->
        .form-group select {
            -webkit-appearance: none;
            -moz-appearance: none;
            appearance: none;
            padding-right: 40px;
        }
```

- [ ] **Step 2: 验证样式变更**
由于这是纯前端样式修改，请使用浏览器打开 `add-job.html`。
Expected: `所属部门`、`工作地点` 等下拉框的右侧仅显示一个箭头，不再有双箭头重叠。

- [ ] **Step 3: Commit**
```bash
git add add-job.html
git commit -m "fix: remove native background-image from select to fix double arrow bug"
```

---

### Task 2: 增加 Segmented Control 的 CSS 样式

**Files:**
- Modify: `add-job.html`

- [ ] **Step 1: 添加 CSS 样式**
在 `add-job.html` 的 `<style>` 标签内的末尾（`/* Quill 编辑器覆写 */` 之前）插入以下样式代码：

```css
        /* Segmented Control Styles */
        .segmented-control {
            display: flex;
            background: #f0f0f5;
            border-radius: 8px;
            padding: 4px;
            gap: 4px;
        }
        .segmented-item {
            flex: 1;
            text-align: center;
            padding: 8px 0;
            font-size: 13px;
            font-weight: 500;
            color: var(--text-secondary);
            cursor: pointer;
            border-radius: 6px;
            transition: all 0.2s ease;
        }
        .segmented-item:hover {
            color: var(--text-primary);
        }
        .segmented-item.active {
            background: white;
            color: var(--primary-color);
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        /* Error state for segmented control */
        .segmented-control.has-error {
            border: 1px solid #FF3B30;
            background: #FFF0F0;
        }
```

- [ ] **Step 2: Commit**
```bash
git add add-job.html
git commit -m "style: add css for segmented controls"
```

---

### Task 3: 将短选项下拉框重构为 Segmented Controls

**Files:**
- Modify: `add-job.html`

- [ ] **Step 1: 替换 HTML 结构**
将 `jobCategory`, `jobType`, `jobExperience`, `jobLevel` 四个原生 `<select>` 替换为 `<input type="hidden">` 和 `.segmented-control` 容器。

```html
<!-- 替换职位类别 -->
                            <div class="form-group">
                                <label>职位类别<span class="required-mark">*</span></label>
                                <input type="hidden" id="jobCategory" required>
                                <div class="segmented-control" data-target="jobCategory">
                                    <div class="segmented-item" data-value="技术/研发">技术/研发</div>
                                    <div class="segmented-item" data-value="产品/设计">产品/设计</div>
                                    <div class="segmented-item" data-value="运营/市场">运营/市场</div>
                                    <div class="segmented-item" data-value="职能/支持">职能/支持</div>
                                </div>
                            </div>
<!-- 替换职位性质 -->
                            <div class="form-group">
                                <label>职位性质</label>
                                <input type="hidden" id="jobType" required value="全职">
                                <div class="segmented-control" data-target="jobType">
                                    <div class="segmented-item active" data-value="全职">全职</div>
                                    <div class="segmented-item" data-value="兼职">兼职</div>
                                    <div class="segmented-item" data-value="实习">实习</div>
                                    <div class="segmented-item" data-value="外包">外包</div>
                                </div>
                            </div>

<!-- 替换工作经验 -->
                            <div class="form-group">
                                <label>工作经验</label>
                                <input type="hidden" id="jobExperience" required value="不限">
                                <div class="segmented-control" data-target="jobExperience">
                                    <div class="segmented-item active" data-value="不限">不限</div>
                                    <div class="segmented-item" data-value="应届生">应届生</div>
                                    <div class="segmented-item" data-value="1-3年">1-3年</div>
                                    <div class="segmented-item" data-value="3-5年">3-5年</div>
                                    <div class="segmented-item" data-value="5-10年">5-10年</div>
                                    <div class="segmented-item" data-value="10年以上">10年以上</div>
                                </div>
                            </div>
<!-- 替换职级 -->
                            <div class="form-group">
                                <label>职级</label>
                                <input type="hidden" id="jobLevel" required>
                                <div class="segmented-control" data-target="jobLevel">
                                    <div class="segmented-item" data-value="初级">初级</div>
                                    <div class="segmented-item" data-value="中级">中级</div>
                                    <div class="segmented-item" data-value="高级">高级</div>
                                    <div class="segmented-item" data-value="资深/专家">资深/专家</div>
                                </div>
                            </div>
```

- [ ] **Step 2: 编写交互 JS 代码**
在 `<script>` 标签内，`setupCustomSelects()` 函数定义的下方，添加 `setupSegmentedControls()` 函数：

```javascript
        function setupSegmentedControls() {
            document.querySelectorAll('.segmented-control').forEach(control => {
                const targetId = control.dataset.target;
                const targetInput = document.getElementById(targetId);
                
                control.querySelectorAll('.segmented-item').forEach(item => {
                    item.addEventListener('click', () => {
                        control.querySelectorAll('.segmented-item').forEach(i => i.classList.remove('active'));
                        item.classList.add('active');
                        targetInput.value = item.dataset.value;
                        control.classList.remove('has-error');
                    });
                });
            });
        }
```

并在 `document.addEventListener("DOMContentLoaded", () => { ... })` 中，紧接着 `setupCustomSelects();` 调用它：

```javascript
            setupCustomSelects();
            setupSegmentedControls();
```

- [ ] **Step 3: Commit**
```bash
git add add-job.html
git commit -m "feat: implement segmented controls for category, type, experience, and level"
```

---

### Task 4: 更新表单验证逻辑

**Files:**
- Modify: `add-job.html`

- [ ] **Step 1: 移除已变更为胶囊的 select 的验证，增加新的胶囊验证逻辑**
在 `createJob()` 函数中，更新必填校验的逻辑。找到 `const requiredSelects = ['jobDepartment', 'jobLocation', 'jobCategory', 'jobHrName'];` 这一段并替换。

```javascript
            const requiredSelects = ['jobDepartment', 'jobLocation', 'jobHrName'];
            requiredSelects.forEach(id => {
                const select = document.getElementById(id);
                if (!select.value) {
                    isValid = false;
                    const wrapper = select.closest('.custom-select-wrapper');
                    if (wrapper) {
                        wrapper.querySelector('.custom-select-trigger').classList.add('has-error');
                    }
                }
            });

            // 验证职位类别 (Segmented Control)
            const categoryInput = document.getElementById('jobCategory');
            if (!categoryInput.value) {
                isValid = false;
                document.querySelector('.segmented-control[data-target="jobCategory"]').classList.add('has-error');
            }

            // 验证职级 (Segmented Control)
            const levelInput = document.getElementById('jobLevel');
            if (!levelInput.value) {
                isValid = false;
                document.querySelector('.segmented-control[data-target="jobLevel"]').classList.add('has-error');
            }
```

- [ ] **Step 2: 测试表单**
使用浏览器打开 `add-job.html`。
1. 直接点击“确认发布”，应看到“职位名称”、“所属部门”、“职位类别”、“薪资”等带有红色高亮提示。
2. 点击“职位类别”的“技术/研发”，高亮提示应消失。
3. 填写其余所有必填项后点击提交，观察控制台是否成功触发 `/api/jobs` 接口请求。

- [ ] **Step 3: Commit**
```bash
git add add-job.html
git commit -m "fix: update validation for segmented controls"
```
