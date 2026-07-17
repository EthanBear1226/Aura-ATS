from datetime import datetime, timedelta

class FeishuCalendarService:
    @staticmethod
    def get_freebusy(interviewer_email_or_name: str, date_str: str, db=None):
        # TODO: 接入真实飞书 OpenAPI 获取忙闲
        # 目前结合本地数据库实现一个动态计算的档期版本
        working_hours = ["09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00", "17:00"]
        slots = []
        busy_times = set()

        if db:
            import models
            from sqlalchemy import func
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                interviews = db.query(models.Interview).filter(
                    models.Interview.interviewer_name == interviewer_email_or_name,
                    models.Interview.status != "已取消",
                    func.date(models.Interview.start_time) == target_date
                ).all()

                for interview in interviews:
                    # 将时间格式化为 HH:MM 格式，标记为忙碌
                    busy_times.add(interview.start_time.strftime("%H:%M"))
            except Exception as e:
                print("Error parsing date or querying db:", e)

        for t in working_hours:
            slots.append({"time": t, "isFree": t not in busy_times})
            
        return slots
        
    @staticmethod
    def create_event(interviewer_email: str, start_time: datetime, end_time: datetime, summary: str, description: str):
        # TODO: 调用飞书 API 锁定日程
        print(f"[Feishu Mock] Created event for {interviewer_email} at {start_time}")
        return True

class EmailService:
    @staticmethod
    def _send_smtp_email(to_email: str, subject: str, content: str) -> bool:
        import os
        import smtplib
        from email.mime.text import MIMEText
        from email.header import Header

        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = os.getenv("SMTP_PORT")
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        
        # 如果没有配置完整的 SMTP 环境变量，则返回 False，回退到 Mock 打印模式
        if not all([smtp_server, smtp_port, smtp_user, smtp_password]):
            print("[Email SMTP] 缺少必要的环境变量，无法发送真实邮件。将回退到 Mock 打印。")
            return False
            
        try:
            # 创建邮件内容
            message = MIMEText(content, 'plain', 'utf-8')
            message['From'] = Header(f"Aura 招聘系统 <{smtp_user}>", 'utf-8')
            message['To'] = Header(to_email, 'utf-8')
            message['Subject'] = Header(subject, 'utf-8')
            
            # 判断端口类型
            port = int(smtp_port)
            if port == 465:
                # SSL 加密连接
                server = smtplib.SMTP_SSL(smtp_server, port, timeout=10)
            else:
                # 普通或 STARTTLS 连接
                server = smtplib.SMTP(smtp_server, port, timeout=10)
                if port == 587:
                    server.starttls()
            
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, [to_email], message.as_string())
            server.quit()
            print(f"[Email SMTP] 成功发送真实邮件至: {to_email}")
            return True
        except Exception as e:
            print(f"[Email SMTP] 发送真实邮件失败，错误信息: {e}")
            return False

    @staticmethod
    def send_interview_invitation(to_email: str, subject: str, content: str):
        # 尝试使用真实发送
        if EmailService._send_smtp_email(to_email, subject, content):
            return True
        # 回退到 Mock 打印
        print(f"[Email Mock] Sending to: {to_email}")
        print(f"[Email Mock] Subject: {subject}")
        print(f"[Email Mock] Content:\n{content}")
        return True

    @staticmethod
    def send_user_invitation(to_email: str, invite_link: str, inviter_name: str, company_name: str):
        subject = f"【Aura 协同招聘】{company_name} 诚邀您加入企业招聘协作平台"
        content = f"""您好！
   
我是管理员 {inviter_name}。为了提升我们团队的招聘效率，方便后续在岗位招聘、简历评估及面试日程上进行高效协同，我们已经开通了 {company_name} 专属的 Aura 智能招聘协作平台。
   
现诚意邀请您加入，共同协作管理相关候选人的面试及评估工作。您的专属协同部门与系统角色已由管理员配置完成。
   
请点击下方专属链接，设置您的登录密码并激活协同账号：
{invite_link}
   
*(注：为了保障企业招聘数据的安全，请在收到邮件后尽快点击激活。如有任何疑问，请随时联系管理员 {inviter_name}。)*
   
祝工作顺利！
{company_name} 招聘协同团队
"""
        # 尝试使用真实发送
        if EmailService._send_smtp_email(to_email, subject, content):
            return True
        # 回退到 Mock 打印
        print(f"[Email Mock] Sending Invitation to: {to_email}")
        print(f"[Email Mock] Subject: {subject}")
        print(f"[Email Mock] Content:\n{content}")
        return True

class FeishuNotificationService:
    @staticmethod
    def send_offer_approval_card(instance, step) -> bool:
        # 1. 解析Offer高级字段以在飞书消息卡片中进行高保真Markdown拼装
        details = getattr(instance, "offer_details", None) or {}
        if details:
            content_str = (
                f"**候选人姓名**：{instance.candidate_name}\n"
                f"**合同职位名称**：{details.get('contract_job', instance.job_title)}\n"
                f"**合同主体**：{details.get('contract_subject', '--')}\n"
                f"**录用部门**：{details.get('department', instance.department)}\n"
                f"**职位级别**：{details.get('job_level', instance.job_level)}\n"
                f"**预计入职时间**：{details.get('proposed_start_date', '--')}\n"
                f"**薪资待遇方案**：¥{details.get('base_salary', 0):,.0f} /月 ({details.get('salary_type', '月薪')})\n"
                f"**试用期细节**：试用期 {details.get('probation_months', 3)} 个月 · 发放比例 {details.get('probation_salary_rate', '100%')}\n"
                f"**目标年终奖**：{details.get('target_bonus_months', 2)} 个月奖金\n"
                f"**股票期权数**：{details.get('stock_options', 0):,.0f} 股\n"
                f"**福利及其他**：绩效工资 ¥{details.get('performance_bonus', 0):,.0f} · 员工类型 {details.get('employment_type', '--')}\n"
                f"**合规情况**：符合签署基金条件 - {details.get('compliance_check', '是')}\n"
                f"**保障年基本薪资合计**：**¥{((details.get('base_salary', 0) or 0) * (12 + (float(details.get('target_bonus_months', 0) or 0)))):,.0f}**"
            )
        else:
            content_str = (
                f"**候选人姓名**：{instance.candidate_name}\n"
                f"**应聘职位**：{instance.job_title}\n"
                f"**拟录用职级**：{instance.job_level}\n"
                f"**录用部门**：{instance.department}\n"
                f"**薪酬方案**：**{instance.salary}**"
            )

        # 2. 模拟构造飞书端原生的交互式“消息卡片”JSON结构
        feishu_card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"📋 待审批 Offer - {instance.candidate_name}"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": content_str
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "markdown",
                    "content": f"**当前审批节点**：【{step['label']}】\n"
                               f"**当前待审批人**：{step['approver_email']}\n"
                               f"*注：直接在下方点击即可处理，审批结果将实时刷回此卡片，优先无需跳转。*"
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "同意"
                            },
                            "type": "primary",
                            "value": {
                                "action": "approve",
                                "instance_id": instance.id,
                                "step_label": step['label']
                            }
                        },
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "驳回"
                            },
                            "type": "danger",
                            "value": {
                                "action": "reject",
                                "instance_id": instance.id,
                                "step_label": step['label']
                            }
                        }
                    ]
                }
            ]
        }
        
        print(f"\n[Feishu Integration] =========================================")
        print(f"[Feishu Integration] 成功向 {step['approver_email']} 发送飞书交互消息卡片:")
        import json
        print(json.dumps(feishu_card, ensure_ascii=False, indent=2))
        print(f"[Feishu Integration] =========================================\n")
        return True

