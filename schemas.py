from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class CandidateBase(BaseModel):
    name: str
    job: str
    stage: str
    exp: str
    phone: Optional[str] = None
    email: Optional[str] = None
    skills: Optional[List[str]] = []
    raw_text: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_analysis: Optional[str] = None
    match_score: Optional[int] = None
    match_reason: Optional[str] = None
    pdf_path: Optional[str] = None

class CandidateCreate(CandidateBase):
    pass

class CandidateUpdate(BaseModel):
    stage: Optional[str] = None
    operator: Optional[str] = "系统" # Default operator
    details: Optional[str] = None

class CandidateLog(BaseModel):
    id: int
    candidate_id: int
    operator: str
    action: str
    details: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class Candidate(CandidateBase):
    id: int
    created_at: datetime
    updated_at: datetime
    logs: List[CandidateLog] = []

    class Config:
        from_attributes = True

class JobBase(BaseModel):
    title: str
    department: str
    location: str
    status: str = "热招中"
    hr_name: str
    interview_process: str = "标准面试流程"
    description: Optional[str] = None
    job_type: str = "全职"
    category: Optional[str] = None
    experience: str = "不限"
    job_level: Optional[str] = None
    headcount: int = 1
    salary_range: Optional[str] = None
    salary_months: int = 12

class JobCreate(JobBase):
    pass

class JobUpdate(BaseModel):
    status: Optional[str] = None

class Job(JobBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class JobFunnel(BaseModel):
    new: int
    screened: int
    interviewing: int
    offered: int

class JobWithFunnel(Job):
    funnel: JobFunnel