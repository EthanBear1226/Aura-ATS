from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from database import Base
import datetime

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    job = Column(String(100))
    stage = Column(String(50), default="新投递")
    exp = Column(String(100))
    skills = Column(JSON)
    raw_text = Column(Text)
    pdf_path = Column(String(255))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)