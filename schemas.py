from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class CandidateBase(BaseModel):
    name: str
    job: str
    stage: str
    exp: str
    email: Optional[str] = None
    skills: Optional[List[str]] = []
    raw_text: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_analysis: Optional[str] = None
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