# 系统设置页面与组织架构动态化设计文档

## 1. 目标与背景
目前 Aura ATS 系统中的诸多基础数据（如部门、负责人、地点、面试流程等）多为前端硬编码，无法满足实际业务中灵活调整的需求。
本项目旨在为管理员（Admin / SuperAdmin）提供一个专门的“系统设置”模块，用于动态维护公司的基础组织架构与业务字典，并使各个业务端表单通过 API 获取这些动态数据。

## 2. 核心架构与布局

### 2.1 页面级入口与访问控制
- **入口位置**：左侧边栏的最下方新增一个“⚙️ 系统设置”的导航项。
- **权限控制**：
  - 前端：在渲染侧边栏（`renderSidebar`）时，检查 `localStorage` 中的 `aura_user` 角色。只有 `SuperAdmin` 或 `Admin` 角色的用户可见，普通账号不予体现。

### 2.2 独立设置页面 (`settings.html`)
- **布局设计**：采用经典的“左侧设置菜单 + 右侧内容区”布局。
  - 左侧设置菜单包含以下核心配置字典：
    1. **【部门管理】**：公司组织架构。
    2. **【人员管理】**：管理 HR、面试官、用人经理及其所属部门。
    3. **【办公/面试地点】**：管理物理办公区、会议室或常用的线上会议形式（如：北京总部、腾讯会议）。
    4. **【面试流程模板】**：预设不同岗位的面试轮次（如：“常规技术面(初筛->一面->HR面)”、“高管特批流程”等）。
    5. **【职位类别】**：管理公司开放的职位族（如：技术/研发、产品/设计等）。
  - 右侧内容区为主数据表格，展示已有条目，并在顶部提供“新增/停用”等维护操作。

## 3. 数据模型与 API 设计

### 3.1 数据库表 (SQLAlchemy)
- **`Department` 表**：`id`, `name`, `status`, `created_at`
- **`Interviewer` (人员) 表**：`id`, `name`, `role_type` (HR/Manager/Interviewer), `department_id`, `created_at`
- **`Location` (地点) 表**：`id`, `name`, `type` (线上/线下), `created_at`
- **`InterviewProcess` (面试流程) 表**：`id`, `name`, `stages` (描述文本或 JSON), `created_at`
- **`JobCategory` (职位类别) 表**：`id`, `name`, `created_at`

### 3.2 接口设计
为上述 5 张字典表分别提供标准的 RESTful API (`GET`, `POST`, `DELETE`)，如 `/api/settings/departments`, `/api/settings/locations` 等。

## 4. 业务端联动影响范围
一旦基础配置完成，前端的表单交互将全面动态化：
- **发布新职位 (`add-job.html`) & 职位列表弹窗**：
  - 【所属部门】从 `GET /api/settings/departments` 获取。
  - 【工作地点】从 `GET /api/settings/locations` 获取。
  - 【职位类别】从 `GET /api/settings/categories` 获取（替代硬编码的胶囊按钮数据）。
  - 【面试流程】从 `GET /api/settings/interview-processes` 获取。
- **候选人流转 & 面试安排 (`candidate-detail.html`, `candidates.html`)**：
  - 【推荐给用人部门】弹窗中的“用人经理”下拉框从 `GET /api/settings/interviewers` 动态拉取。
  - 【安排面试】抽屉中的面试官和面试地点，同样从对应 API 动态加载。

## 5. 实施边界
- 界面使用现有的全局 CSS (`styles.css`)，保持响应式特性。
- 修改并填充 `seed_data.py`，预置初始的基础字典数据，确保线上旧系统平滑升级后依然有基础选项可用。
