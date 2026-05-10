from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    job = Column(String(100))
    stage = Column(String(50), default="初筛")
    exp = Column(String(100))
    phone = Column(String(50))
    email = Column(String(255))
    skills = Column(JSON)
    raw_text = Column(Text)
    ai_summary = Column(Text)
    ai_analysis = Column(Text)
    match_score = Column(Integer, nullable=True) # 0-100 系统推荐匹配分
    match_reason = Column(Text, nullable=True) # 匹配维度点评
    pdf_path = Column(String(255))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    logs = relationship("CandidateLog", back_populates="candidate", cascade="all, delete-orphan", order_by="desc(CandidateLog.created_at)")

class CandidateLog(Base):
    __tablename__ = "candidate_logs"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), index=True)
    operator = Column(String(100)) # The user who performed the action
    action = Column(String(200))   # Describe the action (e.g., "入库成功", "状态推进至: 初筛")
    details = Column(Text, nullable=True) # Optional details
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    candidate = relationship("Candidate", back_populates="logs")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), index=True)
    department = Column(String(100))
    location = Column(String(100))
    status = Column(String(50), default="热招中") # 热招中 / 已停招
    hr_name = Column(String(50))
    interview_process = Column(String(200), default="标准面试流程")
    description = Column(Text, nullable=True) # 富文本职位介绍
    job_type = Column(String(50), default="全职") # 职位性质
    category = Column(String(100), nullable=True) # 职位类别
    experience = Column(String(50), default="不限") # 工作经验
    job_level = Column(String(50), nullable=True) # 职级
    headcount = Column(Integer, default=1) # 招聘人数
    salary_range = Column(String(50), nullable=True) # 薪资区间
    salary_months = Column(Integer, default=12) # 薪资月数
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

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