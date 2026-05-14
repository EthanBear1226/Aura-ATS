# 面试安排与协作反馈深度化设计文档

## 1. 目标与背景
当前的“面试安排”模块仅为前端 Mock 演示。本设计旨在将其升级为具备真实协作能力的业务模块。
核心目标包括：基于真实邮箱发送邀约（支持模板）、预留并定义飞书（Feishu）日历协作接口以实现档期同步与锁定、建立独立且支持自定义的面试评价体系（评价与阶段流转解耦）。

## 2. 核心架构与模块规划

### 2.1 基础配置层 (System Settings 扩充)
在系统设置中新增两大配置项，赋予业务极大的灵活性：
- **【邮件模板配置】**：
  - 允许管理员配置发送给候选人的邮件标题和正文。
  - 支持变量插值，如：`{candidate_name}`, `{job_title}`, `{interview_time}`, `{location}`。
- **【面试评价表配置】**：
  - 默认提供“纯文本评价”模板。
  - 支持未来扩展结构化打分项。目前只需支持定义默认的提示文本或问题大纲。

### 2.2 核心业务流 (Scheduling & Notification)
- **档期判断 (飞书接口预留)**：
  - 抽象出 `FeishuCalendarService` 类。
  - `get_freebusy(interviewer_email, date)`: 目前返回 mock 数据，未来接入飞书 OpenAPI 获取真实忙闲。
- **发送邀约**：
  - 候选人端：调用真实 SMTP 服务向简历解析出的 Email 发送套用模板后的 HTML 邮件。
  - 面试官端：同样发送提醒邮件，并调用 `FeishuCalendarService.create_event(...)` 预留接口锁定飞书日程。

### 2.3 反馈闭环 (Interview Feedback)
- 面试官在看板或详情页点击对应面试，弹出【填写评价】模态框。
- 评价字段：
  1. 结论：满意 / 待定 / 不满意
  2. 评价内容：结合评价表模板的富文本或长文本。
- **解耦逻辑**：提交评价后，只更新面试记录本身的状态和反馈数据，**绝对不自动改变**候选人的招聘阶段（Stage），由 HR 结合评价人工决定后续流转。

## 3. 数据模型设计 (SQLAlchemy)

- **`Interview` (面试记录表)**:
  - `id`: Integer
  - `candidate_id`: Integer (FK)
  - `interviewer_id`: Integer (FK)
  - `job_title`: String
  - `start_time`: DateTime
  - `end_time`: DateTime
  - `location`: String
  - `status`: String (已安排, 已完成, 已取消)
  - `feedback_result`: String (满意, 待定, 不满意)
  - `feedback_text`: Text
  - `created_at`: DateTime

- **`EmailTemplate` & `FeedbackTemplate` (设置表)**:
  - 为了极简实现，可以在数据库中建立两张小表，或者目前直接以单独的表设计：`id`, `name`, `content`。

## 4. UI/UX 交互升级
- **安排面试抽屉**：
  - 加载真实候选人数据与邮箱。
  - 动态渲染从“飞书预留接口”获取的时间块。
  - 提交时显示“发送邀约中...”的加载状态。
- **面试日程看板 (`interviews.html`)**：
  - 移除假数据，真实读取 `Interview` 表，按状态或日期归类。
  - 卡片上增加【填写评价】和【查看评价】的明显入口。

## 5. 实施边界
- 邮件发送环节，开发阶段若无真实的 SMTP 账号密码，将使用控制台打印或捕获模拟发送，保证代码逻辑 100% 正确且随时可用。
- 飞书接口层只写好 Python 的 Class 封装和函数签名，内部直接返回可用/成功的 Mock 响应，等待后续填入 Feishu App ID 和 Secret。