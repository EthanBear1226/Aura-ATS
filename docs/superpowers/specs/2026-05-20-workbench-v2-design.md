# Aura 工作台 2.0 (The Command Center) 设计文档

## 1. 概述 (Overview)
Aura 工作台 2.0 旨在将现有的静态数据展示升级为“以任务为中心、千人千面、极简 Apple 风格”的招聘指挥中心。它将根据登录账号的角色（HR、面试官、管理员）动态呈现核心待办、实时动态与关键指标。

## 2. 核心目标 (Core Goals)
- **身份感知 (Identity Awareness)**：每个用户登录后仅看到与其相关的任务。
- **辅助决策 (Decision Support)**：通过 AI 评分置顶、面试冲突提醒等“非侵入式自动化”提升处理效能。
- **极致美学 (Aesthetic Excellence)**：全面采用 Apple 风格的 Bento Box (便当盒) 布局、磨砂玻璃材质与非线性动效。

## 3. 技术规格 (Technical Specifications)

### 3.1 后端 API (FastAPI)
- **Endpoint**: `GET /api/workbench/dashboard`
- **逻辑**: 
  - 从 `localStorage`/Session 获取当前 `user_id` 和 `role`。
  - **面试官角色**: 聚合 `Interview` 表中 `interviewer_id` 匹配的当日/未来面试。
  - **HR/管理员角色**: 聚合所负责职位的简历待筛选数、高匹配度 (Score > 85) 简历预警、超时的面试评价。
  - **公共统计**: 返回关键招聘漏斗数据（进行的职位、活跃候选人、转化率等）。

### 3.2 前端布局 (HTML/CSS)
- **布局容器**: 使用 `display: grid` 和 `grid-template-columns: 2fr 1fr` 的 Bento Box 结构。
- **视觉风格**:
  - `background: rgba(255, 255, 255, 0.7)` + `backdrop-filter: blur(20px)` 实现磨砂玻璃卡片。
  - `border-radius: 20px` 的大圆角设计。
  - `box-shadow: 0 4px 24px rgba(0,0,0,0.04)` 的微扩散阴影。
- **动效**: 使用 `cubic-bezier(0.4, 0, 0.2, 1)` 实现平滑的悬停缩放与列表载入动画。

## 4. 核心功能组件 (Key Components)

### 4.1 即时待办 (Actionable Feed)
- **面试雷达**: 展示最近一场面试，支持一键进入详情或评价。
- **智能预警**: 置顶展示 AI 评分极高且未处理的候选人。
- **状态感知**: 面试结束后自动在工作台生成“待写评价”磁贴。

### 4.2 招聘动态 (Live Stream)
- 实时展示团队协作动态（如：某面试官提交了反馈、某职位已招满）。

### 4.3 数据统计 (Metric Tiles)
- 环形图或进度条展示本月招聘达成率。

## 5. 暂不涉及 (Out of Scope)
- **全自动邀约**: 坚持人工决策，系统不自动向候选人发送任何联络信息。
- **第三方日历同步**: 本阶段仅处理内部数据库状态，暂不涉及飞书/Google Calendar 的实时读写（已在 V1.7 完成基础对接，此处指工作台实时同步）。

## 6. 测试与验证 (Verification Plan)
- **多账号验证**: 使用不同角色的账号登录，确认工作台内容完全不同。
- **响应式测试**: 验证在 1920px (Desktop) 和 375px (Mobile) 下布局的伸缩性。
- **性能验证**: 确保 `/api/workbench/dashboard` 的响应时间在 200ms 以内。
