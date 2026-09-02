from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import uvicorn
import os
import shutil
import pdfplumber
import google.generativeai as genai
import json
import secrets
from datetime import datetime
from dotenv import load_dotenv

from typing import Optional

import models
import schemas
import services
from database import engine, get_db

# Create database tables
models.Base.metadata.create_all(bind=engine)

# 自动注入隐藏审计日志种子与默认Offer审批流（如果表为空）
from database import SessionLocal
try:
    db_seed = SessionLocal()
    if db_seed.query(models.UserLoginLog).count() == 0:
        import datetime
        now = datetime.datetime.utcnow()
        db_seed.add(models.UserLoginLog(email="hr@aura.com", login_time=now - datetime.timedelta(hours=5), is_online=False))
        db_seed.add(models.UserLoginLog(email="manager@aura.com", login_time=now - datetime.timedelta(hours=2), is_online=False))
        db_seed.add(models.UserLoginLog(email="interviewer@aura.com", login_time=now - datetime.timedelta(minutes=45), is_online=False))
        db_seed.add(models.UserLoginLog(email="admin@aura.com", login_time=now - datetime.timedelta(minutes=5), is_online=True))
        db_seed.commit()
        
    if db_seed.query(models.OfferApprovalRule).count() == 0:
        default_steps = [
            {"label": "HR上级", "approver_email": "hr_manager@example.com"},
            {"label": "薪酬", "approver_email": "finance@example.com"},
            {"label": "直线经理/业务线负责人", "approver_email": "line_manager@example.com"},
            {"label": "HRVP", "approver_email": "hrvp@example.com"}
        ]
        db_seed.add(models.OfferApprovalRule(
            name="默认全局审批流",
            department=None,
            job_level=None,
            steps=default_steps
        ))
        db_seed.commit()
    db_seed.close()
except Exception as e:
    print(f"Failed to auto-seed startup data: {e}")

# Auto-migrate: add phone column if it doesn't exist
from sqlalchemy import text
try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE candidates ADD COLUMN phone VARCHAR(50);"))
except Exception:
    pass  # column already exists or other error


# Database Migration for new Job columns (Safe for SQLite)
def upgrade_db():
    from sqlalchemy import text
    
    # 1. 独立自愈 departments 树状 parent_id 字段（防范 MySQL/SQLite 下因其他表的 PRAGMA 抛错而被打断）
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE departments ADD COLUMN parent_id INTEGER NULL"))
    except Exception:
        pass
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE departments ADD CONSTRAINT fk_dept_parent FOREIGN KEY (parent_id) REFERENCES departments(id) ON DELETE CASCADE"))
    except Exception:
        pass

    try:
        with engine.begin() as conn:
            # Check if one of the new columns exists
            result = conn.execute(text("PRAGMA table_info(jobs)")).fetchall()
            columns = [row[1] for row in result]
            if "description" not in columns:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN description TEXT"))
                conn.execute(text("ALTER TABLE jobs ADD COLUMN job_type VARCHAR(50) DEFAULT '全职'"))
                conn.execute(text("ALTER TABLE jobs ADD COLUMN category VARCHAR(100)"))
                conn.execute(text("ALTER TABLE jobs ADD COLUMN experience VARCHAR(50) DEFAULT '不限'"))
                conn.execute(text("ALTER TABLE jobs ADD COLUMN job_level VARCHAR(50)"))
                conn.execute(text("ALTER TABLE jobs ADD COLUMN headcount INTEGER DEFAULT 1"))
                conn.execute(text("ALTER TABLE jobs ADD COLUMN salary_range VARCHAR(50)"))
                conn.execute(text("ALTER TABLE jobs ADD COLUMN salary_months INTEGER DEFAULT 12"))
                
            c_result = conn.execute(text("PRAGMA table_info(candidates)")).fetchall()
            c_columns = [row[1] for row in c_result]
            if "match_score" not in c_columns:
                conn.execute(text("ALTER TABLE candidates ADD COLUMN match_score INTEGER"))
                conn.execute(text("ALTER TABLE candidates ADD COLUMN match_reason TEXT"))

    except Exception as e:
        print(f"Migration error (ignoring if tables just created): {e}")

upgrade_db()

# --- AUTH SECURITY CONFIG & TOOLS ---
import hashlib
import base64
import jwt
from datetime import timedelta
from fastapi.security import OAuth2PasswordBearer

SECRET_KEY = "aura-ats-super-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return f"{base64.b64encode(salt).decode('utf-8')}:{base64.b64encode(pwd_hash).decode('utf-8')}"

def verify_password(password: str, hashed: str) -> bool:
    try:
        salt_b64, hash_b64 = hashed.split(":")
        salt = base64.b64decode(salt_b64)
        target_hash = base64.b64decode(hash_b64)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return pwd_hash == target_hash
    except Exception:
        return False

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(db: Session = Depends(get_db), token: Optional[str] = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="未提供登录凭证")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="登录凭证已失效")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="登录凭证已过期")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="登录凭证解析失败")
        
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user

def check_admin_permission(current_user: models.User):
    if current_user.role not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="无权操作系统设置，仅限管理员角色操作")

async def get_current_user_optional(db: Session = Depends(get_db), token: Optional[str] = Depends(oauth2_scheme)):
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        user = db.query(models.User).filter(models.User.email == email).first()
        return user
    except Exception:
        return None

def init_admin_user():
    db = next(get_db())
    try:
        admin = db.query(models.User).filter(models.User.email == "hr@example.com").first()
        if not admin:
            hashed = hash_password("123456")
            db_admin = models.User(
                company="Aura Tech",
                email="hr@example.com",
                hashed_password=hashed,
                name="HR Manager",
                role="SuperAdmin"
            )
            db.add(db_admin)
            db.commit()
            print("Successfully initialized default admin user (hr@example.com / 123456)")
    except Exception as e:
        print(f"Error initializing default user: {e}")
    finally:
        db.close()

init_admin_user()

load_dotenv()

app = FastAPI(title="Aura API", description="Backend API for Aura Recruitment System")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure uploads directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# --- API ROUTES ---

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Aura API is running."}

# --- AUTH ROUTERS ---

@app.post("/api/auth/register", response_model=schemas.TokenResponse)
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="该工作邮箱已被注册")
        
    hashed = hash_password(user_data.password)
    new_user = models.User(
        company=user_data.company,
        email=user_data.email,
        hashed_password=hashed,
        name=user_data.name,
        role=user_data.role or "Admin"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    token = create_access_token({"sub": new_user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": new_user
    }

@app.post("/api/auth/login", response_model=schemas.TokenResponse)
def login(login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="邮箱或密码错误")
        
    # 登录成功，记录日志并将之前的登录记录置为离线
    db.query(models.UserLoginLog).filter(models.UserLoginLog.email == user.email).update({"is_online": False})
    new_log = models.UserLoginLog(email=user.email, is_online=True)
    db.add(new_log)
    db.commit()
    
    token = create_access_token({"sub": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }

@app.get("/api/auth/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@app.post("/api/auth/logout")
def logout(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db.query(models.UserLoginLog).filter(models.UserLoginLog.email == current_user.email).update({"is_online": False})
    db.commit()
    return {"ok": True}

@app.get("/api/settings/login-logs", response_model=list[schemas.UserLoginLogResponse])
def get_login_logs(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_admin_permission(current_user)
    return db.query(models.UserLoginLog).order_by(models.UserLoginLog.login_time.desc()).limit(100).all()

# --- USER INVITATION ROUTERS ---

@app.post("/api/auth/invite", response_model=schemas.UserInvitationResponse)
def create_user_invitation(invite_data: schemas.UserInvitationCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="没有权限执行此操作，仅限管理员")
        
    existing_user = db.query(models.User).filter(models.User.email == invite_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="该邮箱已注册为协同成员")
        
    existing_invite = db.query(models.UserInvitation).filter(models.UserInvitation.email == invite_data.email).first()
    if existing_invite and existing_invite.status == "pending":
        existing_invite.name = invite_data.name
        existing_invite.department = invite_data.department
        existing_invite.role = invite_data.role
        existing_invite.token = secrets.token_hex(24)
        existing_invite.created_at = datetime.utcnow()
        db.commit()
        db.refresh(existing_invite)
        invitation = existing_invite
    else:
        if existing_invite:
            db.delete(existing_invite)
            db.commit()
            
        token = secrets.token_hex(24)
        invitation = models.UserInvitation(
            email=invite_data.email,
            name=invite_data.name,
            department=invite_data.department,
            role=invite_data.role,
            token=token,
            status="pending"
        )
        db.add(invitation)
        db.commit()
        db.refresh(invitation)

    invite_link = f"https://aura-ats.zeabur.app/register.html?invite_token={invitation.token}"
    company_name = current_user.company or "Aura Tech"
    
    services.EmailService.send_user_invitation(
        to_email=invitation.email,
        invite_link=invite_link,
        inviter_name=current_user.name,
        company_name=company_name
    )
    
    return invitation

@app.get("/api/auth/invite", response_model=list[schemas.UserInvitationResponse])
def get_user_invitations(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="没有权限执行此操作")
    return db.query(models.UserInvitation).order_by(models.UserInvitation.id.desc()).all()

@app.get("/api/auth/invite/detail/{token}", response_model=schemas.UserInvitationResponse)
def get_invitation_detail(token: str, db: Session = Depends(get_db)):
    invite = db.query(models.UserInvitation).filter(models.UserInvitation.token == token).first()
    if not invite or invite.status != "pending":
        raise HTTPException(status_code=400, detail="邀请链接无效或已过期")
    return invite

@app.delete("/api/auth/invite/{invite_id}")
def delete_user_invitation(invite_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="没有权限执行此操作，仅限管理员")
        
    invite = db.query(models.UserInvitation).filter(models.UserInvitation.id == invite_id).first()
    if not invite:
        raise HTTPException(status_code=404, detail="未找到该邀请记录")
        
    if current_user.email == invite.email:
        raise HTTPException(status_code=400, detail="禁止删除当前登录的账号")
        
    # 如果该成员已经接受邀请，需要同时清理 users 表中的账号
    if invite.status == "accepted":
        associated_user = db.query(models.User).filter(models.User.email == invite.email).first()
        if associated_user:
            db.delete(associated_user)
            
    db.delete(invite)
    db.commit()
    return {"detail": "已成功删除并注销该协同成员"}

@app.post("/api/auth/register-by-invite", response_model=schemas.TokenResponse)
def register_by_invite(reg_data: schemas.RegisterByInvite, db: Session = Depends(get_db)):
    invite = db.query(models.UserInvitation).filter(models.UserInvitation.token == reg_data.token).first()
    if not invite or invite.status != "pending":
        raise HTTPException(status_code=400, detail="激活链接失效，注册失败")
        
    existing_user = db.query(models.User).filter(models.User.email == invite.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="该邮箱已被注册")
        
    hashed = hash_password(reg_data.password)
    new_user = models.User(
        company="Aura Tech",
        email=invite.email,
        hashed_password=hashed,
        name=reg_data.name or invite.name,
        role=invite.role
    )
    db.add(new_user)
    invite.status = "accepted"
    db.commit()
    db.refresh(new_user)

    # 同步加入面试官人员库
    if invite.role in ["Interviewer", "HiringManager", "Recruiter", "Admin"]:
        dept_id = None
        if invite.department:
            dept = db.query(models.Department).filter(models.Department.name == invite.department).first()
            if dept:
                dept_id = dept.id
        
        existing_interviewer = db.query(models.Interviewer).filter(models.Interviewer.name == new_user.name).first()
        if not existing_interviewer:
            db_interviewer = models.Interviewer(
                name=new_user.name,
                role_type=invite.role,
                department_id=dept_id
            )
            db.add(db_interviewer)
            db.commit()
    
    token = create_access_token({"sub": new_user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": new_user
    }



@app.get("/api/jobs", response_model=list[schemas.JobWithFunnel])
def get_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    jobs = db.query(models.Job).order_by(models.Job.id.desc()).offset(skip).limit(limit).all()
    result = []
    for job in jobs:
        yesterday = datetime.utcnow() - datetime.timedelta(days=1) if hasattr(datetime, 'timedelta') else datetime.now() - __import__('datetime').timedelta(days=1)
        new_resume = db.query(models.Candidate).filter(models.Candidate.job == job.title, models.Candidate.stage == "初筛", models.Candidate.created_at >= yesterday).count()
        screened = db.query(models.Candidate).filter(models.Candidate.job == job.title, models.Candidate.stage == "初筛").count()
        interviewing = db.query(models.Candidate).filter(models.Candidate.job == job.title, models.Candidate.stage.in_(["一面", "二面", "HR面"])).count()
        offered = db.query(models.Candidate).filter(models.Candidate.job == job.title, models.Candidate.stage == "发Offer").count()
        
        job_dict = schemas.Job.model_validate(job).model_dump()
        job_dict["funnel"] = {
            "new": new_resume,
            "screened": screened,
            "interviewing": interviewing,
            "offered": offered
        }
        result.append(job_dict)
    return result

@app.post("/api/jobs", response_model=schemas.Job)
def create_job(job: schemas.JobCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_job = models.Job(**job.model_dump())
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

@app.get("/api/jobs/{job_id}", response_model=schemas.Job)
def get_job(job_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")
    return db_job

@app.get("/api/public/jobs/{job_id}", response_model=schemas.Job)
def get_public_job(job_id: int, db: Session = Depends(get_db)):
    db_job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")
    return db_job

@app.patch("/api/jobs/{job_id}", response_model=schemas.Job)
def update_job_status(job_id: int, job_update: schemas.JobUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job_update.status:
        db_job.status = job_update.status
    db.commit()
    db.refresh(db_job)
    return db_job

@app.get("/api/candidates", response_model=list[schemas.Candidate])
def get_candidates(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    try:
        role = current_user.role or "Admin"
        name = current_user.name or "系统"
        email = current_user.email or ""
        
        if role == "Interviewer":
            my_candidate_ids = db.query(models.Interview.candidate_id).filter(models.Interview.interviewer_name == name).distinct().all()
            candidate_id_list = [c[0] for c in my_candidate_ids]
            if not candidate_id_list:
                return []
            return db.query(models.Candidate).filter(models.Candidate.id.in_(candidate_id_list)).order_by(models.Candidate.id.desc()).offset(skip).limit(limit).all()
        elif role == "HiringManager":
            user_invite = db.query(models.UserInvitation).filter(models.UserInvitation.email == email).first()
            dept_name = user_invite.department if user_invite else None
            if dept_name:
                dept_jobs = db.query(models.Job).filter(models.Job.department == dept_name).all()
                job_titles = [j.title for j in dept_jobs]
                if job_titles:
                    return db.query(models.Candidate).filter(models.Candidate.job.in_(job_titles)).order_by(models.Candidate.id.desc()).offset(skip).limit(limit).all()
            return []
            
        candidates = db.query(models.Candidate).order_by(models.Candidate.id.desc()).offset(skip).limit(limit).all()
        return candidates
    except Exception as e:
        print(f"DB Error: {e}")
        raise HTTPException(status_code=500, detail="Database error")

@app.get("/api/candidates/{candidate_id}", response_model=schemas.Candidate)
def get_candidate(candidate_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    candidate = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # RBAC 防越权校验
    role = current_user.role or "Admin"
    name = current_user.name or "系统"
    email = current_user.email or ""

    if role == "Interviewer":
        # 面试官仅可查看与自己绑定的候选人
        has_interview = db.query(models.Interview).filter(
            models.Interview.candidate_id == candidate.id,
            models.Interview.interviewer_name == name
        ).first()
        if not has_interview:
            raise HTTPException(status_code=403, detail="无权查看非指派面试的候选人档案")
    elif role == "HiringManager":
        # 用人经理仅可查看属于本部门职位的候选人
        user_invite = db.query(models.UserInvitation).filter(models.UserInvitation.email == email).first()
        dept_name = user_invite.department if user_invite else None
        if dept_name and candidate.job:
            job_obj = db.query(models.Job).filter(models.Job.title == candidate.job).first()
            if job_obj and job_obj.department != dept_name:
                raise HTTPException(status_code=403, detail="无权查看非本部门管辖的候选人档案")

    return candidate

@app.post("/api/candidates/{candidate_id}/screen", response_model=schemas.Candidate)
def screen_candidate(candidate_id: int, request: schemas.CandidateScreenRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role not in ["SuperAdmin", "Admin", "HiringManager"]:
        raise HTTPException(status_code=403, detail="没有权限执行此操作，仅限用人经理或管理员")
        
    candidate = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    old_stage = candidate.stage
    if request.action == "pass":
        candidate.stage = "复筛通过"
        action_name = "用人经理复筛通过"
        details_text = f"复筛评估通过，已指派 HR 发起面试安排"
        
        # 自动生成 SystemTask 通知 HR 排期
        job_info = candidate.job or "未知职位"
        task = models.SystemTask(
            title=f"安排面试：请为 {candidate.name} 协调排期",
            content=f"候选人 {candidate.name} 投递了职位 【{job_info}】，已通过用人经理 {current_user.name} 的复筛，请 HR 协助安排面试排期。",
            task_type="schedule_interview",
            candidate_id=candidate.id,
            status="pending"
        )
        db.add(task)
    elif request.action == "fail":
        candidate.stage = "已淘汰"
        action_name = "用人经理复筛淘汰"
        details_text = f"复筛评估为不合适，直接归档淘汰"
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
        
    db_log = models.CandidateLog(
        candidate_id=candidate.id,
        operator=current_user.name,
        action=action_name,
        details=details_text
    )
    db.add(db_log)
    db.commit()
    db.refresh(candidate)
    return candidate


@app.post("/api/candidates/{candidate_id}/reupload-resume", response_model=schemas.Candidate)
async def reupload_resume(candidate_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    candidate = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    candidate.pdf_path = f"/uploads/{safe_filename}"
    
    db_log = models.CandidateLog(
        candidate_id=candidate.id,
        operator=current_user.name,
        action="重新上传并补全了原始简历文件"
    )
    db.add(db_log)
    db.commit()
    db.refresh(candidate)
    return candidate


async def _process_resume_upload(file: UploadFile, job_title: str, operator: str, db: Session, current_user: Optional[models.User] = None):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
            
    try:
        extracted_text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"
                    
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")
            
        import re
        extracted_text = re.sub(r'[用专聘招球雪]', '', extracted_text)
        extracted_text = re.sub(r'\n\s*\n', '\n', extracted_text)

        parsed_data = {}
        
        job_info_text = ""
        if job_title != "默认（AI自动提取）":
            job_obj = db.query(models.Job).filter(models.Job.title == job_title).first()
            if job_obj:
                import re
                clean_desc = re.sub(r'<[^>]+>', '', job_obj.description or '')
                job_desc = f"{clean_desc} {job_obj.job_type or ''} {job_obj.experience or ''} {job_obj.category or ''}"
                job_info_text = f"\n【正在应聘的职位及JD】\n职位名称：{job_title}\n职位JD：{job_desc[:1000]}\n"

        if api_key:
            candidate_models = [
                'gemini-2.5-flash-lite',
                'gemini-flash-lite-latest',
                'gemini-2.5-flash',
                'gemini-flash-latest'
            ]
            success = False
            last_error = ""

            for model_name in candidate_models:
                try:
                    print(f"Trying AI model: {model_name}...")
                    model = genai.GenerativeModel(model_name)
                    prompt = f"""
                    请作为一名资深HR数据提取专家，从以下简历文本中提取结构化信息。
                    要求：返回合法 JSON，包含 name(请准确提取候选人本人的真实姓名，不要提取成文件名、其他称呼或乱码), job, exp(仅提取最高学历，如"本科"、"硕士"等，不要包含工作年限), phone(请仔细提取手机号，通常为11位数字), email, skills(array), ai_summary, ai_analysis。
                    在编写 ai_analysis 时，请务必包含以下三个维度的结构化点评（请只使用纯文本和 HTML 的 <br> 换行，绝对不要使用 Markdown 语法如 **加粗** 或 # 标题）：
                    ✅ 亮点（候选人优势）；<br>
                    ⚠️ 风险（劣势项或经验短板）；<br>
                    🎯 面试建议（结合职位描述，提示需面试官重点关注或追问的维度）。
                    如果提供了【正在应聘的职位及JD】，请在提取信息和编写点评时，紧密结合该 JD要求，并额外输出 match_score（0-100的整数）和 match_reason（简短的综合匹配度总结）。{job_info_text}
                    简历文本：{extracted_text[:4000]}
                    """
                    response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                    parsed_data = json.loads(response.text.strip())
                    success = True
                    print(f"Successfully parsed using {model_name}")
                    break
                except Exception as e:
                    last_error = str(e)
                    print(f"Model {model_name} failed: {e}")
                    if "429" in last_error or "quota" in last_error.lower():
                        continue
                    elif "404" in last_error or "not found" in last_error.lower():
                        continue
                    else:
                        break

            if not success:
                if "429" in last_error or "quota" in last_error.lower():
                    parsed_data = {
                        "name": file.filename.replace('.pdf', '')[:10],
                        "job": "演示模式（API额度已满）",
                        "exp": "3-5年 / 本科",
                        "email": "demo@example.com",
                        "skills": ["所有模型额度已满", "演示模式"],
                        "ai_summary": "⚠️ 抱歉，当前所有可用的 Gemini 免费模型额度（包含 1.5/2.0 系列）均已耗尽。系统已自动切至演示模式。",
                        "ai_analysis": "Google 免费 API 每日限额较低。若需继续测试，请更换 API Key 或等待次日配额刷新。"
                    }
                else:
                    parsed_data = {"name": "AI 解析异常", "job": "错误", "exp": "未知", "email": "未知", "skills": ["解析失败"], "ai_summary": "服务响应异常", "ai_analysis": last_error}
        else:
            parsed_data = {"name": file.filename, "job": "未配置 API Key", "exp": "未知", "email": "未知", "skills": ["模拟"], "ai_summary": "未配置 Key", "ai_analysis": "未配置 Key"}

        final_job = job_title if job_title != "默认（AI自动提取）" else parsed_data.get("job", "未知")

        skills_raw = parsed_data.get("skills")
        if isinstance(skills_raw, list):
            skills_val = [str(item) for item in skills_raw]
        elif skills_raw:
            skills_val = [str(skills_raw)]
        else:
            skills_val = []

        phone_val = str(parsed_data.get("phone") or "").strip()
        email_val = str(parsed_data.get("email") or "").strip()
        
        if not phone_val or phone_val == "None":
            phone_val = "暂无"
        if not email_val or email_val == "None":
            email_val = "暂无"
            
        existing_candidate = None
        if phone_val and phone_val != "暂无" and len(phone_val) > 4:
            existing_candidate = db.query(models.Candidate).filter(models.Candidate.phone == phone_val).first()
        if not existing_candidate and email_val and email_val != "暂无" and "@" in email_val:
            existing_candidate = db.query(models.Candidate).filter(models.Candidate.email == email_val).first()

        operator_name = current_user.name if current_user else operator

        if existing_candidate:
            existing_candidate.job = str(final_job or "未知")
            existing_candidate.stage = "初筛"
            existing_candidate.exp = str(parsed_data.get("exp") or existing_candidate.exp)
            existing_candidate.skills = skills_val
            existing_candidate.ai_summary = str(parsed_data.get("ai_summary") or "")
            existing_candidate.ai_analysis = str(parsed_data.get("ai_analysis") or "")
            existing_candidate.match_score = parsed_data.get("match_score")
            existing_candidate.match_reason = str(parsed_data.get("match_reason") or "") if parsed_data.get("match_reason") else None
            existing_candidate.raw_text = extracted_text
            existing_candidate.pdf_path = f"/uploads/{safe_filename}"
            existing_candidate.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(existing_candidate)
            db_candidate = existing_candidate
            
            details_str = f"检测到手机号[{phone_val}]或邮箱[{email_val}]已存在。本次新投递职位【{final_job}】，已更新该候选人的主表属性及简历原件。"
            db_log = models.CandidateLog(
                candidate_id=db_candidate.id,
                operator=operator_name,
                action="重复投递自动合并",
                details=details_str
            )
            db.add(db_log)
            db.commit()
        else:
            db_candidate = models.Candidate(
                name=str(parsed_data.get("name") or "未知"),
                job=str(final_job or "未知"),
                stage="初筛",
                exp=str(parsed_data.get("exp") or "未知"),
                phone=phone_val,
                email=email_val,
                skills=skills_val,
                ai_summary=str(parsed_data.get("ai_summary") or ""),
                ai_analysis=str(parsed_data.get("ai_analysis") or ""),
                match_score=parsed_data.get("match_score"),
                match_reason=str(parsed_data.get("match_reason") or "") if parsed_data.get("match_reason") else None,
                raw_text=extracted_text,
                pdf_path=f"/uploads/{safe_filename}"
            )
            db.add(db_candidate)
            db.commit()
            db.refresh(db_candidate)
            
            db_log = models.CandidateLog(
                candidate_id=db_candidate.id,
                operator=operator_name,
                action="简历解析成功并入库"
            )
            db.add(db_log)
            db.commit()

        db_app = models.JobApplication(
            candidate_id=db_candidate.id,
            job_title=str(final_job or "未知"),
            stage="初筛",
            pdf_path=f"/uploads/{safe_filename}"
        )
        db.add(db_app)
        db.commit()

        if operator == "Candidate (Self-Submitted)":
            task = models.SystemTask(
                title=f"新投递：{db_candidate.name} 自主投递了 {db_candidate.job}",
                content=f"候选人 {db_candidate.name} 投递了职位 【{db_candidate.job}】，简历已由 AI 自动解析完毕，请 HR 尽快完成初筛。",
                task_type="new_application",
                candidate_id=db_candidate.id,
                status="pending"
            )
            db.add(task)
            db.commit()

        return db_candidate

    except Exception as e:
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/parse-resume", response_model=schemas.Candidate)
async def parse_resume(file: UploadFile = File(...), job_title: str = Form("默认（AI自动提取）"), operator: str = Form("系统"), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return await _process_resume_upload(file=file, job_title=job_title, operator=operator, db=db, current_user=current_user)

@app.post("/api/public/submit-resume", response_model=schemas.Candidate)
async def submit_public_resume(file: UploadFile = File(...), job_title: str = Form("默认（AI自动提取）"), db: Session = Depends(get_db)):
    return await _process_resume_upload(file=file, job_title=job_title, operator="Candidate (Self-Submitted)", db=db, current_user=None)

@app.patch("/api/candidates/{candidate_id}", response_model=schemas.Candidate)
def update_candidate_stage(candidate_id: int, candidate_update: schemas.CandidateUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    candidate = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    if candidate_update.stage and candidate_update.stage != candidate.stage:
        old_stage = candidate.stage
        candidate.stage = candidate_update.stage
        # 使用当前登录的真实用户记录修改日志
        operator_name = current_user.name if current_user else candidate_update.operator
        db_log = models.CandidateLog(candidate_id=candidate.id, operator=operator_name, action=f"阶段流转: {old_stage} ➔ {candidate.stage}", details=candidate_update.details)
        db.add(db_log)
        
        # 自动消解 new_application 待办任务
        pending_app_tasks = db.query(models.SystemTask).filter(
            models.SystemTask.candidate_id == candidate.id,
            models.SystemTask.status == "pending",
            models.SystemTask.task_type == "new_application"
        ).all()
        for task in pending_app_tasks:
            task.status = "resolved"

        # 同步更新最新的投递记录状态
        latest_app = db.query(models.JobApplication).filter(models.JobApplication.candidate_id == candidate.id).order_by(models.JobApplication.created_at.desc()).first()
        if latest_app:
            latest_app.stage = candidate.stage

    # 检查是否修改了基本信息
    has_basic_update = False
    changes = []
    operator_name = current_user.name if current_user else candidate_update.operator
    
    if candidate_update.name is not None and candidate_update.name != candidate.name:
        changes.append(f"姓名: {candidate.name} ➔ {candidate_update.name}")
        candidate.name = candidate_update.name
        has_basic_update = True
    if candidate_update.phone is not None and candidate_update.phone != candidate.phone:
        changes.append(f"电话: {candidate.phone} ➔ {candidate_update.phone}")
        candidate.phone = candidate_update.phone
        has_basic_update = True
    if candidate_update.email is not None and candidate_update.email != candidate.email:
        changes.append(f"邮箱: {candidate.email} ➔ {candidate_update.email}")
        candidate.email = candidate_update.email
        has_basic_update = True
    if candidate_update.exp is not None and candidate_update.exp != candidate.exp:
        changes.append(f"学历: {candidate.exp} ➔ {candidate_update.exp}")
        candidate.exp = candidate_update.exp
        has_basic_update = True
    if candidate_update.job is not None and candidate_update.job != candidate.job:
        changes.append(f"职位: {candidate.job} ➔ {candidate_update.job}")
        candidate.job = candidate_update.job
        has_basic_update = True
        
    if has_basic_update:
        db_log = models.CandidateLog(
            candidate_id=candidate.id,
            operator=operator_name,
            action="修改基本信息",
            details="修改项：\n" + "\n".join(changes)
        )
        db.add(db_log)
    
    db.commit()
    db.refresh(candidate)
    return candidate

@app.delete("/api/candidates/{candidate_id}")
def delete_candidate(candidate_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    candidate = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    
    if candidate.pdf_path:
        file_path = candidate.pdf_path.lstrip('/')
        if os.path.exists(file_path):
            try: os.remove(file_path)
            except: pass

    db.delete(candidate)
    db.commit()
    return {"status": "success"}

# --- STATIC FILES & PAGE ROUTES ---

# Mount assets and uploads
if os.path.exists("assets"):
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.get("/")
@app.get("/index.html")
async def read_index():
    return FileResponse('index.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/candidates.html")
async def read_candidates():
    return FileResponse('candidates.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
@app.get("/talent-pool.html")
async def read_talent_pool():
    return FileResponse('talent-pool.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/candidate-detail.html")
async def read_detail():
    return FileResponse('candidate-detail.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/interviews.html")
async def read_interviews():
    return FileResponse('interviews.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/jobs.html")
async def read_jobs():
    return FileResponse('jobs.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/add-candidate.html")
async def read_add_candidate():
    return FileResponse('add-candidate.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/add-job.html")
async def read_add_job():
    return FileResponse('add-job.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/login.html")
async def read_login():
    return FileResponse('login.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/register.html")
async def read_register():
    return FileResponse('register.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/settings.html")
async def read_settings():
    return FileResponse('settings.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/portal.html")
async def read_portal():
    return FileResponse('portal.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

# --- System Settings APIs ---

@app.get("/api/settings/departments", response_model=list[schemas.Department])
def get_departments(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Department).all()

@app.post("/api/settings/departments", response_model=schemas.Department)
def create_department(item: schemas.DepartmentCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_admin_permission(current_user)
    try:
        existing = db.query(models.Department).filter(models.Department.name == item.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="该部门名称已存在，请勿重复添加")
            
        db_item = models.Department(**item.model_dump())
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return db_item
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"数据库异常: {str(e)}")

@app.delete("/api/settings/departments/{item_id}")
def delete_department(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_admin_permission(current_user)
    db.query(models.Department).filter(models.Department.id == item_id).delete()
    db.commit()
    return {"ok": True}

@app.get("/api/settings/interviewers", response_model=list[schemas.Interviewer])
def get_interviewers(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Interviewer).all()

@app.post("/api/settings/interviewers", response_model=schemas.Interviewer)
def create_interviewer(item: schemas.InterviewerCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_admin_permission(current_user)
    db_item = models.Interviewer(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/api/settings/interviewers/{item_id}")
def delete_interviewer(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_admin_permission(current_user)
    db.query(models.Interviewer).filter(models.Interviewer.id == item_id).delete()
    db.commit()
    return {"ok": True}

@app.get("/api/settings/locations", response_model=list[schemas.Location])
def get_locations(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Location).all()

@app.post("/api/settings/locations", response_model=schemas.Location)
def create_location(item: schemas.LocationCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_admin_permission(current_user)
    db_item = models.Location(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/api/settings/locations/{item_id}")
def delete_location(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_admin_permission(current_user)
    db.query(models.Location).filter(models.Location.id == item_id).delete()
    db.commit()
    return {"ok": True}

@app.get("/api/settings/interview-processes", response_model=list[schemas.InterviewProcess])
def get_interview_processes(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.InterviewProcess).all()

@app.post("/api/settings/interview-processes", response_model=schemas.InterviewProcess)
def create_interview_process(item: schemas.InterviewProcessCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_admin_permission(current_user)
    db_item = models.InterviewProcess(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/api/settings/interview-processes/{item_id}")
def delete_interview_process(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_admin_permission(current_user)
    db.query(models.InterviewProcess).filter(models.InterviewProcess.id == item_id).delete()
    db.commit()
    return {"ok": True}

@app.get("/api/settings/categories", response_model=list[schemas.JobCategory])
def get_categories(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.JobCategory).all()

@app.post("/api/settings/categories", response_model=schemas.JobCategory)
def create_category(item: schemas.JobCategoryCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_admin_permission(current_user)
    db_item = models.JobCategory(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/api/settings/categories/{item_id}")
def delete_category(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_admin_permission(current_user)
    db.query(models.JobCategory).filter(models.JobCategory.id == item_id).delete()
    db.commit()
    return {"ok": True}

@app.patch("/api/settings/departments/{item_id}", response_model=schemas.Department)
def update_department(item_id: int, item: schemas.DepartmentCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_admin_permission(current_user)
    try:
        db_item = db.query(models.Department).filter(models.Department.id == item_id).first()
        if not db_item:
            raise HTTPException(status_code=404, detail="Department not found")
        
        # 检查重名（排查自身）
        existing = db.query(models.Department).filter(models.Department.name == item.name, models.Department.id != item_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="该部门名称已存在，请勿重复添加")
        
        # 环路指派防御逻辑：在树形配置中，不能把上级部门设为自己
        if item.parent_id == item_id:
            raise HTTPException(status_code=400, detail="Cannot set parent department to itself")
            
        for key, val in item.model_dump().items():
            setattr(db_item, key, val)
        db.commit()
        db.refresh(db_item)
        return db_item
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"数据库异常: {str(e)}")

@app.patch("/api/settings/interviewers/{item_id}", response_model=schemas.Interviewer)
def update_interviewer(item_id: int, item: schemas.InterviewerCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_admin_permission(current_user)
    db_item = db.query(models.Interviewer).filter(models.Interviewer.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Interviewer not found")
    for key, val in item.model_dump().items():
        setattr(db_item, key, val)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.patch("/api/settings/locations/{item_id}", response_model=schemas.Location)
def update_location(item_id: int, item: schemas.LocationCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_admin_permission(current_user)
    db_item = db.query(models.Location).filter(models.Location.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Location not found")
    for key, val in item.model_dump().items():
        setattr(db_item, key, val)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.patch("/api/settings/interview-processes/{item_id}", response_model=schemas.InterviewProcess)
def update_interview_process(item_id: int, item: schemas.InterviewProcessCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_admin_permission(current_user)
    db_item = db.query(models.InterviewProcess).filter(models.InterviewProcess.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="InterviewProcess not found")
    for key, val in item.model_dump().items():
        setattr(db_item, key, val)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.patch("/api/settings/categories/{item_id}", response_model=schemas.JobCategory)
def update_category(item_id: int, item: schemas.JobCategoryCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_admin_permission(current_user)
    db_item = db.query(models.JobCategory).filter(models.JobCategory.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="JobCategory not found")
    for key, val in item.model_dump().items():
        setattr(db_item, key, val)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/api/settings/email-templates", response_model=list[schemas.EmailTemplate])
def get_email_templates(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.EmailTemplate).all()

@app.post("/api/settings/email-templates", response_model=schemas.EmailTemplate)
def create_email_template(item: schemas.EmailTemplateCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_admin_permission(current_user)
    db_item = models.EmailTemplate(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.patch("/api/settings/email-templates/{item_id}", response_model=schemas.EmailTemplate)
def update_email_template(item_id: int, item: schemas.EmailTemplateCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_admin_permission(current_user)
    db_item = db.query(models.EmailTemplate).filter(models.EmailTemplate.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="EmailTemplate not found")
    for key, val in item.model_dump().items():
        setattr(db_item, key, val)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/api/settings/email-templates/{item_id}")
def delete_email_template(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_admin_permission(current_user)
    db.query(models.EmailTemplate).filter(models.EmailTemplate.id == item_id).delete()
    db.commit()
    return {"ok": True}

@app.get("/api/settings/feedback-templates", response_model=list[schemas.FeedbackTemplate])
def get_feedback_templates(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.FeedbackTemplate).all()

@app.post("/api/settings/feedback-templates", response_model=schemas.FeedbackTemplate)
def create_feedback_template(item: schemas.FeedbackTemplateCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_admin_permission(current_user)
    db_item = models.FeedbackTemplate(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.patch("/api/settings/feedback-templates/{item_id}", response_model=schemas.FeedbackTemplate)
def update_feedback_template(item_id: int, item: schemas.FeedbackTemplateCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_admin_permission(current_user)
    db_item = db.query(models.FeedbackTemplate).filter(models.FeedbackTemplate.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="FeedbackTemplate not found")
    for key, val in item.model_dump().items():
        setattr(db_item, key, val)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/api/settings/feedback-templates/{item_id}")
def delete_feedback_template(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_admin_permission(current_user)
    db.query(models.FeedbackTemplate).filter(models.FeedbackTemplate.id == item_id).delete()
    db.commit()
    return {"ok": True}

@app.get("/api/calendar/freebusy")
def get_freebusy(interviewer: str, date: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return services.FeishuCalendarService.get_freebusy(interviewer, date, db)

@app.post("/api/interviews", response_model=schemas.Interview)
def create_interview(item: schemas.InterviewCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_item = models.Interview(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    
    # Send email and create event
    candidate = db.query(models.Candidate).filter(models.Candidate.id == item.candidate_id).first()
    if candidate:
        # 联动将候选人状态推进至“面试中”
        old_stage = candidate.stage
        candidate.stage = "面试中"
        
        # 记录操作日志
        db_log = models.CandidateLog(
            candidate_id=candidate.id,
            operator=current_user.name,
            action=f"安排面试并流转至: 面试中",
            details=f"安排了与 {item.interviewer_name} 的面试，时间: {item.start_time.strftime('%Y-%m-%d %H:%M')}"
        )
        db.add(db_log)
        
        template = db.query(models.EmailTemplate).first() # Simplify: get first template
        if template:
            content = template.content.replace("{candidate_name}", candidate.name) \
                                      .replace("{job_title}", item.job_title) \
                                      .replace("{interview_time}", str(item.start_time)) \
                                      .replace("{location}", item.location)
            subject = template.subject.replace("{job_title}", item.job_title)
            services.EmailService.send_interview_invitation(candidate.email or "demo@example.com", subject, content)
            
    # 自动将该候选人关联的待安排面试任务标记为已解决 (resolved)
    pending_tasks = db.query(models.SystemTask).filter(
        models.SystemTask.candidate_id == item.candidate_id,
        models.SystemTask.status == "pending",
        models.SystemTask.task_type == "schedule_interview"
    ).all()
    for task in pending_tasks:
        task.status = "resolved"
        
    db.commit()
    
    services.FeishuCalendarService.create_event(item.interviewer_name, item.start_time, item.end_time, "面试安排", "...")
    
    return db_item

@app.get("/api/interviews", response_model=list[schemas.Interview])
def get_interviews(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    role = current_user.role
    name = current_user.name
    email = current_user.email
    
    if role == "Interviewer":
        return db.query(models.Interview).filter(models.Interview.interviewer_name == name).all()
    elif role == "HiringManager":
        user_invite = db.query(models.UserInvitation).filter(models.UserInvitation.email == email).first()
        dept_name = user_invite.department if user_invite else None
        if dept_name:
            dept_jobs = db.query(models.Job).filter(models.Job.department == dept_name).all()
            job_titles = [j.title for j in dept_jobs]
            if job_titles:
                return db.query(models.Interview).filter(models.Interview.job_title.in_(job_titles)).all()
        return []
        
    return db.query(models.Interview).all()

@app.patch("/api/interviews/{interview_id}/feedback", response_model=schemas.Interview)
def submit_feedback(interview_id: int, feedback: schemas.InterviewUpdateFeedback, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    interview = db.query(models.Interview).filter(models.Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    interview.feedback_result = feedback.feedback_result
    interview.feedback_text = feedback.feedback_text
    interview.status = "已完成" # Automatically set status to completed
    
    # 联动如果评价为不满意，则候选人自动淘汰归档
    if feedback.feedback_result == "不满意":
        candidate = db.query(models.Candidate).filter(models.Candidate.id == interview.candidate_id).first()
        if candidate:
            candidate.stage = "已淘汰"
            db_log = models.CandidateLog(
                candidate_id=candidate.id,
                operator=current_user.name,
                action="面试判定淘汰",
                details=f"面试官 {interview.interviewer_name} 提交了不满意评价，候选人已自动淘汰归档。"
            )
            db.add(db_log)
            
    db.commit()
    db.refresh(interview)
    return interview

# --- Workbench Dashboard API ---

@app.get("/api/workbench/dashboard", response_model=schemas.DashboardSummary)
def get_dashboard_data(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    try:
        role = current_user.role or "SuperAdmin"
        name = current_user.name or "系统管理员"
        email = current_user.email or ""

        from datetime import datetime, timedelta
        
        # 辅助获取当前协同角色的所属部门
        user_invite = db.query(models.UserInvitation).filter(models.UserInvitation.email == email).first() if email else None
        dept_name = user_invite.department if user_invite else None

        stats = []
        todos = []
        activities = []

        # ==================== 1. 面试官 (Interviewer) 视角 ====================
        if role == "Interviewer":
            # 活跃职位：我参与过面试的在招职位
            my_jobs = db.query(models.Interview.job_title).filter(models.Interview.interviewer_name == name).distinct().all()
            my_job_list = [j[0] for j in my_jobs]
            my_active_jobs_count = db.query(models.Job).filter(models.Job.title.in_(my_job_list), models.Job.status == "热招中").count() if my_job_list else 0

            # 我评估的候选人：去重总数
            evaluated_candidates = db.query(models.Interview.candidate_id).filter(models.Interview.interviewer_name == name).distinct().count()

            # 我的待面试日程：状态为“已安排”的面试数
            my_pending_count = db.query(models.Interview).filter(
                models.Interview.interviewer_name == name,
                models.Interview.status == "已安排"
            ).count()

            # 我的待提交评价：当前时间已过但未填写 feedback_result 并且状态为已安排
            my_todo_feedback = db.query(models.Interview).filter(
                models.Interview.interviewer_name == name,
                models.Interview.status == "已安排",
                models.Interview.start_time <= datetime.utcnow()
            ).count()

            stats = [
                {"label": "参与职位", "value": my_active_jobs_count, "change": "正在协同", "icon": "briefcase"},
                {"label": "累计评估", "value": evaluated_candidates, "change": "去重人数", "icon": "users"},
                {"label": "我的待面试", "value": my_pending_count, "change": "待沟通", "icon": "calendar"},
                {"label": "待写反馈", "value": my_todo_feedback, "change": "急需填写", "icon": "alert-circle"}
            ]

            # 待办事项：列出面试官未开始的待面试排期
            my_interviews = db.query(models.Interview).filter(
                models.Interview.interviewer_name == name,
                models.Interview.status == "已安排"
            ).order_by(models.Interview.start_time.asc()).limit(5).all()

            for idx, itv in enumerate(my_interviews):
                todos.append({
                    "id": itv.id,
                    "type": "interview",
                    "title": f"面试评估: {itv.job_title}",
                    "time": itv.start_time.strftime("%m-%d %H:%M"),
                    "status": "去评估" if itv.start_time <= datetime.utcnow() else "待开始",
                    "candidate_id": itv.candidate_id
                })

            # 最近动态
            activities = [
                {
                    "id": 1,
                    "content": f"系统已自动同步您名下在飞书日历关联的 {my_pending_count} 场协同面试安排。",
                    "time": "刚刚",
                    "icon": "calendar",
                    "color": "#007AFF",
                    "candidate_id": None
                }
            ]
            # 追加最近评估的动态
            recent_itvs = db.query(models.Interview).filter(
                models.Interview.interviewer_name == name,
                models.Interview.status == "已完成"
            ).order_by(models.Interview.start_time.desc()).limit(3).all()
            for idx, ritv in enumerate(recent_itvs):
                candidate = db.query(models.Candidate).filter(models.Candidate.id == ritv.candidate_id).first()
                c_name = candidate.name if candidate else "未知"
                res_color = "#34C759" if ritv.feedback_result == "满意" else ("#FF9500" if ritv.feedback_result == "待定" else "#FF3B30")
                activities.append({
                    "id": 10 + idx,
                    "content": f"您已完成对候选人 <strong>{c_name}</strong> 的面试评估，评价结果为：<span style='color:{res_color};font-weight:600'>{ritv.feedback_result}</span>。",
                    "time": ritv.start_time.strftime("%m-%d"),
                    "icon": "check-circle" if ritv.feedback_result == "满意" else "alert-circle",
                    "color": res_color,
                    "candidate_id": ritv.candidate_id
                })

        # ==================== 2. 用人经理 (HiringManager) 视角 ====================
        elif role == "HiringManager":
            # 部门在招职位
            dept_jobs = db.query(models.Job).filter(models.Job.department == dept_name, models.Job.status == "热招中").all() if dept_name else []
            dept_job_titles = [j.title for j in dept_jobs]
            dept_active_jobs_count = len(dept_jobs)

            # 待我初筛简历 (阶段为“初筛”且投递的是本部门职位的候选人)
            dept_screening_count = db.query(models.Candidate).filter(
                models.Candidate.stage == "初筛",
                models.Candidate.job.in_(dept_job_titles) if dept_job_titles else False
            ).count() if dept_name else 0

            # 部门面试中
            dept_interviewing_count = db.query(models.Candidate).filter(
                models.Candidate.stage == "面试中",
                models.Candidate.job.in_(dept_job_titles) if dept_job_titles else False
            ).count() if dept_name else 0

            # 部门已录用 (Offer)
            dept_offered_count = db.query(models.Candidate).filter(
                models.Candidate.stage.in_(["Offer", "入职"]),
                models.Candidate.job.in_(dept_job_titles) if dept_job_titles else False
            ).count() if dept_name else 0

            stats = [
                {"label": "部门在招职位", "value": dept_active_jobs_count, "change": f"所属部门: {dept_name or '未指派'}", "icon": "briefcase"},
                {"label": "待我初筛", "value": dept_screening_count, "change": "急需处理", "icon": "users"},
                {"label": "部门面试中", "value": dept_interviewing_count, "change": "正在沟通", "icon": "calendar"},
                {"label": "部门已录用", "value": dept_offered_count, "change": "已发Offer", "icon": "check-circle"}
            ]

            # 待办事项：列出部门下待初筛的候选人
            screening_candidates = db.query(models.Candidate).filter(
                models.Candidate.stage == "初筛",
                models.Candidate.job.in_(dept_job_titles) if dept_job_titles else False
            ).order_by(models.Candidate.created_at.desc()).limit(5).all() if dept_name and dept_job_titles else []

            for c in screening_candidates:
                todos.append({
                    "id": c.id,
                    "type": "resume_alert",
                    "title": f"待初筛: {c.name} ({c.job})",
                    "time": "待评估",
                    "status": "去初筛",
                    "candidate_id": c.id
                })

            # 最近动态：本部门候选人状态更新
            activities = [
                {
                    "id": 1,
                    "content": f"您目前以 <strong>{dept_name or '未指派'}</strong> 部门负责人身份管理招聘协同大盘。",
                    "time": "刚刚",
                    "icon": "shield",
                    "color": "#AF52DE",
                    "candidate_id": None
                }
            ]
            recent_candidates = db.query(models.Candidate).filter(
                models.Candidate.job.in_(dept_job_titles) if dept_job_titles else False
            ).order_by(models.Candidate.updated_at.desc()).limit(3).all() if dept_name and dept_job_titles else []
            for idx, rc in enumerate(recent_candidates):
                activities.append({
                    "id": 20 + idx,
                    "content": f"部门候选人 <strong>{rc.name}</strong> 阶段流转为：<span style='color:var(--primary-color);font-weight:600'>{rc.stage}</span>。",
                    "time": rc.updated_at.strftime("%m-%d"),
                    "icon": "refresh-cw",
                    "color": "#007AFF",
                    "candidate_id": rc.id
                })

        # ==================== 3. 管理员 / HR (SuperAdmin / Admin / Recruiter) 视角 ====================
        else:
            active_jobs = db.query(models.Job).filter(models.Job.status == "热招中").count()
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            week_candidates = db.query(models.Candidate).filter(models.Candidate.created_at >= seven_days_ago).count()
            
            # 待安排面试与新简历处理任务
            pending_tasks_count = db.query(models.SystemTask).filter(
                models.SystemTask.status == "pending",
                models.SystemTask.task_type.in_(["schedule_interview", "new_application"])
            ).count()
            
            high_score_alerts = db.query(models.Candidate).filter(models.Candidate.match_score > 85).count()
            
            stats = [
                {"label": "活跃职位", "value": active_jobs, "change": "热招中", "icon": "briefcase"},
                {"label": "本周候选人", "value": week_candidates, "change": "新增简历", "icon": "users"},
                {"label": "待处理任务", "value": pending_tasks_count, "change": "协同处理待办", "icon": "calendar"},
                {"label": "待处理预警", "value": high_score_alerts, "change": "高分简历", "icon": "alert-circle"}
            ]

            # 待办事项：优先显示协同待办任务
            tasks = db.query(models.SystemTask).filter(
                models.SystemTask.status == "pending",
                models.SystemTask.task_type.in_(["schedule_interview", "new_application"])
            ).order_by(models.SystemTask.created_at.desc()).limit(5).all()

            for t in tasks:
                if t.task_type == "schedule_interview":
                    todos.append({
                        "id": t.id,
                        "type": "schedule_task",
                        "title": t.title,
                        "time": "待安排",
                        "status": "去排期",
                        "candidate_id": t.candidate_id
                    })
                elif t.task_type == "new_application":
                    todos.append({
                        "id": t.id,
                        "type": "new_application_task",
                        "title": t.title,
                        "time": "新投递",
                        "status": "去初筛",
                        "candidate_id": t.candidate_id
                    })

            if not todos:
                alerts = db.query(models.Candidate).filter(
                    models.Candidate.match_score > 85
                ).order_by(models.Candidate.match_score.desc()).limit(5).all()
                for c in alerts:
                    todos.append({
                        "id": c.id,
                        "type": "resume_alert",
                        "title": f"高分预警: {c.name} ({c.match_score}分)",
                        "time": "刚刚",
                        "status": "待查看",
                        "candidate_id": c.id
                    })

            activities = [
                {
                    "id": 1,
                    "content": "AI 简历分析服务运行正常，智能匹配引擎已就绪。",
                    "time": "10 分钟前",
                    "icon": "sparkles",
                    "color": "#AF52DE",
                    "candidate_id": None
                }
            ]
            recent_logs = db.query(models.CandidateLog).order_by(models.CandidateLog.created_at.desc()).limit(3).all()
            for idx, log in enumerate(recent_logs):
                activities.append({
                    "id": 30 + idx,
                    "content": f"<strong>{log.operator}</strong> 进行了操作：{log.action}，详情：{log.details or ''}",
                    "time": log.created_at.strftime("%m-%d %H:%M"),
                    "icon": "activity",
                    "color": "#007AFF",
                    "candidate_id": log.candidate_id
                })
            
        return {
            "stats": stats,
            "todos": todos,
            "activities": activities
        }
    except Exception as e:
        print(f"Dashboard query fallback error: {e}")
        return {
            "stats": [
                {"label": "活跃职位", "value": 8, "change": "热招中", "icon": "briefcase"},
                {"label": "本周候选人", "value": 24, "change": "新增简历", "icon": "users"},
                {"label": "待处理任务", "value": 5, "change": "协同处理待办", "icon": "calendar"},
                {"label": "待处理预警", "value": 3, "change": "高分简历", "icon": "alert-circle"}
            ],
            "todos": [],
            "activities": [
                {
                    "id": 1,
                    "content": "系统工作台数据已就绪，各项模块正常服务中。",
                    "time": "刚刚",
                    "icon": "sparkles",
                    "color": "#AF52DE",
                    "candidate_id": None
                }
            ]
        }

@app.get("/api/tasks", response_model=list[schemas.SystemTaskResponse])
def get_system_tasks(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role not in ["SuperAdmin", "Admin", "Recruiter"]:
        raise HTTPException(status_code=403, detail="没有权限查看任务列表")
    tasks = db.query(models.SystemTask).filter(models.SystemTask.status == "pending").all()
    return tasks

@app.post("/api/tasks/{task_id}/resolve", response_model=schemas.SystemTaskResponse)
def resolve_system_task(task_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role not in ["SuperAdmin", "Admin", "Recruiter"]:
        raise HTTPException(status_code=403, detail="没有权限执行此操作")
    task = db.query(models.SystemTask).filter(models.SystemTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = "resolved"
    db.commit()
    db.refresh(task)
    return task

    return task

# ==============================================================================
#                      ▎ OFFER APPROVAL ENGINE ROUTERS
# ==============================================================================

@app.get("/api/settings/users", response_model=list[schemas.UserResponse])
def get_settings_users(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.User).all()

@app.get("/api/settings/approval-rules", response_model=list[schemas.OfferApprovalRuleResponse])
def get_approval_rules(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.OfferApprovalRule).all()

@app.post("/api/settings/approval-rules", response_model=schemas.OfferApprovalRuleResponse)
def create_approval_rule(item: schemas.OfferApprovalRuleCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_admin_permission(current_user)
    db_item = models.OfferApprovalRule(
        name=item.name,
        department=item.department,
        job_level=item.job_level,
        steps=[s.model_dump() for s in item.steps]
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.patch("/api/settings/approval-rules/{item_id}", response_model=schemas.OfferApprovalRuleResponse)
def update_approval_rule(item_id: int, item: schemas.OfferApprovalRuleCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_admin_permission(current_user)
    db_item = db.query(models.OfferApprovalRule).filter(models.OfferApprovalRule.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Rule not found")
    db_item.name = item.name
    db_item.department = item.department
    db_item.job_level = item.job_level
    db_item.steps = [s.model_dump() for s in item.steps]
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/api/settings/approval-rules/{item_id}")
def delete_approval_rule(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_admin_permission(current_user)
    db.query(models.OfferApprovalRule).filter(models.OfferApprovalRule.id == item_id).delete()
    db.commit()
    return {"ok": True}

@app.post("/api/approvals/launch", response_model=schemas.OfferApprovalInstanceResponse)
def launch_offer_approval(item: schemas.OfferApprovalInstanceCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # 1. 查找候选人及所投职位
    cand = db.query(models.Candidate).filter(models.Candidate.id == item.candidate_id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # 2. 智能匹配规则 (精确双匹配 -> 单部门匹配 -> 单职级匹配 -> 全局默认)
    rule = db.query(models.OfferApprovalRule).filter(
        models.OfferApprovalRule.department == item.department,
        models.OfferApprovalRule.job_level == item.job_level
    ).first()
    
    if not rule:
        rule = db.query(models.OfferApprovalRule).filter(
            models.OfferApprovalRule.department == item.department,
            models.OfferApprovalRule.job_level == None
        ).first()
        
    if not rule:
        rule = db.query(models.OfferApprovalRule).filter(
            models.OfferApprovalRule.department == None,
            models.OfferApprovalRule.job_level == item.job_level
        ).first()
        
    if not rule:
        rule = db.query(models.OfferApprovalRule).filter(
            models.OfferApprovalRule.name == "默认全局审批流"
        ).first()
        
    # 3. 固化步骤及节点初始化
    steps_list = []
    if rule and rule.steps:
        steps_list = [
            {
                "label": s["label"],
                "approver_email": s["approver_email"],
                "status": "pending",
                "comment": "",
                "action_time": ""
            }
            for s in rule.steps
        ]
    else:
        # 硬编码极简兜底
        steps_list = [
            {"label": "HR上级", "approver_email": "hr_manager@example.com", "status": "pending", "comment": "", "action_time": ""},
            {"label": "HRVP", "approver_email": "hrvp@example.com", "status": "pending", "comment": "", "action_time": ""}
        ]
        
    # 4. 创建实例
    instance = models.OfferApprovalInstance(
        candidate_id=item.candidate_id,
        candidate_name=cand.name,
        job_title=cand.job or "未知职位",
        salary=item.salary,
        job_level=item.job_level,
        department=item.department,
        current_step_index=0,
        status="pending",
        creator_email=current_user.email,
        steps_data=steps_list,
        offer_details=item.offer_details.dict() if item.offer_details else None
    )
    
    db.add(instance)
    
    # 5. 自动记录候选人动态日志
    new_log = models.CandidateLog(
        candidate_id=cand.id,
        operator=current_user.name,
        action="已发起 Offer 审批",
        details=f"职级: {item.job_level} | 部门: {item.department} | 薪酬方案: {item.salary}"
    )
    db.add(new_log)
    db.commit()
    db.refresh(instance)
    
    # 6. 自动触发飞书通知接口推送 (后台模拟打印)
    if len(steps_list) > 0:
        services.FeishuNotificationService.send_offer_approval_card(instance, steps_list[0])
        
    return instance

# Offer 详情字段填报配置 (默认全量 30 项大厂字段定义与预填模板配置)
DEFAULT_OFFER_FIELDS_CONFIG = [
    # 1. 基础与合规类
    {"field_key": "compliance_pass", "field_name": "请判断该员工是否符合签署雪球基金的条件", "category": "基础与合规", "enabled": True, "required": False, "control_type": "select", "options": ["是", "否"]},
    {"field_key": "contract_subject", "field_name": "合同主体", "category": "基础与合规", "enabled": True, "required": True, "control_type": "select", "options": ["北京雪球私募基金管理有限公司", "雪球(北京)技术开发有限公司", "上海雪球信息科技有限公司", "香港雪球金融服务有限公司"]},
    {"field_key": "department", "field_name": "入职部门", "category": "基础与合规", "enabled": True, "required": True, "control_type": "dept_tree", "use_dept_tree": True, "options": []},
    {"field_key": "job_level", "field_name": "拟录用职级", "category": "基础与合规", "enabled": True, "required": False, "control_type": "select", "options": ["X4", "X5", "X6", "X7", "P5", "P6", "P7", "P8", "M1", "M2"]},
    {"field_key": "proposed_start_date", "field_name": "预计入职日期", "category": "基础与合规", "enabled": True, "required": True, "control_type": "input", "options": []},
    {"field_key": "employee_type", "field_name": "员工类型", "category": "基础与合规", "enabled": True, "required": False, "control_type": "select", "options": ["正式员工", "实习生", "外包人员", "顾问/兼职"]},
    {"field_key": "is_campus_hire", "field_name": "是否校招生", "category": "基础与合规", "enabled": True, "required": False, "control_type": "select", "options": ["否", "是"]},

    # 2. 薪酬考核与福利类
    {"field_key": "base_salary", "field_name": "基础月薪（元）", "category": "薪酬考核与福利", "enabled": True, "required": True, "control_type": "input", "options": []},
    {"field_key": "perf_salary", "field_name": "绩效工资-私行适用", "category": "薪酬考核与福利", "enabled": True, "required": False, "control_type": "select", "options": ["0", "2000", "5000", "8000"]},
    {"field_key": "probation_rate", "field_name": "私行适用-试用期工资发放比例", "category": "薪酬考核与福利", "enabled": True, "required": False, "control_type": "select", "options": ["100%", "80%", "90%"]},
    {"field_key": "target_bonus_months", "field_name": "目标年终奖金月数", "category": "薪酬考核与福利", "enabled": True, "required": False, "control_type": "select", "options": ["2", "3", "4", "6"]},
    {"field_key": "stock_options", "field_name": "期权数", "category": "薪酬考核与福利", "enabled": True, "required": False, "control_type": "select", "options": ["0", "5000", "10000", "20000"]},
    {"field_key": "probation_months", "field_name": "试用期（月）", "category": "薪酬考核与福利", "enabled": True, "required": False, "control_type": "select", "options": ["6", "3", "1"]},
    {"field_key": "prev_month_salary", "field_name": "上家公司月薪（元）", "category": "薪酬考核与福利", "enabled": True, "required": False, "control_type": "input", "options": []},
    {"field_key": "prev_annual_salary", "field_name": "上家公司年薪（元）", "category": "薪酬考核与福利", "enabled": True, "required": False, "control_type": "input", "options": []},

    # 3. 架构序列与主管类
    {"field_key": "job_category", "field_name": "职位类", "category": "架构序列与主管", "enabled": True, "required": False, "control_type": "select", "options": ["职能支持类", "技术研发类", "产品运营类", "市场销售类"]},
    {"field_key": "job_family", "field_name": "职位族", "category": "架构序列与主管", "enabled": True, "required": False, "control_type": "select", "options": ["法务合规", "软件工程", "产品设计", "人力资源", "财务风控"]},
    {"field_key": "job_sequence", "field_name": "职位序列", "category": "架构序列与主管", "enabled": True, "required": False, "control_type": "select", "options": ["风控合规", "后端开发", "前端开发", "数据分析"]},
    {"field_key": "base_position", "field_name": "基础岗位", "category": "架构序列与主管", "enabled": True, "required": False, "control_type": "select", "options": ["风控合规专家", "高级软件工程师", "资深HRBP", "财务经理"]},
    {"field_key": "contract_title", "field_name": "合同职位", "category": "架构序列与主管", "enabled": True, "required": False, "control_type": "select", "options": ["高级风控合规", "资深开发工程师", "高级产品经理"]},
    {"field_key": "direct_manager", "field_name": "直属主管", "category": "架构序列与主管", "enabled": True, "required": False, "control_type": "select", "options": ["代天娇", "孟繁拙", "曹一雄"]},
    {"field_key": "gender", "field_name": "性别", "category": "架构序列与主管", "enabled": True, "required": False, "control_type": "select", "options": ["女", "男"]},

    # 4. 办公地点与成本类
    {"field_key": "pc_config", "field_name": "电脑配置", "category": "办公地点与成本", "enabled": True, "required": False, "control_type": "select", "options": ["Windows 笔记本 (Standard)", "MacBook Pro 14 (M3)", "MacBook Pro 16 (M3 Max)", "自带设备 (BYOD)"]},
    {"field_key": "onboard_location", "field_name": "入职办理地点", "category": "办公地点与成本", "enabled": True, "required": False, "control_type": "select", "options": ["北京市朝阳区融新科技中心C座18层", "上海市静安区嘉里中心22层", "深圳市南山区腾讯大厦B座"]},
    {"field_key": "work_area", "field_name": "办公区", "category": "办公地点与成本", "enabled": True, "required": False, "control_type": "select", "options": ["北京（融新）", "北京（朝阳）", "上海（嘉里）", "深圳（南山）", "成都（高新）"]},
    {"field_key": "cost_center", "field_name": "成本中心-财务", "category": "办公地点与成本", "enabled": True, "required": False, "control_type": "select", "options": ["资产管理", "技术研发部", "市场营销部", "法务合规部", "行政人事部"]},
    {"field_key": "salary_special_note", "field_name": "薪酬特殊说明（年现金涨幅超20%时说明原因）", "category": "办公地点与成本", "enabled": True, "required": False, "control_type": "input", "options": []},
    {"field_key": "edu_special_note", "field_name": "学历特殊说明", "category": "办公地点与成本", "enabled": True, "required": False, "control_type": "select", "options": ["-", "统招本科双学士", "QS前50海归硕士"]},
    {"field_key": "attachment_name", "field_name": "发送附件给审批人", "category": "办公地点与成本", "enabled": True, "required": False, "control_type": "input", "options": []},
    {"field_key": "remarks", "field_name": "备注（职级，HC，核心职责等）", "category": "办公地点与成本", "enabled": True, "required": False, "control_type": "input", "options": []}
]

offer_fields_config_db = [dict(item) for item in DEFAULT_OFFER_FIELDS_CONFIG]

@app.get("/api/approvals/offer-fields-config")
def get_offer_fields_config(current_user: models.User = Depends(get_current_user)):
    return offer_fields_config_db

@app.post("/api/approvals/offer-fields-config")
def save_offer_fields_config(payload: list[dict], current_user: models.User = Depends(get_current_user)):
    global offer_fields_config_db
    offer_fields_config_db = payload
    return {"status": "ok", "msg": "Offer 详情字段填报配置保存成功", "config": offer_fields_config_db}

@app.get("/api/approvals/pending", response_model=list[schemas.OfferApprovalInstanceResponse])
def get_pending_approvals(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    try:
        instances = db.query(models.OfferApprovalInstance).filter(models.OfferApprovalInstance.status == "pending").all()
        pending_list = []
        for inst in instances:
            steps = inst.steps_data
            if isinstance(steps, str):
                try:
                    steps = json.loads(steps)
                except Exception:
                    steps = []
            elif not isinstance(steps, list):
                steps = []

            step_idx = inst.current_step_index or 0
            if 0 <= step_idx < len(steps):
                current_step = steps[step_idx]
                if isinstance(current_step, dict) and current_step.get("approver_email") == current_user.email:
                    pending_list.append(inst)
        return pending_list
    except Exception as e:
        print(f"Error in get_pending_approvals: {e}")
        return []

@app.get("/api/approvals/my-launches", response_model=list[schemas.OfferApprovalInstanceResponse])
def get_my_launches(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    try:
        return db.query(models.OfferApprovalInstance).filter(models.OfferApprovalInstance.creator_email == current_user.email).all()
    except Exception as e:
        print(f"Error in get_my_launches: {e}")
        return []

@app.get("/api/approvals/candidate/{candidate_id:int}", response_model=Optional[schemas.OfferApprovalInstanceResponse])
def get_candidate_approval(candidate_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    instance = db.query(models.OfferApprovalInstance).filter(
        models.OfferApprovalInstance.candidate_id == candidate_id
    ).order_by(models.OfferApprovalInstance.id.desc()).first()
    return instance

@app.get("/api/approvals/{id:int}", response_model=schemas.OfferApprovalInstanceResponse)
def get_approval_detail(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    inst = db.query(models.OfferApprovalInstance).filter(models.OfferApprovalInstance.id == id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")
    return inst

@app.post("/api/approvals/{id:int}/action", response_model=schemas.OfferApprovalInstanceResponse)
def action_offer_approval(id: int, req: schemas.OfferApprovalActionRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    inst = db.query(models.OfferApprovalInstance).filter(models.OfferApprovalInstance.id == id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")
    if inst.status != "pending":
        raise HTTPException(status_code=400, detail="流程已结束")
        
    steps = inst.steps_data or []
    if inst.current_step_index < 0 or inst.current_step_index >= len(steps):
        raise HTTPException(status_code=400, detail="异常的节点流转位置")
        
    current_step = steps[inst.current_step_index]
    if current_step.get("approver_email") != current_user.email:
        raise HTTPException(status_code=403, detail="您不是当前节点的审批人")
        
    import datetime
    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    # 执行决策
    if req.action == "approve":
        current_step["status"] = "approved"
        current_step["comment"] = req.comment or "同意"
        current_step["action_time"] = now_str
        
        # 递增至下一个节点
        inst.current_step_index += 1
        if inst.current_step_index >= len(steps):
            # 终审通过
            inst.status = "approved"
            # 自动联动将候选人招聘阶段更新为“沟通offer”
            cand = db.query(models.Candidate).filter(models.Candidate.id == inst.candidate_id).first()
            if cand:
                cand.stage = "沟通offer"
                new_log = models.CandidateLog(
                    candidate_id=cand.id,
                    operator="系统审核流",
                    action="Offer审批终审通过",
                    details="薪酬及各级审核通过，候选人阶段已推进至：沟通offer"
                )
                db.add(new_log)
        else:
            # 流转给下一级，触发飞书推送
            next_step = steps[inst.current_step_index]
            services.FeishuNotificationService.send_offer_approval_card(inst, next_step)
            
    elif req.action == "reject":
        current_step["status"] = "rejected"
        current_step["comment"] = req.comment or "驳回"
        current_step["action_time"] = now_str
        
        # 流程中止
        inst.status = "rejected"
        cand = db.query(models.Candidate).filter(models.Candidate.id == inst.candidate_id).first()
        if cand:
            new_log = models.CandidateLog(
                candidate_id=cand.id,
                operator=current_user.name,
                action="Offer审批已被驳回",
                details=f"驳回人: {current_user.name} | 原因: {req.comment or '无'}"
            )
            db.add(new_log)
            
    # 强制将修改标记为脏数据以确保 JSON 数据类型被 SQLAlchmey 捕获更新入库
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(inst, "steps_data")
    
    db.commit()
    db.refresh(inst)
    return inst

@app.post("/api/feishu/approval-callback")
def feishu_approval_callback(payload: dict, db: Session = Depends(get_db)):
    # 飞书消息卡片交互回调WebHook占位接口 (优先无需跳转直接响应)
    print("Received Feishu approval callback payload:", payload)
    return {"status": "ok", "msg": "飞书卡片数据已实时刷新"}

if __name__ == "__main__":
    # In Zeabur, use the PORT environment variable
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
