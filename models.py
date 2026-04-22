from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    job = Column(String(100))
    stage = Column(String(50), default="新投递")
    exp = Column(String(100))
    email = Column(String(255))
    skills = Column(JSON)
    raw_text = Column(Text)
    ai_summary = Column(Text)
    ai_analysis = Column(Text)
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
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)