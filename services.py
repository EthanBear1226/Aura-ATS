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
        subject = f"【Aura 灵犀招聘】{inviter_name} 邀请您加入 {company_name} 企业空间"
        content = f"""您好！
   
Aura 智能招聘系统超级管理员 {inviter_name} 邀请您加入 {company_name} 的企业协同空间。
   
请点击以下链接完成您的账户密码设置以激活您的账号：
{invite_link}
   
（该链接长期有效，请妥善保管）
"""
        # 尝试使用真实发送
        if EmailService._send_smtp_email(to_email, subject, content):
            return True
        # 回退到 Mock 打印
        print(f"[Email Mock] Sending Invitation to: {to_email}")
        print(f"[Email Mock] Subject: {subject}")
        print(f"[Email Mock] Content:\n{content}")
        return True

