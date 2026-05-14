from datetime import datetime

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
