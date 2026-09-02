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
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    exp: Optional[str] = None
    job: Optional[str] = None

class CandidateLog(BaseModel):
    id: int
    candidate_id: int
    operator: str
    action: str
    details: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class JobApplicationBase(BaseModel):
    id: int
    candidate_id: int
    job_title: str
    stage: str
    pdf_path: str
    created_at: datetime

    class Config:
        from_attributes = True

class Candidate(CandidateBase):
    id: int
    created_at: datetime
    updated_at: datetime
    logs: List[CandidateLog] = []
    applications: List[JobApplicationBase] = []

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

class DictItemBase(BaseModel):
    name: str

class DepartmentCreate(DictItemBase):
    parent_id: Optional[int] = None

class Department(DictItemBase):
    id: int
    parent_id: Optional[int] = None
    status: str
    class Config: from_attributes = True

class InterviewerCreate(DictItemBase):
    role_type: str
    department_id: Optional[int] = None
class Interviewer(InterviewerCreate):
    id: int
    class Config: from_attributes = True

class LocationCreate(DictItemBase):
    type: str = "线下"
class Location(LocationCreate):
    id: int
    class Config: from_attributes = True

class InterviewProcessCreate(DictItemBase):
    stages: str
class InterviewProcess(InterviewProcessCreate):
    id: int
    class Config: from_attributes = True

class JobCategoryCreate(DictItemBase):
    pass
class JobCategory(DictItemBase):
    id: int
    class Config: from_attributes = True

class EmailTemplateCreate(BaseModel):
    name: str
    subject: str
    content: str
class EmailTemplate(EmailTemplateCreate):
    id: int
    class Config: from_attributes = True

class FeedbackTemplateCreate(BaseModel):
    name: str
    content: str
class FeedbackTemplate(FeedbackTemplateCreate):
    id: int
    class Config: from_attributes = True

class InterviewCreate(BaseModel):
    candidate_id: int
    interviewer_name: str
    job_title: str
    start_time: datetime
    end_time: datetime
    location: str

class InterviewUpdateFeedback(BaseModel):
    feedback_result: str
    feedback_text: str

class Interview(InterviewCreate):
    id: int
    status: str
    feedback_result: Optional[str] = None
    feedback_text: Optional[str] = None
    created_at: datetime
    candidate: Optional[CandidateBase] = None
    class Config: from_attributes = True

# --- Workbench Dashboard Schemas ---

class DashboardStat(BaseModel):
    label: str
    value: int
    change: str
    icon: str

class DashboardTodo(BaseModel):
    id: int
    type: str # 'interview' or 'resume_alert'
    title: str
    time: str
    status: str
    candidate_id: Optional[int] = None

class DashboardActivity(BaseModel):
    id: int
    content: str
    time: str
    icon: Optional[str] = None
    color: Optional[str] = None
    candidate_id: Optional[int] = None

class DashboardSummary(BaseModel):
    stats: List[DashboardStat]
    todos: List[DashboardTodo]
    activities: List[DashboardActivity]

# --- Auth Schemas ---

class UserCreate(BaseModel):
    company: Optional[str] = None
    email: str
    password: str
    name: str
    role: Optional[str] = "Admin"

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    company: Optional[str] = None
    email: str
    name: str
    role: str

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class UserInvitationCreate(BaseModel):
    email: str
    name: str
    department: Optional[str] = None
    role: str

class UserInvitationResponse(BaseModel):
    id: int
    email: str
    name: str
    department: Optional[str] = None
    role: str
    token: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class RegisterByInvite(BaseModel):
    token: str
    password: str
    name: str

class SystemTaskResponse(BaseModel):
    id: int
    title: str
    content: Optional[str] = None
    status: str
    task_type: str
    candidate_id: Optional[int] = None
    created_at: datetime
    candidate: Optional[CandidateBase] = None

    class Config:
        from_attributes = True

class CandidateScreenRequest(BaseModel):
    action: str  # "pass" / "fail"

class UserLoginLogResponse(BaseModel):
    id: int
    email: str
    login_time: datetime
    is_online: bool

    class Config:
        from_attributes = True

class OfferApprovalRuleStep(BaseModel):
    label: str
    approver_email: str

class OfferApprovalRuleCreate(BaseModel):
    name: str
    department: Optional[str] = None
    job_level: Optional[str] = None
    steps: list[OfferApprovalRuleStep]

class OfferApprovalRuleResponse(BaseModel):
    id: int
    name: str
    department: Optional[str] = None
    job_level: Optional[str] = None
    steps: list[OfferApprovalRuleStep]
    created_at: datetime

    class Config:
        from_attributes = True
class OfferDetailsSchema(BaseModel):
    contract_subject: Optional[str] = ""
    department: Optional[str] = ""
    job_level: Optional[str] = ""
    proposed_start_date: Optional[str] = ""
    salary_type: Optional[str] = "月薪"
    base_salary: Optional[float] = 0.0
    employment_type: Optional[str] = "正式员工"
    performance_bonus: Optional[float] = 0.0
    probation_salary_rate: Optional[str] = "100%"
    target_bonus_months: Optional[float] = 0.0
    stock_options: Optional[float] = 0.0
    probation_months: Optional[int] = 3
    prev_monthly_salary: Optional[float] = 0.0
    prev_annual_salary: Optional[str] = ""
    job_category: Optional[str] = ""
    job_family: Optional[str] = ""
    job_sequence: Optional[str] = ""
    base_post: Optional[str] = ""
    contract_job: Optional[str] = ""
    compliance_check: Optional[str] = "是"

class OfferApprovalInstanceCreate(BaseModel):
    candidate_id: int
    salary: str
    job_level: str
    department: str
    offer_details: Optional[OfferDetailsSchema] = None

class OfferApprovalStepData(BaseModel):
    label: Optional[str] = ""
    approver_email: Optional[str] = ""
    status: Optional[str] = "pending"
    comment: Optional[str] = ""
    action_time: Optional[str] = ""

    class Config:
        from_attributes = True

class OfferApprovalInstanceResponse(BaseModel):
    id: int
    candidate_id: Optional[int] = None
    candidate_name: Optional[str] = ""
    job_title: Optional[str] = ""
    salary: Optional[str] = ""
    job_level: Optional[str] = ""
    department: Optional[str] = ""
    current_step_index: Optional[int] = 0
    status: Optional[str] = "pending"
    creator_email: Optional[str] = ""
    steps_data: Optional[list[dict]] = []
    offer_details: Optional[dict] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class OfferApprovalActionRequest(BaseModel):
    action: str  # "approve" / "reject"
    comment: Optional[str] = ""